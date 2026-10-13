"""Результаты запуска: вкладки «Требования», «Тест-кейсы» и «Чек-лист» — фильтры, ручная правка, форма, доработка с ИИ."""
import json

import pytest

from tests.support.model import ModelError
from tests.support.model_generation import CLIPBOARD_JS, generate_by_template, three_steps_cases, wait_until


@pytest.fixture
def results(app):
    """Сгенерированный пример ТЗ: 4 кейса (API-001, API-002, UI-001, E2E-001), чек-лист из 4 пунктов; открыта вкладка «Тест-кейсы»."""
    app.add_sample()
    app.generate()
    app.tab('cases')
    return app


def row(app, disp_id):
    return app.page.locator(f'#case-list article:has(.case-id:text-is("{disp_id}"))')


def open_case(app, disp_id):
    row(app, disp_id).locator('.case-h').click()
    return row(app, disp_id)


def case_state(app, disp_id, expr):
    return app.state(f"(() => {{ const c = S.run.cases.find((x) => x.dispId === '{disp_id}'); return {expr}; }})()")


def visible_ids(app):
    return app.page.eval_on_selector_all('#case-list article .case-id', 'els => els.map((e) => e.textContent)')


# ---------- требования ----------
def test_requirement_row_shows_details_and_cases(results):
    results.tab('reqs')
    results.page.click('tr.req-row[data-id=R-002]')
    d = results.text('tr.req-detail')
    assert 'POST /api/v1/password-reset' in d and '202 для корректного email' in d and 'API-001' in d


def test_requirement_coverage_cell(results):
    results.tab('reqs')
    assert results.text('#tab-body .sec-h .muted') == 'покрыто 4 из 4'


def test_goto_case_from_requirement_opens_it(results):
    results.tab('reqs')
    results.page.click('tr.req-row[data-id=R-001]')
    results.page.click('tr.req-detail [data-act=goto-case]')
    assert results.state('S.tab') == 'cases' and results.count('#case-list .case-b') == 1
    assert row(results, 'UI-001').locator('.case-b').count() == 1


# ---------- фильтры ----------
def test_filter_chips_show_counts(results):
    chips = results.page.eval_on_selector_all('.toolbar:not(.scope-sw) .fchip', "els => els.map((e) => e.innerText.replace(/\\s+/g, ' '))")
    assert chips == ['Все 4', 'API 2', 'UI 1', 'E2E 1', 'Смоук 3', 'Регресс 4']


def test_type_filter(results):
    results.page.click('[data-act=ftype][data-t=api]')
    assert visible_ids(results) == ['API-001', 'API-002']


def test_smoke_filter_and_back(results):
    results.page.click('[data-act=fsuite][data-s=smoke]')
    assert sorted(visible_ids(results)) == ['API-001', 'E2E-001', 'UI-001']
    results.page.click('[data-act=fsuite][data-s=smoke]')
    assert len(visible_ids(results)) == 4


def test_regression_filter(results):
    results.page.click('[data-act=fsuite][data-s=regression]')
    assert len(visible_ids(results)) == 4


def test_type_and_suite_filters_combine(results):
    results.page.click('[data-act=ftype][data-t=api]')
    results.page.click('[data-act=fsuite][data-s=smoke]')
    assert visible_ids(results) == ['API-001']


def test_search_by_id_and_by_text(results):
    results.page.fill('#case-q', 'api-002')
    assert visible_ids(results) == ['API-002']
    results.page.fill('#case-q', 'Открыть /login')   # текст шага внутри кейса
    assert len(visible_ids(results)) == 4
    results.page.fill('#case-q', 'нет такого текста')
    assert visible_ids(results) == [] and 'Ничего не найдено' in results.text('#case-list')


def test_expand_and_collapse_all(results):
    results.page.click('[data-act=expand-all]')
    assert results.count('#case-list .case-b') == 4
    results.page.click('[data-act=collapse-all]')
    assert results.count('#case-list .case-b') == 0


def test_opened_case_shows_template_fields_without_title_and_id_duplicates(results):
    body = open_case(results, 'UI-001').locator('.case-b').inner_text()
    low = body.lower()   # заголовки полей на экране набраны капсом стилем, а не в тексте
    assert 'предусловия' in low and 'шаги' in low and 'ожидаемый результат' in low and 'Открыть /login' in body
    assert 'проверка восстановления пароля' not in low   # название — в заголовке, не в теле


