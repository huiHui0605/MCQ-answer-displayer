"""Regressions for the small English quiz shown in the reported screenshot."""
import unittest
from pathlib import Path
from unittest.mock import Mock

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from auto_scan import scan_selected_area
from screen_scan import ScreenReader, prepare_questions


LINES = ['1. An individual who starts, creates and manages a new business can be called',
         '______________.', 'A. A leader', 'B. A manager', 'C. A professional',
         'D. An entrepreneur', 'ANSWER: D']


class SelectedOCRTests(unittest.TestCase):
    def test_degraded_raw_pass_no_longer_vetoes_enlarged_read(self):
        reader = Mock()
        reader.ocr.return_value = (None, None)
        reader.read.return_value = prepare_questions(LINES)
        result = scan_selected_area(reader, object())
        self.assertTrue(result.ready)
        self.assertTrue(result.questions[0].text)
        reader.ocr.assert_not_called()

    def test_answer_keys_and_blank_rules_do_not_change_options(self):
        result = prepare_questions(LINES)
        self.assertTrue(result.ready)
        self.assertNotIn('ANSWER', result.questions[0].text)
        self.assertNotIn('____', result.questions[0].text)
        self.assertTrue(result.questions[0].text.endswith('D. An entrepreneur'))

    def test_low_confidence_decoration_and_answer_key_are_ignored(self):
        reader = ScreenReader.__new__(ScreenReader)
        reader.ocr = Mock(return_value=([[[], line, .1 if i in (1,6) else .99]
                                        for i,line in enumerate(LINES)], None))
        result = scan_selected_area(reader, None)
        self.assertTrue(result.ready, result.warning)

    def test_low_confidence_question_words_still_require_correction(self):
        reader = ScreenReader.__new__(ScreenReader)
        reader.ocr = Mock(return_value=([[[], line, .5 if i == 0 else .99]
                                        for i,line in enumerate(LINES)], None))
        result = scan_selected_area(reader, None)
        self.assertFalse(result.ready)
        self.assertIn('individual', result.warning)

    def test_missing_choice_is_not_reconstructed_from_printed_answer(self):
        result = prepare_questions(LINES[:5] + ['ANSWER: D'])
        self.assertFalse(result.ready)

    def test_inline_answer_key_and_true_false(self):
        result = prepare_questions(['2. A patent protects an invention.',
                                    'True', 'False ANSWER: True'])
        self.assertTrue(result.ready, result.warning)
        self.assertEqual(result.questions[0].number, '2')
        self.assertTrue(result.questions[0].text.endswith('T. True\nF. False'))

    def test_answer_words_in_stem_or_options_are_preserved(self):
        lines = ['Which answer is NOT correct?', 'A. The answer is true',
                 'B. Answer: context matters', 'C. 1.5 percent', 'D. 15 percent']
        result = prepare_questions(lines)
        self.assertTrue(result.ready)
        for phrase in ('NOT', 'answer is true', 'Answer: context matters', '1.5', '15'):
            self.assertIn(phrase, result.questions[0].text)

    def test_real_small_serif_quiz(self):
        fonts = [Path('C:/Windows/Fonts/times.ttf'),
                 Path('/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf')]
        path = next((path for path in fonts if path.exists()), None)
        if path is None:
            self.skipTest('Needs Times New Roman or DejaVu Serif')
        font = ImageFont.truetype(str(path), 13)
        image = Image.new('RGB', (660, 160), 'white')
        draw = ImageDraw.Draw(image)
        for i,line in enumerate(LINES):
            draw.text((12, 10+i*19), line, font=font, fill='black')
        result = scan_selected_area(ScreenReader(), np.array(image)[:, :, ::-1].copy())
        self.assertTrue(result.ready, result.text + result.warning)
        self.assertEqual(len(result.questions), 1)
        text = result.questions[0].text
        self.assertIn('entrepreneur', text)
        self.assertNotIn('ANSWER', text)
        self.assertIn('new business', text)


if __name__ == '__main__':
    unittest.main()
