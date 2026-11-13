import unittest
from unittest.mock import Mock
import numpy as np
from answers import answer_questions
from screen_scan import Question, crop_region, prepare_image, prepare_questions

Q = 'Which protects an invention?\nA. Patent\nB. Trademark\nC. Copyright\nD. Franchise'


class BatchTests(unittest.TestCase):
    def test_numbered_batch_preserves_numbers(self):
        result = prepare_questions(('5. ' + Q + '\n6. ' + Q).splitlines())
        self.assertTrue(result.ready, result.warning)
        self.assertEqual([q.number for q in result.questions], ['5', '6'])
        self.assertTrue(all(q.text.startswith('Which') for q in result.questions))

    def test_question_heading_and_separate_number(self):
        for prefix in ['Question 7\n', '7.\n', 'Q7: ']:
            result = prepare_questions((prefix + Q).splitlines())
            self.assertTrue(result.ready, result.warning)
            self.assertEqual(result.questions[0].number, '7')

    def test_single_unnumbered_defaults_to_one(self):
        result = prepare_questions(Q.splitlines())
        self.assertTrue(result.ready)
        self.assertEqual(result.questions[0].number, '1')

    def test_missing_or_duplicate_number_requires_edit(self):
        for num in ['5', '7']:
            self.assertFalse(prepare_questions(('5. '+Q+'\n'+num+'. '+Q).splitlines()).ready)

    def test_unnumbered_batch_requires_edit(self):
        self.assertFalse(prepare_questions((Q+'\n'+Q).splitlines()).ready)

    def test_dont_silently_drop_unnumbered_first_question(self):
        self.assertFalse(prepare_questions((Q+'\n2. '+Q).splitlines()).ready)

    def test_partial_batch_requires_edit(self):
        self.assertFalse(prepare_questions(('1. '+Q+'\n2. Incomplete?\nA. Option').splitlines()).ready)

    def test_output_has_only_numbers_and_lowercase_answers(self):
        engine = Mock()
        engine.answer.side_effect = [dict(answer='B', explanation='NEVER SHOW THIS', references=['hidden']), dict(answer='C')]
        progress = Mock()
        result = answer_questions(engine, [Question('1', Q), Question('2', Q)], progress=progress)
        self.assertEqual(result.text, '1. b\n2. c')
        self.assertEqual(result.errors, [])
        self.assertEqual(progress.call_count, 2)

    def test_unknown_and_failed_questions_remain_in_order(self):
        engine = Mock()
        engine.answer.side_effect = [dict(answer='?'), ValueError('model unavailable'), dict(answer='D')]
        result = answer_questions(engine, [Question(str(n), Q) for n in (3,4,5)])
        self.assertEqual(result.text, '3. ?\n4. ?\n5. d')
        self.assertEqual(result.errors, ['model unavailable'])

    def test_crop_uses_only_selected_region_and_accepts_reverse_drag(self):
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        image[40:120, 50:200] = 127
        crop = crop_region(image, (200,120), (50,40))
        self.assertEqual(crop.shape, (80,150,3))
        self.assertTrue((crop == 127).all())
        crop[:] = 0
        self.assertTrue((image[40:120,50:200] == 127).all())

    def test_crop_clamps_bounds_and_rejects_tiny_selections(self):
        image = np.zeros((200, 300, 3), dtype=np.uint8)
        self.assertEqual(crop_region(image, (-10,-10), (1000,1000)).shape, image.shape)
        with self.assertRaises(ValueError): crop_region(image, (0,0), (5,5))

    def test_small_text_image_is_enlarged_and_bordered(self):
        image = np.zeros((200,300,3), dtype=np.uint8)
        result = prepare_image(image)
        self.assertEqual(result.shape, (632,932,3))
        self.assertTrue((result[0] == 255).all())

    def test_real_english_numbered_batch_ocr(self):
        import cv2
        from screen_scan import ScreenReader
        image = np.full((1200, 1400, 3), 255, dtype=np.uint8)
        lines = ('1. '+Q+'\n2. '+Q).splitlines()
        for n, line in enumerate(lines):
            cv2.putText(image, line, (35,65+n*105), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0,0,0), 2, cv2.LINE_AA)
        result = ScreenReader().read(image)
        self.assertTrue(result.ready, result.text+'\n'+result.warning)
        self.assertEqual([q.number for q in result.questions], ['1','2'])
        self.assertTrue(all('Patent' in q.text for q in result.questions))


if __name__ == '__main__': unittest.main()
