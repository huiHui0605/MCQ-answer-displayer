"""Exercise actual UI handlers with Tk drawing mocked; no display required."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest
from app import FloatingApp
from screen_scan import ScanResult, Question
from answers import Answers


class FloatingTests(unittest.TestCase):
    def setUp(self):
        self.root=Mock()
        self.root.cget.return_value='#ff00ff'
        self.root.winfo_screenwidth.return_value=1920
        self.root.winfo_screenheight.return_value=1080
        self.root.winfo_x.return_value=80
        self.root.winfo_y.return_value=100
        self.patch=patch('app.tk.Canvas')
        self.canvas=self.patch.start().return_value
        self.addCleanup(self.patch.stop)
        self.app=FloatingApp(self.root,engine=Mock(),reader=Mock())
        self.app.background=Mock()

    def click(self):
        event=SimpleNamespace(x_root=90,y_root=110)
        self.app.press(event)
        self.app.release(event)

    def test_circle_has_transparent_windows_background_and_no_titlebar(self):
        self.root.overrideredirect.assert_called_once_with(True)
        self.root.attributes.assert_any_call('-transparentcolor','#ff00ff')
        self.canvas.create_oval.assert_called()
        self.assertEqual(self.app.mode,'idle')

    def test_answer_click_returns_circle_without_rescanning(self):
        self.app.show_answers('1. b\n2. c')
        self.click()
        self.assertEqual(self.app.mode,'idle')
        self.app.background.assert_not_called()
        self.canvas.create_text.assert_called_with(34,34,text='MCQ',fill='white',font=('Segoe UI',11,'bold'))

    def test_repeated_scan_answer_click_cycle(self):
        for _ in range(2):
            self.click()
            self.assertEqual(self.app.mode,'busy')
            self.root.withdraw.assert_called()
            # Capture completion is delivered once, OCR once, then local answers.
            self.app.events.put(('captured',object()))
            self.app.poll()
            self.assertEqual(self.app.background.call_args.args[0],'scanned')
            self.app.events.put(('scanned',ScanResult('',True,questions=[Question('1','question')])) )
            self.app.poll()
            self.assertEqual(self.app.background.call_args.args[0],'answer')
            self.app.events.put(('answer',Answers('1. b',[])))
            self.app.poll()
            self.assertEqual(self.app.mode,'answer')
            self.assertEqual(self.app.last_answers,'1. b')
            self.click()
            self.assertEqual(self.app.mode,'idle')

    def test_busy_click_does_not_launch_duplicate_capture(self):
        self.app.mode='busy'
        self.click()
        self.app.background.assert_not_called()

    def test_drag_moves_without_scan(self):
        self.app.press(SimpleNamespace(x_root=90,y_root=110))
        self.app.move(SimpleNamespace(x_root=120,y_root=150))
        self.app.release(SimpleNamespace(x_root=120,y_root=150))
        self.assertEqual(self.app.anchor,(110,140))
        self.assertEqual(self.app.mode,'idle')
        self.app.background.assert_not_called()

    def test_failed_ocr_is_click_to_dismiss_question_mark(self):
        self.app.events.put(('scanned',ScanResult('',False,'ambiguous layout')))
        self.app.poll()
        self.assertEqual(self.app.last_answers,'?')
        self.assertEqual(self.app.last_error,'ambiguous layout')
        self.click()
        self.assertEqual(self.app.mode,'idle')


if __name__=='__main__': unittest.main()
