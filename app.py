"""User-selected local OCR with a compact answer-only result view."""
import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext
from core import Engine, load_pages
from screen_scan import (ScreenReader, capture_screen, crop_region,
                         enable_dpi_awareness, prepare_questions)
from answers import answer_questions


def main():
    enable_dpi_awareness()
    root = tk.Tk()
    root.title('MCQ')
    root.geometry('90x70+80+100')
    root.attributes('-topmost', True)
    events = queue.Queue()
    state = {'engine': None, 'reader': None, 'busy': False, 'panel': None,
             'editor': None, 'text': '', 'selector': None}

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
        if state['panel'] is None:
            panel = tk.Toplevel(root)
            state['panel'] = panel
            panel.title('答案')
            panel.geometry('180x230')
            panel.attributes('-topmost', True)
            panel.protocol('WM_DELETE_WINDOW', hide_panel)
            output = scrolledtext.ScrolledText(panel, wrap='none', font=('Consolas', 18), width=8, height=6)
            output.pack(fill='both', expand=True, padx=8, pady=8)
            output.configure(state='disabled')
            state['output'] = output
            status = tk.Label(panel, text='')
            status.pack()
            state['status'] = status
        state['panel'].deiconify()
        state['panel'].lift()

    def display(text):
        open_panel()
        output = state['output']
        output.configure(state='normal')
        output.delete('1.0', 'end')
        output.insert('end', text)
        output.configure(state='disabled')

    def status(text):
        open_panel()
        state['status'].configure(text=text)

    def set_busy(value):
        state['busy'] = value
        icon.configure(text='处理中…' if value else '框选 MCQ')

    def open_editor():
        if state['editor'] is not None and state['editor'].winfo_exists():
            state['editor'].deiconify()
            state['editor'].lift()
            return
        editor = tk.Toplevel(root)
        state['editor'] = editor
        editor.title('校正题目')
        editor.geometry('540x420')
        editor.attributes('-topmost', True)
        tk.Label(editor, text='题号用 1. / 2.，每题 A/B/C/D 各占一行').pack(pady=8)
        text = scrolledtext.ScrolledText(editor, wrap='word')
        text.pack(fill='both', expand=True, padx=8, pady=8)
        text.insert('end', state['text'])
        refresh = tk.BooleanVar()
        tk.Checkbutton(editor, text='重新推理', variable=refresh).pack()

        def submit():
            if state['busy']:
                return
            state['text'] = text.get('1.0', 'end')
            result = prepare_questions(state['text'].splitlines())
            if not result.ready:
                messagebox.showwarning('请校正', result.warning, parent=editor)
                return
            editor.withdraw()
            solve(result.questions, refresh.get())
        tk.Button(editor, text='显示答案', command=submit).pack(pady=8)

    def solve(questions, refresh=False):
        if state['engine'] is None:
            return
        set_busy(True)
        display('')
        status('推理中…')
        background('answer', lambda: answer_questions(state['engine'], questions, refresh,
            lambda done, total: events.put(('progress', f'{done}/{total}'))))

    def cancel_selection():
        if state['selector'] is not None:
            state['selector'].destroy()
            state['selector'] = None
        root.deiconify()
        set_busy(False)

    def choose_region(image):
        # Select on a frozen in-memory image; only the crop is sent to OCR.
        from PIL import Image, ImageTk
        height, width = image.shape[:2]
        overlay = tk.Toplevel(root)
        state['selector'] = overlay
        overlay.overrideredirect(True)
        overlay.geometry(f'{width}x{height}+0+0')
        overlay.attributes('-topmost', True)
        canvas = tk.Canvas(overlay, width=width, height=height, highlightthickness=0, cursor='crosshair')
        canvas.pack(fill='both', expand=True)
        photo = ImageTk.PhotoImage(Image.fromarray(image[:, :, ::-1]))
        canvas.image = photo
        canvas.create_image(0, 0, image=photo, anchor='nw')
        canvas.create_text(20, 20, anchor='nw', text='拖动框选完整题目和选项（单列）；Esc 取消',
                           fill='#ff4040', font=('', 16, 'bold'))
        drag = {'start': None, 'box': None}

        def press(event):
            drag['start'] = (event.x, event.y)
            if drag['box'] is not None:
                canvas.delete(drag['box'])
            drag['box'] = canvas.create_rectangle(event.x, event.y, event.x, event.y, outline='#ff4040', width=3)

        def move(event):
            if drag['start'] is not None:
                canvas.coords(drag['box'], *drag['start'], event.x, event.y)

        def release(event):
            if drag['start'] is None:
                return
            try:
                crop = crop_region(image, drag['start'], (event.x, event.y))
            except ValueError as exc:
                cancel_selection()
                messagebox.showwarning('重新框选', str(exc))
                return
            overlay.destroy()
            state['selector'] = None
            root.deiconify()
            display('')
            status('识别中…')
            background('scanned', lambda: state['reader'].read(crop))
        canvas.bind('<ButtonPress-1>', press)
        canvas.bind('<B1-Motion>', move)
        canvas.bind('<ButtonRelease-1>', release)
        overlay.bind('<Escape>', lambda event: cancel_selection())
        overlay.focus_force()

    def scan():
        if state['busy']:
            return
        if state['engine'] is None or state['reader'] is None:
            messagebox.showinfo('准备中', '正在准备讲义和本地 OCR，请稍后再试。')
            return
        set_busy(True)
        hide_panel()
        if state['editor'] is not None and state['editor'].winfo_exists():
            state['editor'].destroy()
            state['editor'] = None
        root.withdraw()
        root.after(300, lambda: background('captured', capture_screen))

    def poll():
        try:
            while True:
                kind, value = events.get_nowait()
                if kind == 'ready':
                    state['engine'], state['reader'] = value
                    icon.configure(text='框选 MCQ')
                elif kind == 'captured':
                    try:
                        choose_region(value)
                    except Exception as exc:
                        cancel_selection()
                        messagebox.showerror('无法框选', str(exc))
                elif kind == 'scanned':
                    state['text'] = value.text
                    if value.ready:
                        solve(value.questions)
                    else:
                        set_busy(False)
                        status('请重新框选或校正')
                        messagebox.showwarning('识别不完整', value.warning)
                elif kind == 'progress':
                    status(value)
                elif kind == 'error':
                    if state['selector'] is not None:
                        state['selector'].destroy()
                        state['selector'] = None
                    root.deiconify()
                    set_busy(False)
                    status('处理失败')
                    messagebox.showerror('MCQ', value)
                elif kind == 'answer':
                    set_busy(False)
                    display(value.text)
                    status('')
                    if value.errors:
                        messagebox.showerror('本地模型错误', value.errors[0])
        except queue.Empty:
            pass
        root.after(100, poll)

    icon = tk.Button(root, text='准备中…', command=scan, font=('', 10, 'bold'))
    icon.pack(fill='both', expand=True)
    menu = tk.Menu(root, tearoff=0)
    menu.add_command(label='框选题目', command=scan)
    menu.add_command(label='查看答案', command=open_panel)
    menu.add_command(label='校正识别文字 / 手动粘贴', command=open_editor)
    menu.add_command(label='退出', command=root.destroy)
    root.bind('<Button-3>', lambda event: menu.tk_popup(event.x_root, event.y_root))
    background('ready', lambda: (Engine(*load_pages()), ScreenReader()))
    root.after(100, poll)
    root.mainloop()


if __name__ == '__main__':
    main()
