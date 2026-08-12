# -*- coding: utf-8 -*-
"""
路演分析平台 Python 版 - 主入口
对应原 JS 版 roadshow_analyzer/run.js

在 Spyder 中直接运行（F5），或命令行执行：
    python main.py "D:\\某目录"     # 指定输入目录

输出：输入目录/analysis_output/1目录.html（总览目录页）+ 各项目报告HTML
"""
import argparse
import sys
from pathlib import Path

# 确保模块间 import 正常（main.py 在 roadshow_analyzer_py/ 下运行时）
if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from index_builder import build_index_html
from pipeline import process_project
from scanner import ensure_dirs, scan_projects


# ---------------------------------------------------------------------------
# 环境自检：确保关键依赖可用（避免在错误的 Python 环境运行）
# ---------------------------------------------------------------------------
def _check_dependencies() -> None:
    """
    启动时检查运行环境是否完整：
    1. pytesseract（OCR 必需）
    2. Tesseract OCR 软件本体
    若缺失则打印醒目中文提示，退出前告知用户应激活的正确环境。
    """
    missing = []

    # 1. pytesseract Python 包
    try:
        import pytesseract  # noqa: F401
    except ImportError:
        missing.append("pytesseract（Python 包）")

    # 2. Tesseract OCR 软件本体
    if "pytesseract" not in missing:
        try:
            import pytesseract
            pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
            pytesseract.get_tesseract_version()
        except Exception:
            missing.append("Tesseract OCR 软件（tesseract.exe）")

    if missing:
        print("\n" + "=" * 60)
        print("❌ 环境自检未通过！缺少以下组件：")
        for m in missing:
            print(f"   - {m}")
        print("=" * 60)
        print("\n当前运行的 Python 是:")
        print(f"  {sys.executable}")
        print("\n最常见原因是【没有激活项目专用的 conda 环境】。")
        print("正确做法：")
        print("  1. 打开【Anaconda Prompt】")
        print("  2. 先激活环境:  conda activate roadshow_analyzer")
        print("     （注意：提示符应从 (base) 变成 (roadshow_analyzer)）")
        print(f"  3. 再运行:      python \"{Path(__file__).resolve()}\" \"D:\\要分析的文件夹\"")
        print("\n如果已经激活环境仍缺依赖，执行修复命令：")
        print("  conda activate roadshow_analyzer")
        print("  pip install pytesseract==0.3.10 pillow==10.3.0")
        print("  （并确认已安装 Tesseract OCR 软件：https://github.com/UB-Mannheim/tesseract/wiki）")
        print("=" * 60 + "\n")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="路演学习分析平台（Python版）")
    parser.add_argument("input_dir", nargs="?", default=None,
                        help="输入目录（含各项目子文件夹）。缺省为 config.INPUT_DIR")
    args = parser.parse_args()

    # ---- 解析输入目录并重设输出目录（与 JS 版一致：输出在输入目录下） ----
    if args.input_dir:
        config.INPUT_DIR = Path(args.input_dir).resolve()
        if not config.INPUT_DIR.exists():
            print(f"错误: 输入目录不存在: {config.INPUT_DIR}")
            sys.exit(1)
    config.OUTPUT_DIR = config.INPUT_DIR / "analysis_output"

    # 环境自检（必须有 pytesseract 才能识别图片）
    _check_dependencies()

    ensure_dirs()
    print("===== 路演学习分析平台（Python版） =====")
    print("输入目录:", config.INPUT_DIR)
    print("输出目录:", config.OUTPUT_DIR)

    # ---- 扫描项目 ----
    projects = scan_projects(config.INPUT_DIR)
    print(f"找到 {len(projects)} 个项目文件夹\n")

    # ---- 逐项目处理 ----
    results = []
    for proj in projects:
        try:
            r = process_project(proj)
            results.append(r)
        except Exception as e:
            print(f"[项目失败] {proj.name}: {e}")
            results.append(None)

    # ---- 生成总览目录页（文件名：1目录.html） ----
    index_html = build_index_html(results)
    index_path = config.OUTPUT_DIR / "1目录.html"
    index_path.write_text(index_html, encoding="utf-8")
    print(f"\n✅ 全部完成！目录页已生成: {index_path}")


if __name__ == "__main__":
    main()