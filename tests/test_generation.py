"""Генерация: анализ требований, чек-лист, план, кейсы, черновик; выбор результата и видов тестов; ответы на вопросы."""
import re

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
    keys = ('parse', 'analyze', 'checklist', 'plan', 'gen_api', 'gen_ui', 'gen_e2e', 'coverage')
    assert {k: st[k] for k in keys} == {k: 'done' for k in keys}
    assert st['map'] == 'skipped' and st['actualize'] == 'skipped'


def test_model_is_asked_in_pipeline_order(done):
    seq = collapsed_kinds(done)
    cut = seq.index('promptCoverageAudit') + 1
    # выбраны чек-лист и кейсы: план строится из чек-листа, отдельного запроса плана нет
    assert seq[:cut] == ['promptAnalyze', 'promptAnalyzeMore', 'promptChecklist', 'promptGenerate', 'promptCoverageAudit']


def test_generation_toast_and_draft_tab(done):
    assert done.state('S.tab') == 'draft'
    assert 'Готово: 4 тест-кейса, чек-лист из 4 пунктов' in ' '.join(done.toast_texts())


# ---------- что генерировать ----------
def switch(app, sel, on):
    """Флажок за стилизованной подписью: нажимается подпись."""
    if app.page.is_checked(sel) != on:
        app.page.click(f'label:has({sel})')


def set_outputs(app, cases=True, checklist=True):
    for k, on in (('cases', cases), ('checklist', checklist)):
        switch(app, f'#out-{k}', on)


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


def test_checklist_only_run_counts_coverage_by_checklist(app):
    set_outputs(app, cases=False)
    app.generate()
    app.tab('agent')
    stat = app.text('#tab-body .stat:has(span:text-is("Покрытие"))')
    assert '50%' in stat and 'требований в чек-листе' in stat   # R-001 и R-002 есть в пунктах, R-003 и R-004 — нет


def test_nothing_selected_blocks_the_run(app):
    set_outputs(app, cases=False, checklist=False)
    assert app.page.is_disabled('#btn-run')
    assert app.text('#run-note') == 'Выберите, что сгенерировать.'


def test_no_test_types_blocks_the_run(app):
    for t in ('api', 'ui', 'e2e'):
        switch(app, f'#type-{t}', False)
    assert app.page.is_disabled('#btn-run')
    assert app.text('#run-note') == 'Выберите хотя бы один вид тестов.'


def test_no_documents_blocks_the_run(app):
    app.page.click('[data-doc-act=unrun]')
    assert app.page.is_disabled('#btn-run')
    assert 'Загрузите ТЗ для этого запуска' in app.text('#run-note')


def test_selected_types_limit_requirements_and_cases(app):
    for t in ('api', 'e2e'):
        switch(app, f'#type-{t}', False)
    app.generate()
    assert app.state("S.run.cases.every((c) => c.type === 'ui')") is True and app.state('S.run.cases.length') >= 1
    assert app.state("S.run.requirements.filter((r) => !r.inScope).map((r) => r.id)") == ['R-002', 'R-003']
    assert 'вне выбранных видов тестов' in ' '.join(app.state("S.run.steps.analyze.log.map((l) => l.text)"))
    app.tab('reqs')
    assert app.text('tr.req-row[data-id=R-002] td:last-child') == 'вне выбора' and app.text('tr.req-row[data-id=R-001] td:last-child') != 'вне выбора'


# ---------- анализ: несколько фрагментов ----------
def test_requirements_from_fragments_are_merged(app, tmp_path):
    """Большой документ режется на фрагменты; одинаковое требование из двух фрагментов — одно, критерии складываются."""
    para = ('Абзац требований. ' * 500).strip()   # ~9 тыс. знаков: вместе с примером ТЗ документы дают ровно два фрагмента
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
    assert app.state("S.run.requirements.map((r) => r.priority)") == ['P3_HIGH', 'P1_LOW', 'P2_MEDIUM']


def test_second_run_reuses_analysis_of_same_documents(app):
    app.generate()
    app.generate()
    assert len(app.model.calls_of('promptAnalyze')) == 1
    assert 'взят из кэша продукта' in ' '.join(app.state("S.run.steps.analyze.log.map((l) => l.text)"))


def test_changed_rules_invalidate_analysis_cache(app):
    app.generate()
    app.page.fill('#cfg-rules', 'Новые правила команды')
    app.generate()
    assert len(app.model.calls_of('promptAnalyze')) == 2


