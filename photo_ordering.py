# -*- coding: utf-8 -*-
"""
图片排序模块（文稿方向仲裁版）

背景：早期版本用"OCR 关键词与演讲稿 Dice 匹配"来精确还原每张图的位置，
但实际经常匹配不准（OCR 噪声大、讲稿用词与 PPT 文字不一致），用户反馈顺序错误。

新策略（三层配合）：
1. 【候选顺序】
   - 优先：倒计时（路演屏幕右上角剩余时间，MM:SS / HH:MM:SS），
     剩余时间多 = 页面越早 → 按降序排列。
   - 其次：文件名自然排序（数字不按字典序），初始默认升序。
2. 【文稿方向仲裁】
   候选顺序的方向（升序还是降序）由文稿最终决定：
   - 把文稿按时间先后切成与图片数相同的段；
   - 按候选顺序把每张图的 OCR 与对应位置文稿段做关键词匹配，
     累加得到"正向得分"；再把候选顺序整体反转，得到"反向得分"；
   - 哪个方向得分高，就用哪个方向（这就是"文稿只决定要不要反过来"）。
3. 【兜底】文件名完全无数字且无 OCR 时，保持文件列表原序。
"""
import re


# ---------------------------------------------------------------------------
# 倒计时提取
# ---------------------------------------------------------------------------
# HH:MM:SS（如 00:05:02）与 MM:SS（如 5:02 / 05:02，兼容全角冒号）
_COUNTDOWN_HMS = re.compile(r"(?<!\d)(\d{1,2})\s*[:：]\s*(\d{2})\s*[:：]\s*(\d{2})(?!\d)")
_COUNTDOWN_MS = re.compile(r"(?<!\d)(\d{1,2})\s*[:：]\s*(\d{2})(?!\d)")


def _extract_countdown_sec(ocr: str):
    """
    从 OCR 文本提取倒计时秒数；无则返回 None。
    倒计时显示的是剩余时间 mm:ss（或 hh:mm:ss）。
    """
    if not ocr:
        return None
    # 优先 HH:MM:SS
    m = _COUNTDOWN_HMS.search(ocr)
    if m:
        hh, mm, ss = int(m.group(1)), int(m.group(2)), int(m.group(3))
        total = hh * 3600 + mm * 60 + ss
        if 0 <= ss < 60 and 0 <= mm < 60 and 0 <= total <= 3 * 3600:
            return total
    # 再找 MM:SS
    for m in _COUNTDOWN_MS.finditer(ocr):
        mm, ss = int(m.group(1)), int(m.group(2))
        # 路演倒计时一般 ≤ 30 分钟
        if 0 <= ss < 60 and 0 <= mm <= 30:
            return mm * 60 + ss
    return None


# ---------------------------------------------------------------------------
# 文件名自然排序
# ---------------------------------------------------------------------------
def _natural_key(name: str):
    """文件名数字自然排序 key：把 'abc123.jpg' 拆成 ('abc',123,'.jpg')"""
    return tuple((int(p) if p.isdigit() else p) for p in re.split(r"(\d+)", name or ""))


def _main_number(name: str):
    """取文件名中最后一个数字段（通常最能代表顺序），无则 None"""
    nums = [int(x) for x in re.findall(r"\d+", name or "")]
    return nums[-1] if nums else None


# ---------------------------------------------------------------------------
# 关键词匹配工具（供文稿方向仲裁使用）
# ---------------------------------------------------------------------------
# 中文停用词（降低噪声）
_STOPWORDS = {
    "我们", "这个", "一个", "可以", "然后", "还有", "所以", "但是",
    "那个", "非常", "就是", "什么", "现在", "大家", "咱们", "其实",
    "因为", "如果", "进行", "已经", "目前", "以及", "对于", "这样",
    "包括", "应该", "需要", "主要", "通过", "并且", "同时", "方面",
    "今天", "这些", "那些", "没有", "不是", "都是", "觉得", "看到",
}


def _tokenize(text: str) -> set:
    """
    提取文本关键词集合（纯标准库）：
    - 中文：2~6 字连续块 + 2 字 bigram（滑动词，能匹配"封面/项目"这类词）
    - 英文词 / 数字
    过滤停用词。
    """
    tokens = set()
    # 2~6 字连续块
    for w in re.findall(r"[\u4e00-\u9fff]{2,6}", text or ""):
        if w not in _STOPWORDS:
            tokens.add(w)
    # 2 字 bigram 滑动窗口（"这是封面" → "这是","是封","封面"，可捕获 OCR 中的二字词）
    chars = re.findall(r"[\u4e00-\u9fff]", text or "")
    for i in range(len(chars) - 1):
        w = chars[i] + chars[i + 1]
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


