"""Обогащение базы знаний файлами: те же форматы, что и при генерации; файлы попадают в документы продукта и разбираются."""
from tests.support import files


def doc_names(app):
    return app.state('S.docs.map((d) => d.name)')


def sections(app):
    app.mode('help')
    app.page.click('[data-act=help-view][data-v=blocks]')


def test_kb_has_add_documents_button_in_sections(app):
    sections(app)
    assert app.page.is_visible('[data-act=kb-add-docs]')


def test_add_documents_button_opens_file_picker_with_same_formats(app):
    sections(app)
    assert app.page.get_attribute('#file-input', 'accept') == '.docx,.pdf,.txt,.md,.markdown,.xlsx,.xls,.csv,.json,.yaml,.yml'
    with app.page.expect_file_chooser() as chooser:
        app.page.click('[data-act=kb-add-docs]')
    assert chooser.value is not None


def test_uploaded_file_joins_product_documents(app, tmp_path):
    app.mode('help')
    before = app.state('S.docs.length')
    app.upload(files.write(tmp_path / 'Регламент-возвратов.md', '# Регламент возвратов\n\nВозврат в течение 14 дней.'))
    assert app.state('S.docs.length') == before + 1
    assert 'Регламент-возвратов.md' in doc_names(app)
    assert app.state("S.docs.find((d) => d.name === 'Регламент-возвратов.md').status") == 'ready'


def test_file_dropped_on_knowledge_base_is_added(app):
    sections(app)
    app.page.evaluate("""() => {
        const dt = new DataTransfer();
        dt.items.add(new File(['# Права ролей\\n\\nАдминистратор видит отчёты.'], 'Права-ролей.md', { type: 'text/markdown' }));
        document.querySelector('#kb-pane').dispatchEvent(new DragEvent('drop', { dataTransfer: dt, bubbles: true, cancelable: true }));
    }""")
    app.wait_docs()
    assert 'Права-ролей.md' in doc_names(app)


def test_help_text_no_longer_mentions_video(app):
    app.mode('help')
    assert 'mp4' not in app.page.inner_text('#docs-note') and 'Материалах' not in app.page.inner_text('#docs-note')
