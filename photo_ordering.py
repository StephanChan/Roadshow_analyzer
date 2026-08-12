# -*- coding: utf-8 -*-
"""
图片排序模块（新策略）

背景：早期版本用"OCR 关键词与演讲稿 Dice 匹配"来还原翻页顺序，
但实际路演照片经常匹配不准（OCR 噪声大、讲稿用词与 PPT 文字不一致），
用户反馈 AI器官芯片 等项目排序错误。

新策略（按可靠性从高到低依次尝试）：
1. 【倒计时优先】路演屏幕右上角常有倒计时（如 05:02 表示剩余 5 分 2 秒），
   每页照片的 OCR 里若能提取到 mm:ss，就能精确还原翻页顺序：
   剩余时间越多 = 页面越靠前，故按倒计时【降序】排列。
   （若实际屏幕显示的是"已用时间"而非剩余时间，把 _ORDER_BY_COUNTDOWN 里
    的 -cd 改为 cd 即可切换为升序。）
2. 【文件名排序】无倒计时（或数量太少）时，按文件名自然排序，
   并自动判断升序/降序：
     - 优先看第一张/最后一张是否像封面页（AI 识别的 slide_role 或标题性 OCR）
     - 否则看文件名数字序列的整体趋势
   例：微信图片_20260805132329_204_2.jpg 时间戳递增 → 升序 = 拍摄顺序。
3. 【讲稿匹配兜底】仅当文件名完全无数字规律时才回退到原 OCR-讲稿
   关键词匹配（_order_by_text_legacy），避免排序退化。
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


def _looks_like_cover(p: dict) -> bool:
    """判断一张图是否像封面页（演讲的第一张，应排在最前）"""
    role = (p.get("slide_role") or "").strip()
    if role == "封面":
        return True
    if role == "尾页":
        return False
    ocr = (p.get("ocr") or "").strip()
    theme = (p.get("theme") or "").strip()
    # 标题性 OCR：文字较少且含 届/赛/封面/项目名 等标志
    if ocr and len(ocr) <= 120:
        if re.search(r"第.{1,5}届|创业大赛|封面|欢迎|项目名称|路演|答辩", ocr):
            return True
    if theme and re.search(r"封面|路演|欢迎|第.{1,5}届|大赛", theme):
        return True
    return False


def _detect_name_direction(photos: list) -> int:
    """
    自动判断文件名应为升序(1)还是降序(-1)。

    依据1：封面页应在第一张——分别看"文件名升序的第一张"和
           "文件名降序的第一张"哪个更像封面，即得到正确方向。
    依据2：当封面判断不明确时，看文件名数字序列的整体趋势
           （升多于降 → 升序；降多于升 → 降序）。
    """
    if len(photos) < 2:
        return 1

    asc = sorted(photos, key=lambda p: _natural_key(p.get("file", "")))
    desc = list(reversed(asc))

    asc_cover = _looks_like_cover(asc[0])
    desc_cover = _looks_like_cover(desc[0])
    if asc_cover and not desc_cover:
        return 1
    if desc_cover and not asc_cover:
        return -1

    # 数字趋势判断
    nums = [_main_number(p.get("file", "")) for p in photos]
    nums = [x for x in nums if x is not None]
    if len(nums) >= 3:
        inc = sum(1 for i in range(1, len(nums)) if nums[i] > nums[i - 1])
        dec = sum(1 for i in range(1, len(nums)) if nums[i] < nums[i - 1])
        if dec > inc:
            return -1
    return 1


# ---------------------------------------------------------------------------
# 三种排序实现
# ---------------------------------------------------------------------------
def _order_by_countdown(photos: list, cd: dict) -> list:
    """
    倒计时主导排序：
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


def _order_by_filename(photos: list, direction: int) -> list:
    """按文件名自然序升序(1)/降序(-1)排序"""
    return sorted(
        range(len(photos)),
        key=lambda i: _natural_key(photos[i].get("file", "")),
        reverse=(direction < 0),
    )


