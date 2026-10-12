"""Черновик: после генерации кейсы лежат в нём, а не в продукте. Ревью, исправление, убрать, очистить, добавить в проект, флажки выбора."""
import pytest

from tests.support import files, model_draft as md, seed

FINDINGS = {'API-001': ['critical', 'minor'], 'UI-001': ['major']}   # у API-001 два замечания, у UI-001 одно, у остальных нет
IDS = 'S.run.cases.map((c) => c.dispId)'
OPEN_CASE_FINDINGS = "S.run.findings.filter((f) => f.kind === 'case' && f.status === 'open')"


@pytest.fixture
def draft(app):
    """Черновик из четырёх кейсов: API-001, API-002, UI-001, E2E-001."""
    return md.make_draft(app, review=md.review(FINDINGS))


@pytest.fixture
def reviewed(draft):
    draft.page.click('[data-act=draft-review]')
    draft.wait_idle()
    return draft


def index_ids(app):
    """Номера кейсов в индексе продукта (база: products/<id>/meta/cases)."""
    doc = app.db.get(f'products/{app.state("S.productId")}/meta/cases') or {}
    return [x['i'] for x in doc.get('items', [])]


def twice(app, sel):
    """Опасные кнопки срабатывают со второго нажатия: первое только меняет подпись."""
    app.page.click(sel)
    app.page.click(sel + '.armed')


# ---------- после генерации ----------
def test_generation_opens_draft_tab(draft):
    assert draft.state('S.tab') == 'draft'
    assert draft.page.get_attribute('#tab-draft', 'aria-selected') == 'true'


def test_run_stage_is_draft(draft):
    assert draft.state('S.run.stage') == 'draft'


def test_head_counts_cases_by_type(draft):
    head = draft.text('.draft-head')
    assert 'Черновик тест-кейсов · 4' in head and 'API 2 · UI 1 · E2E 1' in head


def test_head_says_cases_are_not_in_product_yet(draft):
    assert 'Кейсы ещё не в продукте' in draft.text('.draft-head')


def test_draft_cases_are_not_in_product_index(draft):
    assert draft.state('S.prodIndex.cases.length') == 0
    assert index_ids(draft) == []


def test_draft_does_not_take_product_numbers(draft):
    ctr = draft.state('S.products.find((p) => p.id === S.productId).counters')
    assert [ctr.get(t, 0) for t in ('api', 'ui', 'e2e')] == [0, 0, 0]


def test_next_run_starts_numbering_over_while_first_is_draft(draft, tmp_path):
    """Номера черновика не заняты: второй запуск получает те же номера."""
    first = sorted(draft.state(IDS))
    draft.page.click('#btn-newses')
    draft.upload(files.spec_file(tmp_path))
    draft.generate()
    assert sorted(draft.state(IDS)) == first


def test_draft_is_restored_after_reload(draft):
    md.wait_saved(draft, cases=4, stage='draft')
    draft.reload()
    draft.page.wait_for_function('() => window.__qa.S.run', timeout=15000)
    assert draft.state('[S.run.stage, S.run.cases.length]') == ['draft', 4]


# ---------- ревью ----------
def test_review_is_not_started_yet(draft):
    assert 'ревью ещё не запускалось' in draft.text('.draft-head')
    assert draft.text('[data-act=draft-review]') == 'Запустить ревью'


def test_review_asks_once_per_type(draft):
    draft.page.click('[data-act=draft-review]')
    draft.wait_idle()
    asked = sorted(tuple(md.reviewed_ids(c.prompt)) for c in draft.model.calls_of('promptReviewCases'))
    assert asked == [('API-001', 'API-002'), ('E2E-001',), ('UI-001',)]


def test_review_batches_are_five_cases_at_most(app, tmp_path):
    cases = [seed.case(f'u{i}', 'api', f'API-{i:03d}', f'[BE] POST /x — проверка {i}', ['R-001']) for i in range(1, 13)]
    run = seed.run('run_d', 'Док', cases, [seed.req('R-001', 'Док')], stage='draft')
    app.import_product(seed.write(tmp_path, seed.product_export(runs=[run])))
    app.page.wait_for_selector('#pcase-list .sec', timeout=15000)
    app.call("a.openHistory('run_d', { tab: 'draft' })")
    app.page.wait_for_selector('.draft-head')
    app.page.click('[data-act=draft-review]')
    app.wait_idle()
    assert sorted(len(md.reviewed_ids(p)) for p in app.model.prompts_of('promptReviewCases')) == [2, 5, 5]


