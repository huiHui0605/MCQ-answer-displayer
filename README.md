# MCQ Study · 免费本地讲义练习助手

Windows 桌面悬浮小窗口。点击 **扫描 MCQ**，截取一次当前主屏幕，在本机 OCR 识别题干和 A/B/C/D 选项，然后自动显示答案、解释及 PDF 原文页码。点击结果窗口的“收起”按钮可收起；右键图标可查看结果、手动粘贴或退出，用系统标题栏拖动。

**没有云端 AI 调用，没有 API key，也没有按题目收费。** 本地 Ollama 加载 Qwen2.5 3B 推理，讲义检索和缓存也在本机。程序只向 `127.0.0.1:11434` 发送本机请求，不使用系统代理、不跟随重定向；云端模型名称和 Ollama 报告的远程模型会被拒绝。初次安装软件、Python 依赖和下载模型需要联网，下载完成后可断网使用。OCR 使用 RapidOCR 包内附带的 ONNX 权重，无需额外 OCR key、Tesseract 或在线识别服务；ONNX Runtime 的可选遥测在创建 OCR 引擎前显式关闭。需要自行提供电脑、存储空间和电力。

默认针对 Windows、16GB 以上内存，不要求独立显卡。CPU 也可运行，但首次加载或推理可能需要几十秒至数分钟；无法保证秒回或每题正确。相同题目命中缓存时通常更快。

## Windows 安装

