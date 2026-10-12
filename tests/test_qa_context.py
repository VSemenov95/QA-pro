"""Дополнительный контекст от QA: общий и по видам тестов (API, UI, E2E). Что попадает в запросы к модели и как сохраняется."""
import pytest

from tests.support import files, model_draft as md

TEXT = {'all': 'ОКРУЖЕНИЕ-STAGE роль Оператор', 'api': 'БАЗОВЫЙ-URL-API https://stage/api', 'ui': 'ЭКРАН-ПРОФИЛЬ Главная → Настройки', 'e2e': 'ПИСЬМА-В-ЯЩИК test@example.ru'}
BLOCK = 'Дополнительный контекст от QA'


def set_ctx(app, **kw):
    """Заполняет вкладки контекста как пользователь: set_ctx(app, all='…', ui='…')."""
    for k, v in kw.items():
        app.page.click(f'[data-ctx={k}]')
        app.page.fill('#qa-ctx', v)


def full(app):
    set_ctx(app, **TEXT)
    return app


def marks(prompt):
    """Какие из контекстов видны в запросе: ['all', 'ui']."""
    return [k for k, v in TEXT.items() if v in prompt]


def gen_type(prompt):
    return 'api' if 'вида API' in prompt else 'ui' if 'вида UI' in prompt else 'e2e'


def log(app):
    return app.state('S.run.steps.parse.log.map((l) => l.text)')


# ---------- поле контекста ----------
def test_empty_note(app):
    assert app.text('#qa-ctx-note') == 'Пусто — агент опирается только на загруженные документы.'


def test_four_tabs(app):
    assert app.page.eval_on_selector_all('#qa-ctx-tabs button', 'bs => bs.map((b) => b.textContent.replace("•", ""))') == ['Для всех', 'API', 'UI', 'E2E']


def test_all_tab_is_open_first(app):
    assert app.page.get_attribute('[data-ctx=all]', 'aria-pressed') == 'true'


def test_note_lists_filled_tabs(app):
    set_ctx(app, all=TEXT['all'], ui=TEXT['ui'])
    assert app.text('#qa-ctx-note') == 'Учитывается при генерации: для всех, UI. Контекст «для всех» получают все виды тестов, остальное — только свой вид.'


def test_filled_tabs_are_marked(app):
    set_ctx(app, all=TEXT['all'], ui=TEXT['ui'])
    assert [app.count(f'[data-ctx={k}] .dot-d') for k in ('all', 'api', 'ui', 'e2e')] == [1, 0, 1, 0]


def test_each_tab_keeps_its_own_text(app):
    full(app)
    for k, v in TEXT.items():
        app.page.click(f'[data-ctx={k}]')
        assert app.page.input_value('#qa-ctx') == v


def test_tabs_have_different_hints(app):
    hints = []
    for k in TEXT:
        app.page.click(f'[data-ctx={k}]')
        hints.append(app.page.get_attribute('#qa-ctx', 'placeholder'))
    assert len(set(hints)) == 4 and all(hints)


def test_whitespace_only_text_is_empty(app):
    set_ctx(app, all='   \n  ')
    assert app.text('#qa-ctx-note').startswith('Пусто') and app.count('[data-ctx=all] .dot-d') == 0


def test_clearing_all_tabs_returns_to_empty_note(app):
    full(app)
    set_ctx(app, **{k: '' for k in TEXT})
    assert app.text('#qa-ctx-note').startswith('Пусто')


@pytest.mark.parametrize('mode,shown', [('generate', True), ('update', True), ('help', False)])
def test_context_is_shown_only_for_generation_and_update(app, mode, shown):
    app.mode(mode)
    assert app.visible('#qa-ctx-box') is shown


# ---------- что получает модель ----------
@pytest.fixture
def generated(app):
    full(app)
    app.generate()
    assert app.state('S.run.status') == 'done'
    return app


def test_generation_prompt_has_general_and_own_type_context_only(generated):
    got = {gen_type(p): marks(p) for p in generated.model.prompts_of('promptGenerate')}
    assert got == {'api': ['all', 'api'], 'ui': ['all', 'ui'], 'e2e': ['all', 'e2e']}


