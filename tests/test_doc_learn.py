"""Кнопка «Разобрать» у документа, который ещё не разобран по разделам базы знаний."""
from tests.support import files


def learned_names(app):
    return app.state("Object.keys(S.kb.index.docs || {}).map((id) => (S.docs.find((d) => d.id === id) || {}).name)")


def row(name):
    return f'li:has(.doc-name[title="{name}"])'


def manual_learning(app):
    """Автоматический разбор выключен — документы остаются не разобранными, пока их не разберут вручную."""
    app.mode('help')
    app.call('(() => { S.settings.kbAuto = false; return true; })()')


def test_not_learned_document_has_learn_button(app, tmp_path):
    manual_learning(app)
    app.upload(files.write(tmp_path / 'Правила-скидок.md', '# Правила скидок\n\nСкидка до 15% для постоянных клиентов.'))
    assert app.page.is_visible(f'{row("Правила-скидок.md")} [data-doc-act=learn]')


def test_learn_button_runs_only_that_document(app, tmp_path):
    manual_learning(app)
    app.upload(files.write(tmp_path / 'Правила-скидок.md', '# Правила скидок\n\nСкидка до 15% для постоянных клиентов.'))
    app.upload(files.write(tmp_path / 'Журнал-заказов.md', '# Журнал заказов\n\nЗаказ создаётся кнопкой.'))
    app.page.click(f'{row("Правила-скидок.md")} [data-doc-act=learn]')
    app.wait_idle()
    names = learned_names(app)
    assert 'Правила-скидок.md' in names and 'Журнал-заказов.md' not in names, names
    assert app.page.is_visible(f'{row("Журнал-заказов.md")} [data-doc-act=learn]')


def test_learned_document_has_no_learn_button(app, tmp_path):
    manual_learning(app)
    app.upload(files.write(tmp_path / 'Глоссарий.md', '# Глоссарий\n\nПродукт — кабинет клиента.'))
    app.page.click(f'{row("Глоссарий.md")} [data-doc-act=learn]')
    app.wait_idle()
    assert not app.page.is_visible(f'{row("Глоссарий.md")} [data-doc-act=learn]')
