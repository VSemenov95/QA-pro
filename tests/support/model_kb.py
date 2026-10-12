"""Мок модели для базы знаний, паспорта продукта и справки (подключается функцией install).

    kb = model_kb.install(app.model)
    kb.mode = 'limit'            # сводки отвечают «лимит запросов»; 'trunc' — длинный ответ обрывается, короткий проходит
    kb.synth_calls               # сколько запросов сводки сделано

Документы в тестах пишутся так, чтобы мок понимал их без файлов-образцов:
    «## Название»                    — функциональный раздел базы знаний;
    «### Бизнес-правила и ограничения» — подзаголовок из списка приложения (без подзаголовка — «Описание»);
    «- Ключ: значение»               — факт; один ключ с разными значениями в двух документах — расхождение.
Пример ТЗ (в нём есть «POST /api/v1/password-reset») делится на два раздела, как делила бы его модель.
Тип запроса определяет support/model.py по первой строке prompts/*.md; формулировки промптов здесь не используются.
"""
import json
import re

from .model import ModelError

SUBHEADS = ['Описание', 'Экраны и навигация', 'Поля и элементы', 'Бизнес-правила и ограничения', 'API и интеграции',
            'Сообщения и ошибки', 'Роли и права', 'Сценарии', 'Открытые вопросы']
CONF_HEAD = 'Расхождения между документами'
GENERAL = 'Общие сведения'

KINDS = ['promptKbSplit', 'promptKbSynth', 'promptKbSynthPart', 'promptKbCondense', 'promptHelp', 'promptHelpExpand',
         'promptPassportFull', 'promptPassportDelta', 'promptVidFrames']


def _norm(s):
    return re.sub(r'\s+', ' ', str(s or '').lower().replace('ё', 'е')).strip()


def _base(name):
    return re.sub(r'\.[a-z0-9]{1,5}$', '', str(name), flags=re.I)


# ---------- документы для тестов ----------
def limits_doc(n=3, title='Лимиты'):
    """Небольшой документ о разделе «Восстановление пароля»: лимит запросов n за 15 минут."""
    return f"# {title}\n## Восстановление пароля\n### Бизнес-правила и ограничения\n- Лимит запросов на сброс: не более {n} за 15 минут\n"


def call_doc(n=5):
    """Запись созвона: другой лимит и текст ошибки."""
    return (f"# Созвон с аналитиком\n## Восстановление пароля\n### Бизнес-правила и ограничения\n- Лимит запросов на сброс: не более {n} за 15 минут\n"
            "### Сообщения и ошибки\n- Сообщение при превышении: «Слишком много попыток. Повторите через 30 минут»\n")


def big_doc(k, subs=4, facts=24, conflict=None):
    """Большой документ об одном разделе: facts фактов в каждом из subs подзаголовков. Факты «Факт F<подзаголовок>-<номер>»
    одинаковы во всех документах, «Факт U<документ>-…» — у каждого документа свои. conflict=(подзаголовок, номер, значение) —
    этот документ называет другое значение факта."""
    out = [f'# Документ {k}', f'## {GENERAL}']
    for si, sub in enumerate(SUBHEADS[:subs]):
        out.append(f'### {sub}')
        for j in range(facts):
            v = conflict[2] if conflict and conflict[0] == si and conflict[1] == j else 10 * (j + 1)
            out.append(f'- Факт F{si}-{j}: поле «Поле {j}» на экране «Профиль» — до {v} символов, ошибка 4{j % 10}0')
        out.append(f'- Факт U{k}-{si}: поле «Особое {k}» видно только роли «Оператор {k}» и сохраняется кнопкой «Сохранить»')
        out.append('')
    return '\n'.join(out)


