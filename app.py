"""Visible circular desktop button: click, scan once, answer, click to reset."""
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from answers import answer_questions
from auto_scan import scan_screen
from core import Engine, load_pages
from screen_scan import ScreenReader, enable_dpi_awareness, prepare_questions, capture_screen


class FloatingApp:
    def __init__(self, root, engine=None, reader=None):
        self.root = root
        self.engine, self.reader = engine, reader
        self.events = queue.Queue()
        self.mode = 'loading'
        self.last_text = ''
        self.last_error = ''
        self.last_answers = ''
        self.editor = None
        self.anchor = (80, 100)
        self.drag = None
        self.closed = False
        root.title('MCQ Study')
        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.configure(bg='#ff00ff')
        # Windows colorkey makes the area outside the circle transparent/click-through.
        try:
            root.attributes('-transparentcolor', '#ff00ff')
        except tk.TclError:
            # Other desktops may show a square background; no hidden capture features.
            root.configure(bg='#eef2ff')
        self.canvas = tk.Canvas(root, bg=root.cget('bg'), highlightthickness=0, cursor='hand2')
        self.canvas.pack(fill='both', expand=True)
        self.canvas.bind('<ButtonPress-1>', self.press)
        self.canvas.bind('<B1-Motion>', self.move)
        self.canvas.bind('<ButtonRelease-1>', self.release)
        self.canvas.bind('<Button-3>', self.menu)
        self.canvas.bind('<MouseWheel>', lambda e: self.canvas.yview_scroll(-1 if e.delta > 0 else 1, 'units'))
        self.canvas.bind('<Button-4>', lambda e: self.canvas.yview_scroll(-1, 'units'))
        self.canvas.bind('<Button-5>', lambda e: self.canvas.yview_scroll(1, 'units'))
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.circle('…')
        if engine is not None and reader is not None:
            self.mode = 'idle'
            self.circle('MCQ')
        else:
            self.background('ready', lambda: (Engine(*load_pages()), ScreenReader()))
        root.after(80, self.poll)

    def background(self, kind, fn):
        def run():
            try:
                self.events.put((kind, fn()))
            except Exception as exc:
                self.events.put(('error', str(exc)))
        threading.Thread(target=run, daemon=True).start()

    def place(self, width, height):
        x = max(0, min(self.anchor[0], self.root.winfo_screenwidth()-width))
        y = max(0, min(self.anchor[1], self.root.winfo_screenheight()-height))
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        self.root.deiconify()

    def circle(self, label):
        self.place(68, 68)
        self.canvas.configure(scrollregion=(0, 0, 68, 68))
        self.canvas.yview_moveto(0)
        self.canvas.delete('all')
        self.canvas.create_oval(2, 2, 66, 66, fill='#2563eb', outline='#93c5fd', width=2)
        self.canvas.create_text(34, 34, text=label, fill='white', font=('Segoe UI', 11, 'bold'))

    def show_answers(self, text):
        self.mode = 'answer'
        self.last_answers = text
        lines = max(1, len(text.splitlines()))
        height = min(max(70, lines*32+24), max(70, self.root.winfo_screenheight()-80))
        self.place(180, height)
        self.canvas.delete('all')
        self.canvas.configure(scrollregion=(0, 0, 180, max(height, lines*32+24)))
        self.canvas.yview_moveto(0)
        self.canvas.create_rectangle(0, 0, 180, max(height, lines*32+24), fill='#eff6ff', outline='#2563eb', width=2)
        self.canvas.create_text(16, 12, anchor='nw', text=text, fill='#172554', font=('Consolas', 18, 'bold'))

    def reset(self):
        if self.mode in ('busy', 'loading'):
            return
        self.mode = 'idle'
        self.circle('MCQ')

    def press(self, event):
        self.drag = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y(), False)

    def move(self, event):
        if self.drag is None:
            return
        sx, sy, x, y, moved = self.drag
        dx, dy = event.x_root-sx, event.y_root-sy
        if moved or abs(dx)+abs(dy) > 6:
            self.drag = (sx, sy, x, y, True)
            nx, ny = max(0, x+dx), max(0, y+dy)
            self.anchor = (nx, ny)
            self.root.geometry(f'+{nx}+{ny}')

    def release(self, event):
        moved = self.drag is not None and self.drag[-1]
        self.drag = None
        if moved:
            return
        if self.mode == 'answer':
            self.reset()
        elif self.mode == 'idle':
            self.scan()

    def menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label='扫描一次', command=self.scan)
        menu.add_command(label='回到圆形图标', command=self.reset)
        menu.add_command(label='查看上次答案', command=lambda: self.show_answers(self.last_answers) if self.mode not in ('busy', 'loading') and self.last_answers else None)
        menu.add_command(label='校正识别文字 / 手动输入', command=self.open_editor)
        menu.add_command(label='查看最近错误', command=lambda: messagebox.showinfo('MCQ', self.last_error or '没有错误记录。'))
        menu.add_separator()
        menu.add_command(label='退出', command=self.close)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def scan(self):
        if self.mode in ('busy', 'loading'):
            return
        if self.engine is None or self.reader is None:
            self.last_error = '初始化失败。请检查 notes 中的 PDF 和安装依赖后重新启动。'
            self.show_answers('?')
            return
        self.mode = 'busy'
        self.last_error = ''
        if self.editor is not None and self.editor.winfo_exists():
            self.editor.destroy()
            self.editor = None
        self.root.withdraw()
        # Let our own window disappear before the single screenshot.
        self.root.after(300, lambda: self.background('captured', capture_screen))

    def solve(self, questions, refresh=False):
        self.mode = 'busy'
        self.circle('AI…')
        self.background('answer', lambda: answer_questions(self.engine, questions, refresh,
            lambda done, total: self.events.put(('progress', f'{done}/{total}'))))

    def open_editor(self):
        if self.mode in ('busy', 'loading'):
            return
        if self.editor is not None and self.editor.winfo_exists():
            self.editor.lift()
            return
        editor = tk.Toplevel(self.root)
        self.editor = editor
        editor.title('校正题目')
        editor.geometry('540x420')
        editor.attributes('-topmost', True)
        text = scrolledtext.ScrolledText(editor, wrap='word')
        text.pack(fill='both', expand=True, padx=8, pady=8)
        text.insert('end', self.last_text)
        force = tk.BooleanVar()
        tk.Checkbutton(editor, text='重新推理', variable=force).pack()

        def submit():
            if self.mode == 'busy':
                return
            result = prepare_questions(text.get('1.0', 'end').splitlines())
            if not result.ready:
                messagebox.showwarning('识别不完整', result.warning, parent=editor)
                return
            refresh = force.get()
            editor.destroy()
            self.editor = None
            self.solve(result.questions, refresh)
        tk.Button(editor, text='显示答案', command=submit).pack(pady=8)

    def poll(self):
        if self.closed:
            return
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == 'ready':
                    self.engine, self.reader = value
                    self.mode = 'idle'
                    self.circle('MCQ')
                elif kind == 'captured':
                    self.circle('OCR…')
                    self.background('scanned', lambda image=value: scan_screen(self.reader, image))
                elif kind == 'scanned':
                    self.last_text = value.text
                    self.last_error = value.warning
                    if value.ready:
                        self.solve(value.questions)
                    else:
                        self.last_error = value.warning
                        self.show_answers('?')
                elif kind == 'progress':
                    self.circle(value)
                elif kind == 'answer':
                    if value.errors:
                        self.last_error = '\n'.join(dict.fromkeys(value.errors))
                    self.show_answers(value.text or '?')
                elif kind == 'error':
                    self.last_error = value
                    self.show_answers('?')
        except queue.Empty:
            pass
        self.root.after(80, self.poll)

    def close(self):
        self.closed = True
        self.root.destroy()


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    FloatingApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
