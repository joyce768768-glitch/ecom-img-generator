"""
server.py - FastAPI Web后端（前端交互使用）
------------------------------------------------
【类型可配置版】
- 类型（TypeConfig）：白名单 + 15场景Prompt + 类目专属System段，持久化 JSON
- 强制流程：主页面必须先选类型（type_id）才能生成

接口一览：
  基础：
    GET  /api/config        - 前端初始化：模型枚举/尺寸常量表/类型列表简版/全局负面词基础段
    POST /api/generate      - 触发生成，必须传 type_id
    GET  /api/status/{id}   - 轮询进度+日志
    GET  /api/results/{id}  - 已生成图片清单
    GET  /output/{file}     - 静态图片访问
  类型管理（8 个）：
    GET    /api/types                 - 类型列表（仅 type_id/type_name/计数元信息）
    GET    /api/types/{type_id}       - 类型详情（含白名单、15场景完整结构）
    POST   /api/types                 - 新建类型
    PUT    /api/types/{type_id}       - 更新类型（支持部分字段）
    DELETE /api/types/{type_id}       - 删除类型（至少保留1个）
    POST   /api/types/{id}/duplicate  - 复制类型
    GET    /api/types/export          - 导出全部类型为 JSON
    POST   /api/types/import          - 导入（body: { mode: "merge"|"replace", data: {...} }）
"""
from __future__ import annotations

import io
import json
import logging
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Union

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# 四层业务模块（与main.py共用一套核心代码，零重复）
from config import (
    IMAGE_SIZE,
    ImageModel,
    ModelConfig,
    NEGATIVE_PROMPT,
    OUTPUT_DIR,
    ProductInfo,
    validate_product_params,
)
from prompt_builder import BuiltPrompt, PromptBuilder
from image_client import create_image_client
from type_configs import TypeConfig, get_type_manager
from translator import auto_translate_scenes, translate_zh_to_en

# ---------------------------
# FastAPI App
# ---------------------------
app = FastAPI(title="1688电商主图/详情图生成Agent", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载输出目录，前端可直接 /output/main_1.png 预览图片
os.makedirs(OUTPUT_DIR, exist_ok=True)
app.mount("/output", StaticFiles(directory=OUTPUT_DIR), name="output")

# 日志
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("server")

# 类型管理器单例
_TM = get_type_manager()


# ============================================================
# 任务状态模型（内存态，重启清空；本地工具无需持久化）
# ============================================================
@dataclass
class TaskLogEntry:
    ts: float
    level: str   # INFO / WARN / ERROR
    message: str


@dataclass
class TaskState:
    task_id: str
    type_id: str
    type_name: str
    model: str
    only_keys: List[str]
    dry_run: bool
    output_dir: str
    status: str = "pending"   # pending / running / done
    total: int = 0
    done: int = 0
    failed: int = 0
    current_key: Optional[str] = None
    logs: List[TaskLogEntry] = field(default_factory=list)
    generated_paths: List[str] = field(default_factory=list)
    start_ts: float = field(default_factory=time.time)
    end_ts: Optional[float] = None

    def log(self, level: str, message: str) -> None:
        self.logs.append(TaskLogEntry(ts=time.time(), level=level, message=message))
        if len(self.logs) > 300:
            self.logs = self.logs[-300:]


TASKS: Dict[str, TaskState] = {}
_LOCK = threading.Lock()


# ============================================================
# Pydantic 请求/响应模型
# ============================================================
class GenerateRequest(BaseModel):
    type_id: str = Field(..., description="必填：配置中心创建的类型 ID")
    model: str = Field(
        default=ModelConfig().DEFAULT_MODEL.value,
        description=f"图像模型枚举: {[m.value for m in ImageModel]}",
    )
    only_keys: List[str] = Field(
        default_factory=list,
        description="空=该类型下全部场景，否则如 [main_1,detail_3]",
    )
    dry_run: bool = Field(default=False, description="仅打印Prompt不调用API，生成占位图")
    extra_negative: str = Field(
        default="", description="用户自定义追加的负面词，会拼到通用负面词后面"
    )
    product: Dict[str, Any] = Field(
        ...,
        description="必填：商品参数 dict（基于所选类型的白名单）",
    )
    original_image: Optional[str] = Field(
        default=None,
        description="商品原始图 base64 data URL，作为15张图的设计参考",
    )
    ref_strength: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="参考图影响强度（0-1，仅当 original_image 存在时生效；越大越接近参考图）",
    )


