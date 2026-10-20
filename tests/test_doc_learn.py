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


def test_learn_buttons_stay_usable_while_another_document_is_learned(app, tmp_path):
    """Разобрать один документ — и сразу нажать «Разобрать» у другого: второй должен разобраться, а не остаться неактивным."""
    manual_learning(app)
    app.upload(files.write(tmp_path / 'Правила-скидок.md', '# Правила скидок\n\nСкидка до 15% для постоянных клиентов.'))
    app.upload(files.write(tmp_path / 'Журнал-заказов.md', '# Журнал заказов\n\nЗаказ создаётся кнопкой.'))
    app.page.click(f'{row("Правила-скидок.md")} [data-doc-act=learn]')
    app.page.click(f'{row("Журнал-заказов.md")} [data-doc-act=learn]', timeout=5000)
    app.wait_idle()
    names = learned_names(app)
    assert 'Правила-скидок.md' in names and 'Журнал-заказов.md' in names, names


def test_learn_while_other_work_is_running_queues_the_document(app, tmp_path):
    """Идёт другая работа с базой знаний (например, сборка сводок): кнопка активна, документ встаёт в очередь."""
    manual_learning(app)
    app.upload(files.write(tmp_path / 'Журнал-заказов.md', '# Журнал заказов\n\nЗаказ создаётся кнопкой.'))
    app.call('(() => { S.kb.job.busy = true; return true; })()')
    app.mode('generate')
    app.mode('help')
    assert not app.page.is_disabled(f'{row("Журнал-заказов.md")} [data-doc-act=learn]')
    app.page.click(f'{row("Журнал-заказов.md")} [data-doc-act=learn]')
    assert app.state("S.kb.queue.map((d) => d.name)") == ['Журнал-заказов.md']
    app.call('(() => { S.kb.job.busy = false; S.kb.queue = []; return true; })()')
