# -*- coding: utf-8 -*-
"""
单项目处理管线：转录 → AI纠错 → 图片分析 → 风格分析 → 商业化点评 → HTML生成
对应原 JS 版 roadshow_analyzer/pipeline.js

新增特性：
- AI 纠错后的全文会立刻保存在项目子文件夹内（{项目名}_全文.txt）
- 下次处理时若检测到该文件，直接读取并跳过音频转写与 AI 纠错
"""
import json
from pathlib import Path
from urllib.parse import quote

import config
from analyzer import (academic_review, ai_fix, analyze_ppt_style,
                      analyze_speech_style, commercial_review, split_qa)
from html_reporter import generate_project_html
from photo_analyzer import analyze_image
from photo_ordering import order_photos_by_text
from transcriber import transcribe_audio


# ---------------------------------------------------------------------------
# 读取文稿文件内容（.txt/.md 直接读取，.doc/.docx 不支持时给出警告）
# ---------------------------------------------------------------------------
def read_doc_file(doc_path: Path | str) -> str:
    doc_path = Path(doc_path)
    ext = doc_path.suffix.lower()
    if ext in (".txt", ".md"):
        return doc_path.read_text(encoding="utf-8", errors="replace")
    # .doc/.docx 是二进制，暂不支持直接读取
    print(f"  [警告] 不支持直接读取 {ext} 文稿，请先转为 .txt/.md")
    return ""


# ---------------------------------------------------------------------------
# 转录文稿的保存与查找（{项目名}_全文.txt）
# ---------------------------------------------------------------------------
def _transcript_path(proj) -> Path:
    """AI 纠错后全文的保存路径（项目子文件夹内）"""
    return proj.dir / f"{proj.name}{config.TRANSCRIPT_SUFFIX}.txt"


def _find_existing_transcript(proj):
    """
    查找项目子文件夹内已存在的转录文稿：
    优先精确匹配 {项目名}_全文.txt；找不到时也匹配任意 *_全文.txt
    返回文件路径；不存在返回 None
    """
    # 精确匹配
    exact = _transcript_path(proj)
    if exact.exists() and exact.is_file():
        return exact

    # 模糊匹配：文件夹内任何以 "_全文.txt" 结尾的文件
    if proj.dir.is_dir():
        for f in proj.dir.iterdir():
            if f.is_file() and f.name.endswith(f"{config.TRANSCRIPT_SUFFIX}.txt"):
                return f
    return None


def _save_transcript(proj, text: str) -> bool:
    """将 AI 纠错后的全文立即保存到项目子文件夹内"""
    if not text or not text.strip():
        return False
    try:
        out = _transcript_path(proj)
        out.write_text(text.strip(), encoding="utf-8")
        print(f"  [保存文稿] → {out.name}")
        return True
    except Exception as e:
        print(f"  [警告] 文稿保存失败: {e}")
        return False


