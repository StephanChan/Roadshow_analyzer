========================================================================
                        路演分析平台 使用说明书
                            （新手友好版）
========================================================================

一、这个项目是干什么的？
-----------------------------------------------------------------------
把您指定的文件夹里的"路演项目材料"（音频、PPT照片、文稿）自动分析，
生成一份份图文并茂的 HTML 报告，包括：

  1. 音频自动转成文字（中文）
  2. 识别 PPT 照片上的内容
  3. AI 帮忙纠错文字、总结每个项目的亮点和不足
  4. 分析语速、演讲时长、高频词
  5. 给项目打分（赛道、壁垒、临床、商业、团队五个方面）
  6. 最后生成一个总览页面，方便横向对比所有项目

整个过程全自动，您只需要准备好材料、运行一下程序，然后打开浏览器
看报告就行。


二、在"新电脑"上要装哪些东西？
-----------------------------------------------------------------------
归纳起来就 4 样：

  [1] Anaconda（或者已有的 Python 环境）-- 提供 Python 运行环境
  [2] Tesseract OCR 软件                 -- 用来识别图片上的文字
  [3] 这个项目的依赖包                   -- 用一条命令自动装好
  [4] DeepSeek 的 API Key                -- AI 服务要用的钥匙

下面一步步教您怎么装。


三、第 1 步：安装 Anaconda
-----------------------------------------------------------------------
目的：让电脑拥有运行 Python 程序的环境。

1. 打开浏览器，访问：https://www.anaconda.com/download
   或者在国内镜像下载：https://mirrors.tuna.tsinghua.edu.cn/anaconda/archive/
   （搜文件名带 "Windows-x86_64.exe" 的最新版本，例如
    Anaconda3-2024.xx-Windows-x86_64.exe）

2. 双击下载好的 exe 文件，一路点"下一步 / Next"。
   小提示：
   - 安装到哪都行，记住路径即可（默认 C:\Users\你的用户名\anaconda3）
   - 安装过程中如果问 "Add Anaconda3 to my PATH environment variable"，
     建议勾选（小白勾选后下一步在 cmd 里直接用 python 更省事）

3. 装完后，在"开始菜单"里找到并打开：
   "Anaconda Prompt"（这是一个黑色的命令行窗口）

4. 以后所有电脑操作，都在这个 Anaconda Prompt 里进行。


四、第 2 步：安装 Tesseract OCR（识别图片文字必需）
-----------------------------------------------------------------------
这个不是 Python 包，而是一个独立的软件，必须单独装。

1. 打开浏览器访问（Windows 版下载页）：
   https://github.com/UB-Mannheim/tesseract/wiki

2. 找一个以 "tesseract-ocr-w64-setup-5.x.x.exe" 命名的链接，下载并双击安装。

3. 安装过程中出现选择语言包的界面时：
   一定要勾选   Additional language data → Chinese (Simplified)
   （简体中文语言包，否则识别不了中文！）

4. 安装完成后，验证是否成功：
   打开 Anaconda Prompt，输入下面命令后按回车：

       tesseract --version

   如果显示出版本号（例如 tesseract v5.3.3），说明安装成功。
   如果提示"不是内部或外部命令"，请把安装目录（默认
   C:\Program Files\Tesseract-OCR）加入系统 PATH，或者在
   项目文件夹的 config.py 里手动填写 tesseract.exe 的完整路径。


五、第 3 步：把项目放到电脑上
-----------------------------------------------------------------------
您可以从 GitHub 上下载项目（推荐，能拿到最新版）：

1. 打开 https://github.com/StephanChan/Roadshow_analyzer
2. 点绿色的 "Code" 按钮 → 选 "Download ZIP" → 下载到电脑
3. 解压 ZIP，得到一个文件夹，就是项目文件夹
   （里面应该有 main.py、config.py、README.txt 等文件）

小提示：
  把项目文件夹放在一个好找的地方，比如  D:\roadshow_analyzer_py
  注意：整个路径里最好别有奇怪字符，中文路径也能用，但要保证
  记清楚这个文件夹在哪。


