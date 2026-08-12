# -*- coding: utf-8 -*-
"""
路演分析平台 - 配置文件
对应原 JS 版 roadshow_analyzer/config.js
"""
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# OpenMP 冲突规避（必须在任何 OpenMP 相关库导入前设置）
# ctranslate2（faster-whisper 底层）自带 libomp.dll，
# 而 conda 环境中的 numpy 等其他包可能带 libiomp5md.dll（Intel OpenMP）。
# 同一进程加载两份 OpenMP 运行时会报:
#   OMP: Error #15: Initializing libomp.dll, but found libiomp5md.dll already initialized.
# 设置 KMP_DUPLICATE_LIB_OK=TRUE 是官方文档允许的无害绕行方案，业界普遍使用。
# ---------------------------------------------------------------------------
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# ---------------------------------------------------------------------------
# 目录配置
# ---------------------------------------------------------------------------
# 输入目录（默认当前工作目录，可用环境变量 INPUT_DIR 覆盖）
INPUT_DIR = Path(os.environ.get("INPUT_DIR", os.getcwd()))

# 模型/缓存目录（Whisper 模型缓存、临时 WAV 文件）
CACHE_DIR = Path(__file__).resolve().parent / "cache"

# 输出目录：跟随输入目录，放在输入目录下的 analysis_output/ 子文件夹
# 注意：main.py 会在解析命令行参数后动态重设 OUTPUT_DIR
OUTPUT_DIR = INPUT_DIR / "analysis_output"

# ---------------------------------------------------------------------------
# DeepSeek API 配置
# 优先从环境变量读取；其次从项目根目录 .env 文件读取；
# 若都未配置，则使用本地文件 _secrets.py 中的占位值（仅本地开发用，勿提交到 git）
# ---------------------------------------------------------------------------
def _load_api_key() -> str:
    """读取 DeepSeek API Key：环境变量 > .env 文件 > 本地 secrets"""
    env_key = os.environ.get("DEEPSEEK_API_KEY")
    if env_key:
        return env_key

    # 从 .env 文件读取（格式: DEEPSEEK_API_KEY=sk-xxx）
    env_file = Path(__file__).resolve().parent / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        except OSError:
            pass

    # 本地占位文件 _secrets.py（不入库），用于未配置环境变量时的备用
    secrets_file = Path(__file__).resolve().parent / "_secrets.py"
    if secrets_file.exists():
        try:
            ns: dict = {}
            exec(secrets_file.read_text(encoding="utf-8"), ns)
            return ns.get("DEEPSEEK_API_KEY", "")
        except OSError:
            pass

    return ""


DEEPSEEK_API_KEY = _load_api_key()
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"

# ---------------------------------------------------------------------------
# Whisper 模型配置（faster-whisper）
# ---------------------------------------------------------------------------
# 可选: "large-v3"（约3GB）, "medium"（约1.5GB）, "small"（约460MB）, "base", "tiny"
# 网络不好时可先用 small 验证整体流程，再换回 large-v3
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "large-v3")
WHISPER_DEVICE = "cpu"          # 无 GPU 时用 cpu
WHISPER_COMPUTE_TYPE = "int8"   # CPU 量化加速
WHISPER_LANGUAGE = "zh"
WHISPER_CHUNK_LENGTH_S = 30
WHISPER_STRIDE_LENGTH_S = 5

# HuggingFace 镜像（加速国内下载；下载失败时先确认此站点可达）
# 若公司网络禁止访问 hf-mirror.com，可改为官方 https://huggingface.co
HF_MIRROR = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com")

# 本地模型目录：优先从该目录加载模型（配合 download_model.py 预下载）
# 目录结构: roadshow_analyzer_py/models/models--Systran--faster-whisper-large-v3/
LOCAL_MODEL_DIR = Path(__file__).resolve().parent / "models"

# ---------------------------------------------------------------------------
# 外部可执行文件
# ---------------------------------------------------------------------------
# 复用 transcribe_v3 下已有的 ffmpeg.exe（若不存在则回退到系统 PATH 中的 ffmpeg）
_DEFAULT_FFMPEG = Path(__file__).resolve().parents[1] / "transcribe_v3" / "ffmpeg.exe"
FFMPEG_PATH = str(_DEFAULT_FFMPEG) if _DEFAULT_FFMPEG.exists() else "ffmpeg"

# pytesseract 的 tesseract.exe 路径
# 若未安装到默认位置，请手动改为实际安装路径，例如:
#   r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_CMD = os.environ.get("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
# 中文训练数据目录（当前工作目录下已有 chi_sim.traineddata，可指向现工作目录）
TESSDATA_PREFIX = os.environ.get("TESSDATA_PREFIX", os.getcwd())

# ---------------------------------------------------------------------------
# 文件后缀定义
# ---------------------------------------------------------------------------
AUDIO_EXTS = [".m4a", ".mp3", ".wav", ".mp4", ".aac", ".flac", ".ogg"]
DOC_EXTS = [".txt", ".md", ".doc", ".docx"]
PHOTO_EXTS = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"]

# ---------------------------------------------------------------------------
# 幂等控制：已处理的标记文件
# ---------------------------------------------------------------------------
DONE_MARKER = ".roadshow_done"

# ---------------------------------------------------------------------------
# 其他参数
# ---------------------------------------------------------------------------
# AI 纠错/分析的分段大小（字符数）
CHUNK_SIZE = 3000

# 转录文稿保存命名：AI纠错后的全文保存在各项目子文件夹内，后缀为 "_全文"
# 例：AI器官芯片-清华-国创中心/AI器官芯片-清华-国创中心_全文.txt
# 下次处理时若检测到该文件，将直接读取并跳过音频转写
TRANSCRIPT_SUFFIX = "_全文"

# 排除的目录名（扫描项目时跳过）
EXCLUDED_DIR_KEYS = ("roadshow_analyzer", "analysis_output", "output", "cache")