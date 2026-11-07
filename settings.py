"""Local preferences only: screen rectangle and model name, never screenshots."""
import json
from core import DATA, model_name

PATH = DATA / 'settings.json'


def load_settings():
    try:
        value = json.loads(PATH.read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_settings(value):
    PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = PATH.with_suffix('.tmp')
    temporary.write_text(json.dumps(value), encoding='utf-8')
    temporary.replace(PATH)


def preferred_model(settings):
    saved=settings.get('model')
    return model_name(saved if isinstance(saved,str) and saved.strip() else None)


def make_region(shape, start, end):
    height, width = shape[:2]
    x1,x2 = sorted((int(start[0]),int(end[0])))
    y1,y2 = sorted((int(start[1]),int(end[1])))
    x1,x2=max(0,x1),min(width,x2)
    y1,y2=max(0,y1),min(height,y2)
    if x2-x1 < 80 or y2-y1 < 80:
        raise ValueError('选区过小，请包含完整题干和四个选项。')
    return {'screen': [width,height], 'rect': [x1,y1,x2,y2]}


def apply_region(image, region):
    if not region:
        return image
    height,width=image.shape[:2]
    try:
        screen=region['screen']
        x1,y1,x2,y2=region['rect']
        if any(type(v) is not int for v in (*screen,x1,y1,x2,y2)):
            raise ValueError()
        if screen != [width,height]:
            raise ValueError('显示器分辨率已变化，请右键重新设置题目区域。')
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height and x2-x1 >= 80 and y2-y1 >= 80):
            raise ValueError()
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(str(exc) if str(exc).startswith('显示器') else '保存的选区无效，请右键重新设置题目区域。') from None
    return image[y1:y2,x1:x2].copy()
