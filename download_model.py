# -*- coding: utf-8 -*-
"""
Whisper 模型预下载脚本（推荐先运行，避免 main.py 运行中下载失败）

用法：
    python download_model.py                # 下载 config.WHISPER_MODEL（默认 large-v3）
    python download_model.py small          # 下载指定模型（small/medium/large-v3...）

下载完成后模型保存在 roadshow_analyzer_py/models/ 目录，
后续运行 main.py / transcriber.py 时自动优先使用本地模型，不再联网。

如果 hf-mirror 无法访问，可改镜像：
    python download_model.py large-v3 --endpoint https://huggingface.co
"""
import argparse
import sys
from pathlib import Path

# 确保模块间 import 正常
if __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import config


def main() -> None:
    parser = argparse.ArgumentParser(description="下载 Whisper 模型（支持断点续传）")
    parser.add_argument("model", nargs="?", default=config.WHISPER_MODEL,
                        help=f"模型名，默认 {config.WHISPER_MODEL}")
    parser.add_argument("--endpoint", default=config.HF_MIRROR,
                        help=f"镜像地址，默认 {config.HF_MIRROR}")
    args = parser.parse_args()

    # 构造镜像环境变量（必须在导入 huggingface_hub 之前设置）
    import os
    os.environ["HF_ENDPOINT"] = args.endpoint

    # 完整仓库名（与 faster-whisper 一致）
    repo_id = f"Systran/faster-whisper-{args.model}"

    config.LOCAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    local_dir = config.LOCAL_MODEL_DIR / f"models--{repo_id.replace('/', '--')}"

    print("=" * 60)
    print(f"模型仓库 : {repo_id}")
    print(f"下载镜像 : {args.endpoint}")
    print(f"保存目录 : {local_dir}")
    print("=" * 60)

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("缺少 huggingface_hub，请先执行: pip install huggingface-hub==0.24.0")
        sys.exit(1)

    try:
        path = snapshot_download(
            repo_id=repo_id,
            local_dir=str(local_dir),
            resume_download=True,
        )
    except Exception as e:
        print(f"\n[下载失败] {e}")
        print("\n处理建议：")
        print("  1. 镜像不通 → 换官方地址: python download_model.py large-v3 --endpoint https://huggingface.co")
        print("  2. 公司网络限制 → 切换到可用的镜像站（如 https://hf-mirror.com）")
        print("  3. 磁盘空间不足（large-v3 约需 3GB）→ 清理磁盘或改下 small 模型")
        sys.exit(1)

    print(f"\n✅ 下载完成！模型已保存到: {path}")
    print("现在可以正常运行 main.py（将自动使用本地模型，不再联网下载）")


if __name__ == "__main__":
    main()