def test_suite_toggle_on_case_changes_its_suites(results):
    open_case(results, 'API-002')
    results.page.click('#case-list [data-act=case-suite][data-s=smoke]')
    assert case_state(results, 'API-002', 'c.suites') == ['smoke', 'regression']
    results.page.click('#case-list [data-act=case-suite][data-s=regression]')
    assert case_state(results, 'API-002', 'c.suites') == ['smoke']


def test_case_after_suite_toggle_is_found_by_the_filter(results):
    open_case(results, 'API-002')
    results.page.click('#case-list [data-act=case-suite][data-s=smoke]')
    results.page.click('[data-act=fsuite][data-s=smoke]')
    assert len(visible_ids(results)) == 4


@pytest.mark.xfail(strict=True, reason='БАГ: после переключения набора «Смоук» у кейса числа на кнопках фильтров («Смоук 3», «Регресс 4») '
                   'остаются прежними, пока не перерисуется вкладка: перерисовывается только список кейсов')
def test_suite_filter_counts_follow_the_toggle(results):
    open_case(results, 'API-002')
    results.page.click('#case-list [data-act=case-suite][data-s=smoke]')
    assert results.text('[data-act=fsuite][data-s=smoke] .n') == '4'


# ---------- форма редактирования ----------
@pytest.fixture
def steps3(app):
    app.model.on('promptGenerate', three_steps_cases)
    app.add_sample()
    app.generate()
    app.tab('cases')
    return app


def form_of(app, disp_id='API-001'):
    open_case(app, disp_id)
    app.page.click(f'#case-list article:has(.case-id:text-is("{disp_id}")) [data-act=form-case]')


def test_form_saves_new_title_and_step(results):
    form_of(results)
    results.page.fill('.case-form input[data-fp="title"]', 'Ручная правка названия')
    results.page.click('[data-act=ff-row][data-op=add]')
    n = results.count('.ff-table tbody tr')
    assert n == 2
    results.page.locator('.ff-table tbody tr').nth(n - 1).locator('textarea').first.fill('Новый шаг')
    results.page.click('[data-act=ff-save]')
    assert case_state(results, 'API-001', 'c.testCase.title') == 'Ручная правка названия'
    assert case_state(results, 'API-001', 'c.testCase.steps.map((s) => [s.step, s.action])') == [[1, 'Открыть /login'], [2, 'Новый шаг']]
    assert 'Ручная правка названия' in results.text('#case-list article:has(.case-id:text-is("API-001")) .case-t')


def test_form_has_no_field_for_case_id(results):
    form_of(results)
    fields = results.page.eval_on_selector_all('.case-form [data-fp]', 'els => els.map((e) => e.dataset.fp.split("|")[0])')
    assert 'id' not in fields and 'title' in fields


def test_form_cancel_keeps_the_case(results):
    form_of(results)
    results.page.fill('.case-form input[data-fp="title"]', 'Не сохранится')
    results.page.click('[data-act=ff-cancel]')
    assert case_state(results, 'API-001', 'c.testCase.title') == '[BE] Кейс для P-02: проверка восстановления пароля'


def test_form_changes_requirement_links(results):
    form_of(results)
    results.page.fill('.case-form input[data-meta=reqs]', 'R-001, R-003;R-004')
    results.page.click('[data-act=ff-save]')
    assert case_state(results, 'API-001', 'c.requirementIds') == ['R-001', 'R-003', 'R-004']


def test_form_rows_move_and_renumber(steps3):
    form_of(steps3)
    steps3.page.click('[data-act=ff-row][data-op=down][data-i="0"]')
    steps3.page.click('[data-act=ff-row][data-op=del][data-i="2"]')
    steps3.page.click('[data-act=ff-save]')
    assert case_state(steps3, 'API-001', 'c.testCase.steps.map((s) => [s.step, s.action])') == [[1, 'Действие 2'], [2, 'Действие 1']]


def test_form_json_field_error_blocks_saving(results):
    form_of(results)
    results.page.click('[data-act=ff-json]')
    results.page.fill('#case-list textarea[data-field=draft]', '{"title": ')
    results.page.click('[data-act=save-edit]')
    assert 'Ошибка JSON' in results.text('#case-list .case-note.err')
    assert case_state(results, 'API-001', 'c.testCase.title').startswith('[BE]')


@pytest.fixture
def full(app):
    """Кейсы ровно по образцу шаблона: у API-кейса есть вложенный объект request."""
    app.model.on('promptGenerate', generate_by_template)
    app.add_sample()
    app.generate()
    app.tab('cases')
    return app


