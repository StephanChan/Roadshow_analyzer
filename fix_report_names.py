# -*- coding: utf-8 -*-
"""
一次性修复脚本：把 analysis_output 下百分号编码的 HTML 文件名改回中文原名。

背景：旧版 pipeline.py 用 urlencode 保存报告（如 AI%E5%99%A8%E8%8A%AF%E7%89%87.html），
浏览器打开 index.html 时会自动把 %XX 解码成中文名，而磁盘上是编码字面量名，
导致总览链接跳转失败。本脚本把所有这些文件批量重命名为中文原名。

用法：
    python fix_report_names.py "D:\\某目录\\analysis_output"
    # 不传参数则默认扫描当前目录下的 analysis_output
"""
import sys
from pathlib import Path
from urllib.parse import unquote


def main() -> None:
    force = "--force" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if args:
        out_dir = Path(args[0])
    else:
        out_dir = Path.cwd() / "analysis_output"

    if not out_dir.is_dir():
        print(f"目录不存在: {out_dir}")
        sys.exit(1)

    renamed = 0
    skipped = 0

    for f in sorted(out_dir.iterdir()):
        if not f.is_file() or f.suffix.lower() != ".html":
            continue
        name = f.name

        # 只处理含百分号编码的文件名
        if "%" not in name:
            continue

        # 解码 %XX → 中文（url 编码）
        decoded = unquote(name)
        if decoded == name:
            continue

        target = out_dir / decoded

        # 目标已存在：不同内容则备份
        if target.exists():
            if target.stat().st_size != f.stat().st_size or force:
                backup = out_dir / (target.stem + ".old.html")
                print(f"  [冲突] {target.name} 已存在，原文件备份为 {backup.name}")
                try:
                    target.rename(backup)
                except OSError:
                    print(f"  [跳过] {target.name} 备份失败")
                    skipped += 1
                    continue
            else:
                # 内容大小相同，直接删掉旧的编码文件
                f.unlink()
                print(f"  [去重] 删除旧编码文件 {name}（内容与 {decoded} 一致）")
                skipped += 1
                continue

        try:
            f.rename(target)
            print(f"  [重命名] {name} → {decoded}")
            renamed += 1
        except OSError as e:
            print(f"  [失败] {name}: {e}")
            skipped += 1

    print(f"\n完成：重命名 {renamed} 个，跳过/失败 {skipped} 个。")
    if renamed:
        print("请重新打开 index.html 进行验证。")


if __name__ == "__main__":
    main()