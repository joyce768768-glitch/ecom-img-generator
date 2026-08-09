"""
config.py - 全局常量配置层
---------------------------------
- 硬编码单一类目：衣架
- 15套图模板（5主图 + 10详情图）
- 模型枚举、尺寸常量、参数白名单校验
- 切换模型/类目仅修改本文件与.env，不改动业务代码
"""
from __future__ import annotations

import os
from enum import Enum
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

from dotenv import load_dotenv

# ---------------------------
# 0. 环境变量加载
# ---------------------------
load_dotenv()


# ---------------------------
# 1. 模型枚举（开闭原则：新增模型仅在此加枚举 + image_client加子类）
# ---------------------------
class ImageModel(str, Enum):
    """文生图模型枚举，统一配置入口"""
    # 云端方案
    TONGYI_WANXIANG = "tongyi_wanxiang"      # 阿里通义万相（推荐电商）
    DALLE3 = "dalle3"                        # OpenAI DALL·E3
    # 本地方案
    OLLAMA_SDXL = "ollama_sdxl"              # Ollama SDXL
    OLLAMA_FLUX = "ollama_flux"              # Ollama Flux（推荐本地画质）

    @classmethod
    def is_cloud(cls, model: "ImageModel") -> bool:
        return model in (cls.TONGYI_WANXIANG, cls.DALLE3)

    @classmethod
    def is_local(cls, model: "ImageModel") -> bool:
        return model in (cls.OLLAMA_SDXL, cls.OLLAMA_FLUX)


# ---------------------------
# 2. 1688平台尺寸规范
# ---------------------------
IMAGE_SIZE: Dict[str, Tuple[int, int]] = {
    "main": (800, 800),      # 主图 800×800
    "detail": (750, 1000),   # 详情图 750×1000
}
SIZE_TO_STR = {
    (800, 800): "800*800",
    (750, 1000): "750*1000",
}


# ---------------------------
# 3. 硬编码单一类目：衣架  —— 所有字段白名单，杜绝AI编造
# ---------------------------
class HangerParams:
    """衣架类目参数白名单 —— 任何超出此范围的参数将被拒绝"""

    CATEGORY = "家居百货 > 收纳整理 > 衣架/裤架/领带架 > 衣架"

    TITLE_WHITELIST: List[str] = [
        "防滑无痕衣架家用挂衣架子衣柜挂衣批发",
        "不锈钢衣架子加粗加厚成人防滑晾晒衣架",
        "植绒衣架家用无痕防肩角衣柜收纳整理",
        "实木衣架服装店酒店木质挂衣架批发",
        "塑料衣架成人儿童两用防滑晾晒衣挂",
    ]

    MATERIAL_WHITELIST: List[str] = [
        "ABS塑料", "PP塑料", "不锈钢", "实木榉木",
        "实木荷木", "竹制", "植绒", "硅胶防滑",
    ]

    SPEC_WHITELIST: List[str] = [
        "成人款 40cm", "成人款 42cm", "儿童款 30cm",
        "加粗款 1.2cm管径", "常规款 0.8cm管径",
    ]

    COLOR_WHITELIST: List[str] = [
        "象牙白", "典雅黑", "原木色", "樱花粉",
        "薄荷绿", "深空灰", "香槟金",
    ]

    FEATURE_WHITELIST: List[str] = [
        "防滑设计", "无痕防肩角", "晾晒防风挂钩",
        "360度旋转挂钩", "叠挂省空间", "干湿两用",
    ]

    DEFAULT_SELECTED_FEATURES: List[str] = [
        "防滑设计", "无痕防肩角", "360度旋转挂钩",
    ]


# ---------------------------
# 4. 默认商品数据（模拟1688商家上架表单输入）
# ---------------------------
@dataclass
class ProductInfo:
    """
    商品参数。
    - type_id：必填，指定所属配置类型（配置中心创建）
    - 其他参数会基于该类型的白名单做校验
    """
    type_id: str
    title: str
    material: str
    spec: str
    color: str
    features: Tuple[str, ...] = field(default_factory=tuple)


# ---------------------------
# 5. 5套主图模板 + 10套详情图模块模板（单图专属场景短句）
# 【保留】作为 type_configs.json 不存在时初始化默认衣架配置的基准值
# 实际业务校验/Prompt生成走 TypeConfigManager
# ---------------------------
MAIN_IMAGE_SCENES: Dict[str, Tuple[str, str]] = {
    # 主图1：白底正面全景（搜索主图，点击率核心）
    "main_1": ("白底正面全景", "White background studio shot, single hanger front view full shot, centered composition, clean 1688 e-commerce style"),
    # 主图2：使用场景-衣柜挂衣（场景代入）
    "main_2": ("使用场景-衣柜挂衣", "Modern wardrobe interior scene, hangers with clothes hanging neatly, warm home lifestyle atmosphere"),
    # 主图3：细节特写-防滑肩部（卖点1）
    "main_3": ("细节特写-防滑肩部", "Close-up macro shot of hanger shoulder anti-slip texture, highlight non-slip rubber material details"),
    # 主图4：细节特写-旋转挂钩（卖点2）
    "main_4": ("细节特写-旋转挂钩", "Close-up of 360-degree rotating hook, metal hook + plastic connector detail display"),
    # 主图5：多色多规格组合展示（sku一览）
    "main_5": ("多色多规格组合", "Multiple hangers in different colors arranged neatly on white background, color variation display grid"),
}