# ---------------------------------------------------------------------------
# 处理单个项目：完整管线（支持 音频/文稿/仅图片 三种模式）
# ---------------------------------------------------------------------------
def process_project(proj) -> dict | None:
    """
    处理一个项目文件夹。
    返回结果 dict 供总览使用；转录失败时返回 None（与 JS 版一致）。
    """
    print(f"\n===== 开始处理: {proj.name} =====")

    # ---- 内容获取：已有_全文 → 音频转写 → 读取文稿 → 仅图片 ----
    content_text = None
    chunks = []
    transcript_loaded = False  # 是否复用已有的 _全文 文稿

    # 文稿类型识别（文件名约定，零配置）：
    # - doc_loaded_name : 实际加载的文稿文件名（用于判断是否 AI 总结稿）
    doc_loaded_name = ""
    # - is_ai_summary : True = AI 总结稿（跳过 AI 纠错，标题用"AI总结"）
    is_ai_summary = False

    # 优先检查：该文件夹是否已有保存的转录文稿（跳过转写与AI纠错）
    existing = _find_existing_transcript(proj)
    if existing:
        doc = read_doc_file(existing)
        if doc:
            content_text = doc
            transcript_loaded = True
            doc_loaded_name = existing.name
            print(f"  [来源] 复用已有文稿 {existing.name} ({len(doc)}字，跳过转写与纠错)")

    # 模式1：有音频 → 转写
    if content_text is None and proj.audio_files:
        audio_path = proj.dir / proj.audio_files[0]
        try:
            transcript = transcribe_audio(audio_path)
            content_text = transcript["text"]
            chunks = transcript["chunks"]
        except Exception as e:
            print(f"  [转录失败] {e}")
            return None
        doc_loaded_name = proj.audio_files[0]
        print(f"  [来源] 音频转写 ({len(content_text)}字)")

    # 模式2：无音频但有文稿 → 读取文稿
    if content_text is None and proj.doc_files:
        doc_path = proj.dir / proj.doc_files[0]
        doc = read_doc_file(doc_path)
        if doc:
            content_text = doc
            doc_loaded_name = proj.doc_files[0]
            print(f"  [来源] 读取文稿 {proj.doc_files[0]} ({len(doc)}字)")
        else:
            print("  [警告] 文稿读取为空/不支持格式，按仅图片处理")

    # 根据文件名判断是否为 AI 总结稿（文件名含"总结"/"summary"）
    if doc_loaded_name:
        lower = doc_loaded_name.lower()
        is_ai_summary = any(k.lower() in lower for k in config.AI_SUMMARY_KEYS)

    # 根据项目文件夹名判断是否为学术报告
    is_academic = any(k in proj.name for k in config.ACADEMIC_REPORT_KEYS)

    # 模式3：无内容 → 仅图片
    if content_text is None:
        print("  [警告] 该文件夹无音频也无文稿，仅处理图片，跳过AI纠错/点评")

    has_text = bool(content_text)

    # ---- 图片分析（三种模式都执行） ----
    photos = []
    total_photos = len(proj.photo_files)
    for i, pf in enumerate(proj.photo_files):
        img_path = proj.dir / pf
        analysis = analyze_image(img_path, proj.name, i, total_photos)
        photos.append({
            **analysis,
            "file": pf,
            "src": f"../{quote(proj.name)}/{quote(pf)}",
        })
        print(f"  [图片{i + 1}/{total_photos}] {analysis.get('theme') or '?'}")

    # ---- 有文字的后续处理 ----
    pitch, qa, fixed_text = "", "", ""
    speech_style = {}
    ppt_style = {"slideCount": len(photos), "structure": {}, "pageTypes": {}, "dataDensity": 0}
    review = None

    if has_text:
        if transcript_loaded or is_ai_summary:
            # 已有纠错后的全文，或 AI 总结稿：直接使用，不再重复 AI 纠错
            fixed_text = content_text
            if is_ai_summary:
                print(f"  [AI总结稿] 文稿已是整理后的总结，跳过 AI 纠错")
        else:
            # 新转录/新文稿：执行 AI 纠错
            fixed_text = content_text
            try:
                fixed_text = ai_fix(proj.name, content_text)
            except Exception as e:
                print(f"  [AI纠错失败，用原始] {e}")

            # AI 纠错完成后立即保存全文（不再等全部项目处理完）
            _save_transcript(proj, fixed_text)

        # 拆路演/问答
        sp = split_qa(fixed_text)
        pitch = sp["pitch"]
        qa = sp["qa"]

        # 风格分析
        speech_style = analyze_speech_style(fixed_text, chunks)
        ppt_style = analyze_ppt_style(photos)

        # 点评：学术报告 → 学术质量评审；路演报告 → 商业化五维点评
        try:
            if is_academic:
                print(f"  [点评] 学术报告 → 学术质量评审")
                review = academic_review(proj.name, fixed_text, [p.get("theme") for p in photos])
            else:
                print(f"  [点评] 路演报告 → 商业化五维分析")
                review = commercial_review(proj.name, fixed_text, [p.get("theme") for p in photos])
        except Exception as e:
            print(f"  [AI点评失败] {e}")
    else:
        # 仅图片：最小规模 PPT 风格分析
        ppt_style = {"slideCount": len(photos), "structure": {}, "pageTypes": {}, "dataDensity": 0}

    # ---- 生成 HTML 报告 ----
    # 重排照片顺序（新策略：倒计时 > 文件名自动升降序 > 讲稿匹配兜底）
    # 无论是否有文字都执行排序（仅图片模式同样需要按路演顺序展示）
    display_photos = photos
    try:
        display_photos = order_photos_by_text(photos, pitch, chunks)
        note = ""
        if display_photos and display_photos[0].get("order_note"):
            note = display_photos[0]["order_note"]
        print(f"  [排序] 已重排 {len(display_photos)} 张图片（{note or '顺序'})")
    except Exception as e:
        print(f"  [警告] 图片排序失败，保持文件顺序: {e}")
        display_photos = photos

    html = generate_project_html(proj.name, {
        "text": pitch,
        "qa": qa,
        "photos": display_photos,
        "speechStyle": speech_style,
        "pptStyle": ppt_style,
        "review": review,
        "hasText": has_text,
        "isAiSummary": is_ai_summary,
        "isAcademic": is_academic,
    })
    # 注：HTML 文件名使用项目中文原名（不用 urlencode）。
    # 若用百分号编码名保存，浏览器打开 index.html 时会自动解码链接中的 %XX，
    # 去请求中文名文件，而磁盘上却是编码字面量名，导致跳转 404。
    out_file = config.OUTPUT_DIR / (proj.name + ".html")
    out_file.write_text(html, encoding="utf-8")
    print(f"  [完成] → {out_file.name} ({'含文字分析' if content_text else '仅图片'})")

    # ---- 保存中间结果（便于 Spyder 检查与排错） ----
    _save_intermediate(proj, {
        "text": fixed_text,
        "pitch": pitch,
        "qa": qa,
        "chunks": chunks,
        "photos": photos,
        "speechStyle": speech_style,
        "pptStyle": ppt_style,
        "review": review,
        "hasText": has_text,
        "transcriptLoaded": transcript_loaded,
    })

    return {
        "name": proj.name,
        "review": review,
        "speechStyle": speech_style,
        "pptStyle": ppt_style,
        "photoCount": len(photos),
        "hasText": has_text,
    }


def _save_intermediate(proj, data: dict) -> None:
    """将单项目中间结果保存为 JSON（analysis_output/cache/项目名.json）"""
    try:
        cache_dir = config.OUTPUT_DIR / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        out = cache_dir / f"{proj.name}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"  [警告] 中间结果保存失败: {e}")


if __name__ == "__main__":
    from scanner import scan_projects
    # 简单自测：处理输入目录下第一个项目（仅测试扫描，不自动运行全管线）
    projs = scan_projects(config.INPUT_DIR)
    print(f"扫描到 {len(projs)} 个项目。要执行完整处理，请运行 main.py")