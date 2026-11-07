import unittest
from unittest.mock import Mock
import cv2
import numpy as np
from auto_scan import locate_blocks, scan_screen
from screen_scan import Question, ScanResult, ScreenReader


def row(text, x, y, width=650, score=.99):
    return [[[x,y],[x+width,y],[x+width,y+30],[x,y+30]], text, score]


def example(number=7, y=100):
    return [row(f'{number}. Which protects an invention?', 220, y),
            row('A. Patent',220,y+80), row('B. Trademark',220,y+160),
            row('C. Copyright',220,y+240), row('D. Franchise',220,y+320)]


class AutoScanTests(unittest.TestCase):
    def test_browser_header_and_submit_are_excluded(self):
        rows = [row('Home Profile Settings',20,10), *example(), row('Submit answer',220,600)]
        blocks = locate_blocks(rows, (1000,1400,3))
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].number, '7')
        self.assertTrue(blocks[0].complete)
        self.assertEqual(len(blocks[0].rows),5)
        self.assertNotIn('Submit', str(blocks))

    def test_incomplete_question_is_marked_unknown(self):
        rows = example()[:-1]
        reader = Mock()
        reader.ocr.return_value = rows, None
        result = scan_screen(reader, np.zeros((1000,1400,3), dtype=np.uint8))
        self.assertTrue(result.ready)
        self.assertEqual(result.questions, [Question('7','')])
        reader.read.assert_not_called()

    def test_ocr_disagreement_on_not_requires_unknown(self):
        rows = example()
        reader = Mock()
        reader.ocr.return_value = rows, None
        reader.read.return_value = ScanResult('', True, questions=[Question('7',
            'Which does NOT protect an invention?\nA. Patent\nB. Trademark\nC. Copyright\nD. Franchise')])
        result = scan_screen(reader, np.zeros((1000,1400,3), dtype=np.uint8))
        self.assertEqual(result.questions[0].text,'')

    def test_low_first_pass_confidence_does_not_get_hidden_by_second(self):
        rows = example()
        rows[1][2]=.6
        reader = Mock()
        reader.ocr.return_value = rows, None
        text = 'Which protects an invention?\nA. Patent\nB. Trademark\nC. Copyright\nD. Franchise'
        reader.read.return_value = ScanResult('',True, questions=[Question('7',text)])
        self.assertEqual(scan_screen(reader, np.zeros((1000,1400,3),dtype=np.uint8)).questions[0].text,'')

    def test_question_number_disagreement_is_not_silently_accepted(self):
        reader=Mock()
        reader.ocr.return_value=example(),None
        text='Which protects an invention?\nA. Patent\nB. Trademark\nC. Copyright\nD. Franchise'
        reader.read.return_value=ScanResult('',True,questions=[Question('1',text)])
        result=scan_screen(reader,np.zeros((1000,1400,3),dtype=np.uint8))
        self.assertEqual(result.questions[0].text,'')

    def test_two_questions_preserve_numbers(self):
        rows = example(7,100)+example(8,600)
        self.assertEqual([b.number for b in locate_blocks(rows,(1200,1400,3))], ['7','8'])

    def test_wrapped_last_option_is_not_cut_off(self):
        rows = example()+[row('The company keeps the information confidential.',220,455),
                          row('Submit answer',220,490)]
        block = locate_blocks(rows,(1000,1400,3))[0]
        self.assertEqual(len(block.rows),6)
        self.assertIn('confidential',block.rows[-1][1])
        self.assertLessEqual(block.bounds[3],490)  # exclusive crop boundary

    def test_no_mcq_returns_no_answer(self):
        reader=Mock()
        reader.ocr.return_value=[row('News and weather',20,20)],None
        self.assertFalse(scan_screen(reader,np.zeros((600,1000,3),dtype=np.uint8)).ready)

    def test_cross_column_labels_not_merged(self):
        rows=example()
        rows[3]=row('C. Copyright',950,340)
        self.assertTrue(all(not b.complete for b in locate_blocks(rows,(1000,1600,3))))

    def test_interleaved_columns_are_separated(self):
        left=example(1,100)
        right=example(2,100)
        for r in right:
            for point in r[0]: point[0]+=730
        blocks=locate_blocks(left+right,(1000,1800,3))
        self.assertEqual([b.number for b in blocks],['1','2'])
        self.assertTrue(all(b.complete for b in blocks))
        self.assertTrue(all(len(b.rows)==5 for b in blocks))

    def test_real_two_column_english_page(self):
        image=np.full((1100,1800,3),255,dtype=np.uint8)
        for n,x in [(1,50),(2,950)]:
            for k,text in enumerate([f'{n}. Which protects an invention?','A. Patent','B. Trademark','C. Copyright','D. Franchise']):
                cv2.putText(image,text,(x,150+k*100),cv2.FONT_HERSHEY_SIMPLEX,.85,(0,0,0),2,cv2.LINE_AA)
        result=scan_screen(ScreenReader(),image)
        self.assertTrue(result.ready,result.warning)
        self.assertEqual([q.number for q in result.questions],['1','2'])
        self.assertTrue(all(q.text for q in result.questions))

    def test_real_auto_localization_and_two_pass_english_ocr(self):
        image=np.full((1000,1600,3),255,dtype=np.uint8)
        lines=[('Home Courses Profile',30,45,.7),
               ('7. Which intellectual property protects an invention?',300,220,1.),
               ('A. Patent',300,320,1.),('B. Trademark',300,420,1.),
               ('C. Copyright',300,520,1.),('D. Franchise',300,620,1.),
               ('Submit answer',300,800,.8)]
        for text,x,y,size in lines:
            cv2.putText(image,text,(x,y),cv2.FONT_HERSHEY_SIMPLEX,size,(0,0,0),2,cv2.LINE_AA)
        result=scan_screen(ScreenReader(),image)
        self.assertTrue(result.ready,result.warning)
        self.assertEqual(result.questions[0].number,'7')
        self.assertIn('Patent',result.questions[0].text)
        self.assertNotIn('Home',result.questions[0].text)
        self.assertNotIn('Submit',result.questions[0].text)


if __name__=='__main__': unittest.main()
