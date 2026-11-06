import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import core

QUESTION = 'What protects an invention?\nA. Patent\nB. Trademark\nC. Copyright\nD. Franchise'

class Reply:
    def __init__(self, answer):
        self.data = json.dumps({'choices': [{'message': {'content': json.dumps(answer)}}]}).encode()
    def __enter__(self):
        import io
        return io.BytesIO(self.data)
    def __exit__(self, *args):
        pass

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = patch.object(core, 'DATA', Path(self.tmp.name))
        self.data.start()
        self.addCleanup(self.data.stop)
        self.engine = core.Engine([{'file': 'notes.pdf', 'page': 2, 'text': 'A patent protects an invention.'},
                                   {'file': 'other.pdf', 'page': 1, 'text': 'Marketing uses segmentation.'}], 'abc')
    def test_retrieval(self):
        self.assertEqual(self.engine.retrieve(QUESTION)[0]['page'], 2)
    def test_missing_options(self):
        with self.assertRaises(ValueError): self.engine.answer('choose a patent')
    @patch.dict('os.environ', {'MCQ_API_KEY': 'test'})
    def test_answer_cache_and_refresh(self):
        reply = {'answer': 'A', 'confidence': 'high', 'explanation': 'Patent', 'sources': [1]}
        with patch('urllib.request.urlopen', return_value=Reply(reply)) as request:
            first = self.engine.answer(QUESTION)
            self.assertEqual(first['answer'], 'A')
            self.assertEqual(first['references'][0]['page'], 2)
            self.assertFalse(first['cached'])
            self.assertTrue(self.engine.answer(QUESTION)['cached'])
            self.assertEqual(request.call_count, 1)
            self.assertFalse(self.engine.answer(QUESTION, refresh=True)['cached'])
            self.assertEqual(request.call_count, 2)
        reloaded = core.Engine(self.engine.pages, 'abc')
        self.assertTrue(reloaded.answer(QUESTION)['cached'])
        changed = core.Engine(self.engine.pages, 'different-notes')
        self.assertNotEqual(changed.fingerprint, self.engine.fingerprint)
        self.assertEqual(len(changed.cache), 1)
    @patch.dict('os.environ', {'MCQ_API_KEY': 'test'})
    def test_invalid_citation_rejected(self):
        with patch('urllib.request.urlopen', return_value=Reply({'answer': 'A', 'confidence': 'high', 'explanation': '', 'sources': [99]})):
            with self.assertRaises(ValueError): self.engine.answer(QUESTION)
    @patch.dict('os.environ', {'MCQ_API_KEY': 'test'})
    def test_unsupported_answer_not_cached(self):
        with patch('urllib.request.urlopen', return_value=Reply({'answer': 'A', 'confidence': 'high', 'explanation': '', 'sources': []})):
            self.assertEqual(self.engine.answer(QUESTION)['answer'], '?')
            self.assertEqual(self.engine.cache, {})
    @patch.dict('os.environ', {'MCQ_API_KEY': 'test'})
    def test_timeout(self):
        with patch('urllib.request.urlopen', side_effect=TimeoutError):
            with self.assertRaisesRegex(ValueError, '超时'): self.engine.answer(QUESTION)

if __name__ == '__main__': unittest.main()
