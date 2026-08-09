"""
image_client.py - 文生图模型调用层（核心新增模块）
------------------------------------------------
- 抽象基类 BaseImageClient：统一入参与出参
- 4个具体实现：
    1) TongyiWanxiangClient   云端-通义万相（推荐电商）
    2) Dalle3Client           云端-DALL·E3
    3) OllamaSDXLClient       本地-Ollama SDXL
    4) OllamaFluxClient       本地-Ollama Flux（本地画质SOTA）
- 开闭原则：新增模型仅新增子类，不修改业务调度代码
- 统一出参：本地图片绝对文件路径
"""
from __future__ import annotations

import abc
import base64
import io
import logging
import os
import time
from typing import Optional, Tuple

import requests
from PIL import Image

from config import (
    IMAGE_SIZE,
    ModelConfig,
    SIZE_TO_STR,
)

logger = logging.getLogger("image_client")

# ---------------------------
# 统一图片尺寸字符串映射（兼容各模型不同格式要求）
# ---------------------------
DALLE3_SIZE_MAP = {
    (800, 800): "1024x1024",    # 正方形映射
    (750, 1000): "1024x1792",   # 竖版映射到 DALL·E3 支持的最近尺寸
}


# ============================================================
# 工具函数
# ============================================================
def _download_image_to_file(url: str, save_path: str, timeout: int = 60) -> str:
    """下载云端图片URL到本地路径，返回本地绝对路径"""
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(resp.content)
    logger.info(f"图片下载完成 → {save_path}")
    return os.path.abspath(save_path)


def _save_base64_image(b64_data: str, save_path: str) -> str:
    """base64 图片数据保存为文件"""
    # 兼容 data:image/png;base64,xxx 前缀
    if "," in b64_data:
        b64_data = b64_data.split(",", 1)[1]
    img_bytes = base64.b64decode(b64_data)
    img = Image.open(io.BytesIO(img_bytes))
    img.save(save_path)
    logger.info(f"本地base64图片保存完成 → {save_path}")
    return os.path.abspath(save_path)


def _resize_if_needed(img_path: str, target_size: Tuple[int, int]) -> str:
    """
    云端/本地模型输出尺寸若不严格匹配800x800/750x1000，则本地resize
    保持主图/详情图严格符合1688规范
    """
    with Image.open(img_path) as im:
        if im.size == target_size:
            return img_path
        resized = im.resize(target_size, Image.LANCZOS)
        resized.save(img_path, quality=95)
        logger.info(f"图片尺寸由 {im.size} 强制 resize → {target_size}")
    return img_path


# ============================================================
# 抽象基类
# ============================================================
class BaseImageClient(abc.ABC):
    """
    文生图客户端抽象基类
    统一接口：generate_image(prompt, size, negative_prompt, model_name) -> str(本地路径)
    """

    def __init__(self, output_dir: str, ref_img_url: Optional[str] = None):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.cfg = ModelConfig()
        self.ref_img_url = ref_img_url  # 参考图 URL（图生图模式）

    # --- 子类必须实现 ---
    @abc.abstractmethod
    def generate_image(
        self,
        prompt: str,
        *,
        size_type: str,          # "main" | "detail"
        negative_prompt: Optional[str] = None,
        file_stem: str,          # 如 main_1 / detail_3
    ) -> str:
        """
        生成图片并落地本地，返回本地绝对路径
        :param prompt: 完整正向Prompt
        :param size_type: main/detail
        :param negative_prompt: 负面提示词
        :param file_stem: 文件名主体（不含后缀）
        :return: 本地图片绝对路径
        """
        raise NotImplementedError

    # --- 公共工具 ---
    def _make_save_path(self, file_stem: str) -> str:
        return os.path.join(self.output_dir, f"{file_stem}.png")


