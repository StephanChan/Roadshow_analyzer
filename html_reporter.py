# -*- coding: utf-8 -*-
"""
HTML 报告生成模块：单项目学习报告
对应原 JS 版 roadshow_analyzer/pipeline.js 中的 esc / fmtDur / paragraphs / generateProjectHtml
"""
import re


# ---------------------------------------------------------------------------
# HTML 转义
# ---------------------------------------------------------------------------
def esc(s) -> str:
    """HTML 转义（使用 chr(38) 构造 & 符号，与 JS 版 String.fromCharCode(38) 一致）"""
    amp = chr(38)  # &
    return (
        str(s or "")
        .replace(amp, amp + "amp;")
        .replace("<", amp + "lt;")
        .replace(">", amp + "gt;")
        .replace('"', amp + "quot;")
    )


def fmt_dur(sec) -> str:
    """秒 → "M:SS" 格式"""
    if not sec:
        return "0:00"
    return f"{int(sec) // 60}:{int(sec) % 60:02d}"


# ---------------------------------------------------------------------------
# 智能分段：按标点聚合为约 200-300 字的自然段落
# ---------------------------------------------------------------------------
def paragraphs(text: str) -> list:
    """将全文按标点切句，聚合为约 240 字的自然段落"""
    if not text:
        return ["（暂无内容）"]

    clean = re.sub(r"[\n\r]+", "", text)

    # 按句末标点切句（保留标点）
    sentences = re.split(r"(?<=[。！？!?；;])", clean)
    sentences = [s.strip() for s in sentences if s.strip()]

    paras = []
    cur = ""
    for s in sentences:
        if len(cur) + len(s) > 240 and cur.strip():
            paras.append(cur.strip())
            cur = ""
        cur += s
    if cur.strip():
        paras.append(cur.strip())
    return paras


