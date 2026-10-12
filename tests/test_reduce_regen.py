"""«Перегенерировать по правилам» и «Сократить количество тестов»: кнопки под «Сгенерировать», видны только у черновика с кейсами.
Перегенерация не трогает базу знаний и паспорт продукта; сокращение получает текст документации и сохраняет покрытие требований."""
import re

import pytest

from tests.support import files, model_draft as md, seed
from tests.support.model import ModelError

IDS = 'S.run.cases.map((c) => c.dispId)'
COVERED = 'new Set(S.run.cases.flatMap((c) => c.requirementIds))'
# мок-модель даёт четыре кейса: API-001 (R-002), API-002 (R-004), UI-001 (R-001), E2E-001 (R-003, R-002).
# Чтобы покрыть все четыре требования, нужно минимум три кейса: E2E-001, API-002 и UI-001
MIN_KEEP = ['E2E-001', 'API-002', 'UI-001']


@pytest.fixture
def draft(app):
    return md.make_draft(app)


def hidden(app, sel):
    return app.page.evaluate('(s) => document.querySelector(s).hidden', sel)


def regen(app):
    """Кнопка заменяет кейсы со второго нажатия."""
    app.page.click('#btn-regen')
    app.page.click('#btn-regen.armed')
    app.wait_idle()


def open_reduce(app, n=None):
    app.page.click('#btn-reduce')
    if n is not None:
        app.page.fill('#reduce-n', str(n))


def reduce_go(app):
    app.page.click('#reduce-go')
    app.page.wait_for_function("() => !document.querySelector('#reduce-go').disabled", timeout=30000)


def drop_cases(app, *ids):
    for cid in ids:
        sel = f'.draft-case:has(.mono:text-is("{cid}")) [data-act=draft-drop]'
        app.page.click(sel)
        app.page.click(sel + '.armed')


# ---------- когда видны кнопки ----------
def test_buttons_are_hidden_before_the_first_run(app):
    assert hidden(app, '#btn-regen') and hidden(app, '#btn-reduce')


def test_buttons_appear_for_a_draft(draft):
    assert not hidden(draft, '#btn-regen') and not hidden(draft, '#btn-reduce')
    assert draft.text('#btn-regen') == 'Перегенерировать по правилам' and draft.text('#btn-reduce') == 'Сократить количество тестов'
    assert not draft.page.is_disabled('#btn-regen') and not draft.page.is_disabled('#btn-reduce')


def test_buttons_are_hidden_while_generation_runs(draft):
    draft.js('window.__sampleDelay = 600')   # запросы идут медленно, чтобы застать запуск
    draft.page.click('#btn-regen')
    draft.page.click('#btn-regen.armed')
    draft.page.wait_for_function('() => window.__qa.S.running')
    assert hidden(draft, '#btn-regen') and hidden(draft, '#btn-reduce')
    draft.js('window.__sampleDelay = 15')
    draft.wait_idle()
    assert not hidden(draft, '#btn-regen') and not hidden(draft, '#btn-reduce')


def test_buttons_are_hidden_when_added_run_is_opened_again(draft):
    md.add_to_project(draft)
    md.wait_saved(draft, stage='added')
    draft.reload()
    draft.page.wait_for_function('() => window.__qa.S.run', timeout=15000)
    assert draft.state('S.run.stage') == 'added' and hidden(draft, '#btn-regen') and hidden(draft, '#btn-reduce')


@pytest.mark.xfail(strict=True, reason='БАГ: после «Добавить в проект» кнопки «Перегенерировать по правилам» и «Сократить количество тестов» остаются на экране (до следующей перерисовки), хотя кейсы уже не черновик; нажатие ничего не делает')
def test_buttons_are_hidden_right_after_adding_to_project(draft):
    md.add_to_project(draft)
    assert hidden(draft, '#btn-regen') and hidden(draft, '#btn-reduce')


