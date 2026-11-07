"""Parse only explicit True/False choice rows, never words inside a statement."""
import re
import unicodedata

TRUTH = re.compile(r'^\s*[○◯●•□☐☑]?\s*(?:[ABTF][.):、]\s*)?(true|false|t|f)\s*$', re.I)


def truth_choices(text):
    text=unicodedata.normalize('NFKC',str(text)).strip()
    text=re.sub(r'\s+(?=[ABTF][.):]\s*(?:true|false)\b)', '\n', text, flags=re.I)
    if re.fullmatch(r'(?:true\s+false|false\s+true)',text,re.I):
        text='\n'.join(text.split())
    parts=text.splitlines()
    values=[]
    for part in parts:
        match=TRUTH.fullmatch(part)
        if not match:
            return []
        values.append('True' if match.group(1).lower() in ('true','t') else 'False')
    return values


def normalize_true_false(text):
    lines=text.splitlines()
    rows=[(i,truth_choices(line)) for i,line in enumerate(lines)]
    options=[(i,v) for i,values in rows for v in values]
    if len(options)!=2 or {v for _,v in options}!={'True','False'}:
        return None
    first,last=options[0][0],options[-1][0]
    if any(re.match(r'^\s*[ABCD][.):]',line,re.I) for line in lines[last+1:]):
        return None  # True and False can also be distractors in a four-choice MCQ.
    if any(line.strip() and not truth_choices(line) for line in lines[first:last+1]):
        return None
    stem='\n'.join(lines[:first]).strip()
    if not stem or re.search(r'(?im)^\s*[ABCD][.):]',stem):
        return None
    return stem+'\nT. True\nF. False'
