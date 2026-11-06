"""User-triggered local screen OCR and a visible floating study window."""
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
from core import Engine, load_pages
from screen_scan import ScreenReader, capture_screen, enable_dpi_awareness


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    root.title('MCQ 扫描')
    root.geometry('90x70+80+100')
    root.attributes('-topmost', True)
    events = queue.Queue()
    state = {'engine': None, 'reader': None, 'busy': False, 'panel': None}

    def worker(kind, fn):
        try:
            events.put((kind, fn()))
        except Exception as exc:
            events.put(('error', str(exc)))

    def background(kind, fn):
        threading.Thread(target=worker, args=(kind, fn), daemon=True).start()

    def hide_panel():
        if state['panel'] is not None:
            state['panel'].withdraw()

    def open_panel():
        if state['panel'] is not None:
            state['panel'].deiconify()
            state['panel'].lift()
            return
        panel = tk.Toplevel(root)
        state['panel'] = panel
        panel.title('MCQ · 本地扫描与答案')
        panel.geometry('580x700')
        panel.attributes('-topmost', True)
        panel.protocol('WM_DELETE_WINDOW', hide_panel)
        tk.Label(panel, text='扫描文字（可校正）；A/B/C/D 选项各一行', font=('', 12, 'bold')).pack(pady=10)
        question = scrolledtext.ScrolledText(panel, height=11, wrap='word')
        question.pack(fill='x', padx=12)
        state['question'] = question
        row = tk.Frame(panel)
        row.pack(fill='x', padx=12, pady=8)
        refresh = tk.BooleanVar()
        state['refresh'] = refresh
        tk.Checkbutton(row, text='重新推理', variable=refresh).pack(side='left')
        tk.Button(row, text='收起', command=hide_panel).pack(side='left')
        tk.Button(row, text='重新扫描', command=scan).pack(side='right')
        tk.Button(row, text='显示答案', command=solve).pack(side='right')
        output = scrolledtext.ScrolledText(panel, wrap='word', height=22)
        output.pack(fill='both', expand=True, padx=12, pady=8)
        output.insert('end', '点击悬浮图标扫描主屏幕，或手动粘贴完整题目。')
        output.configure(state='disabled')
        state['output'] = output

    def display(text):
        open_panel()
        output = state['output']
        output.configure(state='normal')
        output.delete('1.0', 'end')
        output.insert('end', text)
        output.configure(state='disabled')

    def set_busy(value):
        state['busy'] = value
        icon.configure(text='处理中…' if value else '扫描 MCQ')

    def solve():
        if state['busy']:
            return
        if state['engine'] is None:
            messagebox.showinfo('准备中', '讲义仍在索引，稍后再试。')
            return
        q = state['question'].get('1.0', 'end')
        force = state['refresh'].get()
        set_busy(True)
        display('正在本机检索讲义并推理…首次加载或 CPU 推理可能需要数分钟。')
        background('answer', lambda: state['engine'].answer(q, force))

    def scan():
        if state['busy']:
            return
        if state['engine'] is None or state['reader'] is None:
            messagebox.showinfo('准备中', '正在准备讲义和本地 OCR，请稍后再扫描。')
            return
        set_busy(True)
        # Briefly remove our own windows so they do not cover the question.
        hide_panel()
        root.withdraw()
        root.after(300, lambda: background('captured', capture_screen))

    def poll():
        try:
            while True:
                kind, value = events.get_nowait()
                if kind == 'ready':
                    state['engine'], state['reader'] = value
                    icon.configure(text='扫描 MCQ')
                elif kind == 'captured':
                    root.deiconify()
                    display('截图已在内存中取得，正在本地识别文字…')
                    background('scanned', lambda image=value: state['reader'].read(image))
                elif kind == 'scanned':
                    set_busy(False)
                    state['question'].delete('1.0', 'end')
                    state['question'].insert('end', value.text)
                    if value.ready:
                        solve()
                    else:
                        display(value.warning)
                elif kind == 'error':
                    root.deiconify()
                    set_busy(False)
                    display(value)
                elif kind == 'answer':
                    set_busy(False)
                    text = f'{value["answer"]}    ·    参考置信度 {value["confidence"]}\n'
                    text += ('缓存命中' if value['cached'] else f'AI 用时 {value["seconds"]} 秒') + '\n\n' + value['explanation']
                    text += '\n\n讲义依据（PDF 文件页码）：\n'
                    for ref in value['references']:
                        text += f'\n{ref["file"]} · p.{ref["page"]}\n{ref["text"]}\n'
                    display(text)
        except queue.Empty:
            pass
        root.after(100, poll)

    icon = tk.Button(root, text='准备中…', command=scan, font=('', 10, 'bold'))
    icon.pack(fill='both', expand=True)
    menu = tk.Menu(root, tearoff=0)
    menu.add_command(label='扫描主屏幕', command=scan)
    menu.add_command(label='查看结果 / 手动粘贴', command=open_panel)
    menu.add_command(label='退出', command=root.destroy)
    root.bind('<Button-3>', lambda event: menu.tk_popup(event.x_root, event.y_root))
    background('ready', lambda: (Engine(*load_pages()), ScreenReader()))
    root.after(100, poll)
    root.mainloop()


if __name__ == '__main__':
    main()