@pytest.mark.xfail(strict=True, reason='БАГ: после «Очистить» кнопки «Перегенерировать по правилам» и «Сократить количество тестов» остаются на экране при пустом черновике; нажатие ничего не делает')
def test_buttons_are_hidden_right_after_clearing_draft(draft):
    draft.page.click('[data-act=draft-clear]')
    draft.page.click('[data-act=draft-clear].armed')
    assert draft.state('S.run.cases.length') == 0
    assert hidden(draft, '#btn-regen') and hidden(draft, '#btn-reduce')


def test_reduce_is_hidden_for_one_case_after_reload(draft):
    drop_cases(draft, 'API-001', 'API-002', 'UI-001')
    md.wait_saved(draft, cases=1)
    draft.reload()
    draft.page.wait_for_function('() => window.__qa.S.run', timeout=15000)
    assert draft.state('S.run.cases.length') == 1 and hidden(draft, '#btn-reduce') and not hidden(draft, '#btn-regen')


def test_reduce_is_visible_for_two_cases(draft):
    drop_cases(draft, 'API-001', 'API-002')
    assert draft.state('S.run.cases.length') == 2 and not hidden(draft, '#btn-reduce')


@pytest.mark.xfail(strict=True, reason='БАГ: после «Убрать» последних кейсов до одного кнопка «Сократить количество тестов» остаётся на экране (сократить можно от двух кейсов); нажатие ничего не делает')
def test_reduce_is_hidden_right_after_dropping_to_one_case(draft):
    drop_cases(draft, 'API-001', 'API-002', 'UI-001')
    assert draft.state('S.run.cases.length') == 1 and hidden(draft, '#btn-reduce')


def test_regen_is_disabled_when_documents_are_deleted_from_product(draft):
    draft.mode('help')
    draft.page.click('[data-doc-act=remove]')
    draft.page.click('[data-doc-act=remove].armed')
    draft.mode('generate')
    assert draft.state('S.docs.length') == 0 and draft.page.is_disabled('#btn-regen')


# ---------- перегенерация ----------
def test_regen_asks_for_confirmation(draft):
    draft.page.click('#btn-regen')
    assert draft.text('#btn-regen') == 'Заменить кейсы черновика?' and not draft.state('S.running')
    assert draft.state('S.run.cases.length') == 4


def test_regen_starts_after_second_click(draft):
    draft.js('window.__sampleDelay = 300')
    draft.page.click('#btn-regen')
    draft.page.click('#btn-regen.armed')
    draft.page.wait_for_function('() => window.__qa.S.running')
    assert draft.state('S.run.cases.length') == 0   # старые кейсы удалены сразу
    draft.js('window.__sampleDelay = 15')
    draft.wait_idle()


def test_regen_replaces_cases_in_the_same_run(draft):
    before = draft.state('[S.run.id, S.run.cases.map((c) => c.uid)]')
    regen(draft)
    after = draft.state('[S.run.id, S.run.cases.map((c) => c.uid), S.run.status, S.run.stage]')
    assert after[0] == before[0] and after[2:] == ['done', 'draft']
    assert len(after[1]) == 4 and not set(after[1]) & set(before[1])


def test_regen_restarts_case_numbers(draft):
    before = sorted(draft.state(IDS))
    regen(draft)
    assert sorted(draft.state(IDS)) == before


def test_regen_shows_draft_when_done(draft):
    regen(draft)
    assert draft.state('S.tab') == 'draft'


def test_regen_does_not_analyze_documents_again(draft):
    draft.model.reset()
    regen(draft)
    kinds = {c.kind for c in draft.model.calls}
    assert 'promptAnalyze' not in kinds and {'promptPlan', 'promptGenerate'} <= kinds


def test_regen_keeps_requirements(draft):
    before = draft.state('S.run.requirements.map((r) => r.id + r.title)')
    regen(draft)
    assert draft.state('S.run.requirements.map((r) => r.id + r.title)') == before


