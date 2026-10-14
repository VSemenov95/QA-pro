"""«Новый запуск» остаётся в шапке во всех режимах: в «Базе знаний» он неактивен, а не скрыт."""


def test_new_run_is_visible_but_disabled_in_knowledge_base(app):
    app.mode('help')
    assert app.page.is_visible('#btn-newses') and app.page.is_disabled('#btn-newses')


def test_new_run_is_enabled_in_generation_and_update(app):
    app.mode('generate')
    assert app.page.is_visible('#btn-newses') and not app.page.is_disabled('#btn-newses')
    app.mode('update')
    assert app.page.is_visible('#btn-newses') and not app.page.is_disabled('#btn-newses')
