"""<脚本名>：<一句话功能说明>

用法：
    python template_script.py --input <输入路径> --output <输出目录> [--overwrite]

退出码：0 成功；2 参数或输入错误；1 运行失败。
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def setup_logging(log_file: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
        format="%(asctime)s %(levelname)s %(message)s",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="输入文件或目录")
    parser.add_argument("--output", type=Path, required=True, help="输出目录（必须显式指定）")
    parser.add_argument("--overwrite", action="store_true", help="允许覆盖已存在的输出")
    parser.add_argument("--log-file", type=Path, default=None, help="日志文件路径，默认 <output>/run.log")
    return parser.parse_args(argv)


def run(input_path: Path, output_dir: Path, overwrite: bool) -> int:
    """主体逻辑：同输入重复执行结果一致（幂等）。"""
    if not input_path.exists():
        LOGGER.error("输入不存在: %s", input_path)
        return 2
    # TODO 业务逻辑：流式处理、逐条留痕、敏感值脱敏、临时文件 try/finally 清理
    LOGGER.info("处理完成：输入 %s -> 输出 %s", input_path, output_dir)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)
    setup_logging(args.log_file or (args.output / "run.log"))
    try:
        return run(args.input, args.output, args.overwrite)
    except Exception:  # noqa: BLE001 —— 脚本形态下兜底记录并给非零退出码
        LOGGER.exception("运行失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
