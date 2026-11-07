import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch,Mock
import core
from answers import answer_questions
from screen_scan import Question

QUESTION='What is the capital of France?\nA. Paris\nB. Madrid\nC. Rome\nD. Berlin'


def reply(letter,confidence='high'):
    return {'done':True,'message':{'content':json.dumps({'answer':letter,'confidence':confidence})}}


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        for p in (patch.object(core,'DATA',Path(self.directory.name)),patch.dict('os.environ',{'MCQ_MODEL':'qwen2.5:3b'})):
            p.start()
            self.addCleanup(p.stop)
        self.engine=core.Engine([],'no-notes')

    def responses(self,*items):
        return patch('core.local_request',side_effect=[{'models':[{'name':'qwen2.5:3b'}]}, {}, *items])

    def test_answers_without_any_notes_or_quotes(self):
        with self.responses(reply('A'),reply('D')) as request:
            result=self.engine.answer(QUESTION)
            self.assertEqual(result['answer'],'A')
            self.assertEqual(result['basis'],'general_knowledge')
            self.assertEqual(result['references'],[])
            prompt=request.call_args_list[2].args[1]
            self.assertIn('general knowledge',prompt['messages'][0]['content'])
            self.assertIn('optional references',prompt['messages'][0]['content'])
            self.assertEqual(prompt['format']['required'],['answer','confidence'])

    def test_optional_notes_folder_may_be_empty(self):
        root=Path(self.directory.name)/'project'
        root.mkdir()
        with patch.object(core,'ROOT',root):
            pages,_=core.load_pages()
            self.assertEqual(pages,[])

    def test_unrelated_notes_do_not_make_answering_impossible(self):
        self.engine=core.Engine([{'file':'business.pdf','page':1,'text':'A business plan includes financial forecasts.'}],'irrelevant')
        with self.responses(reply('A'),reply('D')):
            self.assertEqual(self.engine.answer(QUESTION)['answer'],'A')

    def test_true_false_uses_knowledge_without_notes(self):
        question='Paris is the capital of France.\nTrue\nFalse'
        with self.responses(reply('T'),reply('T')):
            result=self.engine.answer(question)
        engine=Mock()
        engine.answer.return_value=result
        self.assertEqual(answer_questions(engine,[Question('1',question)]).text,'T')

    def test_low_confidence_still_abstains_with_specific_reason(self):
        with self.responses(reply('A','low')):
            result=self.engine.answer(QUESTION)
            self.assertEqual(result['answer'],'?')
            self.assertIn('无法可靠判断',result['reason'])
            self.assertFalse(self.engine.cache)

    def test_disagreement_has_specific_reason(self):
        with self.responses(reply('A'),reply('B')):
            result=self.engine.answer(QUESTION)
            self.assertEqual(result['answer'],'?')
            self.assertIn('两次判断不一致',result['reason'])

    def test_unknown_reason_reaches_right_click_diagnostics(self):
        engine=Mock()
        engine.answer.return_value={'answer':'?','reason':'本地模型无法判断'}
        result=answer_questions(engine,[Question('1',QUESTION)])
        self.assertEqual(result.text,'1. ?')
        self.assertEqual(result.errors,['本地模型无法判断'])

    def test_ocr_failure_is_not_silently_called_model_uncertainty(self):
        engine=Mock()
        result=answer_questions(engine,[Question('1','')])
        engine.answer.assert_not_called()
        self.assertIn('OCR',result.errors[0])


if __name__=='__main__': unittest.main()