def test_regen_keeps_checklist(app):
    app.generate()
    before = app.state('S.run.checklist.groups.flatMap((g) => g.items.map((i) => i.id + i.check))')
    assert before
    app.model.reset()
    regen(app)
    assert app.state('S.run.checklist.groups.flatMap((g) => g.items.map((i) => i.id + i.check))') == before
    assert not app.model.calls_of('promptChecklist')


def test_regen_uses_current_rules(draft):
    draft.page.fill('#cfg-rules', 'Платёжный шлюз ПЛАТИ-777 не тестируем')
    draft.model.reset()
    regen(draft)
    prompts = draft.model.prompts_of('promptPlan', 'promptGenerate')
    assert prompts and all('ПЛАТИ-777' in p for p in prompts)


def test_old_rules_are_not_used_by_next_regen(draft):
    draft.page.fill('#cfg-rules', 'Платёжный шлюз ПЛАТИ-777 не тестируем')
    regen(draft)
    draft.page.fill('#cfg-rules', '')
    draft.model.reset()
    regen(draft)
    assert not any('ПЛАТИ-777' in p for p in draft.model.prompts_of('promptPlan', 'promptGenerate'))


def test_regen_removes_findings_of_old_cases(draft):
    draft.model.on('promptReviewCases', md.review({'API-001': ['critical']}))
    draft.page.click('[data-act=draft-review]')
    draft.wait_idle()
    regen(draft)
    assert draft.state("S.run.findings.filter((f) => f.kind === 'case').length") == 0


@pytest.mark.xfail(strict=True, reason='БАГ: после перегенерации в шапке черновика написано «Ревью: замечаний нет», хотя новые кейсы ещё не проверялись (надо «ревью ещё не запускалось»)')
def test_regenerated_cases_are_not_shown_as_reviewed(draft):
    draft.model.on('promptReviewCases', md.review({'API-001': ['critical']}))
    draft.page.click('[data-act=draft-review]')
    draft.wait_idle()
    regen(draft)
    assert 'ревью ещё не запускалось' in draft.text('.draft-head')


# ---------- перегенерация и знания о продукте ----------
@pytest.fixture
def knowledge(make_app, tmp_path):
    """Продукт «Магазин» с паспортом и разделом базы знаний; черновик получен обычной генерацией (знания в запросах есть)."""
    app = make_app(settings={'kbAuto': False})
    data = seed.product_export(name='Магазин')
    data['product']['passport'] = {'text': '## Роли и пользователи\n- Оператор поддержки видит заявки клиентов\n## Бизнес-правила и ограничения\n- Лимит запросов на сброс пароля: 3 за 15 минут'}
    block = {'id': 'kb1', 'title': 'Восстановление пароля', 'summary': 'Сброс пароля по ссылке из письма', 'updatedAt': 1700000000000}
    data['kb'] = {'index': {'blocks': [block], 'docs': {}},
                  'blocks': [{**block, 'synth': '### Бизнес-правила и ограничения\n- Лимит запросов на сброс пароля: 3 за 15 минут (ТЗ)\n- Ссылка действует 30 минут',
                              'synthAt': 1700000000000, 'synthV': 99, 'parts': [], 'conflicts': [], 'links': []}]}
    app.import_product(seed.write(tmp_path, data))
    app.page.wait_for_function('() => window.__qa.S.products.length === 2 && window.__qa.S.kb.index.blocks.length === 1', timeout=20000)
    app.upload(files.spec_file(tmp_path))
    md.make_draft(app)
    return app


def stored_knowledge(app):
    pid = app.state('S.productId')
    return {p: app.db.get(p) for p in (f'products/{pid}/meta/passport', f'products/{pid}/meta/kb', f'products/{pid}/kb/kb1')}


def test_first_generation_uses_passport_and_knowledge_base(knowledge):
    """Контроль: в обычной генерации знания в запросах есть."""
    prompts = knowledge.model.prompts_of('promptPlan', 'promptGenerate')
    assert prompts and all('Знания о продукте' in p and 'База знаний продукта' in p for p in prompts)