# ============================================================
# 方案A1：通义万相（阿里DashScope）
# ============================================================
class TongyiWanxiangClient(BaseImageClient):
    """通义万相 wanx-v1，电商素材推荐"""

    # wanx-v1 仅支持以下尺寸（宽*高）
    _SUPPORTED_SIZES = ["1024*1024", "720*1280", "1280*720", "768*1152"]

    def __init__(self, output_dir: str, ref_img_url: Optional[str] = None):
        super().__init__(output_dir, ref_img_url=ref_img_url)
        if not self.cfg.DASHSCOPE_API_KEY:
            raise RuntimeError("通义万相未配置密钥，请在.env设置 DASHSCOPE_API_KEY")
        try:
            import dashscope  # noqa: F401
        except ImportError as e:
            raise RuntimeError("未安装 dashscope SDK，请 pip install dashscope") from e

    def _map_size(self, size: Tuple[int, int]) -> str:
        """将业务尺寸映射到 wanx-v1 支持的最接近尺寸"""
        w, h = size
        ratio = w / h
        # wanx-v1 支持尺寸的宽高比
        candidates = [
            ("1024*1024", 1.0),
            ("720*1280", 0.5625),   # 竖图
            ("1280*720", 1.7778),   # 横图
            ("768*1152", 0.6667),   # 竖图
        ]
        # 找宽高比最接近的
        best = min(candidates, key=lambda c: abs(c[1] - ratio))
        return best[0]

    def generate_image(
        self,
        prompt: str,
        *,
        size_type: str,
        negative_prompt: Optional[str] = None,
        file_stem: str,
    ) -> str:
        from dashscope import ImageSynthesis

        size = IMAGE_SIZE[size_type]
        # wanx-v1 不支持 800*800 / 750*1000，映射到最接近的支持尺寸
        size_str = self._map_size(size)

        # 有参考图时用 wanx2.1-t2i-turbo（支持 ref_img），否则用配置的模型
        use_model = self.cfg.TONGYI_MODEL_NAME
        if self.ref_img_url:
            use_model = "wanx2.1-t2i-turbo"
            logger.info(f"[通义万相] 检测到参考图，切换模型: {self.cfg.TONGYI_MODEL_NAME} → {use_model}")

        logger.info(f"[通义万相] 调用模型: {use_model}, size={size_str} (原始 {size[0]}×{size[1]}), ref_img={'有' if self.ref_img_url else '无'}")
        save_path = self._make_save_path(file_stem)

        extra = {}
        if negative_prompt:
            extra["negative_prompt"] = negative_prompt
        # 传参考图 URL 和影响强度
        if self.ref_img_url:
            extra["ref_img"] = self.ref_img_url
            extra["ref_strength"] = 0.5  # 参考图影响强度（0-1，越大越接近参考图）

        actual_key = self.cfg.DASHSCOPE_API_KEY
        logger.info(f"[通义万相] 实际使用 key: 长度={len(actual_key)}, 前10={repr(actual_key[:10])}, 后5={repr(actual_key[-5:])}")

        rsp = ImageSynthesis.call(
            model=use_model,
            prompt=prompt,
            size=size_str,
            n=1,
            api_key=actual_key,
            **extra,
        )

        if rsp.status_code != 200:
            raise RuntimeError(f"通义万相调用失败 code={rsp.status_code}, msg={rsp.message}")

        results = getattr(rsp.output, "results", None) or []
        if not results:
            raise RuntimeError(f"通义万相未返回图片: {rsp.output}")

        image_url = results[0].url
        local_path = _download_image_to_file(image_url, save_path)
        return _resize_if_needed(local_path, size)


# ============================================================
# 方案A2：DALL·E3（OpenAI）
# ============================================================
class Dalle3Client(BaseImageClient):
    """OpenAI DALL·E3，通用能力强"""

    def __init__(self, output_dir: str, ref_img_url: Optional[str] = None):
        super().__init__(output_dir, ref_img_url=ref_img_url)
        if not self.cfg.OPENAI_API_KEY:
            raise RuntimeError("DALL·E3未配置密钥，请在.env设置 OPENAI_API_KEY")
        try:
            import openai  # noqa: F401
        except ImportError as e:
            raise RuntimeError("未安装 openai SDK，请 pip install openai") from e

    def generate_image(
        self,
        prompt: str,
        *,
        size_type: str,
        negative_prompt: Optional[str] = None,
        file_stem: str,
    ) -> str:
        from openai import OpenAI

        target_size = IMAGE_SIZE[size_type]
        dalle_size = DALLE3_SIZE_MAP[target_size]

        logger.info(f"[DALL·E3] 调用模型: {self.cfg.DALLE3_MODEL_NAME}, "
                    f"internal={dalle_size}, quality={self.cfg.DALLE3_QUALITY}")
        save_path = self._make_save_path(file_stem)

        client = OpenAI(
            api_key=self.cfg.OPENAI_API_KEY,
            base_url=self.cfg.OPENAI_BASE_URL,
        )

        final_prompt = prompt
        if negative_prompt:
            # DALL·E3 无原生negative_prompt参数，附加到正向末尾
            final_prompt = f"{prompt}. AVOID: {negative_prompt}"

        resp = client.images.generate(
            model=self.cfg.DALLE3_MODEL_NAME,
            prompt=final_prompt,
            size=dalle_size,
            quality=self.cfg.DALLE3_QUALITY,
            n=1,
            response_format="url",
        )
        if not resp.data:
            raise RuntimeError(f"DALL·E3未返回图片: {resp}")

        image_url = resp.data[0].url
        local_path = _download_image_to_file(image_url, save_path)
        return _resize_if_needed(local_path, target_size)


