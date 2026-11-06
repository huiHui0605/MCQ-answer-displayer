# MCQ Study · 免费本地讲义练习助手

Windows 桌面悬浮小窗口。点击 **MCQ** 展开，粘贴题目和分行 A/B/C/D 选项，显示答案、解释及 PDF 原文页码。再次点击收起；用标题栏拖动，关闭主窗口退出。

**没有云端 AI 调用，没有 API key，也没有按题目收费。** 本地 Ollama 加载 Qwen2.5 3B 推理，讲义检索和缓存也在本机。程序只向 `127.0.0.1:11434` 发送本机请求，不使用系统代理、不跟随重定向；云端模型名称和 Ollama 报告的远程模型会被拒绝。初次安装软件、Python 依赖和下载模型需要联网，下载完成后可断网使用。需要自行提供电脑、存储空间和电力。

默认针对 Windows、16GB 以上内存，不要求独立显卡。CPU 也可运行，但首次加载或推理可能需要几十秒至数分钟；无法保证秒回或每题正确。相同题目命中缓存时通常更快。

## Windows 安装

1. 安装 [Python 3.12](https://www.python.org/downloads/)（保留 Tcl/Tk 和 Python Launcher 组件）和 [Ollama Windows 版](https://ollama.com/download/windows)。若用 Git 克隆，也要安装 Git；不想安装 Git 可在 GitHub 点击 **Code → Download ZIP** 后解压。
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
4. 双击 `setup_windows.bat` 安装 Python 依赖。
5. 把你自己的 lecture note PDF 复制到项目的 `notes` 文件夹。GitHub **不包含教材 PDF 或提取后的教材正文**；云端用于验证的 13 份文件仍保留在本地，未上传。
6. 双击 `start_windows.bat`。它先检查 PDF 文本和本机模型，成功后打开悬浮窗口。不需要填写任何 key。

若希望手动安装和启动，使用：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe check_setup.py
.\.venv\Scripts\python.exe app.py
```

每次启动时都需要 Ollama 后台在运行，但不需要重新下载模型。`check_setup.py` 只检查文件和模型，不验证推理准确率。

## 使用

粘贴完整题目，选项各占一行，例如：

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
- 本工具没有录屏、自动读屏、剪贴板监听或隐藏/规避检测功能。

## 模型与本地数据

默认 `qwen2.5:3b` 是速度、内存和能力的折中。若你愿意等待更久且内存充足，可先下载 `ollama pull qwen2.5:7b`，再在 PowerShell 中设置：

```powershell
$env:MCQ_MODEL = "qwen2.5:7b"
.\.venv\Scripts\python.exe app.py
```

7B 不保证适合所有 16GB 电脑；显卡显存、其他程序和上下文都会影响性能。保持 3B 是默认建议。不要设置远程模型或 cloud 模型。更换其他模型需要支持 Ollama 的结构化 JSON 输出。`.env.example` 仅供参考，程序不自动加载 `.env`。

成功答案与引用缓存于 `~/.mcq-study/answers.json`；Windows 通常在 `C:\Users\你的用户名\.mcq-study\answers.json`。删除文件可清空；`MCQ_DATA_DIR` 可改变目录。题目只作为哈希键保存，但解释和引用可能包含题目信息。旧云端版本缓存不会复用。替换讲义后重启会自动使旧讲义缓存失效；同名模型更新后请手动清空缓存。

如曾设置 `MCQ_API_KEY`，新版不会读取，可自行从系统环境变量中删除。程序不下载模型、不请求互联网服务、不上传题目；Ollama 是独立软件，其升级或模型下载由你控制。可在完成安装后断网运行。

## macOS / Linux

安装对应版本的 Ollama 并下载 `qwen2.5:3b`。macOS 建议安装 python.org 的 Python（包含 Tk）；Linux 需要图形桌面和与你的 Python 匹配的 Tk/venv 包，例如 `python3-tk python3-venv`。在项目目录执行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
# 把 PDF 复制到 notes 后：
.venv/bin/python check_setup.py
.venv/bin/python app.py
```

## 验证与限制

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

14 项自动测试覆盖检索、输入、缓存/刷新/讲义变更、引用、低置信度、模型缺失、云端模型拒绝、超时、截断及本机 HTTP 通信。通信测试使用本机模拟 Ollama，不下载模型、不发外部请求，不能代表真实模型准确率。

开发云端已用用户提供的 13 份 PDF 提取出 352 个文本页面。云端未安装 Ollama，也没有可用图形显示器，未完成真实模型推理或桌面交互验证；Windows 安装脚本尚未在 Windows 上实测。模型的速度、准确率和你的电脑兼容性需要在本机验证。Python 编译检查和依赖检查也已通过。
