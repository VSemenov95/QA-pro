"""Документы продукта и запуска: список сворачивается, пример ТЗ добавляется только в пустой продукт, запуск идёт по загруженным для него документам."""
import json

import pytest

from tests.support import files, model_kb

SAMPLE = 'Пример — ТЗ восстановление пароля.md'
OWN = 'правила.md'
OWN_TEXT = '# Правила\n## Роли\n- Оператор: видит заявки своей смены\n'


def names(app):
    return app.page.eval_on_selector_all('#doc-list .doc .doc-name', 'els => els.map((e) => e.textContent)')


def remove_all(app):
    """Убирает документы из продукта (в режиме запуска — сначала из запуска, потом из продукта в «Базе знаний»)."""
    app.mode('help')
    while app.count('#doc-list [data-doc-act=remove]'):
        btn = '#doc-list [data-doc-act=remove] >> nth=0'
        app.page.click(btn)
        if app.count('#doc-list [data-doc-act=remove].armed'):
            app.page.click('#doc-list [data-doc-act=remove].armed >> nth=0')
        app.page.wait_for_timeout(150)
    app.wait_idle()
    app.page.wait_for_function('() => window.__qa.S.docs.length === 0')


def sample_button(app):
    return app.state("!document.querySelector('#btn-sample').hidden")


def own_doc(tmp_path, name=OWN, text=OWN_TEXT):
    return files.write(tmp_path / name, text)


# ---------- кнопка «Добавить пример ТЗ» ----------
@pytest.mark.parametrize('mode', ['help', 'generate', 'update'])
def test_sample_button_is_hidden_while_the_product_has_documents(app, mode):
    app.mode(mode)
    assert sample_button(app) is False


@pytest.mark.parametrize('mode', ['help', 'generate'])
def test_sample_button_appears_in_an_empty_product(app, mode):
    remove_all(app)
    app.mode(mode)
    assert sample_button(app) is True


def test_own_document_hides_the_button_and_removing_it_brings_it_back(app, tmp_path):
    remove_all(app)
    app.mode('generate')
    app.upload(own_doc(tmp_path))
    assert sample_button(app) is False
    app.mode('help')
    remove_all(app)
    assert sample_button(app) is True


def test_button_adds_the_sample_once_and_hides_itself(app):
    remove_all(app)
    app.page.click('#btn-sample')
    app.page.wait_for_function('() => window.__qa.S.docs.length === 1')
    assert names(app) == [SAMPLE] and sample_button(app) is False and 'пример' in app.text('#doc-list')


def test_sample_added_by_button_is_kept_after_reload(app):
    remove_all(app)
    app.page.click('#btn-sample')
    app.page.wait_for_function("() => window.__qa.S.products.find((p) => p.id === window.__qa.S.productId).docs.length === 1")
    app.reload()
    app.mode('help')
    assert names(app) == [SAMPLE] and sample_button(app) is False


def test_standalone_button_follows_the_same_rule(make_app):
    app = make_app(kind='standalone')
    assert sample_button(app) is False
    remove_all(app)
    assert sample_button(app) is True


# ---------- сворачивание списка документов ----------
def fold_state(app):
    return app.page.evaluate("() => ({ expanded: document.querySelector('#docs-fold').getAttribute('aria-expanded'), bodyHidden: document.querySelector('#docs-body').hidden, sumHidden: document.querySelector('#docs-sum').hidden })")


def test_folding_hides_the_list_and_shows_a_summary(app):
    app.mode('help')
    app.page.click('#docs-fold')
    assert fold_state(app) == {'expanded': 'false', 'bodyHidden': True, 'sumHidden': False}
    summary = app.text('#docs-sum')
    assert 'Пример — ТЗ восстановление пароля' in summary and 'не разобрано 1' in summary and 'в базе знаний 0 из 1' in summary


def test_summary_shows_three_names_and_the_rest_as_count(app, tmp_path):
    app.mode('help')
    app.state('S.settings.kbAuto = false')
    app.upload(*[files.write(tmp_path / f'док{i}.md', f'# Док {i}\n- Факт {i}: значение {i}\n') for i in range(1, 5)])
    app.page.click('#docs-fold')
    assert 'и ещё 2' in app.text('#docs-sum .fold-sum-n')


def test_folded_empty_product_says_so(app):
    remove_all(app)
    app.page.click('#docs-fold')
    assert 'В продукте пока нет документов' in app.text('#docs-sum')


def test_fold_state_is_separate_for_each_mode(app):
    app.mode('help')
    app.page.click('#docs-fold')
    app.mode('generate')
    assert fold_state(app)['expanded'] == 'true'
    app.page.click('#docs-fold')
    assert fold_state(app)['expanded'] == 'false'
    app.mode('help')
    assert fold_state(app)['expanded'] == 'false'
    assert json.loads(app.js("localStorage.getItem('qapro.docsFold')")) == {'help': True, 'generate': True}


