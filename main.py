# -*- coding: utf-8 -*-
"""
路演分析平台 Python 版 - 主入口
对应原 JS 版 roadshow_analyzer/run.js

在 Spyder 中直接运行（F5），或命令行执行：
    python main.py "D:\\某目录"     # 指定输入目录

输出：输入目录/analysis_output/目录.html（总览目录页）+ 各项目报告HTML
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

    # ---- 生成总览目录页（文件名：目录.html） ----
    index_html = build_index_html(results)
    index_path = config.OUTPUT_DIR / "目录.html"
    index_path.write_text(index_html, encoding="utf-8")
    print(f"\n✅ 全部完成！目录页已生成: {index_path}")


if __name__ == "__main__":
    main()