class TypeCreateRequest(BaseModel):
    type_id: Optional[str] = None
    type_name: str
    default_title: str = ""
    titles: List[str] = []
    materials: List[str] = []
    specs: List[str] = []
    colors: List[str] = []
    features: List[str] = []
    default_selected_features: List[str] = []
    system_extra_prompt: str = ""
    main_scenes: Optional[Union[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]] = None
    detail_scenes: Optional[Union[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]] = None


class TypeUpdateRequest(BaseModel):
    type_name: Optional[str] = None
    default_title: Optional[str] = None
    titles: Optional[List[str]] = None
    materials: Optional[List[str]] = None
    specs: Optional[List[str]] = None
    colors: Optional[List[str]] = None
    features: Optional[List[str]] = None
    default_selected_features: Optional[List[str]] = None
    system_extra_prompt: Optional[str] = None
    main_scenes: Optional[Union[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]] = None
    detail_scenes: Optional[Union[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]] = None


class DuplicateRequest(BaseModel):
    new_type_name: str
    new_type_id: Optional[str] = None


class TranslateRequest(BaseModel):
    zh_text: str = Field(..., description="中文文本，翻译为英文")


class ImportRequest(BaseModel):
    mode: str = Field(default="merge", description="merge（按type_id覆盖并保留其他） | replace（清空重写）")
    data: Dict[str, Any] = Field(..., description="从 /api/types/export 导出的完整 JSON")