# ---------------------------------------------------------------------------
# 单项目 HTML 学习报告
# ---------------------------------------------------------------------------
def generate_project_html(proj_name: str, data: dict) -> str:
    """
    data 结构:
        text: str       路演部分全文
        qa: str         评委问答全文
        photos: list    照片分析列表 [{src, theme, slide_role, ...}]
        speechStyle: dict
        pptStyle: dict
        review: dict
        hasText: bool
    """
    speech = data.get("speechStyle") or {}
    ppt = data.get("pptStyle") or {}
    review = data.get("review") or {}
    has_text = data.get("hasText", False)

    # ---- 照片网格 ----
    photo_html = ""
    for p in data.get("photos") or []:
        photo_html += (
            f'<figure class="slide"><img src="{p.get("src", "")}" loading="lazy" '
            f'onclick="this.classList.toggle(\'expand\')">'
            f'<figcaption>{esc(p.get("theme", ""))}<br>'
            f'<span class="role">[{esc(p.get("slide_role", ""))}]</span></figcaption></figure>\n'
        )

    # ---- PPT 风格结构 ----
    struct_html = "".join(
        f'<span class="chip">{esc(k)}×{v}</span>'
        for k, v in (ppt.get("structure") or {}).items()
    )
    type_html = "".join(
        f'<span class="chip">{esc(k)}×{v}</span>'
        for k, v in (ppt.get("pageTypes") or {}).items()
    )

    # ---- 五维雷达（星级条） ----
    dims = review.get("five_dimensions") or {}
    radar = ""
    for k, v in dims.items():
        half = max(1, round(v))
        stars = "★" * half + "☆" * max(0, 5 - half)
        radar += (
            f'<div class="dim"><span class="dim-name">{esc(k)}</span>'
            f'<span class="stars">{stars}</span></div>\n'
        )

    # ---- 演讲风格 ----
    style_html = ""
    if speech.get("cpm"):
        style_html = (
            f'<div class="stat"><b>{speech["cpm"]}</b>字/分钟</div>\n'
            f'<div class="stat"><b>{fmt_dur(speech.get("durationSec"))}</b>时长</div>\n'
            f'<div class="stat"><b>{speech.get("totalChars", 0)}</b>总字数</div>\n'
        )
    trans_html = "".join(
        f'<span class="chip">{esc(k)}×{v}</span>'
        for k, v in (speech.get("transitions") or {}).items()
    )
    words_html = "".join(
        f'<span class="chip">{esc(w.get("word", ""))}×{w.get("count", 0)}</span>'
        for w in (speech.get("topWords") or [])
    )

    # ---- 全文段落 ----
    pitch_paras = paragraphs(data.get("text") or "")
    qa_paras = paragraphs(data.get("qa") or "")
    text_html = '<h3 class="phase-title">🎤 路演部分</h3>\n'
    text_html += "\n".join(f"<p>{esc(p)}</p>" for p in pitch_paras)
    if data.get("qa"):
        text_html += '<h3 class="phase-title qa">💬 评委问答</h3>\n'
        text_html += "\n".join(f"<p>{esc(p)}</p>" for p in qa_paras)

    # ---- 仅图片模式：只显示照片（+简单页数统计） ----
    photo_counts = len(data.get("photos") or [])
    photo_only_section = (
        ""
        if has_text
        else f'<section><h2>📸 PPT照片（{photo_counts}张）</h2>'
             f'<div class="grid">{photo_html or "<p>无照片</p>"}</div></section>'
    )

    # ---- 评分星级 ----
    rating = review.get("rating") or 3
    rating_full = "★" * max(1, round(rating))
    rating_empty = "☆" * max(0, 5 - round(rating))

    strengths = review.get("key_strengths") or []
    risks = review.get("key_risks") or []
    learn_tips = review.get("learn_tips") or ""

    strengths_html = (
        f'<div class="strength"><b>✅ 看点：</b>'
        f'{"；".join(esc(x) for x in strengths)}</div>'
        if strengths else ""
    )
    risks_html = (
        f'<div class="risk"><b>⚠️ 短板：</b>'
        f'{"；".join(esc(x) for x in risks)}</div>'
        if risks else ""
    )
    tips_html = (
        f'<div class="tip"><b>📌 值得学习：</b>{esc(learn_tips)}</div>'
        if learn_tips else ""
    )

    # ---- 有文字时的段落 ----
    review_section = ""
    if has_text:
        review_section = (
            '<section><h2>⭐ 商业化可行性与学习要点</h2>\n'
            '<div class="review-box"><p><b>评分：'
            + rating_full + rating_empty
            + '</b></p>\n<p>' + esc(review.get("summary") or "") + '</p></div>\n'
        )
        if radar:
            review_section += f'<div style="margin-top:12px">{radar}</div>\n'
        review_section += strengths_html + "\n" + risks_html + "\n" + tips_html + "\n</section>"

    ppt_section = ""
    if has_text:
        ppt_section = (
            '<section><h2>🎨 PPT风格分析</h2>\n'
            '<p class="stats"><div class="stat"><b>'
            + str(ppt.get("slideCount") or 0)
            + '</b>页</div><div class="stat"><b>'
            + str(ppt.get("dataDensity") or 0)
            + '%</b>为数据图表页</div></p>\n'
            '<p><b>路演结构：</b>' + (struct_html or "无") + '</p>\n'
            '<p><b>页面类型：</b>' + (type_html or "无") + '</p>\n</section>'
        )

    speech_section = ""
    if has_text:
        speech_section = (
            '<section><h2>🎤 演讲风格分析</h2>\n'
            '<div class="stats">' + (style_html or "<p>音频时间缺失</p>") + '</div>\n'
        )
        if trans_html:
            speech_section += f'<p><b>常用过渡语：</b>{trans_html}</p>\n'
        if words_html:
            speech_section += f'<p><b>高频词：</b>{words_html}</p>\n'
        speech_section += "</section>"

    fulltext_section = ""
    if has_text:
        fulltext_section = (
            '<section><h2>📄 路演全文（AI纠错·分段）</h2>'
            f'<div class="fulltext">{text_html}</div></section>'
        )

    # ---- 组装 HTML 模板（CSS 与原 JS 版完全一致） ----
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{esc(proj_name)} - 路演学习分析</title>
<style>
body{{font-family:"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f7fa;color:#2c3e50;line-height:1.9;margin:0}}
.container{{max-width:980px;margin:0 auto;padding:24px 20px 60px}}
header{{background:linear-gradient(135deg,#1e3a5f,#3b6ea5);color:#fff;border-radius:14px;padding:24px;margin-bottom:20px}}
header h1{{font-size:24px;margin:0 0 6px}}
header .sub{{opacity:.85;font-size:13px}}
section{{background:#fff;border-radius:12px;padding:22px 26px;margin-bottom:18px;box-shadow:0 2px 10px rgba(0,0,0,.06)}}
section h2{{font-size:18px;color:#1e3a5f;border-left:4px solid #3b6ea5;padding-left:10px;margin:0 0 14px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}}
.slide img{{width:100%;border-radius:8px;border:1px solid #ddd;cursor:zoom-in;max-height:300px;object-fit:contain}}
.slide img.expand{{position:fixed;inset:20px;width:auto;height:auto;max-width:92vw;max-height:90vh;margin:auto;z-index:1000;box-shadow:0 0 0 100vmax rgba(0,0,0,.75)}}
.slide figcaption{{font-size:12px;color:#555;margin-top:4px}}.slide .role{{color:#999;font-size:11px}}
.chip{{display:inline-block;background:#eef3fb;color:#3b6ea5;border-radius:12px;padding:1px 10px;font-size:12px;margin:2px}}
.stats{{display:flex;gap:20px;flex-wrap:wrap}}.stat b{{font-size:22px;color:#1e3a5f}}.stat{{font-size:12px;color:#666}}
.dim{{margin-bottom:6px}}.dim-name{{display:inline-block;width:70px;font-size:13px}}.stars{{color:#f5b942;letter-spacing:2px}}
.phase-title{{font-size:15px;color:#fff;background:#3b6ea5;display:inline-block;padding:3px 14px;border-radius:16px;margin:12px 0}}
.phase-title.qa{{background:#8e44ad}}
.fulltext p{{text-indent:2em;margin-bottom:12px;font-size:14px}}
.review-box{{background:#fdf8f2;border-left:4px solid #f5b942;padding:14px 18px;border-radius:8px;font-size:14px}}
.risk{{color:#c0392b}}.strength{{color:#27ae60}}.tip{{background:#eef7ee;border-left:4px solid #27ae60;padding:10px 14px;border-radius:6px;font-size:13px;margin-top:10px}}
a.back{{display:inline-block;margin-bottom:14px;color:#3b6ea5;font-size:13px;text-decoration:none}}
</style></head><body><div class="container">
<a class="back" href="目录.html">← 返回项目总览</a>
<header><h1>{esc(proj_name)}</h1><div class="sub">路演学习分析报告｜照片 {photo_counts}张｜音频 {fmt_dur(speech.get("durationSec"))}</div></header>

{photo_only_section}

{review_section}

<section><h2>📸 PPT现场照片（按路演顺序）</h2><div class="grid">{photo_html or '<p>无照片</p>'}</div></section>

{ppt_section}

{speech_section}

{fulltext_section}
</div></body></html>"""


if __name__ == "__main__":
    # 简单自测：渲染一个最小报告
    sample = {
        "text": "大家好，这是我们项目的介绍。我们的解决方案是XXX。谢谢大家，请各位评委提问。",
        "qa": "问：成本多少？答：很低。",
        "photos": [{"src": "../test/a.jpg", "theme": "封面", "slide_role": "封面"}],
        "speechStyle": {"cpm": 180, "durationSec": 75, "totalChars": 225,
                        "transitions": {"那么": 1}, "topWords": [{"word": "项目", "count": 3}]},
        "pptStyle": {"slideCount": 1, "structure": {"封面": 1},
                     "pageTypes": {"标题页": 1}, "dataDensity": 0},
        "review": {"rating": 4, "summary": "测试点评。",
                   "five_dimensions": {"赛道空间": 4, "技术壁垒": 3, "临床验证": 3, "商业模式": 4, "团队实力": 4},
                   "key_strengths": ["A"], "key_risks": ["B"], "learn_tips": "C"},
        "hasText": True,
    }
    print(generate_project_html("测试项目", sample))