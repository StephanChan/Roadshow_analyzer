# -*- coding: utf-8 -*-
"""
综合分析模块：AI纠错 + PPT风格分析 + 演讲风格分析 + 商业化点评
对应原 JS 版 roadshow_analyzer/analyzer.js
"""
import re
from collections import Counter

from deepseek_client import call_api_retry, chunk_text, extract_json


# ===========================================================================
# DeepSeek AI 二次纠错
# ===========================================================================
def ai_fix(proj_name: str, text: str) -> str:
    """
    对转录文本按 3000 字分段，逐段调用 DeepSeek 纠错
    返回纠错后全文（分段间用换行连接，与 JS 版 join('\\n') 一致）
    """
    print(f"  [AI纠错] {proj_name} ({len(text)}字)")
    chunks = chunk_text(text)

    system_prompt = (
        "你是专业中文听写纠错专家。修正识别错误（错字/漏字/繁简混用），"
        "特别是医疗/生物科技术语。保持口语风格，直接输出纠错后全文，不解释。"
    )

    fixed_parts = []
    for i, chunk in enumerate(chunks):
        print(f"    [第{i+1}/{len(chunks)}段纠错中...]")
        r = call_api_retry(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"行业背景：医企创业路演。请纠错：\n{chunk}"},
            ],
            {"temperature": 0.2, "maxTokens": 4000},
        )
        fixed_parts.append(r)
    return "\n".join(fixed_parts)


# ===========================================================================
# 演讲稿结构拆解（路演/问答分界）
# ===========================================================================
def split_qa(text: str) -> dict:
    """
    用正则定位"谢谢大家，请评委提问"之类分界点，切分路演与问答
    返回 {"pitch": str, "qa": str}
    """
    # 与 JS 版一致的正则（Python 需加 re.S 使 . 匹配换行）
    qa_kws = re.compile(
        r"(谢谢大家?|多谢)[^。！？]{0,25}(请|有请)?\s*(评委|专家|各位评委)[^。！？]{0,10}(提问|评议|点评|议论)",
        re.S,
    )
    m = qa_kws.search(text or "")
    if not m:
        return {"pitch": text or "", "qa": ""}

    idx = m.start()
    if idx <= 0:
        return {"pitch": text or "", "qa": ""}

    # 从最近的句号后切割
    cut = text.rfind("。", 0, idx)
    split_at = (cut + 1) if cut > 0 else idx
    return {"pitch": text[:split_at], "qa": text[split_at:]}


# ===========================================================================
# 演讲风格分析（语速/结构化/金句）
# ===========================================================================
# 过渡语列表（与 JS 版一致）
_TRANSITIONS = [
    "我们可以看到", "简单来说", "也就是说", "所以说", "举个例子",
    "另外", "其实", "最终", "所以说", "那么",
]
# 高频词黑名单（与 JS 版一致）
_BLACKLIST = {
    "什么", "就是", "这个", "一个", "我们", "可以", "然后",
    "还有", "所以", "但是", "那个", "非常",
}


def analyze_speech_style(text: str, chunks: list) -> dict:
    """
    演讲风格分析：
    - cpm: 汉字数/分钟
    - duration_sec: 总时长（最后一个 chunk 的结束时间）
    - total_chars: 汉字总数
    - transitions: 过渡语出现次数
    - top_words: 高频词 Top10（按出现次数降序）
    返回 dict（键名与 JS 版 word 风格一致，方便 HTML 渲染）
    """
    # 汉字数
    hanzi = re.findall(r"[\u4e00-\u9fff]", text or "")
    total_chars = len(hanzi)

    # 总时长（秒）
    total_seconds = 0.0
    if chunks:
        total_seconds = chunks[-1].get("timestamp", [0, 0])[1] or 0
    cpm = round(total_chars / (total_seconds / 60)) if total_seconds > 60 else None

    # 过渡语统计
    trans_hits = {}
    for t in _TRANSITIONS:
        n = len(re.findall(re.escape(t), text or ""))
        if n > 0:
            trans_hits[t] = n

    # 高频词 Top10
    words = re.findall(r"[\u4e00-\u9fff]{2,6}", text or "")
    freq = Counter(words)
    top_words = [
        {"word": w, "count": n}
        for w, n in freq.most_common()
        if n >= 3 and w not in _TRANSITIONS and w not in _BLACKLIST
    ][:10]

    return {
        "cpm": cpm,
        "durationSec": round(total_seconds),
        "totalChars": total_chars,
        "transitions": trans_hits,
        "topWords": top_words,
    }


# ===========================================================================
# PPT风格分析（基于图片分析结果）
# ===========================================================================
def analyze_ppt_style(photo_analyses: list) -> dict:
    """
    PPT 风格统计：
    - slide_count: 页数
    - structure: 各 slide_role 数量分布
    - page_types: 各 type 数量分布
    - data_density: 数据图表页占比(%)
    返回 dict（键名与 JS 版一致）
    """
    roles = Counter()
    types = Counter()
    for p in photo_analyses or []:
        roles[p.get("slide_role", "")] += 1
        types[p.get("type", "")] += 1

    total = len(photo_analyses or [])
    data_density = round((types.get("数据图表页", 0) / max(total, 1)) * 100)

    return {
        "slideCount": total,
        "structure": dict(roles),
        "pageTypes": dict(types),
        "dataDensity": data_density,
    }