def test_review_stays_on_draft_tab(reviewed):
    assert reviewed.state('S.tab') == 'draft'


def test_findings_belong_to_their_cases(reviewed):
    got = reviewed.state("S.run.findings.map((f) => [f.targetId, f.severity, f.status, f.source])")
    assert sorted(got) == [['API-001', 'critical', 'open', 'ai'], ['API-001', 'minor', 'open', 'ai'], ['UI-001', 'major', 'open', 'ai']]


def test_head_summarizes_open_findings(reviewed):
    assert 'открытых замечаний 3: критичных 1, существенных 1, мелких 1' in reviewed.text('.draft-head')


def test_case_row_shows_its_findings(reviewed):
    row = reviewed.text('.draft-case:has(.mono:text-is("API-001"))')
    assert 'замечаний 2' in row and 'Замечание 1 к API-001' in row and 'Замечание 2 к API-001' in row


def test_clean_cases_are_marked(reviewed):
    assert reviewed.count('.draft-case .chip.ok:text-is("без замечаний")') == 2


def test_review_button_changes_to_repeat(reviewed):
    assert reviewed.text('[data-act=draft-review]') == 'Повторить ревью'


def test_findings_of_missing_template_fields_are_found_without_model(app):
    """Автоматическая проверка: если в кейсе нет полей шаблона, замечание появляется без запроса к модели."""
    app.page.click('label:has(#out-checklist)')
    app.generate()
    app.model.reset()
    app.page.click('[data-act=draft-review]')
    app.wait_idle()
    auto = app.state("S.run.findings.filter((f) => f.source === 'auto' && f.category === 'Шаблон').length")
    assert auto == 4 and 'Нет полей шаблона' in app.text('.draft-list')


def test_second_review_checks_only_changed_cases(reviewed):
    """«Повторно проверяются только изменённые кейсы»: исправленный кейс уходит на ревью, остальные сохраняют замечания."""
    reviewed.page.click('.draft-case:has(.mono:text-is("API-001")) [data-act=draft-fix]')
    reviewed.wait_idle()
    reviewed.model.reset()
    reviewed.page.click('[data-act=draft-review]')
    reviewed.wait_idle()
    assert [md.reviewed_ids(c.prompt) for c in reviewed.model.calls_of('promptReviewCases')] == [['API-001']]
    assert reviewed.state("S.run.findings.filter((f) => f.targetId === 'UI-001' && f.status === 'open').length") == 1


# ---------- исправить ----------
def test_fix_one_sends_only_this_cases_findings(reviewed):
    reviewed.model.reset()
    reviewed.page.click('.draft-case:has(.mono:text-is("UI-001")) [data-act=draft-fix]')
    reviewed.wait_idle()
    calls = reviewed.model.calls_of('promptRefine')
    assert len(calls) == 1 and 'Замечание 1 к UI-001' in calls[0].prompt and 'API-001' not in calls[0].prompt


def test_fix_one_closes_all_findings_of_that_case(reviewed):
    reviewed.page.click('.draft-case:has(.mono:text-is("API-001")) [data-act=draft-fix]')
    reviewed.wait_idle()
    st = reviewed.state("S.run.findings.map((f) => [f.targetId, f.status])")
    assert sorted(st) == [['API-001', 'fixed'], ['API-001', 'fixed'], ['UI-001', 'open']]


def test_fix_one_rewrites_only_that_case(reviewed):
    before = reviewed.state('S.run.cases.map((c) => a.pickTitleText(c.testCase))')
    reviewed.page.click('.draft-case:has(.mono:text-is("UI-001")) [data-act=draft-fix]')
    reviewed.wait_idle()
    after = reviewed.state('S.run.cases.map((c) => a.pickTitleText(c.testCase))')
    changed = [i for i, (x, y) in enumerate(zip(before, after)) if x != y]
    assert changed == [2] and 'Доработанный кейс' in after[2]