def test_regen_does_not_put_knowledge_into_prompts(knowledge):
    knowledge.model.reset()
    regen(knowledge)
    prompts = knowledge.model.prompts_of('promptPlan', 'promptGenerate')
    assert prompts and not any('Знания о продукте' in p or 'База знаний продукта' in p for p in prompts)


def test_regen_does_not_change_passport_and_knowledge_base(knowledge):
    before = stored_knowledge(knowledge)
    assert all(before.values())
    knowledge.model.reset()
    regen(knowledge)
    assert stored_knowledge(knowledge) == before
    assert not knowledge.model.calls_of('promptPassportFull', 'promptPassportDelta', 'promptKbSplit', 'promptKbSynth')


# ---------- отбор кейсов при сокращении (чистая функция) ----------
CASES = """[
  { dispId: 'A', requirementIds: ['R1', 'R2'], testCase: { priority: 'High' }, type: 'api' },
  { dispId: 'B', requirementIds: ['R1'], testCase: { priority: 'Medium' }, type: 'api' },
  { dispId: 'C', requirementIds: ['R2'], testCase: { priority: 'Low' }, type: 'api' },
  { dispId: 'D', requirementIds: ['R3'], testCase: { priority: 'High' }, type: 'api' },
  { dispId: 'E', requirementIds: ['R3'], testCase: { priority: 'Low' }, type: 'api' }]"""


def pick(app, keep, target):
    return app.call(f"""(() => {{
      const cases = {CASES};
      const r = a.reduceSelect(cases, arg.keep, arg.target);
      const cov = new Set(cases.filter((c) => (r.keep || []).includes(c.dispId)).flatMap((c) => c.requirementIds));
      return {{ warn: !!r.warn, error: r.error || null, keep: r.keep || [], covered: cov.size, min: r.min ?? null, uncovered: r.uncovered ?? null }};
    }})()""", {'keep': keep, 'target': target})


def test_select_keeps_models_choice_when_it_covers_everything(app):
    r = pick(app, ['A', 'D', 'B'], 3)
    assert not r['warn'] and sorted(r['keep']) == ['A', 'B', 'D']


def test_select_adds_to_models_choice_up_to_target(app):
    r = pick(app, ['A'], 3)
    assert not r['warn'] and len(r['keep']) == 3 and r['covered'] == 3 and 'A' in r['keep']


def test_select_trims_models_choice_down_to_target(app):
    r = pick(app, ['A', 'B', 'C', 'D', 'E'], 3)
    assert not r['warn'] and len(r['keep']) == 3 and r['covered'] == 3


def test_select_without_models_choice(app):
    r = pick(app, [], 2)
    assert not r['warn'] and sorted(r['keep']) == ['A', 'D'] and r['covered'] == 3


def test_select_repairs_models_choice_that_loses_requirements(app):
    r = pick(app, ['B', 'C'], 2)
    assert not r['warn'] and len(r['keep']) == 2 and r['covered'] == 3


def test_select_ignores_unknown_ids(app):
    r = pick(app, ['нет-такого', 'A'], 2)
    assert not r['warn'] and len(r['keep']) == 2 and r['covered'] == 3 and 'нет-такого' not in r['keep']


def test_select_warns_when_coverage_is_impossible(app):
    r = pick(app, [], 1)
    assert r['warn'] and r['min'] == 2 and r['uncovered'] == 1 and len(r['keep']) == 1


def test_select_prefers_important_cases_when_equal(app):
    """Из двух кейсов, закрывающих R3, оставляется тот, у которого приоритет выше."""
    r = pick(app, [], 2)
    assert 'D' in r['keep'] and 'E' not in r['keep']


# ---------- форма «Сократить» ----------
def test_form_is_closed_until_button_is_pressed(draft):
    assert hidden(draft, '#reduce-form')


def test_form_suggests_half_of_cases(draft):
    open_reduce(draft)
    assert not hidden(draft, '#reduce-form')
    assert draft.state("[document.querySelector('#reduce-n').value, document.querySelector('#reduce-n').max]") == ['2', '3']


