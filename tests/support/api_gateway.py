"""Подмена API провайдеров в автономной версии (qa-pro.html ходит к ним через fetch).

    gw = Gateway(app)        # перехватывает OpenAI, Anthropic и Иннокод; отвечает мок-моделью страницы
    gw.requests              # [Req(url, host, headers, body)] — что ушло провайдерам
    gw.to('api.openai.com')  # запросы одному провайдеру
    gw.fail('api.openai.com', 401)   # провайдер отвечает ошибкой HTTP
    gw.down('api.openai.com')        # провайдер недоступен (сеть)
"""
import json
from dataclasses import dataclass, field

HOSTS = ('api.openai.com', 'api.anthropic.com', 'chat.aicenter.inno.tech')


@dataclass
class Req:
    url: str
    host: str
    headers: dict
    body: dict = field(default_factory=dict)

    @property
    def prompt(self):
        m = self.body['messages'][-1]['content']
        return m if isinstance(m, str) else ''.join(b.get('text', '') for b in m)


class Gateway:
    def __init__(self, app, hosts=HOSTS):
        self.app, self.requests, self.failures, self.offline = app, [], {}, set()
        for h in hosts:
            app.ctx.route(f'https://{h}/**', self._handle)

    def to(self, host):
        return [r for r in self.requests if r.host == host]

    def fail(self, host, status=401, text='invalid api key'):
        self.failures[host] = (status, text)

    def down(self, host):
        self.offline.add(host)

    def _handle(self, route):
        req = route.request
        host = req.url.split('/')[2]
        cors = {'access-control-allow-origin': '*', 'access-control-allow-methods': 'POST, OPTIONS',
                'access-control-allow-headers': req.headers.get('access-control-request-headers', '*')}
        if req.method == 'OPTIONS':
            return route.fulfill(status=204, headers=cors)
        if host in self.offline:
            return route.abort()
        r = Req(req.url, host, {k.lower(): v for k, v in req.headers.items()}, json.loads(req.post_data or '{}'))
        self.requests.append(r)
        if host in self.failures:
            status, text = self.failures[host]
            return route.fulfill(status=status, body=text, headers=cors)
        out = self.app.model.handle(r.prompt, {})
        if '__error' in out:
            return route.fulfill(status=500, body=out['__error'].get('message', 'error'), headers=cors)
        text = json.dumps(out['json'], ensure_ascii=False)
        if '/v1/messages' in req.url:
            res = {'content': [{'type': 'text', 'text': text}], 'stop_reason': 'end_turn', 'usage': {'input_tokens': 10, 'output_tokens': 5}}
        else:
            res = {'choices': [{'message': {'role': 'assistant', 'content': text}}], 'usage': {'prompt_tokens': 10, 'completion_tokens': 5}}
        route.fulfill(status=200, content_type='application/json', body=json.dumps(res, ensure_ascii=False), headers=cors)
