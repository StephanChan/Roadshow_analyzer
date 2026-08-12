# -*- coding: utf-8 -*-
"""
总览 index.html 生成模块：全部项目横向对比表格
对应原 JS 版 roadshow_analyzer/run.js 中的 buildIndexHtml

注意：链接 href 直接使用项目中文原名（不做 URL 编码），与 pipeline.py
保存的 HTML 文件名（中文原名）保持一致。若 href 用 %XX 编码串而磁盘文件名
也是编码字面量，浏览器打开 file:// 时会把 %XX 解码成中文去请求文件，
而磁盘上是编码字面量名，文件名不匹配导致跳转失败。
"""
def esc(s) -> str:
    """HTML 转义（使用 chr(38) 构造 & 符号）"""
    amp = chr(38)  # &
    return (
        str(s or "")
        .replace(amp, amp + "amp;")
        .replace("<", amp + "lt;")
        .replace(">", amp + "gt;")
        .replace('"', amp + "quot;")
    )


def _stars(n: int) -> str:
    """生成长度为 5 的星号串（四舍五入）"""
    n = max(1, round(n))
    return "★" * n + "☆" * max(0, 5 - n)


def build_index_html(results: list) -> str:
    """
    生成总览 HTML。
    results: list，每个元素是 None（失败）或 dict:
        {name, review, speechStyle, pptStyle, photoCount, hasText}
    """
    dim_names = ["赛道空间", "技术壁垒", "临床验证", "商业模式", "团队实力"]

    rows = []
    for i, r in enumerate(results, start=1):
        if not r:
            continue
        review = r.get("review") or {}
        dims = review.get("five_dimensions") or {}
        dim_str = " ".join(
            f"{d}:{_stars(dims.get(d, 3))}" for d in dim_names
        )
        summary = (review.get("summary") or "")[:60]
        rating = review.get("rating") or 3
        cpm = (r.get("speechStyle") or {}).get("cpm")
        cpm_str = f"{cpm}字/分" if cpm else "-"

        rows.append(f"""<tr>
      <td>{i}</td>
      <td><a href="{r['name']}.html">{esc(r['name'])}</a></td>
      <td>{_stars(rating)}</td>
      <td><small>{esc(summary)}</small></td>
      <td><small>{dim_str}</small></td>
      <td>{r.get('photoCount') or 0}</td>
      <td>{cpm_str}</td>
    </tr>""")

    rows_html = "\n".join(rows)
    total = len([r for r in results if r])

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><title>路演项目学习分析 - 总览</title>
<style>
body{{font-family:"PingFang SC","Microsoft YaHei",sans-serif;background:#f5f7fa;padding:30px}}
h1{{color:#1e3a5f;text-align:center}}.sub{{text-align:center;color:#666;margin-bottom:24px}}
table{{width:100%;border-collapse:collapse;background:#fff;box-shadow:0 2px 10px rgba(0,0,0,.06);border-radius:10px;overflow:hidden}}
th{{background:#1e3a5f;color:#fff;padding:12px;font-size:13px;text-align:left}}
td{{padding:12px;border-bottom:1px solid #eef2f7;font-size:13px;vertical-align:top}}
tr:hover td{{background:#f0f4fa}}a{{color:#3b6ea5;text-decoration:none;font-weight:600}}
</style></head><body>
<h1>🏥 医企创业路演 - 学习分析平台</h1>
<p class="sub">共 {total} 个项目｜评分 / 五维雷达 / 演讲风格 / PPT风格</p>
<table><thead><tr><th>#</th><th>项目</th><th>评分</th><th>犀利点评</th><th>五维</th><th>PPT数</th><th>语速</th></tr></thead>
<tbody>{rows_html}</tbody></table>
</body></html>"""


if __name__ == "__main__":
    # 简单自测
    sample = [
        {"name": "测试项目A", "review": {"rating": 4, "summary": "点评A",
                                        "five_dimensions": {"赛道空间": 4, "技术壁垒": 3, "临床验证": 3, "商业模式": 4, "团队实力": 4}},
         "speechStyle": {"cpm": 180}, "photoCount": 3, "hasText": True},
        None,
        {"name": "测试项目B", "review": {"rating": 5, "summary": "点评B",
                                        "five_dimensions": {"赛道空间": 5, "技术壁垒": 5, "临床验证": 4, "商业模式": 5, "团队实力": 4}},
         "speechStyle": {}, "photoCount": 1, "hasText": False},
    ]
    print(build_index_html(sample))