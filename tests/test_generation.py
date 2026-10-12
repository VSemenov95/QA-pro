"""Генерация: анализ требований, чек-лист, план, кейсы, черновик; выбор результата и видов тестов; ответы на вопросы."""
import pytest

from tests.support import files
from tests.support.model import ModelError, case_body
from tests.support.model_generation import cases_for, checks_of, requirement


@pytest.fixture
def done(app):
    """Пример ТЗ сгенерирован целиком: чек-лист и кейсы."""
    app.add_sample()
    app.generate()
    return app


def collapsed_kinds(app):
    out = []
    for c in app.model.calls:
        if not out or out[-1] != c.kind:
            out.append(c.kind)
    return out


# ---------- сквозная генерация ----------
def test_generation_finishes_without_errors(done):
    assert done.state('S.run.status') == 'done', done.state('S.run.error')
    assert done.state('S.run.failed.length') == 0 and done.state('S.run.error') is None


def test_requirements_and_questions_come_from_analysis(done):
    assert done.state("S.run.requirements.map((r) => r.id)") == ['R-001', 'R-002', 'R-003', 'R-004']
    assert done.state("S.run.requirements.every((r) => r.inScope)") is True
    assert done.state("S.run.questions.map((q) => [q.id, q.text])") == [['Q-01', 'Что происходит при 4-м запросе через UI?']]


def test_checklist_is_built_in_groups(done):
    groups = done.state("S.run.checklist.groups.map((g) => [g.title, g.items.map((i) => i.id)])")
    assert groups == [['Форма восстановления', ['CL-001', 'CL-002']], ['API сброса', ['CL-003', 'CL-004']]]


def test_every_check_becomes_a_case_with_id_by_type(done):
    ids = done.state("S.run.cases.map((c) => [c.type, c.dispId, c.testCase.id])")
    assert sorted(ids) == sorted([['api', 'API-001', 'API-001'], ['api', 'API-002', 'API-002'], ['ui', 'UI-001', 'UI-001'], ['e2e', 'E2E-001', 'E2E-001']])


def test_all_requirements_are_covered(done):
    assert done.state("a.S.run.requirements.filter((r) => r.inScope && !S.run.cases.some((c) => c.requirementIds.includes(r.id))).length") == 0
    done.tab('agent')
    assert '100%' in done.text('#tab-body .stats')


def test_steps_are_marked_by_outcome(done):
    st = done.state("Object.fromEntries(Object.entries(S.run.steps).map(([k, v]) => [k, v.status]))")
    assert {k: st[k] for k in ('parse', 'analyze', 'checklist', 'plan', 'generate', 'coverage')} == {k: 'done' for k in ('parse', 'analyze', 'checklist', 'plan', 'generate', 'coverage')}
    assert st['map'] == 'skipped' and st['actualize'] == 'skipped'


def test_model_is_asked_in_pipeline_order(done):
    seq = collapsed_kinds(done)
    cut = seq.index('promptCoverageAudit') + 1
    assert seq[:cut] == ['promptAnalyze', 'promptAnalyzeMore', 'promptChecklist', 'promptPlan', 'promptGenerate', 'promptCoverageAudit']


def test_generation_toast_and_draft_tab(done):
    assert done.state('S.tab') == 'draft'
    assert 'Готово: 4 тест-кейса, чек-лист из 4 пунктов' in ' '.join(done.toast_texts())


# ---------- черновик ----------
def test_cases_wait_in_draft_outside_the_product(done):
    assert done.state('S.run.stage') == 'draft'
    assert done.state('S.prodIndex.cases.length') == 0
    assert done.text('#tab-draft .cnt') == '4'


def test_add_to_project_moves_cases_into_product_index(done):
    done.tab('draft')
    done.page.click('[data-act=draft-add]')
    done.page.wait_for_function("() => window.__qa.S.run.stage === 'added'")
    done.page.wait_for_function("() => window.__qa.S.prodIndex.cases.length === 4")
    assert sorted(done.state('S.prodIndex.cases.map((x) => x.i)')) == ['API-001', 'API-002', 'E2E-001', 'UI-001']
    assert 'Мой продукт' in ' '.join(done.toast_texts())


def test_added_cases_leave_the_draft_actions(done):
    done.tab('draft')
    done.page.click('[data-act=draft-add]')
    done.page.wait_for_function("() => window.__qa.S.run.stage === 'added'")
    assert done.count('[data-act=draft-add]') == 0 and 'в проекте' in done.text('.draft-head')