# ============================================================
# 辅助：TypeConfig → 前端响应 dict
# ============================================================
def _type_slim(t: TypeConfig) -> Dict[str, Any]:
    return {
        "type_id": t.type_id,
        "type_name": t.type_name,
        "default_title": t.default_title,
        "main_count": len(t.main_scenes),
        "detail_count": len(t.detail_scenes),
        "titles_count": len(t.titles),
        "materials_count": len(t.materials),
        "specs_count": len(t.specs),
        "colors_count": len(t.colors),
        "features_count": len(t.features),
        "has_system_extra": bool(t.system_extra_prompt.strip()),
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


def _type_full(t: TypeConfig) -> Dict[str, Any]:
    return {
        "type_id": t.type_id,
        "type_name": t.type_name,
        "default_title": t.default_title,
        "titles": t.titles,
        "materials": t.materials,
        "specs": t.specs,
        "colors": t.colors,
        "features": t.features,
        "default_selected_features": t.default_selected_features,
        "system_extra_prompt": t.system_extra_prompt,
        "main_scenes": [
            {
                "key": sc.key,
                "scene_cn": sc.scene_cn,
                "scene_en": sc.scene_en,
                "size": sc.size,
            }
            for sc in _sorted_scenes(t.main_scenes, "main")
        ],
        "detail_scenes": [
            {
                "key": sc.key,
                "scene_cn": sc.scene_cn,
                "scene_en": sc.scene_en,
                "size": sc.size,
            }
            for sc in _sorted_scenes(t.detail_scenes, "detail")
        ],
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


def _sorted_scenes(pool: Dict, prefix: str) -> List:
    def _sort_key(k: str):
        rest = k[len(prefix) + 1:] if k.startswith(f"{prefix}_") else k
        return (0, int(rest)) if rest.isdigit() else (1, k)
    return [pool[k] for k in sorted(pool.keys(), key=_sort_key)]


# ============================================================
# 核心生成Worker
# ============================================================
def _run_generation_task(
    state: TaskState,
    product: ProductInfo,
    extra_negative: str = "",
    original_image: Optional[str] = None,
    ref_strength: float = 0.5,
) -> None:
    try:
        state.status = "running"
        state.log(
            "INFO",
            f"任务启动: type={state.type_name}({state.type_id}), "
            f"model={state.model}, dry_run={state.dry_run}"
            + (f", 参考图=有, ref_strength={ref_strength}" if original_image else ", 参考图=无")
        )

        # 1. Prompt 构建（带白名单校验）
        validate_product_params(product)
        builder = PromptBuilder(product, extra_negative=extra_negative, original_image=original_image)
        all_prompts: List[BuiltPrompt] = list(builder.build_all())
        if state.only_keys:
            run_prompts = [p for p in all_prompts if p.scene_key in state.only_keys]
        else:
            run_prompts = all_prompts
        state.total = len(run_prompts)
        state.log(
            "INFO",
            f"构建Prompt完成: 类型总场景={len(all_prompts)}, 本轮生成={state.total}, "
            f"system_extra={'有' if builder._system_extra else '无'}"
        )

        # 1.5 保存参考图到 output 目录（供 dashscope ref_img 使用）
        ref_img_url = None
        if original_image and original_image.startswith("data:image"):
            try:
                import base64 as b64mod
                # 解析 data URL: data:image/png;base64,xxxx
                header, b64data = original_image.split(",", 1)
                img_bytes = b64mod.b64decode(b64data)

                # 1.5.1 rembg 自动抠图：去除原背景干扰，只保留商品主体
                #   抠图失败时降级使用原图，不阻断流程
                try:
                    # 设置模型缓存目录到项目内（避免沙箱限制 ~/.u2net）
                    os.environ.setdefault(
                        "U2NET_HOME",
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".u2net"),
                    )
                    from rembg import remove as rembg_remove
                    clean_bytes = rembg_remove(img_bytes)
                    # rembg 输出为 RGBA PNG；保存为 PNG 保留透明背景
                    state.log("INFO", "rembg 抠图成功，已去除原背景（输出透明 PNG）")
                    img_bytes_to_save = clean_bytes
                except ImportError:
                    state.log("WARNING", "rembg 未安装，参考图未抠图（建议 pip install rembg）")
                    img_bytes_to_save = img_bytes
                except Exception as rembg_err:
                    state.log("WARNING", f"rembg 抠图失败，降级使用原图: {type(rembg_err).__name__}: {rembg_err}")
                    img_bytes_to_save = img_bytes

                ref_path = os.path.join(state.output_dir, "_original_ref.png")
                with open(ref_path, "wb") as f:
                    f.write(img_bytes_to_save)
                # 构建可访问的 URL（后端静态文件服务已挂载 /output）
                ref_img_url = f"http://127.0.0.1:8000/output/_original_ref.png"
                state.log("INFO", f"参考图已保存: {ref_path} → URL: {ref_img_url}")
            except Exception as e:
                state.log("WARNING", f"参考图保存失败（将仅用文字描述）: {e}")

        # 2. 模型客户端
        client = None
        if not state.dry_run:
            model_enum = ImageModel(state.model)
            ref_info = ""
            if ref_img_url:
                ref_info = (
                    f", ref_img=有, ref_strength={ref_strength}, "
                    f"模式=wanx2.1-imageedit 图像编辑(保持商品主体, strength={round(1.0 - ref_strength, 3)})"
                )
            state.log(
                "INFO",
                f"初始化图像客户端: {state.model} "
                f"({'云端' if ImageModel.is_cloud(model_enum) else '本地'}){ref_info}"
            )
            try:
                client = create_image_client(
                    model_enum,
                    state.output_dir,
                    ref_img_url=ref_img_url,
                    ref_strength=ref_strength,
                )
            except Exception as e:
                state.status = "done"
                state.end_ts = time.time()
                state.log("ERROR", f"模型客户端初始化失败: {type(e).__name__}: {e}")
                return

        # 3. 循环生成
        for idx, p in enumerate(run_prompts, 1):
            state.current_key = p.scene_key
            state.log("INFO", f"[{idx}/{state.total}] {p.scene_key}（{p.scene_cn}）开始")
            state.log("INFO", f"[{p.scene_key}] POSITIVE: {p.positive}")
            scene_start = time.time()
            save_path = os.path.abspath(os.path.join(state.output_dir, f"{p.scene_key}.png"))

            if state.dry_run:
                try:
                    from PIL import Image, ImageDraw, ImageFont
                    size = IMAGE_SIZE.get(p.size_type) or (800, 800)
                    img = Image.new("RGB", size, (230, 232, 235))
                    draw = ImageDraw.Draw(img)
                    draw.text((20, 30), f"[DRY-RUN] {p.scene_key}  {p.scene_cn}", fill=(30, 64, 175))
                    draw.text((20, 70), f"{size[0]}x{size[1]} | {state.model} | type={state.type_name}", fill=(75, 85, 99))
                    draw.text((20, 110), f"System Extra: {'ON' if builder._system_extra else 'OFF'}", fill=(34, 139, 34))
                    img.save(save_path)
                    state.generated_paths.append(save_path)
                    state.done += 1
                    state.log("INFO", f"[{idx}/{state.total}] {p.scene_key} DRY-RUN 占位图完成 → {save_path}")
                except Exception as e:
                    state.failed += 1
                    state.log("ERROR", f"[{idx}/{state.total}] 占位图失败: {type(e).__name__}: {e}")
                continue

            # 真·生成
            try:
                real_path = client.generate_image(
                    prompt=p.positive,
                    size_type=p.size_type,
                    negative_prompt=p.negative,
                    file_stem=p.scene_key,
                )
                elapsed = time.time() - scene_start
                state.generated_paths.append(real_path)
                state.done += 1
                state.log(
                    "INFO",
                    f"[{idx}/{state.total}] {p.scene_key} 完成, 耗时 {elapsed:.1f}s → {real_path}"
                )
            except Exception as e:
                state.failed += 1
                state.log(
                    "ERROR",
                    f"[{idx}/{state.total}] {p.scene_key} 失败: {type(e).__name__}: {e}"
                )

        state.status = "done"
        state.end_ts = time.time()
        elapsed_total = (state.end_ts or state.start_ts) - state.start_ts
        state.log(
            "INFO",
            f"任务结束: 成功 {state.done}/{state.total}, 失败 {state.failed}, 总耗时 {elapsed_total:.1f}s"
        )

    except Exception as e:
        state.status = "done"
        state.end_ts = time.time()
        state.log("ERROR", f"任务异常终止: {type(e).__name__}: {e}")


# ============================================================
# API 路由
# ============================================================
@app.get("/")
async def index_html():
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=404, detail="templates/index.html 不存在（前端以 Vite dev server 方式运行时无需此文件）")
    return FileResponse(html_path, media_type="text/html; charset=utf-8")


