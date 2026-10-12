"""Мок Сферы ФТ и «хостинг» для тестов расширения: один локальный HTTP-сервер.

    sf = SferaMock(model=MockModel()).start()
    sf.base                       # http://127.0.0.1:порт — адрес Сферы в настройках загрузчика
    sf.posts                      # тела созданных кейсов (POST /app/testing/api/v1/test-issues)
    sf.serve('/blank.html', '<title>x</title>')   # любая своя страница
    /qa-pro.html                  # автономная версия QA pro
    /v1/chat/completions          # OpenAI-совместимая «модель» (MockModel) для автономной версии
"""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SECTIONS = [{'id': 123, 'name': 'Личный кабинет', 'parentSectionId': None, 'ownElementsCount': 0},
            {'id': 124, 'name': 'Восстановление пароля', 'parentSectionId': 123, 'ownElementsCount': 3}]


class SferaMock:
    def __init__(self, model=None, sections=None):
        self.model = model
        self.sections = sections if sections is not None else SECTIONS
        self.posts, self.requests, self.pages = [], [], {}
        self.fail_sections = False        # справочник разделов отвечает 500
        self.fail_marker = 'сбой'         # кейс с этим словом в названии Сфера отклоняет (400)
        mock = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, body, ctype):
                b = body if isinstance(body, bytes) else body.encode('utf-8')
                self.send_response(code)
                self.send_header('Content-Type', ctype)
                self.send_header('Content-Length', str(len(b)))
                self.end_headers()
                self.wfile.write(b)

            def _json(self, obj, code=200):
                self._send(code, json.dumps(obj, ensure_ascii=False), 'application/json')

            def do_GET(self):
                u = urlparse(self.path)
                q = parse_qs(u.query)
                if u.path in mock.pages:
                    body, ctype = mock.pages[u.path]
                    return self._send(200, body, ctype)
                if u.path == '/qa-pro.html':
                    with open(os.path.join(ROOT, 'qa-pro.html'), 'rb') as f:
                        return self._send(200, f.read(), 'text/html; charset=utf-8')
                if u.path.startswith('/project/'):
                    return self._send(200, '<title>Сфера ФТ · PPAN</title><h1>Сфера</h1>', 'text/html; charset=utf-8')
                mock.requests.append({'method': 'GET', 'path': u.path, 'auth': self.headers.get('Authorization')})
                if u.path == '/app/testing/api/v1/attributes':
                    if q.get('categories', [''])[0] == 'TEST_CASE_STATUS':
                        return self._json({'content': [{'objectType': 'TEST_CASE', 'values': [{'id': 'st-new', 'code': 'new'}, {'id': 'st-created', 'code': 'created'}]}]})
                    return self._json({'content': [{'code': 'ti_status', 'objectType': 'TEST_CASE', 'values': [{'id': 'tis-def', 'isDefault': True}]},
                                                   {'code': 'ti_priority', 'objectType': 'TEST_CASE', 'values': [{'id': 'tip-def', 'isDefault': True}]}]})
                if u.path == '/app/testing/api/v1/projects/PPAN/sections':
                    return self._json({'error': 'boom'}, 500) if mock.fail_sections else self._json(mock.sections)
                self._json({'error': 'not found'}, 404)

            def do_POST(self):
                n = int(self.headers.get('Content-Length', '0'))
                body = json.loads(self.rfile.read(n) or b'{}')
                mock.requests.append({'method': 'POST', 'path': self.path, 'auth': self.headers.get('Authorization')})
                if self.path == '/app/testing/api/v1/test-issues':
                    mock.posts.append(body)
                    if mock.fail_marker and mock.fail_marker in body.get('name', ''):
                        return self._json({'message': 'bad'}, 400)
                    return self._json({'testIssueCode': f'PPAN-T{len(mock.posts)}'})
                if self.path == '/v1/chat/completions' and mock.model is not None:
                    msgs = body['messages']
                    u = msgs[-1]['content']
                    text = u if isinstance(u, str) else ' '.join(p.get('text', '') for p in u if p.get('type') == 'text')
                    res = mock.model.handle(text, {})
                    out = res.get('json', {}) if isinstance(res, dict) else {}
                    return self._json({'choices': [{'message': {'role': 'assistant', 'content': json.dumps(out, ensure_ascii=False)}}], 'usage': {'prompt_tokens': 100, 'completion_tokens': 20}})
                self._json({}, 404)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), H)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self.base = f'http://127.0.0.1:{self.port}'
        self.thread = None

    def serve(self, path, body, ctype='text/html; charset=utf-8'):
        self.pages[path] = (body, ctype)

    def start(self):
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        self.server.shutdown()
        self.server.server_close()

    def conn(self):
        """Подключение к «модели» для автономной версии QA pro (localStorage qapro.conns)."""
        return {'id': 'p-mock', 'preset': 'mock', 'kind': 'openai', 'name': 'Мок', 'baseUrl': self.base + '/v1', 'apiKey': 'k', 'auth': 'Bearer', 'model': 'gpt-x', 'headers': '', 'tools': False, 'noTemp': False}

    def api_posts(self):
        return [r for r in self.requests if r['method'] == 'POST']