# ---------- разбор строк «- ключ: значение (источники)» ----------
def _facts(text, label):
    """Факты из выдержки. label — подпись выдержки: имя документа либо «прежняя сводка» / «сжатый материал» (там источники в скобках)."""
    own = [] if re.match(r'^(прежняя|сжатый)', label) else [_base(label)]
    out = []
    for raw in str(text).split('\n'):
        l = raw.strip()
        if not l or l.startswith('#'):
            continue
        body = l[2:] if l.startswith('- ') else l
        srcs = list(own)
        if not own:
            m = re.match(r'^(.*) \(([^()]*)\)$', body)
            if m:
                body, srcs = m.group(1), [s.strip() for s in m.group(2).split(';') if s.strip()]
        key, sep, val = body.partition(': ')
        out.append((key.strip(), val.strip() if sep else '', srcs))
    return out


def merge(excerpts):
    """excerpts — [(подпись, текст)]. Возвращает все варианты, чистые пункты (без противоречий) и расхождения."""
    variants = {}   # ключ -> {значение -> источники}
    order = []
    for label, text in excerpts:
        for key, val, srcs in _facts(text, label):
            vs = variants.setdefault(key, {})
            if not vs:
                order.append(key)
            vs.setdefault(val, set()).update(srcs)

    def line(key, val, srcs):
        return f"- {key}{': ' + val if val else ''} ({'; '.join(sorted(srcs))})"
    allv, clean, conflicts = [], [], []
    for key in order:
        vs = variants[key]
        for val, srcs in vs.items():
            allv.append(line(key, val, srcs))
        if len(vs) == 1:
            val, srcs = next(iter(vs.items()))
            clean.append(line(key, val, srcs))
        else:
            conflicts.append(f"{key}: " + '; '.join(f"{', '.join(sorted(srcs))} — {val}" for val, srcs in vs.items()))
    return {'all': allv, 'clean': clean, 'conflicts': conflicts}


def _excerpts(text):
    return [(m.group(1), m.group(2)) for m in re.finditer(r'<excerpt document="([^"]+)"[^>]*>\n([\s\S]*?)\n</excerpt>', text)]


def _by_subs(text):
    """Текст по подзаголовкам «### …» из списка приложения; текст до первого подзаголовка — «Описание»."""
    out, cur = {}, SUBHEADS[0]
    for l in str(text).split('\n'):
        m = re.match(r'^#{2,4}\s+(.+?)\s*$', l)
        if m:
            sub = next((s for s in SUBHEADS if _norm(s) == _norm(m.group(1))), None)
            if sub:
                cur = sub
                continue
        out[cur] = out.get(cur, '') + l + '\n'
    return out