六、第 4 步：一键安装依赖包（二选一，推荐方式 A）
-----------------------------------------------------------------------
方式 A：用 Conda（推荐，最省心、版本最稳）

  在 Anaconda Prompt 里，先进入项目文件夹：

      cd /d D:\roadshow_analyzer_py

  （把 D:\roadshow_analyzer_py 换成您实际解压出来的项目路径；
    注意是 "cd /d 路径"，"/d" 不能省，否则跨盘符会切不过去）

  然后执行下面这条命令，自动创建环境并装好全部依赖：

      conda env create -f environment.yml

  第一次执行会下载很多东西，耐心等几分钟。完成后激活环境：

      conda activate roadshow_analyzer

  以后每次使用前，都要先执行上面这条激活命令。


方式 B：用 pip（适合已经会 Python 的朋友）

  在 Anaconda Prompt 里：

      cd /d D:\roadshow_analyzer_py
      pip install -r requirements.txt


七、第 5 步：配置 DeepSeek API Key
-----------------------------------------------------------------------
程序调用 DeepSeek 的 AI 接口需要一把"钥匙"（API Key）。
这把钥匙是花钱买的（很便宜，新账号通常有赠送额度），
请务必保管好，别泄露给别人。

1. 去 DeepSeek 开放平台申请：
   https://platform.deepseek.com/
   注册登录 → "API Keys" → 创建一个 Key（形如 sk-xxxxxxxxxxxx）

2. 在项目文件夹里新建一个文件，取名叫：
       .env
   （注意开头有个点，是半角的点）

3. 用记事本打开这个 .env，把下面内容写进去，保存：

       DEEPSEEK_API_KEY=sk-把这里换成你自己的key

   保存后，这个 .env 文件不要发给任何人、不要传到网上。
   （项目里的 .gitignore 已经保证它不会被上传到 GitHub。）

4. 验证：打开 Anaconda Prompt，进入项目文件夹后运行：

       python -c "import config; print(config.DEEPSEEK_API_KEY[:6])"

   如果显示 sk-xxxx 这样的前几位，说明配置成功。


八、第 6 步：下载语音识别模型（约 3GB，只需下载一次）
-----------------------------------------------------------------------
程序默认使用 faster-whisper large-v3 模型（中文识别效果好，约 3GB）。
模型不用上传 GitHub、也不用手动拷到别的电脑，
每台新电脑只需要自己下载一次即可。（国内已配置好镜像加速）

方式 A：提前手动下载（推荐，避免运行时突然下载）

  在 Anaconda Prompt 里，进入项目文件夹后执行：

      cd /d D:\roadshow_analyzer_py
      python download_model.py

  等待下载完成，模型会保存在项目文件夹的 models\ 目录里。

方式 B：不提前下载也行

  第一次运行 main.py 转写音频时，程序会自动下载，只是您要多等一会儿。

补充说明：
  - 如果下载很慢或失败，可以换一个小一点的模型先用着（约 460MB）：

        python download_model.py small

    然后在 config.py 里把 WHISPER_MODEL 改成 "small"，即可用这个模型。
    等以后网速好的时候，再下载 large-v3 换回来。

  - 如果 hf-mirror.com 镜像连不上，换官方源试试：

        python download_model.py large-v3 --endpoint https://huggingface.co


九、第 7 步：把要分析的材料放好
-----------------------------------------------------------------------
在您电脑上准备一个"资料文件夹"，里面每个"项目"一个子文件夹。
例如：

       D:\比赛资料\
       ├── 项目A-张伟\          （里面放 音频.mp3、PPT照片、文稿.txt）
       ├── 项目B-李娜\
       └── 项目C-王强\

程序支持三种材料，可以自由组合：
  1. 音频文件：.m4a .mp3 .wav .mp4 .aac .flac .ogg
  2. 文稿：.txt .md .doc .docx
  3. PPT 照片：.jpg .jpeg .png .gif .webp .bmp（拍的照片或截图都行）

三种模式：
  - 有音频      ：会自动转文字 + 全部分析（最完整）
  - 只有文稿    ：直接读文稿 + 全部分析（跳过转写，很快）
  - 只有照片    ：只做图片识别 + AI 图片分析


