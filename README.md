# 路演分析平台（Python 版）

原 JS 版 `roadshow_analyzer/` 的 Python 改写版，可在 **Spyder** 中直接运行。

## 功能

自动扫描指定目录下的项目子文件夹（每个文件夹含音频/PPT照片/文稿），对每个项目：

1. **音频转写**：ffmpeg 转 16kHz WAV → faster-whisper（默认 large-v3）中文转写，带时间戳 chunks
2. **图片理解**：pytesseract 本地 OCR（chi_sim）→ DeepSeek AI 判断每张 PPT 的 theme / slide_role / type / key_points
3. **AI 纠错**：DeepSeek 对转写文本按 3000 字分段纠错（医疗术语 + 繁简统一）
4. **路演/问答拆分**：正则定位"谢谢大家，请评委提问"分界
5. **演讲风格分析**：语速（字/分）、时长、总字数、过渡语、高频词 Top10
6. **PPT 风格分析**：页数、路演结构分布、页面类型分布、数据页占比
7. **商业化五维点评**：评分 + 五维雷达（赛道/壁垒/临床/商业/团队）+ 看点/短板/学习点
8. **输出 HTML**：单项目报告 + 总览 1目录.html 横向对比表

支持三种模式：
- **有音频**：转写 + 全部分析
- **有文稿（.txt/.md）**：读文稿 + 全部分析（跳过转写）
- **仅图片**：只做 OCR + AI 图片理解 + 照片网格

## 目录结构

```
roadshow_analyzer_py/
├── config.py            # 全局配置（路径/API/模型/OCR）
├── scanner.py           # 扫描项目子文件夹
├── audio_utils.py       # ffmpeg 转 WAV + 解析 float32
├── transcriber.py       # faster-whisper 音频转写
├── ocr_module.py        # pytesseract 本地 OCR
├── photo_analyzer.py    # 图片 OCR + DeepSeek AI 分析
├── deepseek_client.py   # DeepSeek API 封装（重试/分段/JSON提取）
├── analyzer.py          # AI纠错/路演问答拆分/两种风格分析/商业化点评
├── html_reporter.py     # 单项目 HTML 报告生成
├── index_builder.py     # 总览 1目录.html 生成
├── pipeline.py          # 单项目完整管线
├── main.py              # 主入口（Spyder F5 运行）
├── environment.yml      # Conda 一键环境（精确锁定全部版本，推荐）
├── requirements.txt     # pip 依赖清单（精确锁定全部版本）
```

## 需要安装的模块清单

下表列出了运行本程序**必须**安装的 Python 包（以及可选的繁简转换包），并标注了各模块分别在代码的哪个环节使用：

| 模块 | 用途 | 必需 |
|---|---|---|
| `faster-whisper` | 语音转录（替代 JS 版 transformers whisper）| ✅ 必需 |
| `numpy` | WAV 音频解析为 float32 数组 | ✅ 必需 |
| `pytesseract` | 调用 tesseract.exe 做中文 OCR | ✅ 必需 |
| `Pillow` | pytesseract 图像处理底层依赖 | ✅ 必需 |
| `requests` | DeepSeek API 调用 | ✅ 必需 |
| `opencc-python-reimplemented` | 繁简转换（补充 AI 纠错）| ⬜ 可选 |
| `jieba` | 中文分词（增强高频词统计，不装也能跑）| ⬜ 可选 |

另外还有**一个非 Python 软件**需要安装：**Tesseract OCR**（tesseract.exe），详见下文第 3 节。

---

## 环境准备

### 1. 安装 Python 依赖（提供两种精确锁定版本方式）

#### 方式 A：Conda 环境文件（推荐，一条命令装好全部依赖并精确锁定版本）

项目已提供 **`environment.yml`**，用 conda 一键创建环境（自动安装 Python + 全部模块，版本全部精确锁定）：

```bat
cd roadshow_analyzer_py
conda env create -f environment.yml
```

创建完成后激活环境：

```bat
conda activate roadshow_analyzer
```

在 Spyder 中使用该环境：**工具 → 偏好设置 → Python 解释器 → 使用以下解释器**，选择
`你的conda路径\envs\roadshow_analyzer\python.exe`。

> 为什么推荐 Conda：`environment.yml` 同时锁定了 Python 版本（3.11.10，已规避 3.11.9 在 Windows 上的 ssl 证书缺陷）和每个包的确切版本，任何机器上都能 100% 复现环境，避免"我这能跑你那不能跑"的版本差异问题。

#### 方式 B：pip requirements.txt（同样精确锁定版本）

