"""Вкладка «Ревью», правила ревью, правила для агента и память агента (уроки из замечаний)."""
import pytest

from tests.support.model import ModelError
from tests.support.model_generation import generate_by_template, reviewer, wait_until

FINDINGS = {'API-001': ['critical'], 'UI-001': ['major'], 'CL-002': ['minor']}
AI_FINDINGS = "S.run.findings.filter((f) => f.source === 'ai')"


@pytest.fixture
def generated(app):
    """Кейсы по образцу шаблона (авто-проверки молчат), чек-лист из 4 пунктов, ревьюер ещё не запускался."""
    app.model.on('promptGenerate', generate_by_template).on('promptReviewCases', reviewer(FINDINGS)).on('promptReviewChecklist', reviewer(FINDINGS))
    app.add_sample()
    app.generate()
    return app


@pytest.fixture
def reviewed(generated):
    generated.tab('review')
    generated.page.click('[data-act=start-review]')
    generated.wait_idle()
    return generated


def finding_of(app, target):
    return app.page.locator(f'.fd:has(.fd-h button:text-is("{target}"))')


def open_findings(app):
    return app.state("S.run.findings.filter((f) => f.status === 'open').map((f) => [f.targetId, f.severity])")


# ---------- запуск ----------
def test_review_button_is_hidden_until_there_are_results(app):
    assert app.page.is_hidden('#btn-review')
    app.generate()
    assert app.page.is_visible('#btn-review') and not app.page.is_disabled('#btn-review')


def test_review_tab_offers_to_start_review(generated):
    generated.tab('review')
    assert generated.text('[data-act=start-review]') == 'Запустить ревью' and generated.count('.fd') == 0


def test_review_tab_before_generation_is_empty(app):
    app.tab('review')
    assert 'Ревью появится после генерации' in app.text('#tab-body')


def test_review_button_starts_review_and_opens_tab(generated):
    generated.page.click('#btn-review')
    generated.wait_idle()
    assert generated.state('S.tab') == 'review' and generated.count('.fd') == 3


def test_reviewer_gets_cases_by_type_and_checklist_separately(reviewed):
    assert sorted(len(c.prompt.split('## Кейсы на ревью')[-1].split('"type"')) - 1 for c in reviewed.model.calls_of('promptReviewCases')) == [1, 1, 2]
    assert len(reviewed.model.calls_of('promptReviewChecklist')) == 1


def test_findings_come_from_reviewer_for_cases_and_items(reviewed):
    got = reviewed.state(AI_FINDINGS + ".map((f) => [f.kind, f.targetId, f.severity, f.category])")
    assert sorted(got) == [['case', 'API-001', 'critical', 'Соответствие ТЗ'], ['case', 'UI-001', 'major', 'Соответствие ТЗ'], ['checklist', 'CL-002', 'minor', 'Соответствие ТЗ']]


def test_findings_are_sorted_by_severity(reviewed):
    sev = reviewed.page.eval_on_selector_all('.fd', 'els => els.map((e) => e.className.match(/sev-(\\w+)/)[1])')
    assert sev == ['critical', 'major', 'minor']


def test_finding_card_shows_text_target_and_suggestion(reviewed):
    card = reviewed.text('.fd:has(.fd-h button:text-is("API-001"))')
    assert 'Критичное' in card and 'Соответствие ТЗ' in card and 'должен быть код 202' in card and 'Указать код 202' in card
    assert 'Кейс для P-02' in card   # название кейса рядом с номером


def test_filter_counts(reviewed):
    chips = reviewed.page.eval_on_selector_all('.toolbar .fchip', "els => els.map((e) => e.innerText.replace(/\\s+/g, ' '))")
    assert chips == ['Открытые 3', 'Критичные 1', 'Существенные 1', 'Мелкие 1', 'Исправленные 0', 'Отклонённые 0', 'Все 3']


def test_tab_counter_is_number_of_open_findings(reviewed):
    assert reviewed.text('#tab-review .cnt') == '3'


def test_goto_finding_opens_the_case(reviewed):
    reviewed.page.click('.fd:has(.fd-h button:text-is("UI-001")) .fd-h button')
    assert reviewed.state('S.tab') == 'cases' and reviewed.count('#case-list .case-b') == 1


