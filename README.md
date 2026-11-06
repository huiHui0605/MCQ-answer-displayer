# MCQ Study · BBMK3113 讲义练习助手

桌面悬浮小窗口，点击 **MCQ** 展开，手动粘贴题目和 A/B/C/D 选项，再显示答案、简短解释、讲义原文和 PDF 页码。再次点击 MCQ 收起；右键小窗口选择退出，或关闭主窗口。可用系统标题栏拖动窗口。

当前云端已用用户提供的 13 份 lecture notes 验证，提取出 352 个有文本的页面。GitHub 仓库不包含教材 PDF，也不包含提取后的教材正文。安装后请把自己的 13 份 PDF 复制到 `notes/` 文件夹；程序在本机读取，不修改教材内容。

这是学习工具。没有自动录屏、读屏、监听剪贴板、全局快捷键或隐藏/规避检测功能。悬浮窗仍是普通可见窗口，操作系统对置顶的支持可能不同。不承诺答案正确，也不承诺固定延迟；请核对原文。置信度只是模型自评，不是正确率。

## 安装（建议 Python 3.11 或 3.12）

### Windows

安装 python.org 的 Python，勾选 Python 加入 PATH 和 Tcl/Tk 支持。在 PowerShell 中：

```powershell
git clone https://github.com/huiHui0605/MCQ-answer-displayer.git
cd MCQ-answer-displayer
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

以后在仓库目录执行最后一行即可。无需激活虚拟环境。

### macOS / Linux

macOS 建议安装 python.org 的 Python（带 Tk）。Linux 需要图形桌面，以及发行版的 Tk/venv 包，例如 Debian/Ubuntu 的 `python3-tk python3-venv`。

```bash
git clone https://github.com/huiHui0605/MCQ-answer-displayer.git
cd MCQ-answer-displayer
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

若报告 Tk 模块缺失，先安装与你的 Python 版本匹配的 Tk，再重新创建 venv。

## 使用

1. 先将下载到本机的 lecture note PDF 复制进项目的 `notes/` 文件夹，再打开小窗口，等讲义索引完成。
2. 粘贴完整题目，选项各占一行，例如：

   ```text
   Which form of intellectual property protects an invention?
   A. Patent
   B. Trademark
   C. Copyright
   D. Franchising
   ```
3. 点击“显示答案”。首次会要求输入你自己的 **OpenAI API key**，输入框会遮盖字符，只在当前程序内存保存，不写入文件。需要可用的 API 余额和模型权限；ChatGPT 订阅不等于 API 额度。
4. 查看答案与引用。`?` 表示证据不足、低置信度或无法判定；不要当成确定答案。引用是模型选择的相关片段，程序只验证引用 ID 有效，不能证明模型推理正确。
5. 相同题目、讲义内容和模型命中缓存时，无需再次请求 API。勾选“重新推理”绕过缓存；模糊或无依据的答案不缓存。

默认模型为 `gpt-4.1-mini`。可设置 `MCQ_MODEL` 更换为支持 Chat Completions、temperature 和严格 JSON Schema 的模型；不是所有模型都兼容。可通过环境变量 `MCQ_API_KEY` 预先配置密钥。`.env.example` 仅供参考，程序**不会自动加载 .env**。不要把真实 key 提交到 GitHub。

## 速度、隐私与局限

- 启动时本地读取 PDF，使用 BM25 选出最多 8 页，只进行一次有 35 秒超时的 AI 请求。相同题目缓存更快，首次响应取决于网络和模型；没有保证秒数。
- 只支持可提取文本的 PDF；扫描件需要先 OCR。英文关键词检索效果较好；纯中文题目匹配英文讲义可能不佳。未检索到的章节、表格或图片可能影响准确率。
- 题目和检索到的讲义文本会发送到 `api.openai.com`，受你的 API 账户及服务商数据政策约束。不会发送整个 PDF，也没有其他遥测。不要输入敏感信息。
- 成功答案、题目哈希和引用缓存在用户目录 `~/.mcq-study/answers.json`，可以删除该文件清空缓存。原始题目不单独保存，但解释和引用可能包含题目信息。`MCQ_DATA_DIR` 可更改缓存目录。
- 加入或替换 `notes/` 中的 PDF 后重启。讲义指纹变化会使旧缓存失效。
- 网络错误不会自动重试，避免重复计费。401 检查 key，429 检查余额/限流，400 检查模型参数兼容性。更换 key 请重启程序。

## 验证

```bash
# Windows 使用 .\.venv\Scripts\python.exe 替换下面的解释器路径
.venv/bin/python -m unittest discover -s tests -v
```

6 项自动测试覆盖检索、缺少选项、模拟 AI 回应、缓存/强制刷新、无效引用、无依据结果和超时。测试使用模拟 API，不代表已验证真实 AI 准确率。

开发环境已实际读取 13 份 PDF、352 页文本并运行这些测试。云端没有可用图形显示器，未完成桌面交互测试；没有提供 API key，未验证真实 AI 调用、响应速度或答案准确率。Windows/macOS 安装步骤尚需在相应系统上验证。