def test_form_edits_nested_object_as_json(full):
    form_of(full)
    req = full.state("S.run.cases.find((c) => c.dispId === 'API-001').testCase.request")
    req['endpoint'] = '/api/v2/password-reset'
    full.page.fill('.case-form textarea[data-fp="request"]', json.dumps(req, ensure_ascii=False))
    full.page.click('[data-act=ff-save]')
    assert case_state(full, 'API-001', 'c.testCase.request.endpoint') == '/api/v2/password-reset'
    assert case_state(full, 'API-001', 'c.testCase.request.headers') == {'Content-Type': 'application/json'}


def test_form_json_error_names_the_field_and_blocks_saving(full):
    form_of(full)
    full.page.fill('.case-form input[data-fp="title"]', '[BE] Не сохранится')
    full.page.fill('.case-form textarea[data-fp="request"]', '{"method": ')
    full.page.click('[data-act=ff-save]')
    assert full.text('#case-list .case-note.err').startswith('Поле «Запрос»: ошибка JSON')
    assert case_state(full, 'API-001', 'c.testCase.title').startswith('[BE] Кейс для')


def test_form_list_of_strings_is_edited_one_per_line(full):
    form_of(full)
    full.page.fill('.case-form textarea[data-fp="tags"]', 'password-reset\nnegative\n\n')
    full.page.fill('.case-form textarea[data-fp="preconditions"]', 'Первое условие\nВторое условие')
    full.page.click('[data-act=ff-save]')
    assert case_state(full, 'API-001', '[c.testCase.tags, c.testCase.preconditions]') == [['password-reset', 'negative'], ['Первое условие', 'Второе условие']]


def test_form_keeps_field_order_of_template(full):
    form_of(full)
    full.page.fill('.case-form input[data-fp="title"]', '[BE] Новый заголовок')
    full.page.click('[data-act=ff-save]')
    assert case_state(full, 'API-001', 'Object.keys(c.testCase)') == ['id', 'title', 'priority', 'preconditions', 'request', 'steps', 'expectedResult', 'tags']


def test_json_edit_requires_an_object(results):
    open_case(results, 'API-001')
    results.page.click('#case-list article:has(.case-id:text-is("API-001")) [data-act=edit-case]')
    results.page.fill('#case-list textarea[data-field=draft]', '[1, 2]')
    results.page.click('[data-act=save-edit]')
    assert results.text('#case-list .case-note.err') == 'Нужен JSON-объект.'


def test_json_edit_saves_valid_object(results):
    open_case(results, 'API-001')
    results.page.click('#case-list article:has(.case-id:text-is("API-001")) [data-act=edit-case]')
    tc = results.state("S.run.cases.find((c) => c.dispId === 'API-001').testCase")
    tc['title'] = '[BE] Правка JSON'
    results.page.fill('#case-list textarea[data-field=draft]', json.dumps(tc, ensure_ascii=False))
    results.page.click('[data-act=save-edit]')
    assert case_state(results, 'API-001', 'c.testCase.title') == '[BE] Правка JSON'


def test_undo_returns_previous_version_after_form_save(results):
    form_of(results)
    results.page.fill('.case-form input[data-fp="title"]', 'Другое название')
    results.page.click('[data-act=ff-save]')
    results.page.click('#case-list [data-act=undo-case]')
    assert case_state(results, 'API-001', 'c.testCase.title') == '[BE] Кейс для P-02: проверка восстановления пароля'


# ---------- ручные кейсы ----------
def add_manual(app, ty='api', title=None):
    app.page.click(f'.cases-foot [data-act=add-case][data-t={ty}]')
    if title:
        app.page.locator('.case-form input[data-fp="title"]').last.fill(title)
        app.page.locator('[data-act=ff-save]').last.click()


def test_manual_case_gets_next_number_and_mark(results):
    add_manual(results, 'api', 'Ручной API-кейс')
    assert case_state(results, 'API-003', 'c.testCase.title') == 'Ручной API-кейс'
    assert results.state('S.run.cases.length') == 5
    assert case_state(results, 'API-003', '[c.manual, c.planItem, c.suites, c.requirementIds]') == [True, 'manual', ['regression'], []]
    assert 'вручную' in results.text('#case-list article:has(.case-id:text-is("API-003")) .case-sub')


def test_cancelled_manual_case_releases_its_number(results):
    results.page.click('.cases-foot [data-act=add-case][data-t=ui]')
    results.page.click('[data-act=ff-cancel]')
    assert results.state('S.run.cases.length') == 4
    add_manual(results, 'ui', 'Второй заход')
    assert case_state(results, 'UI-002', 'c.testCase.title') == 'Второй заход'


