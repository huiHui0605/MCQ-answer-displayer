"""Circular desktop button: select, answer, hide, right-click to restore."""
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from answers import answer_questions
from auto_scan import scan_selected_area
from core import Engine, load_pages, check_model
from screen_scan import ScreenReader, enable_dpi_awareness, prepare_questions, capture_screen
from settings import load_settings, save_settings, preferred_model, make_region, apply_region
from mouse_wake import RightClickWake

IDLE_SYMBOL = '☁'


class FloatingApp:
    def __init__(self, root, engine=None, reader=None):
        self.root = root
        self.engine, self.reader = engine, reader
        self.events = queue.Queue()
        self.settings = load_settings()
        self.selector = None
        self.mode = 'loading'
        self.last_text = ''
        self.last_error = ''
        self.last_answers = ''
        self.editor = None
        self.anchor = (80, 100)
        self.drag = None
        self.closed = False
        self.wake = RightClickWake(root, self.restore)
        root.title('MCQ Study')
        root.overrideredirect(True)
        root.attributes('-topmost', True)
        root.configure(bg='#ff00ff')
        # Windows colorkey makes the area outside the circle transparent/click-through.
        try:
            root.attributes('-transparentcolor', '#ff00ff')
        except tk.TclError:
            # Other desktops may show a square background; no hidden capture features.
            root.configure(bg='#f2f4f5')
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
            self.engine.model = preferred_model(self.settings)
            self.mode = 'idle'
            self.circle(IDLE_SYMBOL)
        else:
            self.background('ready', lambda: (Engine(*load_pages(), model=preferred_model(self.settings)), ScreenReader()))
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
        self.place(52, 52)
        self.canvas.configure(scrollregion=(0, 0, 52, 52))
        self.canvas.yview_moveto(0)
        self.canvas.delete('all')
        self.canvas.create_oval(2, 2, 50, 50, fill='#edf0f2', outline='#dce2e6', width=1)
        self.canvas.create_text(26, 26, text=label, fill='#8a969e',
                                font=('Segoe UI Symbol', 18) if label == IDLE_SYMBOL else ('Segoe UI', 10))

    def show_answers(self, text):
        self.mode = 'answer'
        self.last_answers = text
        lines = max(1, len(text.splitlines()))
        height = min(max(52, lines*26+20), max(52, self.root.winfo_screenheight()-80))
        self.place(140, height)
        self.canvas.delete('all')
        self.canvas.configure(scrollregion=(0, 0, 140, max(height, lines*26+20)))
        self.canvas.yview_moveto(0)
        self.canvas.create_rectangle(0, 0, 140, max(height, lines*26+20), fill='#f6f7f8', outline='#dce2e6', width=1)
        self.canvas.create_text(12, 10, anchor='nw', text=text, fill='#65717a', font=('Consolas', 14))

    def reset(self):
        if self.mode in ('busy', 'loading'):
            return
        self.wake.cancel()
        self.mode = 'idle'
        self.circle(IDLE_SYMBOL)

    def hide_answer(self):
        if not self.wake.available:
            # Non-Windows desktops keep a reachable icon.
            self.reset()
            return
        self.mode = 'hidden'
        if self.editor is not None and self.editor.winfo_exists():
            self.editor.destroy()
            self.editor = None
        self.root.withdraw()
        self.wake.arm()

    def restore(self):
        if not self.closed and self.mode == 'hidden':
            self.reset()

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
            self.hide_answer()
        elif self.mode == 'idle':
            self.scan()

    def menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label='框选题目', command=self.scan)
        models=tk.Menu(menu,tearoff=0)
        for name in ('qwen2.5:3b','qwen2.5:7b'):
            models.add_command(label=name,command=lambda n=name:self.switch_model(n))
        menu.add_cascade(label='本地模型',menu=models)
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

    def switch_model(self,name):
        if self.mode in ('busy','loading'):
            return
        self.mode='busy'
        self.circle('…')
        self.background('model_ready',lambda:check_model(name))

    def process_image(self,image):
        # Only the current user-drawn crop is passed here; old saved regions are ignored.
        return scan_selected_area(self.reader,image)

    def choose_region(self,image):
        from PIL import Image,ImageTk
        height,width=image.shape[:2]
        overlay=tk.Toplevel(self.root)
        self.selector=overlay
        overlay.overrideredirect(True)
        overlay.geometry(f'{width}x{height}+0+0')
        overlay.attributes('-topmost',True)
        canvas=tk.Canvas(overlay,width=width,height=height,highlightthickness=0,cursor='crosshair')
        canvas.pack(fill='both',expand=True)
        photo=ImageTk.PhotoImage(Image.fromarray(image[:,:,::-1]))
        canvas.image=photo
        canvas.create_image(0,0,image=photo,anchor='nw')
        canvas.create_text(20,20,anchor='nw',fill='#526b7a',text='拖动框选完整题干与选项；Esc 或右键取消',font=('',14,'bold'))
        drag={'start':None,'box':None}
        def press(event):
            drag['start']=(event.x,event.y)
            if drag['box'] is not None:
                canvas.delete(drag['box'])
            drag['box']=canvas.create_rectangle(event.x,event.y,event.x,event.y,outline='#879eae',width=2)
        def move(event):
            if drag['start']:
                canvas.coords(drag['box'],*drag['start'],event.x,event.y)
        def cancel():
            overlay.destroy()
            self.selector=None
            self.mode='idle'
            self.circle(IDLE_SYMBOL)
        def release(event):
            if not drag['start']:
                return
            try:
                region=make_region(image.shape,drag['start'],(event.x,event.y))
                cropped=apply_region(image,region)
            except (ValueError,OSError) as exc:
                cancel()
                self.last_error=str(exc)
                self.show_answers('?')
                return
            overlay.destroy()
            self.selector=None
            self.circle('…')
            self.background('scanned',lambda:self.process_image(cropped))
        canvas.bind('<ButtonPress-1>',press)
        canvas.bind('<B1-Motion>',move)
        canvas.bind('<ButtonRelease-1>',release)
        overlay.bind('<Escape>',lambda e:cancel())
        overlay.bind('<Button-3>',lambda e:cancel())
        overlay.focus_force()

    def solve(self, questions, refresh=False):
        self.mode = 'busy'
        self.circle('…')
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
                    self.circle(IDLE_SYMBOL)
                elif kind == 'captured':
                    try:
                        self.choose_region(value)
                    except Exception as exc:
                        if self.selector is not None:
                            self.selector.destroy()
                            self.selector=None
                        self.last_error=str(exc)
                        self.show_answers('?')
                elif kind == 'model_ready':
                    updated={**self.settings,'model':value}
                    try:
                        save_settings(updated)
                        self.settings=updated
                        self.engine.model=value
                        self.mode='idle'
                        self.circle(IDLE_SYMBOL)
                    except OSError as exc:
                        self.last_error=str(exc)
                        self.show_answers('?')
                elif kind == 'scanned':
                    self.last_text = ('\n\n'.join(f'{q.number}. {q.text}' for q in value.questions)
                                      if value.questions and all(q.text for q in value.questions) else value.text)
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
        self.wake.cancel()
        self.root.destroy()


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    FloatingApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
