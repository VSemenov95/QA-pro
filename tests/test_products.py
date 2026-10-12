"""Продукты: выбор и создание, документы и контекст продукта, индекс кейсов и нумерация между запусками, панель продукта, экспорт и импорт."""
import json
import re

import pytest

from tests.support import files, model_kb, seed
from tests.support.db import MemoryDB

SAMPLE = 'Пример — ТЗ восстановление пароля.md'
CASE_IDS = ['API-001', 'API-002', 'E2E-001', 'UI-001']


def pid_of(app):
    return app.state('S.productId')


def product_doc(app, pid=None):
    return app.db.get(f'products/{pid or pid_of(app)}')


def add_draft(app):
    app.tab('draft')
    app.page.click('[data-act=draft-add]')
    app.page.wait_for_function('() => window.__qa.S.prodIndex.cases.length > 0 && window.__qa.S.run.stage !== "draft"')
    app.wait_idle()


def first_run(app):
    """Генерация по примеру ТЗ и добавление кейсов в проект: в продукте 4 кейса и 4 пункта чек-листа."""
    app.generate()
    add_draft(app)
    return app


def second_run(app):
    app.page.click('#btn-newses')
    app.page.wait_for_function('() => !window.__qa.S.run')
    app.js("() => { const S = window.__qa.S; for (const d of S.docs) S.runDocs.add(d.id); window.__qa.renderAll(); }")   # документ снова в запуск
    app.model.reset()
    app.generate()


def index_ids(app):
    return sorted(x['i'] for x in app.db.get(f'products/{pid_of(app)}/meta/cases')['items'])


def select_text(app):
    return app.page.eval_on_selector('#prod-select', 'e => e.selectedOptions[0].textContent')


def new_product(app, name, desc='', **kw):
    return app.create_product(name, desc)


# ---------- выбор и создание ----------
def test_new_user_gets_a_product_with_the_sample(app):
    assert select_text(app) == 'Мой продукт' and app.count('#prod-select option') == 2
    assert app.page.eval_on_selector('#prod-select option:last-child', 'e => e.textContent') == '+ Новый продукт…'
    assert app.text('#doc-list .doc-name') == SAMPLE and 'Мой продукт' in app.text('#prod-info')


def test_selector_subline_counts_documents_and_cases(app):
    assert app.text('#ps-sub') == '1 документ · 0 тест-кейсов'
    first_run(app)
    assert app.text('#ps-sub') == '1 документ · 4 тест-кейса'


def test_extra_context_is_saved_in_the_product_and_restored(app):
    app.page.fill('#qa-ctx', 'Окружение stage, роль Оператор')
    app.page.wait_for_function('() => !window.__qa.S.ctxDirty')
    assert product_doc(app)['qaCtx']['all'] == 'Окружение stage, роль Оператор'
    app.reload()
    assert app.page.input_value('#qa-ctx') == 'Окружение stage, роль Оператор'


def test_create_product_from_the_dialog(app):
    app.page.select_option('#prod-select', '__new')
    app.page.wait_for_selector('#prod-name')
    assert app.visible('#prod-ov')
    app.page.fill('#prod-name', 'Биллинг')
    app.page.fill('#prod-desc', 'Счета и оплаты')
    app.page.press('#prod-name', 'Enter')
    app.page.wait_for_function("() => window.__qa.S.products.some((p) => p.name === 'Биллинг') && window.__qa.S.prodReady && window.__qa.S.productId === window.__qa.S.products.find((p) => p.name === 'Биллинг').id")
    assert select_text(app) == 'Биллинг' and not app.visible('#prod-ov')
    d = product_doc(app)
    assert d['name'] == 'Биллинг' and d['description'] == 'Счета и оплаты' and d['docs'] == [] and d['counters'] == {'api': 0, 'ui': 0, 'e2e': 0, 'cl': 0}
    assert 'Счета и оплаты' in app.text('#prod-info')


def test_new_product_starts_empty(app):
    app.page.fill('#qa-ctx', 'контекст первого продукта')
    app.create_product('Биллинг')
    assert names_in_list(app) == [] and app.page.input_value('#qa-ctx') == '' and app.state('S.run') is None and app.state('S.tab') == 'agent'
    assert app.text('#ps-sub') == '0 документов · 0 тест-кейсов'


def test_product_name_is_required(app):
    app.page.select_option('#prod-select', '__new')
    app.page.wait_for_selector('#prod-name')
    app.page.click('[data-pact=save]')
    assert 'Введите название продукта.' in app.text('#prod-body') and app.state('S.products.length') == 1


