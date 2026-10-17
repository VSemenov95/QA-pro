"""Мок модели. Тип запроса определяется по первой строке файлов prompts/*.md, поэтому правка формулировок промптов тесты не ломает.

    model.on('promptGenerate', lambda call: {...})   # свой ответ на один вид запросов
    model.on('promptReviewCases', ModelError('rate_limited'))  # ошибка вместо ответа
    model.calls_of('promptMap')                       # все запросы этого вида
"""
import glob
import os
import re
import threading
from dataclasses import dataclass, field

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class ModelError(Exception):
    """Модель «ответила ошибкой»: в приложении это исключение с кодом (rate_limited, invalid_json, ...)."""
    def __init__(self, code='invalid_json', message=''):
        super().__init__(code)
        self.code, self.message = code, message


@dataclass
class Call:
    kind: str
    prompt: str
    info: dict = field(default_factory=dict)
    index: int = 0   # номер запроса этого вида, с нуля


def _signatures():
    sigs = []
    for f in glob.glob(os.path.join(ROOT, 'prompts', '*.md')):
        first = open(f, encoding='utf-8').readline().strip()
        sig = first.split('⟦')[0].strip()
        if len(sig) >= 20:
            sigs.append((sig, os.path.basename(f)[:-3]))
    return sorted(sigs, key=lambda x: -len(x[0]))


SIGS = _signatures()


def _split_signatures():
    """Промпты базы знаний начинаются одинаково («Ты — аналитик базы знаний … по продукту «⟦…⟧».») и различаются дальше:
    для них сравнивается вся первая строка, а подстановки ⟦…⟧ считаются любым текстом."""
    by = {}
    for f in glob.glob(os.path.join(ROOT, 'prompts', '*.md')):
        first = open(f, encoding='utf-8').readline().strip()
        by.setdefault(first.split('⟦')[0].strip(), []).append((first, os.path.basename(f)[:-3]))
    out = []
    for items in by.values():
        if len(items) < 2 or len(items[0][0].split('⟦')[0].strip()) < 20:
            continue
        for first, kind in items:
            out.append((re.compile('.*?'.join(re.escape(p) for p in re.split(r'⟦[^⟧]*⟧', first)), re.S), kind))
    return out


SPLIT_SIGS = _split_signatures()


def classify(prompt):
    head = prompt[:600]
    long_head = prompt[:3000]
    for rx, kind in SPLIT_SIGS:
        if rx.match(long_head):
            return kind
    for sig, kind in SIGS:
        if sig in head:
            return kind
    if 'Верни только изменения паспорта' in prompt:
        return 'promptPassportDelta'
    if 'Ты ведёшь «паспорт продукта»' in prompt:
        return 'promptPassportFull'
    if 'Проверка связи' in prompt:
        return 'ping'
    return 'unknown'


def num(prompt, pat, default=None):
    m = re.search(pat, prompt)
    return m.group(1) if m else default


# ---------- ответы по умолчанию: тестовое ТЗ «Восстановление пароля» ----------
def _analyze(c):
    return {'requirements': [
        {'title': 'Ссылка «Забыли пароль?»', 'description': 'На /login есть ссылка', 'types': ['ui'], 'priority': 'high', 'doc': 'Пример', 'section': '2.1', 'quote': 'отображается ссылка', 'criteria': ['Ссылка видна под полем пароля']},
        {'title': 'API запроса сброса', 'description': 'POST /api/v1/password-reset', 'types': ['api'], 'priority': 'high', 'doc': 'Пример', 'section': '3.1', 'quote': 'POST', 'criteria': ['202 для корректного email', '400 INVALID_EMAIL']},
        {'title': 'Сквозное восстановление', 'description': 'Полный путь', 'types': ['e2e'], 'priority': 'high', 'doc': 'Пример', 'section': '5', 'quote': '', 'criteria': []},
        {'title': 'Лимит запросов', 'types': ['api', 'ui'], 'priority': 'medium', 'criteria': ['3 запроса за 15 минут']},
    ], 'questions': ['Что происходит при 4-м запросе через UI?']}


