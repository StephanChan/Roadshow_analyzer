# -*- coding: utf-8 -*-
"""
目录扫描模块：识别输入目录下的项目子文件夹（含音频/文稿/图片）
对应原 JS 版 roadshow_analyzer/scanner.js
"""
from dataclasses import dataclass
from pathlib import Path

import config


@dataclass
class Project:
    """一个项目子文件夹"""
    name: str                      # 文件夹名
    dir: Path                      # 文件夹路径
    audio_files: list              # 音频文件名列表
    photo_files: list              # 图片文件名列表
    doc_files: list                # 文稿文件名列表
    has_content: bool              # 是否有音频或文稿（用于区分仅图片模式）
    done: bool = False             # 是否已处理过（存在完成标记）


def _is_excluded_dir(name: str) -> bool:
    """排除隐藏目录、平台目录、输出目录"""
    if name.startswith("."):
        return True
    for key in config.EXCLUDED_DIR_KEYS:
        if key in name:
            return True
    return False


def scan_projects(input_dir: Path | str) -> list:
    """
    识别输入目录下所有"项目子文件夹"（包含音频/文稿/图片）
    返回按中文排序的 Project 列表
    """
    input_dir = Path(input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"输入目录不存在: {input_dir}")

    projects = []
    for entry in input_dir.iterdir():
        if not entry.is_dir():
            continue
        if _is_excluded_dir(entry.name):
            continue

        # 收集该子文件夹内的 音频/图片/文稿 文件名
        audio_files = [
            f.name for f in entry.iterdir()
            if f.is_file() and f.suffix.lower() in config.AUDIO_EXTS
        ]
        photo_files = [
            f.name for f in entry.iterdir()
            if f.is_file() and f.suffix.lower() in config.PHOTO_EXTS
        ]
        doc_files = [
            f.name for f in entry.iterdir()
            if f.is_file() and f.suffix.lower() in config.DOC_EXTS
        ]

        # 三个都没有则不是项目文件夹
        if not (audio_files or photo_files or doc_files):
            continue

        projects.append(Project(
            name=entry.name,
            dir=entry,
            audio_files=sorted(audio_files),
            photo_files=sorted(photo_files),
            doc_files=sorted(doc_files),
            has_content=bool(audio_files) or bool(doc_files),
            done=(entry / config.DONE_MARKER).exists(),
        ))

    # 按名称排序（用 Unicode 排序即可近似 JS 的 localeCompare('zh-CN')）
    projects.sort(key=lambda p: p.name)
    return projects


def ensure_dirs() -> None:
    """确保输出目录与缓存目录存在"""
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    # 简单自测
    projs = scan_projects(config.INPUT_DIR)
    print(f"找到 {len(projs)} 个项目文件夹:")
    for p in projs:
        print(f"  - {p.name} 音频:{len(p.audio_files)} 图片:{len(p.photo_files)} 文稿:{len(p.doc_files)}")