# ----------------------
# 基础：初始化配置
# ----------------------
@app.get("/api/config")
async def api_config():
    """前端初始化：模型枚举 + 类型列表简版 + 尺寸常量表 + 基础负面词 + API Key配置状态"""
    models = []
    for m in ImageModel:
        label_map = {
            ImageModel.TONGYI_WANXIANG: "通义万相（云端·电商推荐）",
            ImageModel.DALLE3: "DALL·E3（云端·通用SOTA）",
            ImageModel.OLLAMA_SDXL: "Ollama SDXL（本地·免费）",
            ImageModel.OLLAMA_FLUX: "Ollama Flux（本地·画质SOTA）",
        }
        models.append({
            "value": m.value,
            "label": label_map.get(m, m.value),
            "type": "cloud" if ImageModel.is_cloud(m) else "local",
        })
    mc = ModelConfig()
    return {
        "models": models,
        "default_model": mc.DEFAULT_MODEL.value,
        "types": [_type_slim(t) for t in _TM.list_all()],
        "sizes": {k: list(v) for k, v in IMAGE_SIZE.items()},
        "negative_base": NEGATIVE_PROMPT,
        "api_keys": {
            "dashscope_configured": bool(mc.DASHSCOPE_API_KEY),
            "openai_configured": bool(mc.OPENAI_API_KEY),
            "ollama_configured": True,  # Ollama 本地无需 Key，总是可用
        },
        "message": (
            "请先在顶部选择「类型」（没有合适的就点右上角「配置中心」新增）。"
            "类型选定后，会拉取该类型下的：白名单下拉值、默认参数、15场景模板。"
        ),
    }


class ApiKeyUpdateRequest(BaseModel):
    dashscope_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None


