"""Помощники для тестов генерации, результатов и сессии: «стоп-кран» для запросов к модели, подключение
автономной версии к мок-модели и ответы модели, специфичные для этой области."""
import json
import re

from .model import SIGS, ModelError, case_body

# ---------- подписи запросов ----------


def sig(kind):
    """Первая строка prompts/<kind>.md до первой подстановки: по ней запрос узнаёт и мок, и «стоп-кран»."""
    return next(s for s, k in SIGS if k == kind)


# ---------- «стоп-кран»: запрос стоит, пока тест его не отпустит ----------
HOLD_JS = r"""
(() => {
  const holds = [];
  window.__holds = holds;
  window.__hold = (sig) => { let open; const p = new Promise((r) => { open = r; }); holds.push({ sig, p, open, hits: 0 }); };
  window.__release = () => { for (const h of holds.splice(0)) h.open(); };
  window.__wait = async (text) => { for (const h of [...holds]) if (text.includes(h.sig)) { h.hits++; await h.p; } };
  const use = window.claude && window.claude.use;
  if (use) window.claude.use = async (n) => {
    const c = await use(n);
    if (n === 'sample' && c && !c.__held) { const j = c.json; c.json = async (prompt, o) => { await window.__wait(prompt); return j(prompt, o); }; c.__held = true; }
    return c;
  };
  const f = window.fetch.bind(window);
  window.fetch = async (u, o) => { if (String(u).startsWith('http://ai.test/') && o && typeof o.body === 'string') await window.__wait(o.body); return f(u, o); };
})();
"""


class Hold:
    """Запросы выбранного вида останавливаются на входе в модель, пока тест не вызовет release().
    Так страницу можно рассмотреть посреди генерации без sleep:

        h = Hold(app.page).on('promptGenerate')   # (страница открыта с init=HOLD_JS)
        app.generate(wait=False); h.wait()        # запрос дошёл до «модели» и стоит
        ...                                       # проверки во время запуска
        h.release(); app.wait_idle()
    """
    def __init__(self, page):
        self.page = page

    def on(self, kind):
        self.page.evaluate('(s) => window.__hold(s)', sig(kind))
        return self

    def wait(self, timeout=20000):
        self.page.wait_for_function('() => window.__holds.some((h) => h.hits > 0)', timeout=timeout)

    def release(self):
        self.page.evaluate('() => window.__release()')


# ---------- автономная версия: подключение «по ключу» отвечает мок-модель ----------
AI_CONN = {'id': 'aiX', 'kind': 'openai', 'name': 'Корп. LLM', 'baseUrl': 'http://ai.test/v1', 'model': 'corp-llm', 'apiKey': 'secret', 'auth': 'Bearer', 'headers': '', 'tools': False}
CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': 'POST, OPTIONS'}


def standalone(**settings):
    """Аргументы make_app для автономной версии с подключением к http://ai.test/v1 (запросы перехватывает connect_ai)."""
    return dict(kind='standalone', local_storage={'qapro.conns': [AI_CONN]}, settings={'genAI': 'conn:aiX', **settings}, init=HOLD_JS)


class AiRoute:
    """Подмена API подключения: промпт → мок-модель, ответ — в формате OpenAI. Запоминает заголовки и модель запросов."""
    def __init__(self, app):
        self.app, self.requests = app, []
        app.ctx.route('http://ai.test/**', self.handle)

    def handle(self, route):
        req = route.request
        if req.method == 'OPTIONS':   # предзапрос браузера (CORS)
            return route.fulfill(status=204, headers=CORS)
        body = json.loads(req.post_data)
        prompt = next(m['content'] for m in body['messages'] if m['role'] == 'user')
        self.requests.append({'url': req.url, 'auth': req.headers.get('authorization'), 'model': body.get('model'), 'stream': body.get('stream')})
        res = self.app.model.handle(prompt, {'model': body.get('model')})
        if '__error' in res:
            code = res['__error']['code']
            if code == 'rate_limited':
                return route.fulfill(status=429, body='limit', headers=CORS)
            return route.fulfill(status=200, content_type='application/json', headers=CORS,
                                 body=json.dumps({'choices': [{'message': {'role': 'assistant', 'content': '{"cases": [ обрыв'}}]}))
        route.fulfill(status=200, content_type='application/json', headers=CORS,
                      body=json.dumps({'choices': [{'message': {'role': 'assistant', 'content': json.dumps(res['json'], ensure_ascii=False)}}], 'usage': {'prompt_tokens': 100, 'completion_tokens': 50}}))