def _plan(c):
    if '## Уже есть в продукте' in c.prompt:
        e2e = num(c.prompt, r'- (E2E-\d+) \[e2e\]')
        return {'items': [
            {'type': 'ui', 'title': 'Форма — новые проверки', 'requirementIds': ['R-001'], 'checks': ['Кнопка неактивна при пустом поле']},
            {'type': 'api', 'title': 'API — новые проверки', 'requirementIds': ['R-002'], 'checks': ['429 на четвёртый запрос']},
        ], 'alreadyCovered': [{'requirementId': 'R-003', 'caseIds': [e2e]}] if e2e else []}
    return {'items': [
        {'type': 'ui', 'title': 'Форма', 'requirementIds': ['R-001'], 'checks': ['Ссылка видна', 'Переход на экран']},
        {'type': 'api', 'title': 'API', 'requirementIds': ['R-002'], 'checks': ['202', '400']},
        {'type': 'e2e', 'title': 'E2E', 'requirementIds': ['R-003', 'R-002'], 'checks': ['Полный путь']},
    ]}


def _checklist(c):
    return {'groups': [
        {'title': 'Форма восстановления', 'items': [
            {'check': 'Отображение ссылки «Забыли пароль?»', 'expected': 'Ссылка видна под полем пароля', 'kind': 'positive', 'type': 'ui', 'priority': 'high', 'suites': ['smoke', 'regression'], 'requirementIds': ['R-001']},
            {'check': 'Email без @ в форме восстановления', 'expected': 'Сообщение «Введите корректный email»', 'kind': 'negative', 'type': 'ui', 'priority': 'medium', 'suites': ['regression'], 'requirementIds': ['R-001']}]},
        {'title': 'API сброса', 'items': [
            {'check': 'Запрос сброса с корректным email', 'expected': 'POST /api/v1/password-reset — 202', 'kind': 'positive', 'type': 'api', 'priority': 'high', 'suites': ['smoke', 'regression'], 'requirementIds': ['R-002']},
            {'check': 'Четвёртый запрос за 15 минут', 'expected': '429 RATE_LIMIT', 'kind': 'negative', 'type': 'api', 'priority': 'medium', 'suites': ['regression'], 'requirementIds': ['R-002']}]},
    ]}


def case_body(title, check='проверка'):
    return {'title': title, 'id': '', 'priority': 'High', 'preconditions': ['Пользователь зарегистрирован'],
            'steps': [{'step': 1, 'action': 'Открыть /login', 'expected': 'Открыта страница'}], 'expectedResult': 'ok', 'tags': ['t']}


def _generate(c):
    """Один кейс на пункт плана; если пункт плана собран из чек-листа — кейс связан с первым его пунктом."""
    items = re.findall(r'### ([A-Z]+-\d+)\.', c.prompt)
    out = []
    for k, pid in enumerate(items):
        cl = re.findall(r'(?m)^\d+\. (CL-\d+) · ', re.search(r'### ' + re.escape(pid) + r'\.(.*?)(?=\n### |\Z)', c.prompt, re.S).group(1))
        out.append({'planItem': pid, 'requirementIds': [], 'suites': ['smoke', 'regression'] if k == 0 else ['regression'],
                    **({'checklistId': cl[0]} if cl else {}), 'testCase': case_body(f'Кейс для {pid}: проверка восстановления пароля')})
    return {'cases': out}


def generate_per_check(c):
    """Кейс на каждый пункт чек-листа в запросе (как просит промпт)."""
    out = []
    for k, pid in enumerate(re.findall(r'### ([A-Z]+-\d+)\.', c.prompt)):
        block = re.search(r'### ' + re.escape(pid) + r'\.(.*?)(?=\n### |\Z)', c.prompt, re.S).group(1)
        for j, cl in enumerate(re.findall(r'(?m)^\d+\. (CL-\d+) · ', block) or [None]):
            out.append({'planItem': pid, 'requirementIds': [], 'suites': ['smoke', 'regression'] if k == 0 and j == 0 else ['regression'],
                        **({'checklistId': cl} if cl else {}), 'testCase': case_body(f'Кейс для {pid}{" " + cl if cl else ""}: проверка восстановления пароля')})
    return {'cases': out}