@app.post("/api/config/api-keys")
async def update_api_keys(req: ApiKeyUpdateRequest):
    """保存 API Key 到 .env 文件（不返回密钥明文）"""
    try:
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")

        def _read_env() -> Dict[str, str]:
            env: Dict[str, str] = {}
            if os.path.exists(env_path):
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            env[k.strip()] = v.strip().strip('"').strip("'")
            return env

        def _write_env(env: Dict[str, str]) -> None:
            with open(env_path, "w", encoding="utf-8") as f:
                for k, v in env.items():
                    f.write(f'{k}="{v}"\n')

        env = _read_env()
        changed = False

        if req.dashscope_api_key is not None:
            env["DASHSCOPE_API_KEY"] = req.dashscope_api_key.strip()
            changed = True
        if req.openai_api_key is not None:
            env["OPENAI_API_KEY"] = req.openai_api_key.strip()
            changed = True

        if changed:
            _write_env(env)
            # 重新加载 .env 到进程环境
            from dotenv import load_dotenv
            load_dotenv(override=True)

        mc = ModelConfig()
        return {
            "ok": True,
            "api_keys": {
                "dashscope_configured": bool(mc.DASHSCOPE_API_KEY),
                "openai_configured": bool(mc.OPENAI_API_KEY),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存 API Key 失败: {e}")


# ----------------------
# 类型管理：列表/导入/导出（静态路径路由放最前，避免被 {type_id} 误匹配）
# ----------------------
@app.get("/api/types")
async def list_types(slim: bool = True):
    """默认 slim=true 返回简版（配置中心列表）；slim=false 返回全部（极少用）"""
    all_t = _TM.list_all()
    if slim:
        return {"items": [_type_slim(t) for t in all_t], "total": len(all_t)}
    return {"items": [_type_full(t) for t in all_t], "total": len(all_t)}


@app.get("/api/types/export")
async def export_types():
    data = _TM.export_all()
    filename = f"type_configs_export_{int(time.time())}.json"
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@app.post("/api/types/import")
async def import_types(req: ImportRequest):
    try:
        mode = (req.mode or "merge").lower()
        if mode not in ("merge", "replace"):
            raise ValueError(f"非法 mode: {req.mode!r}，仅支持 merge/replace")
        items = _TM.import_all(req.data, mode=mode)
        return {
            "ok": True,
            "mode": mode,
            "items": [_type_slim(t) for t in items],
            "total": len(items),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/types/import-file")
async def import_types_file(
    mode: str = Form(default="merge"),
    file: UploadFile = File(...),
):
    """通过上传 JSON 文件方式导入（与 import 接口等价，方便 UI 操作）"""
    try:
        raw = await file.read()
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict) or "types" not in data:
            raise ValueError("上传的 JSON 缺少 types 字段（请使用 /api/types/export 导出的格式）")
        mode_v = (mode or "merge").lower()
        if mode_v not in ("merge", "replace"):
            raise ValueError(f"非法 mode: {mode!r}")
        items = _TM.import_all(data, mode=mode_v)
        return {
            "ok": True,
            "mode": mode_v,
            "items": [_type_slim(t) for t in items],
            "total": len(items),
        }
    except (ValueError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=400, detail=f"导入失败: {e}")


# ----------------------
# 类型管理：增/改/删/详情/复制（带 {type_id} 参数的路由放静态路径后面）
# ----------------------
@app.post("/api/types")
async def create_type(req: TypeCreateRequest):
    try:
        payload = req.model_dump()
        # 把 main_scenes / detail_scenes 从 list 转 dict（list更适合前端编辑顺序）
        if isinstance(payload.get("main_scenes"), list):
            payload["main_scenes"] = {s["key"]: s for s in payload["main_scenes"]}
        if isinstance(payload.get("detail_scenes"), list):
            payload["detail_scenes"] = {s["key"]: s for s in payload["detail_scenes"]}
        # 自动翻译：scene_en 为空但 scene_cn 有中文时
        if payload.get("main_scenes"):
            payload["main_scenes"] = auto_translate_scenes(payload["main_scenes"])
        if payload.get("detail_scenes"):
            payload["detail_scenes"] = auto_translate_scenes(payload["detail_scenes"])
        created = _TM.create(payload)
        return {"ok": True, "item": _type_full(created)}
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/types/{type_id}")
async def get_type(type_id: str):
    t = _TM.get(type_id)
    if t is None:
        raise HTTPException(status_code=404, detail=f"type_id={type_id!r} 不存在")
    return _type_full(t)


@app.put("/api/types/{type_id}")
async def update_type(type_id: str, req: TypeUpdateRequest):
    try:
        payload = req.model_dump(exclude_unset=True)
        if isinstance(payload.get("main_scenes"), list):
            payload["main_scenes"] = {s["key"]: s for s in payload["main_scenes"]}
        if isinstance(payload.get("detail_scenes"), list):
            payload["detail_scenes"] = {s["key"]: s for s in payload["detail_scenes"]}
        # 自动翻译：scene_en 为空但 scene_cn 有中文时
        if payload.get("main_scenes"):
            payload["main_scenes"] = auto_translate_scenes(payload["main_scenes"])
        if payload.get("detail_scenes"):
            payload["detail_scenes"] = auto_translate_scenes(payload["detail_scenes"])
        updated = _TM.update(type_id, payload)
        return {"ok": True, "item": _type_full(updated)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/api/types/{type_id}")
async def delete_type(type_id: str):
    try:
        _TM.delete(type_id)
        return {"ok": True, "types": [_type_slim(t) for t in _TM.list_all()]}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/types/{src_type_id}/duplicate")
async def duplicate_type(src_type_id: str, req: DuplicateRequest):
    try:
        new_t = _TM.duplicate(src_type_id, req.new_type_name, req.new_type_id)
        return {"ok": True, "item": _type_full(new_t)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ----------------------
# 翻译接口（中文 → 英文）
# ----------------------
@app.post("/api/translate")
async def api_translate(req: TranslateRequest):
    """将中文文本翻译为英文（用于 scene_cn → scene_en 自动翻译）"""
    try:
        en_text = translate_zh_to_en(req.zh_text)
        is_cached = (en_text == req.zh_text)  # 翻译失败时返回原文
        return {
            "ok": True,
            "zh_text": req.zh_text,
            "en_text": en_text,
            "translated": not is_cached,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"翻译失败: {e}")


# ----------------------
# 基础：生成/状态/结果
# ----------------------
@app.post("/api/generate")
async def api_generate(req: GenerateRequest):
    """触发异步生成任务，必须传 type_id + product"""
    # 0. 强制 type_id 校验（用户决策4：无类型不执行）
    if not req.type_id:
        raise HTTPException(
            status_code=400,
            detail="未指定 type_id。请先在顶部选择类型（没有合适的请到「配置中心」新增）。",
        )
    t = _TM.get(req.type_id)
    if t is None:
        raise HTTPException(status_code=400, detail=f"type_id={req.type_id!r} 在服务器上不存在，请刷新或重新选择")

    # 1. 校验模型名
    try:
        model_enum = ImageModel(req.model)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"非法model: {req.model}")

    # 2. 组装 ProductInfo（严格来自 product dict）
    p = req.product or {}
    try:
        # 允许前端不传 features 字段
        feat_raw = p.get("features") or []
        if not isinstance(feat_raw, (list, tuple)):
            raise ValueError("product.features 必须是数组")
        product = ProductInfo(
            type_id=req.type_id,
            title=str(p.get("title", "") or "").strip(),
            material=str(p.get("material", "") or "").strip(),
            spec=str(p.get("spec", "") or "").strip(),
            color=str(p.get("color", "") or "").strip(),
            features=tuple(str(x).strip() for x in feat_raw if str(x).strip()),
        )
        validate_product_params(product)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. 创建任务
    task_id = uuid.uuid4().hex[:12]
    state = TaskState(
        task_id=task_id,
        type_id=t.type_id,
        type_name=t.type_name,
        model=model_enum.value,
        only_keys=list(req.only_keys or []),
        dry_run=bool(req.dry_run),
        output_dir=OUTPUT_DIR,
    )
    with _LOCK:
        TASKS[task_id] = state

    # 4. 后台线程执行
    t_th = threading.Thread(
        target=_run_generation_task,
        args=(state, product, req.extra_negative or "", req.original_image, req.ref_strength),
        daemon=True,
    )
    t_th.start()

    return {
        "task_id": task_id,
        "type_id": t.type_id,
        "type_name": t.type_name,
        "message": "任务已启动，请用 /api/status/{task_id} 轮询",
    }


@app.get("/api/status/{task_id}")
async def api_status(task_id: str, logs_since: Optional[int] = None):
    state = TASKS.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="task不存在")
    logs = state.logs
    if logs_since is not None and 0 <= logs_since < len(logs):
        logs = logs[logs_since:]
    return {
        "task_id": state.task_id,
        "type_id": state.type_id,
        "type_name": state.type_name,
        "status": state.status,
        "model": state.model,
        "dry_run": state.dry_run,
        "total": state.total,
        "done": state.done,
        "failed": state.failed,
        "current_key": state.current_key,
        "elapsed": round((time.time() - state.start_ts), 1) if state.status != "done"
                   else round((state.end_ts or state.start_ts) - state.start_ts, 1),
        "logs_since_next": len(state.logs),
        "logs": [asdict(l) for l in logs],
    }


@app.get("/api/results/{task_id}")
async def api_results(task_id: str):
    state = TASKS.get(task_id)
    if not state:
        raise HTTPException(status_code=404, detail="task不存在")
    items = []
    for p in state.generated_paths:
        fname = os.path.basename(p)
        try:
            size_kb = round(os.path.getsize(p) / 1024, 1)
        except OSError:
            size_kb = 0
        items.append({
            "file": fname,
            "key": os.path.splitext(fname)[0],
            "size_kb": size_kb,
            "url": f"/output/{fname}",
        })
    return {
        "task_id": task_id,
        "type_id": state.type_id,
        "type_name": state.type_name,
        "status": state.status,
        "output_dir": state.output_dir,
        "generated": items,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