def test_form_hint_tells_the_range(draft):
    open_reduce(draft)
    assert draft.text('#reduce-hint') == 'В черновике 4 кейса. Оставить можно от 1 до 3; покрытие требований сохранится.'


@pytest.mark.parametrize('value', ['4', '9', '0', '-1', '', '2.5'])
def test_wrong_number_is_rejected_without_model_request(draft, value):
    open_reduce(draft, value)
    draft.page.click('#reduce-go')
    assert draft.text('#reduce-hint') == 'Введите целое число от 1 до 3.' and 'err' in draft.page.get_attribute('#reduce-hint', 'class')
    assert not draft.model.calls_of('promptReduceCases') and draft.state('S.run.cases.length') == 4


def test_cancel_closes_the_form(draft):
    open_reduce(draft)
    draft.page.click('#reduce-cancel')
    assert hidden(draft, '#reduce-form') and draft.state('S.run.cases.length') == 4


def test_enter_in_the_field_starts_reduction(draft):
    draft.model.on('promptReduceCases', md.reduce_keep(MIN_KEEP))
    open_reduce(draft, 3)
    draft.page.press('#reduce-n', 'Enter')
    draft.page.wait_for_function('() => window.__qa.S.run.cases.length === 3')


def test_two_cases_can_be_reduced_to_one(draft):
    draft.page.click('#tab-draft')
    drop_cases(draft, 'API-001', 'API-002')
    open_reduce(draft)
    assert draft.state("[document.querySelector('#reduce-n').value, document.querySelector('#reduce-n').max]") == ['1', '1']


@pytest.mark.xfail(strict=True, reason='БАГ: в черновике актуализации с устаревшим кейсом подсказка формы говорит «Оставить можно от 1 до 3» (считает и устаревший), а число 3 отвергается сообщением «Оставить можно от 1 до 2»')
def test_form_hint_matches_validation_with_obsolete_cases(app, tmp_path):
    cases = [seed.case(f'u{i}', 'ui', f'UI-00{i}', f'[FE] Кейс {i}', [f'R-00{i}']) for i in (1, 2, 3)]
    cases.append(seed.case('u4', 'ui', 'UI-004', '[FE] Устаревший', ['R-004'], status='obsolete'))
    run = seed.run('run_u', 'Док', cases, [seed.req(f'R-00{i}', 'Док') for i in (1, 2, 3, 4)], stage='draft')
    app.import_product(seed.write(tmp_path, seed.product_export(runs=[run])))
    app.page.wait_for_selector('#pcase-list .sec', timeout=15000)
    app.call("a.openHistory('run_u', { tab: 'draft' })")
    app.page.wait_for_selector('.draft-head')
    open_reduce(app)
    biggest = re.search(r'от 1 до (\d+)', app.text('#reduce-hint')).group(1)
    app.page.fill('#reduce-n', biggest)
    reduce_go(app)
    assert 'err' not in app.page.get_attribute('#reduce-hint', 'class'), f'число {biggest} из подсказки отвергнуто: ' + app.text('#reduce-hint')


# ---------- сокращение с сохранением покрытия ----------
def reduce_to(app, n):
    open_reduce(app, n)
    reduce_go(app)


def test_reduce_keeps_models_choice(draft):
    draft.model.on('promptReduceCases', md.reduce_keep(MIN_KEEP))
    reduce_to(draft, 3)
    assert sorted(draft.state(IDS)) == sorted(MIN_KEEP)


def test_reduce_closes_form_and_reports(draft):
    draft.model.on('promptReduceCases', md.reduce_keep(MIN_KEEP))
    reduce_to(draft, 3)
    assert hidden(draft, '#reduce-form')
    assert 'Осталось 3 теста, убрано 1. Покрытие требований сохранено.' in draft.toast_texts()


def test_reduce_shows_new_count_in_draft(draft):
    draft.model.on('promptReduceCases', md.reduce_keep(MIN_KEEP))
    reduce_to(draft, 3)
    assert 'Черновик тест-кейсов · 3' in draft.text('.draft-head')