def test_changed_document_invalidates_analysis_cache(app, tmp_path):
    app.generate()
    app.upload(files.spec_file(tmp_path))
    app.generate()
    assert len(app.model.calls_of('promptAnalyze')) == 2


def test_analysis_cache_can_be_switched_off(app):
    switch(app, '#reuse-analysis', False)
    app.generate()
    app.generate()
    assert len(app.model.calls_of('promptAnalyze')) == 2


# ---------- расход токенов ----------
def test_usage_counts_every_model_request_by_step(done):
    u = done.state('S.run.usage')
    assert u['calls'] == len(done.model.calls)
    assert {k: v['calls'] for k, v in u['by'].items()} == {'analyze': 2, 'checklist': 1, 'gen_api': 1, 'gen_ui': 1, 'gen_e2e': 1, 'coverage': 1, 'knowledge': 1}
    assert u['in'] > 0 and u['out'] > 0


def test_agent_tab_shows_usage(done):
    done.tab('agent')
    assert '8 запросов' in done.text('#tab-body .stats')   # план — из чек-листа, без запроса and 'Расход по шагам (оценка): ' in done.text('.usage-line')
    assert 'генерация' in done.text('.usage-line') and 'анализ' in done.text('.usage-line')


def test_new_generation_resets_case_filters(done):
    done.tab('cases')
    done.page.click('[data-act=fsuite][data-s=smoke]')
    done.page.fill('#case-q', 'API')
    done.generate()
    done.tab('cases')
    assert done.state("S.filter.suite") == 'all' and done.page.input_value('#case-q') == '' and done.count('#case-list article') >= 4


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
    assert items == [['CL-001', 'Ссылка видна', 'ui', 'P3_HIGH', ['smoke', 'regression'], ['R-001']], ['CL-002', 'Ответ 202', 'api', 'P2_MEDIUM', [], []]]
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
def test_rate_limit_in_analysis_stops_the_run(app):
    app.model.on('promptAnalyze', ModelError('rate_limited'))
    app.generate()
    assert app.state('S.run.status') == 'error'
    assert 'исчерпан лимит' in app.state('S.run.error')
    app.tab('agent')
    assert 'Работа прервана' in app.text('.banner.err')
    assert app.count('[data-act=resume-run]') == 1
    assert app.state('S.run.cases.length') == 0 and len(app.model.calls_of('promptPlan')) == 0


def test_resume_after_rate_limit_in_analysis_repeats_analysis(app):
    app.model.on('promptAnalyze', ModelError('rate_limited'))
    app.generate()
    app.model.handlers.pop('promptAnalyze')
    app.tab('agent')
    app.page.click('[data-act=resume-run]')
    app.wait_idle()
    assert app.state('S.run.requirements.length') == 4 and app.state('S.run.cases.length') == 4


def test_resume_after_rate_limit_in_checklist_repeats_checklist(app):
    app.model.on('promptChecklist', ModelError('rate_limited'))
    app.generate()
    assert app.state('S.run.status') == 'error' and app.state('S.run.requirements.length') == 4
    app.model.handlers.pop('promptChecklist')
    app.tab('agent')
    app.page.click('[data-act=resume-run]')
    app.wait_idle()
    assert app.state('S.run.checklist && S.run.checklist.groups.length') == 2


def test_resume_after_rate_limit_in_cases_writes_only_missing(app):
    """Лимит на шаге кейсов: анализ, чек-лист и план не повторяются, кейсы допишутся."""
    app.model.on('promptGenerate', ModelError('rate_limited'))
    app.generate()
    assert app.state('S.run.status') == 'error' and app.state('S.run.cases.length') == 0
    app.model.handlers.pop('promptGenerate')
    app.tab('agent')
    app.page.click('[data-act=resume-run]')
    app.wait_idle()
    assert app.state('S.run.status') == 'done' and app.state('S.run.cases.length') >= 4
    assert [len(app.model.calls_of(k)) for k in ('promptAnalyze', 'promptChecklist', 'promptPlan')] == [1, 1, 0]   # план — из чек-листа


def test_plan_failure_falls_back_to_acceptance_criteria(app):
    set_outputs(app, checklist=False)
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


