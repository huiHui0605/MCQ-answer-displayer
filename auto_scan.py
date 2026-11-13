"""Locate conventional English MCQ blocks from local OCR boxes."""
from dataclasses import dataclass
import re
import unicodedata
from screen_scan import Question, ScanResult, crop_region, prepare_questions
from question_types import truth_choices

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


def same_question(first,second):
    a=unicodedata.normalize('NFKC',first).casefold()
    b=unicodedata.normalize('NFKC',second).casefold()
    critical=r'\b(?:not|no|never|except|least|false|true|cannot|without|incorrect)\b'
    if re.findall(critical,a)!=re.findall(critical,b):
        return False
    numbers=r'\d+(?:[.,]\d+)?'
    if re.findall(numbers,a)!=re.findall(numbers,b):
        return False
    # OCR frequently merges English spaces; preserve letters, numbers and negation checks.
    return re.sub(r'[^a-z0-9]','',a)==re.sub(r'[^a-z0-9]','',b)


def locate_blocks(rows, shape):
    """Build label chains within each column instead of interleaving the whole page."""
    rows = sorted(rows, key=lambda r: (box(r)[1], box(r)[0]))
    labels = []
    for i, row in enumerate(rows):
        for match in LABEL.finditer(unicodedata.normalize('NFKC', row[1])):
            labels.append((i, (match.group(1) or match.group(2)).upper()))
    seeds = [(i, box(rows[i])[0]) for i, letter in labels if letter == 'A']
    h, w = shape[:2]
    blocks = []
    for start, (ai, letter) in enumerate(labels):
        if letter != 'A':
            continue
        ax, ay, ar, ab = box(rows[ai])
        line_height = max(12, ab-ay)
        tolerance = max(50, line_height*2.5)
        right_columns = [x for i,x in seeds if x > ax+tolerance*2]
        right_edge = min(right_columns)-line_height if right_columns else w
        following = []
        for i,label in labels[start:]:
            if i != ai and abs(box(rows[i])[0]-ax) > tolerance:
                continue
            if following and label == 'A':
                break
            following.append((i,label))
            if label == 'D':
                break
        complete = [v for _,v in following] == list('ABCD')
        di = following[-1][0]
        floor = max((max(box(r)[3] for r in b.rows) for b in blocks
                     if abs(b.bounds[0]+14-ax) <= tolerance), default=-1)
        candidates = [i for i in range(ai) if box(rows[i])[1] > floor
                      and abs(box(rows[i])[0]-ax) < max(120,line_height*4)
                      and 0 <= ay-box(rows[i])[3] < line_height*18]
        numbered = [i for i in candidates if NUMBER.match(rows[i][1])]
        stems = [i for i in candidates if STEM.match(rows[i][1]) or '?' in rows[i][1]]
        if numbered:
            begin = numbered[-1]
        elif stems:
            # Keep the beginning of a wrapped question, not just its last line.
            begin = stems[-1]
            for earlier in reversed(stems[:-1]):
                if box(rows[begin])[1]-box(rows[earlier])[3] <= line_height*1.5:
                    begin = earlier
                else:
                    break
        else:
            continue
        y_start, y_end = box(rows[begin])[1], box(rows[di])[3]
        group = [r for r in rows if y_start <= box(r)[1] and box(r)[3] <= y_end+line_height*.3
                 and ax-max(120,line_height*4) <= box(r)[0] < right_edge]
        if not group:
            continue
        if any(box(r)[2] > right_edge+line_height for r in group):
            complete=False  # OCR merged text across columns; do not guess the split.
        for r in rows[di+1:]:
            x,y,right,bottom=box(r)
            gap=y-max(box(v)[3] for v in group)
            if x < ax-line_height*2 or x >= right_edge or gap < -line_height*.3:
                continue
            if (not complete or gap > line_height*1.2 or NUMBER.match(r[1])
                    or CONTROL.match(r[1]) or LABEL.search(r[1])
                    or (gap > line_height*.7 and STEM.match(r[1]))):
                break
            group.append(r)
            if len(group) > 100:
                complete=False
                break
        coords=[box(r) for r in group]
        bounds=(max(0,int(min(v[0] for v in coords)-14)), max(0,int(min(v[1] for v in coords)-14)),
                min(w,int(min(right_edge,max(v[2] for v in coords)+14))), min(h,int(max(v[3] for v in coords)+14)))
        next_tops=[box(r)[1] for r in rows if box(r)[1] >= max(v[3] for v in coords)
                   and box(r)[0] < bounds[2] and box(r)[2] > bounds[0]]
        if next_tops:
            bounds=(*bounds[:3],min(bounds[3],int(min(next_tops))))
        match=NUMBER.match(rows[begin][1])
        blocks.append(Block(match.group(1) if match else str(len(blocks)+1), group, bounds, complete))
    return blocks