def test_manual_case_form_follows_template_fields(results):
    results.page.click('.cases-foot [data-act=add-case][data-t=api]')
    fields = results.page.eval_on_selector_all('.case-form [data-fp]', 'els => [...new Set(els.map((e) => e.dataset.fp.split("|")[0]))]')
    assert fields[:3] == ['title', 'priority', 'preconditions'] and 'steps' in fields and 'request' in fields


def test_delete_case_needs_second_click(results):
    open_case(results, 'API-002')
    btn = '#case-list article:has(.case-id:text-is("API-002")) [data-act=del-case]'
    results.page.click(btn)
    assert results.state('S.run.cases.length') == 4 and results.text(btn) == 'Точно удалить?'
    results.page.click(btn)
    assert visible_ids(results) == ['API-001', 'UI-001', 'E2E-001']
    assert 'API-002 удалён' in ' '.join(results.toast_texts())


# ---------- доработка кейса с ИИ ----------
def refine(app, disp_id='API-001', comment='Сделай короче'):
    open_case(app, disp_id)
    app.page.click(f'#case-list article:has(.case-id:text-is("{disp_id}")) [data-act=refine-case]')
    app.page.fill('textarea[data-field=comment]', comment)
    app.page.click('[data-act=do-refine]')


def test_refine_replaces_case_and_keeps_its_number(results):
    refine(results)
    results.page.wait_for_selector('.case-note:has-text("Кейс доработан.")')
    assert case_state(results, 'API-001', 'c.testCase.title') == '[BE] Доработанный кейс'
    assert case_state(results, 'API-001', 'c.testCase.id') == 'API-001'


def test_refine_prompt_has_comment_and_current_case(results):
    refine(results, comment='Укажи код ответа в ожидаемом результате')
    results.page.wait_for_selector('.case-note:has-text("Кейс доработан.")')
    p = results.model.prompts_of('promptRefine')[0]
    assert 'Укажи код ответа в ожидаемом результате' in p and 'Кейс для P-02: проверка восстановления пароля' in p


def test_refine_without_comment_asks_to_describe(results):
    open_case(results, 'API-001')
    results.page.click('#case-list [data-act=refine-case]')
    results.page.click('[data-act=do-refine]')
    assert results.text('#case-list .case-note.err') == 'Опишите, что нужно исправить.'
    assert len(results.model.calls_of('promptRefine')) == 0


@pytest.mark.parametrize('err,text', [(ModelError('invalid_json'), 'Модель ответила не в формате JSON.'), (ModelError('rate_limited'), 'Слишком много запросов')])
def test_refine_error_is_shown_and_case_stays(results, err, text):
    results.model.on('promptRefine', err)
    refine(results)
    results.page.wait_for_selector('#case-list .case-note.err')
    assert text in results.text('#case-list .case-note.err')
    assert case_state(results, 'API-001', 'c.testCase.title').startswith('[BE] Кейс для P-02')


def test_refine_can_be_undone(results):
    refine(results)
    results.page.wait_for_selector('.case-note:has-text("Кейс доработан.")')
    results.page.click('#case-list [data-act=undo-case]')
    assert case_state(results, 'API-001', 'c.testCase.title').startswith('[BE] Кейс для P-02')


def test_refine_remark_becomes_a_rule_for_the_team(results):
    refine(results, comment='Укажи код ответа в ожидаемом результате')
    lessons = wait_until(results, lambda: results.db.children('lessons'))
    assert [v['text'] for v in lessons.values()] == ['В ожидаемом результате API-кейсов всегда указывай код ответа и ключевые поля тела']
    assert 'Укажи код ответа в ожидаемом результате' in results.model.prompts_of('promptLesson')[0]


def test_short_remark_is_not_generalized(results):
    refine(results, comment='ок')
    results.page.wait_for_selector('.case-note:has-text("Кейс доработан.")')
    assert len(results.model.calls_of('promptLesson')) == 0


# ---------- копирование ----------
@pytest.fixture
def copying(make_app):
    app = make_app(init=CLIPBOARD_JS)
    app.add_sample()
    app.generate()
    return app


def copied(app):
    app.page.wait_for_function("() => window.__copied !== undefined")
    return app.js('window.__copied')


