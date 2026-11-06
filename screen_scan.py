"""One user-requested screenshot, local OCR, no image files or network calls."""
from dataclasses import dataclass
import re
import sys
import unicodedata


@dataclass
class ScanResult:
    text: str
    ready: bool
    warning: str = ''


def enable_dpi_awareness():
    # Call before Tk creates windows; keeps coordinates consistent on Windows.
    if sys.platform == 'win32':
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()


def capture_screen():
    import mss
    import numpy as np
    try:
        with mss.mss() as capture:
            # Capture the Windows primary monitor, not the combined multi-monitor desktop.
            monitors = capture.monitors[1:]
            monitor = next((m for m in monitors if m['left'] == 0 and m['top'] == 0), monitors[0])
            return np.asarray(capture.grab(monitor))[:, :, :3].copy()  # BGR for RapidOCR
    except Exception as exc:
        raise ValueError('无法截取主屏幕。请在本机图形桌面运行，并检查系统的屏幕录制权限。') from exc


def prepare_question(lines):
    """Conservative option detection: ambiguous scans require a manual edit."""
    text = '\n'.join(unicodedata.normalize('NFKC', str(line)).strip() for line in lines)
    text = re.sub(r'(?<!\w)\(?([A-Da-d])\s*[.、:：)]\s*', r'\n\1. ', text)
    text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
    labels = list(re.finditer(r'(?m)^([A-Da-d])(?:[.、:：)]\s*|[ \t]+|$)', text))
    if [m.group(1).upper() for m in labels] != list('ABCD'):
        return ScanResult(text, False, '没有识别到唯一一组顺序正确的 A/B/C/D 选项。请保留一道完整题目，校正文字后再答题。')
    # Canonicalize labels, including OCR boxes containing an isolated letter.
    for match in reversed(labels):
        text = text[:match.start()] + match.group(1).upper() + '. ' + text[match.end():]
    labels = list(re.finditer(r'(?m)^[ABCD]\. ', text))
    if not text[:labels[0].start()].strip():
        return ScanResult(text, False, '未识别到题干，请在文字框补充题目。')
    ends = [m.start() for m in labels[1:]] + [len(text)]
    if any(not text[m.end():end].strip() for m, end in zip(labels, ends)):
        return ScanResult(text, False, '部分选项为空，请校正识别文字。')
    return ScanResult(text, True)


class ScreenReader:
    def __init__(self):
        # Package includes ONNX weights; inference never downloads models.
        import onnxruntime
        onnxruntime.disable_telemetry_events()
        from rapidocr_onnxruntime import RapidOCR
        self.ocr = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)

    def read(self, image):
        rows, _ = self.ocr(image)
        if not rows:
            return ScanResult('', False, '没有识别到文字。请放大题目，并确认题目在主屏幕上清晰可见。')
        result = prepare_question([row[1] for row in rows])
        if any(float(row[2]) < .65 for row in rows):
            result.ready = False
            result.warning = '部分文字识别置信度较低。请核对题干、NOT/EXCEPT 和选项后点击显示答案。'
        return result