def locate_true_false(rows, shape):
    rows=sorted(rows,key=lambda r:(box(r)[1],box(r)[0]))
    choices=[(i,truth_choices(r[1])) for i,r in enumerate(rows) if truth_choices(r[1])]
    used=set()
    blocks=[]
    height,width=shape[:2]
    for i,values in choices:
        if i in used:
            continue
        x,y,right,bottom=box(rows[i])
        lh=max(12,bottom-y)
        partners=[(j,vs) for j,vs in choices if j!=i and j not in used and len(vs)==1
                  and vs!=values and ((abs(box(rows[j])[0]-x)<lh*3 and abs(box(rows[j])[1]-y)<lh*10)
                  or (abs(box(rows[j])[1]-y)<lh and abs(box(rows[j])[0]-x)<700))]
        if len(values)==2 and set(values)=={'True','False'}:
            indices=[i]
        elif len(values)==1 and partners:
            partner=min(partners,key=lambda p:abs(box(rows[p[0]])[1]-y)*3+abs(box(rows[p[0]])[0]-x))[0]
            indices=sorted([i,partner])
        else:
            continue
        top=min(box(rows[k])[1] for k in indices)
        left=min(box(rows[k])[0] for k in indices)
        option_bottom=max(box(rows[k])[3] for k in indices)
        candidates=[k for k,r in enumerate(rows) if box(r)[3]<=top and top-box(r)[3]<lh*18
                    and abs(box(r)[0]-left)<max(180,lh*5)]
        numbered=[k for k in candidates if NUMBER.match(rows[k][1])]
        stems=[k for k in candidates if STEM.match(rows[k][1]) or '?' in rows[k][1]]
        if numbered:
            begin=numbered[-1]
        elif stems:
            begin=stems[-1]
        else:
            continue
        start_y=box(rows[begin])[1]
        start_x=box(rows[begin])[0]
        right_edge=max([box(rows[k])[2] for k in indices]+[box(rows[begin])[2]])+20
        group=[r for r in rows if start_y<=box(r)[1] and box(r)[3]<=option_bottom+lh*.2
               and start_x-lh<=box(r)[0]<right_edge]
        parsed=prepare_questions([r[1] for r in group])
        if not parsed.ready or len(parsed.questions)!=1 or '\nT. True\nF. False' not in parsed.questions[0].text:
            continue
        coords=[box(r) for r in group]
        bounds=(max(0,int(min(v[0] for v in coords)-12)),max(0,int(start_y-12)),
                min(width,int(max(v[2] for v in coords)+12)),min(height,int(option_bottom+12)))
        match=NUMBER.match(rows[begin][1])
        blocks.append(Block(match.group(1) if match else str(len(blocks)+1),group,bounds,True))
        used.update(indices)
    return blocks


def scan_screen(reader, image):
    first_rows, _ = reader.ocr(image)
    if not first_rows:
        return ScanResult('', False, '未识别到题目。')
    boolean_blocks = locate_true_false(first_rows, image.shape)
    blocks = [b for b in locate_blocks(first_rows, image.shape) if not any(
        abs(b.bounds[1]-t.bounds[1])<30 and abs(b.bounds[0]-t.bounds[0])<60 for t in boolean_blocks)] + boolean_blocks
    blocks.sort(key=lambda b:(int(b.number),b.bounds[0]))
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
                or first.questions[0].number != second.questions[0].number
                or not same_question(first.questions[0].text,second.questions[0].text)):
            items.append(Question(block.number, ''))
        else:
            items.append(Question(block.number, second.questions[0].text))
    if len({q.number for q in items}) != len(items):
        return ScanResult('\n'.join(r[1] for r in first_rows), False, '题号重复或多栏排版无法可靠区分。')
    warning = '部分题目识别不完整或两次 OCR 不一致，已标记 ?。' if any(not q.text for q in items) else ''
    return ScanResult('\n'.join(r[1] for r in first_rows), bool(items),
                      warning if items else '未找到完整 MCQ 区域。', items)


def scan_selected_area(reader, image):
    # The user's crop already supplies the region. Read its enlarged version;
    # a degraded raw-size pass is not independent evidence against this text.
    # ScreenReader still validates option completeness and text confidence.
    return reader.read(image)