# ============================================================
# 方案B1：Ollama SDXL 本地
# ============================================================
class OllamaSDXLClient(BaseImageClient):
    """Ollama 本地 stable-diffusion，低成本本地推理"""

    def __init__(self, output_dir: str, ref_img_url: Optional[str] = None):
        super().__init__(output_dir, ref_img_url=ref_img_url)
        self.base_url = self.cfg.OLLAMA_BASE_URL.rstrip("/")
        self._check_service_alive()

    def _check_service_alive(self) -> None:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(
                f"无法连接Ollama服务: {self.base_url}。"
                f"请先执行: ollama serve，并 ollama pull {self.cfg.OLLAMA_SDXL_MODEL}"
            ) from e

    def generate_image(
        self,
        prompt: str,
        *,
        size_type: str,
        negative_prompt: Optional[str] = None,
        file_stem: str,
    ) -> str:
        target_size = IMAGE_SIZE[size_type]
        model = self.cfg.OLLAMA_SDXL_MODEL

        logger.info(f"[Ollama SDXL] 调用模型: {model}, target_size={target_size}")
        save_path = self._make_save_path(file_stem)

        # Ollama 图像生成模型统一走 /api/generate，stream=false
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if negative_prompt:
            # 部分ollama sd模型支持 negative_prompt 在 options
            payload["options"] = {"negative_prompt": negative_prompt}

        resp = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.cfg.OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        images = data.get("images", []) or []
        if not images:
            raise RuntimeError(f"Ollama SDXL未返回图像数据: {data}")

        local_path = _save_base64_image(images[0], save_path)
        return _resize_if_needed(local_path, target_size)


# ============================================================
# 方案B2：Ollama Flux 本地（开源画质SOTA）
# ============================================================
class OllamaFluxClient(BaseImageClient):
    """Ollama 本地 Flux，目前本地开源生图SOTA"""

    def __init__(self, output_dir: str, ref_img_url: Optional[str] = None):
        super().__init__(output_dir, ref_img_url=ref_img_url)
        self.base_url = self.cfg.OLLAMA_BASE_URL.rstrip("/")
        self._check_service_alive()

    def _check_service_alive(self) -> None:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
        except Exception as e:
            raise RuntimeError(
                f"无法连接Ollama服务: {self.base_url}。"
                f"请先执行: ollama serve，并 ollama pull {self.cfg.OLLAMA_FLUX_MODEL}"
            ) from e

    def generate_image(
        self,
        prompt: str,
        *,
        size_type: str,
        negative_prompt: Optional[str] = None,
        file_stem: str,
    ) -> str:
        target_size = IMAGE_SIZE[size_type]
        model = self.cfg.OLLAMA_FLUX_MODEL

        logger.info(f"[Ollama Flux] 调用模型: {model}, target_size={target_size}")
        start_ts = time.time()
        save_path = self._make_save_path(file_stem)

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if negative_prompt:
            payload["options"] = {"negative_prompt": negative_prompt}

        resp = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.cfg.OLLAMA_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        images = data.get("images", []) or []
        if not images:
            raise RuntimeError(f"Ollama Flux未返回图像数据: {data}")

        elapsed = time.time() - start_ts
        logger.info(f"[Ollama Flux] 推理耗时: {elapsed:.1f}s")

        local_path = _save_base64_image(images[0], save_path)
        return _resize_if_needed(local_path, target_size)


# ============================================================
# 工厂函数：根据模型枚举 → 具体客户端实例（业务层唯一入口）
# ============================================================
def create_image_client(model_enum, output_dir: str, ref_img_url: Optional[str] = None) -> BaseImageClient:
    """
    模型客户端工厂（切换模型仅改config或--model参数，业务代码零改动）
    """
    from config import ImageModel

    mapping = {
        ImageModel.TONGYI_WANXIANG: TongyiWanxiangClient,
        ImageModel.DALLE3: Dalle3Client,
        ImageModel.OLLAMA_SDXL: OllamaSDXLClient,
        ImageModel.OLLAMA_FLUX: OllamaFluxClient,
    }
    if model_enum not in mapping:
        raise ValueError(f"未支持的模型: {model_enum}, 可用: {list(mapping.keys())}")
    return mapping[model_enum](output_dir, ref_img_url=ref_img_url)