# ===========================================================================
# 学术报告点评（学术质量评审，不点评商业化）
# ===========================================================================
def academic_review(proj_name: str, text: str, photo_themes: list = None) -> dict:
    """
    针对学术报告做学术质量五维评审：
    返回 dict（rating/five_dimensions/summary/key_strengths/key_risks/learn_tips）
    失败时返回 fallback
    """
    post_it = (text or "")[:5000]
    photo_summary = "; ".join(photo_themes or [])[:20 * 40]

    prompt = f"""请针对以下学术报告做学术质量评审，输出JSON：
{{
  "rating": 1-5的整数评分,
  "five_dimensions": {{"创新性": 1-5, "方法严谨性": 1-5, "数据充分性": 1-5, "结论合理性": 1-5, "表达清晰度": 1-5}},
  "summary": "150字以内的犀利评审（直指研究的创新点/方法缺陷/数据支撑/结论过度推演等）",
  "key_strengths": ["2-3个学术亮点"],
  "key_risks": ["2-3个学术短板（方法/数据/论证逻辑问题）"],
  "learn_tips": "从这份学术报告中值得学习的一点（研究设计/论证逻辑/图表表达）"
}}

【评审严谨性要求 —— 必须遵守】
1. 这是学术报告而非商业路演，【不要评审商业化可行性】（用户明确不需要）；
   不要提"商业模式/市场规模/付费方/融资"等话题。
2. 重点评审：研究问题是否有价值、方法是否严谨、数据是否充分、
   结论是否被数据支持（避免过度推演）、表达是否清晰。
3. 每一条优缺点必须注明推断来源（来自报告内容 / PPT画面 / 学术常识）。
4. 杜绝空泛模板结论："创新性一般""数据不足"等一律禁止，
   要针对该报告的具体研究内容做点上的分析。

项目：{proj_name}
PPT页面主题：{photo_summary or '无照片'}
报告内容（节选）：{post_it}
只输出JSON。"""

    try:
        raw = call_api_retry(
            [
                {"role": "system", "content": "你是学术报告质量评审专家，严谨、直击要害。"},
                {"role": "user", "content": prompt},
            ],
            {"temperature": 0.4, "maxTokens": 1500},
        )
        return extract_json(raw)
    except Exception as e:
        print(f"    [AI学术评审失败] {e}")
        return {"rating": 3, "summary": "（AI学术评审生成失败）"}


# ===========================================================================
# 商业化五维点评
# ===========================================================================
def commercial_review(proj_name: str, text: str, photo_themes: list = None) -> dict:
    """
    调用 DeepSeek 做商业化可行性五维评分点评
    返回 dict（rating/five_dimensions/summary/key_strengths/key_risks/learn_tips）
    失败时返回 fallback
    """
    post_it = (text or "")[:5000]
    photo_summary = "; ".join(photo_themes or [])[:20 * 40]  # 截取前20个主题的容量

    prompt = f"""请针对以下医企创业路演项目做商业化可行性分析，输出JSON：
{{
  "rating": 1-5的整数评分,
  "five_dimensions": {{"赛道空间": 1-5, "技术壁垒": 1-5, "临床验证": 1-5, "商业模式": 1-5, "团队实力": 1-5}},
  "summary": "150字以内的犀利点评（直指商业模式本质/可复制性/监管风险）",
  "key_strengths": ["2-3个看点"],
  "key_risks": ["2-3个致命短板"],
  "learn_tips": "从这份路演中值得学习的一点（PPT逻辑/叙事方式/数据呈现）"
}}

【分析严谨性要求 —— 必须遵守】
1. 区分"患者个人支付意愿"与"付费方结构/支付能力"：患者强烈需要不等于商业上付费路径清晰。
   除非材料中确有依据，否则不要把"个体想买"武断表述为"支付意愿低"或"支付意愿强"，
   应改为讨论：谁付费（自费/医保/残联/商保）、目标群体购买力、获客与复购结构。
2. 区分医疗器械分类与注册周期：二类器械注册通常1-2年、成本可控；三类植入/侵入器械才需多年高成本。
   除非材料明确指向三类，否则不要笼统写"注册周期长、成本高"。
3. 每一条风险/优势必须注明推断来源（来自讲稿内容 / PPT画面 / 行业常识），
   避免把"路演模板常见话术"当成该项目的事实。
4. 杜绝空泛模板结论："目标人群小=没市场""需要注册=周期长""团队无商业经验=必败"等一律禁止，
   要针对该项目的具体产品形态、付费场景、竞品替代方案做点上的分析。

项目：{proj_name}
PPT页面主题：{photo_summary or '无照片'}
演讲内容（节选）：{post_it}
只输出JSON。"""

    try:
        raw = call_api_retry(
            [
                {"role": "system", "content": "你是医企投资路演商业化分析专家，风格犀利、直击要害。"},
                {"role": "user", "content": prompt},
            ],
            {"temperature": 0.4, "maxTokens": 1500},
        )
        return extract_json(raw)
    except Exception as e:
        print(f"    [AI点评失败] {e}")
        return {"rating": 3, "summary": "（AI点评生成失败）"}


if __name__ == "__main__":
    # 简单自测
    print(split_qa("大家好，这是我的项目介绍。谢谢大家，请各位评委提问。我们的产品是X。"))
    print(analyze_speech_style("我们我们我们大家好，这是一个测试", [{"timestamp": [0, 75]}]))
    print(analyze_ppt_style([
        {"slide_role": "封面", "type": "标题页"},
        {"slide_role": "市场数据", "type": "数据图表页"},
        {"slide_role": "市场数据", "type": "数据图表页"},
    ]))