@pytest.mark.parametrize('kind', ['promptAnalyze', 'promptChecklist', 'promptPlan'])
def test_prompts_for_all_types_have_every_context(generated, kind):
    prompts = generated.model.prompts_of(kind)
    assert prompts and all(marks(p) == ['all', 'api', 'ui', 'e2e'] for p in prompts)


def test_context_block_has_labels(generated):
    p = next(p for p in generated.model.prompts_of('promptGenerate') if gen_type(p) == 'ui')
    assert 'Для всех видов тестов:\n' + TEXT['all'] in p and 'Для UI-тестов:\n' + TEXT['ui'] in p


def test_only_general_context_reaches_every_type(app):
    set_ctx(app, all=TEXT['all'])
    app.generate()
    assert all(marks(p) == ['all'] for p in app.model.prompts_of('promptGenerate'))


def test_only_ui_context_does_not_reach_api_and_e2e(app):
    set_ctx(app, ui=TEXT['ui'])
    app.generate()
    got = {gen_type(p): marks(p) for p in app.model.prompts_of('promptGenerate')}
    assert got == {'api': [], 'ui': ['ui'], 'e2e': []}
    assert BLOCK not in next(p for p in app.model.prompts_of('promptGenerate') if gen_type(p) == 'api')


def test_empty_context_adds_no_block_to_any_prompt(app):
    app.generate()
    assert not [c.kind for c in app.model.calls if BLOCK in c.prompt]


def test_cleared_context_adds_no_block(app):
    full(app)
    set_ctx(app, **{k: '' for k in TEXT})
    app.generate()
    assert not [c.kind for c in app.model.calls if BLOCK in c.prompt or any(v in c.prompt for v in TEXT.values())]


def test_whitespace_context_adds_no_block(app):
    set_ctx(app, all='  ', api='\n')
    app.generate()
    assert not [c.kind for c in app.model.calls if BLOCK in c.prompt]


def test_passport_request_gets_context(generated):
    p = generated.model.prompts_of('promptPassportFull', 'promptPassportDelta')
    assert p and marks(p[0]) == ['all', 'api', 'ui', 'e2e']


def test_log_names_filled_contexts(app):
    set_ctx(app, all=TEXT['all'], ui=TEXT['ui'])
    app.generate()
    assert 'Доп. контекст от QA: для всех, UI' in log(app)


def test_log_says_when_context_is_empty(app):
    app.generate()
    assert 'Доп. контекста от QA нет — работаю только по документам' in log(app)


def test_run_remembers_context(generated):
    assert generated.state('S.run.qaCtx') == TEXT


def test_review_gets_context_of_its_type(generated):
    generated.model.reset()
    generated.page.click('#btn-review')
    generated.wait_idle()
    got = {}
    for p in generated.model.prompts_of('promptReviewCases'):
        got[md.reviewed_ids(p)[0].split('-')[0]] = marks(p)
    assert got == {'API': ['all', 'api'], 'UI': ['all', 'ui'], 'E2E': ['all', 'e2e']}


def test_review_tells_not_to_treat_context_as_invention(generated):
    generated.model.reset()
    generated.page.click('#btn-review')
    generated.wait_idle()
    assert all('не считай ошибкой или выдумкой' in p for p in generated.model.prompts_of('promptReviewCases'))


def test_checklist_review_gets_every_context(generated):
    generated.model.reset()
    generated.page.click('#btn-review')
    generated.wait_idle()
    prompts = generated.model.prompts_of('promptReviewChecklist')
    assert prompts and marks(prompts[0]) == ['all', 'api', 'ui', 'e2e']


def test_context_edited_after_generation_is_used_by_review(generated):
    set_ctx(generated, ui='НОВЫЙ-КОНТЕКСТ-UI')
    generated.model.reset()
    generated.page.click('#btn-review')
    generated.wait_idle()
    ui = next(p for p in generated.model.prompts_of('promptReviewCases') if 'UI-001' in md.reviewed_ids(p))
    assert 'НОВЫЙ-КОНТЕКСТ-UI' in ui and TEXT['ui'] not in ui


