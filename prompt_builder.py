"""
prompt_builder.py - Prompt分层组装工具
----------------------------------------
五层拼接架构：
  完整正向Prompt = ① System全局约束
                 + ①.5 类目专属 System Extra 段（配置中心可改）
                 + ② 商品公共变量
                 + ③ 单图专属场景短句（该类型下配置的15条，配置中心可改）
  单独负面Prompt = ④ 通用负面提示词（作为独立参数传给模型客户端）

所有变量基于 type_id 动态从 TypeConfigManager 读取（不再硬编码）。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Tuple

from config import (
    NEGATIVE_PROMPT,
    ProductInfo,
    SYSTEM_PROMPT_BASE,
    SYSTEM_PROMPT_MAIN,
    SYSTEM_PROMPT_DETAIL,
)
from type_configs import TypeConfig, get_type_manager
from translator import translate_scene_cn_to_en

logger = logging.getLogger("prompt_builder")


# ============================================================
# 组装结果数据类
# ============================================================
@dataclass(frozen=True)
class BuiltPrompt:
    """组装完成的完整绘图Prompt对"""
    positive: str          # 完整正向Prompt
    negative: str          # 完整负面Prompt
    scene_key: str         # 如 main_1 / detail_3
    size_type: str         # main / detail
    size_key: str          # 如 SQUARE_800
    scene_cn: str          # 中文场景（日志用）


# ============================================================
# Prompt分层组装器
# ============================================================
class PromptBuilder:
    """
    五层Prompt分层组装：
      ①   System全局固定（画风/画质/尺寸风格约束）
      ①.5 类目专属 System Extra（配置中心可改，如衣架强调承重）
      ②   商品公共变量（标题/材质/规格/颜色/卖点 - 全局复用一次）
      ③   单图专属场景短句（该类型下的5主图+10详情图各自独立，配置中心可改）
      ④   通用负面Prompt（单独字段）
    """

    def __init__(self, product: ProductInfo, extra_negative: str = "", original_image: str = ""):
        if not product.type_id:
            raise ValueError(
                "PromptBuilder 初始化失败：ProductInfo.type_id 为空。"
                "请先选择一个类型。"
            )
        self.product = product
        self.type_cfg: TypeConfig = get_type_manager().get_or_raise(product.type_id)
        self._original_image = original_image or ""

        # ①.5 类目专属 System 追加段
        self._system_extra: str = (self.type_cfg.system_extra_prompt or "").strip()

        # ② 商品公共变量提前生成（所有图复用，避免重复计算）
        self._product_common_block = self._build_product_common_block()

        # ④ 负面：通用 + 外部追加（如模型配置弹窗的负面词）
        self._negative_base = NEGATIVE_PROMPT
        self._extra_negative = (extra_negative or "").strip()

        logger.info(
            "PromptBuilder 初始化完成：type=%s, main=%d, detail=%d, system_extra=%s, original_image=%s",
            self.type_cfg.type_name,
            len(self.type_cfg.main_scenes),
            len(self.type_cfg.detail_scenes),
            "有" if self._system_extra else "无",
            "有" if self._original_image else "无",
        )

    # --------------------
    # ② 公共商品变量块（标题/材质/规格/颜色/卖点 - 英文生成模型友好格式）
    # --------------------
    def _build_product_common_block(self) -> str:
        feat_raw = list(self.product.features or [])
        feat_str = ", ".join(feat_raw) if feat_raw else "(none)"
        lines = [
            f"Product category type: {self.type_cfg.type_name}",
            f"Product title (subject): {self.product.title or '(not specified)'}",
            f"Material: {self.product.material or '(not specified)'}",
            f"Specification: {self.product.spec or '(not specified)'}",
            f"Main color: {self.product.color or '(not specified)'}",
            f"Key features: {feat_str}",
        ]
        return "; ".join(lines)

    # --------------------
    # 完整 System 段（基础 + 类目追加）
    # --------------------
    def _build_full_system_block(self) -> str:
        if self._system_extra:
            return f"{SYSTEM_PROMPT_BASE}. Category-specific notes: {self._system_extra}"
        return SYSTEM_PROMPT_BASE

    # --------------------
    # 完整 负面 段（通用 + 用户追加）
    # --------------------
    def _build_full_negative(self) -> str:
        if self._extra_negative:
            return f"{NEGATIVE_PROMPT}, {self._extra_negative}"
        return NEGATIVE_PROMPT

    # --------------------
    # 单张图完整Prompt组装
    # --------------------
    def _build_single(
        self,
        scene_key: str,
        size_type: str,
    ) -> BuiltPrompt:
        """
        :param scene_key: main_1 / detail_1 等
        :param size_type: main / detail
        """
        # 从类型配置里取场景
        pool = self.type_cfg.main_scenes if size_type == "main" else self.type_cfg.detail_scenes
        if scene_key not in pool:
            raise ValueError(
                f"类型「{self.type_cfg.type_name}」缺少场景 {scene_key!r}。"
                f"请在配置中心补全 5 主图 / 10 详情图模板。"
            )
        scene_cfg = pool[scene_key]

        # 自动翻译：scene_en 为空时从 scene_cn 翻译
        scene_en = scene_cfg.scene_en
        if not scene_en and scene_cfg.scene_cn:
            scene_en = translate_scene_cn_to_en(scene_cfg.scene_cn)

        # 完整正向 = ① System全局 + ①.5 类目追加 + ①.6 主图/详情图专属规则 + ② 公共变量 + ②.5 参考图说明 + ③ 单图场景
        # 主图用 SYSTEM_PROMPT_MAIN，详情图用 SYSTEM_PROMPT_DETAIL，差异化风格约束
        scene_specific_system = SYSTEM_PROMPT_MAIN if size_type == "main" else SYSTEM_PROMPT_DETAIL
        positive_parts = [
            f"[SYSTEM] {self._build_full_system_block()} {scene_specific_system}",
            f"[PRODUCT] {self._product_common_block}",
        ]
        # ②.5 参考图说明（如果有上传原始图）
        # 走 wanx2.1-imageedit 图像编辑模式：prompt 是对参考图的"编辑指令"，
        # 不是"从零生成"。所以这里要明确：产品主体保持不变，[SCENE] 只作用于背景/环境。
        if self._original_image:
            positive_parts.append(
                f"[REFERENCE] The base image is the uploaded original product photo. "
                f"Keep the product itself completely unchanged: identical shape, color, texture and proportions. "
                f"Treat the following [SCENE] as an edit instruction applied to the background/environment only. "
                f"The product must remain the central subject, occupying 70-85% of the frame."
            )
        positive_parts.append(f"[SCENE] {scene_en}")
        positive = " ".join(positive_parts)

        # ④ 负面Prompt
        negative = self._build_full_negative()

        return BuiltPrompt(
            positive=positive,
            negative=negative,
            scene_key=scene_key,
            size_type=size_type,
            size_key=scene_cfg.size,
            scene_cn=scene_cfg.scene_cn,
        )

    # --------------------
    # 批量生成 5张主图 + 10张详情图 = 15张完整Prompt
    # --------------------
    def build_all(self) -> Tuple[BuiltPrompt, ...]:
        """返回15个BuiltPrompt，顺序：先main_1..5 再 detail_1..10。
        如果某类型下实际数量不足/多于 5/10，按类型配置的实际存在的 key 生成。
        """
        results = []
        # 主图：按 main_1~main_N 的顺序取
        main_keys = sorted(
            [k for k in self.type_cfg.main_scenes.keys() if k.startswith("main_")],
            key=lambda x: (0, int(x.split("_", 1)[1])) if x.split("_", 1)[1].isdigit() else (1, x),
        )
        for key in main_keys:
            results.append(self._build_single(key, "main"))

        # 详情图：按 detail_1~detail_N 的顺序取
        detail_keys = sorted(
            [k for k in self.type_cfg.detail_scenes.keys() if k.startswith("detail_")],
            key=lambda x: (0, int(x.split("_", 1)[1])) if x.split("_", 1)[1].isdigit() else (1, x),
        )
        for key in detail_keys:
            results.append(self._build_single(key, "detail"))
        return tuple(results)

    # --------------------
    # 调试/日志辅助：输出可读分层
    # --------------------
    @staticmethod
    def format_for_log(p: BuiltPrompt) -> str:
        return (
            f"\n========== [{p.scene_key} | {p.scene_cn} | size_type={p.size_type} | size_key={p.size_key}] ==========\n"
            f"[POSITIVE]\n{p.positive}\n"
            f"[NEGATIVE]\n{p.negative}\n"
            f"========================================================\n"
        )