项目已提供 **`requirements.txt`**，所有必需包（含 faster-whisper 底层 ctranslate2/tokenizers 等传递依赖）均已 `==` 精确锁定：

```bat
pip install -r roadshow_analyzer_py\requirements.txt
```

#### 方式 C：手动用 pip 挑选安装（不锁版本，仅用于快速验证）

```python
!pip install faster-whisper numpy pytesseract Pillow requests
```

（在 Spyder 的 IPython 控制台中输入，注意 `!` 前缀；或在 Anaconda Prompt / CMD 中去掉 `!`。此方式不锁版本，可能与上述精确版本略有差异。）

---

### 2. 验证依赖安装成功

在 Spyder 控制台或 CMD 中运行：

```python
import faster_whisper, numpy, pytesseract, PIL, requests
print("全部导入成功")
```

出现 `全部导入成功` 即安装完成。

---

### 3. 安装 Tesseract OCR（中文识别必需，属于软件而非 Python 包）

1. 下载安装包：[UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)（Windows 版）
   - 直接下载链接示例：<https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe>
2. 安装时勾选 **Additional language data → Chinese (Simplified)**（简体中文语言包），或安装后在 `tessdata` 文件夹放入 `chi_sim.traineddata`
3. 本项目当前目录已自带 `chi_sim.traineddata`，`config.py` 的 `TESSDATA_PREFIX` 默认指向当前目录，无需重复下载
4. 若 tesseract.exe 未安装在默认路径 `C:\Program Files\Tesseract-OCR\tesseract.exe`，请编辑 `roadshow_analyzer_py/config.py`：
   ```python
   TESSERACT_CMD = r"你的实际路径\tesseract.exe"
   ```

验证 Tesseract 是否可用（在 CMD 或 Spyder 控制台）：

```bat
tesseract --version
```

若提示不是内部命令，请把 `C:\Program Files\Tesseract-OCR` 加入系统 PATH，或在 `config.py` 中指定 `TESSERACT_CMD` 完整路径。

---

### 4. ffmpeg（可选，已有自带版本）

`config.py` 会自动复用 `transcribe_v3/ffmpeg.exe`（项目内已存在），无需额外安装；若该文件被删除，则回退到系统 PATH 中的 `ffmpeg`。

---

### 5. 首次运行会自动下载 Whisper 模型

运行 `main.py` 转写第一个音频时，程序会自动从 HuggingFace（已配置 `hf-mirror.com` 镜像）下载 Whisper large-v3 模型（约 3GB，只需下载一次，之后自动缓存到本地）。若网络较慢，可在 `config.py` 中把 `WHISPER_MODEL` 改为 `"small"`（约 460MB，速度快、精度略低）先行验证流程。

---

### 6. 常见安装报错与解决

| 报错信息 | 原因 | 解决方法 |
|---|---|---|
| `pip 不是内部或外部命令` | Python 未加入 PATH | 用 Spyder 控制台 `!pip install ...` 或 Anaconda Prompt |
| `ModuleNotFoundError: No module named 'faster_whisper'` | 依赖未安装到当前环境 | 确认是在 Spyder 使用的同一个 Python 环境里安装 |
| `pytesseract.pytesseract.TesseractNotFoundError` | 找不到 tesseract.exe | 安装 Tesseract 或在 `config.py` 设置 `TESSERACT_CMD` |
| `Error opening data file chi_sim.traineddata` | TESSDATA_PREFIX 指向错误 | 确认 `config.py` 中 `TESSDATA_PREFIX` 指向含 `chi_sim.traineddata` 的目录 |
| 模型下载超时/失败 | 网络问题 | 重试一次；或设置 `WHISPER_MODEL="small"` 减小体积 |
| `No module named 'ctranslate2'` | faster-whisper 安装不完整 | `pip install faster-whisper` 会自动带 ctranslate2，重装一次即可 |
| **Spyder 打不开**：`ssl.SSLError: [ASN1: NOT_ENOUGH_DATA] not enough data` | 环境创建时误用了 **Python 3.11.9**，该版本在 Windows 有已知 ssl 证书解析缺陷（3.11.10 修复） | 见下方"Spyder 打不开的专项修复" |
| `ModuleNotFoundError: No module named 'pkg_resources'` | conda 新建的 Python 3.11+ 环境默认不捆绑 setuptools，而 ctranslate2（faster-whisper 底层）依赖其 pkg_resources 模块 | `pip install setuptools==69.5.1`；`environment.yml` 与 `requirements.txt` 已加入该依赖，重装环境后自动解决 |

