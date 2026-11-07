import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import core

Q='What protects an invention?\nA. Patent\nB. Trademark\nC. Copyright\nD. Franchise'
QUOTE='A patent protects an invention.'


def response(letter, quote=QUOTE):
    answer={'answer':letter,'confidence':'high','explanation':'Internal only',
            'sources':[1],'evidence':[{'source':1,'quote':quote}]}
    return {'done':True,'message':{'content':json.dumps(answer)}}


class AccuracyTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        for patcher in [patch.object(core,'DATA',Path(self.temporary.name)),
                        patch.dict('os.environ',{'MCQ_MODEL':'qwen2.5:3b'})]:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.engine=core.Engine([{'file':'notes.pdf','page':1,'text':QUOTE}],'test')

    def requests(self,*responses):
        return patch('core.local_request',side_effect=[{'models':[{'name':'qwen2.5:3b'}]}, {}, *responses])

    def test_order_consistent_answer_accepted(self):
        with self.requests(response('A'),response('D')) as request:
            self.assertEqual(self.engine.answer(Q)['answer'],'A')
            second=request.call_args_list[-1].args[1]
            text=json.loads(second['messages'][1]['content'])['question']
            self.assertIn('A. Franchise',text)
            self.assertIn('D. Patent',text)
            self.assertNotIn('first_answer',second['messages'][1]['content'])

    def test_order_bias_or_conflicting_answer_not_cached(self):
        with self.requests(response('A'),response('A')):
            self.assertEqual(self.engine.answer(Q)['answer'],'?')
            self.assertEqual(self.engine.cache,{})

    def test_fabricated_evidence_rejected_without_verification_call(self):
        with self.requests(response('A','A made-up statement about patents.')) as request:
            self.assertEqual(self.engine.answer(Q)['answer'],'?')
            self.assertEqual(request.call_count,3)
            self.assertEqual(self.engine.cache,{})

    def test_evidence_from_unseen_end_of_long_page_is_rejected(self):
        self.engine=core.Engine([{'file':'x.pdf','page':1,'text':'patent '*400+QUOTE}],'long')
        with self.requests(response('A')):
            self.assertEqual(self.engine.answer(Q)['answer'],'?')

    def test_missing_second_evidence_does_not_validate_first_answer(self):
        with self.requests(response('A'),response('D','Unsupported words in the response.')):
            self.assertEqual(self.engine.answer(Q)['answer'],'?')

    def test_copyright_footer_removed_but_real_definition_kept(self):
        page='12 - 3\nCopyright © 2025 Pearson. All Rights Reserved\nCopyright protects original creative work.'
        clean=core.clean_reference(page)
        self.assertEqual(clean,'Copyright protects original creative work.')

    def test_header_only_page_does_not_win_retrieval(self):
        pages=[{'file':'footer.pdf','page':1,'text':'Copyright © 2025 Pearson. All Rights Reserved\nCash flow statement'},
               {'file':'notes.pdf','page':2,'text':'Copyright protects original creative work.'}]
        engine=core.Engine(pages,'notes')
        self.assertEqual(engine.retrieve('What does copyright protect?\nA. Original creative works\nB. Cash\nC. Logo\nD. Inventions')[0]['page'],2)

    def test_missing_or_duplicate_option_not_inferred(self):
        for text in [Q+'\nA. Another',Q.replace('A. Patent','A. ')]:
            with self.assertRaises(ValueError): self.engine.answer(text)

    def test_english_article_a_is_not_an_option_label(self):
        from screen_scan import prepare_questions
        question=Q.replace('What protects an invention?', 'A patent protects which of the following?')
        result=prepare_questions(question.splitlines())
        self.assertTrue(result.ready,result.warning)
        stem,choices=core.parse_options(result.questions[0].text)
        self.assertTrue(stem.startswith('A patent'))
        self.assertEqual(choices[0],'Patent')


if __name__=='__main__': unittest.main()