def test_partial_run_shows_banner_and_can_be_repeated(app):
    app.model.on('promptGenerate', {'cases': []})
    app.generate()
    app.tab('agent')
    assert 'Готово с ошибками.' in app.text('.banner.warn') and app.count('#tab-body [data-act=resume-run]') == 1
    app.model.handlers.pop('promptGenerate')
    app.page.click('#tab-body [data-act=resume-run]')
    app.wait_idle()
    assert app.state('S.run.status') == 'done' and app.state('S.run.cases.length') >= 4 and app.state('S.run.failed.length') == 0


@pytest.mark.parametrize('shape', ['list', 'testCases', 'flat', 'junk'])
def test_cases_answer_shapes_are_accepted(app, shape):
    """Модель вернула кейсы не в том виде, что просили: массив, ключ testCases, поля кейса без обёртки testCase, посторонние элементы."""
    def gen(call):
        cases = [{'planItem': pid, 'suites': ['regression'], 'testCase': case_body('Кейс: ' + c)} for pid, c in checks_of(call.prompt)]
        if shape == 'list':
            return cases
        if shape == 'testCases':
            return {'testCases': cases}
        if shape == 'flat':
            return {'cases': [{'planItem': c['planItem'], 'suites': c['suites'], **c['testCase']} for c in cases]}
        return {'cases': [None, 'text', 5] + cases}
    app.model.on('promptGenerate', gen)
    app.generate()
    titles = app.state("S.run.cases.map((c) => c.testCase.title)")
    assert app.state('S.run.status') == 'done' and len(titles) == app.state("S.run.plan.reduce((n, p) => n + p.checks.length, 0)")
    assert all(t.startswith('[') and ': ' in t for t in titles)


def test_cases_with_foreign_plan_item_and_requirements_are_repaired(app):
    """Модель назвала несуществующие группу плана и требование: кейс привязывается к группе пачки и её требованиям."""
    def gen(call):
        return {'cases': [{'planItem': 'P-99', 'requirementIds': ['R-999'], 'suites': [], 'testCase': case_body('Кейс ' + c)} for _, c in checks_of(call.prompt)]}
    app.model.on('promptGenerate', gen)
    app.generate()
    assert app.state("S.run.cases.every((c) => S.run.plan.some((p) => p.id === c.planItem) && c.planItem !== 'P-99')") is True
    assert app.state("S.run.cases.every((c) => c.requirementIds.length > 0 && !c.requirementIds.includes('R-999') && c.requirementIds.every((id) => S.run.reqById[id]))") is True


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


def test_changed_answer_is_pending_again(done):
    answer_first_question(done)
    done.page.click('[data-act=apply-answers]')
    done.wait_idle()
    done.tab('questions')
    done.page.fill('textarea[data-q="Q-01"]', 'Показываем таймер и блокируем кнопку')
    assert done.text('#qst-Q-01') == 'не учтён' and not done.page.is_disabled('[data-act=apply-answers]')


def test_impact_prompt_contains_the_answer(done):
    answer_first_question(done)
    done.page.click('[data-act=apply-answers]')
    done.wait_idle()
    p = done.model.prompts_of('promptImpact')[0]
    assert 'При 4-м запросе показываем таймер обратного отсчёта' in p and 'Q-01' in p


def test_answer_rewrites_affected_case_and_adds_new_check(done):
    done.model.on('promptImpact', {'criteria': [], 'update': [{'caseId': 'API-001', 'instruction': 'Указать код 429 на четвёртый запрос'}],
                                   'add': [{'type': 'api', 'requirementIds': ['R-002'], 'check': 'Четвёртый запрос за 15 минут — 429', 'suites': ['regression']}], 'checklistUpdate': [{'itemId': 'CL-004', 'check': 'Четвёртый запрос — 429 и таймер'}]})
    done.model.on('promptGenerate', lambda call: cases_for(call.prompt))
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


