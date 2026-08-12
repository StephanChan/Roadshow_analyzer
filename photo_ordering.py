# -*- coding: utf-8 -*-
"""
图片-演讲稿 对照排序模块

背景：目前图片按文件名（字典序）展示，但真实路演翻页顺序通常与演讲内容对应。
本模块利用每张 PPT 的 OCR 文字与 AI 纠错后的演讲稿做关键词匹配，
把每张图"钉"到讲稿中语义最相关的位置，再按该位置重排图片顺序。

算法（纯标准库，无额外依赖）：
1. 讲稿切块：优先用 Whisper chunks（带文本），否则按约240字切段
2. 每块讲稿与每张图 OCR 提取关键词（中文2~6字 + 英文词 + 数字）
3. 计算各图与各块的字词重合度（Dice 系数）
4. 贪心最大匹配：图→块（每块至多用一次）
5. 无 OCR 的图片保持相对顺序，排在末位
"""
import re


# 中文停用词（降低噪声）
_STOPWORDS = {
    "我们", "这个", "一个", "可以", "然后", "还有", "所以", "但是",
    "那个", "非常", "就是", "什么", "现在", "大家", "咱们", "其实",
    "因为", "如果", "进行", "已经", "目前", "以及", "对于", "这样",
    "包括", "应该", "需要", "主要", "通过", "并且", "同时", "方面",
    "今天", "这些", "那些", "没有", "不是", "都是", "觉得", "看到",
}


# ---------------------------------------------------------------------------
# 文本处理
# ---------------------------------------------------------------------------
def _tokenize(text: str) -> set:
    """提取文本关键词集合：中文2~6字串 + 英文词 + 数字（过滤停用词）"""
    tokens = set()
    # 中文 2~6 字
    for w in re.findall(r"[\u4e00-\u9fff]{2,6}", text or ""):
        if w not in _STOPWORDS:
            tokens.add(w)
    # 英文单词/数字
    for w in re.findall(r"[A-Za-z]{2,}[A-Za-z0-9]*|\d+", text or ""):
        tokens.add(w.lower())
    return tokens


def _dice(a: set, b: set) -> float:
    """Dice 系数：2*|A∩B| / (|A|+|B|)，无交集返回0"""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return 2.0 * inter / (len(a) + len(b))


def _split_script(text: str, chunks: list = None) -> list:
    """
    把讲稿切成带序号的块：
    优先用 Whisper chunks（每块一段），否则按约240字切段。
    返回 [{"index": i, "text": str}, ...]
    """
    if chunks:
        blocks = []
        for i, c in enumerate(chunks):
            t = (c.get("text") or "").strip()
            if t:
                blocks.append({"index": i, "text": t})
        if len(blocks) >= 2:
            return blocks

    # 按 240 字切段
    text = re.sub(r"[\n\r]+", "", text or "")
    sentences = re.split(r"(?<=[。！？!?；;])", text)
    blocks, cur = [], ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if len(cur) + len(s) > 240 and cur:
            blocks.append({"index": len(blocks), "text": cur})
            cur = ""
        cur += s
    if cur:
        blocks.append({"index": len(blocks), "text": cur})
    return blocks


# ---------------------------------------------------------------------------
# 主排序函数
# ---------------------------------------------------------------------------
def order_photos_by_text(photos: list, text: str, chunks: list = None) -> list:
    """
    根据演讲稿对图片列表重新排序。

    参数:
        photos: analyze_image 返回的列表，每项含 'ocr'（可能为空）、'theme' 等
        text:   AI 纠错后的演讲稿全文
        chunks: Whisper 分段结果（带文本），可为空
    返回:
        重排后的 photos 列表（保持原 dict 结构；附加 'order_rank' / 'order_note'）
    """
    if not photos:
        return []

    # 统一以 photos 的列表序号为 key
    n = len(photos)
    if n < 2:
        for p in photos:
            p["order_rank"] = 0
            p["order_note"] = "唯一图片"
        return list(photos)

    blocks = _split_script(text or "", chunks)
    if not blocks:
        for i, p in enumerate(photos):
            p["order_rank"] = i
            p["order_note"] = "无讲稿，保持文件顺序"
        return list(photos)

    # ---- 1) 有 OCR / 无 OCR ----
    indexed = []      # [(photo_index, tokens)]
    no_ocr = set()    # 无 OCR 图的序号
    for i, p in enumerate(photos):
        tok = _tokenize(p.get("ocr") or "")
        if tok:
            indexed.append((i, tok))
        else:
            no_ocr.add(i)

    # ---- 2) 评分矩阵 ----
    block_tokens = [_tokenize(b["text"]) for b in blocks]
    n_blocks = len(block_tokens)

    scores = []  # (score, photo_idx, block_idx)
    for photo_idx, tok in indexed:
        for bi, bt in enumerate(block_tokens):
            sc = _dice(tok, bt)
            if sc > 0:
                scores.append((sc, photo_idx, bi))

    scores.sort(key=lambda x: (-x[0], x[1], x[2]))

    # ---- 3) 贪心最大匹配（每块至多用一次） ----
    used_blocks = set()
    assigned = {}  # photo_idx -> block_idx
    for sc, photo_idx, bi in scores:
        if photo_idx in assigned:
            continue
        if bi in used_blocks:
            continue
        assigned[photo_idx] = bi
        used_blocks.add(bi)

    # ---- 4) 计算每张图排序值 ----
    # 有匹配的图：位置 = block_idx*1000 + 分数微调（保证同块先后的稳定性）
    # 无匹配但有 OCR、无 OCR 的图：按原文件序号放大后排在后面
    rank = {}
    for i in range(n):
        if i in assigned:
            bi = assigned[i]
            sc = _dice([t for (idx, t) in indexed if idx == i][0], block_tokens[bi])
            rank[i] = bi * 1000 + round(sc * 999)
        else:
            rank[i] = 10 ** 9 + i

    # ---- 5) 排序并附加信息 ----
    ordered_idx = sorted(range(n), key=lambda i: rank[i])
    ordered = []
    for pos, i in enumerate(ordered_idx):
        p = photos[i]
        p["order_rank"] = pos
        if i in assigned:
            p["order_note"] = f"对应讲稿第{assigned[i] + 1}段"
        elif i in no_ocr:
            p["order_note"] = "纯图页(无OCR文字)"
        else:
            p["order_note"] = "未匹配到讲稿段"
        ordered.append(p)

    return ordered


if __name__ == "__main__":
    # 简单自测
    demo_photos = [
        {"file": "b.jpg", "ocr": "市场规模 2025 百亿 增长"},
        {"file": "a.jpg", "ocr": "封面 AI器官芯片 清华 国创中心"},
        {"file": "c.jpg", "ocr": ""},
    ]
    demo_text = "大家好，今天我们介绍AI器官芯片项目。首先封面展示清华与国创中心合作。"
    demo_chunks = [
        {"timestamp": [0, 5], "text": "大家好，今天我们介绍AI器官芯片项目。"},
        {"timestamp": [5, 10], "text": "首先封面展示清华与国创中心合作。"},
    ]
    result = order_photos_by_text(demo_photos, demo_text, demo_chunks)
    for p in result:
        print(p["file"], "->", p.get("order_note"))