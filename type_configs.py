"""
类型配置管理器（持久化：项目根目录 type_configs.json）
- 多类目（类型）：每个类型有自己的白名单值 + 15张图场景 Prompt
- 线程安全的文件读写（RLock）
- 初始化时如文件不存在 → 写入内置默认衣架配置
"""
from __future__ import annotations

import copy
import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional


# ============================================================
# 数据结构
# ============================================================
@dataclass
class SceneConfig:
    """单图场景配置（一张主图/详情图的prompt配置）"""
    key: str                                    # main_1 / detail_1 等
    scene_cn: str                               # 中文场景，用于前端展示
    scene_en: str                               # 英文场景短句，用于实际 Prompt
    size: str                                   # 尺寸常量 KEY（如 SQUARE_800）


@dataclass
class TypeConfig:
    """一个类型（一个类目）的完整配置"""
    type_id: str                                # 唯一ID，如 "hanger"
    type_name: str                              # 展示名，如 "衣架-ABS塑料成人款"
    default_title: str                          # 默认商品标题
    # 白名单（前端下拉来源 + 后端校验）
    titles: List[str] = field(default_factory=list)
    materials: List[str] = field(default_factory=list)
    specs: List[str] = field(default_factory=list)
    colors: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    default_selected_features: List[str] = field(default_factory=list)
    # Prompt 段
    system_extra_prompt: str = ""               # 该类目专属 System 追加段
    main_scenes: Dict[str, SceneConfig] = field(default_factory=dict)     # 5 张
    detail_scenes: Dict[str, SceneConfig] = field(default_factory=dict)   # 10 张
    # 元信息
    created_at: float = 0.0
    updated_at: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "TypeConfig":
        # 对 main_scenes/detail_scenes 反序列化，同时支持 dict 和 SceneConfig 对象
        def _to_scene(v):
            if isinstance(v, SceneConfig):
                return copy.deepcopy(v)
            return SceneConfig(**v)
        main = {k: _to_scene(v) for k, v in (d.get("main_scenes") or {}).items()}
        detail = {k: _to_scene(v) for k, v in (d.get("detail_scenes") or {}).items()}
        d2 = {**d, "main_scenes": main, "detail_scenes": detail}
        return cls(**d2)


# ============================================================
# 默认衣架配置（JSON 不存在时写入）
# ============================================================
def _build_default_hanger() -> TypeConfig:
    # 延迟导入，避免循环依赖；且项目根目录直接作为 PYTHONPATH，用绝对导入
    from config import MAIN_IMAGE_SCENES, DETAIL_IMAGE_SCENES, HangerParams

    def _mk(key: str, cn: str, en: str, size: str) -> SceneConfig:
        return SceneConfig(key=key, scene_cn=cn, scene_en=en, size=size)

    main_scenes: Dict[str, SceneConfig] = {}
    for k, (cn, en) in MAIN_IMAGE_SCENES.items():
        main_scenes[k] = _mk(k, cn, en, "main")
    detail_scenes: Dict[str, SceneConfig] = {}
    for k, (cn, en) in DETAIL_IMAGE_SCENES.items():
        detail_scenes[k] = _mk(k, cn, en, "detail")

    now = time.time()
    return TypeConfig(
        type_id="hanger_default",
        type_name="衣架-ABS塑料成人款（默认）",
        default_title=HangerParams.TITLE_WHITELIST[0],
        titles=list(HangerParams.TITLE_WHITELIST),
        materials=list(HangerParams.MATERIAL_WHITELIST),
        specs=list(HangerParams.SPEC_WHITELIST),
        colors=list(HangerParams.COLOR_WHITELIST),
        features=list(HangerParams.FEATURE_WHITELIST),
        default_selected_features=list(HangerParams.DEFAULT_SELECTED_FEATURES),
        system_extra_prompt=(
            "Emphasize the hanger's load-bearing capacity, material durability, "
            "and wardrobe organizational benefits. Avoid cartoonish, toy-like, "
            "or overly artistic presentations that would not be suitable for "
            "an e-commerce 1688 wholesale product listing."
        ),
        main_scenes=main_scenes,
        detail_scenes=detail_scenes,
        created_at=now,
        updated_at=now,
    )


