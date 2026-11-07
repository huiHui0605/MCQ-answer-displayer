# MCQ Study · 免费本地圆形悬浮助手

**点击圆形图标 → 扫描 → 显示简短答案 → 点击答案回到图标**。A/B/C/D 题显示 `1. b`；单道 True/False 题只显示 `T` 或 `F`。多题可以混合：

```text
1. b
2. T
3. F
4. ?
```

没有任何答案解释、置信度或引用出现在结果窗口。`?` 表示识别不可靠、依据不足或核验不一致，不代表某个选项。完全本地推理，无云端 API、无 key、无按次费用。初次安装和下载模型需要联网，之后可离线使用。

## Windows 安装 / 更新

需要 64 位 Windows、Python 3.12 和 Ollama。16GB 以上内存可尝试默认 3B 模型；CPU 能运行，但可能需要数分钟，不能保证秒回或每题正确。

1. 安装 [Python 3.12.10 的 Windows installer (64-bit)](https://www.python.org/downloads/release/python-31210/)，保留 Tcl/Tk 和 Python Launcher。OCR 依赖不支持 Python 3.13 及更新版本，不用卸载其他 Python。
2. 安装并打开 [Ollama](https://ollama.com/download/windows)，在 PowerShell 下载本地模型：

   ```powershell
   ollama pull qwen2.5:3b
   ```

3. 下载项目 ZIP 解压，或克隆：

   ```powershell
   git clone https://github.com/huiHui0605/MCQ-answer-displayer.git
   cd MCQ-answer-displayer
   ```

4. 双击 `setup_windows.bat`，依赖安装到独立的 `.venv-py312`，保留旧 `.venv`。
5. 将自己的 lecture note PDF 放入 `notes/`。仓库不包含教材 PDF、提取后的正文或截图。
6. 保持 Ollama 在后台运行，双击 `start_windows.bat`。

已有用户更新代码即可，**本版无新增依赖**。保留 `notes/` 和 `.venv-py312`；无需重新下载 3B 模型。首次升级需要重新提取讲义与比较表，可能多等一会儿，之后会复用本地索引。

手动安装 / 启动：

```powershell
py -3.12 -m venv .venv-py312
.\.venv-py312\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-py312\Scripts\python.exe check_setup.py
.\.venv-py312\Scripts\python.exe app.py
```

## 解决整页扫描漏题：设置一次题目区域

如果题目页面有菜单、侧栏、多个栏目或较小字体，建议：

1. 右键圆形图标 → **设置题目区域（记住）**。
2. 拖动框住完整题干和全部选项，排除菜单和广告，松开后立即扫描。Esc 可取消。
3. **以后直接点击圆形图标即可扫描同一区域**，不用每次框选；重启后也会记住。
4. 浏览器窗口移动、页面布局变化时重新设置区域；显示器分辨率变化会要求重设。
5. 想恢复整页自动定位：右键 → **清除选区，恢复整屏**。

固定区域不需要先猜题目位置，因此能避开部分整页定位失败；它不是跟踪网页元素的位置。保持窗口与题目区域的位置稳定，题干和选项必须完整可见。截屏无法可靠判断屏幕外是否还有选项。

未设区域时仍会自动扫描**主显示器**。新版按列建立 A/B/C/D 题块，避免双栏选项互相混合；常见双栏和 True/False 布局已用生成的英文图片测试。复杂排版、图片题、未标注选项或 OCR 合并了两列的文字仍可能失败。

## True / False

支持完整题干后显示 `True` 和 `False` 的选项，也支持 `A. True / B. False`、反向排列或 `T. True / F. False`。会按语义显示 T/F，不显示 A/B。

```text
A patent protects an invention.
True
False
```

单题结果为 `T` 或 `F`；有题号的多题混合结果会保留题号，如 `2. F`。只出现 True/False 标题、没有完整题干或选项的画面可能无法识别。四选项题中如果 True 和 False 只是其中两个干扰项，仍按 A/B/C/D 处理。

## 操作与校正

- 图标出现 `MCQ` 后单击扫描；处理中显示 `OCR…`、`AI…` 或进度，不重复发起任务。
- 单击答案收回圆形图标；按住拖动可移动，拖动不会触发扫描。很多答案时可滚轮查看。
- 右键 → **校正识别文字 / 手动输入**，可查看识别出的实际题目并改正后答题；识别完全失败时显示原始 OCR 文本以供校正。
- 右键 → **查看最近错误** 可查看模型未下载、截屏失败等具体原因；默认结果仍只显示 `?`。
- 右键退出。新扫描替换上一轮结果，不累计答题历史。

只有手动编辑时需要完整选项，例如：

```text
1. Which protects an invention?
A. Patent
B. Trademark
C. Copyright
D. Franchising

2. A patent protects an invention.
True
False
```

## 准确性修复与局限

- 两遍 OCR 允许普通英文空格的合并/分开，避免 `can generate` 与 `cangenerate` 被一律判为失败；仍检查字符、NOT/EXCEPT 等关键词和数字/小数差异。空格容错本身也不保证语义正确。
- 清理固定版权页脚，保留实际讨论版权的正文。检索加重题干关键词，长页改为挑选相关片段，不再始终截取页面开头。
- 对能检测到、具有明确行列标题的比较表，保留各列标题与单元格的对应关系，减少平铺文本串列。不是所有 PDF 表格都能提取，图片和复杂表格仍可能丢失内容。
- 模型必须返回能在提供的讲义片段中找到的原文，且两次判断均自评为 high 才接受；medium/low、原文缺失、冲突显示 `?`。自评不是实际正确率。
- 普通 MCQ 反转选项后重新作答，检查一致性。含 “All/None of the above” 或 “A and C” 等位置引用的选项会保留顺序复核，避免换序改变题意；True/False 同样保留语义和顺序复核。
- 两次推理使用同一模型，可能两次都错；原文存在也不能证明它支持结论。没有真实错题样本的情况下，尚未测量真实题库准确率或提升百分比。

这些检查更保守，会输出更多 `?`，也比单次作答慢。请先核对 OCR 文字，再判断是否是模型推理或讲义检索出错。

## 可选更大模型

3B 模型的能力有限，不能通过增加提示词保证正确。如果愿意占用更多内存和等待时间，可以在 PowerShell 执行：

```powershell
ollama pull qwen2.5:7b
```

下载后右键图标 → **本地模型 → qwen2.5:7b**。软件只检查已下载模型，不会自动下载。选择成功后记住设置，启动检查也使用已选模型。7B 不保证更准，16GB 电脑可能较慢或内存不足；可切回 3B。不要选择 cloud 模型。

没有菜单设置时使用 `MCQ_MODEL` 环境变量或默认 `qwen2.5:3b`；保存的菜单选择优先。`.env.example` 仅供参考，不会自动加载，旧 `MCQ_API_KEY` 已不再读取。

## 本地数据

仅在用户点击时取得一次主屏幕截图，在内存裁剪和 OCR，不保存图片、不上传、不持续录屏、不监听剪贴板。RapidOCR 使用包内 ONNX 权重，初始化时关闭可选遥测。不需要 Tesseract 或 OCR key。

只连接固定本机地址 `127.0.0.1:11434`，不用系统代理、不跟随重定向，拒绝 cloud 名称和 Ollama 报告的远程模型。Ollama 是独立软件，其下载和升级由用户控制。

本地数据目录默认 `~/.mcq-study/`，Windows 通常是 `C:\Users\你的用户名\.mcq-study\`，可用 `MCQ_DATA_DIR` 修改：

- `settings.json`：模型名、选区坐标与分辨率，不包含题目或截图。
- `lecture-index.json`：从 PDF 提取的讲义正文，含表格整理结果。PDF 改动会自动重新建立索引，删除文件也可重建。
- `answers.json`：已核验答案及内部引用，结果窗口不显示解释或引用。题目作为哈希键保存，但内部解释和引用可能包含题目信息。删除文件可清空。本版不复用旧版答案缓存；同名模型更新后请手动清空。

讲义需为可提取文本的 PDF，扫描件先 OCR。每题提供最多 4 个页面片段、每个最多 1800 字符，仍是关键词检索而非对整套讲义的完整理解。

模型保留内存约 30 分钟；退出后可执行 `ollama stop qwen2.5:3b`（或所选模型名）释放。单次推理超时 300 秒，每题最多两次；超时不保证后台立即停止计算。

## 故障排查与其他系统

Python runtime not found：安装上方 Python 3.12 64 位版，执行 `py -3.12 --version` 验证。不要用 3.13+ 强装 OCR，也不必卸载其他 Python。

Ollama 连接失败：打开 Ollama 或在另一终端运行 `ollama serve`。提示模型不存在时下载所选模型。Windows DPI、远程桌面或受保护窗口可能影响截屏；主显示器之外的屏幕不扫描。

macOS/Linux 需 Python 3.12（带 Tk）、图形桌面、Ollama 与本地模型：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

macOS 需屏幕录制权限，Linux Wayland 可能不支持当前截图方式。圆形透明背景针对 Windows，其他系统可能显示方形背景。

## 验证

```powershell
.\.venv-py312\Scripts\python.exe -m unittest discover -s tests -v
```

90 项自动测试覆盖真实 OCR 图片、双栏定位、True/False、单题 T/F 与混合输出、选区复用、模型设置、表格列对应、讲义索引缓存、OCR 空格/否定词/数字检查、检索及核验。模型测试使用模拟 Ollama，UI 测试模拟 Tk 绘制调用；不能据此宣称真实答题准确率。

云端实际读取 13 份 PDF、352 页文本，并验证了讲义中比较表的列对应。编译和依赖检查通过；没有真实 Ollama 推理或 Windows 窗口/DPI/拖动实机测试。