def _review(c):
    m = re.search(r'"id": "([A-Z0-9-]+)"', c.prompt) or re.search(r'(CL-\d+)', c.prompt)
    if not m:
        return {'findings': []}
    tid = m.group(1)
    return {'findings': [{'targetId': tid, 'severity': 'minor' if tid.startswith('CL') else 'critical', 'category': 'Соответствие ТЗ',
                          'message': 'Ожидаемый результат не совпадает с п. 3.1: должен быть код 202.', 'suggestion': 'Указать код 202 и тело {"status":"sent"}.'}]}


def _passport_full(c):
    return {'passport': '## Назначение и границы\n- Восстановление пароля в личном кабинете (ТЗ v1.3)\n## Бизнес-правила и ограничения\n- Не более 3 запросов на сброс за 15 минут'}


def _passport_delta(c):
    return {'ops': [{'op': 'add', 'section': 'Бизнес-правила и ограничения', 'text': 'Ссылка действует 30 минут'}]}


def src_blocks(prompt):
    """Кейсы из файла в запросе сверки и актуализации: [(номер из заголовка «### #N», текст блока)]."""
    return [(int(m.group(1)), m.group(2)) for m in re.finditer(r'(?m)^### #(\d+)\b(.*?)(?=^### #|\Z)', prompt, re.S)]


def _map(c):
    blocks = src_blocks(c.prompt)
    out = []
    for i, text in blocks:
        ty = 'api' if re.search(r'POST|api', text, re.I) else 'e2e' if re.search(r'Сквозн|e2e', text, re.I) else 'ui'
        st = 'obsolete' if 'SMS' in text else 'changed' if 'Неверный email' in text else 'same'
        out.append({'index': i, 'type': ty, 'requirementIds': ['R-002'] if ty == 'api' else ['R-003'] if ty == 'e2e' else ['R-001'], 'status': st,
                    'reason': 'Восстановления по SMS в ТЗ нет' if st == 'obsolete' else 'п. 2.3: текст ошибки изменился' if st == 'changed' else 'Соответствует ТЗ',
                    'instruction': 'Ожидаемый результат: «Неверный email» → «Введите корректный email»' if st == 'changed' else ''})
    return {'cases': out}


def _actualize(c):
    blocks = [(i, 'Статус: "changed"' in text) for i, text in src_blocks(c.prompt)]
    return {'cases': [{'index': i, 'suites': ['regression'], 'changes': ['Ожидаемый результат: «Неверный email» → «Введите корректный email»'] if ch else [],
                       'testCase': case_body(f'Актуализированный кейс #{i}')} for i, ch in blocks]}


def _etalon(c):
    """Сравнение с эталоном: по правилу на вид теста + правило, которое уже есть в шаблоне (его агент не должен показать)."""
    t = 'API' if 'вида API' in c.prompt else 'UI' if 'вида UI' in c.prompt else 'E2E'
    rules = [
        {'text': f'В ожидаемом результате {t}-кейса указывай точный текст сообщения из эталона', 'why': 'в эталоне тексты дословные', 'generated': [f'{t}-001'], 'etalon': f'Эталон {t} 1'},
        {'text': f'Каждый {t}-кейс начинай с предусловия о роли пользователя', 'why': 'в эталоне роль в предусловиях', 'generated': [], 'etalon': ''},
    ]
    if t == 'API':   # уже есть в шаблоне API — агент не должен его показать
        rules.append({'text': 'Один тест-кейс проверяет один эндпоинт и одну ситуацию (позитивную или негативную).', 'why': 'дубль действующего правила'})
    return {'summary': f'Эталон {t} конкретнее в ожидаемых результатах.', 'rules': rules}