DETAIL_IMAGE_SCENES: Dict[str, Tuple[str, str]] = {
    # 详情图1：首屏主KV + 核心卖点清单
    "detail_1": ("首屏KV·三卖点", "Hero banner layout, hanger product main visual with 3 core selling points icons around, premium e-commerce detail page header"),
    # 详情图2：材质解析展示
    "detail_2": ("材质解析", "Material anatomy infographic style, label callouts pointing to ABS plastic body, anti-slip rubber, metal hook parts"),
    # 详情图3：尺寸规格图
    "detail_3": ("尺寸规格图", "Product dimension diagram, hanger silhouette with size markups 40cm width x 22cm height, technical drawing style"),
    # 详情图4：承重测试展示
    "detail_4": ("承重测试", "Load-bearing test scene, hanger hanging heavy winter coat to show strength, stress test visual"),
    # 详情图5：防滑效果对比
    "detail_5": ("防滑效果对比", "Side-by-side comparison, left non-slip hanger holds clothes firmly vs right regular hanger slipping off"),
    # 详情图6：衣柜收纳场景
    "detail_6": ("衣柜收纳场景", "Neat organized closet scene, multiple hangers stacked space-saving, tidy wardrobe interior"),
    # 详情图7：干湿两用场景
    "detail_7": ("干湿两用场景", "Split scene composition, left dry clothes hanging indoor, right wet laundry outdoor drying"),
    # 详情图8：颜色/款式全览
    "detail_8": ("颜色款式全览", "Color swatch palette display, all 7 colors of hangers arranged with color name labels"),
    # 详情图9：适用人群/场景矩阵
    "detail_9": ("人群场景矩阵", "Icon grid matrix, scenarios: home/laundry/dorm/clothing store, user groups: adult/children/shop owner"),
    # 详情图10：包装与批发说明
    "detail_10": ("批发包装说明", "Wholesale bulk packaging display, 10pcs/20pcs/50pcs pack options stacked with price tag style labels"),
}


# ---------------------------
# 6. 通用负面提示词（见下方 7.3 电商专用负面词，已替换为更精准版本）
# ---------------------------


# ---------------------------
# 7. System全局固定Prompt（所有图共用，约束1688 B端批发写实画风）
# ---------------------------
SYSTEM_PROMPT_BASE = (
    "1688 B2B wholesale e-commerce product photography style, "
    "ultra realistic photo, 8K high resolution, professional studio lighting, "
    "crisp sharp focus, accurate product color reproduction, "
    "clean composition suitable for Chinese e-commerce platform, "
    "commercial photography grade, no artistic filters, "
    "product centered, highlight material texture and craftsmanship details"
)

# ---------------------------
# 7.1 主图专属System（5张主图800×800，纯白底·产品居中·无模特）
# ---------------------------
SYSTEM_PROMPT_MAIN = (
    "[MAIN IMAGE RULES] 1688 main image specification: "
    "product centered occupying 70-85% of frame, pure white background (#FFFFFF), "
    "no shadows, no reflections, no floor, single angle front or 45-degree view, "
    "absolutely no human body, no model, no mannequin, no hands, "
    "no text overlay, no watermark, no logo, no price tag, "
    "single product only, no duplicates, no collage, no split view"
)

# ---------------------------
# 7.2 详情图专属System（10张详情图750×1000，允许场景化·细节展示·KV构图）
# ---------------------------
SYSTEM_PROMPT_DETAIL = (
    "[DETAIL IMAGE RULES] 1688 detail image specification: "
    "scene-styled background allowed (gradient, lifestyle context, material closeup), "
    "can show structural details, texture zoom-in, functional demonstration, "
    "visual hierarchy with KV-style composition for first-screen scenes, "
    "props allowed but product must remain the visual focus, "
    "no human body, no model, no text overlay, no watermark, "
    "single product focus, no collage"
)

# ---------------------------
# 7.3 电商专用负面词（替换通用负面词，更精准）
# ---------------------------
NEGATIVE_PROMPT = (
    "low quality, blurry, distorted, deformed, ugly, bad anatomy, "
    "text overlay, watermark, logo, brand name, price tag, QR code, barcode, "
    "human body, human face, model, mannequin, hand, skin, fingers, "
    "multiple objects, duplicate, collage, split view, grid layout, "
    "cartoon, anime, illustration, painting, 3d render, CGI, "
    "chinese characters, gibberish text, typography, frame, border"
)


