"""База знаний при подключённой папке: папка — единственный источник.

Разделы — файлы products/<папка>/kb/*.md и knowledge/*.md; вкладка «База знаний», вопросы, генерация и поиск агента берут их;
разбор новых документов пишет разделы в файлы (служебный блок <!-- qa-pro:kb … --> с выдержками), отметки о разобранных
документах — products/<папка>/qa-pro-docs.json; в хранилище QA pro разделы не пишутся.
"""
import json

import pytest

from tests.support import model_kb
from tests.test_context_source import REPO, connect, init, repo, wait_repo
from tests.test_knowledge_base import ROWS, TITLES, parse_sample


def kb_files(app):
    return {k: v for k, v in repo(app).items() if k.startswith('products/moi/kb/')}


def db_kb(app):
    pid = app.state('S.productId')
    return [k for k in app.db.store if k.startswith(f'products/{pid}/kb/')]


@pytest.fixture
def kbapp(make_app):
    app = make_app(init=init())
    model_kb.install(app.model)
    connect(app)
    app.close_settings()
    app.mode('help')
    return app


# ---------- оглавление и вопросы ----------
def test_knowledge_tab_shows_folder_sections(kbapp):
    kbapp.page.wait_for_function("() => document.querySelectorAll('#kb-rows .kb-row').length === 2")
    assert sorted(kbapp.page.evaluate('() => ' + TITLES)) == ['Восстановление пароля', 'Глоссарий']


def test_section_opens_with_folder_text(kbapp):
    kbapp.page.click('#kb-rows .kb-row:has-text("Восстановление пароля")')
    kbapp.page.wait_for_selector('.kb-art h3')
    assert 'ЗНАНИЕ-ИЗ-РЕПО' in kbapp.text('.kb-art')


def test_questions_use_folder_sections(kbapp):
    from tests.test_help_qa import ask
    kbapp.page.click('[data-act=help-view][data-v=qa]')
    ask(kbapp, 'Сколько действует ссылка на восстановление пароля?', 1)
    prompts = kbapp.model.prompts_of('promptHelp')
    assert prompts and 'ЗНАНИЕ-ИЗ-РЕПО' in prompts[-1]


def test_only_folder_sections_are_used_not_qa_pro_storage(make_app):
    app = make_app()
    model_kb.install(app.model)
    app.mode('help')
    parse_sample(app)   # база знаний в хранилище QA pro: два раздела из примера ТЗ
    stored = sorted(app.page.evaluate('() => ' + TITLES))
    app.ctx.add_init_script(script=init())
    app.reload()
    connect(app)
    app.close_settings()
    titles = sorted(app.call('a.kbSections(S.productId).map((x) => x.b.title)'))
    assert titles == ['Восстановление пароля', 'Глоссарий'] and titles != stored


# ---------- разбор документов пишет файлы ----------
def test_parsing_documents_writes_sections_into_folder(kbapp):
    before = set(kb_files(kbapp))
    kbapp.page.click('[data-act=kb-run]')
    kbapp.wait_idle()
    kbapp.page.wait_for_function('() => !window.__qa.S.ctx.pending.size', timeout=15000)
    new = {k: v for k, v in kb_files(kbapp).items() if k not in before}
    assert new and all('<!-- qa-pro:kb' in v for v in new.values())
    assert db_kb(kbapp) == []   # в хранилище QA pro разделы не пишутся
    docs = json.loads(repo(kbapp, 'products/moi/qa-pro-docs.json'))
    sample = kbapp.state('S.docs.find((d) => d.sample).id')
    assert sample in docs and docs[sample]['hash']


def test_parsed_section_keeps_excerpts_and_summary(kbapp):
    kbapp.page.click('[data-act=kb-run]')
    kbapp.wait_idle()
    kbapp.page.wait_for_function('() => !window.__qa.S.ctx.pending.size', timeout=15000)
    path, text = next((k, v) for k, v in kb_files(kbapp).items() if '<!-- qa-pro:kb' in v)
    d = kbapp.call('a.ctxKbParse(arg[0], arg[1]).d', [path, text])
    assert d['parts'] and d['parts'][0]['docId'] and d.get('synth')
    assert text.startswith('# ' + d['title'])


