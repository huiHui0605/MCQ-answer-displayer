"""Locate conventional English MCQ blocks from local OCR boxes."""
from dataclasses import dataclass
import re
import unicodedata
from screen_scan import Question, ScanResult, crop_region, prepare_questions

LABEL = re.compile(r'(?<!\w)\(?([A-D])\s*[.):](?:\s|(?=[A-Za-z])|$)|^\s*([A-D])\s*$', re.I)
NUMBER = re.compile(r'^\s*(?:(?:question|q)\s*)?(\d{1,3})(?:[.):]|\s|$)', re.I)
STEM = re.compile(r'^\s*(?:Which|What|When|Where|Why|Who|How|Select|Identify|Choose|According|All|Each|For|In|If|The|An?|To|Entrepreneurs?)\b', re.I)
CONTROL = re.compile(r'^\s*(?:submit|next|previous|back|save|finish|review)(?:\s|$)', re.I)


@dataclass
class Block:
    number: str
    rows: list
    bounds: tuple
    complete: bool


def box(row):
    points = row[0]
    return (min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points))


def normalized(text):
    return ' '.join(re.findall(r'[a-z0-9]+', unicodedata.normalize('NFKC', text).lower()))


def locate_blocks(rows, shape):
    """One column, vertical choices or A/B/C/D on a shared line. Fail closed."""
    rows = sorted(rows, key=lambda r: (box(r)[1], box(r)[0]))
    labels = []
    for i, row in enumerate(rows):
        for match in LABEL.finditer(unicodedata.normalize('NFKC', row[1])):
            labels.append((i, (match.group(1) or match.group(2)).upper()))
    blocks, floor = [], -1
    for start, (ai, letter) in enumerate(labels):
        if letter != 'A':
            continue
        following = []
        for item in labels[start:]:
            if following and item[1] == 'A':
                break
            following.append(item)
            if item[1] == 'D':
                break
        complete = [v for _, v in following] == list('ABCD')
        di = following[-1][0]
        ax, ay, ar, ab = box(rows[ai])
        line_height = max(12, ab-ay)
        # Reject cross-column label sequences instead of merging different questions.
        if any(abs(box(rows[i])[0]-ax) > max(70, line_height*4) for i, _ in following if i != ai):
            continue
        candidates = [i for i in range(max(floor+1, ai-12), ai)
                      if abs(box(rows[i])[0]-ax) < max(160, line_height*7)
                      and ay-box(rows[i])[3] < line_height*14]
        numbered = [i for i in candidates if NUMBER.match(rows[i][1])]
        stems = [i for i in candidates if STEM.match(rows[i][1])]
        if numbered:
            begin = numbered[-1]
        elif stems:
            begin = stems[-1]
        else:
            continue
        group = rows[begin:di+1]
        # Keep tightly wrapped lines of option D, including lines starting "The".
        end = di
        for j in range(di+1, min(len(rows), di+4)):
            x, y, r, b = box(rows[j])
            prev_bottom = box(rows[end])[3]
            gap = y-prev_bottom
            if (not complete or gap > line_height*1.2 or x < ax-line_height*2
                    or x > max(box(row)[2] for row in group)
                    or NUMBER.match(rows[j][1]) or CONTROL.match(rows[j][1]) or LABEL.search(rows[j][1])
                    or (gap > line_height*.7 and STEM.match(rows[j][1]))):
                break
            group.append(rows[j])
            end = j
        # Text in a sidebar overlapping this block's vertical span is ambiguous.
        if any(box(row)[0] < ax-max(160, line_height*7) for row in group):
            complete = False
        coords = [box(row) for row in group]
        h, w = shape[:2]
        bounds = (max(0, int(min(v[0] for v in coords)-14)), max(0, int(min(v[1] for v in coords)-14)),
                  min(w, int(max(v[2] for v in coords)+14)), min(h, int(max(v[3] for v in coords)+14)))
        # Padding must not clip a few pixels of the next button/heading into OCR.
        next_tops = [box(r)[1] for r in rows[end+1:]
                     if box(r)[1] >= max(v[3] for v in coords)
                     and box(r)[0] < bounds[2] and box(r)[2] > bounds[0]]
        if next_tops:
            bounds = (*bounds[:3], min(bounds[3], int(min(next_tops))))
        number_match = NUMBER.match(rows[begin][1])
        number = number_match.group(1) if number_match else str(len(blocks)+1)
        blocks.append(Block(number, group, bounds, complete))
        floor = end
    return blocks


def scan_screen(reader, image):
    first_rows, _ = reader.ocr(image)
    if not first_rows:
        return ScanResult('', False, '未识别到题目。')
    blocks = locate_blocks(first_rows, image.shape)
    items = []
    for block in blocks:
        first = prepare_questions([row[1] for row in block.rows])
        x1, y1, x2, y2 = block.bounds
        if not block.complete or not first.ready or len(first.questions) != 1:
            items.append(Question(block.number, ''))
            continue
        second = reader.read(crop_region(image, (x1,y1), (x2,y2)))
        # Require both OCR passes to agree on all words, numbers and negations.
        if (not second.ready or len(second.questions) != 1
                or any(float(row[2]) < .8 for row in block.rows)
                or normalized(first.questions[0].text) != normalized(second.questions[0].text)):
            items.append(Question(block.number, ''))
        else:
            items.append(Question(block.number, second.questions[0].text))
    if len({q.number for q in items}) != len(items):
        return ScanResult('\n'.join(r[1] for r in first_rows), False, '题号重复或多栏排版无法可靠区分。')
    warning = '部分题目识别不完整或两次 OCR 不一致，已标记 ?。' if any(not q.text for q in items) else ''
    return ScanResult('\n'.join(r[1] for r in first_rows), bool(items),
                      warning if items else '未找到完整 MCQ 区域。', items)
