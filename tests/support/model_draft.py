"""Ответы мок-модели для черновика, ревью, исправления и сокращения набора.

Обработчики подключаются так:  app.model.on('promptReviewCases', model_draft.review({'API-001': [...]}))
"""
import json
import os
import re

from .model import ROOT, Call


def template_case(ty, title):
    """Тест-кейс ровно по образцу шаблона templates/<вид>.md: у него есть все поля, поэтому автоматическая проверка полей шаблона молчит."""
    with open(os.path.join(ROOT, 'templates', ty + '.md'), encoding='utf-8') as f:
        text = f.read()
    sample = json.loads(text.split('```json\n', 1)[1].rsplit('\n```', 1)[0])
    sample = sample[0] if isinstance(sample, list) else sample
    sample['title'] = title
    sample['id'] = ''
    return sample


def plan_items(prompt):
    """Шаги плана из запроса «Напиши тест-кейсы»: [(P-01, вид)]."""
    ty = 'api' if 'вида API' in prompt else 'ui' if 'вида UI' in prompt else 'e2e'
    return [(pid, ty) for pid in re.findall(r'### ([A-Z]+-\d+)\.', prompt)]


def generate_by_template(call: Call):
    """Кейсы по шаблону вместо «неполных» кейсов мока: ревью не находит в них недостающих полей."""
    cases = []
    for k, (pid, ty) in enumerate(plan_items(call.prompt)):
        cases.append({'planItem': pid, 'requirementIds': [], 'suites': ['smoke', 'regression'] if k == 0 else ['regression'],
                      'testCase': template_case(ty, f'Кейс для {pid}: проверка восстановления пароля')})
    return {'cases': cases}


def reviewed_ids(prompt):
    """id кейсов в блоке «Кейсы на ревью» (в запросе они записаны компактным JSON: "id":"API-001")."""
    block = prompt.split('## Кейсы на ревью', 1)[-1]
    return re.findall(r'\{"id":"([A-Z0-9-]+)","type"', block)


def finding(target, severity='major', message='Ожидаемый результат не совпадает с п. 3.1', suggestion='Указать код 202'):
    return {'targetId': target, 'severity': severity, 'category': 'Соответствие ТЗ', 'message': message, 'suggestion': suggestion}


def review(by_case):
    """Ревьюер: {'API-001': ['critical', 'minor'], 'UI-001': ['major']} → замечания к этим кейсам; остальным кейсам замечаний нет."""
    def handler(call: Call):
        out = []
        for cid in reviewed_ids(call.prompt):
            for n, sev in enumerate(by_case.get(cid, [])):
                out.append(finding(cid, sev, f'Замечание {n + 1} к {cid}'))
        return {'findings': out}
    return handler


def reduce_keep(ids):
    """Модель сокращения «выбрала» эти кейсы."""
    return lambda call: {'keep': list(ids)}


def reduce_line_ids(prompt):
    """Кейсы из запроса сокращения: строки «id | вид | приоритет | требования | заголовок»."""
    block = prompt.split('## Кейсы', 1)[1].split('## Требования', 1)[0]
    return [m.group(1) for m in re.finditer(r'(?m)^([A-Z0-9]+-\d+) \|', block)]


def make_draft(app, review=None):
    """Генерация на мок-модели без чек-листа: в запуске остаются только кейсы по шаблонам — API-001, API-002, UI-001, E2E-001 (черновик)."""
    app.model.on('promptGenerate', generate_by_template)
    if review is not None:
        app.model.on('promptReviewCases', review)
    app.page.click('label:has(#out-checklist)')
    app.generate()
    assert app.state('S.run.status') == 'done', app.state('S.run.error')
    return app


def add_to_project(app):
    """Кнопка «Добавить в проект» (при критичных замечаниях — с подтверждением); ждёт, пока кейсы попадут в индекс продукта."""
    n = app.state('S.run.cases.length')
    app.page.click('[data-act=draft-add]')
    if app.count('[data-act=draft-add].armed'):
        app.page.click('[data-act=draft-add].armed')
    app.page.wait_for_function("() => window.__qa.S.run.stage === 'added'", timeout=15000)
    app.page.wait_for_function('(n) => window.__qa.S.prodIndex.cases.length >= n', arg=n, timeout=15000)


def run_path(app):
    return app.state('`products/${S.productId}/runs/${S.run.id}`')


def wait_db(app, pred, what='запись в базе', tries=100):
    """Запуск сохраняется в базу отложенно: ждём, пока в ней появится нужное (pred получает базу), а не спим фиксированное время."""
    for _ in range(tries):
        if pred(app.db):
            return
        app.page.wait_for_timeout(100)
    raise AssertionError('не дождались: ' + what)


def wait_saved(app, cases=None, stage=None):
    """Ждёт, пока сохранённый запуск станет таким: столько кейсов и/или такая стадия."""
    path = run_path(app)
    wait_db(app, lambda db: (cases is None or len((db.get(path + '/parts/p0') or {}).get('cases', [])) == cases)
            and (stage is None or (db.get(path) or {}).get('stage') == stage), f'запуск сохранён: кейсов {cases}, стадия {stage}')