# ============================================================
# 管理器
# ============================================================
class TypeConfigManager:
    """持久化 JSON 型配置管理器（线程安全）"""

    def __init__(self, json_path: str):
        self.json_path = os.path.abspath(json_path)
        self._lock = threading.RLock()
        self._types: Dict[str, TypeConfig] = {}
        # 首次读取 + 初始化
        self._load_or_init()

    # ---------- 内部 ----------
    def _ensure_file_dir(self) -> None:
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)

    def _load_or_init(self) -> None:
        with self._lock:
            if not os.path.exists(self.json_path):
                self._ensure_file_dir()
                hanger = _build_default_hanger()
                self._types = {hanger.type_id: hanger}
                self._persist()
                return
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                types_list = raw.get("types") or []
                self._types = {
                    t["type_id"]: TypeConfig.from_dict(t) for t in types_list
                }
                if not self._types:
                    # JSON 被清空 → 补默认
                    hanger = _build_default_hanger()
                    self._types = {hanger.type_id: hanger}
                    self._persist()
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                raise RuntimeError(
                    f"type_configs.json 损坏，请检查或删除后重试：{self.json_path}. 错误: {e}"
                ) from e

    def _persist(self) -> None:
        """必须在锁内调用"""
        self._ensure_file_dir()
        data = {"version": 1, "types": [t.to_dict() for t in self._types.values()]}
        tmp = self.json_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.json_path)

    # ---------- 查询 ----------
    def list_all(self) -> List[TypeConfig]:
        with self._lock:
            return [copy.deepcopy(t) for t in self._types.values()]

    def get(self, type_id: str) -> Optional[TypeConfig]:
        with self._lock:
            t = self._types.get(type_id)
            return copy.deepcopy(t) if t else None

    def get_or_raise(self, type_id: str) -> TypeConfig:
        t = self.get(type_id)
        if t is None:
            raise ValueError(f"type_id={type_id!r} 不存在，请先在配置中心创建或选择一个类型")
        return t

    # ---------- 变更 ----------
    def create(self, payload: dict) -> TypeConfig:
        """新建类型；如未传 type_id 则自动生成"""
        with self._lock:
            type_id = (payload.get("type_id") or "").strip()
            if not type_id:
                type_id = f"type_{uuid.uuid4().hex[:8]}"
            if type_id in self._types:
                raise ValueError(f"type_id={type_id!r} 已存在")
            type_name = (payload.get("type_name") or "").strip()
            if not type_name:
                raise ValueError("type_name 不能为空")
            # 默认场景：复制衣架配置的结构，空值让用户自己填
            base = _build_default_hanger()
            now = time.time()
            cfg = TypeConfig(
                type_id=type_id,
                type_name=type_name,
                default_title=(payload.get("default_title") or "").strip(),
                titles=_to_str_list(payload.get("titles")),
                materials=_to_str_list(payload.get("materials")),
                specs=_to_str_list(payload.get("specs")),
                colors=_to_str_list(payload.get("colors")),
                features=_to_str_list(payload.get("features")),
                default_selected_features=_to_str_list(payload.get("default_selected_features")),
                system_extra_prompt=(payload.get("system_extra_prompt") or "").strip(),
                main_scenes=_parse_scenes(payload.get("main_scenes"), base.main_scenes, "main"),
                detail_scenes=_parse_scenes(payload.get("detail_scenes"), base.detail_scenes, "detail"),
                created_at=now,
                updated_at=now,
            )
            self._types[cfg.type_id] = cfg
            self._persist()
            return copy.deepcopy(cfg)

    def update(self, type_id: str, payload: dict) -> TypeConfig:
        with self._lock:
            if type_id not in self._types:
                raise ValueError(f"type_id={type_id!r} 不存在")
            old = self._types[type_id]
            type_name = payload.get("type_name")
            if "type_name" in payload and not (type_name or "").strip():
                raise ValueError("type_name 不能为空")
            now = time.time()
            merged: dict = old.to_dict()
            merged["updated_at"] = now
            for k in [
                "type_name", "default_title",
                "titles", "materials", "specs", "colors", "features",
                "default_selected_features", "system_extra_prompt",
            ]:
                if k in payload and payload[k] is not None:
                    if k in ("type_name", "default_title", "system_extra_prompt"):
                        merged[k] = str(payload[k]).strip()
                    else:
                        merged[k] = _to_str_list(payload[k])
            if "main_scenes" in payload and payload["main_scenes"] is not None:
                merged["main_scenes"] = _parse_scenes(
                    payload["main_scenes"], old.main_scenes, "main"
                )
            if "detail_scenes" in payload and payload["detail_scenes"] is not None:
                merged["detail_scenes"] = _parse_scenes(
                    payload["detail_scenes"], old.detail_scenes, "detail"
                )
            self._types[type_id] = TypeConfig.from_dict(merged)
            self._persist()
            return copy.deepcopy(self._types[type_id])

    def delete(self, type_id: str) -> None:
        with self._lock:
            if type_id not in self._types:
                raise ValueError(f"type_id={type_id!r} 不存在")
            if len(self._types) <= 1:
                raise ValueError("至少保留一个类型，无法删除最后一个")
            del self._types[type_id]
            self._persist()

    def duplicate(self, src_type_id: str, new_type_name: str, new_type_id: Optional[str] = None) -> TypeConfig:
        """复制类型（方便用户基于衣架快速改出手机壳/T恤）"""
        with self._lock:
            src = self.get_or_raise(src_type_id)
            new_tid = (new_type_id or "").strip() or f"{src.type_id}_copy_{uuid.uuid4().hex[:6]}"
            if new_tid in self._types:
                raise ValueError(f"新 type_id={new_tid!r} 已存在")
            new_name = (new_type_name or "").strip()
            if not new_name:
                raise ValueError("新类型名不能为空")
            now = time.time()
            # deepcopy 场景（SceneConfig dataclass 没有 to_dict，直接深拷贝对象）
            main = {k: copy.deepcopy(v) for k, v in src.main_scenes.items()}
            detail = {k: copy.deepcopy(v) for k, v in src.detail_scenes.items()}
            new_cfg = TypeConfig(
                type_id=new_tid,
                type_name=new_name,
                default_title=src.default_title,
                titles=list(src.titles),
                materials=list(src.materials),
                specs=list(src.specs),
                colors=list(src.colors),
                features=list(src.features),
                default_selected_features=list(src.default_selected_features),
                system_extra_prompt=src.system_extra_prompt,
                main_scenes=main,
                detail_scenes=detail,
                created_at=now,
                updated_at=now,
            )
            self._types[new_tid] = new_cfg
            self._persist()
            return copy.deepcopy(new_cfg)

    # ---------- 导入/导出 ----------
    def export_all(self) -> dict:
        with self._lock:
            return {
                "version": 1,
                "exported_at": time.time(),
                "types": [t.to_dict() for t in self._types.values()],
            }

    def import_all(self, data: dict, mode: str = "merge") -> List[TypeConfig]:
        """
        mode:
          - merge: 以 type_id 为 key 合并覆盖
          - replace: 清空后重新写入（至少保留一个类型）
        """
        with self._lock:
            types_raw = data.get("types") or []
            if not isinstance(types_raw, list):
                raise ValueError("导入 JSON 中 types 必须是数组")
            if mode == "replace" and not types_raw:
                raise ValueError("replace 模式下 types 不能为空（至少保留 1 个类型）")
            incoming: Dict[str, TypeConfig] = {}
            for t in types_raw:
                cfg = TypeConfig.from_dict(t)
                if not cfg.type_id or not cfg.type_name:
                    raise ValueError(f"导入项 type_id/type_name 不能为空: {t}")
                if cfg.type_id in incoming:
                    raise ValueError(f"导入数据内 type_id 重复: {cfg.type_id}")
                incoming[cfg.type_id] = cfg
            if mode == "replace":
                self._types = incoming
            else:  # merge
                merged = {**self._types}
                merged.update(incoming)
                self._types = merged
            self._persist()
            return [copy.deepcopy(t) for t in self._types.values()]


