"""Exercise actual UI handlers with Tk drawing mocked; no display required."""
from types import SimpleNamespace
from unittest.mock import Mock, patch
import unittest
from app import FloatingApp, IDLE_SYMBOL
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
        wake_patch=patch('app.RightClickWake')
        self.wake=wake_patch.start().return_value
        self.wake.available=True
        self.addCleanup(wake_patch.stop)
        with patch('app.load_settings',return_value={}):
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

    def test_answer_click_hides_then_right_click_restores_without_rescanning(self):
        self.app.show_answers('1. b\n2. c')
        self.click()
        self.assertEqual(self.app.mode,'hidden')
        self.root.withdraw.assert_called()
        self.wake.arm.assert_called()
        self.app.restore()
        self.assertEqual(self.app.mode,'idle')
        self.app.background.assert_not_called()
        self.assertEqual(self.canvas.create_text.call_args.kwargs['text'],IDLE_SYMBOL)

    def test_repeated_scan_answer_click_cycle(self):
        for _ in range(2):
            self.click()
            self.assertEqual(self.app.mode,'busy')
            self.root.withdraw.assert_called()
            # Capture completion is delivered once, OCR once, then local answers.
            image=object()
            self.app.events.put(('captured',image))
            with patch.object(self.app,'choose_region') as choose:
                self.app.poll()
                choose.assert_called_once_with(image)
            self.app.events.put(('scanned',ScanResult('',True,questions=[Question('1','question')])) )
            self.app.poll()
            self.assertEqual(self.app.background.call_args.args[0],'answer')
            self.app.events.put(('answer',Answers('1. b',[])))
            self.app.poll()
            self.assertEqual(self.app.mode,'answer')
            self.assertEqual(self.app.last_answers,'1. b')
            self.click()
            self.assertEqual(self.app.mode,'hidden')
            self.app.restore()
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

    def test_current_crop_is_used_instead_of_previous_saved_region(self):
        import numpy as np
        from settings import make_region
        image=np.zeros((800,1200,3),dtype=np.uint8)
        self.app.settings={'region':make_region(image.shape,(100,100),(900,700))}
        crop=image[50:400,70:600].copy()
        with patch('app.scan_selected_area') as scan:
            self.app.process_image(crop)
            self.assertEqual(scan.call_args.args[1].shape,(350,530,3))

    def test_model_choice_is_saved_and_applied(self):
        self.app.events.put(('model_ready','qwen2.5:7b'))
        with patch('app.save_settings') as save:
            self.app.poll()
            save.assert_called_once_with({'model':'qwen2.5:7b'})
        self.assertEqual(self.app.engine.model,'qwen2.5:7b')
        self.assertEqual(self.app.mode,'idle')

    def test_every_scan_opens_a_new_selection_before_ocr(self):
        for _ in range(2):
            self.app.mode='idle'
            self.app.scan()
            self.app.events.put(('captured',object()))
            with patch.object(self.app,'choose_region') as select:
                self.app.poll()
                select.assert_called_once()
        self.app.background.assert_not_called()

    def test_selector_release_crops_only_this_drag_without_saving_region(self):
        import numpy as np
        image=np.zeros((800,1200,3),dtype=np.uint8)
        original_settings={'model':'qwen2.5:3b','region':{'old':'unused'}}
        self.app.settings=original_settings.copy()
        with patch('app.tk.Toplevel'),patch('app.tk.Canvas') as canvas_factory,patch('PIL.ImageTk.PhotoImage'),patch('app.save_settings') as save:
            canvas=canvas_factory.return_value
            self.app.choose_region(image)
            handlers={call.args[0]:call.args[1] for call in canvas.bind.call_args_list}
            handlers['<ButtonPress-1>'](SimpleNamespace(x=100,y=120))
            handlers['<ButtonRelease-1>'](SimpleNamespace(x=900,y=720))
            save.assert_not_called()
            self.assertEqual(self.app.settings,original_settings)
            kind,fn=self.app.background.call_args.args
            self.assertEqual(kind,'scanned')
            with patch('app.scan_selected_area') as scan:
                fn()
                self.assertEqual(scan.call_args.args[1].shape,(600,800,3))

    def test_selector_escape_returns_to_icon_without_scanning(self):
        import numpy as np
        with patch('app.tk.Toplevel') as top,patch('app.tk.Canvas'),patch('PIL.ImageTk.PhotoImage'):
            overlay=top.return_value
            self.app.choose_region(np.zeros((800,1200,3),dtype=np.uint8))
            handlers={call.args[0]:call.args[1] for call in overlay.bind.call_args_list}
            handlers['<Escape>'](SimpleNamespace())
            self.assertEqual(self.app.mode,'idle')
            self.assertIsNone(self.app.selector)
            self.app.background.assert_not_called()

    def test_corrected_editor_uses_question_text_sent_to_model(self):
        result=ScanResult('Home menu unrelated',True,questions=[Question('1','actual question')])
        self.app.events.put(('scanned',result))
        self.app.poll()
        self.assertEqual(self.app.last_text,'1. actual question')

    def test_failed_ocr_is_click_to_dismiss_question_mark(self):
        self.app.events.put(('scanned',ScanResult('',False,'ambiguous layout')))
        self.app.poll()
        self.assertEqual(self.app.last_answers,'?')
        self.assertEqual(self.app.last_error,'ambiguous layout')
        self.click()
        self.assertEqual(self.app.mode,'hidden')
        self.root.withdraw.assert_called()
        self.wake.arm.assert_called()
        self.app.restore()
        self.assertEqual(self.app.mode,'idle')


    def test_right_click_restore_does_not_interrupt_other_states(self):
        for mode in ('idle', 'busy', 'answer', 'loading'):
            self.app.mode=mode
            self.app.restore()
            self.assertEqual(self.app.mode,mode)
        self.app.background.assert_not_called()

    def test_unsupported_platform_keeps_icon_reachable(self):
        self.wake.available=False
        self.app.show_answers('T')
        self.click()
        self.assertEqual(self.app.mode,'idle')
        self.wake.arm.assert_not_called()

    def test_close_cancels_mouse_polling(self):
        self.app.show_answers('F')
        self.click()
        self.app.close()
        self.wake.cancel.assert_called()
        self.app.restore()
        self.assertTrue(self.app.closed)
        self.assertEqual(self.app.mode,'hidden')


if __name__=='__main__': unittest.main()