# ---------- полнота анализа и сверка покрытия ----------
def test_completeness_pass_adds_missing_requirements_and_criteria(app):
    """Второй проход по фрагменту: пропущенное требование добавляется, дубль по названию — нет, критерий дописывается существующему."""
    app.model.on('promptAnalyzeMore', {
        'requirements': [requirement('Блокировка после 5 неудачных попыток', types=('ui', 'api'), criteria=['6-я попытка — «Вход заблокирован на 30 минут»']), {'title': 'Ссылка «Забыли пароль?»', 'description': 'дубль'}],
        'criteria': [{'title': 'Ссылка «Забыли пароль?»', 'add': ['Ссылка ведёт на /password-reset', 'Ссылка видна под полем пароля']}]})
    app.generate()
    assert app.state("S.run.requirements.map((r) => r.title)") == ['Ссылка «Забыли пароль?»', 'API запроса сброса', 'Сквозное восстановление', 'Лимит запросов', 'Блокировка после 5 неудачных попыток']
    assert app.state("S.run.reqById['R-001'].criteria") == ['Ссылка видна под полем пароля', 'Ссылка ведёт на /password-reset']   # повторный критерий не дублируется
    assert app.state("S.run.reqById['R-005'].criteria") == ['6-я попытка — «Вход заблокирован на 30 минут»']
    assert 'проверка полноты: +1 требование, +1 критерий' in ' '.join(app.state("S.run.steps.analyze.log.map((l) => l.text)"))


def test_completeness_pass_failure_keeps_first_answer(app):
    app.model.on('promptAnalyzeMore', ModelError('invalid_json'))
    app.generate()
    assert app.state('S.run.status') == 'done' and app.state('S.run.requirements.length') == 4


def audit_gap(call):
    ids = re.findall(r'### (R-\d+) ', call.prompt)
    if 'R-001' not in ids:
        return {'gaps': []}
    return {'gaps': [{'requirementId': 'R-001', 'type': 'ui', 'checks': ['Ссылка ведёт на /password-reset', 'Проверить запись в таблице users напрямую в БД']}, {'requirementId': 'R-777', 'type': 'ui', 'checks': ['Чужое требование']}]}


def test_coverage_audit_adds_checks_for_uncovered_criteria(app):
    app.model.on('promptCoverageAudit', audit_gap).on('promptGenerate', lambda call: cases_for(call.prompt))
    app.generate()
    assert app.state("S.run.plan.filter((p) => p.id.startsWith('C-')).map((p) => [p.id, p.type, p.requirementIds, p.checks])") == [['C-01', 'ui', ['R-001'], ['Ссылка ведёт на /password-reset']]]
    assert app.state("S.run.cases.some((c) => c.testCase.title === '[FE] Кейс: Ссылка ведёт на /password-reset' && c.requirementIds.includes('R-001'))") is True
    assert app.state('S.run.auditDone') is True
    log = ' '.join(app.state("S.run.steps.coverage.log.map((l) => l.text)"))
    assert 'Сверяю покрытие критериев: 4 требования, 1 запрос' in log and 'Дописываю 1 кейс для непокрытых критериев' in log


def test_completeness_prompt_lists_requirements_already_found(app):
    app.generate()
    p = app.model.prompts_of('promptAnalyzeMore')[0]
    assert '«Ссылка «Забыли пароль?»»: Ссылка видна под полем пароля' in p and '«Лимит запросов»' in p
    assert len(app.model.calls_of('promptAnalyzeMore')) == 1 and len(app.model.calls_of('promptCoverageAudit')) == 1


def test_coverage_audit_gets_cases_of_each_requirement(app):
    app.generate()
    p = app.model.prompts_of('promptCoverageAudit')[0]
    assert '### R-001 «Ссылка «Забыли пароль?»»' in p and 'Критерии: 1) Ссылка видна под полем пароля' in p
    assert 'UI-001' in p and 'API-001' in p


def test_failed_audit_is_repeated_not_marked_done(app):
    app.model.on('promptCoverageAudit', ModelError('invalid_json'))
    app.generate()
    assert app.state('S.run.status') == 'done' and app.state('!S.run.auditDone') is True


# ---------- объём тестирования ----------
SCOPE_CASES = [
    ('Исследовательское тестирование формы восстановления', True),
    ('Свободное исследование формы', True),
    ('Исследовательская проверка на усмотрение тестировщика', True),
    ('Выполнить INSERT INTO users и проверить ответ', True),
    ('Создать запись в таблице заявок', True),
    ('Проверить запись в таблице users напрямую в БД', True),
    ('После сброса SELECT * FROM users показывает новый хэш', True),
    ('В выпадающем списке SELECT «Роль» есть «Оператор»', False),
    ('POST /api/v1/password-reset с корректным email — 202', False),
    ('DELETE /api/v1/password-reset/1 — 405', False),
    ('После запроса в таблице заявок появилась запись со статусом NEW', False),
    ('', False),
]


