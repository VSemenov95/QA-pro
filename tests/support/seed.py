"""Готовые продукты и запуски для тестов: выгрузка продукта в формате QA pro (её можно загрузить кнопкой «Импорт»)."""
import json
import os


def case(uid, ty, disp_id, title, reqs=(), suites=('regression',), **extra):
    tc = {'id': disp_id, 'title': title, 'priority': 'High', 'preconditions': ['Пользователь зарегистрирован'],
          'steps': [{'step': 1, 'action': 'Открыть /login', 'expected': 'Открыта страница входа'}], 'expectedResult': 'ok'}
    tc.update(extra.pop('testCase', {}))
    c = {'uid': uid, 'type': ty, 'planItem': 'P-01', 'requirementIds': list(reqs), 'suites': list(suites), 'dispId': disp_id, 'testCase': tc}
    c.update(extra)
    return c


def req(rid, doc, title=None, types=('ui',)):
    return {'id': rid, 'title': title or 'Требование ' + rid, 'description': 'd', 'criteria': [], 'types': list(types), 'priority': 'High', 'doc': doc, 'section': '1', 'quote': '', 'inScope': True}


def run(run_id, doc, cases, reqs, stage='added', created=1700000000000, status='done'):
    """Сохранённый запуск: meta + части с кейсами (как их пишет приложение)."""
    meta = {'id': run_id, 'kind': 'run', 'status': status, 'stage': stage, 'createdAt': created, 'finishedAt': created + 100000, 'partsCount': 1, 'srcParts': 0,
            'docs': [{'id': 'd-' + run_id, 'name': doc}], 'requirements': reqs, 'questions': [], 'plan': [], 'settings': {'types': ['api', 'ui', 'e2e']},
            'counters': {'api': 0, 'ui': 0, 'e2e': 0, 'cl': 0}, 'mode': 'generate', 'by': 'local', 'updatedAt': created + 100000}
    return {'meta': meta, 'parts': [{'cases': cases}], 'src': []}


def product_export(name='Магазин', runs=None, index=None, case_sections=None):
    """index=None — собрать индекс из запусков со стадией added (как делает приложение); index=[] — пустой индекс."""
    runs = runs or []
    if index is None:
        index = [{'r': r['meta']['id'], 'i': c['dispId'], 't': c['type'], 'n': c['testCase']['title']}
                 for r in runs if r['meta']['stage'] != 'draft' for p in r['parts'] for c in p['cases']]
    n = sum(len(p['cases']) for r in runs for p in r['parts'])
    return {'format': 'qa-pro-product', 'version': 1, 'exportedAt': '2026-10-12T00:00:00Z',
            'product': {'name': name, 'description': '', 'qaCtx': {}, 'passport': None, 'passportPrev': None, 'counters': {'api': 0, 'ui': 0, 'e2e': 0, 'cl': 0},
                        'stats': {'cases': len(index), 'checklist': 0, 'lastRunAt': 1700000100000}, 'createdAt': 1700000000000, 'caseSections': case_sections or {}},
            'docs': [], 'index': {'cases': index, 'checklist': []}, 'known': None, 'runs': runs, 'kb': {'index': None, 'blocks': []}, '_cases': n}


def shop_export(**kw):
    """Две документа, семь кейсов: «ТЗ-Авторизация» (3), «ТЗ-Платежи» (3) и один кейс без требований."""
    a = run('run_a', 'ТЗ-Авторизация.docx', [
        case('u1', 'ui', 'UI-001', '[FE] Вход с верным паролем', ['R-001']), case('u2', 'api', 'API-001', '[BE] POST /login — успех', ['R-001']),
        case('u3', 'ui', 'UI-002', '[FE] Вход без пароля', ['R-002'])], [req('R-001', 'ТЗ-Авторизация.docx'), req('R-002', 'ТЗ-Авторизация.docx')], created=1700000000000)
    b = run('run_b', 'ТЗ-Платежи.md', [
        case('u4', 'api', 'API-002', '[BE] POST /pay — оплата картой', ['R-001']), case('u5', 'ui', 'UI-003', '[FE] Оплата: ошибка карты', ['R-001']),
        case('u6', 'e2e', 'E2E-001', '[E2E] Покупка от корзины до чека', ['R-001', 'R-002']), case('u7', 'ui', 'UI-004', 'Ручной кейс без требований', [])],
        [req('R-001', 'ТЗ-Платежи.md'), req('R-002', 'ТЗ-Платежи.md')], created=1700000001000)
    return product_export(runs=[a, b], **kw)


def write(tmp_path, data, name='product.json'):
    d = {k: v for k, v in data.items() if not k.startswith('_')}
    p = os.path.join(str(tmp_path), name)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False)
    return p
