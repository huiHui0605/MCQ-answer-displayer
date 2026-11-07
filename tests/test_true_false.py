import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock,patch
import cv2
import numpy as np
import core
from answers import answer_questions
from auto_scan import scan_screen,scan_selected_area
from screen_scan import prepare_questions,Question,ScreenReader

TF='A patent protects an invention.\nTrue\nFalse'
QUOTE='A patent protects an invention.'


class TrueFalseTests(unittest.TestCase):
    def test_plain_and_labeled_true_false_choices(self):
        for choices in ['True\nFalse','False\nTrue','T. True\nF. False','A. True\nB. False','A. False\nB. True','True False']:
            result=prepare_questions(('3. A patent protects an invention.\n'+choices).splitlines())
            self.assertTrue(result.ready,result.warning)
            self.assertEqual(result.questions[0].number,'3')
            self.assertTrue(result.questions[0].text.endswith('T. True\nF. False'))

    def test_four_choices_with_true_false_distractors_remain_mcq(self):
        result=prepare_questions('Which answer?\nA. True\nB. False\nC. Neither\nD. Both'.splitlines())
        self.assertTrue(result.ready)
        self.assertIn('D. Both',result.questions[0].text)
        self.assertNotIn('T. True',result.questions[0].text)

    def test_true_word_inside_statement_is_not_a_choice(self):
        result=prepare_questions('It is true that patents exist.\nA. Patent\nB. Trademark\nC. Copyright\nD. Franchise'.splitlines())
        self.assertTrue(result.ready)
        self.assertNotIn('T. True',result.questions[0].text)

    def test_single_t_f_has_no_number_or_explanation(self):
        engine=Mock()
        for letter in ('T','F'):
            engine.answer.return_value={'answer':letter,'explanation':'never show'}
            result=answer_questions(engine,[Question('7',TF)])
            self.assertEqual(result.text,letter)

    def test_mixed_batch_keeps_numbers_and_letter_case(self):
        engine=Mock()
        engine.answer.side_effect=[{'answer':'B'},{'answer':'T'},{'answer':'F'}]
        result=answer_questions(engine,[Question('1','mcq'),Question('2',TF),Question('3',TF)])
        self.assertEqual(result.text,'1. b\n2. T\n3. F')

    def test_true_false_schema_and_consistency_check(self):
        for letter in ('T','F'):
            with tempfile.TemporaryDirectory() as directory,patch.object(core,'DATA',Path(directory)),patch.dict('os.environ',{'MCQ_MODEL':'qwen2.5:3b'}):
                engine=core.Engine([{'file':'notes.pdf','page':1,'text':QUOTE}],'tf')
                data={'answer':letter,'confidence':'high','explanation':'Internal','sources':[1],
                      'evidence':[{'source':1,'quote':QUOTE}]}
                reply={'done':True,'message':{'content':json.dumps(data)}}
                with patch('core.local_request',side_effect=[{'models':[{'name':'qwen2.5:3b'}]}, {},reply,reply]) as request:
                    self.assertEqual(engine.answer(TF)['answer'],letter)
                    payload=request.call_args.args[1]
                    self.assertEqual(payload['format']['properties']['answer']['enum'],['T','F','?'])
                    self.assertIn('T. True\nF. False',json.loads(payload['messages'][1]['content'])['question'])

    def test_real_screen_true_false_ocr(self):
        image=np.full((800,1300,3),255,dtype=np.uint8)
        for text,x,y in [('3. A patent protects an invention.',200,180),('True',220,300),('False',220,400)]:
            cv2.putText(image,text,(x,y),cv2.FONT_HERSHEY_SIMPLEX,1.,(0,0,0),2,cv2.LINE_AA)
        result=scan_screen(ScreenReader(),image)
        self.assertTrue(result.ready,result.warning)
        self.assertEqual(result.questions[0].number,'3')
        self.assertIn('T. True',result.questions[0].text)

    def test_selected_area_does_not_require_question_anchor_words(self):
        image=np.full((650,1200,3),255,dtype=np.uint8)
        for i,text in enumerate(['Creativity can generate business ideas.','True','False']):
            cv2.putText(image,text,(40,100+i*140),cv2.FONT_HERSHEY_SIMPLEX,.9,(0,0,0),2,cv2.LINE_AA)
        result=scan_selected_area(ScreenReader(),image)
        self.assertTrue(result.ready,result.warning)
        self.assertTrue(result.questions[0].text)


if __name__=='__main__': unittest.main()