DEFAULTS = {
    'promptAnalyze': _analyze,
    'promptAnalyzeMore': lambda c: {'requirements': [], 'criteria': []},
    'promptTrace': lambda c: {'steps': [{'n': 1, 'title': 'Инициация действия (Frontend/UI)', 'layer': 'Frontend', 'details': ['Действие: пользователь отправляет форму']}, {'n': 2, 'title': 'Обработка на стороне сервиса', 'layer': 'Backend', 'details': ['Сервис получает JSON и десериализует тело']}], 'failure': {'error': 'ClassCastException', 'location': 'TimeBasedRuleDto', 'cause': 'тип поля не совпадает с данными'}, 'response': {'status': '500', 'body': 'Ошибка десериализации'}, 'result': 'Правило не создано', 'summary': 'Проверить тип поля в DTO', 'questions': ['Приложите стек трейс']},
    'promptDefect': lambda c: {'title': 'Сохранение правила корреляции по времени возвращает 500', 'severity': 'Critical', 'priority': 'high', 'component': 'Backend: rule-service', 'environment': '', 'preconditions': ['Пользователь с правами администратора'], 'steps': ['1. Открыть раздел «Правила корреляции»', 'Создать правило типа «по времени» с интервалом 30', 'Нажать «Сохранить»'], 'expected': 'Правило сохранено', 'actual': 'Ошибка 500, правило не создано', 'analysis': 'ClassCastException в TimeBasedRuleDto: интервал приходит числом', 'fields': [{'name': 'Версия сборки', 'value': 'нет данных'}], 'relatedCases': ['API-001', 'API-999'], 'duplicates': []},
    'promptCoverageAudit': lambda c: {'gaps': []},
    'promptCoverRequirement': lambda c: {'checks': [
        {'check': 'Основной сценарий: запрос на восстановление пароля отправлен', 'kind': 'positive', 'type': 'ui'},
        {'check': 'Пустой email — ошибка «Введите адрес»', 'kind': 'negative', 'type': 'ui'},
        {'check': 'Email длиной 254 символа принимается', 'kind': 'boundary', 'type': 'ui'}]},
    'promptChecklist': _checklist,
    'promptPlan': _plan,
    'promptGenerate': _generate,
    'promptReviewCases': _review,
    'promptReviewChecklist': _review,
    'promptRefine': lambda c: case_body('Доработанный кейс'),
    'promptRefineItem': lambda c: {'check': 'Исправленный пункт с конкретным лимитом 3 запроса', 'priority': 'high', 'suites': ['regression']},
    'promptReviseBatch': lambda c: {'cases': []},
    'promptImpact': lambda c: {'criteria': [{'requirementId': 'R-004', 'add': ['На 4-й запрос UI показывает таймер']}], 'update': [], 'add': [], 'checklistUpdate': []},
    'promptEtalon': _etalon,
    'promptLesson': lambda c: {'rule': 'В ожидаемом результате API-кейсов всегда указывай код ответа и ключевые поля тела', 'scope': 'both'},
    'promptPassportFull': _passport_full,
    'promptPassportDelta': _passport_delta,
    'promptMap': _map,
    'promptActualize': _actualize,
    'ping': lambda c: {'ok': True, 'model': 'mock'},
}


class MockModel:
    def __init__(self):
        self.calls = []
        self.handlers = {}
        self._lock = threading.Lock()

    def on(self, kind, handler):
        """handler — функция call → JSON, готовый JSON или ModelError (его бросят/вернут как ошибку модели)."""
        self.handlers[kind] = handler
        return self

    def calls_of(self, *kinds):
        return [c for c in self.calls if c.kind in kinds]

    def prompts_of(self, *kinds):
        return [c.prompt for c in self.calls_of(*kinds)]

    def reset(self):
        self.calls.clear()

    # вызывается из страницы (window.__model)
    def handle(self, prompt, info=None):
        kind = classify(prompt)
        with self._lock:
            call = Call(kind, prompt, info or {}, sum(1 for c in self.calls if c.kind == kind))
            self.calls.append(call)
        h = self.handlers.get(kind, DEFAULTS.get(kind))
        try:
            if isinstance(h, ModelError):
                raise h
            res = h(call) if callable(h) else h if h is not None else {}
            if isinstance(res, ModelError):
                raise res
            if isinstance(res, dict) and '__tools' in res:
                return res
            return {'json': res}
        except ModelError as e:
            return {'__error': {'code': e.code, 'message': e.message}}