def test_next_run_continues_numbering_after_added_draft(done):
    done.tab('draft')
    done.page.click('[data-act=draft-add]')
    done.page.wait_for_function("() => window.__qa.S.prodIndex.cases.length === 4")
    done.call('a.S.run = null; a.renderAll()')
    done.generate()
    assert sorted(done.state("S.run.cases.map((c) => c.dispId)")) == ['API-003', 'API-004', 'E2E-002', 'UI-002']


# ---------- что генерировать ----------
def set_outputs(app, cases=True, checklist=True):
    for k, on in (('cases', cases), ('checklist', checklist)):
        app.page.set_checked(f'#out-{k}', on)


@pytest.mark.parametrize('cases,checklist,label', [
    (True, True, 'Сгенерировать чек-лист и тест-кейсы'), (True, False, 'Сгенерировать тест-кейсы'), (False, True, 'Сгенерировать чек-лист')])
def test_run_button_label_follows_outputs(app, cases, checklist, label):
    set_outputs(app, cases, checklist)
    assert app.text('#btn-run') == label


def test_only_cases_skips_checklist(app):
    set_outputs(app, checklist=False)
    app.generate()
    kinds = {c.kind for c in app.model.calls}
    assert 'promptChecklist' not in kinds and 'promptGenerate' in kinds
    assert app.state('S.run.checklist') is None and app.state('S.run.cases.length') == 4
    assert app.state('S.run.steps.checklist.status') == 'skipped'


def test_only_checklist_skips_plan_and_cases(app):
    set_outputs(app, cases=False)
    app.generate()
    kinds = {c.kind for c in app.model.calls}
    assert 'promptChecklist' in kinds and not kinds & {'promptPlan', 'promptGenerate', 'promptCoverageAudit'}
    assert app.state('S.run.cases.length') == 0 and app.state('S.run.checklist.groups.length') == 2
    assert app.state('S.tab') == 'agent'   # кейсов нет — в черновик переходить некуда


def test_nothing_selected_blocks_the_run(app):
    set_outputs(app, cases=False, checklist=False)
    assert app.page.is_disabled('#btn-run')
    assert app.text('#run-note') == 'Выберите, что сгенерировать.'


def test_no_test_types_blocks_the_run(app):
    for t in ('api', 'ui', 'e2e'):
        app.page.set_checked(f'#type-{t}', False)
    assert app.page.is_disabled('#btn-run')
    assert app.text('#run-note') == 'Выберите хотя бы один вид тестов.'


def test_no_documents_blocks_the_run(app):
    app.page.click('[data-doc-act=unrun]')
    assert app.page.is_disabled('#btn-run')
    assert 'Загрузите ТЗ для этого запуска' in app.text('#run-note')


def test_selected_types_limit_requirements_and_cases(app):
    for t in ('api', 'e2e'):
        app.page.set_checked(f'#type-{t}', False)
    app.generate()
    assert app.state("S.run.cases.every((c) => c.type === 'ui')") is True and app.state('S.run.cases.length') >= 1
    assert app.state("S.run.requirements.filter((r) => !r.inScope).map((r) => r.id)") == ['R-002', 'R-003']
    assert 'вне выбранных видов тестов' in ' '.join(app.state("S.run.steps.analyze.log.map((l) => l.text)"))


# ---------- анализ: несколько фрагментов ----------
def test_requirements_from_fragments_are_merged(app, tmp_path):
    """Большой документ режется на фрагменты; одинаковое требование из двух фрагментов — одно, критерии складываются."""
    para = ('Абзац требований. ' * 600).strip()   # ~10 тыс. знаков
    big = files.write(tmp_path / 'ТЗ-большое.md', '\n\n'.join(f'## Раздел {i}\n{para}' for i in range(3)))
    answers = [
        {'requirements': [requirement('Ссылка «Забыли пароль?»', criteria=['видна под полем']), requirement('Только в первом', types=('api',))], 'questions': ['Нужен ли капча?']},
        {'requirements': [requirement('ссылка «забыли пароль?»', criteria=['ведёт на экран', 'видна под полем']), requirement('Только во втором')], 'questions': ['нужен ли капча', 'Сколько живёт ссылка?']},
    ]
    app.model.on('promptAnalyze', lambda call: answers[call.index])
    app.upload(big)
    app.generate()
    assert 'Документы разбиты на 2 фрагмента' in ' '.join(app.state("S.run.steps.analyze.log.map((l) => l.text)"))
    reqs = app.state("S.run.requirements.map((r) => [r.id, r.title, r.criteria])")
    assert reqs == [['R-001', 'Ссылка «Забыли пароль?»', ['видна под полем', 'ведёт на экран']], ['R-002', 'Только в первом', []], ['R-003', 'Только во втором', []]]
    assert app.state("S.run.questions.map((q) => q.text)") == ['Нужен ли капча?', 'Сколько живёт ссылка?']


