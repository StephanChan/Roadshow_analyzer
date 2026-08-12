# -*- coding: utf-8 -*-
"""
图片分析模块：本地 OCR 提取文字 + DeepSeek AI 综合理解（识别PPT主题/版式/数据）
对应原 JS 版 roadshow_analyzer/photo_analyzer.js
"""
import json
from pathlib import Path

from deepseek_client import call_api_retry, extract_json
from ocr_module import ocr_image


# ---------------------------------------------------------------------------
# 分析单张图片
# ---------------------------------------------------------------------------
def analyze_image(img_path: Path | str, proj_name: str, img_index: int, total: int) -> dict:
    """
    分析一张图片：
    返回 {"theme": str, "slide_role": str, "type": str, "key_points": list, "ocr": str}
    AI 分析失败时返回基于 OCR 的 fallback 结果（与 JS 版一致）
    """
    img_path = Path(img_path)

    # 1. 本地 OCR
    ocr = ocr_image(img_path)

    # 2. 构造 DeepSeek 分析 prompt（与原 JS 版一致）
    prompt = f"""你是一位PPT路演分析专家。下面是一张路演PPT图片的OCR提取文字（可能有噪声）。
项目：{proj_name}（第{img_index + 1}/{total}张）
OCR内容：{ocr or '（OCR未识别到文字，可能是纯图片页）'}
请分析并输出JSON：
{{
  "theme": "该PPT页面的核心主题（一句话）",
  "slide_role": "在路演结构中的角色（封面/痛点/解决方案/市场数据/技术原理/产品展示/竞争分析/商业模式/团队介绍/融资页/政策背景/临床验证/发展规划/尾页）",
  "type": "页面类型（标题页/文字要点页/数据图表页/图文混排页/团队介绍页/流程图页）",
  "key_points": ["该页最关键的2-3个要点（从OCR提取，简练）"]
}}
只输出JSON。"""

    # fallback 基础结果
    fallback = {
        "theme": ocr[:60] if ocr else "（图片页，无文字）",
        "slide_role": "其他",
        "type": "图文页",
        "key_points": [ocr[:50]] if ocr else [],
    }

    try:
        raw = call_api_retry(
            [{"role": "user", "content": prompt}],
            {"temperature": 0.2, "maxTokens": 1000},
        )
        parsed = extract_json(raw)
        # 合并解析结果与 OCR 文本
        result = dict(fallback)
        result.update(parsed)
        result["ocr"] = ocr
        return result
    except Exception as e:
        print(f"    [图片AI分析失败] {img_path.name}: {e}")
        fallback["ocr"] = ocr
        return fallback


if __name__ == "__main__":
    # 简单自测: python photo_analyzer.py <图片路径> <项目名> <序号> <总数>
    import sys
    if len(sys.argv) > 1:
        r = analyze_image(
            sys.argv[1],
            sys.argv[2] if len(sys.argv) > 2 else "测试项目",
            int(sys.argv[3]) if len(sys.argv) > 3 else 0,
            int(sys.argv[4]) if len(sys.argv) > 4 else 1,
        )
        print(json.dumps(r, ensure_ascii=False, indent=2))