def test_human_section_survives_and_is_not_duplicated(kbapp):
    kbapp.page.click('[data-act=kb-run]')
    kbapp.wait_idle()
    titles = kbapp.page.evaluate('() => ' + TITLES)
    assert titles.count('Восстановление пароля') == 1   # раздел человека дополнен, а не продублирован
    kbapp.page.wait_for_function('() => !window.__qa.S.ctx.pending.size', timeout=15000)
    f = repo(kbapp, 'products/moi/kb/vosstanovlenie.md')
    assert '<!-- qa-pro:kb' in f and '"human":true' in f   # тот же файл, теперь с выдержками из ТЗ
    synth = [c.prompt for c in kbapp.model.calls if c.kind.startswith('promptKbSynth')]
    assert any('ЗНАНИЕ-ИЗ-РЕПО' in p for p in synth)   # текст человека ушёл в сводку как прежняя версия


def test_document_is_not_parsed_twice_after_reload(kbapp):
    kbapp.page.click('[data-act=kb-run]')
    kbapp.wait_idle()
    kbapp.page.wait_for_function('() => !window.__qa.S.ctx.pending.size', timeout=15000)
    n = len(kbapp.model.calls)
    keep = repo(kbapp)   # «папка» живёт в памяти страницы — переносим её через перезагрузку
    kbapp.ctx.add_init_script(script='window.__repo.files = ' + json.dumps(keep, ensure_ascii=False) + ';')
    kbapp.reload()
    kbapp.page.wait_for_function('() => window.__qa.S.ctx.on && !window.__qa.S.ctx.busy && window.__qa.S.kb.index.blocks.length > 2', timeout=20000)
    kbapp.wait_idle()
    assert kbapp.state('a.S.kb.index.docs && Object.keys(S.kb.index.docs).length') >= 1
    assert not any(c.kind.startswith('promptKb') for c in kbapp.model.calls[n:])


# ---------- правка и удаление раздела ----------
def test_section_edit_writes_the_file(kbapp):
    rid = kbapp.state('S.kb.index.blocks.find((b) => b.title === "Глоссарий").id')
    kbapp.call('a.kbSave(S.productId, arg, (cur) => ({ ...cur, synth: "ЛК — личный кабинет. ПРАВКА-ИЗ-QA-PRO." }))', rid)
    text = wait_repo(kbapp, 'knowledge/glossary.md', 'ПРАВКА-ИЗ-QA-PRO')
    assert text.startswith('# Глоссарий') and 'qa-pro:kb' in text


def test_section_delete_removes_the_file(kbapp):
    rid = kbapp.state('S.kb.index.blocks.find((b) => b.title === "Глоссарий").id')
    kbapp.call('a.kbSave(S.productId, arg, () => null)', rid)
    kbapp.page.wait_for_function('() => !("knowledge/glossary.md" in window.__repo.files)', timeout=8000)
    assert 'Глоссарий' not in kbapp.state('S.kb.index.blocks.map((b) => b.title)')


def test_human_edit_in_file_becomes_section_text(kbapp):
    kbapp.page.click('[data-act=kb-run]')
    kbapp.wait_idle()
    kbapp.page.wait_for_function('() => !window.__qa.S.ctx.pending.size', timeout=15000)
    path, text = next((k, v) for k, v in kb_files(kbapp).items() if '<!-- qa-pro:kb' in v and 'bodyIsSynth":true' in v)
    head, meta = text.split('<!-- qa-pro:kb', 1)
    edited = head.split('\n\n', 1)[0] + '\n\nТЕКСТ-ПОПРАВИЛ-ЧЕЛОВЕК\n\n<!-- qa-pro:kb' + meta
    kbapp.page.evaluate('([p, t]) => { window.__repo.files[p] = t; }', [path, edited])
    kbapp.open_settings('ctx')
    kbapp.page.click('[data-ctx-act=refresh]')
    kbapp.page.wait_for_function('() => !window.__qa.S.ctx.busy', timeout=10000)
    texts = kbapp.call('a.kbSections(S.productId).map((x) => x.d.synth || "").join(" ")')
    assert 'ТЕКСТ-ПОПРАВИЛ-ЧЕЛОВЕК' in texts