1. 安装 [Python 3.12.10 的 Windows installer (64-bit)](https://www.python.org/downloads/release/python-31210/)（保留 Tcl/Tk 和 Python Launcher 组件；OCR 依赖要求 Python < 3.13，不能使用 3.13/3.14 或更新版本）和 [Ollama Windows 版](https://ollama.com/download/windows)。若用 Git 克隆，也要安装 Git；不想安装 Git 可在 GitHub 点击 **Code → Download ZIP** 后解压。
2. 打开 Ollama 应用，确保它在后台运行。在 PowerShell 执行一次模型下载：

   ```powershell
   ollama pull qwen2.5:3b
   ```

   模型需要约数 GB 磁盘空间。不要选择带 `cloud` 的模型；无需登录 Ollama 账户。若命令未找到，重开 PowerShell；若连不上本机服务，打开 Ollama，或在单独终端运行 `ollama serve` 并保持该终端开启。
3. 获取本项目：

   ```powershell
   git clone https://github.com/huiHui0605/MCQ-answer-displayer.git
   cd MCQ-answer-displayer
   ```

   已经克隆的用户在项目目录执行 `git pull origin main`。下载 ZIP 的用户直接打开解压后的项目目录。
4. 双击 `setup_windows.bat`。脚本明确选择 64 位 Python 3.12，并在 `.venv-py312` 中安装依赖；会保留旧的 `.venv`，无需卸载其他 Python 版本。
5. 把你自己的 lecture note PDF 复制到项目的 `notes` 文件夹。GitHub **不包含教材 PDF 或提取后的教材正文**；云端用于验证的 13 份文件仍保留在本地，未上传。
6. 双击 `start_windows.bat`。它先检查 PDF 文本和本机模型，成功后打开悬浮窗口。不需要填写任何 key。

若希望手动安装和启动，使用：

```powershell
py -3.12 -m venv .venv-py312
.\.venv-py312\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-py312\Scripts\python.exe check_setup.py
.\.venv-py312\Scripts\python.exe app.py
```

每次启动时都需要 Ollama 后台在运行，但不需要重新下载模型。`check_setup.py` 只检查文件和模型，不验证推理准确率。

## 一键扫描当前画面

1. 将**一道题及完整 A/B/C/D 选项**清晰显示在 Windows 的主屏幕（系统设置中的主显示器）上，建议放大文字，避免同时出现多道题。
2. 等悬浮图标由“准备中”变成“扫描 MCQ”，单击一次。
3. 程序会短暂收起自己的窗口（约 0.3 秒，避免挡住题目），截取一次主屏幕，随即恢复窗口并显示“正在本地识别文字”。没有持续截屏或定时扫描。
4. OCR 识别到唯一完整的 A/B/C/D 选项后，自动检索讲义、调用本地模型并显示结果，无需再点击答题按钮。
5. 选项缺失、出现多组 A/B/C/D 或 OCR 置信度较低时，会显示识别文字和提示。校正后点击“显示答案”；也可以点击“重新扫描”。即使自动识别成功，也应核对题干、NOT/EXCEPT、数字和选项。

截图仅保留在内存供 OCR 处理，不写入图片文件，不上传；文字识别和推理均在本机完成。识别文字会出现在窗口中，成功答案和引用按下述规则缓存。OCR 仍可能在高置信度下识别错误，检测通过不代表题目一定识别正确。没有额外的 OCR 识别费用。

多显示器时只扫描主屏幕，不跟随鼠标；先把题目移到主屏幕。屏幕受保护、远程桌面、系统权限、过小字体或复杂排版可能导致黑屏或识别失败。Linux Wayland 可能不支持该截屏方式，macOS 需要给运行 Python 的终端/应用屏幕录制权限。

右键悬浮图标 → **查看结果 / 手动粘贴** 仍可手动输入，例如：

```text
Which form of intellectual property protects an invention?
A. Patent
B. Trademark
C. Copyright
D. Franchising
```

点击“显示答案”。程序本地检索最多 4 页、每页最多 1800 字符，再让模型检查各选项（包括 NOT/EXCEPT）。显示答案、中文解释和讲义原文；PDF 页码按文件实际页序计算。`?` 表示证据不足或低置信度，请自行核对。

- 无相关文本时直接显示 `?`，不调用模型。英文关键词匹配英文讲义效果较好；纯中文题目可能检索不到相关内容。
- 只支持带文本的 PDF，扫描件先进行 OCR。图片和复杂表格可能提取不完整。
- 置信度是模型自评，不是正确率；引用编号有效不等于推理正确。小模型更容易在复杂、否定或模糊题目上出错。
- 相同题目、模型名、讲义内容使用缓存；勾选“重新推理”绕过缓存。不确定答案不缓存。模型在内存中保留约 30 分钟以减少再次加载；退出窗口后 Ollama 可能继续占用内存，可执行 `ollama stop qwen2.5:3b` 释放。
- 单次本地推理超时为 300 秒。超时不一定让 Ollama 立即停止后台运算，避免连续重复提交。没有保证响应时间。
- 本工具只在用户点击时截取一次画面并识别文字，不持续录屏、不监听剪贴板，也不包含隐藏/规避检测功能。

## 模型与本地数据

默认 `qwen2.5:3b` 是速度、内存和能力的折中。若你愿意等待更久且内存充足，可先下载 `ollama pull qwen2.5:7b`，再在 PowerShell 中设置：

```powershell
$env:MCQ_MODEL = "qwen2.5:7b"
.\.venv-py312\Scripts\python.exe app.py
```

7B 不保证适合所有 16GB 电脑；显卡显存、其他程序和上下文都会影响性能。保持 3B 是默认建议。不要设置远程模型或 cloud 模型。更换其他模型需要支持 Ollama 的结构化 JSON 输出。`.env.example` 仅供参考，程序不自动加载 `.env`。

成功答案与引用缓存于 `~/.mcq-study/answers.json`；Windows 通常在 `C:\Users\你的用户名\.mcq-study\answers.json`。删除文件可清空；`MCQ_DATA_DIR` 可改变目录。题目只作为哈希键保存，但解释和引用可能包含题目信息。旧云端版本缓存不会复用。替换讲义后重启会自动使旧讲义缓存失效；同名模型更新后请手动清空缓存。

如曾设置 `MCQ_API_KEY`，新版不会读取，可自行从系统环境变量中删除。程序不下载模型、不请求互联网服务、不上传题目；Ollama 是独立软件，其升级或模型下载由你控制。可在完成安装后断网运行。

## macOS / Linux

安装对应版本的 Ollama 并下载 `qwen2.5:3b`。macOS 建议安装 python.org 的 Python 3.12（包含 Tk）；Linux 需要图形桌面和与你的 Python 匹配的 Tk/venv 包，例如 `python3-tk python3-venv`。在项目目录执行：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# 把 PDF 复制到 notes 后：
.venv/bin/python check_setup.py
.venv/bin/python app.py
```

## 验证与限制

```powershell
.\.venv-py312\Scripts\python.exe -m unittest discover -s tests -v
```

27 项自动测试覆盖原有本地问答流程、选项识别（含同行及分离标签）、多道题/缺失题干/空选项拒绝、低置信度处理、截屏失败、主屏幕选择与颜色通道，以及真实离线 OCR → 题目提取 → 模拟模型答题流程。OCR 测试使用程序生成的测试图片和真实附带权重；本机通信测试使用模拟 Ollama，不能代表真实模型准确率。

开发云端已用用户提供的 13 份 PDF 提取出 352 个文本页面，并用真实 OCR 成功识别生成的英文 MCQ 图片。云端未安装 Ollama，也没有可用图形显示器，未完成真实桌面截屏、窗口交互或模型推理验证；Windows 安装脚本尚未在 Windows 上实测。模型的速度、准确率和你的电脑兼容性需要在本机验证。Python 编译检查和依赖检查也已通过。

## 从旧版升级

在项目目录执行 `git pull origin main`（或重新下载 ZIP），然后重新运行 `setup_windows.bat` 安装新增的截屏和本地 OCR 依赖，最后启动 `start_windows.bat`。保留 `notes/` 中的 PDF 和已下载的 Ollama 模型，无需重新下载。

## 修复 Python 版本安装错误

如果 pip 提示 `rapidocr-onnxruntime==1.4.4` 要求 `Requires-Python >=3.6,<3.13` 且 `No matching distribution found`，通常是旧脚本的 `py -3` 选择了较新的 Python。升级 pip 不能修复这个版本限制，也不要用 `--ignore-requires-python` 强装。

安装上文链接的 **Python 3.12.10 64 位版**，获取本项目最新代码，重新运行 `setup_windows.bat`，再运行 `start_windows.bat`。新版使用独立的 `.venv-py312`，保留旧 `.venv`、`notes/` 和已下载的 Ollama 模型。下载 ZIP 的用户请确保在新版项目目录里操作，把原来的 PDF 复制到新版 `notes/`。

可以在 PowerShell 执行 `py -3.12 --version` 确认已安装。若仍显示找不到 Python 3.12，检查是否安装了 3.12 的 Python Launcher 组件，并重新打开终端。Windows 脚本已加入版本、64 位架构检查和具体失败提示，但尚未在真实 Windows 系统执行验证。