def test_copy_case_json(copying):
    copying.tab('cases')
    open_case(copying, 'UI-001')
    copying.page.click('#case-list [data-act=copy-case]')
    assert json.loads(copied(copying)) == copying.state("S.run.cases.find((c) => c.dispId === 'UI-001').testCase")
    assert 'Скопировано в буфер обмена' in ' '.join(copying.toast_texts())


def test_copy_checklist_gives_markdown(copying):
    copying.tab('checklist')
    copying.page.click('[data-act=cl-copy]')
    assert copied(copying).startswith('# Чек-лист\n\n## Форма восстановления\n\n- [ ] CL-001 ')


def test_copy_export_gives_the_file_text(copying):
    copying.tab('export')
    copying.page.click('[data-act=copy-out]')
    assert json.loads(copied(copying))['testCases']['api'][0]['id'] == 'API-001'


# ---------- чек-лист ----------
def cl_texts(app):
    return app.page.eval_on_selector_all('.cl-item', "els => els.map((e) => [e.querySelector('.cl-id').textContent, e.querySelector('.cl-text')?.textContent])")


@pytest.fixture
def checklist(results):
    results.tab('checklist')
    return results


def test_checklist_shows_groups_and_items(checklist):
    groups = checklist.page.eval_on_selector_all('.cl-group', "els => els.map((g) => [g.querySelector('h4').firstChild.textContent.trim(), [...g.querySelectorAll('.cl-id')].map((i) => i.textContent)])")
    assert groups == [['Форма восстановления', ['CL-001', 'CL-002']], ['API сброса', ['CL-003', 'CL-004']]]


def test_checklist_filter_chips(checklist):
    chips = checklist.page.eval_on_selector_all('.toolbar:not(.scope-sw) .fchip', "els => els.map((e) => e.innerText.replace(/\\s+/g, ' '))")
    assert chips == ['Все 4', 'API 2', 'UI 2', 'Смоук 2', 'Регресс 4']
    checklist.page.click('[data-act=cl-fsuite][data-s=smoke]')
    assert [i for i, _ in cl_texts(checklist)] == ['CL-001', 'CL-003']
    checklist.page.click('[data-act=cl-ftype][data-t=api]')
    assert [i for i, _ in cl_texts(checklist)] == ['CL-003']


def test_checklist_suite_toggle(checklist):
    checklist.page.click('[data-act=cl-suite][data-id=CL-002][data-s=smoke]')
    assert checklist.state("S.run.checklist.groups[0].items[1].suites") == ['smoke', 'regression']
    assert checklist.text('[data-act=cl-fsuite][data-s=smoke] .n') == '3'


def test_checklist_markdown_download(checklist):
    checklist.page.click('[data-act=cl-dl-md]')
    checklist.page.wait_for_function('() => window.__downloads && window.__downloads.length')
    d = checklist.downloads()[-1]
    day = checklist.state('new Date(S.run.createdAt).toISOString().slice(0, 10)')
    assert d['filename'] == f'checklist_{day}.md'
    lines = d['text'].splitlines()
    assert lines[0] == '# Чек-лист' and '## Форма восстановления' in lines
    assert '- [ ] CL-001 Ссылка «Забыли пароль?» видна под полем пароля — UI, высокий, смоук, регресс (R-001)' in lines
    assert '- [ ] CL-004 Четвёртый запрос за 15 минут — 429 RATE_LIMIT — API, средний, регресс (R-002)' in lines


def test_checklist_json_download(checklist):
    checklist.page.click('[data-act=cl-dl-json]')
    checklist.page.wait_for_function('() => window.__downloads && window.__downloads.length')
    out = json.loads(checklist.downloads()[-1]['text'])
    assert out['sources'] == ['Пример — ТЗ восстановление пароля.md']
    assert [g['title'] for g in out['groups']] == ['Форма восстановления', 'API сброса']
    assert out['groups'][1]['items'][0] == {'id': 'CL-003', 'check': 'POST /api/v1/password-reset с корректным email — 202', 'type': 'api', 'priority': 'P3_HIGH', 'suites': ['smoke', 'regression'], 'requirementIds': ['R-002']}


def new_item(app, text, group='0'):
    app.page.click('[data-act=cl-add][data-gi="0"]')
    app.page.fill('#cl-input', text)
    app.page.select_option('#cl-group', group)
    app.page.click('[data-act=cl-save]')


def test_manual_checklist_item_goes_to_chosen_group(checklist):
    new_item(checklist, 'Ручной пункт', group='1')
    assert checklist.state("S.run.checklist.groups[1].items.map((i) => [i.id, i.check, i.manual])")[-1] == ['CL-005', 'Ручной пункт', True]
    assert checklist.state("S.run.checklist.groups[0].items.length") == 2