# ============================================================
# 辅助
# ============================================================
def _to_str_list(v) -> List[str]:
    if v is None:
        return []
    if isinstance(v, str):
        # 支持用逗号/换行分隔粘贴
        parts = [p.strip() for p in v.replace("\n", ",").split(",") if p.strip()]
        return parts
    return [str(x).strip() for x in list(v) if str(x).strip()]


def _parse_scenes(raw, fallback: Dict[str, SceneConfig], prefix: str) -> Dict[str, SceneConfig]:
    """
    raw 可以是 dict（key -> SceneConfig dict） 或 list
    """
    if raw is None:
        # 没有传 → 保持 fallback（确保有5张主图10张详情）
        return {k: SceneConfig(**v.to_dict()) for k, v in fallback.items()}

    result: Dict[str, SceneConfig] = {}
    if isinstance(raw, dict):
        items = raw.items()
    elif isinstance(raw, list):
        items = [(f"{prefix}_{i+1}", v) for i, v in enumerate(raw)]
    else:
        raise ValueError(f"scenes 必须是 dict 或 list，实际 {type(raw)}")

    for key, v in items:
        if not isinstance(v, dict):
            raise ValueError(f"scene {key!r} 必须是 dict")
        sc = SceneConfig(
            key=str(v.get("key") or key).strip(),
            scene_cn=str(v.get("scene_cn") or "").strip(),
            scene_en=str(v.get("scene_en") or "").strip(),
            size=str(v.get("size") or fallback.get(key).size if fallback.get(key) else "").strip(),
        )
        if not sc.scene_cn or not sc.scene_en:
            raise ValueError(f"scene {key!r} 的 scene_cn / scene_en 不能为空")
        result[sc.key] = sc
    return result


# ============================================================
# 模块级单例
# ============================================================
_DEFAULT_JSON_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "type_configs.json",
)
_type_manager: Optional[TypeConfigManager] = None


def get_type_manager(json_path: Optional[str] = None) -> TypeConfigManager:
    global _type_manager
    if _type_manager is None:
        _type_manager = TypeConfigManager(json_path or _DEFAULT_JSON_PATH)
    return _type_manager
