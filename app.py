"""Small, user-controlled desktop study window. No capture or global hooks."""
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
from core import Engine, load_pages


def main():
    root = tk.Tk()
    root.title('MCQ Study')
    root.geometry('76x66+80+100')
    root.attributes('-topmost', True)
    events = queue.Queue()
    state = {'engine': None, 'busy': False, 'panel': None}

    def worker(fn):
        try:
            events.put(('ok', fn()))
        except Exception as exc:
            events.put(('error', str(exc)))

    def open_panel():
        if state['panel'] is not None:
            state['panel'].destroy()
            state['panel'] = None
            return
        panel = tk.Toplevel(root)
        state['panel'] = panel
        panel.title('MCQ · 本地离线练习助手')
        panel.geometry('540x650')
        panel.attributes('-topmost', True)
        panel.protocol('WM_DELETE_WINDOW', open_panel)
        tk.Label(panel, text='粘贴题目，A/B/C/D 选项各一行', font=('', 12, 'bold')).pack(pady=10)
        question = scrolledtext.ScrolledText(panel, height=10, wrap='word')
        question.pack(fill='x', padx=12)
        row = tk.Frame(panel)
        row.pack(fill='x', padx=12, pady=8)
        refresh = tk.BooleanVar()
        tk.Checkbutton(row, text='重新推理（不使用答案缓存）', variable=refresh).pack(side='left')
        output = scrolledtext.ScrolledText(panel, wrap='word', height=20)
        output.pack(fill='both', expand=True, padx=12, pady=8)
        output.insert('end', '首次启动正在读取讲义…' if state['engine'] is None else '讲义已就绪。AI 可能出错，请核对引用。')
        output.configure(state='disabled')
        state['output'] = output

        def solve():
            if state['busy']:
                return
            if state['engine'] is None:
                messagebox.showinfo('准备中', '讲义仍在索引，稍后再试。')
                return
            q, force = question.get('1.0', 'end'), refresh.get()
            state['busy'] = True
            display('正在本机检索讲义并推理…首次加载或 CPU 推理可能需要数分钟。')
            threading.Thread(target=worker, args=(lambda: state['engine'].answer(q, force),), daemon=True).start()
        tk.Button(row, text='显示答案', command=solve).pack(side='right')
        question.focus_set()

    def display(text):
        output = state.get('output')
        if output is not None and output.winfo_exists():
            output.configure(state='normal')
            output.delete('1.0', 'end')
            output.insert('end', text)
            output.configure(state='disabled')

    def poll():
        try:
            while True:
                kind, value = events.get_nowait()
                state['busy'] = False
                if kind == 'error':
                    display(value)
                    if state['panel'] is None:
                        messagebox.showerror('MCQ Study', value)
                elif isinstance(value, Engine):
                    state['engine'] = value
                    display(f'已读取 {len(value.pages)} 页讲义。粘贴题目后点击显示答案。')
                else:
                    text = f'{value["answer"]}    ·    参考置信度 {value["confidence"]}\n'
                    text += ('缓存命中' if value['cached'] else f'AI 用时 {value["seconds"]} 秒') + '\n\n' + value['explanation']
                    text += '\n\n讲义依据（PDF 文件页码）：\n'
                    for ref in value['references']:
                        text += f'\n{ref["file"]} · p.{ref["page"]}\n{ref["text"]}\n'
                    display(text)
        except queue.Empty:
            pass
        root.after(100, poll)

    tk.Button(root, text='MCQ', command=open_panel, font=('', 11, 'bold')).pack(fill='both', expand=True)
    menu = tk.Menu(root, tearoff=0)
    menu.add_command(label='退出', command=root.destroy)
    root.bind('<Button-3>', lambda event: menu.tk_popup(event.x_root, event.y_root))
    threading.Thread(target=worker, args=(lambda: Engine(*load_pages()),), daemon=True).start()
    root.after(100, poll)
    root.mainloop()


if __name__ == '__main__':
    main()