def test_fold_state_survives_reload(app):
    app.mode('help')
    app.page.click('#docs-fold')
    app.reload()
    assert fold_state(app)['expanded'] == 'false'


def test_summary_click_expands_and_moves_focus_to_the_header(app):
    app.mode('help')
    app.page.click('#docs-fold')
    app.page.click('#docs-sum .fold-sum')
    assert fold_state(app)['expanded'] == 'true' and app.state('document.activeElement.id') == 'docs-fold'


def test_plus_in_folded_panel_opens_file_chooser(app):
    app.mode('help')
    app.page.click('#docs-fold')
    with app.page.expect_file_chooser(timeout=5000) as fc:
        app.page.click('#docs-sum [data-docs-act=add]')
    assert fc.value.is_multiple()


def test_file_dropped_on_folded_panel_is_added(app):
    app.mode('help')
    app.state('S.settings.kbAuto = false')
    app.page.click('#docs-fold')
    app.js("""() => {
      const dt = new DataTransfer();
      dt.items.add(new File(['# Лимиты\\nНе более 3 запросов за 15 минут.'], 'limits.md', { type: 'text/markdown' }));
      const t = document.querySelector('#docs-sum .fold-sum');
      for (const type of ['dragenter', 'dragover', 'drop']) t.dispatchEvent(new DragEvent(type, { bubbles: true, cancelable: true, dataTransfer: dt }));
    }""")
    app.page.wait_for_function("() => window.__qa.S.docs.some((d) => d.name === 'limits.md' && d.status === 'ready')")
    assert fold_state(app)['expanded'] == 'false' and 'limits' in app.text('#docs-sum')


# ---------- документы запуска ----------
def test_run_list_shows_run_documents_without_selection(app):
    assert app.text('#h-docs-t') == 'Документы запуска' and names(app) == [SAMPLE]
    assert app.count('#doc-list input[type=checkbox]') == 0


def test_knowledge_base_mode_lists_all_product_documents(app, tmp_path):
    app.state('S.settings.kbAuto = false')
    app.mode('help')
    app.upload(own_doc(tmp_path))
    assert app.text('#h-docs-t') == 'Документы продукта' and names(app) == [SAMPLE, OWN]


def test_document_uploaded_in_knowledge_base_is_not_in_the_run(app, tmp_path):
    app.state('S.settings.kbAuto = false')
    app.mode('help')
    app.upload(own_doc(tmp_path))
    app.mode('generate')
    assert names(app) == [SAMPLE]
    assert app.state('S.products.find((p) => p.id === S.productId).docs.length') == 2   # но в продукте он есть


def test_run_note_points_to_the_knowledge_base(app):
    note = app.text('#docs-note')
    assert 'Генерация идёт по этим документам.' in note and 'База знаний продукта пока пуста' in note


def test_run_note_counts_sections_and_documents(app):
    model_kb.install(app.model)
    app.mode('help')
    app.page.click('[data-act=kb-run]')
    app.wait_idle()
    app.mode('generate')
    assert 'Остальное о продукте агент берёт из базы знаний: 2 раздела из 1 документа.' in app.text('#docs-note')
    assert app.visible('#docs-note [data-docs-act=kb]')


def test_link_in_the_note_opens_the_knowledge_base(app):
    model_kb.install(app.model)
    app.mode('help')
    app.page.click('[data-act=kb-run]')
    app.wait_idle()
    app.mode('generate')
    app.page.click('#docs-note [data-docs-act=kb]')
    assert app.state('S.settings.mode') == 'help' and app.visible('#help-view')


def test_cross_removes_a_document_from_the_run_only(app):
    app.page.click('#doc-list [data-doc-act=unrun]')
    assert names(app) == [] and app.state('S.docs.length') == 1
    assert app.page.is_disabled('#btn-run') and 'Загрузите ТЗ для этого запуска' in app.text('#run-note')
    app.mode('help')
    assert names(app) == [SAMPLE]   # из продукта документ не ушёл


def test_document_uploaded_in_generation_goes_to_run_and_product(app, tmp_path):
    app.state('S.settings.kbAuto = false')
    app.upload(own_doc(tmp_path))
    assert names(app) == [SAMPLE, OWN]
    app.page.wait_for_function("() => window.__qa.S.products.find((p) => p.id === window.__qa.S.productId).docs.length === 2")
    pid = app.state('S.productId')
    assert [m['name'] for m in app.db.get(f'products/{pid}')['docs']] == [SAMPLE, OWN]
    assert app.db.get(f'products/{pid}/docparts/' + app.state("S.docs.find((d) => d.name === '" + OWN + "').id") + '_0')['text'] == OWN_TEXT.strip()