def test_clean_run_says_no_findings(generated):
    generated.model.on('promptReviewCases', {'findings': []}).on('promptReviewChecklist', {'findings': []})
    generated.tab('review')
    generated.page.click('[data-act=start-review]')
    generated.wait_idle()
    assert 'Замечаний нет' in generated.text('#tab-body')


def test_reviewer_error_is_reported_and_run_ends(generated):
    generated.model.on('promptReviewCases', ModelError('rate_limited'))
    generated.tab('review')
    generated.page.click('[data-act=start-review]')
    generated.wait_idle()
    assert generated.state('S.run.status') == 'error' and 'исчерпан лимит' in generated.state('S.run.error')


def test_findings_for_unknown_objects_are_ignored(generated):
    generated.model.on('promptReviewCases', {'findings': [{'targetId': 'API-777', 'severity': 'major', 'message': 'нет такого'}, {'targetId': 'API-001', 'message': ''}]})
    generated.model.on('promptReviewChecklist', {'findings': []})
    generated.tab('review')
    generated.page.click('[data-act=start-review]')
    generated.wait_idle()
    assert generated.state(AI_FINDINGS + '.length') == 0


@pytest.mark.parametrize('word,sev', [('Блокирующее', 'critical'), ('low', 'minor'), ('мелкое', 'minor'), ('что-то', 'major')])
def test_severity_words_are_normalized(generated, word, sev):
    generated.model.on('promptReviewCases', {'findings': [{'targetId': 'API-001', 'severity': word, 'message': 'Проблема'}]})
    generated.model.on('promptReviewChecklist', {'findings': []})
    generated.tab('review')
    generated.page.click('[data-act=start-review]')
    generated.wait_idle()
    assert generated.state(AI_FINDINGS + '.map((f) => f.severity)') == [sev]


# ---------- проверки без модели ----------
def test_review_finds_uncovered_requirement_without_model(generated):
    generated.model.on('promptReviewCases', {'findings': []}).on('promptReviewChecklist', {'findings': []})
    generated.tab('cases')
    generated.page.click('#case-list article:has(.case-id:text-is("E2E-001")) .case-h')
    generated.page.click('#case-list article:has(.case-id:text-is("E2E-001")) [data-act=del-case]')
    generated.page.click('#case-list article:has(.case-id:text-is("E2E-001")) [data-act=del-case]')
    generated.tab('review')
    generated.page.click('[data-act=start-review]')
    generated.wait_idle()
    f = generated.state("S.run.findings.map((f) => [f.kind, f.targetId, f.category, f.message, f.source])")
    assert ['req', 'R-003', 'Покрытие', 'Требование R-003 «Сквозное восстановление» не покрыто тест-кейсами.', 'auto'] in f


def test_review_warns_about_title_without_tag_after_manual_edit(generated):
    """Вручную правленые названия метка не поправляется, но ревью предупреждает."""
    generated.model.on('promptReviewCases', {'findings': []}).on('promptReviewChecklist', {'findings': []})
    generated.tab('cases')
    generated.page.click('#case-list article:has(.case-id:text-is("UI-001")) .case-h')
    generated.page.click('#case-list [data-act=form-case]')
    generated.page.fill('.case-form input[data-fp="title"]', 'Вход без метки')
    generated.page.click('[data-act=ff-save]')
    generated.tab('review')
    generated.page.click('[data-act=start-review]')
    generated.wait_idle()
    f = generated.state("S.run.findings.map((f) => [f.targetId, f.category, f.message])")
    assert f == [['UI-001', 'Название', 'В названии нет метки вида теста [FE].']]


def test_review_finds_missing_template_fields_without_model(app):
    app.model.on('promptReviewCases', {'findings': []}).on('promptReviewChecklist', {'findings': []})
    app.generate()
    app.tab('review')
    app.page.click('[data-act=start-review]')
    app.wait_idle()
    f = app.state("S.run.findings.filter((f) => f.category === 'Шаблон').map((f) => [f.targetId, f.severity, f.message])")
    assert ['UI-001', 'minor', 'Нет полей шаблона: testData.'] in f
    assert not any('request' in m for _, _, m in f), 'у API-шаблона нет блока request'


