"""
main.py - 1688电商主图/详情图 批量生成主程序（调度层·类型可配置版）
------------------------------------------------------------------
- 入口：python main.py --type <type_id> [--model xxx] [--only main_1,main_2] [--list-types]
- 四层解耦协调：config ↔ prompt_builder ↔ image_client ← storage(output/)
- 强制参数：--type 必须指定（请先到配置中心/前端新增类型）
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from typing import List, Optional

# ---------------------------
# 日志初始化（控制台 + 文件双输出）
# ---------------------------
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")

# ---------------------------
# 本项目模块导入（四层解耦）
# ---------------------------
from config import (  # noqa: E402
    ImageModel,
    ModelConfig,
    OUTPUT_DIR,
    ProductInfo,
    validate_product_params,
)
from prompt_builder import PromptBuilder, BuiltPrompt  # noqa: E402
from image_client import create_image_client  # noqa: E402
from type_configs import TypeConfig, get_type_manager  # noqa: E402


# ============================================================
# CLI 参数解析
# ============================================================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="1688电商主图/详情图批量生成Agent（类型可配置版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  python main.py --list-types                              # 列出所有已配置的类型\n"
            "  python main.py --type hanger_default                    # 用.env默认模型生成该类型全部场景\n"
            "  python main.py --type hanger_default --model tongyi_wanxiang\n"
            "  python main.py --type phone_case   --only main_1,main_2  # 仅生成2张主图测试\n"
            "  python main.py --type phone_case   --dry-run             # 仅打印15条Prompt（调参用）\n"
        ),
    )
    model_choices = [m.value for m in ImageModel]

    parser.add_argument(
        "--type",
        dest="type_id",
        type=str,
        default=None,
        help="【必填】类型ID。先到前端「配置中心」创建，或用 --list-types 查询可用 ID",
    )
    parser.add_argument(
        "--model",
        choices=model_choices,
        default=None,
        help=f"指定图像模型，覆盖.env DEFAULT_IMAGE_MODEL。可选: {model_choices}",
    )
    parser.add_argument(
        "--only",
        type=str,
        default=None,
        help="仅生成指定的图，英文逗号分隔；如 main_1,detail_3,detail_10；默认该类型下全部",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help=f"指定图片输出目录，默认 {OUTPUT_DIR}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印完整Prompt不调用文生图API（用于调参/验证）",
    )
    parser.add_argument(
        "--list-types",
        action="store_true",
        help="列出所有已配置的类型（id / 名称 / 场景数）后退出",
    )
    parser.add_argument(
        "--list",
        dest="list_scenes",
        action="store_true",
        help="需要和 --type 一起使用：列出该类型所有场景key后退出",
    )
    return parser.parse_args()


# ============================================================
# 业务辅助
# ============================================================
def resolve_model(args_model: Optional[str]) -> ImageModel:
    cfg = ModelConfig()
    if args_model:
        model = ImageModel(args_model)
        logger.info(f"[CLI] 使用指定模型: {model.value}")
    else:
        model = cfg.DEFAULT_MODEL
        logger.info(f"[ENV] 使用默认模型: {model.value}")
    return model


def build_product_from_type(t: TypeConfig) -> ProductInfo:
    """从类型配置取默认值（第1条白名单值）构造 ProductInfo"""
    if not t.titles:
        raise ValueError(f"类型「{t.type_name}」缺少 titles 白名单，请先配置")
    if not t.materials:
        raise ValueError(f"类型「{t.type_name}」缺少 materials 白名单，请先配置")
    if not t.specs:
        raise ValueError(f"类型「{t.type_name}」缺少 specs 白名单，请先配置")
    if not t.colors:
        raise ValueError(f"类型「{t.type_name}」缺少 colors 白名单，请先配置")
    features = tuple(t.default_selected_features) if t.default_selected_features else tuple()
    return ProductInfo(
        type_id=t.type_id,
        title=t.default_title or t.titles[0],
        material=t.materials[0],
        spec=t.specs[0],
        color=t.colors[0],
        features=features,
    )


def filter_prompts(all_prompts: List[BuiltPrompt], only_str: Optional[str]) -> List[BuiltPrompt]:
    if not only_str:
        return all_prompts
    only_keys = {k.strip() for k in only_str.split(",") if k.strip()}
    filtered = [p for p in all_prompts if p.scene_key in only_keys]
    missing = only_keys - {p.scene_key for p in filtered}
    if missing:
        logger.warning(f"以下 --only 中的 key 不存在，已忽略: {sorted(missing)}")
    if not filtered:
        raise ValueError(f"--only 过滤后无有效任务，请检查: {only_str}")
    logger.info(f"--only 模式，共 {len(filtered)} 张: {[p.scene_key for p in filtered]}")
    return filtered


# ============================================================
# 业务主流程
# ============================================================
def run_batch(
    model_enum: ImageModel,
    prompts: List[BuiltPrompt],
    output_dir: str,
    dry_run: bool,
) -> List[str]:
    os.makedirs(output_dir, exist_ok=True)

    # 1) 实例化模型客户端
    client = None
    if not dry_run:
        logger.info("=" * 60)
        logger.info(
            f"初始化图像模型客户端: {model_enum.value} "
            f"({'云端' if ImageModel.is_cloud(model_enum) else '本地Ollama'})"
        )
        logger.info("=" * 60)
        client = create_image_client(model_enum, output_dir)

    generated: List[str] = []
    total = len(prompts)
    start_all = time.time()

    for idx, p in enumerate(prompts, 1):
        log_str = PromptBuilder.format_for_log(p)
        logger.info(log_str)

        scene_start = time.time()
        save_path = os.path.abspath(os.path.join(output_dir, f"{p.scene_key}.png"))

        if dry_run:
            logger.info(f"[DRY-RUN {idx}/{total}] 跳过模型调用 → {save_path}")
            generated.append(save_path)
            continue

        try:
            logger.info(
                f"[生成中 {idx}/{total}] scene={p.scene_key}({p.scene_cn}), "
                f"size_type={p.size_type}, model={model_enum.value}"
            )
            real_path = client.generate_image(
                prompt=p.positive,
                size_type=p.size_type,
                negative_prompt=p.negative,
                file_stem=p.scene_key,
            )
            elapsed = time.time() - scene_start
            logger.info(
                f"[完成 {idx}/{total}] {p.scene_key} 耗时 {elapsed:.1f}s → {real_path}"
            )
            generated.append(real_path)
        except Exception as e:
            logger.error(
                f"[失败 {idx}/{total}] {p.scene_key} 生成异常: {type(e).__name__}: {e}"
            )
            continue

    total_elapsed = time.time() - start_all
    ok = sum(1 for p in generated if dry_run or os.path.exists(p))
    logger.info("=" * 60)
    logger.info(f"全部任务结束: 成功 {ok}/{total} 张，总耗时 {total_elapsed:.1f}s")
    logger.info(f"输出目录: {os.path.abspath(output_dir)}")
    logger.info("=" * 60)
    return generated


# ============================================================
# 列表功能
# ============================================================
def list_all_types() -> None:
    tm = get_type_manager()
    all_t = tm.list_all()
    print()
    print("=" * 80)
    print(f"已配置类型（共 {len(all_t)} 个，使用 --type <ID> 选择）：")
    print("=" * 80)
    if not all_t:
        print("  （空）请先通过前端配置中心 / API 创建类型")
        return
    for t in all_t:
        print(
            f"  ID: {t.type_id:<22} | 名称: {t.type_name:<26} "
            f"| 主图场景={len(t.main_scenes):>2} 详情场景={len(t.detail_scenes):>2}"
        )
    print()
    print("示例：python main.py --type " + (all_t[0].type_id if all_t else "hanger_default"))
    print()


def list_scenes_for_type(t: TypeConfig) -> None:
    print()
    print(f"类型「{t.type_name}」({t.type_id}) 可用场景Key：")
    main_keys = [s.key for s in sorted(
        t.main_scenes.values(),
        key=lambda s: int(s.key.split("_")[-1]) if s.key.split("_")[-1].isdigit() else 999,
    )]
    detail_keys = [s.key for s in sorted(
        t.detail_scenes.values(),
        key=lambda s: int(s.key.split("_")[-1]) if s.key.split("_")[-1].isdigit() else 999,
    )]
    print(f"  【主图 {len(main_keys)} 张】: {'  '.join(main_keys)}")
    print(f"  【详情图 {len(detail_keys)} 张】: {'  '.join(detail_keys)}")
    print(f"\n示例 --only {main_keys[0]},{detail_keys[0]},{detail_keys[-1]}")
    print()


# ============================================================
# 入口
# ============================================================
def main() -> int:
    args = parse_args()
    tm = get_type_manager()

    # --list-types 快速查询（不要求选类型）
    if args.list_types:
        list_all_types()
        return 0

    # 以下所有命令都强制要求 --type（用户决策4：无类型不执行）
    if not args.type_id:
        print(
            "\n❌ 错误：必须通过 --type <TYPE_ID> 指定类型。\n"
            "   · 先使用  python main.py --list-types  查看可用类型\n"
            "   · 或打开前端  http://127.0.0.1:5173/#/admin  「配置中心」新增类型\n"
        )
        return 2

    type_cfg = tm.get(args.type_id)
    if type_cfg is None:
        print(
            f"\n❌ 错误：type_id={args.type_id!r} 不存在。\n"
            f"   · 请用  python main.py --list-types  确认可用 ID\n"
            f"   · 或去「配置中心」新增类型\n"
        )
        return 2

    # --list 列出该类型的场景
    if args.list_scenes:
        list_scenes_for_type(type_cfg)
        return 0

    # 1) 用类型默认值构造 ProductInfo + 白名单校验
    try:
        product = build_product_from_type(type_cfg)
        validate_product_params(product)
    except ValueError as e:
        logger.error(str(e))
        return 2
    logger.info(
        f"商品参数白名单校验通过 ✓  类型={type_cfg.type_name}  "
        f"标题={product.title[:20]}...  材质={product.material}  "
        f"规格={product.spec}  颜色={product.color}  "
        f"卖点={list(product.features)}"
    )

    # 2) 解析生成范围
    output_dir = args.output_dir or OUTPUT_DIR
    model_enum = resolve_model(args.model)

    # 3) 构建该类型下的全部 Prompt
    builder = PromptBuilder(product)
    all_prompts = list(builder.build_all())
    logger.info(
        f"已构建 Prompt 总数: {len(all_prompts)} 条 "
        f"(system_extra={'有' if builder._system_extra else '无'})"
    )
    run_prompts = filter_prompts(all_prompts, args.only)

    # 4) 批量生成
    generated = run_batch(
        model_enum=model_enum,
        prompts=run_prompts,
        output_dir=output_dir,
        dry_run=args.dry_run,
    )

    # 5) 最终落盘清单
    if generated:
        logger.info("生成清单：")
        for path in generated:
            flag = "✓" if args.dry_run or os.path.exists(path) else "✗"
            logger.info(f"  {flag} {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
