# -*- coding: utf-8 -*-
"""
音频转录模块：faster-whisper 转写音频 → 文本 + chunks（带时间戳）
对应原 JS 版 roadshow_analyzer/transcriber.js
"""
from pathlib import Path

from audio_utils import convert_to_wav, parse_wav_to_float32

import config


# ---------------------------------------------------------------------------
# 模块级环境初始化（必须在任何 huggingface_hub 导入之前执行）
# 设置镜像：优先使用 hf-mirror.com（国内加速）
# ---------------------------------------------------------------------------
import os as _os
_os.environ["HF_ENDPOINT"] = config.HF_MIRROR


# ---------------------------------------------------------------------------
# 模型单例（懒加载，避免重复加载 + 首次自动下载）
# ---------------------------------------------------------------------------
_model = None


def _resolve_model_path():
    """
    返回本地模型的实际路径（含模型文件的目录），找不到返回 None。
    优先匹配 download_model.py 下载的目录结构:
        models/models--Systran--faster-whisper-large-v3/snapshots/<hash>/
    内部含 config.json / model.bin 等实际模型文件。
    """
    # 完整仓库名目录（与 download_model.py 一致）
    repo_dir = config.LOCAL_MODEL_DIR / f"models--Systran--faster-whisper-{config.WHISPER_MODEL}"
    # 兼容旧命名（仅模型名）
    if not repo_dir.exists():
        repo_dir = config.LOCAL_MODEL_DIR / f"models--{config.WHISPER_MODEL}"

    if not repo_dir.exists():
        return None

    # 1) HF 缓存结构: repo_dir/snapshots/<revision>/ 内含实际文件
    snapshots = repo_dir / "snapshots"
    if snapshots.is_dir():
        for rev in snapshots.iterdir():
            if not rev.is_dir():
                continue
            # 验证该版本包含模型文件
            if any((rev / f).exists() for f in ("config.json", "model.bin", "model.onnx")):
                return str(rev)

    # 2) 直接平铺结构: repo_dir/config.json + model.bin
    if (repo_dir / "config.json").exists() or (repo_dir / "model.bin").exists():
        return str(repo_dir)

    # 3) 有目录但内容不完整
    print(f"  [警告] 本地模型目录 {repo_dir} 存在但内容不完整，尝试联网下载...")
    return None


def _get_model():
    """懒加载 faster-whisper 模型（模块级单例）"""
    global _model
    if _model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as e:
            import sys
            raise RuntimeError(
                "缺少 faster-whisper 依赖。\n"
                f"当前解释器: {sys.executable}\n"
                "修复方式：在 Anaconda Prompt 中执行:\n"
                "  conda activate roadshow_analyzer\n"
                "  pip install faster-whisper==1.0.3 ctranslate2==4.4.0 setuptools==69.5.1\n"
            ) from e

        # 优先使用本地模型（已用 download_model.py 预下载时）
        model_path = _resolve_model_path()
        if model_path:
            print(f"  [模型] 使用本地模型: {model_path}")
        else:
            print(f"  [模型] 未找到本地缓存，将从 {config.HF_MIRROR} 下载 {config.WHISPER_MODEL} ...")
            print("  [模型] 也可先运行 python download_model.py 预下载，避免运行中失败")

        _model = WhisperModel(
            model_path or config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
            local_files_only=bool(model_path),
        )
    return _model


# ---------------------------------------------------------------------------
# 转写入口
# ---------------------------------------------------------------------------
def transcribe_audio(audio_path: Path | str) -> dict:
    """
    转写单个音频文件
    返回: {"text": str, "chunks": [{"timestamp": [start, end], "text": str}, ...]}
    """
    audio_path = Path(audio_path)
    print(f"  [转录] {audio_path.name}")

    try:
        model = _get_model()
    except Exception as e:
        # 给出更易操作的提示
        if "local_files_only" in str(e) or "cached snapshot" in str(e) or "locate the file" in str(e):
            raise RuntimeError(
                "Whisper 模型下载失败。可能原因与处理：\n"
                "  1. 网络无法访问 HuggingFace/HF-mirror → 在 config.py 把 HF_MIRROR "
                "改为官方 https://huggingface.co 或可通的镜像\n"
                "  2. 网络不稳定中途失败 → 先运行 python download_model.py 预下载模型（支持断点续传）\n"
                "  3. 磁盘空间不足（large-v3 约需 3GB）→ 清理磁盘或在 config.py 改 WHISPER_MODEL='small'\n"
            ) from e
        raise

    # 1. ffmpeg 解码为 16kHz WAV
    wav_path = convert_to_wav(audio_path)
    try:
        # 2. 解析为 float32 数组
        audio = parse_wav_to_float32(wav_path)
        print(f"  [转录] 音频时长 {len(audio) / 16000:.1f} 秒，转写中...")

        # 3. faster-whisper 转写（API 与 transformers.js 不同：
        #    不支持 stride_length（那是 JS 版参数），
        #    长音频由 chunk_length 自动分段）
        segments, info = model.transcribe(
            audio,
            language=config.WHISPER_LANGUAGE,
            task="transcribe",
            chunk_length=config.WHISPER_CHUNK_LENGTH_S,
            word_timestamps=True,
        )

        # segments 是生成器，需转为列表
        seg_list = list(segments)

        # 重组文本与 chunks（格式对齐 JS 版 result.text / result.chunks）
        text = "".join(s.text for s in seg_list).strip()
        chunks = [
            {"timestamp": [float(s.start), float(s.end)], "text": s.text}
            for s in seg_list
        ]
        return {"text": text, "chunks": chunks}
    finally:
        # 4. 清理临时 WAV
        try:
            wav_path.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    # 简单自测: python transcriber.py <音频路径>
    import sys
    if len(sys.argv) > 1:
        result = transcribe_audio(sys.argv[1])
        print(f"转写文本({len(result['text'])}字):\n{result['text'][:200]}...")
        print(f"chunks 数: {len(result['chunks'])}")