def test_product_names_must_differ(app):
    app.page.select_option('#prod-select', '__new')
    app.page.wait_for_selector('#prod-name')
    app.page.fill('#prod-name', ' мой  продукт ')
    app.page.click('[data-pact=save]')
    assert 'Продукт с таким названием уже есть.' in app.text('#prod-body') and app.state('S.products.length') == 1


def test_dialog_can_be_cancelled(app):
    app.page.select_option('#prod-select', '__new')
    app.page.wait_for_selector('#prod-name')
    app.page.click('#prod-ov [data-close]')
    assert not app.visible('#prod-ov') and select_text(app) == 'Мой продукт'


def test_rename_and_describe_product(app):
    app.page.click('[data-act=prod-edit]')
    app.page.wait_for_selector('#prod-name')
    assert app.page.input_value('#prod-name') == 'Мой продукт'
    app.page.fill('#prod-name', 'Личный кабинет')
    app.page.fill('#prod-desc', 'Веб-кабинет клиента')
    app.page.click('[data-pact=save]')
    app.page.wait_for_function("() => window.__qa.S.products[0].name === 'Личный кабинет'")
    assert select_text(app) == 'Личный кабинет' and product_doc(app)['description'] == 'Веб-кабинет клиента'
    assert 'Веб-кабинет клиента' in app.text('#prod-info')


def names_in_list(app):
    return app.page.eval_on_selector_all('#doc-list .doc-name', 'els => els.map((e) => e.textContent)')


def test_documents_and_context_belong_to_the_product(app, tmp_path):
    app.state('S.settings.kbAuto = false')
    first = pid_of(app)
    app.page.fill('#qa-ctx', 'контекст 1')
    app.page.wait_for_function('() => !window.__qa.S.ctxDirty')
    second = app.create_product('Биллинг')
    app.upload(files.write(tmp_path / 'счета.md', '# Счета\n- Счёт — документ на оплату\n'))
    app.page.fill('#qa-ctx', 'контекст 2')
    app.page.wait_for_function('() => !window.__qa.S.ctxDirty')
    app.page.select_option('#prod-select', first)
    app.page.wait_for_function('(p) => window.__qa.S.productId === p && window.__qa.S.docs.length === 1', arg=first)
    assert names_in_list(app) == [SAMPLE] and app.page.input_value('#qa-ctx') == 'контекст 1'
    app.page.select_option('#prod-select', second)
    app.page.wait_for_function('(p) => window.__qa.S.productId === p && window.__qa.S.docs.length === 1', arg=second)
    assert names_in_list(app) == ['счета.md'] and app.page.input_value('#qa-ctx') == 'контекст 2'


def test_uploaded_document_is_saved_in_the_product(app, tmp_path):
    app.state('S.settings.kbAuto = false')
    text = '# Счета\n- Счёт — документ на оплату\n'
    app.upload(files.write(tmp_path / 'счета.md', text))
    app.page.wait_for_function('() => window.__qa.S.products[0].docs.length === 2')
    d = product_doc(app)
    meta = next(m for m in d['docs'] if m['name'] == 'счета.md')
    assert meta['chars'] == len(text.strip()) and meta['parts'] == 1 and meta['sample'] is False
    assert app.db.get(f'products/{pid_of(app)}/docparts/{meta["id"]}_0')['text'] == text.strip()


def test_documents_are_loaded_back_after_reload(app, tmp_path):
    app.state('S.settings.kbAuto = false')
    app.upload(files.write(tmp_path / 'счета.md', '# Счета\n- Счёт — документ на оплату\n'))
    app.page.wait_for_function('() => window.__qa.S.products[0].docs.length === 2')
    app.reload()
    app.page.wait_for_function("() => window.__qa.S.docs.length === 2 && window.__qa.S.docs.every((d) => d.status === 'ready')")
    app.mode('help')
    assert names_in_list(app) == [SAMPLE, 'счета.md']


def test_product_cannot_be_switched_while_generation_runs(app):
    app.js('window.__sampleDelay = 300')
    app.generate(wait=False)
    app.page.wait_for_function('() => window.__qa.S.running')
    assert app.page.is_disabled('#prod-select') and 'после окончания генерации' in app.page.get_attribute('#prod-select', 'title')
    app.wait_idle()
    assert not app.page.is_disabled('#prod-select')


