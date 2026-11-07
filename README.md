# MCQ Study · 本地圆形悬浮答题助手

**圆形图标 → 点击自动扫描屏幕中的英文 MCQ → 显示答案 → 点击答案回到圆形图标**，可重复操作。无需每次框选。

结果只显示：

```text
1. b
2. c
3. ?
```

不显示解释、置信度或引用。`?` 表示识别不可靠、依据不足、两次判断冲突或处理失败，不能视为某个选项。

没有云端 AI 调用、API key 或按题收费。OCR、讲义检索和模型推理都在本机；初次安装和下载模型需要联网，之后可离线运行。软件不能保证每题正确。

## Windows 安装

适用于 Windows 64 位、16GB 以上内存。默认 Qwen2.5 3B；没有独立显卡也能使用，但 CPU 推理可能需要数分钟。

1. 安装 [Python 3.12.10 Windows installer (64-bit)](https://www.python.org/downloads/release/python-31210/)，保留 Tcl/Tk 和 Python Launcher。OCR 依赖不支持 Python 3.13 及更新版本，无需卸载其他 Python。
2. 安装并打开 [Ollama](https://ollama.com/download/windows)。在 PowerShell 下载一次模型：

   ```powershell
   ollama pull qwen2.5:3b
   ```

   模型占用约数 GB 磁盘空间。不要选择 cloud 模型，无需 Ollama 账户。命令不存在时重开终端；连接失败时打开 Ollama，或在另一个终端执行 `ollama serve` 并保持开启。
3. 下载本项目 ZIP 解压，或克隆：

   ```powershell
   git clone https://github.com/huiHui0605/MCQ-answer-displayer.git
   cd MCQ-answer-displayer
   ```
4. 双击 `setup_windows.bat`。脚本明确选择 64 位 Python 3.12，并在 `.venv-py312` 安装依赖，保留旧 `.venv`。
5. 将自己的 lecture note PDF 放入 `notes/`。GitHub 不包含上传的教材 PDF 或提取后的正文。
6. 保持 Ollama 后台运行，双击 `start_windows.bat`。

手动启动：

```powershell
py -3.12 -m venv .venv-py312
.\.venv-py312\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-py312\Scripts\python.exe check_setup.py
.\.venv-py312\Scripts\python.exe app.py
```

## 使用循环

1. 将完整英文题干和 A/B/C/D 选项显示在**主显示器**上，尽量放大文字。
2. 圆形图标从 `…` 变成 `MCQ` 后，单击一次。程序短暂移开自己的窗口，取得一次截图；不持续或定时扫描。
3. 程序先从 OCR 文本框中定位常见 MCQ 题块，再裁剪、放大并重新识别；整个过程无需拖动框选。
4. 显示 `1. b` 等简短答案。**单击答案区域**即可收回圆形图标；再次点击图标开始新一轮。题目很多时可用鼠标滚轮查看答案。
5. 按住圆形图标或答案区域拖动可移动位置；拖动不会开始扫描。右键可查看上次答案、校正文字、查看最近错误或退出。

扫描时图标显示 `OCR…`，推理时显示 `AI…` 或进度，忙碌期间点击不会重复发起任务。遇到无法定位的画面或运行错误，只显示 `?`，点击同样回到图标；详细错误可通过右键菜单查看。

多个可分开的题块会保留题号；无题号单题默认编号 1。自动定位主要面向**单列、完整、带 A/B/C/D 标签**的英文题目，支持常见纵向选项和同一行的选项。多栏、无字母的单选按钮、图表题、部分选项在屏幕外、特殊排版或低清晰度画面可能无法正确定位。

校正/手动输入示例：

```text
1. Which form of intellectual property protects an invention?
A. Patent
B. Trademark
C. Copyright
D. Franchising
```

自动识别不是完整的页面语义解析器。即使返回答案，也应核对原题；不要把 `?` 当成某个选项。每次新扫描替换上次结果，不累积题目历史。

## 本版的准确性检查

- **自动定位 + 两遍 OCR**：先定位题块，再在裁剪图上放大复读。两遍识别的单词、数字和否定词需一致，相关文字的 OCR 置信度需达到 0.80；不一致的题目显示 `?`。这会更保守，也可能将可读题目标成未知。
- **清理 PDF 页脚**：检索时去除固定版权声明和幻灯片页码，保留真正讨论版权保护的正文。减少干扰项和模板词的影响，加重题干中有区分度的关键词。
- **讲义原文核验**：模型必须引用本次实际提供的讲义片段中的原文；伪造、缺失或来自未提供段落的引文不接受。
- **选项换序复核**：首次有明确答案时，再发起一个全新的本地请求，反转四个选项的顺序，不把首次答案告诉模型。映射回原选项后不一致则显示 `?`。
- 两次作答来自同一个模型，不是两个独立权威；原文存在也不证明其支持结论，模型可能两次都错。未测量真实题库准确率或提升百分比。

本版通常需要两遍 OCR 和每题两次模型推理，比原来的单次方案更慢。不能同时保证最高准确率和秒回。无依据、低置信度、冲突或 OCR 不稳定的结果不缓存。重复且已核验的题目可以命中本地缓存。

## 本地数据与模型

截图只保留在内存，不保存图片、不上传。OCR 使用 RapidOCR 包内附带的 ONNX 权重，不需要 Tesseract、OCR key 或在线识别服务；初始化时关闭 ONNX Runtime 可选遥测。没有持续录屏、剪贴板监听或规避检测功能。圆形透明背景针对 Windows 实现；其他系统可能显示方形背景。

只连接固定本机地址 `127.0.0.1:11434`，不使用系统代理、不跟随重定向，拒绝 cloud 名称及 Ollama 报告的远程模型。Ollama 是独立软件，下载和升级由用户控制。

成功答案及内部引文缓存于 `~/.mcq-study/answers.json`，Windows 通常是 `C:\Users\你的用户名\.mcq-study\answers.json`。界面不显示内部解释或引用。题目作为哈希键保存，但解释和引文可能包含题目信息。删除文件可清空，`MCQ_DATA_DIR` 可改位置。本版不复用旧单次推理版本的缓存。替换讲义后重启使旧讲义缓存失效，同名模型更新后请手动清空缓存。

默认 `qwen2.5:3b`。如果内存、显卡和等待时间允许，可下载 `qwen2.5:7b`，再通过 `MCQ_MODEL` 环境变量选择，但不会自动下载或切换，7B 也不保证每题正确，且可能更慢。不保证所有 16GB 电脑都适合 7B。模型必须支持 Ollama 结构化 JSON 输出。

`.env.example` 仅供参考，不会自动加载。旧 `MCQ_API_KEY` 不再读取。模型约保留内存 30 分钟；退出后可执行 `ollama stop qwen2.5:3b` 释放。每次推理请求超时 300 秒，一题的两次请求可能合计更久；超时不保证后台立刻停止计算。

讲义需是可提取文本的 PDF；扫描件先 OCR。图片和复杂表格可能提取不完整。检索仍是英文关键词匹配，每题提供最多 4 页、每页最多 1800 字符，不是对全部讲义的完整理解。

## 升级与故障排查

更新代码后直接运行 `start_windows.bat`，本版未新增依赖。不需要重新下载 Ollama 模型；保留自己的 `notes/` 和 `.venv-py312`。ZIP 用户更新时注意不要丢失原来的 PDF 和虚拟环境。

如果 Python runtime not found，先安装上面的 Python 3.12 64 位版本，执行 `py -3.12 --version` 验证。如果 pip 提示 OCR 需要 `<3.13`，不要忽略版本限制或只升级 pip，请使用新版安装脚本。

Windows DPI、远程桌面、受保护窗口可能影响截屏或导致黑屏。多显示器只扫描主显示器。macOS 需要屏幕录制权限；Linux Wayland 可能不支持当前截屏方式。其他桌面的透明窗口外观可能与 Windows 不同。

macOS/Linux 需 Python 3.12（带 Tk）、图形桌面、Ollama 和模型：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

## 验证

```powershell
.\.venv-py312\Scripts\python.exe -m unittest discover -s tests -v
```

64 项测试涵盖真实英文图片的自动定位和两遍 OCR、排除导航/提交按钮、保留换行选项、OCR 冲突、原文核验、选项换序冲突、检索、缓存和圆形图标循环处理。UI 测试通过模拟 Tk 绘制调用来测试真实事件处理函数，不是 Windows 屏幕实测；模型推理使用模拟 Ollama。

云端已用用户提供的 13 份 PDF 读取 352 个文本页，并验证 Python 3.12 / Windows 64 位依赖包可解析。没有实际 Ollama 模型，当前未提供桌面控制工具，也没有可用图形显示器，因此尚未完成 Windows 圆形透明效果、实际拖动/多屏和真实模型准确率/延迟验证。代码编译和依赖检查通过，测试不能替代本机验证。