def _split_text_segments(text: str, n: int) -> list:
    """
    把文稿按句子顺序切成 n 段（尽可能等长，保持先后次序）。
    返回 [str, ...]；n<=0 或 text 为空返回空列表。
    """
    if n <= 0 or not text:
        return []
    text = re.sub(r"[\n\r]+", "", text or "")
    sentences = [s.strip() for s in re.split(r"(?<=[。！？!?；;])", text) if s.strip()]
    if not sentences:
        return [text] * n if text else []

    # 把句子尽量均匀分成 n 组（按累计字符数贪心）
    total_chars = sum(len(s) for s in sentences)
    target_len = max(1, total_chars / n)

    segments, cur, cur_len = [], [], 0.0
    for s in sentences:
        cur.append(s)
        cur_len += len(s)
        if cur_len >= target_len and len(segments) < n - 1:
            segments.append("".join(cur))
            cur, cur_len = [], 0.0
    if cur:
        segments.append("".join(cur))

    # 补齐：若切得比 n 少，末尾补空段，保持索引一一对应
    while len(segments) < n:
        segments.append("")
    return segments[:n]


# ---------------------------------------------------------------------------
# 文稿方向仲裁
# ---------------------------------------------------------------------------
def _direction_score(photos: list, order_idx: list, text: str) -> float:
    """
    按给定顺序计算"图片 OCR 与文稿分段"的整体语义匹配总分。
    分数越高说明该顺序与文稿叙述顺序越吻合。
    """
    n = len(order_idx)
    if n < 2 or not text:
        return 0.0

    segments = _split_text_segments(text, n)
    seg_tokens = [_tokenize(s) for s in segments]

    total = 0.0
    matched = 0
    for pos, i in enumerate(order_idx):
        tok = _tokenize((photos[i] or {}).get("ocr") or "")
        if tok and seg_tokens[pos]:
            sc = _dice(tok, seg_tokens[pos])
            total += sc
            if sc > 0:
                matched += 1
    return total


def _resolve_direction(photos: list, candidate: list, text: str) -> tuple:
    """
    用文稿仲裁候选顺序的方向。
    candidate: 候选索引列表（假定为"正向"）
    text:      演讲稿全文
    返回 (final_order_idx, note_suffix)
    """
    fwd = candidate
    rev = list(reversed(candidate))

    score_fwd = _direction_score(photos, fwd, text)
    score_rev = _direction_score(photos, rev, text)

    # 无文稿或双方都匹配不到 → 保持候选方向
    if score_fwd == 0 and score_rev == 0:
        return fwd, "（无文稿可校验，保持默认方向）"

    # 反向得分明显更高（>5% 容差）→ 判定应反转
    if score_rev > score_fwd * 1.05:
        return rev, "（文稿校验：反向与讲稿更吻合）"
    return fwd, "（文稿校验：正向与讲稿吻合）"


# ---------------------------------------------------------------------------
# 候选顺序生成
# ---------------------------------------------------------------------------
def _order_by_countdown(photos: list, cd: dict) -> list:
    """
    倒计时主导候选：
    - 有倒计时的图：按倒计时【降序】（剩余时间多 = 页越早）
    - 无倒计时但像封面的图：排最前（封面是第一页）
    - 其余无倒计时的图：按文件名自然序排在末尾
    cd: {photo_index: countdown_seconds}
    """
    n = len(photos)
    has_cd = sorted(
        (i for i in range(n) if i in cd),
        key=lambda i: (-cd[i], _natural_key(photos[i].get("file", ""))),
    )
    no_cd = [i for i in range(n) if i not in cd]
    cover_idx = sorted(
        (i for i in no_cd if _looks_like_cover(photos[i])),
        key=lambda i: _natural_key(photos[i].get("file", "")),
    )
    rest_idx = sorted(
        (i for i in no_cd if i not in cover_idx),
        key=lambda i: _natural_key(photos[i].get("file", "")),
    )
    return cover_idx + has_cd + rest_idx


def _looks_like_cover(p: dict) -> bool:
    """判断一张图是否像封面页（演讲的第一张，应排在最前）"""
    role = (p.get("slide_role") or "").strip()
    if role == "封面":
        return True
    if role == "尾页":
        return False
    ocr = (p.get("ocr") or "").strip()
    theme = (p.get("theme") or "").strip()
    if ocr and len(ocr) <= 120:
        if re.search(r"第.{1,5}届|创业大赛|封面|欢迎|项目名称|路演|答辩", ocr):
            return True
    if theme and re.search(r"封面|路演|欢迎|第.{1,5}届|大赛", theme):
        return True
    return False