def test_delete_product_removes_all_its_data(app, tmp_path):
    app.state('S.settings.kbAuto = false')
    first = pid_of(app)
    second = app.create_product('Биллинг')
    app.upload(files.write(tmp_path / 'счета.md', '# Счета\n- Счёт — документ на оплату\n'))
    app.page.wait_for_function('() => window.__qa.S.products.find((p) => p.name === "Биллинг").docs.length === 1')
    app.page.click('[data-act=prod-del]')
    assert app.state('S.products.length') == 2   # первое нажатие только просит подтверждения
    app.page.click('[data-act=prod-del]')
    app.page.wait_for_function('(p) => window.__qa.S.products.length === 1 && window.__qa.S.productId === p', arg=first)
    assert [k for k in app.db.store if second in k] == []
    assert select_text(app) == 'Мой продукт'


def test_deleting_the_only_product_creates_a_fresh_one(app):
    old = pid_of(app)
    app.page.click('[data-act=prod-del]')
    app.page.click('[data-act=prod-del]')
    app.page.wait_for_function('(o) => window.__qa.S.productId && window.__qa.S.productId !== o && window.__qa.S.docs.length === 0', arg=old)
    assert select_text(app) == 'Мой продукт' and [k for k in app.db.store if old in k] == []


@pytest.mark.xfail(strict=True, reason='БАГ: «Удалить продукт» не удаляет историю вопросов к базе знаний этого продукта: запись data/users/<пользователь>/help_<id продукта> остаётся в базе навсегда')
def test_delete_product_removes_question_history(app):
    model_kb.install(app.model)
    first = pid_of(app)
    second = app.create_product('Биллинг')
    app.mode('help')
    app.page.click('[data-act=help-view][data-v=qa]')
    app.page.fill('#help-input', 'Что умеет продукт?')
    app.page.press('#help-input', 'Enter')
    app.page.wait_for_function("() => document.querySelectorAll('#help-list .hq').length >= 1")
    app.wait_idle()
    app.mode('generate')
    app.page.click('[data-act=prod-del]')
    app.page.click('[data-act=prod-del]')
    app.page.wait_for_function('(p) => window.__qa.S.productId === p', arg=first)
    app.wait_idle()
    assert [k for k in app.db.store if second in k] == []


def test_panel_folds_to_one_line_summary(app):
    app.page.click('[data-act=pp-toggle] >> nth=0')
    assert app.text('.pp-sum') == '1 документ · 0 кейсов · чек-лист 0 · знаний нет'
    assert app.js("localStorage.getItem('qapro.prodOpen')") == 'false'
    app.reload()
    assert app.count('.pp-sum') == 1


# ---------- индекс кейсов, нумерация ----------
def test_added_cases_go_to_the_product_index(app):
    first_run(app)
    items = app.db.get(f'products/{pid_of(app)}/meta/cases')['items']
    assert sorted(x['i'] for x in items) == CASE_IDS
    assert {x['t'] for x in items} == {'api', 'ui', 'e2e'} and all(x['r'] == app.state('S.run.id') and x['n'].startswith('[') for x in items)


def test_checklist_goes_to_the_product_index(app):
    first_run(app)
    cl = app.db.get(f'products/{pid_of(app)}/meta/checklist')['items']
    assert [x['i'] for x in cl] == ['CL-001', 'CL-002', 'CL-003', 'CL-004'] and all(x['r'] == app.state('S.run.id') for x in cl)


def test_counters_and_stats_follow_the_run(app):
    first_run(app)
    d = product_doc(app)
    assert d['counters'] == {'api': 2, 'ui': 1, 'e2e': 1, 'cl': 4} and d['stats']['cases'] == 4 and d['stats']['checklist'] == 4 and d['stats']['lastRunAt'] > 0


def test_cases_in_draft_do_not_take_numbers(app):
    app.generate()
    assert product_doc(app)['counters'] == {'api': 0, 'ui': 0, 'e2e': 0, 'cl': 4}   # номера кейсов не заняты, пока кейсы не добавлены в проект
    assert app.db.get(f'products/{pid_of(app)}/meta/cases') is None


def test_run_is_saved_inside_the_product(app):
    first_run(app)
    runs = app.db.children(f'products/{pid_of(app)}/runs')
    assert len(runs) == 1 and next(iter(runs.values()))['productId'] == pid_of(app)