@pytest.mark.parametrize('check,out', SCOPE_CASES)
def test_out_of_scope_checks(app, check, out):
    assert app.call('a.outOfScope(arg)', check) is out


def test_scope_rule_is_in_prompts_of_every_step(app):
    from pathlib import Path
    rule = (Path(__file__).resolve().parent.parent / 'rules' / 'scope.md').read_text(encoding='utf-8').splitlines()[0]
    app.generate()
    for kind in ('promptAnalyze', 'promptAnalyzeMore', 'promptChecklist', 'promptGenerate', 'promptCoverageAudit'):
        assert rule in app.model.prompts_of(kind)[0], kind


def test_scope_rule_is_in_plan_prompt_without_checklist(app):
    from pathlib import Path
    rule = (Path(__file__).resolve().parent.parent / 'rules' / 'scope.md').read_text(encoding='utf-8').splitlines()[0]
    set_outputs(app, checklist=False)
    app.generate()
    assert rule in app.model.prompts_of('promptPlan')[0]


def test_reviewer_is_told_about_scope(app):
    app.generate()
    app.page.click('#btn-review')
    app.wait_idle()
    assert 'нет исследовательских тестов и отдельных тестов только на БД' in app.model.prompts_of('promptReviewCases')[0]


def test_plan_drops_exploratory_and_db_only_checks(app):
    set_outputs(app, checklist=False)
    app.model.on('promptPlan', {'items': [
        {'type': 'api', 'title': 'API', 'requirementIds': ['R-002'], 'checks': ['202 для корректного email', 'DELETE /api/v1/password-reset/1 — 405', 'Выполнить INSERT INTO users и проверить ответ']},
        {'type': 'ui', 'title': 'Исследовательское тестирование формы', 'requirementIds': ['R-001'], 'checks': ['Свободное исследование формы']},
        {'type': 'ui', 'title': 'Форма', 'requirementIds': ['R-001'], 'checks': ['Ссылка видна', 'Исследовательская проверка на усмотрение тестировщика']}]})
    app.generate()
    checks = app.state("S.run.plan.filter((p) => p.id.startsWith('P-') && !p.title.startsWith('Дополнительно')).map((p) => [p.title, p.checks])")
    assert checks == [['API', ['202 для корректного email', 'DELETE /api/v1/password-reset/1 — 405']], ['Форма', ['Ссылка видна']]]
    assert 'Убрано проверок вне объёма (исследовательские, только на БД или ручная подготовка данных в БД): 3' in ' '.join(app.state("S.run.steps.plan.log.map((l) => l.text)"))


def test_checklist_drops_out_of_scope_items_but_keeps_ui_select(app):
    app.model.on('promptChecklist', {'groups': [{'title': 'Смешанное', 'items': [
        {'check': 'Ссылка «Забыли пароль?» видна', 'type': 'ui', 'suites': ['smoke'], 'requirementIds': ['R-001']},
        {'check': 'В выпадающем списке SELECT «Роль» есть «Оператор»', 'type': 'ui', 'suites': ['regression'], 'requirementIds': ['R-001']},
        {'check': 'После сброса SELECT * FROM users показывает новый хэш', 'type': 'api', 'suites': ['regression'], 'requirementIds': ['R-002']},
        {'check': 'Исследовательское тестирование формы восстановления', 'type': 'ui', 'suites': ['regression'], 'requirementIds': ['R-001']}]}]})
    app.generate()
    assert app.state("S.run.checklist.groups.flatMap((g) => g.items.map((i) => i.check))") == ['Ссылка «Забыли пароль?» видна', 'В выпадающем списке SELECT «Роль» есть «Оператор»']


def test_audit_drops_out_of_scope_checks(app):
    app.model.on('promptCoverageAudit', audit_gap).on('promptGenerate', lambda call: cases_for(call.prompt))
    app.generate()
    assert not any('напрямую в БД' in t for t in app.state("S.run.cases.map((c) => c.testCase.title)"))


# ---------- как проверки плана делятся на запросы ----------
def plan_of(*items):
    return {'items': [{'type': t, 'title': f'Группа {i + 1}', 'requirementIds': ['R-001', 'R-002', 'R-003', 'R-004'][i % 4:i % 4 + 1], 'checks': [f'{t}-{i + 1}.{k + 1}' for k in range(n)]} for i, (t, n) in enumerate(items)]}