def test_refine_gets_context_of_the_case_type(app):
    full(app)
    md.make_draft(app, review=md.review({'UI-001': ['major']}))
    app.page.click('[data-act=draft-review]')
    app.wait_idle()
    app.model.reset()
    app.page.click('.draft-case:has(.mono:text-is("UI-001")) [data-act=draft-fix]')
    app.wait_idle()
    assert marks(app.model.prompts_of('promptRefine')[0]) == ['all', 'ui']


def test_update_mode_sends_context_to_map_and_actualize(app, tmp_path):
    full(app)
    app.mode('update')
    app.upload_tests(files.cases_json(tmp_path))
    app.upload(files.spec_file(tmp_path, version='2.0'))
    app.generate()
    assert all(marks(p) == ['all', 'api', 'ui', 'e2e'] for p in app.model.prompts_of('promptMap'))
    by = {}
    for p in app.model.prompts_of('promptActualize'):
        if 'POST /api/v1/password-reset — проверка' in p:
            by['api'] = marks(p)
        elif 'Экран восстановления' in p:
            by['ui'] = marks(p)
    assert by == {'api': ['all', 'api'], 'ui': ['all', 'ui']}


# ---------- сохранение ----------
def saved_ctx(app):
    return (app.db.get(f'products/{app.state("S.productId")}') or {}).get('qaCtx') or {}


def test_context_is_saved_in_product(app):
    set_ctx(app, api=TEXT['api'])
    md.wait_db(app, lambda db: saved_ctx(app).get('api') == TEXT['api'], 'контекст сохранён в продукте')


def test_context_survives_reload(app):
    full(app)
    md.wait_db(app, lambda db: saved_ctx(app).get('e2e') == TEXT['e2e'], 'контекст сохранён в продукте')
    app.reload()
    app.page.click('[data-ctx=api]')
    assert app.page.input_value('#qa-ctx') == TEXT['api']
    assert app.text('#qa-ctx-note').startswith('Учитывается при генерации: для всех, API, UI, E2E')


def test_context_is_shared_with_teammate(app, make_app):
    full(app)
    md.wait_db(app, lambda db: saved_ctx(app).get('ui') == TEXT['ui'], 'контекст сохранён в продукте')
    mate = make_app(db=app.db)
    mate.page.click('[data-ctx=ui]')
    assert mate.page.input_value('#qa-ctx') == TEXT['ui']


def test_context_belongs_to_product(app):
    set_ctx(app, all=TEXT['all'])
    md.wait_db(app, lambda db: saved_ctx(app).get('all') == TEXT['all'], 'контекст сохранён в продукте')
    first = app.state('S.productId')
    app.create_product('Второй продукт')
    app.page.click('[data-ctx=all]')
    assert app.page.input_value('#qa-ctx') == '' and app.text('#qa-ctx-note').startswith('Пусто')
    app.page.select_option('#prod-select', first)
    app.page.wait_for_function('(p) => window.__qa.S.productId === p', arg=first)
    app.page.click('[data-ctx=all]')
    assert app.page.input_value('#qa-ctx') == TEXT['all']


def test_unsaved_context_is_saved_when_switching_product(app):
    """Не дожидаясь задержки сохранения, пользователь создаёт другой продукт — контекст первого не теряется."""
    first = app.state('S.productId')
    set_ctx(app, all=TEXT['all'])
    app.create_product('Второй продукт')
    assert (app.db.get(f'products/{first}') or {}).get('qaCtx', {}).get('all') == TEXT['all']


def test_standalone_context_survives_reload(make_app):
    app = make_app(kind='standalone')
    set_ctx(app, api='Базовый URL https://stage/api')
    app.page.wait_for_function('() => !window.__qa.S.ctxDirty', timeout=10000)
    app.reload()
    app.page.click('[data-ctx=api]')
    assert app.page.input_value('#qa-ctx') == 'Базовый URL https://stage/api'
    assert app.text('#qa-ctx-tabs').replace('\n', ' ').replace('•', '').split() == ['Для', 'всех', 'API', 'UI', 'E2E'] and app.count('[data-ctx=api] .dot-d') == 1