# ---------- мок ----------
class KbMock:
    def __init__(self, model):
        self.model = model
        self.mode = ''                 # '', 'limit' (rate_limited), 'trunc' (длинный ответ обрывается)
        self.links = {}                # название раздела -> названия связанных разделов
        self.expand_terms = ['восстановление пароля', 'сброс пароля', 'Забыли пароль?', 'password reset']
        self.big_passport = False
        self.synth_calls = self.part_calls = self.cond_calls = self.expand_calls = 0
        self.trunc_hits = 0
        self.passport_full_calls = self.passport_delta_calls = 0
        self.vid_skip = {1}            # номера кадров (с нуля), которые модель считает «не экраном продукта»

    # ----- разбор документа на разделы -----
    def split(self, call):
        p = call.prompt
        frag = p.split('## Фрагмент документа «', 1)[1] if '## Фрагмент документа «' in p else p
        name = frag.split('»', 1)[0]
        text = '\n'.join(m.group(1) for m in re.finditer(r'<document name="[^"]*" part="[^"]*">\n([\s\S]*?)\n</document>', frag))
        outline = (p.split('## Разделы, которые уже есть в базе знаний\n', 1) + [''])[1].split('\n## Правила')[0]
        known = {_norm(m.group(2)): m.group(1) for m in re.finditer(r'(?m)^- (kb\w+) · (.+?)(?: — .*)?$', outline)}
        if 'POST /api/v1/password-reset' in text:
            blocks = [
                ('Восстановление пароля', 'Сброс пароля по ссылке из письма.', ['2', '4'],
                 '### Описание\n- Пользователь восстанавливает доступ по ссылке из письма\n### Экраны и навигация\n- /login → «Забыли пароль?» → экран «Восстановление пароля»\n### Сообщения и ошибки\n- «Введите корректный email»'),
                ('API сброса пароля', 'Эндпоинты запроса и подтверждения сброса.', ['3.1', '3.2'],
                 '### API и интеграции\n- `POST /api/v1/password-reset` — 202 / 400 INVALID_EMAIL / 429 RATE_LIMIT\n- `POST /api/v1/password-reset/confirm` — 200 / 400 WEAK_PASSWORD / 410 TOKEN_EXPIRED'),
            ]
        else:
            blocks = []
            cur_title, cur = None, []
            for l in text.split('\n'):
                m = re.match(r'^##\s+(.+?)\s*$', l)
                if m:
                    if cur_title is not None or any(x.strip() for x in cur):
                        blocks.append((cur_title or GENERAL, cur))
                    cur_title, cur = m.group(1), []
                elif re.match(r'^#\s', l):
                    continue
                else:
                    cur.append(l)
            if cur_title is not None or any(x.strip() for x in cur):
                blocks.append((cur_title or GENERAL, cur))
            blocks = [(t, f'О разделе «{t}»', [name], self._content(c)) for t, c in blocks if self._content(c).strip()]
            merged = {}
            for t, s, sec, c in blocks:     # один раздел в одном фрагменте — один блок
                if t in merged:
                    merged[t] = (t, s, sec, merged[t][3] + '\n' + c)
                else:
                    merged[t] = (t, s, sec, c)
            blocks = list(merged.values())
        return {'blocks': [{'blockId': known.get(_norm(t)), 'title': t, 'summary': s, 'sections': sec, 'content': c} for t, s, sec, c in blocks]}

    @staticmethod
    def _content(lines):
        """Строки раздела: до первого подзаголовка — в «Описание»."""
        text = '\n'.join(lines).strip('\n')
        if not text.strip():
            return ''
        return text if re.match(r'^\s*###\s', text) else '### Описание\n' + text

    # ----- сводка раздела -----
    def synth(self, call):
        self.synth_calls += 1
        p = call.prompt
        if self.mode == 'limit':
            raise ModelError('rate_limited', '')
        if self.mode == 'trunc' and 'не больше 3000 знаков' not in p:
            self.trunc_hits += 1
            raise ModelError('invalid_json', 'Модель ответила не в формате JSON.')
        title = (re.search(r'сводку раздела «([^»]+)»', p) or [None, ''])[1]
        ex = _excerpts(p.split('## Выдержки из документов\n', 1)[-1].split('\n## Другие разделы')[0])
        by = {}
        for label, text in ex:
            for sub, t in _by_subs(text).items():
                by.setdefault(sub, []).append((label, t))
        parts, conflicts = [], []
        for sub in SUBHEADS:
            if sub in by:
                r = merge(by[sub])
                conflicts += r['conflicts']
                if r['clean']:
                    parts.append(f'### {sub}\n' + '\n'.join(r['clean']))
        if conflicts:
            parts.append(f'### {CONF_HEAD}\n' + '\n'.join('- ' + c for c in conflicts))
        return {'summary': f'Все сведения о разделе «{title}» из документов продукта', 'synth': '\n'.join(parts), 'conflicts': conflicts, 'links': self._links(p, title)}

    def _links(self, prompt, title):
        others = {_norm(m.group(2)): m.group(1) for m in re.finditer(r'(?m)^- (kb\w+) · (.+?)$', prompt.split('## Другие разделы базы знаний\n', 1)[-1])}
        want = list(self.links.get(title, [])) + [a for a, bs in self.links.items() if title in bs]
        return [others[_norm(w)] for w in want if _norm(w) in others]

    def synth_part(self, call):
        self.part_calls += 1
        if self.mode == 'limit':
            raise ModelError('rate_limited', '')
        p = call.prompt
        title = (re.search(r'Раздел «([^»]+)»', p) or [None, ''])[1]
        mat = p.split('\n## Материал\n', 1)[1]
        mat = re.split(r'\n## (?:Расхождения из прежней сводки|Другие разделы)', mat)[0]
        prev_conf = [l[2:] for l in (p.split('\n## Расхождения из прежней сводки\n', 1) + [''])[1].split('\n## ')[0].split('\n') if l.startswith('- ')]
        out, conflicts = [], []
        for sc in re.split(r'(?m)^### ', mat)[1:]:
            sub = sc.split('\n', 1)[0].strip()
            r = merge(_excerpts(sc))
            out.append(f'### {sub}\n' + '\n'.join(r['clean']))
            conflicts += r['conflicts']
        for c in prev_conf:
            if not any(x.split(':')[0] == c.split(':')[0] for x in conflicts):
                conflicts.append(c)
        return {'summary': f'Все сведения о разделе «{title}» из документов продукта', 'synth': '\n'.join(out), 'conflicts': conflicts, 'links': self._links(p, title)}

    def condense(self, call):
        self.cond_calls += 1
        if self.mode == 'limit':
            raise ModelError('rate_limited', '')
        mat = call.prompt.split('## Материал подраздела', 1)[1].split('\n## Правила')[0]
        return {'text': '\n'.join(merge(_excerpts(mat))['all'])}

    # ----- справка -----
    def expand(self, call):
        self.expand_calls += 1
        p = call.prompt
        q = (p.split('## Вопрос\n', 1) + [''])[1].split('\n')[0]
        secs = [(m.group(1), m.group(2).strip()) for m in re.finditer(r'(?m)^- (kb\w+) · ([^\n—]+)', p.split('## Разделы базы знаний', 1)[-1])]
        pick = [i for i, t in secs if 'Восстановление' in t] if re.search(r'помни|доступ|забыл', q, re.I) else []
        return {'sections': pick, 'terms': self.expand_terms if pick else []}

    def help(self, call):
        p = call.prompt
        q = (p.split('## Вопрос\n', 1) + [''])[1].split('\n')[0]
        first = lambda letter: (re.search(r'\n\[(' + letter + r'\d+)\]', p) or [None, None])[1]
        b, k, d = first('B'), first('K'), first('D')
        if re.search(r'оплат', q, re.I):
            return {'status': 'not_found', 'answer': 'В базе знаний нет сведений об оплате картой.', 'sources': [], 'missing': 'Описание оплаты'}
        if re.search(r'лимит|огранич', q, re.I):
            return {'status': 'answered', 'answer': '- Не более **3 запросов** на сброс за 15 минут\n- Ссылка действует 30 минут', 'sources': [x for x in (b, d or k, 'UI-001', 'X-999') if x], 'missing': ''}
        return {'status': 'partial', 'answer': 'Известно только про экран «Восстановление пароля».', 'sources': [x for x in (k,) if x], 'missing': 'Нет описания ролей'}

    # ----- паспорт продукта -----
    def passport_full(self, call):
        self.passport_full_calls += 1
        n = self.passport_full_calls
        prev = (call.prompt.split('## Текущий паспорт\n', 1) + [''])[1].split('\n')[0]
        if self.big_passport:
            return {'passport': '\n\n'.join(f'## Раздел {k + 1}\n' + '\n'.join(f'- Факт {k}.{j}: экран «Профиль клиента», роль Оператор, поле Email до 254 символов, ответ 202/400/429' for j in range(12)) for k in range(9))}
        return {'passport': f"## Назначение и границы\n- Восстановление пароля в личном кабинете (ТЗ v1.3)\n- Версия знаний {n}{'' if prev.startswith('Пока пуст') else ', дополнено'}\n\n"
                            "## Экраны и навигация\n- **Восстановление пароля**: /login → ссылка «Забыли пароль?»\n- Экран «Новый пароль» — по ссылке из письма\n\n"
                            "## API и интеграции\n- `POST /api/v1/password-reset` — 202 / 400 INVALID_EMAIL / 429 RATE_LIMIT\n\n## Открытые вопросы\n1. Что происходит при 4-м запросе через UI?"}

    def passport_delta(self, call):
        self.passport_delta_calls += 1
        n = self.passport_delta_calls
        return {'ops': [{'op': 'add', 'section': 'Бизнес-правила и ограничения', 'text': f'Не более 3 запросов на сброс за 15 минут (дельта {n})'},
                        {'op': 'remove', 'old': 'Что происходит при 4-м запросе через UI?'},
                        {'op': 'add', 'section': 'Термины', 'text': '- Токен сброса — одноразовая ссылка на 30 минут'}]}

    # ----- видео -----
    def vid_frames(self, call):
        return {'frames': [{'n': int(m.group(1)), 'skip': k in self.vid_skip, 'screen': 'Экран в ' + m.group(2), 'details': 'Описание кадра ' + m.group(1)}
                           for k, m in enumerate(re.finditer(r'кадр (\d+) — \[([\d:]+)\]', call.prompt))]}


