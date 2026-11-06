"""One user-requested screenshot, local OCR, no image files or network calls."""
from dataclasses import dataclass, field
import re
import sys
import unicodedata


@dataclass
class Question:
    number: str
    text: str


@dataclass
class ScanResult:
    text: str
    ready: bool
    warning: str = ''
    questions: list[Question] = field(default_factory=list)


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


def prepare_questions(lines):
    """Split only explicitly numbered, consecutive questions in one column."""
    text = '\n'.join(unicodedata.normalize('NFKC', str(line)).strip() for line in lines)
    marker = re.compile(r'(?im)^\s*(?:(?:question|q)\s*(\d{1,3})[.):]?(?:[ \t]+|$)|(\d{1,3})[.):](?:[ \t]+|$))')
    matches = list(marker.finditer(text))
    if not matches:
        result = prepare_question(lines)
        if result.ready:
            result.questions = [Question('1', result.text)]
        return result
    prefix = text[:matches[0].start()]
    if re.search(r'(?im)^\s*[ABCD][.)]\s', prefix):
        return ScanResult(text, False, '框选包含没有题号的题目，请补齐题号后重新答题。')
    numbers = [int(m.group(1) or m.group(2)) for m in matches]
    if any(b != a + 1 for a, b in zip(numbers, numbers[1:])):
        return ScanResult(text, False, '题号不连续或重复，请框选单列完整题目或校正文字。')
    items = []
    for i, match in enumerate(matches):
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        result = prepare_question(text[match.end():end].splitlines())
        if not result.ready:
            return ScanResult(text, False, f'第 {numbers[i]} 题识别不完整，请重新框选或校正文字。')
        items.append(Question(str(numbers[i]), result.text))
    return ScanResult(text, True, questions=items)


def crop_region(image, start, end):
    """Clamp a drag rectangle to the captured primary monitor, never resize it."""
    height, width = image.shape[:2]
    x1, x2 = sorted((max(0, min(width, int(start[0]))), max(0, min(width, int(end[0])))))
    y1, y2 = sorted((max(0, min(height, int(start[1]))), max(0, min(height, int(end[1])))))
    if x2 - x1 < 40 or y2 - y1 < 40:
        raise ValueError('框选区域太小，请包含完整题干和 A/B/C/D 选项。')
    return image[y1:y2, x1:x2].copy()


def prepare_image(image):
    """Enlarge small crops for text recognition, preserving color and punctuation."""
    import cv2
    height, width = image.shape[:2]
    scale = min(2.0, 1800 / max(height, width))
    if scale > 1:
        image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return cv2.copyMakeBorder(image, 16, 16, 16, 16, cv2.BORDER_CONSTANT, value=(255, 255, 255))


class ScreenReader:
    def __init__(self):
        # Package includes ONNX weights; inference never downloads models.
        import onnxruntime
        onnxruntime.disable_telemetry_events()
        from rapidocr_onnxruntime import RapidOCR
        self.ocr = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)

    def read(self, image):
        rows, _ = self.ocr(prepare_image(image) if image is not None else image)
        if not rows:
            return ScanResult('', False, '没有识别到文字。请放大题目，并确认题目在主屏幕上清晰可见。')
        result = prepare_questions([row[1] for row in rows])
        if any(float(row[2]) < .80 for row in rows):
            result.ready = False
            result.warning = '部分文字识别置信度较低。请核对题干、NOT/EXCEPT 和选项后点击显示答案。'
        return result
