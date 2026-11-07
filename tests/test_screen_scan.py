"""Screen OCR and scan-to-answer tests. No desktop capture or cloud needed."""
import tempfile
from pathlib import Path
from unittest.mock import patch
import unittest

import core
from screen_scan import ScreenReader, capture_screen, prepare_question

LINES = ['Which intellectual property protects an invention?', 'A. Patent', 'B. Trademark', 'C. Copyright', 'D. Franchise']


class ScanTests(unittest.TestCase):
    def test_standard_options(self):
        self.assertTrue(prepare_question(LINES).ready)

    def test_inline_options(self):
        result = prepare_question([LINES[0], 'A. Patent B. Trademark C. Copyright D. Franchise'])
        self.assertTrue(result.ready)
        self.assertIn('\nD. Franchise', result.text)

    def test_separate_labels(self):
        result = prepare_question([LINES[0], 'A', 'Patent', 'B', 'Trademark', 'C', 'Copyright', 'D', 'Franchise'])
        self.assertTrue(result.ready)

    def test_multiple_questions_require_edit(self):
        self.assertFalse(prepare_question(LINES + LINES).ready)

    def test_missing_option_requires_edit(self):
        self.assertFalse(prepare_question(LINES[:-1]).ready)

    def test_missing_stem_requires_edit(self):
        self.assertFalse(prepare_question(LINES[1:]).ready)

    def test_empty_option_requires_edit(self):
        self.assertFalse(prepare_question([*LINES[:-1], 'D.']).ready)

    def test_full_width_labels(self):
        result = prepare_question([LINES[0], 'Ａ）Patent', 'Ｂ）Trademark', 'Ｃ）Copyright', 'Ｄ）Franchise'])
        self.assertTrue(result.ready)

    def test_low_confidence_requires_edit(self):
        reader = ScreenReader.__new__(ScreenReader)
        reader.ocr = lambda image: ([[[], text, .5] for text in LINES], None)
        self.assertFalse(reader.read(None).ready)

    def test_no_text(self):
        reader = ScreenReader.__new__(ScreenReader)
        reader.ocr = lambda image: (None, None)
        self.assertFalse(reader.read(None).ready)

    def test_capture_failure_is_actionable(self):
        with patch('mss.mss', side_effect=RuntimeError('no display')):
            with self.assertRaisesRegex(ValueError, '权限'):
                capture_screen()

    def test_primary_monitor_and_color_channels(self):
        import numpy as np
        screenshot = np.zeros((2, 3, 4), dtype=np.uint8)
        screenshot[:] = [10, 20, 30, 255]  # B G R A
        with patch('mss.mss') as create:
            capture = create.return_value.__enter__.return_value
            primary = {'left': 0, 'top': 0, 'width': 3, 'height': 2}
            capture.monitors = [{}, {'left': -1920, 'top': 0}, primary]
            capture.grab.return_value = screenshot
            image = capture_screen()
            capture.grab.assert_called_once_with(primary)
        self.assertEqual(image.shape, (2, 3, 3))
        self.assertEqual(image[0, 0].tolist(), [10, 20, 30])

    def test_real_offline_ocr_to_answer_pipeline(self):
        import cv2
        import numpy as np
        image = np.full((650, 1400, 3), 255, dtype=np.uint8)
        for i, line in enumerate(LINES):
            cv2.putText(image, line, (40, 70 + i*105), cv2.FONT_HERSHEY_SIMPLEX, 1.15, (0, 0, 0), 2, cv2.LINE_AA)
        # The real OCR weights are bundled. Block Python network requests during initialization and OCR.
        with patch('socket.create_connection', side_effect=AssertionError('OCR must be offline')):
            result = ScreenReader().read(image)
        self.assertTrue(result.ready, result.text + result.warning)
        self.assertIn('Patent', result.text)
        with tempfile.TemporaryDirectory() as temporary, patch.object(core, 'DATA', Path(temporary)), patch.dict('os.environ', {'MCQ_MODEL': 'qwen2.5:3b'}):
            engine = core.Engine([{'file': 'example.pdf', 'page': 1, 'text': 'A patent protects an invention.'}], 'example')
            reply = {'done': True, 'message': {'content': '{"answer":"A","confidence":"high","explanation":"Patent","sources":[1],"evidence":[{"source":1,"quote":"A patent protects an invention."}]}'}}
            with patch('core.local_request', side_effect=[{'models': [{'name': 'qwen2.5:3b'}]}, {}, reply, {**reply, 'message': {'content': reply['message']['content'].replace('"answer":"A"', '"answer":"D"')}}]):
                answer = engine.answer(result.text)
            self.assertEqual(answer['answer'], 'A')
            self.assertEqual(answer['references'][0]['page'], 1)


if __name__ == '__main__':
    unittest.main()