十、第 8 步：运行程序（三种方式，任选一种）
-----------------------------------------------------------------------
方式 A：双击 run.bat（最简单，小白首选）

  1. 打开项目文件夹，找到 run.bat
  2. 双击运行
  3. 默认会扫描"项目文件夹的上一级目录"（即当初解压项目时，
     项目放在哪个文件夹里，就扫描哪个文件夹下的所有子项目）。
  4. 如果想指定别的资料文件夹，可以右键 run.bat → 发送到 →
     桌面快捷方式，然后右键快捷方式 → 属性 → 目标一栏最后面
     加上 空格 + "D:\比赛资料"（带引号），保存后双击即可。
     例如目标变成：
       D:\roadshow_analyzer_py\run.bat "D:\比赛资料"
  5. 或者直接用下面的"方式 B"命令行来指定文件夹，更直观。


方式 B：在 Anaconda Prompt 里用命令行

  1. 打开 Anaconda Prompt
  2. 激活环境（如果之前没激活）：

       conda activate roadshow_analyzer

  3. 运行程序，指定资料文件夹（推荐这种写法，最稳）：

       python "D:\roadshow_analyzer_py\main.py" "D:\比赛资料"

     第一个引号里是 main.py 的完整路径；
     第二个引号里是您资料文件夹的路径。


方式 C：用 Spyder（适合想边看代码边跑的）

  1. 打开 Spyder（开始菜单里搜 Spyder）
  2. 打开项目里的 main.py
  3. 菜单：工具 → 偏好设置 → Python 解释器 → 使用以下解释器
     选择  C:\Users\你的用户名\.conda\envs\roadshow_analyzer\python.exe
  4. 按 F5 运行（或在运行配置里填资料文件夹路径）


十一、结果在哪里看？
-----------------------------------------------------------------------
程序运行完后，会在您的"资料文件夹"下生成一个 analysis_output 文件夹：

      D:\比赛资料\analysis_output\
      ├── 1目录.html        ← 总览页（所有项目对比表，最重要）
      ├── 项目A.html        ← 每个项目单独的报告
      └── cache\            ← 中间结果（可忽略）

双击 1目录.html，用浏览器打开，就能看到全部项目的横向对比了。


十二、常见问题排查
-----------------------------------------------------------------------
问：提示 "conda" 不是内部或外部命令？
答：说明您没装 Anaconda，或者没在"Anaconda Prompt"里操作。
   请在开始菜单里打开 Anaconda Prompt 再试。

问：提示 "没有这个环境 roadshow_analyzer"？
答：先执行创建环境的命令：
      conda env create -f environment.yml
   创建完成后才能 conda activate。

问：提示 "ModuleNotFoundError: No module named 'faster_whisper'"？
答：依赖没装好。重新激活环境：
      conda activate roadshow_analyzer
   然后再  pip install faster-whisper  试试。

问：提示 "TesseractNotFoundError" 或 "tesseract 找不到"？
答：第四步的 Tesseract OCR 软件没装，或不在默认位置。
   重装 Tesseract，或在 config.py 里填写你实际的
   tesseract.exe 完整路径。

问：提示 "模型下载超时/失败"？
答：网络问题。重试一次；或改用 small 模型：
      python download_model.py small
   然后在 config.py 里把 WHISPER_MODEL 改成 "small"。
   如果 hf-mirror 不通，用官方源：
      python download_model.py large-v3 --endpoint https://huggingface.co

问：提示 "API Key 为空 / 401 错误"？
答：.env 文件没创建好，或 Key 没填对。
   重新按"第七步"检查：
     1) 项目文件夹里有 .env 文件
     2) 里面内容形如  DEEPSEEK_API_KEY=sk-你的key
     3) Key 前后没有多余空格

问：程序闪一下就没了（双击 run.bat 时）？
答：程序报错后窗口自动关闭了。改用手动方式运行（方式 B），
   错误信息会留在窗口里，把提示内容发给我看。


十三、给新手的整体流程一句话总结
-----------------------------------------------------------------------
  装 Anaconda → 装 Tesseract OCR → 下载项目 → 创建环境
  → 填好 .env 里的 Key → 下载模型 → 放好资料 → 双击 run.bat
  → 打开 analysis_output\1目录.html 看结果

祝使用顺利！
========================================================================