def test_fixed_case_keeps_its_number(reviewed):
    reviewed.page.click('.draft-case:has(.mono:text-is("UI-001")) [data-act=draft-fix]')
    reviewed.wait_idle()
    assert reviewed.state(IDS).count('UI-001') == 1 and reviewed.state("S.run.cases.find((c) => c.dispId === 'UI-001').testCase.id") == 'UI-001'


def test_fix_all_closes_every_open_finding(reviewed):
    assert 'Исправить все (3)' in reviewed.text('[data-act=draft-fixall]')
    reviewed.page.click('[data-act=draft-fixall]')
    reviewed.wait_idle()
    assert reviewed.state(OPEN_CASE_FINDINGS + '.length') == 0
    assert len(reviewed.model.calls_of('promptRefine')) == 2   # по запросу на кейс, а не на замечание


def test_fix_all_is_disabled_without_findings(draft):
    assert draft.page.is_disabled('[data-act=draft-fixall]')


def test_fix_buttons_vanish_after_fixing(reviewed):
    reviewed.page.click('[data-act=draft-fixall]')
    reviewed.wait_idle()
    assert reviewed.count('[data-act=draft-fix]') == 0 and reviewed.page.is_disabled('[data-act=draft-fixall]')


# ---------- убрать, очистить ----------
def test_drop_needs_confirmation(draft):
    draft.page.click('.draft-case:has(.mono:text-is("E2E-001")) [data-act=draft-drop]')
    assert draft.state('S.run.cases.length') == 4
    assert draft.text('[data-act=draft-drop].armed') == 'Убрать?'


def test_drop_removes_the_case(draft):
    twice(draft, '.draft-case:has(.mono:text-is("E2E-001")) [data-act=draft-drop]')
    assert sorted(draft.state(IDS)) == ['API-001', 'API-002', 'UI-001']
    assert 'Черновик тест-кейсов · 3' in draft.text('.draft-head')


def test_drop_removes_findings_of_the_case(reviewed):
    twice(reviewed, '.draft-case:has(.mono:text-is("API-001")) [data-act=draft-drop]')
    assert reviewed.state("S.run.findings.map((f) => f.targetId)") == ['UI-001']


def test_clear_needs_confirmation(draft):
    draft.page.click('[data-act=draft-clear]')
    assert draft.state('S.run.cases.length') == 4 and draft.text('[data-act=draft-clear].armed') == 'Удалить все кейсы черновика?'


def test_clear_empties_the_draft(draft):
    twice(draft, '[data-act=draft-clear]')
    assert draft.state('S.run.cases.length') == 0
    assert 'Черновик пуст' in draft.text('#tab-body')


def test_clear_frees_case_numbers(draft):
    twice(draft, '[data-act=draft-clear]')
    assert draft.state('JSON.stringify(S.run.counters) === JSON.stringify(S.run.baseCounters)') is True


def test_clear_removes_case_findings(reviewed):
    twice(reviewed, '[data-act=draft-clear]')
    assert reviewed.state("S.run.findings.filter((f) => f.kind === 'case').length") == 0


# ---------- открыть ----------
def test_open_shows_the_case_in_cases_tab(draft):
    draft.page.click('.draft-case:has(.mono:text-is("UI-001")) [data-act=draft-open]')
    draft.page.wait_for_selector('.case-b')
    assert draft.state('S.tab') == 'cases' and draft.count('.case-b') == 1
    assert 'UI-001' in draft.text('article.case:has(.case-b)')


# ---------- добавить в проект ----------
def test_add_moves_cases_to_product_index(draft):
    md.add_to_project(draft)
    assert sorted(index_ids(draft)) == ['API-001', 'API-002', 'E2E-001', 'UI-001']


def test_add_changes_stage_and_head(draft):
    md.add_to_project(draft)
    head = draft.text('.draft-head')
    assert draft.state('S.run.stage') == 'added' and 'Тест-кейсы запуска · 4' in head and 'в проекте' in head and 'Добавлены в проект' in head


def test_add_hides_drop_and_clear(draft):
    md.add_to_project(draft)
    assert draft.count('[data-act=draft-drop], [data-act=draft-clear], [data-act=draft-add]') == 0