### ⚠️ Spyder 打不开的专项修复（ssl.SSLError: [ASN1: NOT_ENOUGH_DATA]）

**原因**：若创建环境时用了 `python=3.11.9`，它在 Windows 上读取系统证书库时会崩溃（官方 3.11.10 修复）。Spyder 依赖的 `aiohttp` 初始化 ssl 上下文时触发该错误，导致 Spyder 无法启动；并且您的程序调用 DeepSeek API（requests）时也会同样崩溃，因此**必须修复 Python 版本**。

**方案一：原地升级 Python（推荐，最快）**

```bat
conda activate roadshow_analyzer
conda install python=3.11.10 -y
```

> 若 conda 镜像解析不到 3.11.10，可升级到 3.11.8（无此缺陷）：
> ```bat
> conda install python=3.11.8 -y
> ```

**方案二：删除重装环境**（`environment.yml` 已更新为 `python=3.11.10`）

```bat
conda deactivate
conda env remove -n roadshow_analyzer
cd /d d:\BaiduSyncdisk\南科大博后材料\抗癌药物筛选\26年医企创业比赛\roadshow_analyzer_py
conda env create -f environment.yml
```

**验证修复是否成功**（在 Anaconda Prompt 中）：

```bat
conda activate roadshow_analyzer
python -c "import ssl; ssl.create_default_context(); print('SSL OK')"
```

出现 `SSL OK` 即修复完成。

**修复后如何打开 Spyder**：无需在新环境里再装 Spyder——直接打开您原来的 Spyder（旧环境），然后：**工具 → 偏好设置 → Python 解释器 → 使用以下解释器** → 选择 `C:\Users\shuai\.conda\envs\roadshow_analyzer\python.exe`。这样 Spyder 界面走旧环境（不受影响），而内核与程序都跑在修复后的 `roadshow_analyzer` 环境。

## 使用方式一：Anaconda Prompt 命令行运行（推荐）

### 第 1 步：激活环境

打开 **Anaconda Prompt**，输入：

```bat
conda activate roadshow_analyzer
```

如果提示 `Could not find conda environment`，说明环境尚未创建，先执行（注意 `cd /d` 跨盘符切换）：

```bat
cd /d d:\BaiduSyncdisk\南科大博后材料\抗癌药物筛选\26年医企创业比赛\roadshow_analyzer_py
conda env create -f environment.yml
conda activate roadshow_analyzer
```

（若曾遇到 3.11.9 的 ssl 报错，请先按"Spyder 打不开的专项修复"一节升级 Python。）

### 第 2 步：进入项目根目录（⚠️ 跨盘符要用 `cd /d`）

您的项目在 **D 盘**，而 Anaconda Prompt 默认停在 `C:\Users\shuai>`。直接执行 `cd d:\...` 在 Windows 里**不会切换盘符**——既无报错、提示符也不变（这是 CMD 的经典行为，看起来"没进入"）。

**正确写法（带 `/d` 的绝对路径，复制粘贴即可）：**

```bat
cd /d d:\BaiduSyncdisk\南科大博后材料\抗癌药物筛选\26年医企创业比赛
```

> 或分两步：先输 `d:` 回车，再输 `cd \BaiduSyncdisk\南科大博后材料\抗癌药物筛选\26年医企创业比赛`。
>
> 检查是否成功：输入 `cd`（不带参数）回车，应显示 `d:\BaiduSyncdisk\南科大博后材料\抗癌药物筛选\26年医企创业比赛`。

### 第 3 步：运行程序（三种方式任选）

**方式 ①：不指定目录**（扫描当前工作目录 `26年医企创业比赛` 下的全部项目文件夹）：

```bat
python roadshow_analyzer_py\main.py
```

> 注意：main.py 的"默认输入目录"是**程序运行时的当前工作目录**。因此请务必先执行第 2 步的 `cd /d` 进入项目根目录；否则它会把 Anaconda Prompt 默认的 `C:\Users\shuai` 当作输入目录。
>
> 更稳妥的做法是用**方式 ②**显式指定目录，完全不依赖 cd。

**方式 ②：指定输入目录（最稳妥，不需要 cd）**：

```bat
python "d:\BaiduSyncdisk\南科大博后材料\抗癌药物筛选\26年医企创业比赛\roadshow_analyzer_py\main.py" "d:\BaiduSyncdisk\南科大博后材料\抗癌药物筛选\26年医企创业比赛"
```

> 第一个引号内是 main.py 的绝对路径，第二个引号内是您要扫描的输入目录（替换成您实际要处理的文件夹）。这样无论当前在哪个盘符都能直接运行。