def connect_ai(app):
    return AiRoute(app)


# ---------- ответы модели ----------
def checks_of(prompt):
    """Проверки из раздела «Что покрыть» запроса на написание кейсов: [(id группы плана, текст проверки)]."""
    part = prompt.split('## Что покрыть')[1].split('\n## ')[0]
    out = []
    for block in re.split(r'(?m)^### ', part)[1:]:
        pid = re.match(r'([A-Z]+-\d+)\.', block).group(1)
        body = block.split('Требования:')[0]
        out += [(pid, m.group(1)) for m in re.finditer(r'(?m)^\d+\. (.+)$', body)]
    return out


def cases_for(prompt, only=None):
    """Один кейс на проверку запроса; название — «Кейс: <проверка>»."""
    got = [(pid, c) for pid, c in checks_of(prompt) if only is None or only(c)]
    return {'cases': [{'planItem': pid, 'requirementIds': [], 'suites': ['regression'], 'testCase': case_body('Кейс: ' + c)} for pid, c in got]}


def truncating_generate(limit, sizes=None, fail_on=None):
    """Модель «обрывает ответ» (invalid_json), если проверок в запросе больше limit или в запросе есть fail_on.
    sizes — список, куда пишется число проверок каждого запроса."""
    def handler(call):
        cs = [c for _, c in checks_of(call.prompt)]
        if sizes is not None:
            sizes.append(len(cs))
        if len(cs) > limit or (fail_on and any(fail_on in c for c in cs)):
            raise ModelError('invalid_json', 'Модель ответила не в формате JSON.')
        return cases_for(call.prompt)
    return handler


def requirement(title, types=('ui',), criteria=(), **kw):
    r = {'title': title, 'description': kw.pop('description', title), 'types': list(types), 'priority': 'high', 'doc': 'Пример', 'section': '1', 'quote': '', 'criteria': list(criteria)}
    r.update(kw)
    return r


# ---------- вторая вкладка и ожидание данных в базе ----------
def second_page(app):
    """Ещё одна вкладка того же браузера (база и мок-модель общие, как у двух вкладок одного человека).
    Ошибки страницы второй вкладки валят тест так же, как первой."""
    from .app import URL, App
    page = app.ctx.new_page()
    other = App(app.ctx, page, app.db, app.model, app.kind)
    other.errors = app.errors
    page.goto(URL)
    other.ready()
    return other


def wait_until(app, cond, timeout=15000, step=100):
    """Ждёт, пока cond() вернёт истину (например, запись появится в базе, которая живёт в Python). Возвращает её значение."""
    waited = 0
    while waited <= timeout:
        v = cond()
        if v:
            return v
        app.page.wait_for_timeout(step)
        waited += step
    raise AssertionError('не дождались условия: ' + getattr(cond, '__name__', 'cond'))


# ---------- кейсы по шаблону и ревьюер ----------
def template_case(ty, title):
    """Кейс ровно по образцу templates/<вид>.md: все поля шаблона на месте, поэтому автоматическая проверка полей молчит."""
    import os
    from .model import ROOT
    with open(os.path.join(ROOT, 'templates', ty + '.md'), encoding='utf-8') as f:
        sample = json.loads(f.read().split('```json\n', 1)[1].rsplit('\n```', 1)[0])
    sample = sample[0] if isinstance(sample, list) else sample
    sample['title'] = title
    sample['id'] = ''
    return sample


