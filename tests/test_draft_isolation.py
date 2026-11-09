"""Черновик не в продукте: ни его кейсы, ни его чек-лист не видны во вкладке «Тест-кейсы» продукта, не попадают в индекс
продукта (проверки на повторы следующих запусков) и не занимают номера — до кнопки «Добавить в проект»."""
import pytest

from tests.support import files, model_draft as md, seed
from tests.test_generation import set_outputs


def index(app, kind):
    """Индекс продукта в базе: products/<id>/meta/<cases|checklist>."""
    doc = app.db.get(f'products/{app.state("S.productId")}/meta/{kind}') or {}
    return doc.get('items', [])


def product_cases(app):
    app.call('(a.S.pc.at = 0, true)')
    app.call('(a.ensureProdCases(true), true)')
    app.page.wait_for_function('() => window.__qa.S.pc.loaded && !window.__qa.S.pc.busy', timeout=15000)
    app.page.wait_for_timeout(300)
    return app.call('a.prodItems().map((x) => x.i)')


def settle(app):
    """Сохранение запуска и индекса продукта идёт фоном — ждём, пока очередь записи опустеет."""
    app.page.wait_for_timeout(1500)


@pytest.fixture
def both(app):
    """Черновик с чек-листом и кейсами по нему."""
    app.add_sample()
    set_outputs(app, cases=True, checklist=True)
    app.generate()
    assert app.state('S.run.stage') == 'draft' and app.state('S.run.cases.length') > 0
    assert app.call('a.checklistItems(S.run).length') > 0
    settle(app)
    return app


def add(app):
    app.tab('draft')
    app.page.click('[data-act=draft-add]')
    if app.count('[data-act=draft-add].armed'):
        app.page.click('[data-act=draft-add].armed')
    app.page.wait_for_function("() => window.__qa.S.run.stage === 'added'", timeout=15000)
    settle(app)


# ---------- кейсы ----------
def test_draft_cases_are_not_in_product_cases_tab(both):
    assert product_cases(both) == []
    both.tab('cases')
    assert both.count('[data-act=cases-scope][data-s=product]') == 0   # нет переключателя «Весь продукт» с черновиком


def test_added_cases_appear_in_product_cases_tab(both):
    ids = sorted(both.state('S.run.cases.map((c) => c.dispId)'))
    add(both)
    assert sorted(product_cases(both)) == ids


def test_other_draft_run_is_not_shown_in_product(app, tmp_path):
    """Черновик другого запуска (сохранённый, не открытый) — тоже не в продукте."""
    draft = seed.run('run_d', 'Док', [seed.case('u1', 'api', 'API-001', '[BE] POST /x — черновик', ['R-001'])], [seed.req('R-001', 'Док')], stage='draft')
    done = seed.run('run_a', 'Док', [seed.case('u2', 'ui', 'UI-001', '[FE] Вход', ['R-001'])], [seed.req('R-001', 'Док')], created=1700000200000)
    app.import_product(seed.write(tmp_path, seed.product_export(runs=[draft, done])))
    assert product_cases(app) == ['UI-001']


def test_added_stage_is_saved_at_once(both):
    """Стадия «добавлен» пишется в базу сразу: перезагрузка сразу после нажатия не возвращает запуск в черновики."""
    both.tab('draft')
    both.page.click('[data-act=draft-add]')
    if both.count('[data-act=draft-add].armed'):
        both.page.click('[data-act=draft-add].armed')
    both.page.wait_for_function('() => window.__qa.S.prodIndex.cases.length > 0', timeout=15000)   # индекс — после сохранения стадии
    runs = both.db.children(f'products/{both.state("S.productId")}/runs')
    assert [m.get('stage') for m in runs.values()] == ['added']


# ---------- чек-лист ----------
def test_draft_checklist_is_not_in_product_index(both):
    assert both.state('S.prodIndex.checklist.length') == 0 and index(both, 'checklist') == []
    assert both.state('(S.products.find((p) => p.id === S.productId).counters || {}).cl || 0') == 0   # номера не заняты


def test_added_checklist_goes_to_product_index(both):
    n = both.call('a.checklistItems(S.run).length')
    add(both)
    assert len(index(both, 'checklist')) == n and both.state('S.prodIndex.checklist.length') == n


def test_next_run_does_not_treat_draft_checklist_as_existing(both, tmp_path):
    both.page.click('#btn-newses')
    both.upload(files.spec_file(tmp_path))
    both.generate()
    p = both.model.prompts_of('promptChecklist')[-1]
    assert '## Уже есть в продукте' not in p


def test_checklist_only_draft_can_be_added_to_project(app):
    app.add_sample()
    set_outputs(app, cases=False, checklist=True)
    app.generate()
    n = app.call('a.checklistItems(S.run).length')
    assert app.state('S.run.stage') == 'draft' and n > 0
    app.tab('draft')
    assert f'Добавить в проект ({n})' in app.text('[data-act=draft-add]')
    settle(app)
    assert index(app, 'checklist') == []
    add(app)
    assert len(index(app, 'checklist')) == n


def test_draft_checklist_left_in_index_by_old_version_is_removed(app, tmp_path):
    """Прежние версии писали чек-лист черновика в индекс продукта — при чтении запусков продукта он убирается."""
    draft = seed.run('run_d', 'Док', [seed.case('u1', 'api', 'API-001', '[BE] POST /x', ['R-001'])], [seed.req('R-001', 'Док')], stage='draft')
    done = seed.run('run_a', 'Док', [seed.case('u2', 'ui', 'UI-001', '[FE] Вход', ['R-001'])], [seed.req('R-001', 'Док')], created=1700000200000)
    data = seed.product_export(runs=[draft, done])
    data['index']['checklist'] = [{'r': 'run_d', 'i': 'CL-001', 't': 'api', 'n': 'Пункт черновика'}, {'r': 'run_a', 'i': 'CL-002', 't': 'ui', 'n': 'Пункт проекта'}]
    app.import_product(seed.write(tmp_path, data))
    product_cases(app)
    app.page.wait_for_function("() => window.__qa.S.prodIndex.checklist.every((x) => x.r !== 'run_d')", timeout=15000)
    assert [x['i'] for x in app.state('S.prodIndex.checklist')] == ['CL-002']


def test_checklist_numbers_taken_by_other_run_are_renumbered_on_add(both):
    ids = both.call('a.checklistItems(S.run).map((it) => it.id)')
    both.call("S.prodIndex.checklist.push({ r: 'run_other', i: arg, t: 'ui', n: 'чужой' })", ids[0])
    add(both)
    now = both.call('a.checklistItems(S.run).map((it) => it.id)')
    assert now[0] != ids[0] and len(set(now)) == len(now)
    assert all(c.get('checklistId') != ids[0] for c in both.state('S.run.cases'))   # кейсы ссылаются на новый номер