def test_second_run_continues_numbering(app):
    first_run(app)
    second_run(app)
    ids = app.state('S.run.cases.map((c) => c.dispId)')
    assert ids == ['API-003', 'API-004', 'UI-002']   # E2E-001 уже есть в продукте, поэтому нового сквозного кейса нет
    add_draft(app)
    assert index_ids(app) == sorted(CASE_IDS + ids) and len(set(index_ids(app))) == 7


def test_second_run_sees_existing_cases_and_knowledge(app):
    first_run(app)
    second_run(app)
    for kind in ('promptChecklist', 'promptPlan', 'promptGenerate'):
        ps = app.model.prompts_of(kind)
        assert ps and all('## Знания о продукте' in p for p in ps), kind
    assert '## Уже есть в продукте' in app.model.prompts_of('promptPlan')[0] and '- E2E-001 [e2e]' in app.model.prompts_of('promptPlan')[0]
    assert any('## Уже есть в продукте' in p for p in app.model.prompts_of('promptGenerate'))


def test_requirement_covered_by_product_is_marked_in_requirements(app):
    first_run(app)
    second_run(app)
    assert app.state('S.run.coveredExisting') == [{'requirementId': 'R-003', 'caseIds': ['E2E-001']}]
    app.tab('reqs')
    row = app.page.eval_on_selector_all('#tab-body tr', "rows => rows.map((r) => r.innerText.replace(/\\s+/g, ' ')).find((t) => t.startsWith('R-003'))")
    assert 'в продукте' in row
    app.tab('agent')
    assert 'Уже покрыто кейсами продукта, новые не нужны: R-003 (E2E-001)' in app.text('.timeline')


def test_checklist_of_second_run_continues_numbering(app):
    first_run(app)
    second_run(app)
    ids = app.state("S.run.checklist.groups.flatMap((g) => g.items.map((i) => i.id))")
    assert ids and min(int(i.split('-')[1]) for i in ids) > 4


def test_product_history_lists_the_runs(app):
    first_run(app)
    app.tab('history')
    app.page.wait_for_selector('.hrow')
    assert 'Запуски продукта «Мой продукт»' in app.text('#tab-body') and app.count('.hrow') == 1
    assert SAMPLE in app.text('.hrow h4') and 'API 2' in app.text('.hrow .meta')


def test_history_is_kept_per_product(app):
    first_run(app)
    first = pid_of(app)
    app.create_product('Биллинг')
    app.tab('history')
    app.page.wait_for_function("() => /Запусков пока нет/.test(document.querySelector('#tab-body').textContent)")
    app.page.select_option('#prod-select', first)
    app.page.wait_for_function('() => window.__qa.S.docs.length === 1')
    app.tab('history')
    app.page.wait_for_selector('.hrow')


# ---------- панель продукта ----------
def test_panel_shows_counters_after_a_run(app):
    first_run(app)
    stats = app.page.eval_on_selector_all('#prod-info .pp-stats .stat', "els => els.map((e) => e.innerText.replace(/\\s+/g, ' ').trim())")
    assert stats == ['ДОКУМЕНТОВ 1 2,5 тыс. знаков', 'ТЕСТ-КЕЙСОВ 4 API 2 · UI 1 · E2E 1', 'ЧЕК-ЛИСТ 4 пунктов в продукте', 'ЗНАНИЯ 150 знаков в паспорте']


def test_panel_lists_recent_runs(app):
    first_run(app)
    assert app.count('#prod-info .pp-run') == 1 and 'открыт' in app.text('#prod-info .pp-run')


# ---------- экспорт и импорт продукта ----------
def export_product(app):
    n = len(app.downloads())
    app.page.click('[data-act=prod-export]')
    app.page.wait_for_function('(n) => (window.__downloads || []).length > n', arg=n)
    d = app.downloads()[-1]
    return d['filename'], json.loads(app.js('window.__dlData'))


def test_export_has_product_documents_knowledge_and_runs(app):
    first_run(app)
    name, data = export_product(app)
    assert re.fullmatch(r'qa-pro-мой-продукт-\d{4}-\d\d-\d\d\.json', name)
    assert data['format'] == 'qa-pro-product' and data['version'] == 1 and data['product']['name'] == 'Мой продукт'
    assert [d['name'] for d in data['docs']] == [SAMPLE] and data['docs'][0]['sample'] is True
    assert len(data['runs']) == 1 and sorted(x['i'] for x in data['index']['cases']) == CASE_IDS
    assert data['product']['passport']['text'] and data['product']['counters']['api'] == 2


