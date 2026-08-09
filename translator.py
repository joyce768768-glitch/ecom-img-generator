"""
translator.py - 中文 → 英文 翻译服务
------------------------------------
- 基于 Ollama 本地 LLM（gemma3 推荐）
- 用于配置中心 scene_cn → scene_en 自动翻译
- 用于 System 段中文 Prompt → 英文
- 内存字典缓存，避免重复翻译
- 失败降级：返回原文 + 日志告警
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from typing import Dict, List, Optional

import requests

logger = logging.getLogger("translator")

DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.getenv("TRANSLATE_MODEL", "gemma3")
DEFAULT_TIMEOUT = int(os.getenv("TRANSLATE_TIMEOUT", "60"))

TRANSLATE_SYSTEM_PROMPT = (
    "You are a translator that converts Chinese e-commerce product scene descriptions "
    "into short English image-generation prompts.\n\n"
    "STRICT RULES:\n"
    "- Output ONLY the English translation. Nothing else.\n"
    "- No explanation, no quotation marks, no bullet points, no alternatives.\n"
    "- Keep it under 20 words.\n"
    "- Use photography terms: studio shot, close-up, white background, product photography.\n"
    "- Preserve the visual intent of the Chinese original.\n\n"
    "Input will be Chinese. Output must be English only."
)

TRANSLATE_USER_TEMPLATE = "Translate this Chinese product scene description to English for image generation:\n{text}"


class Translator:
    """Ollama 本地翻译服务（线程安全 + 内存缓存）"""

    def __init__(
        self,
        ollama_url: str = DEFAULT_OLLAMA_URL,
        model: str = DEFAULT_MODEL,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._cache: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._available: Optional[bool] = None
        self._available_cache_until: float = 0

    def is_available(self) -> bool:
        """检查 Ollama 翻译模型是否可用（带缓存 30s）"""
        now = time.time()
        if self._available is not None and now < self._available_cache_until:
            return self._available
        try:
            resp = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            models = [m["name"] for m in resp.json().get("models", [])]
            base = self.model.split(":")[0]
            self._available = any(base in m for m in models)
        except Exception:
            self._available = False
        self._available_cache_until = now + 30
        return self._available

    def translate(self, zh_text: str) -> str:
        """中文 → 英文，带缓存"""
        text = zh_text.strip()
        if not text:
            return ""

        with self._lock:
            if text in self._cache:
                return self._cache[text]

        result = self._do_translate(text)

        with self._lock:
            self._cache[text] = result
        return result

    def translate_batch(self, items: Dict[str, str]) -> Dict[str, str]:
        """批量翻译，items={key: 中文文本} → {key: 英文翻译}"""
        result = {}
        for key, zh in items.items():
            result[key] = self.translate(zh)
        return result

    def _do_translate(self, text: str) -> str:
        """实际调用 Ollama /api/chat 翻译"""
        if not self.is_available():
            logger.warning("Ollama 翻译模型不可用，返回原文")
            return text

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": TRANSLATE_SYSTEM_PROMPT},
                        {"role": "user", "content": TRANSLATE_USER_TEMPLATE.format(text=text)},
                    ],
                    "stream": False,
                    "keep_alive": "30m",
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9,
                    },
                },
                timeout=self.timeout,
            )
            data = resp.json()
            message_content = data.get("message", {}).get("content", "").strip()
            result = self._clean_result(message_content)
            if not result:
                logger.warning("翻译返回空结果，返回原文")
                return text
            logger.debug("翻译成功: %r → %r", text, result)
            return result
        except requests.Timeout:
            logger.warning("翻译超时，返回原文: %r", text)
            return text
        except requests.ConnectionError:
            logger.warning("Ollama 连接失败，返回原文: %r", text)
            return text
        except Exception as e:
            logger.error("翻译异常: %s, 返回原文: %r", e, text)
            return text

    @staticmethod
    def _clean_result(text: str) -> str:
        """清理翻译结果中的多余内容"""
        text = text.strip().strip('"').strip("'")
        prefixes = [
            "English:", "Translation:", "English translation:",
            "翻译:", "译文:",
        ]
        for p in prefixes:
            if text.lower().startswith(p.lower()):
                text = text[len(p):].strip()
        text = re.sub(r'\n{2,}', '\n', text)
        if '\n' in text and len(text) > 60:
            text = text.split('\n')[0].strip()
        return text.strip()


# 模块级单例
_translator: Optional[Translator] = None


def get_translator() -> Translator:
    """获取全局翻译器实例"""
    global _translator
    if _translator is None:
        _translator = Translator()
    return _translator


def translate_zh_to_en(text: str) -> str:
    """便捷函数：中文 → 英文"""
    return get_translator().translate(text)


def translate_scene_cn_to_en(scene_cn: str, fallback_en: str = "") -> str:
    """
    翻译场景描述。
    如果 scene_cn 不含中文或翻译失败，返回 fallback_en 或原文。
    """
    if not scene_cn or not scene_cn.strip():
        return fallback_en

    has_chinese = re.search(r'[\u4e00-\u9fff]', scene_cn)
    if not has_chinese:
        return scene_cn

    translated = translate_zh_to_en(scene_cn)
    if translated == scene_cn:
        return fallback_en if fallback_en else scene_cn
    return translated


def auto_translate_scenes(
    scenes: Dict[str, Dict],
    keys: Optional[List[str]] = None,
) -> Dict[str, Dict]:
    """
    批量翻译场景：将 scene_en 为空的项自动从 scene_cn 翻译。
    scenes: {key: {"scene_cn": ..., "scene_en": ..., "size": ...}}
    返回新的 dict（不修改原 dict）。
    """
    result = {}
    for key, val in scenes.items():
        new_val = dict(val)
        scene_en = (new_val.get("scene_en") or "").strip()
        scene_cn = (new_val.get("scene_cn") or "").strip()

        if not scene_en and scene_cn:
            new_val["scene_en"] = translate_scene_cn_to_en(scene_cn)
        elif scene_en:
            new_val["scene_en"] = scene_en
        else:
            new_val["scene_en"] = scene_cn

        result[key] = new_val
    return result