def _order_by_text_legacy(photos: list, text: str, chunks: list = None) -> list:
    """
    兜底：原"OCR-讲稿关键词匹配"算法。
    仅当文件名无数字规律、无法用倒计时/文件名排序时使用。
    """
    if not photos:
        return []
    n = len(photos)
    if n < 2:
        return list(photos)

    # 中文停用词（降低噪声）
    stopwords = {
        "我们", "这个", "一个", "可以", "然后", "还有", "所以", "但是",
        "那个", "非常", "就是", "什么", "现在", "大家", "咱们", "其实",
        "因为", "如果", "进行", "已经", "目前", "以及", "对于", "这样",
        "包括", "应该", "需要", "主要", "通过", "并且", "同时", "方面",
        "今天", "这些", "那些", "没有", "不是", "都是", "觉得", "看到",
    }

    def tokenize(s):
        toks = set()
        for w in re.findall(r"[\u4e00-\u9fff]{2,6}", s or ""):
            if w not in stopwords:
                toks.add(w)
        for w in re.findall(r"[A-Za-z]{2,}[A-Za-z0-9]*|\d+", s or ""):
            toks.add(w.lower())
        return toks

    def dice(a, b):
        if not a or not b:
            return 0.0
        inter = len(a & b)
        if inter == 0:
            return 0.0
        return 2.0 * inter / (len(a) + len(b))

    # 讲稿切块
    blocks = []
    if chunks:
        for i, c in enumerate(chunks):
            t = (c.get("text") or "").strip()
            if t:
                blocks.append({"index": i, "text": t})
        if len(blocks) < 2:
            blocks = []
    if not blocks:
        text = re.sub(r"[\n\r]+", "", text or "")
        sentences = re.split(r"(?<=[。！？!?；;])", text)
        cur = ""
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
    if not blocks:
        return list(range(n))

    # 评分矩阵 + 贪心最大匹配
    indexed, no_ocr = [], set()
    for i, p in enumerate(photos):
        tok = tokenize(p.get("ocr") or "")
        if tok:
            indexed.append((i, tok))
        else:
            no_ocr.add(i)

    block_tokens = [tokenize(b["text"]) for b in blocks]
    scores = []
    for photo_idx, tok in indexed:
        for bi, bt in enumerate(block_tokens):
            sc = dice(tok, bt)
            if sc > 0:
                scores.append((sc, photo_idx, bi))
    scores.sort(key=lambda x: (-x[0], x[1], x[2]))

    used_blocks, assigned = set(), {}
    for sc, photo_idx, bi in scores:
        if photo_idx in assigned or bi in used_blocks:
            continue
        assigned[photo_idx] = bi
        used_blocks.add(bi)

    rank = {}
    for i in range(len(photos)):
        if i in assigned:
            bi = assigned[i]
            tok = [t for (idx, t) in indexed if idx == i][0]
            sc = dice(tok, block_tokens[bi])
            rank[i] = bi * 1000 + round(sc * 999)
        else:
            rank[i] = 10 ** 9 + i

    return sorted(range(len(photos)), key=lambda i: rank[i])


# ---------------------------------------------------------------------------
# 主排序函数
# ---------------------------------------------------------------------------
def order_photos_by_text(photos: list, text: str, chunks: list = None) -> list:
    """
    对图片列表重新排序（新策略：倒计时 > 文件名 > 讲稿匹配兜底）。

    参数:
        photos: analyze_image 返回的列表，每项含 'ocr'（可能为空）、'theme'、'slide_role' 等
        text:   AI 纠错后的演讲稿全文（可空；仅图片模式也适用）
        chunks: Whisper 分段结果（带文本），可为空
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

    # ---- 2. 倒计时覆盖足够时，用倒计时主导 ----
    if len(cd) >= max(1, n * 0.5):
        ordered_idx = _order_by_countdown(photos, cd)
        note = "倒计时排序"
    else:
        # ---- 3. 文件名主导（自动判断升/降）----
        # 若文件名完全没有数字且无法判断方向，退化到讲稿匹配兜底
        has_num = any(_main_number(p.get("file", "")) is not None for p in photos)
        if not has_num:
            ordered_idx = _order_by_text_legacy(photos, text or "", chunks)
            note = "讲稿匹配兜底"
        else:
            direction = _detect_name_direction(photos)
            ordered_idx = _order_by_filename(photos, direction)
            note = "文件名排序" + ("（升序）" if direction > 0 else "（降序）")

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
    result = order_photos_by_text(demo_photos, "大家好", None)
    for p in result:
        print(p["file"], "->", p.get("order_note"))

    print("\n--- 无倒计时文件名排序测试 ---")
    demo2 = [
        {"file": "IMG_0001.jpg", "ocr": "封面 路演", "slide_role": "封面"},
        {"file": "IMG_0002.jpg", "ocr": "产品介绍", "slide_role": "其他"},
        {"file": "IMG_0003.jpg", "ocr": "团队 谢", "slide_role": "尾页"},
    ]
    for p in order_photos_by_text(demo2, "", None):
        print(p["file"], "->", p.get("order_note"))