def test_reduce_is_one_request(draft):
    draft.model.on('promptReduceCases', md.reduce_keep(MIN_KEEP))
    reduce_to(draft, 3)
    assert len(draft.model.calls_of('promptReduceCases')) == 1


@pytest.mark.parametrize('answer', [
    {},                                              # модель не вернула список
    {'keep': ['НЕТ-1', 'НЕТ-2', 'НЕТ-3']},           # выдумала номера
    {'keep': ['API-001', 'API-002', 'UI-001']},      # потеряла требование R-003
    {'keep': ['API-001', 'API-002', 'UI-001', 'E2E-001']},   # не сократила
    {'keep': ['E2E-001']},                           # оставила меньше, чем просили
], ids=['пусто', 'выдуманные', 'теряет-требование', 'не-сократила', 'слишком-мало'])
def test_reduce_repairs_bad_model_answers(draft, answer):
    draft.model.on('promptReduceCases', answer)
    reduce_to(draft, 3)
    assert draft.state('S.run.cases.length') == 3
    assert draft.state(COVERED + '.size') == 4


def test_reduce_drops_findings_of_removed_cases(draft):
    draft.model.on('promptReviewCases', md.review({'API-001': ['critical'], 'UI-001': ['major']}))
    draft.page.click('[data-act=draft-review]')
    draft.wait_idle()
    draft.model.on('promptReduceCases', md.reduce_keep(MIN_KEEP))
    reduce_to(draft, 3)
    assert draft.state("S.run.findings.map((f) => f.targetId)") == ['UI-001']


def test_reduced_draft_is_saved(draft):
    draft.model.on('promptReduceCases', md.reduce_keep(MIN_KEEP))
    reduce_to(draft, 3)
    md.wait_saved(draft, cases=3)
    draft.reload()
    draft.page.wait_for_function('() => window.__qa.S.run', timeout=15000)
    assert draft.state('[S.run.stage, S.run.cases.length]') == ['draft', 3]


def test_reduce_keeps_the_draft_in_draft(draft):
    draft.model.on('promptReduceCases', md.reduce_keep(MIN_KEEP))
    reduce_to(draft, 3)
    assert draft.state('S.run.stage') == 'draft' and draft.state('S.prodIndex.cases.length') == 0


# ---------- предупреждение, когда покрытие не сохранить ----------
def warn_at_two(app):
    app.model.on('promptReduceCases', md.reduce_keep(['E2E-001', 'API-002']))
    reduce_to(app, 2)


def test_warning_when_coverage_cannot_be_kept(draft):
    warn_at_two(draft)
    assert draft.text('#reduce-hint') == 'При 2 тестах 1 требование останется без проверок: для полного покрытия нужно минимум 3 теста. Сократить всё равно?'
    assert 'warn-hint' in draft.page.get_attribute('#reduce-hint', 'class')


def test_warning_does_not_remove_cases(draft):
    warn_at_two(draft)
    assert draft.state('S.run.cases.length') == 4 and not hidden(draft, '#reduce-form')


def test_warning_changes_button_label(draft):
    warn_at_two(draft)
    assert draft.text('#reduce-go') == 'Сократить всё равно'


def test_confirmed_reduction_removes_cases_without_new_request(draft):
    warn_at_two(draft)
    reduce_go(draft)
    assert draft.state('S.run.cases.length') == 2 and len(draft.model.calls_of('promptReduceCases')) == 1


def test_confirmed_reduction_keeps_the_most_coverage(draft):
    warn_at_two(draft)
    reduce_go(draft)
    assert 'E2E-001' in draft.state(IDS) and draft.state(COVERED + '.size') == 3


def test_confirmed_reduction_reports_without_coverage_note(draft):
    warn_at_two(draft)
    reduce_go(draft)
    assert 'Осталось 2 теста, убрано 2.' in draft.toast_texts()
    assert hidden(draft, '#reduce-form') and draft.text('#reduce-go') == 'Сократить'


