"""Offline tests; local HTTP stub checks transport, not model intelligence."""
import json
import os
from pathlib import Path
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest
from unittest.mock import patch
import core

QUESTION = 'What protects an invention?\nA. Patent\nB. Trademark\nC. Copyright\nD. Franchise'
ANSWER = {'answer': 'A', 'confidence': 'high', 'explanation': 'Patent', 'sources': [1], 'evidence': [{'source': 1, 'quote': 'A patent protects an invention.'}]}

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for p in [patch.object(core, 'DATA', Path(self.tmp.name)),
                  patch.dict(os.environ, {'MCQ_MODEL': 'qwen2.5:3b'})]:
            p.start()
            self.addCleanup(p.stop)
        self.engine = core.Engine([{'file': 'notes.pdf', 'page': 2, 'text': 'A patent protects an invention.'},
                                   {'file': 'other.pdf', 'page': 1, 'text': 'Marketing uses segmentation.'}], 'abc')

    def reply(self, answer):
        return {'done': True, 'done_reason': 'stop', 'message': {'content': json.dumps(answer)}}

    def infer(self, answer):
        return patch('core.local_request', side_effect=[
            {'models': [{'name': 'qwen2.5:3b'}]}, {}, self.reply(answer),
            self.reply({**answer, 'answer': {'A':'D', 'B':'C', 'C':'B', 'D':'A', '?':'?'}[answer['answer']]})])

    def test_retrieval(self):
        self.assertEqual(self.engine.retrieve(QUESTION)[0]['page'], 2)

    def test_missing_options(self):
        with self.assertRaises(ValueError): self.engine.answer('choose a patent')

    def test_answer_cache_refresh_and_note_change(self):
        with self.infer(ANSWER) as request:
            first = self.engine.answer(QUESTION)
            self.assertEqual(first['answer'], 'A')
            self.assertEqual(first['references'][0]['page'], 2)
            self.assertFalse(first['cached'])
            self.assertTrue(self.engine.answer(QUESTION)['cached'])
            self.assertEqual(request.call_count, 4)
        reloaded = core.Engine(self.engine.pages, 'abc')
        self.assertTrue(reloaded.answer(QUESTION)['cached'])
        with self.infer(ANSWER) as request:
            self.assertFalse(reloaded.answer(QUESTION, refresh=True)['cached'])
            self.assertEqual(request.call_count, 4)
        changed = core.Engine(self.engine.pages, 'different-notes')
        with self.infer(ANSWER):
            self.assertFalse(changed.answer(QUESTION)['cached'])

    def test_invalid_citation_is_removed_without_blocking_knowledge(self):
        with self.infer({**ANSWER, 'sources': [99]}):
            result=self.engine.answer(QUESTION)
            self.assertEqual(result['answer'],'A')
            self.assertEqual(result['references'],[])
            self.assertEqual(result['basis'],'general_knowledge')

    def test_general_knowledge_answer_can_be_cached_without_citations(self):
        with self.infer({**ANSWER, 'sources': [], 'evidence': []}):
            result=self.engine.answer(QUESTION)
            self.assertEqual(result['answer'],'A')
            self.assertEqual(result['references'],[])
            self.assertTrue(self.engine.cache)

    def test_low_confidence_abstains(self):
        with self.infer({**ANSWER, 'confidence': 'low'}):
            self.assertEqual(self.engine.answer(QUESTION)['answer'], '?')

    def test_missing_model(self):
        with patch('core.local_request', return_value={'models': []}):
            with self.assertRaisesRegex(ValueError, 'ollama pull'): self.engine.answer(QUESTION)

    def test_cloud_name_rejected(self):
        for name in ['test:cloud', 'test-cloud', 'https://remote/model', 'org/model']:
            with patch.dict(os.environ, {'MCQ_MODEL': name}):
                with self.assertRaises(ValueError): core.model_name()

    def test_renamed_cloud_model_rejected(self):
        with patch('core.local_request', side_effect=[{'models': [{'name': 'qwen2.5:3b'}]}, {'remote_host': 'https://example.com'}]):
            with self.assertRaisesRegex(ValueError, '云端'): self.engine.answer(QUESTION)

    def test_timeout(self):
        with patch('urllib.request.OpenerDirector.open', side_effect=TimeoutError):
            with self.assertRaisesRegex(ValueError, '超时'): self.engine.answer(QUESTION)

    def test_no_retrieved_evidence_still_calls_local_model(self):
        with patch.object(self.engine, 'retrieve', return_value=[]), self.infer({**ANSWER,'sources':[],'evidence':[]}) as request:
            result=self.engine.answer(QUESTION)
            self.assertEqual(result['answer'],'A')
            self.assertEqual(result['references'],[])
            self.assertEqual(request.call_count,4)
            payload=request.call_args.args[1]
            self.assertEqual(json.loads(payload['messages'][1]['content'])['lecture_excerpts'],'')

    def test_truncated_response_rejected(self):
        reply = {**self.reply(ANSWER), 'done_reason': 'length'}
        with patch('core.local_request', side_effect=[{'models': [{'name': 'qwen2.5:3b'}]}, {}, reply]):
            with self.assertRaises(ValueError): self.engine.answer(QUESTION)

    def test_real_loopback_transport_without_proxy_or_credentials(self):
        captured = []
        reply = self.reply(ANSWER)
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.respond({'models': [{'name': 'qwen2.5:3b'}]})
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                captured.append((self.path, body, dict(self.headers)))
                if self.path == '/api/show':
                    self.respond({})
                else:
                    question = json.loads(body['messages'][1]['content'])['question']
                    answer = {**ANSWER, 'answer': 'D' if 'A. Franchise' in question else 'A'}
                    self.respond({'done': True, 'message': {'content': json.dumps(answer)}})
            def respond(self, payload):
                data = json.dumps(payload).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            def log_message(self, *args): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.object(core, 'OLLAMA_URL', f'http://127.0.0.1:{server.server_port}'), patch.dict(os.environ, {'HTTP_PROXY': 'http://127.0.0.1:1', 'HTTPS_PROXY': 'http://127.0.0.1:1'}):
                self.assertEqual(self.engine.answer(QUESTION)['answer'], 'A')
            path, body, headers = captured[-1]
            self.assertEqual(path, '/api/chat')
            self.assertEqual(body['model'], 'qwen2.5:3b')
            self.assertFalse(body['stream'])
            self.assertIn('format', body)
            self.assertNotIn('Authorization', headers)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_redirect_handler_blocks_remote(self):
        with self.assertRaises(ValueError):
            core.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com')

if __name__ == '__main__': unittest.main()