# ---------------------------
# 8. 输出目录配置
# ---------------------------
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------
# 9. 各模型专属配置（从.env读取，密钥永不硬编码）
# ---------------------------
@dataclass
class ModelConfig:
    """模型专属配置聚合

    注意：字段默认值在类定义时求值，进程启动后 os.environ 的变化不会反映到新实例。
    因此用 __post_init__ 在每次实例化时从最新 os.environ 读取，确保 .env 热更新生效。
    """
    # 通义万相
    DASHSCOPE_API_KEY: str = ""
    TONGYI_MODEL_NAME: str = "wanx-v1"
    TONGYI_BASE_URL: str = "https://dashscope.aliyuncs.com"

    # DALL·E3
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DALLE3_MODEL_NAME: str = "dall-e-3"
    DALLE3_QUALITY: str = "hd"

    # Ollama 本地
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_SDXL_MODEL: str = "stable-diffusion"
    OLLAMA_FLUX_MODEL: str = "flux"
    OLLAMA_TIMEOUT: int = 300

    # 全局默认模型
    DEFAULT_MODEL: ImageModel = ImageModel.OLLAMA_SDXL

    def __post_init__(self) -> None:
        """每次实例化时从最新 os.environ 读取，让 .env 热更新生效"""
        # 先尝试从 .env 文件加载（如果 python-dotenv 可用）
        try:
            from dotenv import load_dotenv
            load_dotenv(override=True)
        except ImportError:
            pass

        self.DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
        self.TONGYI_MODEL_NAME = os.getenv("TONGYI_MODEL_NAME", "wanx-v1")
        self.TONGYI_BASE_URL = os.getenv("TONGYI_BASE_URL", "https://dashscope.aliyuncs.com")
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
        self.OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.DALLE3_MODEL_NAME = os.getenv("DALLE3_MODEL_NAME", "dall-e-3")
        self.DALLE3_QUALITY = os.getenv("DALLE3_QUALITY", "hd")
        self.OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.OLLAMA_SDXL_MODEL = os.getenv("OLLAMA_SDXL_MODEL", "stable-diffusion")
        self.OLLAMA_FLUX_MODEL = os.getenv("OLLAMA_FLUX_MODEL", "flux")
        try:
            self.OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "300"))
        except ValueError:
            self.OLLAMA_TIMEOUT = 300
        try:
            self.DEFAULT_MODEL = ImageModel(os.getenv("DEFAULT_IMAGE_MODEL", ImageModel.OLLAMA_SDXL))
        except ValueError:
            self.DEFAULT_MODEL = ImageModel.OLLAMA_SDXL


# ---------------------------
# 10. 参数白名单校验工具（基于 type_id 动态取白名单）
# ---------------------------
def validate_product_params(product: ProductInfo) -> None:
    """
    严格校验：
    1. type_id 必填，且在类型配置中存在
    2. 每个商品参数在该 type_id 对应的白名单内
    """
    from type_configs import get_type_manager  # 延迟导入，避免循环
    if not getattr(product, "type_id", None):
        raise ValueError(
            "商品参数校验失败：未指定 type_id。"
            "请先在配置中心创建/选择一个类型（如衣架-ABS成人款）。"
        )
    type_cfg = get_type_manager().get(product.type_id)
    if type_cfg is None:
        raise ValueError(
            f"商品参数校验失败：type_id={product.type_id!r} 在 type_configs.json 中不存在。"
        )

    errors: List[str] = []
    # 空值视为"不设置"，跳过白名单校验（允许留空）
    if product.title and type_cfg.titles and product.title not in type_cfg.titles:
        errors.append(f"标题不在「{type_cfg.type_name}」白名单内: {product.title}")
    if product.material and type_cfg.materials and product.material not in type_cfg.materials:
        errors.append(f"材质不在「{type_cfg.type_name}」白名单内: {product.material}")
    if product.spec and type_cfg.specs and product.spec not in type_cfg.specs:
        errors.append(f"规格不在「{type_cfg.type_name}」白名单内: {product.spec}")
    if product.color and type_cfg.colors and product.color not in type_cfg.colors:
        errors.append(f"颜色不在「{type_cfg.type_name}」白名单内: {product.color}")
    if type_cfg.features:
        for f in product.features:
            if f not in type_cfg.features:
                errors.append(f"功能特点不在「{type_cfg.type_name}」白名单内: {f}")
    if errors:
        raise ValueError(
            f"商品参数校验失败（禁止编造参数 / 请先到配置中心将值加入白名单）:\n"
            + "\n".join(f"- {e}" for e in errors)
        )