def test_export_does_not_include_sample_text_but_includes_own_documents(app, tmp_path):
    app.state('S.settings.kbAuto = false')
    app.upload(files.write(tmp_path / 'счета.md', '# Счета\n- Счёт — документ на оплату\n'))
    app.page.wait_for_function('() => window.__qa.S.products[0].docs.length === 2')
    _, data = export_product(app)
    docs = {d['name']: d for d in data['docs']}
    assert docs[SAMPLE]['text'] == '' and docs['счета.md']['text'] == '# Счета\n- Счёт — документ на оплату'


@pytest.fixture
def copy(app, tmp_path):
    """Продукт с контекстом QA и одним запуском выгружен и загружен как копия."""
    app.page.fill('#qa-ctx', 'Окружение stage')
    app.page.wait_for_function('() => !window.__qa.S.ctxDirty')
    first_run(app)
    _, data = export_product(app)
    app.exported = files.write(tmp_path / 'product.json', app.js('window.__dlData'))
    app.import_product(app.exported)
    app.page.wait_for_function("() => window.__qa.S.products.length === 2 && window.__qa.S.prodReady && window.__qa.S.products.find((p) => p.id === window.__qa.S.productId).name !== 'Мой продукт'")
    app.wait_idle()
    return app


def test_import_creates_a_copy_with_a_new_name(copy):
    assert select_text(copy) == 'Мой продукт (копия)' and copy.state('S.products.length') == 2


def test_second_import_gets_the_next_copy_number(copy):
    copy.import_product(copy.exported)
    copy.page.wait_for_function("() => window.__qa.S.products.length === 3 && window.__qa.S.products.every((p) => p.docs !== undefined) && window.__qa.S.products.find((p) => p.id === window.__qa.S.productId).name === 'Мой продукт (копия 2)'")


def test_copy_keeps_documents_knowledge_and_counters(copy):
    assert names_in_list(copy) == [SAMPLE]
    d = product_doc(copy)
    assert d['counters'] == {'api': 2, 'ui': 1, 'e2e': 1, 'cl': 4} and d['passport']['len'] > 0
    assert 'Назначение и границы' in copy.state('S.products.find((p) => p.id === S.productId).passport.text')


def test_copy_keeps_extra_context(copy):
    assert copy.page.input_value('#qa-ctx') == 'Окружение stage' and product_doc(copy)['qaCtx']['all'] == 'Окружение stage'


def test_copy_remembers_what_the_passport_already_knows(copy):
    """Требования, которые паспорт уже усвоил, в копии повторно не отправляются модели."""
    if copy.state('!!S.run'):
        copy.page.click('#btn-newses')
        copy.page.wait_for_function('() => !window.__qa.S.run')
    copy.js("() => { const S = window.__qa.S; for (const d of S.docs) S.runDocs.add(d.id); window.__qa.renderAll(); }")
    copy.model.reset()
    copy.generate()
    assert copy.model.calls_of('promptPassportFull', 'promptPassportDelta') == []
    assert 'Новых сведений нет' in copy.state("S.run.steps.knowledge.log.map((l) => l.text).join(' ')")


def test_copy_has_the_same_cases_in_its_index(copy):
    assert index_ids(copy) == CASE_IDS


def test_copy_shows_all_cases_on_the_cases_tab(copy):
    assert copy.state('S.tab') == 'cases' and copy.count('#pcase-list .case') == 4


def test_history_of_the_copy_lists_the_run(copy):
    copy.tab('history')
    copy.page.wait_for_selector('.hrow')
    assert 'Запуски продукта «Мой продукт (копия)»' in copy.text('#tab-body') and copy.count('.hrow') == 1


def test_numbering_continues_in_the_copy(copy):
    if copy.state('!!S.run'):
        copy.page.click('#btn-newses')
        copy.page.wait_for_function('() => !window.__qa.S.run')
    copy.js("() => { const S = window.__qa.S; for (const d of S.docs) S.runDocs.add(d.id); window.__qa.renderAll(); }")
    copy.generate()
    assert copy.state('S.run.cases.map((c) => c.dispId)') == ['API-003', 'API-004', 'UI-002']


def test_copy_does_not_change_the_original(copy):
    original = next(p for p in copy.state('S.products.map((p) => ({ id: p.id, name: p.name }))') if p['name'] == 'Мой продукт')
    assert product_doc(copy, original['id'])['stats']['cases'] == 4 and len(copy.db.children(f'products/{original["id"]}/runs')) == 1


