"""Вкладка «Трассировка»: описание дефекта, необязательный стек трейса и пошаговый разбор агентом."""
DESC = 'Сохранение правила корреляции по времени выдаёт ошибку 500'
STACK = 'java.lang.ClassCastException: class java.lang.Integer cannot be cast to class java.lang.String'


def run_trace(app, desc=DESC, stack=''):
    app.tab('trace')
    app.page.fill('#trace-desc', desc)
    app.page.dispatch_event('#trace-desc', 'input')
    if stack:
        app.page.fill('#trace-stack', stack)
        app.page.dispatch_event('#trace-stack', 'input')
    app.page.click('[data-act=trace-run]')
    app.page.wait_for_selector('.trace-steps li', timeout=30000)


def test_trace_tab_is_in_the_work_area(app):
    assert app.page.is_visible('#tab-trace')


def test_run_is_disabled_without_description(app):
    app.tab('trace')
    assert app.page.is_disabled('[data-act=trace-run]')
    app.page.fill('#trace-desc', 'Ошибка при сохранении')
    app.page.dispatch_event('#trace-desc', 'input')
    assert not app.page.is_disabled('[data-act=trace-run]')


def test_trace_shows_steps_and_failure(app):
    run_trace(app)
    assert app.count('.trace-steps > li') == 2
    text = app.text('.trace-steps')
    assert 'Инициация действия' in text and 'Обработка на стороне сервиса' in text
    assert 'ClassCastException' in app.text('.exp-card:has-text("Место сбоя")')


def test_description_and_stack_go_into_the_prompt(app):
    run_trace(app, stack=STACK)
    prompt = app.model.prompts_of('promptTrace')[0]
    assert DESC in prompt and STACK in prompt


def test_stack_is_optional(app):
    run_trace(app)
    prompt = app.model.prompts_of('promptTrace')[0]
    assert DESC in prompt and 'не приложен' in prompt


def test_draft_survives_switching_tabs(app):
    app.tab('trace')
    app.page.fill('#trace-desc', DESC)
    app.page.dispatch_event('#trace-desc', 'input')
    app.tab('agent')
    app.tab('trace')
    assert app.page.input_value('#trace-desc') == DESC