def test_add_takes_product_numbers(draft):
    md.add_to_project(draft)
    draft.page.wait_for_function("() => window.__qa.S.products.find((p) => p.id === window.__qa.S.productId).counters.api === 2")
    ctr = draft.state('S.products.find((p) => p.id === S.productId).counters')
    assert [ctr[t] for t in ('api', 'ui', 'e2e')] == [2, 1, 1]


def test_product_card_counts_cases_only_after_add(draft):
    assert '0 тест-кейсов' in draft.text('#ps-sub')
    md.add_to_project(draft)
    draft.page.wait_for_function("() => /4 тест-кейса/.test(document.querySelector('#ps-sub').textContent)", timeout=15000)


def test_add_with_critical_finding_asks_again(reviewed):
    reviewed.page.click('[data-act=draft-add]')
    assert reviewed.state('S.run.stage') == 'draft'
    assert reviewed.text('[data-act=draft-add].armed') == 'Есть критичные замечания (1) — всё равно добавить?'


def test_add_without_critical_findings_needs_no_confirmation(app):
    md.make_draft(app, review=md.review({'UI-001': ['major']}))
    app.page.click('[data-act=draft-review]')
    app.wait_idle()
    app.page.click('[data-act=draft-add]')
    app.page.wait_for_function("() => window.__qa.S.run.stage === 'added'", timeout=15000)


def test_add_gives_next_free_numbers_when_taken_meanwhile(draft):
    """Пока кейсы лежали в черновике, номер занял другой запуск: при добавлении кейс получает следующий свободный."""
    first = draft.state('S.run.cases[0].dispId')
    draft.call("S.prodIndex.cases.push({ r: 'run_other', i: arg, t: S.run.cases[0].type, n: 'чужой' })", first)
    md.add_to_project(draft)
    ids = draft.state(IDS)
    assert first not in ids and len(set(ids)) == 4
    assert draft.state('S.run.cases[0].testCase.id') == draft.state('S.run.cases[0].dispId') != first


def test_renumbered_case_keeps_its_findings(draft):
    draft.page.click('[data-act=draft-review]')
    draft.wait_idle()
    draft.call("S.prodIndex.cases.push({ r: 'run_other', i: 'API-001', t: 'api', n: 'чужой' })")
    md.add_to_project(draft)
    new_id = draft.state('S.run.cases[0].dispId')
    assert new_id != 'API-001'
    assert sorted(draft.state("S.run.findings.filter((f) => f.severity !== 'major').map((f) => f.targetId)")) == [new_id, new_id]


def test_run_without_stage_is_already_in_project(app, tmp_path):
    """Запуски, сохранённые до появления черновика, считаются добавленными в проект."""
    old = seed.run('run_old', 'Док', [seed.case('u1', 'ui', 'UI-001', '[FE] Вход', ['R-001'])], [seed.req('R-001', 'Док')])
    data = seed.product_export(runs=[old])
    del data['runs'][0]['meta']['stage']
    app.import_product(seed.write(tmp_path, data))
    app.page.wait_for_selector('#pcase-list .sec', timeout=15000)
    app.call("a.openHistory('run_old', { tab: 'draft' })")
    app.page.wait_for_selector('.draft-head')
    assert app.state('S.run.stage') == 'added' and 'в проекте' in app.text('.draft-head')


# ---------- флажки выбора ----------
def selbar(app):
    return app.text('.sel-bar').replace('\n', ' ')


def test_every_draft_case_has_a_checkbox(draft):
    assert draft.count('.draft-case .case-sel') == 4 and 'Выбрать все (4)' in selbar(draft)


def test_select_one_case(draft):
    draft.page.check('.draft-case:has(.mono:text-is("UI-001")) .case-sel')
    assert 'Выбрано 1 из 4' in selbar(draft) and 'Удалить выбранные (1)' in selbar(draft)


def test_select_all_checkbox(draft):
    draft.page.check('.sel-all-cb')
    assert 'Выбрано 4 из 4' in selbar(draft) and draft.state('S.caseSel.size') == 4


def test_unselect_all_checkbox(draft):
    draft.page.check('.sel-all-cb')
    draft.page.uncheck('.sel-all-cb')
    assert draft.state('S.caseSel.size') == 0 and 'Выбрать все (4)' in selbar(draft)


