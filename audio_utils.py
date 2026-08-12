# -*- coding: utf-8 -*-
"""
音频工具模块：ffmpeg 转 WAV + 解析为 float32 数组
对应原 JS 版 roadshow_analyzer/transcriber.js 中的 convertToWav / parseWavToFloat32
"""
import struct
import subprocess
import time
from pathlib import Path

import numpy as np

import config


# ---------------------------------------------------------------------------
# ffmpeg 转 WAV（16kHz 单声道 16bit PCM）
# ---------------------------------------------------------------------------
def convert_to_wav(input_path: Path | str) -> Path:
    """
    用 ffmpeg 将任意音频转为 16kHz / 单声道 / 16bit PCM WAV
    返回临时 WAV 文件路径（调用方负责删除）
    """
    input_path = Path(input_path)
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    wav_path = config.CACHE_DIR / f"conv_{int(time.time() * 1000)}.wav"

    cmd = [
        config.FFMPEG_PATH,
        "-y",
        "-i", str(input_path),
        "-ar", "16000",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        str(wav_path),
    ]
    # 静默执行，异常时抛出包含 stderr 的错误信息
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg 转换失败: {e.stderr[-500:] if e.stderr else e}")

    if not wav_path.exists():
        raise RuntimeError("ffmpeg 未生成 WAV 文件")
    return wav_path


# ---------------------------------------------------------------------------
# 解析 WAV 为 float32 数组（归一化到 [-1, 1]）
# ---------------------------------------------------------------------------
def parse_wav_to_float32(wav_path: Path | str) -> np.ndarray:
    """
    解析 16bit PCM WAV 文件，返回 float32 数组（值域 [-1.0, 1.0]）
    """
    with open(wav_path, "rb") as f:
        buf = f.read()

    # 定位 data chunk（与 JS 版逻辑一致：从偏移 12 开始逐 chunk 查找）
    i = 12
    data_offset = -1
    data_size = 0
    n = len(buf)
    while i <= n - 8:
        chunk_id = buf[i:i + 4].decode("ascii", errors="replace")
        size = struct.unpack_from("<I", buf, i + 4)[0]
        if chunk_id == "data":
            data_offset = i + 8
            data_size = size
            break
        i += 8 + size + (size % 2)

    if data_offset < 0:
        raise RuntimeError("WAV 中未找到 data chunk")

    # 读取 int16 样本并归一化
    sample_bytes = buf[data_offset:data_offset + data_size]
    sample_count = len(sample_bytes) // 2
    int16 = np.frombuffer(sample_bytes[:sample_count * 2], dtype=np.int16)
    return int16.astype(np.float32) / 32768.0


if __name__ == "__main__":
    # 简单自测：python audio_utils.py <音频路径>
    import sys
    if len(sys.argv) > 1:
        wav = convert_to_wav(sys.argv[1])
        data = parse_wav_to_float32(wav)
        print(f"转换完成: {wav}")
        print(f"采样点数: {len(data)}（时长 {len(data) / 16000:.1f} 秒）")
        try:
            wav.unlink()
        except OSError:
            pass