def batch_sizes(app, plan):
    """Запросы на написание кейсов по проверкам плана: [(групп плана в запросе, проверок в запросе)]. Дополнительные группы покрытия не считаются."""
    set_outputs(app, checklist=False)   # план по требованиям, не из чек-листа
    app.model.on('promptPlan', plan).on('promptGenerate', lambda call: cases_for(call.prompt))
    app.generate()
    out = []
    for c in app.model.calls_of('promptGenerate'):
        mine = [(p, ch) for p, ch in checks_of(c.prompt) if re.fullmatch(r'(api|ui|e2e)-\d+\.\d+', ch)]
        if mine:
            out.append((len({p for p, _ in mine}), len(mine)))
    return sorted(out)


@pytest.mark.parametrize('plan,expected', [
    ([('ui', 10)], [(1, 2), (1, 8)]),                 # у UI и API в запросе до 8 проверок
    ([('api', 9)], [(1, 1), (1, 8)]),
    ([('e2e', 5)], [(1, 1), (1, 4)]),                 # у E2E — до 4
    ([('ui', 1), ('ui', 1), ('ui', 1), ('ui', 1)], [(1, 1), (3, 3)]),   # и не больше трёх групп плана в одном запросе
    ([('ui', 5), ('ui', 4)], [(1, 4), (1, 5)]),       # две группы вместе не помещаются в 8 проверок
    ([('ui', 3), ('ui', 4)], [(2, 7)]),
])
def test_plan_checks_are_split_into_requests_by_type_limits(app, plan, expected):
    assert batch_sizes(app, plan_of(*plan)) == expected


# ---------- обрезанный ответ при генерации ----------
def run_with_limit(app, limit, **kw):
    from tests.support.model_generation import truncating_generate
    sizes = []
    app.model.on('promptGenerate', truncating_generate(limit, sizes, **kw))
    app.generate()
    return sizes


def test_truncated_reply_splits_batch_until_it_fits(app):
    sizes = run_with_limit(app, 1)
    assert max(sizes) > 1 and sizes.count(1) >= 5   # длинные пачки оборвались и поделились; в итоге каждая проверка отдельно
    assert app.state('S.run.status') == 'done' and app.state('S.run.failed.length') == 0
    checks = app.state("S.run.plan.flatMap((p) => p.checks)")
    titles = app.state("S.run.cases.map((c) => c.testCase.title)")
    assert sorted(titles) == sorted('[' + {'api': 'BE', 'ui': 'FE', 'e2e': 'E2E'}[t] + '] Кейс: ' + c for t, c in app.state("S.run.plan.flatMap((p) => p.checks.map((c) => [p.type, c]))"))
    assert len(titles) == len(checks)   # ни дублей, ни потерь


def test_split_is_written_to_the_log(app):
    run_with_limit(app, 1)
    assert 'ответ не уместился — пишу по частям (2)' in ' '.join(app.state("S.run.steps.gen_api.log.map((l) => l.text)"))


def test_batch_fitting_the_limit_is_not_split(app):
    sizes = run_with_limit(app, 100)
    assert app.state('S.run.cases.length') == sum(sizes) and 'не уместился' not in ' '.join(app.state("S.run.steps.gen_api.log.map((l) => l.text)"))


def plan_with_bad_check():
    return {'items': [{'type': 'api', 'title': 'API', 'requirementIds': ['R-002'], 'checks': ['202 для корректного email', '400 для неверного формата', '429 на четвёртый запрос']}]}


def test_check_that_never_fits_does_not_stop_other_cases(app):
    set_outputs(app, checklist=False)
    app.model.on('promptPlan', plan_with_bad_check())
    run_with_limit(app, 10, fail_on='429 на четвёртый')
    titles = app.state("S.run.cases.map((c) => c.testCase.title)")
    assert '[BE] Кейс: 202 для корректного email' in titles and '[BE] Кейс: 400 для неверного формата' in titles
    assert not any('429' in t for t in titles)
    assert app.state('S.run.steps.gen_api.status') == 'error'


@pytest.mark.xfail(strict=True, reason='БАГ: если одна проверка плана так и не уместилась в ответ, запуск всё равно заканчивается «Готово»: '
                   'шаг «Проверка покрытия» стирает запись об ошибке, потому что требование покрыто другими кейсами. Недописанная проверка '
                   'теряется без заметного предупреждения (нет статуса «Готово с ошибками» и кнопки повтора на вкладке «Агент»)')