def test_clear_selection_link(draft):
    draft.page.check('.draft-case:has(.mono:text-is("UI-001")) .case-sel')
    draft.page.click('[data-act=sel-none]')
    assert draft.state('S.caseSel.size') == 0 and draft.count('.case-sel:checked') == 0


def test_delete_selected_needs_confirmation(draft):
    draft.page.check('.draft-case:has(.mono:text-is("UI-001")) .case-sel')
    draft.page.click('[data-act=sel-del]')
    assert draft.state('S.run.cases.length') == 4 and draft.text('[data-act=sel-del].armed') == 'Удалить выбранные (1)?'


def test_delete_selected_removes_only_them(draft):
    draft.page.check('.draft-case:has(.mono:text-is("UI-001")) .case-sel')
    draft.page.check('.draft-case:has(.mono:text-is("E2E-001")) .case-sel')
    twice(draft, '[data-act=sel-del]')
    assert sorted(draft.state(IDS)) == ['API-001', 'API-002']
    assert draft.state('S.caseSel.size') == 0


def test_deleted_from_draft_do_not_reach_product(draft):
    draft.page.check('.draft-case:has(.mono:text-is("UI-001")) .case-sel')
    twice(draft, '[data-act=sel-del]')
    md.add_to_project(draft)
    assert sorted(index_ids(draft)) == ['API-001', 'API-002', 'E2E-001']


def test_delete_selected_removes_their_findings(reviewed):
    reviewed.page.check('.draft-case:has(.mono:text-is("API-001")) .case-sel')
    twice(reviewed, '[data-act=sel-del]')
    assert reviewed.state("S.run.findings.map((f) => f.targetId)") == ['UI-001']


@pytest.fixture
def added(draft):
    """Кейсы уже в проекте: открыта вкладка «Тест-кейсы» запуска."""
    md.add_to_project(draft)
    draft.page.click('#tab-cases')
    draft.page.wait_for_selector('#case-list .case, #pcase-list .case')
    if draft.count('[data-act=cases-scope][data-s=run]'):
        draft.page.click('[data-act=cases-scope][data-s=run]')
    draft.page.wait_for_selector('#case-list .case')
    return draft


def test_cases_tab_has_checkboxes_and_select_all(added):
    assert added.count('#case-list .case-sel') == 4 and 'Выбрать все (4)' in added.text('#case-selbar')


def test_select_all_takes_only_filtered_cases(added):
    added.page.click('[data-act=ftype][data-t=api]')
    added.page.check('#case-selbar .sel-all-cb')
    assert 'Выбрано 2 из 2' in added.text('#case-selbar') and added.count('.case-b') == 0
    assert sorted(added.state("[...S.caseSel].map((u) => S.run.cases.find((c) => c.uid === u).dispId)")) == ['API-001', 'API-002']


def test_checkbox_click_does_not_expand_the_case(added):
    added.page.click('#case-list .case-sel >> nth=0')
    assert added.count('.case-b') == 0 and added.state('S.caseSel.size') == 1


def test_clear_selection_in_cases_tab(added):
    added.page.check('#case-selbar .sel-all-cb')
    added.page.click('#case-selbar [data-act=sel-none]')
    assert added.state('S.caseSel.size') == 0 and 'Выбрать все (4)' in added.text('#case-selbar')


def test_delete_filtered_cases_removes_them_from_run_and_product(added):
    added.page.click('[data-act=ftype][data-t=api]')
    added.page.check('#case-selbar .sel-all-cb')
    twice(added, '#case-selbar [data-act=sel-del]')
    added.page.wait_for_function("() => window.__qa.S.prodIndex.cases.length === 2", timeout=15000)
    assert sorted(added.state(IDS)) == ['E2E-001', 'UI-001']
    assert sorted(i['i'] for i in added.state('S.prodIndex.cases')) == ['E2E-001', 'UI-001']


def test_delete_from_added_run_says_it_leaves_product(added):
    added.page.check('#case-list .case-sel >> nth=0')
    twice(added, '#case-selbar [data-act=sel-del]')
    assert any('в продукте его больше нет' in t for t in added.toast_texts())