# ---------- действия над замечаниями ----------
def test_dismiss_marks_finding_with_reason(reviewed):
    card = finding_of(reviewed, 'API-001')
    card.locator('[data-act=fd-dismiss]').click()
    reviewed.page.fill('textarea[data-fd]', 'У нас коды ответа проверяются в отдельном наборе')
    reviewed.page.click('[data-act=fd-dismiss-ok]')
    assert reviewed.state("S.run.findings.find((f) => f.targetId === 'API-001').status") == 'dismissed'
    assert reviewed.state("S.run.findings.find((f) => f.targetId === 'API-001').reason") == 'У нас коды ответа проверяются в отдельном наборе'
    assert reviewed.text('#tab-review .cnt') == '2'


def test_dismiss_reason_becomes_a_review_rule(reviewed):
    reviewed.model.on('promptLesson', {'rule': 'Коды ответа в ожидаемом результате не придирайся', 'scope': 'review'})
    finding_of(reviewed, 'API-001').locator('[data-act=fd-dismiss]').click()
    reviewed.page.fill('textarea[data-fd]', 'У нас коды ответа проверяются в отдельном наборе')
    reviewed.page.click('[data-act=fd-dismiss-ok]')
    lessons = wait_until(reviewed, lambda: reviewed.db.children('lessons'))
    assert [(v['text'], v['scope'], v['source']) for v in lessons.values()] == [('Коды ответа в ожидаемом результате не придирайся', 'review', 'remark')]
    p = reviewed.model.prompts_of('promptLesson')[0]
    assert 'Это не ошибка: У нас коды ответа проверяются в отдельном наборе' in p


def test_dismiss_without_reason_makes_no_rule(reviewed):
    finding_of(reviewed, 'API-001').locator('[data-act=fd-dismiss]').click()
    reviewed.page.click('[data-act=fd-dismiss-ok]')
    assert reviewed.state("S.run.findings.find((f) => f.targetId === 'API-001').status") == 'dismissed'
    assert len(reviewed.model.calls_of('promptLesson')) == 0


def test_dismiss_can_be_cancelled(reviewed):
    finding_of(reviewed, 'API-001').locator('[data-act=fd-dismiss]').click()
    reviewed.page.click('[data-act=fd-dismiss-cancel]')
    assert reviewed.state("S.run.findings.find((f) => f.targetId === 'API-001').status") == 'open'


def test_dismissed_finding_does_not_come_back_after_full_review(reviewed):
    finding_of(reviewed, 'API-001').locator('[data-act=fd-dismiss]').click()
    reviewed.page.click('[data-act=fd-dismiss-ok]')
    reviewed.page.click('[data-act=start-review-full]')
    reviewed.wait_idle()
    assert sorted(open_findings(reviewed)) == [['CL-002', 'minor'], ['UI-001', 'major']]


def test_reopen_returns_dismissed_finding(reviewed):
    finding_of(reviewed, 'API-001').locator('[data-act=fd-dismiss]').click()
    reviewed.page.click('[data-act=fd-dismiss-ok]')
    reviewed.page.click('[data-act=fd-filter][data-f=dismissed]')
    reviewed.page.click('[data-act=fd-reopen]')
    assert reviewed.state("S.run.findings.find((f) => f.targetId === 'API-001').status") == 'open'


def test_fix_sends_reviewer_remark_to_refine(reviewed):
    finding_of(reviewed, 'API-001').locator('[data-act=fd-fix]').click()
    reviewed.wait_idle()
    p = reviewed.model.prompts_of('promptRefine')[0]
    assert 'Замечание ревьюера (критичное, Соответствие ТЗ): Ожидаемый результат не совпадает с п. 3.1' in p and 'Рекомендация: Указать код 202' in p
    assert reviewed.state("S.run.findings.find((f) => f.targetId === 'API-001').status") == 'fixed'
    assert reviewed.state("S.run.cases.find((c) => c.dispId === 'API-001').testCase.title") == '[BE] Доработанный кейс'


def test_fix_checklist_item_uses_item_refine(reviewed):
    finding_of(reviewed, 'CL-002').locator('[data-act=fd-fix]').click()
    reviewed.wait_idle()
    assert reviewed.state("S.run.checklist.groups[0].items[1].check") == 'Исправленный пункт с конкретным лимитом 3 запроса'
    assert 'Рекомендация: Указать код 202' in reviewed.model.prompts_of('promptRefineItem')[0]


def test_fix_all_closes_every_open_finding(reviewed):
    reviewed.page.click('[data-act=fd-fixall]')
    reviewed.wait_idle()
    assert open_findings(reviewed) == [] and reviewed.state("S.run.findings.filter((f) => f.status === 'fixed').length") == 3
    assert reviewed.page.is_disabled('[data-act=fd-fixall]')