# ---------- выгрузка и отключение ----------
def test_export_moves_qa_pro_knowledge_base_into_files(make_app):
    app = make_app(init=init(files={}))
    model_kb.install(app.model)
    app.mode('help')
    parse_sample(app)
    stored = sorted(app.page.evaluate('() => ' + TITLES))
    connect(app)
    assert app.state('S.kb.index.blocks.length') == 0   # папка пуста — и база знаний пуста
    app.page.click('[data-ctx-act=export]')
    app.page.wait_for_selector('[data-ctx-act=export-run]')
    app.page.click('[data-ctx-act=export-run]')
    app.page.wait_for_function('() => !window.__qa.S.ctx.pending.size && window.__qa.S.kb.index.blocks.length === 2', timeout=15000)
    assert sorted(app.state('S.kb.index.blocks.map((b) => b.title)')) == stored
    assert all('<!-- qa-pro:kb' in v for v in kb_files(app).values()) and repo(app, 'products/moi/qa-pro-docs.json')
    assert app.call('a.kbSections(S.productId).every((x) => x.d.parts.length > 0)')
    n = len(app.model.calls)
    app.close_settings()
    app.wait_idle()
    assert not any(c.kind.startswith('promptKb') for c in app.model.calls[n:])   # разобранные документы не разбираются заново


def test_disconnect_returns_to_qa_pro_knowledge_base(make_app):
    app = make_app(init=init())
    model_kb.install(app.model)
    app.mode('help')
    parse_sample(app)
    stored = sorted(app.page.evaluate('() => ' + TITLES))
    connect(app)
    assert sorted(app.state('S.kb.index.blocks.map((b) => b.title)')) == ['Восстановление пароля', 'Глоссарий']
    app.page.click('[data-ctx-act=off]')
    app.page.wait_for_function('(n) => window.__qa.S.ctx.src.kind === "qa" && window.__qa.S.kb.index.blocks.length === n', arg=len(stored), timeout=10000)
    assert sorted(app.state('S.kb.index.blocks.map((b) => b.title)')) == stored


# ---------- формат файла ----------
def test_parse_and_serialize_round_trip(app):
    d = {'id': 'k1', 'title': 'Платежи', 'summary': 'Оплата картой', 'synth': '## Лимиты\n- до 3 раз\n\n--> стрелка', 'parts': [{'docId': 'd1', 'docName': 'ТЗ', 'chunk': 0, 'md': 'выдержка', 'at': 1}], 'conflicts': ['спор'], 'links': [], 'updatedAt': 5}
    text = app.call('a.ctxKbSerialize(arg)', d)
    back = app.call('a.ctxKbParse("products/moi/kb/platezhi.md", arg)', text)
    assert back['id'] == 'k1' and back['d']['title'] == 'Платежи' and back['d']['summary'] == 'Оплата картой'
    assert back['d']['synth'] == d['synth'] and back['d']['parts'] == d['parts'] and back['d']['conflicts'] == ['спор']


def test_plain_markdown_file_is_a_human_section(app):
    back = app.call('a.ctxKbParse("knowledge/pay.md", arg)', '# Платежи\n\n> Коротко\n\n## Раздел 1\nтекст\n\n## Раздел 2\nещё')
    assert back['d']['title'] == 'Платежи' and back['d']['summary'] == 'Коротко' and back['d']['human'] is True
    assert back['d']['synth'] == '## Раздел 1\nтекст\n\n## Раздел 2\nещё'


def test_huge_section_is_trimmed_to_file_limit(app):
    parts = [{'docId': f'd{i}', 'docName': 'ТЗ', 'chunk': i, 'md': 'я' * 50000, 'at': i} for i in range(30)]
    text = app.call('a.ctxKbSerialize(arg)', {'id': 'k', 'title': 'Большой', 'synth': 'сводка', 'synthAt': 99, 'synthV': 2, 'parts': parts})
    assert len(text.encode('utf-8')) <= 1800000 and 'Большой' in text


def test_folder_without_parse_marks_takes_them_from_qa_pro(make_app):
    """Папку наполнили до этой версии (без qa-pro-docs.json): разобранные в QA pro документы не разбираются заново."""
    app = make_app(init=init())
    model_kb.install(app.model)
    app.mode('help')
    parse_sample(app)
    sample = app.state('S.docs.find((d) => d.sample).id')
    connect(app)
    app.page.wait_for_function('(id) => !!(window.__qa.S.kb.index.docs || {})[id]', arg=sample, timeout=10000)
    app.page.wait_for_function('() => !window.__qa.S.ctx.pending.size', timeout=10000)
    assert sample in json.loads(repo(app, 'products/moi/qa-pro-docs.json'))
    assert app.state('S.docs.filter((d) => d.sample && (S.kb.index.docs || {})[d.id]).length') == 1