def test_requirement_without_title_or_with_unknown_type_is_dropped(app):
    """Требование без названия не создаётся; виды тестов, которых нет среди выбранных, из требования убираются."""
    app.model.on('promptAnalyze', {'requirements': [{'description': 'без названия', 'types': ['ui']}, requirement('Кнопка', types=('ui', 'mobile'))], 'questions': []})
    app.generate()
    assert app.state("S.run.requirements.map((r) => [r.title, r.types])") == [['Кнопка', ['ui']]]


def test_priority_words_are_normalized(app):
    app.model.on('promptAnalyze', {'requirements': [requirement('А', priority='Высокий'), requirement('Б', priority='low'), requirement('В', priority='что-то')], 'questions': []})
    app.generate()
    assert app.state("S.run.requirements.map((r) => r.priority)") == ['high', 'low', 'medium']


def test_second_run_reuses_analysis_of_same_documents(app):
    app.generate()
    app.call('a.S.run = null; a.renderAll()')
    app.generate()
    assert len(app.model.calls_of('promptAnalyze')) == 1
    assert 'взят из кэша продукта' in ' '.join(app.state("S.run.steps.analyze.log.map((l) => l.text)"))


def test_analysis_cache_can_be_switched_off(app):
    app.page.uncheck('#reuse-analysis')
    app.generate()
    app.call('a.S.run = null; a.renderAll()')
    app.generate()
    assert len(app.model.calls_of('promptAnalyze')) == 2


# ---------- чек-лист: нормализация ответа ----------
def test_checklist_items_are_normalized(app):
    app.model.on('promptChecklist', {'groups': [
        {'title': 'Форма', 'items': [
            {'check': 'Ссылка видна', 'type': 'ui', 'priority': 'Высокий', 'suites': ['Смоук', 'Регресс'], 'requirementIds': ['R-001', 'R-999']},
            {'check': '', 'type': 'ui'},
            {'text': 'Ответ 202', 'type': 'mobile', 'suites': ['unknown']}]},
        {'title': 'Пусто', 'items': []}]})
    app.generate()
    items = app.state("S.run.checklist.groups.flatMap((g) => g.items).map((i) => [i.id, i.check, i.type, i.priority, i.suites, i.requirementIds])")
    assert items == [['CL-001', 'Ссылка видна', 'ui', 'high', ['smoke', 'regression'], ['R-001']], ['CL-002', 'Ответ 202', 'api', 'medium', [], []]]
    assert app.state("S.run.checklist.groups.map((g) => g.title)") == ['Форма']


def test_suites_of_cases_are_normalized(app):
    def gen(call):
        res = cases_for(call.prompt)
        for c in res['cases']:
            c['suites'] = ['Смоук', 'regression', 'что-то']
        return res
    app.model.on('promptGenerate', gen)
    app.generate()
    assert app.state("S.run.cases.every((c) => c.suites.join() === 'smoke,regression')") is True


# ---------- ошибки модели ----------
def test_rate_limit_in_analysis_stops_the_run_and_can_be_resumed(app):
    app.model.on('promptAnalyze', ModelError('rate_limited'))
    app.generate()
    assert app.state('S.run.status') == 'error'
    assert 'исчерпан лимит' in app.state('S.run.error')
    app.tab('agent')
    assert 'Работа прервана' in app.text('.banner.err')
    app.model.handlers.pop('promptAnalyze')
    app.page.click('[data-act=resume-run]')
    app.wait_idle()
    assert app.state('S.run.status') == 'done' and app.state('S.run.cases.length') == 4


def test_plan_failure_falls_back_to_acceptance_criteria(app):
    app.model.on('promptPlan', ModelError('invalid_json'))
    app.generate()
    assert app.state('S.run.status') == 'done'
    assert app.state("S.run.plan.every((p) => p.title.startsWith('Дополнительно: '))") is True
    assert app.state('S.run.cases.length') >= 4
    assert 'План построен по критериям приёмки требований' in ' '.join(app.state("S.run.steps.plan.log.map((l) => l.text)"))


def test_empty_generation_answer_gives_partial_run(app):
    app.model.on('promptGenerate', {'cases': []})
    app.generate()
    assert app.state('S.run.status') == 'partial'
    assert app.state("S.run.failed.map((f) => f.error)") != [] and 'Модель не вернула ни одного кейса' in app.state('S.run.failed[0].error')
    assert app.state('S.run.cases.length') == 0