def test_failed_fix_keeps_finding_open(reviewed):
    reviewed.model.on('promptRefine', ModelError('invalid_json'))
    finding_of(reviewed, 'API-001').locator('[data-act=fd-fix]').click()
    reviewed.wait_idle()
    assert ['API-001', 'critical'] in open_findings(reviewed)
    assert 'Не удалось исправить: 1' in ' '.join(reviewed.state('S.run.steps.fix.log.map((l) => l.text)'))


def test_finding_for_uncovered_requirement_writes_missing_cases(generated):
    generated.model.on('promptReviewCases', {'findings': []}).on('promptReviewChecklist', {'findings': []})
    generated.tab('cases')
    generated.page.click('#case-list article:has(.case-id:text-is("E2E-001")) .case-h')
    generated.page.click('#case-list article:has(.case-id:text-is("E2E-001")) [data-act=del-case]')
    generated.page.click('#case-list article:has(.case-id:text-is("E2E-001")) [data-act=del-case]')
    generated.tab('review')
    generated.page.click('[data-act=start-review]')
    generated.wait_idle()
    generated.page.click('.fd:has-text("R-003") [data-act=fd-fix]')
    generated.wait_idle()
    assert generated.state("S.run.cases.some((c) => c.requirementIds.includes('R-003'))") is True
    assert generated.state("S.run.findings.find((f) => f.targetId === 'R-003').status") == 'fixed'


# ---------- повторное ревью ----------
def test_repeat_review_skips_unchanged_objects(reviewed):
    before = len(reviewed.model.calls)
    reviewed.page.click('[data-act=start-review]')
    reviewed.wait_idle()
    assert [c.kind for c in reviewed.model.calls[before:]] == []
    assert 'Не менялись с прошлого ревью' in ' '.join(reviewed.state('S.run.steps.review.log.map((l) => l.text)'))
    assert len(open_findings(reviewed)) == 3   # замечания сохранились


def test_full_review_checks_everything_again(reviewed):
    before = len(reviewed.model.calls)
    reviewed.page.click('[data-act=start-review-full]')
    reviewed.wait_idle()
    kinds = sorted(c.kind for c in reviewed.model.calls[before:])
    assert kinds == ['promptReviewCases'] * 3 + ['promptReviewChecklist']


def test_review_of_changed_case_only(reviewed):
    reviewed.tab('cases')
    reviewed.page.click('#case-list article:has(.case-id:text-is("UI-001")) .case-h')
    reviewed.page.click('#case-list [data-act=form-case]')
    reviewed.page.fill('.case-form input[data-fp="title"]', '[FE] Изменённый кейс')
    reviewed.page.click('[data-act=ff-save]')
    before = len(reviewed.model.calls)
    reviewed.tab('review')
    reviewed.page.click('[data-act=start-review]')
    reviewed.wait_idle()
    new = reviewed.model.calls[before:]
    assert [c.kind for c in new] == ['promptReviewCases'] and '[FE] Изменённый кейс' in new[0].prompt


# ---------- правила ревью ----------
def open_review_rules(app):
    app.open_settings('review')


def test_default_review_rules_say_standard_criteria(reviewed):
    assert 'Не заданы — используй стандартные критерии ниже.' in reviewed.model.prompts_of('promptReviewCases')[0]


def test_team_review_rules_reach_the_reviewer(generated):
    open_review_rules(generated)
    generated.page.fill('#cfg-review', 'Каждый кейс проверяет одно требование')
    generated.close_settings()
    generated.tab('review')
    generated.page.click('[data-act=start-review]')
    generated.wait_idle()
    assert '## Правила ревью команды\nКаждый кейс проверяет одно требование' in generated.model.prompts_of('promptReviewCases')[0]
    assert 'Каждый кейс проверяет одно требование' in generated.model.prompts_of('promptReviewChecklist')[0]
    assert 'правила ревью: заданы командой' in generated.text('.exp-card')


