import unittest
from unittest.mock import Mock
from mouse_wake import RightClickWake


class MouseWakeTests(unittest.TestCase):
    def test_only_right_press_then_release_wakes_once(self):
        root, callback = Mock(), Mock()
        state = Mock(side_effect=[0, 0x8000, 0x8000, 0, 0])
        wake = RightClickWake(root, callback, get_state=state)
        wake.arm()
        for _ in range(3):
            wake.poll()
            callback.assert_not_called()
        wake.poll()
        callback.assert_called_once_with()
        self.assertFalse(wake.armed)
        wake.poll()
        self.assertEqual(state.call_count, 4)
        self.assertTrue(all(call.args == (0x02,) for call in state.call_args_list))

    def test_cancel_removes_timer_and_stops_reading(self):
        root, callback, state = Mock(), Mock(), Mock()
        wake = RightClickWake(root, callback, get_state=state)
        wake.arm()
        wake.cancel()
        root.after_cancel.assert_called_once()
        wake.poll()
        state.assert_not_called()
        callback.assert_not_called()

    def test_old_press_bit_does_not_wake(self):
        callback = Mock()
        wake = RightClickWake(Mock(), callback, get_state=Mock(return_value=1))
        wake.arm()
        wake.poll()
        callback.assert_not_called()

    def test_native_failure_restores_icon_instead_of_leaving_app_hidden(self):
        callback = Mock()
        wake = RightClickWake(Mock(), callback, get_state=Mock(side_effect=OSError()))
        wake.arm()
        wake.poll()
        callback.assert_called_once_with()
        self.assertFalse(wake.armed)


if __name__ == '__main__':
    unittest.main()