def test_cases_with_foreign_plan_item_and_requirements_are_repaired(app):
    """Модель назвала несуществующие группу плана и требование: кейс привязывается к группе пачки и её требованиям."""
    def gen(call):
        return {'cases': [{'planItem': 'P-99', 'requirementIds': ['R-999'], 'suites': [], 'testCase': case_body('Кейс ' + c)} for _, c in checks_of(call.prompt)]}
    app.model.on('promptGenerate', gen)
    app.generate()
    assert app.state("S.run.cases.every((c) => /^P-\\d+$/.test(c.planItem) && c.planItem !== 'P-99' && c.requirementIds.length > 0 && !c.requirementIds.includes('R-999'))") is True


# ---------- ответы на вопросы к документации ----------
def answer_first_question(app, text='При 4-м запросе показываем таймер обратного отсчёта'):
    app.tab('questions')
    app.page.fill('textarea[data-q="Q-01"]', text)


def test_questions_tab_lists_questions_without_answers(done):
    done.tab('questions')
    assert 'Что происходит при 4-м запросе через UI?' in done.text('.q-list') and 'нет ответа' in done.text('#qst-Q-01')


def test_answer_makes_question_pending_and_enables_apply(done):
    answer_first_question(done)
    assert done.text('#qst-Q-01') == 'не учтён'
    assert done.text('[data-act=apply-answers]') == 'Учесть ответы в тест-кейсах и чек-листе (1)'
    assert not done.page.is_disabled('[data-act=apply-answers]')


def test_apply_is_disabled_without_answers(done):
    done.tab('questions')
    assert done.page.is_disabled('[data-act=apply-answers]')


def test_applying_answer_adds_criteria_and_marks_question(done):
    answer_first_question(done)
    done.page.click('[data-act=apply-answers]')
    done.wait_idle()
    assert 'На 4-й запрос UI показывает таймер' in done.state("S.run.reqById['R-004'].criteria")
    assert done.state("S.run.questions[0].appliedAnswer") == 'При 4-м запросе показываем таймер обратного отсчёта'
    assert done.text('#qst-Q-01') == 'учтён'
    assert 'Ответы учтены: Q-01' in ' '.join(done.state("S.run.steps.answers.log.map((l) => l.text)"))


def test_impact_prompt_contains_the_answer(done):
    answer_first_question(done)
    done.page.click('[data-act=apply-answers]')
    done.wait_idle()
    p = done.model.prompts_of('promptImpact')[0]
    assert 'При 4-м запросе показываем таймер обратного отсчёта' in p and 'Q-01' in p


def test_answer_rewrites_affected_case_and_adds_new_check(done):
    done.model.on('promptImpact', {'criteria': [], 'update': [{'caseId': 'API-001', 'instruction': 'Указать код 429 на четвёртый запрос'}],
                                   'add': [{'type': 'api', 'requirementIds': ['R-002'], 'check': 'Четвёртый запрос за 15 минут — 429', 'suites': ['regression']}], 'checklistUpdate': [{'itemId': 'CL-004', 'check': 'Четвёртый запрос — 429 и таймер'}]})
    done.model.on('promptReviseBatch', lambda call: {'cases': [{'caseId': 'API-001', 'testCase': case_body('Исправленный по ответу')}]})
    answer_first_question(done)
    done.page.click('[data-act=apply-answers]')
    done.wait_idle()
    assert done.state("S.run.cases.find((c) => c.dispId === 'API-001').testCase.title") == '[BE] Исправленный по ответу'
    assert done.state("S.run.cases.length") == 5
    assert done.state("S.run.cases.some((c) => c.testCase.title === '[BE] Кейс: Четвёртый запрос за 15 минут — 429')") is True
    assert done.state("S.run.checklist.groups.flatMap((g) => g.items).find((i) => i.id === 'CL-004').check") == 'Четвёртый запрос — 429 и таймер'


def test_answers_go_into_later_prompts(done):
    answer_first_question(done)
    done.page.click('[data-act=apply-answers]')
    done.wait_idle()
    done.tab('cases')
    done.page.click('#case-list article:first-child .case-h')
    done.page.click('[data-act=refine-case]')
    done.page.fill('textarea[data-field=comment]', 'Сделай короче')
    done.page.click('[data-act=do-refine]')
    done.page.wait_for_function("() => document.querySelector('.case-note')?.textContent.includes('доработан')")
    assert 'При 4-м запросе показываем таймер обратного отсчёта' in done.model.prompts_of('promptRefine')[0]
