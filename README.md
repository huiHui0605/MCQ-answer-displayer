# MCQ Study · 免费本地英文题目助手

点击悬浮图标 **框选 MCQ**，拖动选择题目区域，本地 OCR 识别后由本地模型作答。结果窗口只显示：

```text
1. b
2. c
3. ?
```

不显示解释、置信度或引用。`?` 表示依据不足、模型无法确定或该题处理失败，不代表某个选项。题目、OCR 和推理均在本机；没有云端 AI 调用、API key 或按题目收费。初次安装和下载模型需要联网，完成后可以离线使用。

## Windows 安装

适合 Windows 64 位、16GB 以上内存。CPU 可运行，不要求独立显卡，但没有显卡时可能需要较长时间，无法保证秒回或每题正确。

1. 安装 [Python 3.12.10 Windows installer (64-bit)](https://www.python.org/downloads/release/python-31210/)，保留 Tcl/Tk 和 Python Launcher。OCR 依赖不支持 Python 3.13 或更新版本，无需卸载其他 Python。
2. 安装并打开 [Ollama](https://ollama.com/download/windows)，在 PowerShell 执行一次：

   ```powershell
   ollama pull qwen2.5:3b
   ```

   模型需要约数 GB 空间。不要选 cloud 模型，不需要 Ollama 账户。若命令找不到，重开终端；连接失败时打开 Ollama，或在另一个终端运行 `ollama serve` 并保持开启。
3. 下载本项目 ZIP 并解压，或使用 Git：

   ```powershell
   git clone https://github.com/huiHui0605/MCQ-answer-displayer.git
   cd MCQ-answer-displayer
   ```
4. 双击 `setup_windows.bat`，脚本明确选择 64 位 Python 3.12，在 `.venv-py312` 安装依赖，保留旧 `.venv`。
5. 把自己的 lecture note PDF 放入 `notes/`。GitHub 不包含用户提供的教材 PDF 或提取后的教材正文。
6. 保持 Ollama 在后台运行，双击 `start_windows.bat`。

手动安装/启动：

```powershell
py -3.12 -m venv .venv-py312
.\.venv-py312\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-py312\Scripts\python.exe check_setup.py
.\.venv-py312\Scripts\python.exe app.py
```

## 框选与答案

1. 在主显示器上显示完整英文题目和 A/B/C/D 选项。点击 **框选 MCQ**。
2. 屏幕会冻结显示本次截图。拖动框选**题干和全部选项**，排除浏览器菜单、侧栏、广告和其他无关内容。松开鼠标开始识别；按 **Esc** 取消。
3. 结果窗口只显示题号和小写答案。处理中显示短状态，完成后状态清空。
4. 识别不完整时重新框选，或右键悬浮图标 → **校正识别文字 / 手动粘贴**。校正框独立于答案窗口，不会默认展示。
5. 关闭答案窗口可收起；右键图标可查看答案或退出；用系统标题栏拖动。

框选单列多道题时，题号需连续且各题都有完整 A/B/C/D；支持 `1. ...`、`1) ...`、`Question 1`、`Q1:` 等格式。会保留原题号，例如框选第 5、6 题输出 `5. b`、`6. c`。无题号的单题默认显示 `1. ...`；无题号的多题或不完整批次需要校正，避免混题。不支持自动读取整页多栏题目的顺序，请每次框选一列。

手动输入示例：

```text
1. Which form of intellectual property protects an invention?
A. Patent
B. Trademark
C. Copyright
D. Franchising

2. Which term identifies a brand?
A. Patent
B. Trademark
C. Trade secret
D. Business plan
```

多题按顺序逐题推理，总时间可能较长。重复题目可命中本地缓存；在校正窗口勾选“重新推理”可绕过缓存。新扫描会替换上次结果，不是累计的历史答题记录。

## 识别与准确率

- 只对选区执行 OCR，较小选区适度放大（最多 2 倍）并添加边缘留白，保留英文大小写、NOT/EXCEPT、数字和标点，不自动改写英文题目。
- OCR 置信度检查阈值从 0.65 提高为 0.80。有低置信度文字、缺少选项、缺少题干或题号不连续时要求校正，不自动猜题。高置信度仍可能识别错误，阈值不是实际正确率。
- 相比整屏扫描，框选能排除无关内容，但尚未通过真实题目集测量准确率提升幅度。请放大网页文字；OCR 不能恢复本来不可见或模糊的内容。
- 题干和四个选项都必须在选区内，并保留 A/B/C/D 标签。模型结论仍可能出错。
- 讲义检索使用英文关键词，在本地选择最多 4 页、每页最多 1800 字符。图片和复杂表格可能提取不完整；扫描 PDF 需要预先 OCR。没有讲义依据时输出 `?`。

## 本地数据与模型

截图在内存中取得一次主屏幕图像，选择区域后只将裁剪图交给 OCR，不保存图片、不上传，不持续截屏或监听剪贴板。程序不包含隐藏或规避检测功能。OCR 使用 RapidOCR 软件包内的 ONNX 权重，不需要 Tesseract、OCR key 或额外在线识别服务；初始化 OCR 时关闭 ONNX Runtime 可选遥测。

软件只连接固定本机地址 `127.0.0.1:11434`，不使用系统代理，不跟随重定向；拒绝 cloud 名称和 Ollama 报告的远程模型。Ollama 是独立软件，下载/升级由用户控制。安装完成后可断网运行。

成功答案及引用仍在内部缓存于 `~/.mcq-study/answers.json`，答案窗口不展示引用或解释。Windows 通常位于 `C:\Users\你的用户名\.mcq-study\answers.json`。题目作为哈希键，但解释和引用可能包含题目信息。删除缓存文件可清空；`MCQ_DATA_DIR` 可改目录。替换讲义后重启会使旧缓存失效，同名模型更新后需手动清空。

默认 `qwen2.5:3b`，如内存和显卡资源足够可下载 `qwen2.5:7b` 并通过 `MCQ_MODEL` 选择；7B 可能更慢，也不保证适合所有 16GB 电脑。模型需要支持 Ollama 结构化输出。`.env.example` 仅供参考，不会自动加载。旧 `MCQ_API_KEY` 不再读取。

模型在内存中保留约 30 分钟；退出窗口后可运行 `ollama stop qwen2.5:3b` 释放。单题超时为 300 秒，超时不保证后台立即停算，避免连续重复提交。

## 升级和故障排查

已使用 Git 的用户执行 `git pull origin main`；ZIP 用户下载最新版解压，并保留/复制自己的 `notes/`。运行 `setup_windows.bat` 后再启动 `start_windows.bat`；不需要重新下载 Ollama 模型。

若提示 Python runtime not found，先安装上方链接的 Python 3.12 64 位版，再执行 `py -3.12 --version` 验证。若 pip 提示 OCR 要求 `<3.13`，不要强制忽略版本限制或只升级 pip；请使用新版脚本的 `.venv-py312`，不要沿用旧的 `.venv`。

多显示器只支持主显示器。Windows DPI 设置、远程桌面或受保护画面可能影响选择或导致黑屏。macOS 需屏幕录制权限；Linux Wayland 可能不支持当前截图方式。

macOS/Linux 需安装 Python 3.12（带 Tk）、Ollama 和模型，在图形桌面运行：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

## 验证

```powershell
.\.venv-py312\Scripts\python.exe -m unittest discover -s tests -v
```

40 项测试覆盖本地问答、缓存、引用、题目拆分、裁剪边界、小字放大、纯答案格式、单题和多题真实英文 OCR，以及模拟模型的答题流程。真实 OCR 使用生成的测试图；本机模型通信使用模拟 Ollama，不代表真实模型准确率。已验证 Python 3.12 / Windows 64 位依赖安装包可解析，Python 编译和依赖检查通过。

云端已读取用户提供的 13 份 PDF、352 页文本；没有可用图形显示器或实际 Ollama 模型，未完成新版框选窗口、真实 Windows DPI/多屏或模型推理实机验证。