def test_review_rules_are_loaded_from_md_file(app, tmp_path):
    p = tmp_path / 'rules.md'
    p.write_text('# Правила ревью\n- Каждый кейс — одно требование\n', encoding='utf-8')
    open_review_rules(app)
    app.page.set_input_files('#cfg-md', str(p))
    app.page.wait_for_function("() => document.querySelector('#cfg-review').value.includes('Каждый кейс')")
    assert app.page.input_value('#cfg-review') == '# Правила ревью\n- Каждый кейс — одно требование'
    assert 'Правила ревью загружены из rules.md' in ' '.join(app.toast_texts())
    assert app.count('#settab-review .dot-d') == 1   # есть несохранённые изменения


def test_too_large_rules_file_is_refused(app, tmp_path):
    p = tmp_path / 'big.md'
    p.write_text('правило\n' * 60000, encoding='utf-8')
    open_review_rules(app)
    app.page.set_input_files('#cfg-md', str(p))
    app.page.wait_for_function("() => [...document.querySelectorAll('.toast')].some((e) => e.textContent.includes('слишком большой'))")
    assert app.page.input_value('#cfg-review') == ''


def test_review_rules_are_saved_for_the_team(app):
    open_review_rules(app)
    app.page.fill('#cfg-review', 'Негативные кейсы — с кодом ошибки из ТЗ')
    app.page.click('#cfg-foot [data-cfg=save]')
    wait_until(app, lambda: app.db.get('config/review'))
    assert app.db.get('config/review')['text'] == 'Негативные кейсы — с кодом ошибки из ТЗ'
    assert app.count('#settab-review .dot-d') == 0 and 'Версия команды' in app.text('#cfg-foot')


def test_unsaved_review_rules_can_be_reverted(app):
    open_review_rules(app)
    app.page.fill('#cfg-review', 'Временное правило')
    app.page.click('#cfg-foot [data-cfg=revert]')
    assert app.page.input_value('#cfg-review') == '' and app.state('S.cfg.reviewRules') == ''


def test_team_review_rules_are_restored_after_reload(app):
    open_review_rules(app)
    app.page.fill('#cfg-review', 'Правило команды')
    app.page.click('#cfg-foot [data-cfg=save]')
    wait_until(app, lambda: app.db.get('config/review'))
    app.reload()
    assert app.state('S.cfg.reviewRules') == 'Правило команды'


# ---------- память агента ----------
def add_lesson(app, text, scope='generation'):
    app.page.fill('#lesson-new', text)
    app.page.select_option('#lesson-scope', scope)
    app.page.click('[data-cfg=lesson-add]')


def test_lesson_is_added_to_memory_and_shared(app):
    open_review_rules(app)
    add_lesson(app, 'Всегда указывай код ответа', 'both')
    lessons = wait_until(app, lambda: app.db.children('lessons'))
    assert [(v['text'], v['scope'], v['source']) for v in lessons.values()] == [('Всегда указывай код ответа', 'both', 'manual')]
    app.page.wait_for_function("() => document.querySelector('.lessons')?.textContent.includes('Всегда указывай код ответа')")
    assert 'генерация и ревью' in app.text('.lessons') and 'Память агента · 1' in app.text('#cfg-body')
    assert app.page.input_value('#lesson-new') == ''


def test_duplicate_lesson_is_refused(app):
    open_review_rules(app)
    add_lesson(app, 'Всегда указывай код ответа')
    app.page.wait_for_function("() => window.__qa.S.lessons.length === 1")
    add_lesson(app, '  всегда   указывай КОД ответа! ')
    assert 'Такое правило уже есть.' in ' '.join(app.toast_texts())
    assert len(app.db.children('lessons')) == 1


def test_empty_lesson_is_ignored(app):
    open_review_rules(app)
    add_lesson(app, '   ')
    assert app.db.children('lessons') == {} and app.state('S.lessons.length') == 0


def test_lesson_is_cut_to_400_characters(app):
    open_review_rules(app)
    add_lesson(app, 'я' * 500)
    lessons = wait_until(app, lambda: app.db.children('lessons'))
    assert [len(v['text']) for v in lessons.values()] == [400]


def test_lesson_can_be_deleted(app):
    open_review_rules(app)
    add_lesson(app, 'Всегда указывай код ответа')
    app.page.wait_for_selector('.lessons [data-cfg=lesson-del]')
    app.page.click('.lessons [data-cfg=lesson-del]')
    wait_until(app, lambda: app.db.children('lessons') == {})
    assert app.state('S.lessons.length') == 0 and 'Пока пусто' in app.text('.lessons')