def test_check_that_never_fits_makes_run_partial(app):
    set_outputs(app, checklist=False)
    app.model.on('promptPlan', plan_with_bad_check())
    run_with_limit(app, 10, fail_on='429 на четвёртый')
    assert app.state('S.run.status') == 'partial'
    app.tab('agent')
    assert app.count('#tab-body [data-act=resume-run]') == 1


def test_resume_writes_only_missing_checks(app):
    set_outputs(app, checklist=False)
    app.model.on('promptPlan', plan_with_bad_check())
    run_with_limit(app, 10, fail_on='429 на четвёртый')
    before = len(app.model.calls_of('promptGenerate'))
    app.model.on('promptGenerate', lambda call: cases_for(call.prompt))
    app.tab('cases')
    app.page.click('[data-act=resume-run]')
    app.wait_idle()
    new = app.model.calls_of('promptGenerate')[before:]
    assert [[c for _, c in checks_of(x.prompt)] for x in new] == [['429 на четвёртый запрос']]
    assert app.state('S.run.status') == 'done' and app.state('S.run.cases.filter((c) => c.testCase.title.includes("429")).length') == 1
    titles = app.state("S.run.cases.map((c) => c.testCase.title)")
    assert len(titles) == len(set(titles))   # написанные раньше проверки не повторились


# ---------- предпросмотр документов ----------
def preview_btn(name):
    return f'li.doc:has(.doc-name[title="{name}"]) [data-doc-act=preview]'


def test_preview_shows_extracted_text(app, tmp_path):
    app.upload(files.spec_file(tmp_path))
    app.page.click(preview_btn('ТЗ-восстановление.md'))
    t = app.text('.doc-preview')
    assert t.startswith('# ТЗ: Восстановление пароля в личном кабинете') and '4.2. Не более 3 запросов' in t


def test_preview_is_toggled_by_second_click(app, tmp_path):
    app.upload(files.spec_file(tmp_path))
    app.page.click(preview_btn('ТЗ-восстановление.md'))
    assert app.count('.doc-preview') == 1
    app.page.click(preview_btn('ТЗ-восстановление.md'))
    assert app.count('.doc-preview') == 0


def test_preview_of_long_document_is_cut(app, tmp_path):
    text = 'Начало документа.\n' + 'а' * 5500 + '\nКонец документа.'
    app.upload(files.write(tmp_path / 'длинный.txt', text))
    app.page.click(preview_btn('длинный.txt'))
    shown = app.text('.doc-preview')
    assert shown.startswith('Начало документа.') and shown.endswith('…') and 'Конец документа' not in shown


def test_document_with_error_has_no_preview_button(app, tmp_path):
    app.upload(files.write(tmp_path / 'пустой.txt', '   '))
    assert app.count(preview_btn('пустой.txt')) == 0 and 'В файле не найден текст' in app.text('li.doc:has(.doc-name[title="пустой.txt"])')


@pytest.mark.needs_libs
def test_preview_of_docx_with_table(app, tmp_path):
    app.upload(files.docx_file(tmp_path))
    app.page.click(preview_btn('ТЗ-корзина.docx'))
    t = app.text('.doc-preview')
    assert '# ТЗ: Корзина' in t and '2.1. Пользователь добавляет товар в корзину кнопкой «В корзину».' in t and '| Количество | от 1 до 99 |' in t


@pytest.mark.needs_libs
def test_preview_of_xlsx_sheet(app, tmp_path):
    app.upload(files.xlsx_requirements(tmp_path))
    app.page.click(preview_btn('требования.xlsx'))
    t = app.text('.doc-preview')
    assert '### Лист «Требования»' in t and '| FR-1 | Сумма заказа превышает 500 рублей — доставка бесплатная |' in t


@pytest.mark.needs_libs
def test_preview_of_pdf_pages(app, tmp_path):
    app.upload(files.pdf_file(tmp_path))
    app.page.click(preview_btn('спецификация.pdf'))
    t = app.text('.doc-preview')
    assert '--- Страница 1 ---' in t and '3.1. POST /api/v1/cart возвращает 201 Created' in t