def test_empty_new_item_is_dropped_on_cancel(checklist):
    checklist.page.click('[data-act=cl-add][data-gi="0"]')
    checklist.page.click('[data-act=cl-cancel]')
    assert [i for i, _ in cl_texts(checklist)] == ['CL-001', 'CL-002', 'CL-003', 'CL-004']


def test_empty_item_cannot_be_saved(checklist):
    checklist.page.click('[data-act=cl-add][data-gi="0"]')
    checklist.page.click('[data-act=cl-save]')
    assert 'Введите формулировку пункта.' in ' '.join(checklist.toast_texts()) and checklist.count('#cl-input') == 1


def test_item_edit_changes_type_priority_and_requirements(checklist):
    checklist.page.click('[data-act=cl-edit][data-id=CL-002]')
    checklist.page.select_option('#cl-type', 'api')
    checklist.page.select_option('#cl-prio', 'P1_LOW')
    checklist.page.fill('#cl-reqs', 'R-001, R-004')
    checklist.page.click('[data-act=cl-save]')
    assert checklist.state("(({type, priority, requirementIds}) => [type, priority, requirementIds])(S.run.checklist.groups[0].items[1])") == ['api', 'P1_LOW', ['R-001', 'R-004']]


def test_item_refine_with_ai_rewrites_item(checklist):
    checklist.page.click('[data-act=cl-refine][data-id=CL-001]')
    checklist.page.fill('#clr-input', 'Укажи конкретный лимит')
    checklist.page.click('[data-act=cl-refine-go]')
    checklist.page.wait_for_function("() => document.querySelector('#cl-CL-001 .cl-text')?.textContent.startsWith('Исправленный пункт')")
    assert checklist.text('#cl-CL-001 .cl-text') == 'Исправленный пункт с конкретным лимитом 3 запроса'
    assert 'Укажи конкретный лимит' in checklist.model.prompts_of('promptRefineItem')[0]


def test_item_delete(checklist):
    checklist.page.click('[data-act=cl-del][data-id=CL-003]')
    assert [i for i, _ in cl_texts(checklist)] == ['CL-001', 'CL-002', 'CL-004']


def test_group_rename_and_delete_with_confirmation(checklist):
    checklist.page.click('[data-act=cl-gedit][data-gi="1"]')
    checklist.page.fill('#clg-input', 'Сброс по API')
    checklist.page.keyboard.press('Enter')
    assert checklist.state("S.run.checklist.groups.map((g) => g.title)") == ['Форма восстановления', 'Сброс по API']
    checklist.page.click('[data-act=cl-gdel][data-gi="1"]')
    assert checklist.state("S.run.checklist.groups.length") == 2   # пункты в группе — нужно подтверждение
    checklist.page.click('[data-act=cl-gdel][data-gi="1"]')
    assert checklist.state("S.run.checklist.groups.length") == 1


def test_regenerate_checklist_needs_confirmation_and_restarts_numbers(checklist):
    checklist.page.click('[data-act=cl-regen]')
    assert len(checklist.model.calls_of('promptChecklist')) == 1
    checklist.page.click('[data-act=cl-regen]')
    checklist.wait_idle()
    assert len(checklist.model.calls_of('promptChecklist')) == 2
    assert checklist.state("S.run.checklist.groups.flatMap((g) => g.items.map((i) => i.id))") == ['CL-001', 'CL-002', 'CL-003', 'CL-004']


def test_checklist_can_be_made_after_a_cases_only_run(app):
    app.page.click('label:has(#out-checklist)')
    app.generate()
    app.tab('checklist')
    assert 'Чек-листа пока нет' in app.text('#tab-body')
    app.page.click('[data-act=gen-checklist]')
    app.wait_idle()
    assert app.state('S.run.checklist.groups.length') == 2 and app.state('S.run.settings.outputs.checklist') is True


def test_checklist_can_be_started_by_hand(app):
    app.page.click('label:has(#out-checklist)')
    app.generate()
    app.tab('checklist')
    app.page.click('[data-act=cl-new-manual]')
    app.page.fill('#cl-input', 'Первый пункт вручную')
    app.page.click('[data-act=cl-save]')
    assert app.state("S.run.checklist.groups.map((g) => [g.title, g.items.map((i) => i.check)])") == [['Проверки', ['Первый пункт вручную']]]
    assert len(app.model.calls_of('promptChecklist')) == 0
