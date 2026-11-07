"""Compact answer formatting; explanations never enter the result view."""
from dataclasses import dataclass
from screen_scan import Question


@dataclass
class Answers:
    text: str
    errors: list[str]


def answer_questions(engine, questions: list[Question], refresh=False, progress=None):
    lines, errors = [], []
    for i, question in enumerate(questions, 1):
        try:
            value = engine.answer(question.text, refresh) if question.text else {'answer': '?', 'reason': '题目识别不完整或两遍 OCR 不一致，请重新框选或校正文字。'}
            letter = str(value.get('answer', '?'))
            letter = letter.upper() if letter.upper() in ('T','F') else letter.lower()
            if letter not in ('a', 'b', 'c', 'd', 'T', 'F'):
                letter = '?'
            if letter == '?' and value.get('reason'):
                errors.append(value['reason'])
        except ValueError as exc:
            letter = '?'
            errors.append(str(exc))
        lines.append(letter if len(questions) == 1 and letter in ('T','F') else f'{question.number}. {letter}')
        if progress:
            progress(i, len(questions))
    return Answers('\n'.join(lines), errors)