@pytest.mark.needs_libs
def test_generation_reads_every_uploaded_document(app, tmp_path):
    app.upload(files.docx_file(tmp_path), files.xlsx_requirements(tmp_path), files.pdf_file(tmp_path))
    app.generate()
    p = app.model.prompts_of('promptAnalyze')[0]
    for name, piece in (('ТЗ-корзина.docx', 'кнопкой «В корзину»'), ('требования.xlsx', 'FR-1'), ('спецификация.pdf', '/api/v1/cart')):
        assert f'<document name="{name}"' in p and piece in p, name
    assert 'в 4 документах' in ' '.join(app.state("S.run.steps.parse.log.map((l) => l.text)"))


# ---------- мобильная вёрстка ----------
def test_mobile_layout_has_no_horizontal_scroll(make_app):
    app = make_app(viewport=(400, 860))
    app.page.emulate_media(color_scheme='dark')
    app.add_sample()
    app.generate()
    wide = []
    for tab in ('agent', 'reqs', 'questions', 'draft', 'cases', 'checklist', 'review', 'export', 'history'):
        app.tab(tab)
        if tab == 'cases':
            app.page.click('#case-list article:first-child .case-h')
        if app.js('document.documentElement.scrollWidth') > 400:
            wide.append(tab)
    app.open_settings('model')
    for settab in ('tpl', 'export', 'review', 'tms', 'bg'):
        app.page.click(f'#settab-{settab}')
        if app.js('document.documentElement.scrollWidth') > 400:
            wide.append('settings:' + settab)
    assert wide == []


def test_mobile_run_button_is_reachable(make_app):
    app = make_app(viewport=(400, 860))
    box = app.page.locator('#btn-run').bounding_box()
    assert box and 0 <= box['x'] and box['x'] + box['width'] <= 400


# ---------- глубина проверок ----------
@pytest.mark.parametrize('depth,phrase', [('smoke', 'Смоук: только ключевые позитивные проверки'), ('standard', 'Базовый: позитивные проверки, основные негативные сценарии'), ('full', 'Полный: применяй техники тест-дизайна')])
def test_depth_goes_to_checklist_and_plan(app, depth, phrase):
    app.page.click(f'[data-depth={depth}]')
    set_outputs(app, cases=False)
    app.generate()
    assert phrase in app.model.prompts_of('promptChecklist')[0]
    set_outputs(app, cases=True, checklist=False)
    app.generate()
    assert phrase in app.model.prompts_of('promptPlan')[0]


def test_depth_is_basic_by_default(app):
    assert app.page.get_attribute('[data-depth=standard]', 'aria-checked') == 'true'


# ---------- шаблоны кейсов ----------
def test_template_prefix_is_used_in_case_numbers(app):
    app.open_settings('tpl')
    app.page.fill('#cfg-prefix', 'PRJ-API-')
    app.page.click('[data-cfgtype=ui]')
    app.page.fill('#cfg-prefix', 'UI-PRJ-')
    app.close_settings()
    app.generate()
    assert app.state("S.run.cases.map((c) => [c.dispId, c.testCase.id])") == [['PRJ-API-001', 'PRJ-API-001'], ['PRJ-API-002', 'PRJ-API-002'], ['UI-PRJ-001', 'UI-PRJ-001'], ['E2E-001', 'E2E-001']]


def test_template_example_goes_into_cases_prompt(app):
    app.generate()
    p = app.model.prompts_of('promptGenerate')[0]
    assert 'Образец тест-кейса. Повторяй точно его поля' in p and '[BE] POST /api/v1/password-reset — запрос ссылки для зарегистрированного email' in p


def test_broken_template_blocks_the_run_and_opens_settings(app):
    app.open_settings('tpl')
    app.page.fill('#cfg-example', '{')
    app.close_settings()
    app.page.click('#btn-run')
    assert 'Шаблон API: Пример тест-кейса — некорректный JSON' in app.text('#run-note')
    assert app.visible('#set-ov') and app.state('S.run') is None


def test_case_fields_follow_the_template_order(app):
    """Поля кейса идут в порядке шаблона, лишние поля модели — в конце."""
    def gen(call):
        res = cases_for(call.prompt)
        for c in res['cases']:
            c['testCase'] = {'лишнее': 'x', 'steps': [], 'title': 'Кейс', 'priority': 'High', 'id': ''}
        return res
    app.model.on('promptGenerate', gen)
    app.generate()
    keys = app.state("Object.keys(S.run.cases[0].testCase)")
    assert keys[:4] == ['id', 'title', 'priority', 'steps'] and keys[-1] == 'лишнее'