def generate_by_template(call):
    """Ответ на «Напиши тест-кейсы»: по кейсу на группу плана, по образцу шаблона вида."""
    ty = 'api' if 'вида API' in call.prompt else 'ui' if 'вида UI' in call.prompt else 'e2e'
    pref = {'api': '[BE]', 'ui': '[FE]', 'e2e': '[E2E]'}[ty]
    return {'cases': [{'planItem': pid, 'requirementIds': [], 'suites': ['smoke', 'regression'] if k == 0 else ['regression'],
                       'testCase': template_case(ty, f'{pref} Кейс для {pid}: проверка восстановления пароля')}
                      for k, pid in enumerate(re.findall(r'### ([A-Z]+-\d+)\.', call.prompt))]}


def reviewer(by_target, message='Ожидаемый результат не совпадает с п. 3.1: должен быть код 202.', suggestion='Указать код 202 и тело {"status":"sent"}.'):
    """Ревьюер: {'API-001': ['critical'], 'CL-002': ['minor']} → по замечанию на каждую степень важности; остальным объектам замечаний нет.
    Подходит и для кейсов, и для пунктов чек-листа."""
    def handler(call):
        ids = re.findall(r'\{"id":"([A-Z0-9-]+)","type"', call.prompt) + re.findall(r'(?m)^(CL-\d+) \[', call.prompt)
        out = []
        for tid in ids:
            for n, sev in enumerate(by_target.get(tid, [])):
                out.append({'targetId': tid, 'severity': sev, 'category': 'Соответствие ТЗ', 'message': f'{message} ({tid}/{n + 1})', 'suggestion': suggestion})
        return {'findings': out}
    return handler


def three_steps_cases(call):
    """Кейсы с тремя шагами («Действие N» → «Результат N»): для проверки порядка и нумерации шагов."""
    return {'cases': [{'planItem': pid, 'requirementIds': [], 'suites': ['smoke', 'regression'],
                       'testCase': {**case_body('Три шага'), 'steps': [{'step': i, 'action': f'Действие {i}', 'expected': f'Результат {i}'} for i in (1, 2, 3)]}}
                      for pid in re.findall(r'### ([A-Z]+-\d+)\.', call.prompt)]}


# ---------- мок ТМС (Test IT, Qase, TestRail, свой API) ----------
class TmsRoute:
    """Подмена API системы управления тестированием на http://tms.test: запоминает запросы, отвечает так, как отвечают Test IT, Qase и TestRail.
    fail — {часть названия кейса: код ответа}: такой кейс ТМС отклоняет; deny — код ответа на любой запрос (например, 401)."""
    def __init__(self, app, base='http://tms.test'):
        self.requests, self.fail, self.deny, self.n = [], {}, None, 0
        app.ctx.route(base + '/**', self.handle)

    @property
    def posts(self):
        return [r for r in self.requests if r['method'] == 'POST']

    def handle(self, route):
        from urllib.parse import urlparse
        req = route.request
        cors = {'access-control-allow-origin': '*', 'access-control-allow-methods': 'GET, POST, OPTIONS',
                'access-control-allow-headers': req.headers.get('access-control-request-headers', '*')}
        if req.method == 'OPTIONS':
            return route.fulfill(status=204, headers=cors)
        u = urlparse(req.url)
        path = u.path + ('?' + u.query if u.query else '')
        body = json.loads(req.post_data) if req.post_data else None
        self.requests.append({'method': req.method, 'path': path, 'headers': dict(req.headers), 'body': body})
        title = (body or {}).get('name') or (body or {}).get('title') or ''
        code = self.deny or next((c for k, c in self.fail.items() if k in title), None)
        if code:
            return route.fulfill(status=code, body='отклонено', headers=cors)
        self.n += 1
        res = {}
        if req.method == 'GET':
            res = {'name': 'Демо-проект'} if '/api/v2/projects/' in path else {'result': {'title': 'Демо Qase'}} if path.startswith('/project/') else {'name': 'Раздел TestRail'}
        elif path.startswith('/api/v2/workItems'):
            res = {'id': f'uuid-{self.n}', 'globalId': 1000 + self.n}
        elif path.endswith('/bulk'):
            res = {'result': {'ids': [500 + i for i in range(len(body['cases']))]}}
        elif 'add_case' in path:
            res = {'id': 700 + self.n}
        else:
            res = {'id': f'CUS-{self.n}'}
        route.fulfill(status=200, content_type='application/json', body=json.dumps(res), headers=cors)
