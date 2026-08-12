# -*- coding: utf-8 -*-
"""
DeepSeek AI 服务模块：统一调用（文本分析/纠错/图片理解/点评）
对应原 JS 版 roadshow_analyzer/deepseek.js
"""
import json
import re
import time

import requests

import config


# ---------------------------------------------------------------------------
# 基础 API 调用
# ---------------------------------------------------------------------------
def call_api(messages: list, temperature: float = 0.3, max_tokens: int = 4000) -> str:
    """
    调用 DeepSeek Chat Completions API
    参数:
        messages: [{"role": ..., "content": ...}, ...]
    返回:
        模型输出的文本内容（去除首尾空白）
    异常:
        网络错误 / API 错误 / JSON 解析失败时抛出
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
    }
    body = {
        "model": config.DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    resp = requests.post(config.DEEPSEEK_API_URL, json=body, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    if data.get("error"):
        raise RuntimeError(data["error"].get("message", "API错误"))

    try:
        return (data["choices"][0]["message"]["content"] or "").strip()
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"解析失败: {e}")


# ---------------------------------------------------------------------------
# 带重试的调用（指数退避）
# ---------------------------------------------------------------------------
def call_api_retry(messages: list, opts: dict = None, retries: int = 4) -> str:
    """
    带重试的 API 调用。opts 可包含 {"temperature": ..., "maxTokens": ...}
    与 JS 版逻辑一致：失败后等待 (i+1)*5 秒再试
    """
    opts = opts or {}
    temperature = opts.get("temperature", 0.3)
    max_tokens = opts.get("maxTokens", 4000)

    last_exc = None
    for i in range(retries):
        try:
            return call_api(messages, temperature=temperature, max_tokens=max_tokens)
        except Exception as e:
            last_exc = e
            if i == retries - 1:
                break
            wait = (i + 1) * 5
            print(f"    [API重试 {i+1}/{retries}] {e}（{wait}秒后重试...）")
            time.sleep(wait)
    raise last_exc


# ---------------------------------------------------------------------------
# 按长度安全分段
# ---------------------------------------------------------------------------
def chunk_text(text: str, size: int = None) -> list:
    """将文本按字符数分段，默认使用 config.CHUNK_SIZE"""
    if size is None:
        size = config.CHUNK_SIZE
    return [text[i:i + size] for i in range(0, len(text), size)]


# ---------------------------------------------------------------------------
# JSON 提取辅助
# ---------------------------------------------------------------------------
def extract_json(raw: str):
    """
    从模型输出中提取第一个 {...} 并解析为 dict。
    失败时抛出异常（由调用方决定 fallback）。
    """
    m = re.search(r"\{[\s\S]*\}", raw or "")
    if not m:
        raise ValueError(f"输出中未找到 JSON: {raw[:200]}")
    return json.loads(m.group(0))


if __name__ == "__main__":
    # 简单自测：调用一次 API
    r = call_api_retry(
        [{"role": "user", "content": "请回复'连接正常'四个字"}],
        {"temperature": 0.1, "maxTokens": 20},
    )
    print("API测试:", r)