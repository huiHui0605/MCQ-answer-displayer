"""Windows right-button wakeup while hidden; no input interception or recording."""
import sys


class RightClickWake:
    def __init__(self, root, callback, get_state=None):
        self.root = root
        self.callback = callback
        self.get_state = get_state
        if get_state is None and sys.platform == 'win32':
            import ctypes
            try:
                self.get_state = ctypes.windll.user32.GetAsyncKeyState
                self.get_state.argtypes = [ctypes.c_int]
                self.get_state.restype = ctypes.c_short
            except (AttributeError, OSError):
                pass
        self.timer = None
        self.armed = False
        self.pressed = False

    @property
    def available(self):
        return self.get_state is not None

    def arm(self):
        self.cancel()
        if not self.available:
            return
        self.armed = True
        self.pressed = False
        self.timer = self.root.after(20, self.poll)

    def poll(self):
        self.timer = None
        if not self.armed:
            return
        try:
            down = bool(self.get_state(0x02) & 0x8000)  # VK_RBUTTON, current state only
        except (OSError, AttributeError):
            # Keep the icon reachable if the native API becomes unavailable.
            self.cancel()
            self.callback()
            return
        if self.pressed and not down:
            self.cancel()
            # Restore after release so this click cannot open the icon menu.
            self.callback()
            return
        self.pressed = down
        self.timer = self.root.after(20, self.poll)

    def cancel(self):
        self.armed = False
        self.pressed = False
        if self.timer is not None:
            self.root.after_cancel(self.timer)
            self.timer = None
