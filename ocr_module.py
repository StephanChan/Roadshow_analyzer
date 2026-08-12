# -*- coding: utf-8 -*-
"""
OCR 模块：pytesseract 本地识别图片文字（中文简体）
对应原 JS 版 roadshow_analyzer/photo_analyzer.js 中的 OCRImage

Windows 中文路径问题（重要）：
tesseract.exe 底层（C++ std::filesystem）在 Windows 上遇到含中文/非 ASCII 的路径
会报:  exception: filesystem error: Cannot convert character sequence: Illegal byte sequence

规避策略（所有路径均为纯英文）：
1. 图片路径      → 复制到系统临时目录（%TEMP%\\roadshow_ocr\\）再识别
2. 语言包路径    → 把 chi_sim.traineddata 复制到 %TEMP%\\roadshow_tessdata\\，
                   并通过 TESSDATA_PREFIX 环境变量指向该英文目录
                   注意：不要用 --tessdata-dir "带引号路径" 参数（引号会被 tesseract
                   当作路径的一部分，导致 Error opening data file）。只用环境变量。
"""
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path

import config


# ---------------------------------------------------------------------------
# 语言包查找与复制（一次性）
# ---------------------------------------------------------------------------
_tessdata_dir_cache = None  # 成功时缓存目录路径；失败时缓存 None


def _find_traineddata_source() -> Path | None:
    """在多个可能位置查找 chi_sim.traineddata，返回源文件路径；找不到返回 None"""
    candidates = []

    # 1. config.TESSDATA_PREFIX（默认当前工作目录）
    if config.TESSDATA_PREFIX:
        candidates.append(Path(config.TESSDATA_PREFIX) / "chi_sim.traineddata")
    # 2. 当前工作目录
    candidates.append(Path.cwd() / "chi_sim.traineddata")
    # 3. 项目上级目录（26年医企创业比赛 下自带 chi_sim.traineddata）
    candidates.append(Path(__file__).resolve().parent.parent / "chi_sim.traineddata")
    # 4. tesseract 安装目录自带的 tessdata（若用户安装时勾选了中文语言包）
    candidates.append(Path(config.TESSERACT_CMD).parent / "tessdata" / "chi_sim.traineddata")
    candidates.append(Path("C:/Program Files/Tesseract-OCR/tessdata/chi_sim.traineddata"))

    for c in candidates:
        # 去重（不同候选可能指向同一文件）
        if c is not None and c.exists() and c.is_file():
            return c
    return None


def _prepare_tessdata() -> str | None:
    """
    将 chi_sim.traineddata 复制到 %TEMP%\\roadshow_tessdata（纯 ASCII 路径）。
    返回该 tessdata 目录路径（字符串）；无法准备时返回 None。
    """
    global _tessdata_dir_cache
    if _tessdata_dir_cache is not None:
        return _tessdata_dir_cache

    target_dir = Path(tempfile.gettempdir()) / "roadshow_tessdata"
    target_dir.mkdir(parents=True, exist_ok=True)
    dst = target_dir / "chi_sim.traineddata"

    # 目标已存在（之前复制过）→ 直接使用
    if dst.exists() and dst.is_file():
        _tessdata_dir_cache = str(target_dir)
        return _tessdata_dir_cache

    src = _find_traineddata_source()
    if src is None:
        print("  [警告] 未找到 chi_sim.traineddata 语言包！")
        print("        请在下列位置之一放置 chi_sim.traineddata：")
        print(f"          - {Path.cwd()}")
        print(f"          - {Path(__file__).resolve().parent.parent}")
        print(f"          - {Path(config.TESSERACT_CMD).parent / 'tessdata'}")
        print("        或安装 Tesseract 时勾选 Chinese (Simplified) 语言包。")
        _tessdata_dir_cache = None
        return None

    try:
        shutil.copy2(src, dst)
        print(f"  [OCR] 语言包已就绪: {dst}")
    except Exception as e:
        print(f"  [警告] 语言包复制失败: {e}")
        _tessdata_dir_cache = None
        return None

    _tessdata_dir_cache = str(target_dir)
    return _tessdata_dir_cache


# ---------------------------------------------------------------------------
# pytesseract 配置（懒加载）
# ---------------------------------------------------------------------------
def _get_tesseract():
    """返回配置好的 pytesseract 模块（自动设置 tesseract_cmd）"""
    try:
        import pytesseract
    except ImportError:
        raise RuntimeError(
            "缺少 pytesseract 依赖，请先执行: pip install pytesseract"
        )
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    return pytesseract


# 脏字正则：仅保留包含中英文/数字的行
_KEEP_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]")


def _to_ascii_temp_path(img_path: Path) -> Path:
    """将图片复制到纯英文临时路径（规避中文路径 Illegal byte sequence）"""
    tmp_dir = Path(tempfile.gettempdir()) / "roadshow_ocr"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    ext = img_path.suffix.lower() or ".jpg"
    tmp_file = tmp_dir / f"img_{uuid.uuid4().hex[:12]}{ext}"
    shutil.copy2(img_path, tmp_file)
    return tmp_file


def ocr_image(img_path: Path | str) -> str:
    """
    识别单张图片，返回清理后的 OCR 文本（单行 ' | ' 连接，截断 300 字）
    识别失败时返回空字符串（与 JS 版 catch 返回 '' 一致）
    """
    img_path = Path(img_path)
    tmp_img = None
    try:
        pytesseract = _get_tesseract()

        # 准备纯英文 tessdata 目录（语言包）
        tessdata_dir = _prepare_tessdata()
        if tessdata_dir:
            os.environ["TESSDATA_PREFIX"] = tessdata_dir
            # 注意：不传 --tessdata-dir "path"（引号会被 tesseract 当作路径一部分）
        else:
            # 无语言包则回退 tesseract 自带 tessdata 目录试试
            os.environ.pop("TESSDATA_PREFIX", None)

        # 规避图片中文路径：复制到纯英文临时路径
        tmp_img = _to_ascii_temp_path(img_path)

        raw = pytesseract.image_to_string(str(tmp_img), lang="chi_sim")

        lines = [
            ln.strip()
            for ln in raw.split("\n")
            if ln.strip() and len(ln.strip()) > 1 and _KEEP_RE.search(ln)
        ]
        return " | ".join(lines)[:300]
    except Exception as e:
        print(f"    [OCR失败] {img_path.name}: {e}")
        return ""
    finally:
        # 清理临时图片
        if tmp_img is not None:
            try:
                tmp_img.unlink(missing_ok=True)
            except OSError:
                pass


if __name__ == "__main__":
    # 简单自测: python ocr_module.py <图片路径>
    import sys
    if len(sys.argv) > 1:
        text = ocr_image(sys.argv[1])
        print(f"OCR 结果:\n{text}")