def test_uploading_a_known_file_again_reuses_the_document(app, tmp_path):
    app.state('S.settings.kbAuto = false')
    app.mode('help')
    path = own_doc(tmp_path)
    app.upload(path)
    app.mode('generate')
    assert names(app) == [SAMPLE]
    app.page.set_input_files('#file-input', path)
    app.page.wait_for_function("() => window.__qa.S.docs.length === 2 && window.__qa.S.docs.every((d) => d.status === 'ready')")
    assert names(app) == [SAMPLE, OWN]   # копии нет, а имеющийся документ взят в запуск
    assert any('уже есть в продукте — беру его в запуск' in t for t in app.toast_texts())


def test_run_uses_only_run_documents_and_the_base(app, tmp_path):
    model_kb.install(app.model)
    app.mode('help')
    app.page.click('[data-act=kb-run]')
    app.wait_idle()
    app.upload(files.write(tmp_path / 'kb_extra.md', model_kb.limits_doc(3)))
    app.page.wait_for_function("() => Object.keys(window.__qa.S.kb.index.docs).length >= 2 && !window.__qa.S.kb.job.busy")
    app.wait_idle()
    app.mode('generate')
    app.model.reset()
    app.generate()
    assert app.state('S.run.docs.map((d) => d.name)') == [SAMPLE]
    analyze = app.model.prompts_of('promptAnalyze')
    assert analyze and all('kb_extra' not in p.split('## База знаний продукта')[0] for p in analyze)   # документ из базы не подставлен целиком
    assert all('## База знаний продукта — разделы по теме' in p and 'kb_extra' in p.split('## База знаний продукта')[1] for p in analyze)   # но его сведения пришли через базу знаний


def test_agent_tools_search_only_run_documents(app, tmp_path):
    app.state('S.settings.kbAuto = false')
    app.mode('help')
    app.upload(files.write(tmp_path / 'склад.md', '# Склад\nОстатки товара пересчитываются ночью, код операции STOCK-77.\n'))
    app.mode('generate')
    got = app.call("""(async () => {
      const t = a.makeTools(a.newRun(), 'generate'), s = t.find((x) => x.name === 'search_documents'), r = t.find((x) => x.name === 'read_document');
      let err = '';
      try { r.execute({ document: 'склад', offset: 0 }); } catch (e) { err = e.message; }
      return { outside: s.execute({ query: 'STOCK-77' }), inside: [...new Set(s.execute({ query: 'Забыли пароль' }).map((x) => x.document))], err };
    })()""")
    assert got['outside'] == 'Ничего не найдено. Попробуй другие слова.' and got['inside'] == [SAMPLE]
    assert got['err'] == f'Документ не найден. Доступные: {SAMPLE}'


def test_run_list_survives_reload(app, tmp_path):
    app.state('S.settings.kbAuto = false')
    app.upload(own_doc(tmp_path))
    app.page.click('#doc-list li:has-text("Пример") [data-doc-act=unrun]')
    app.page.wait_for_function("() => window.__qa.S.products.find((p) => p.id === window.__qa.S.productId).docs.length === 2")
    app.reload()
    assert names(app) == [OWN]


def test_update_mode_uses_the_same_run_documents(app):
    app.mode('update')
    assert app.text('#h-docs-t') == 'Документы запуска' and names(app) == [SAMPLE]


def test_new_run_starts_with_an_empty_document_list(app):
    app.generate()
    app.page.click('#btn-newses')
    app.page.wait_for_function('() => !window.__qa.S.run')
    assert names(app) == [] and app.state('S.docs.length') == 1   # документ остался в продукте
    app.page.wait_for_function("() => /Загрузите документы для нового запуска/.test(document.querySelector('#toasts').textContent)")
    assert 'Загрузите ТЗ для этого запуска' in app.text('#run-note') and app.page.is_disabled('#btn-run')


def test_deleting_a_document_from_the_product_removes_it_from_the_run(app, tmp_path):
    app.state('S.settings.kbAuto = false')
    app.upload(own_doc(tmp_path))
    app.mode('help')
    btn = f'#doc-list li:has-text("{OWN[:-3]}") [data-doc-act=remove]'
    app.page.click(btn)
    app.page.click(btn)
    app.page.wait_for_function("() => window.__qa.S.docs.length === 1")
    app.mode('generate')
    assert names(app) == [SAMPLE]
    pid = app.state('S.productId')
    app.page.wait_for_function("(pid) => window.__qa.S.products.find((p) => p.id === pid).docs.length === 1", arg=pid)