def test_changing_the_number_cancels_the_warning(draft):
    warn_at_two(draft)
    draft.page.fill('#reduce-n', '3')
    assert draft.text('#reduce-go') == 'Сократить'


def test_after_warning_other_number_asks_the_model_again(draft):
    warn_at_two(draft)
    draft.model.on('promptReduceCases', md.reduce_keep(MIN_KEEP))
    draft.page.fill('#reduce-n', '3')
    reduce_go(draft)
    assert len(draft.model.calls_of('promptReduceCases')) == 2 and draft.state('S.run.cases.length') == 3


def test_cancel_forgets_the_warning(draft):
    warn_at_two(draft)
    draft.page.click('#reduce-cancel')
    open_reduce(draft, 2)
    assert draft.text('#reduce-go') == 'Сократить'


# ---------- ошибки модели ----------
def test_model_error_is_shown_and_cases_stay(draft):
    draft.model.on('promptReduceCases', ModelError('rate_limited', 'Лимит запросов исчерпан'))
    reduce_to(draft, 3)
    assert draft.text('#reduce-hint') == 'Не удалось сократить: Лимит запросов исчерпан' and 'err' in draft.page.get_attribute('#reduce-hint', 'class')
    assert draft.state('S.run.cases.length') == 4 and not hidden(draft, '#reduce-form')


def test_reduction_can_be_repeated_after_model_error(draft):
    draft.model.on('promptReduceCases', ModelError('rate_limited', 'Лимит запросов исчерпан'))
    reduce_to(draft, 3)
    draft.model.on('promptReduceCases', md.reduce_keep(MIN_KEEP))
    reduce_go(draft)
    assert draft.state('S.run.cases.length') == 3


# ---------- что получает модель при сокращении ----------
@pytest.fixture
def with_spec(draft, tmp_path):
    """Черновик, к которому есть документ ТЗ: его имя и текст должны попасть в запрос сокращения."""
    draft.page.click('#btn-newses')
    draft.upload(files.spec_file(tmp_path))
    draft.generate()
    return draft


def reduce_prompt(app):
    app.model.reset()
    reduce_to(app, 2)
    calls = app.model.calls_of('promptReduceCases')
    assert len(calls) == 1
    return calls[0].prompt


def test_prompt_has_documentation_text(with_spec):
    p = reduce_prompt(with_spec)
    assert '### Документ «ТЗ-восстановление.md»' in p and 'Ссылка действует 30 минут' in p


def test_prompt_lists_cases_with_requirements(with_spec):
    p = reduce_prompt(with_spec)
    ids = md.reduce_line_ids(p)
    assert sorted(ids) == sorted(with_spec.state(IDS))
    assert any(l.startswith('API-001 | API | Высокий | R-002 | [BE] ') for l in p.splitlines())


def test_prompt_has_requirements_and_target(with_spec):
    p = reduce_prompt(with_spec)
    assert 'R-003 «Сквозное восстановление»' in p and re.search(r'(?<!\d)2 (штук|кейсов)', p)


def test_prompt_documentation_is_limited(draft, tmp_path):
    """Большой документ обрезается до выдержек, близких к требованиям и кейсам (не больше 60 000 знаков на все документы)."""
    filler = '\n'.join(f'Зебра номер {i} пасётся на лугу' for i in range(4000))
    text = filler[:len(filler) // 2] + '\nЛимит запросов на сброс пароля — не более 3 за 15 минут\n' + filler[len(filler) // 2:]
    draft.page.click('#btn-newses')
    draft.upload(files.write(tmp_path / 'большой.md', text))
    draft.generate()
    p = reduce_prompt(draft)
    doc = p.split('### Документ «большой.md»', 1)[1].split('\n\n## Кейсы', 1)[0]
    assert len(text) > 120000 and len(doc) <= 60000
    assert 'Лимит запросов на сброс пароля — не более 3 за 15 минут' in doc
    assert doc.count('Зебра') < 4000