def test_foreign_file_is_not_imported(app, tmp_path):
    app.import_product(files.write(tmp_path / 'other.json', '{"hello": "world"}'))
    app.page.wait_for_function("() => /Это не файл продукта QA pro/.test(document.querySelector('#toasts').textContent)")
    assert app.state('S.products.length') == 1


def test_broken_file_is_not_imported(app, tmp_path):
    app.import_product(files.write(tmp_path / 'broken.json', '{"format": "qa-pro-product", '))
    app.page.wait_for_function("() => /Это не файл продукта QA pro/.test(document.querySelector('#toasts').textContent)")
    assert app.state('S.products.length') == 1


# ---------- запуски без продукта (прежняя версия) ----------
TEXT = 'ТЗ (legacy): лимит 3 запроса за 15 минут, затем 429 RATE_LIMIT.'


@pytest.fixture
def legacy_db():
    """База пользователя, который работал до появления продуктов: сессия с документом и контекстом и один готовый запуск (API-007, UI-005)."""
    db = MemoryDB()
    cases = [seed.case('c1', 'api', 'API-007', '[BE] 429 на четвёртый запрос', ['R-001']), seed.case('c2', 'ui', 'UI-005', '[FE] Сообщение о лимите', ['R-001'])]
    run = seed.run('run_legacy', 'legacy.txt', cases, [seed.req('R-001', 'legacy.txt', 'Лимит', ('api',))])
    meta = {k: v for k, v in run['meta'].items() if k not in ('stage',)}
    meta['counters'] = {'api': 7, 'ui': 5, 'e2e': 0, 'cl': 0}
    db.store['data/users/u_test/session'] = {'kind': 'session', 'docs': [{'id': 'dL', 'name': 'legacy.txt', 'ext': 'txt', 'chars': len(TEXT), 'parts': 1}],
                                             'qaCtx': {'all': 'legacy ctx', 'api': '', 'ui': '', 'e2e': ''}, 'runId': 'run_legacy', 'tab': 'cases'}
    db.store['data/users/u_test/session/docparts/dL_0'] = {'docId': 'dL', 'i': 0, 'text': TEXT}
    db.store['data/users/u_test/run_legacy'] = meta
    db.store['data/users/u_test/run_legacy/parts/p0'] = run['parts'][0]
    return db


def test_work_before_products_moves_into_the_first_product(make_app, legacy_db):
    app = make_app(db=legacy_db)
    app.page.wait_for_function("() => window.__qa.S.docs.length === 1 && window.__qa.S.docs[0].status === 'ready'")
    app.mode('help')
    assert select_text(app) == 'Мой продукт' and names_in_list(app) == ['legacy.txt'] and app.page.input_value('#qa-ctx') == 'legacy ctx'
    pid = pid_of(app)
    assert legacy_db.get(f'products/{pid}/docparts/dL_0')['text'] == TEXT


def test_legacy_run_is_listed_apart_and_can_be_moved(make_app, legacy_db):
    app = make_app(db=legacy_db)
    app.tab('history')
    app.page.wait_for_selector('[data-act=move-hist]')
    assert 'Личные запуски без продукта' in app.text('#tab-body')
    app.page.click('[data-act=move-hist]')
    app.page.wait_for_function("() => window.__qa.S.prodIndex.cases.length === 2")
    assert index_ids(app) == ['API-007', 'UI-005'] and legacy_db.get('data/users/u_test/run_legacy') is None
    assert legacy_db.get(f'products/{pid_of(app)}/runs/run_legacy')['productId'] == pid_of(app)


def test_numbering_continues_after_a_moved_run(make_app, legacy_db):
    app = make_app(db=legacy_db)
    app.tab('history')
    app.page.wait_for_selector('[data-act=move-hist]')
    app.page.click('[data-act=move-hist]')
    app.page.wait_for_function("() => window.__qa.S.prodIndex.cases.length === 2")
    app.page.click('#btn-newses')
    app.page.wait_for_function('() => !window.__qa.S.run')
    app.js("() => { const S = window.__qa.S; for (const d of S.docs) S.runDocs.add(d.id); window.__qa.renderAll(); }")
    app.generate()
    ids = app.state('S.run.cases.map((c) => c.dispId)')
    assert ids and all(int(i.split('-')[1]) > {'API': 7, 'UI': 5, 'E2E': 0}[i.split('-')[0]] for i in ids)