def install(model, **opts):
    """Подключает мок к модели страницы: разбор документов, сводки, справка, паспорт. Возвращает KbMock для настройки и счётчиков."""
    kb = KbMock(model)
    for k, v in opts.items():
        setattr(kb, k, v)
    model.on('promptKbSplit', kb.split).on('promptKbSynth', kb.synth).on('promptKbSynthPart', kb.synth_part).on('promptKbCondense', kb.condense)
    model.on('promptHelp', kb.help).on('promptHelpExpand', kb.expand)
    model.on('promptPassportFull', kb.passport_full).on('promptPassportDelta', kb.passport_delta).on('promptVidFrames', kb.vid_frames)
    model.kb = kb
    return kb


# ---------- автономная версия: подключение по ключу, запросы к host перехватываются ----------
CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': 'POST, OPTIONS'}
CONN = {'id': 'aiX', 'kind': 'openai', 'name': 'LLM', 'baseUrl': 'http://ai.test/v1', 'model': 'm', 'apiKey': 'k', 'auth': 'Bearer', 'headers': '', 'tools': False}


def serve_openai(app, host='http://ai.test/'):
    """В автономной версии модель — подключение по ключу (OpenAI-совместимый адрес). Запросы к host получает мок модели страницы."""
    def handle(route):
        req = route.request
        if req.method == 'OPTIONS':
            return route.fulfill(status=204, headers=CORS)
        body = json.loads(req.post_data)
        prompt = next(m['content'] for m in body['messages'] if m['role'] == 'user')
        out = app.model.handle(prompt, {'modelTier': None})
        if '__error' in out:
            if out['__error']['code'] == 'rate_limited':
                return route.fulfill(status=429, content_type='application/json', body='{}', headers=CORS)
            return route.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'choices': [{'message': {'role': 'assistant', 'content': 'не JSON'}}]}))
        route.fulfill(status=200, content_type='application/json', headers=CORS,
                      body=json.dumps({'choices': [{'message': {'role': 'assistant', 'content': json.dumps(out['json'], ensure_ascii=False)}}]}))
    app.ctx.route(host + '**', handle)


# ---------- снимки состояния страницы в момент запроса к модели (init-скрипт для make_app(init=...)) ----------
# Обращаться к странице из обработчика модели нельзя (синхронный Playwright зависает), поэтому снимок делает сама страница:
# window.__snaps = [{ head: начало запроса, p: что показывает кнопка «Остановить»/прогресс базы знаний в этот момент }].
SNAPSHOT_INIT = """
(() => {
  let real = window.__model;
  const wrap = (f) => async (prompt, info) => {
    const q = window.__qa;
    let p = null;
    try { p = q && q.kbProgress ? JSON.parse(JSON.stringify(q.kbProgress() || null)) : null; } catch (e) { p = null; }
    (window.__snaps = window.__snaps || []).push({ head: prompt.slice(0, 40), p });
    return f(prompt, info);
  };
  Object.defineProperty(window, '__model', { configurable: true, get() { return real ? wrap(real) : real; }, set(v) { real = v; } });
})();
"""