def _order_by_filename(photos: list, direction: int) -> list:
    """按文件名自然序升序(1)/降序(-1)排序"""
    return sorted(
        range(len(photos)),
        key=lambda i: _natural_key(photos[i].get("file", "")),
        reverse=(direction < 0),
    )


# ---------------------------------------------------------------------------
# 主排序函数
# ---------------------------------------------------------------------------
def order_photos_by_text(photos: list, text: str, chunks: list = None) -> list:
    """
    对图片列表重新排序（倒计时 > 文件名；方向由文稿仲裁）。

    参数:
        photos: analyze_image 返回的列表，每项含 'ocr'（可能为空）、'theme'、'slide_role'、'file' 等
        text:   AI 纠错后的演讲稿全文（可空；仅图片模式也适用）
        chunks: Whisper 分段结果（带文本），可为空（本函数不使用，保留兼容签名）
    返回:
        重排后的 photos 列表（保持原 dict 结构；附加 'order_rank' / 'order_note'）
    """
    if not photos:
        return []

    n = len(photos)
    if n < 2:
        for p in photos:
            p["order_rank"] = 0
            p["order_note"] = "唯一图片"
        return list(photos)

    # ---- 1. 提取倒计时 ----
    cd = {}
    for i, p in enumerate(photos):
        sec = _extract_countdown_sec(p.get("ocr"))
        if sec is not None:
            cd[i] = sec

    # ---- 2. 生成候选顺序 ----
    if len(cd) >= max(1, n * 0.5):
        candidate = _order_by_countdown(photos, cd)
        base_note = "倒计时候选"
    else:
        # 文件名候选方向：有无数字？
        if any(_main_number(p.get("file", "")) is not None for p in photos):
            candidate = _order_by_filename(photos, 1)  # 先按升序做候选
            base_note = "文件名候选（默认升序）"
        else:
            # 文件名无数字 → 保持扫描顺序（无方向可仲裁）
            candidate = list(range(n))
            base_note = "文件顺序（无数字可判）"

    # ---- 3. 文稿方向仲裁：升序还是降序，由文稿最终拍板 ----
    ordered_idx, dir_note = _resolve_direction(photos, candidate, text or "")
    note = f"{base_note}{dir_note}"

    # ---- 4. 附加说明 ----
    ordered = []
    for pos, i in enumerate(ordered_idx):
        p = photos[i]
        p["order_rank"] = pos
        if i in cd:
            mm, ss = divmod(cd[i], 60)
            p["order_note"] = f"{note}，倒计时 {mm:02d}:{ss:02d}"
        else:
            p["order_note"] = note
        ordered.append(p)

    return ordered


if __name__ == "__main__":
    # 简单自测
    demo_photos = [
        {"file": "微信图片_20260805132329_204_2.jpg", "ocr": "封面 第X届深创赛 项目", "theme": "封面", "slide_role": "封面"},
        {"file": "微信图片_20260805132330_205_2.jpg", "ocr": "商业模式 混合模式 05:02", "theme": "商业模式", "slide_role": "商业模式"},
        {"file": "微信图片_20260805132331_206_2.jpg", "ocr": "临床验证 病例 03:30", "theme": "临床验证", "slide_role": "临床验证"},
        {"file": "微信图片_20260805132332_207_2.jpg", "ocr": "技术原理 02:15", "theme": "技术原理", "slide_role": "技术原理"},
    ]
    result = order_photos_by_text(demo_photos, "大家好，今天介绍项目。先是封面。")
    for p in result:
        print(p["file"], "->", p.get("order_note"))

    print("\n--- 无倒计时文件名排序 + 文稿仲裁测试 ---")
    demo2 = [
        {"file": "IMG_0001.jpg", "ocr": "尾页 谢谢 提问", "slide_role": "尾页"},
        {"file": "IMG_0002.jpg", "ocr": "产品介绍 功能", "slide_role": "其他"},
        {"file": "IMG_0003.jpg", "ocr": "封面 项目 路演", "slide_role": "封面"},
    ]
    for p in order_photos_by_text(demo2, "大家好，这是封面。接下来介绍产品。最后感谢大家，欢迎提问。"):
        print(p["file"], "->", p.get("order_note"))