**方式 ③：双击 `roadshow_analyzer_py\run.bat`**（一键脚本，基于脚本自身位置自动定位项目根目录，**不需要手动 cd**；带参数可指定目录：`run.bat "D:\某目录"`）。

### 第 4 步：查看结果

程序结束后，输出在 **输入目录\analysis_output\** 下：

```
analysis_output\
├── 1目录.html                     ← 总览表格（用浏览器打开）
├── 项目名.html                    ← 每个项目的分析报告
└── cache\项目名.json              ← 中间结果（AI纠错全文/图片分析/点评）
```

浏览器打开 `analysis_output\1目录.html` 即可查看全部项目对比。

### 完整示例（复制可用，已处理跨盘符）

```bat
conda activate roadshow_analyzer
cd /d d:\BaiduSyncdisk\南科大博后材料\抗癌药物筛选\26年医企创业比赛
python roadshow_analyzer_py\main.py
```

> 若您想处理的是别的文件夹，把运行命令改为：
> ```bat
> python roadshow_analyzer_py\main.py "D:\要处理的目录"
> ```

---

## 使用方式二：Spyder 运行

1. 在 Spyder 中打开 `roadshow_analyzer_py/main.py`
2. **工具 → 偏好设置 → Python 解释器 → 使用以下解释器**，选择 `C:\Users\shuai\.conda\envs\roadshow_analyzer\python.exe`（确保代码跑在 roadshow_analyzer 环境里）
3. 按 **F5** 运行（默认扫描当前目录）
4. 若要处理指定目录，在 Spyder 的"运行配置"（Ctrl+F6）参数栏填写目录路径

输出目录同样为 `输入目录/analysis_output/`。

## 关键配置（config.py）

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `WHISPER_MODEL` | `large-v3` | 可切换 `small` / `base` / `medium` 加速（首次运行自动下载，支持 hf-mirror 镜像） |
| `DEEPSEEK_API_KEY` | 从环境变量 / `.env` 文件读取 | 可通过环境变量或 `.env` 文件配置 |
| `TESSERACT_CMD` | `C:\Program Files\Tesseract-OCR\tesseract.exe` | 按实际安装路径调整 |
| `TESSDATA_PREFIX` | 当前工作目录 | 指向含 `chi_sim.traineddata` 的目录 |
| `OUTPUT_DIR` | `输入目录/analysis_output` | 自动跟随输入目录 |

## ⚙️ API Key 配置（重要）

`config.py` 中的 `DEEPSEEK_API_KEY` 不再硬编码，按以下顺序读取：

1. **环境变量**（推荐）：`DEEPSEEK_API_KEY=sk-xxx`
2. **项目根目录 `.env` 文件**：在 `roadshow_analyzer_py/.env` 中写入
   ```env
   DEEPSEEK_API_KEY=sk-你的key
   ```
3. **本地 `_secrets.py` 文件**（可选，不入库）

> `.env` 和 `_secrets.py` 已在 `.gitignore` 中排除，不会上传到 GitHub，请自行在本地创建。

## 🔊 Whisper 模型下载（不用手动上传 3GB 模型）

模型文件（约 3GB）**不需要也不应该**提交到 GitHub，`models/` 目录已在 `.gitignore` 中排除。

克隆项目后首次运行 `main.py` 会自动从 HuggingFace 镜像下载模型，也可提前手动下载：

```bat
cd /d "项目路径\roadshow_analyzer_py"
python download_model.py            # 下载 large-v3（约 3GB）
python download_model.py small      # 或下载 small（约 460MB，更快）
```

> 国内网络已默认配置 `hf-mirror.com` 镜像；若不通，可换官方源：
> `python download_model.py large-v3 --endpoint https://huggingface.co`

## 中间结果

每个项目处理完成后，会在 `analysis_output/cache/{项目名}.json` 保存中间数据（纠错后全文、chunks、图片分析、点评等），便于在 Spyder 变量浏览器与文件管理器中双重检查。

## 与 JS 版差异

| 项 | JS 版 | Python 版 |
|---|---|---|
| 语音模型 | @xenova/transformers whisper-large-v3 | faster-whisper large-v3（CPU int8 量化） |
| OCR | tesseract.js | pytesseract + tesseract.exe |
| 繁简转换 | opencc-js | 由 DeepSeek 纠错提示词统一（可选安装 opencc） |
| 输出目录 | 输入目录/analysis_output/ | 同左 |
| 主要改动 | — | 新增中间结果 JSON 落盘便于排查 |