@pytest.mark.parametrize('scope,in_gen,in_rev', [('generation', True, False), ('review', False, True), ('both', True, True)])
def test_lesson_scope_decides_which_prompts_get_it(app, scope, in_gen, in_rev):
    open_review_rules(app)
    add_lesson(app, 'Метка правила ЯЯЯ', scope)
    app.page.wait_for_function("() => window.__qa.S.lessons.length === 1")
    app.close_settings()
    app.generate()
    app.tab('review')
    app.page.click('[data-act=start-review]')
    app.wait_idle()
    gen = app.model.prompts_of('promptGenerate')[0]
    rev = app.model.prompts_of('promptReviewCases')[0]
    assert ('Метка правила ЯЯЯ' in gen) is in_gen and ('Метка правила ЯЯЯ' in rev) is in_rev
    if in_gen:
        assert '## Правила из замечаний команды — соблюдай обязательно' in gen


def test_new_review_rule_makes_repeat_review_check_everything(reviewed):
    reviewed.open_settings('review')
    add_lesson(reviewed, 'Не придирайся к тексту сообщений', 'review')
    reviewed.page.wait_for_function("() => window.__qa.S.lessons.length === 1")
    reviewed.close_settings()
    before = len(reviewed.model.calls)
    reviewed.tab('review')
    reviewed.page.click('[data-act=start-review]')
    reviewed.wait_idle()
    assert sorted(c.kind for c in reviewed.model.calls[before:]) == ['promptReviewCases'] * 3 + ['promptReviewChecklist']


def test_generation_rule_does_not_reset_review_cache(reviewed):
    reviewed.open_settings('review')
    add_lesson(reviewed, 'Пиши шаги короче', 'generation')
    reviewed.page.wait_for_function("() => window.__qa.S.lessons.length === 1")
    reviewed.close_settings()
    before = len(reviewed.model.calls)
    reviewed.tab('review')
    reviewed.page.click('[data-act=start-review]')
    reviewed.wait_idle()
    assert len(reviewed.model.calls) == before


def test_failed_generalization_does_not_break_refine(generated):
    generated.model.on('promptLesson', ModelError('rate_limited'))
    generated.tab('cases')
    generated.page.click('#case-list article:has(.case-id:text-is("API-001")) .case-h')
    generated.page.click('#case-list [data-act=refine-case]')
    generated.page.fill('textarea[data-field=comment]', 'Укажи код ответа в ожидаемом результате')
    generated.page.click('[data-act=do-refine]')
    generated.page.wait_for_selector('.case-note:has-text("Кейс доработан.")')
    for _ in range(100):   # урок учится в фоне: ждём запроса к модели, а не таймаута
        if generated.model.calls_of('promptLesson'):
            break
        generated.page.wait_for_timeout(100)
    assert len(generated.model.calls_of('promptLesson')) == 1 and generated.db.children('lessons') == {}


def test_prompt_gets_only_the_last_sixty_rules(make_app):
    from tests.support.db import MemoryDB
    db = MemoryDB()
    for i in range(70):
        db.op('set', f'lessons/l{i:02d}', {'text': f'Правило номер {i:02d}', 'scope': 'generation', 'source': 'manual', 'createdAt': 1000 + i, 'by': 'u_test'})
    app = make_app(db=db)
    app.page.wait_for_function("() => window.__qa.S.lessons.length === 70")
    app.generate()
    p = app.model.prompts_of('promptGenerate')[0]
    assert 'Правило номер 69' in p and 'Правило номер 10' in p and 'Правило номер 09' not in p


# ---------- правила для агента ----------
def test_agent_rules_reach_planning_and_cases(app):
    app.page.fill('#cfg-rules', 'Больше негативных проверок')
    app.generate()
    for kind in ('promptAnalyze', 'promptChecklist', 'promptPlan', 'promptGenerate'):
        assert 'Больше негативных проверок' in app.model.prompts_of(kind)[0], kind


def test_agent_rules_show_unsaved_mark_and_save_for_team(app):
    app.page.fill('#cfg-rules', 'Больше негативных проверок')
    assert app.page.is_visible('#h-rules-dot')
    app.page.click('#rules-foot [data-cfg=save]')
    wait_until(app, lambda: app.db.get('config/rules'))
    assert app.db.get('config/rules')['text'] == 'Больше негативных проверок' and app.page.is_hidden('#h-rules-dot')
