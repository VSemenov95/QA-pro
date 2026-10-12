"""База знаний продукта: разбор документов на разделы, статьи, сводки по всем документам, расхождения, поиск, переименование, удаление."""
import json

import pytest

from tests.support import files, model_kb

ROWS = "[...document.querySelectorAll('#kb-rows .kb-row')].map((e) => [e.querySelector('.kb-row-t').textContent, e.querySelector('.kb-row-m').textContent])"
TITLES = "[...document.querySelectorAll('#kb-rows .kb-row-t')].map((e) => e.textContent)"
EXTRA, CALL = 'kb_extra.md', 'kb_созвон-call.md'


def titles(app):
    return app.page.evaluate('() => ' + TITLES)


def in_kb(app, *names):
    """Документы разобраны по разделам, сводки собраны, знания о продукте обновлены."""
    app.page.wait_for_function("(names) => { const S = window.__qa.S; return names.every((n) => { const d = S.docs.find((x) => x.name === n); return d && S.kb.index.docs[d.id]; }); }", arg=list(names), timeout=60000)
    app.wait_idle()


def add_docs(app, tmp_path, *docs):
    """docs — пары (имя файла, текст). Документы загружаются и разбираются автоматически."""
    app.upload(*[files.write(tmp_path / name, text) for name, text in docs])
    in_kb(app, *[n for n, _ in docs])


def parse_sample(app):
    app.page.click('[data-act=kb-run]')
    app.wait_idle()
    assert app.state('S.kb.index.blocks.length') == 2


def open_section(app, title):
    app.page.click(f'#kb-rows .kb-row:has-text("{title}")')
    app.page.wait_for_selector('.kb-art h3')


@pytest.fixture
def kb(app):
    """Режим «База знаний» с подключённым мок-ответчиком; в продукте только пример ТЗ."""
    model_kb.install(app.model)
    app.mode('help')
    return app


@pytest.fixture
def parsed(kb):
    """Пример ТЗ разобран на два раздела."""
    parse_sample(kb)
    return kb


@pytest.fixture
def limits(parsed, tmp_path):
    """Кроме примера — два документа с разными лимитами запросов (3 и 5): в разделе «Восстановление пароля» расхождение."""
    add_docs(parsed, tmp_path, (EXTRA, model_kb.limits_doc(3)), (CALL, model_kb.call_doc(5)))
    return parsed


# ---------- оглавление и разбор ----------
def test_unparsed_document_is_offered_for_parsing(kb):
    assert kb.page.get_attribute('[data-act=help-view][data-v=blocks]', 'aria-selected') == 'true'
    job = kb.text('#kb-job')
    assert 'Не разобраны по разделам: 1 документ' in job and kb.count('[data-act=kb-run]') == 1
    assert 'Разделов пока нет' in kb.text('#kb-body')
    assert 'не разобран' in kb.text('#doc-list')


def test_sample_is_split_into_sections_by_function(parsed):
    assert titles(parsed) == ['API сброса пароля', 'Восстановление пароля']
    assert 'разделов 2' in parsed.text('.kb-line')
    assert len(parsed.model.calls_of('promptKbSplit')) == 1 and len(parsed.model.calls_of('promptKbSynth')) == 2


def test_parsed_document_is_marked_in_knowledge_base(parsed):
    assert 'в базе знаний' in parsed.text('#doc-list') and parsed.count('#kb-job .banner') == 0


def test_every_section_gets_a_fresh_summary(parsed):
    stale = parsed.state('S.kb.index.blocks.filter((b) => !b.sh || b.sh !== b.ph).length')
    assert stale == 0 and 'без сводки' not in parsed.text('#kb-body')


def test_parsing_updates_what_the_agent_knows_about_the_product(parsed):
    """Сразу после разбора документ изучается и для паспорта продукта — отдельно «Изучить документы» нажимать не нужно."""
    assert parsed.state('S.prodKnown.docs.length') == 1
    assert 'Версия знаний 1' in parsed.state('S.products.find((p) => p.id === S.productId).passport.text')


def test_upload_in_generation_is_parsed_automatically(app, tmp_path):
    model_kb.install(app.model)
    add_docs(app, tmp_path, (EXTRA, model_kb.limits_doc(3)))
    app.mode('help')
    assert titles(app) == ['Восстановление пароля']
    assert 'в базе знаний' in app.text('#doc-list li:has-text("kb_extra")')


def test_auto_parsing_can_be_switched_off(kb, tmp_path):
    kb.page.click('#kb-auto')   # без документов в базе блок поиска скрыт, но переключатель на месте
    assert kb.state('S.settings.kbAuto') is False
    kb.upload(files.write(tmp_path / EXTRA, model_kb.limits_doc(3)))
    kb.wait_idle()
    assert kb.model.calls_of('promptKbSplit') == []
    assert 'Не разобраны по разделам: 2' in kb.text('#kb-job')


def test_auto_parsing_setting_is_saved(kb):
    kb.page.click('#kb-auto')
    kb.reload()
    assert kb.state('S.settings.kbAuto') is False


def test_documents_without_functional_sections_go_to_general(kb, tmp_path):
    add_docs(kb, tmp_path, ('глоссарий.md', '# Глоссарий\n- Токен: одноразовая ссылка для сброса\n'))
    assert 'Общие сведения' in titles(kb)


def test_sections_survive_reload(parsed):
    parsed.reload()
    parsed.mode('help')
    assert titles(parsed) == ['API сброса пароля', 'Восстановление пароля']


# ---------- статья раздела ----------
def test_article_shows_lead_sources_and_summary(parsed):
    open_section(parsed, 'API сброса пароля')
    art = parsed.text('.kb-art')
    assert 'Эндпоинты запроса и подтверждения сброса' in art
    assert 'Пример — ТЗ восстановление пароля.md' in parsed.text('.kb-art .hq-src')
    assert 'POST /api/v1/password-reset' in parsed.text('.kb-synth .md')


def test_article_back_returns_to_list(parsed):
    open_section(parsed, 'API сброса пароля')
    parsed.page.click('[data-act=kb-back]')
    assert titles(parsed) == ['API сброса пароля', 'Восстановление пароля']


def test_rename_by_enter(parsed):
    open_section(parsed, 'API сброса пароля')
    parsed.page.click('[data-act=kb-rename]')
    assert parsed.page.input_value('#kb-title-input') == 'API сброса пароля'
    parsed.page.fill('#kb-title-input', 'Восстановление доступа: API')
    parsed.page.keyboard.press('Enter')
    parsed.page.wait_for_function("() => document.querySelector('.kb-title-row h3')?.textContent === 'Восстановление доступа: API'")
    parsed.page.click('[data-act=kb-back]')
    assert titles(parsed) == ['Восстановление доступа: API', 'Восстановление пароля']   # список снова по алфавиту


def test_rename_is_saved_for_the_team(parsed):
    open_section(parsed, 'API сброса пароля')
    parsed.page.click('[data-act=kb-rename]')
    parsed.page.fill('#kb-title-input', 'Сброс по API')
    parsed.page.click('[data-act=kb-rename-save]')
    parsed.page.wait_for_function("() => window.__qa.S.kb.index.blocks.some((b) => b.title === 'Сброс по API')")
    pid = parsed.state('S.productId')
    bid = parsed.state("S.kb.index.blocks.find((b) => b.title === 'Сброс по API').id")
    assert parsed.db.get(f'products/{pid}/kb/{bid}')['title'] == 'Сброс по API'


def test_rename_cancelled_by_escape(parsed):
    open_section(parsed, 'API сброса пароля')
    parsed.page.click('[data-act=kb-rename]')
    parsed.page.fill('#kb-title-input', 'Другое')
    parsed.page.keyboard.press('Escape')
    assert parsed.text('.kb-title-row h3') == 'API сброса пароля'


def test_empty_title_is_not_saved(parsed):
    open_section(parsed, 'API сброса пароля')
    parsed.page.click('[data-act=kb-rename]')
    parsed.page.fill('#kb-title-input', '   ')
    parsed.page.click('[data-act=kb-rename-save]')
    parsed.page.wait_for_selector('.kb-title-row h3')
    assert parsed.text('.kb-title-row h3') == 'API сброса пароля'


def test_ask_about_section_puts_draft_into_question_field(parsed):
    open_section(parsed, 'API сброса пароля')
    parsed.page.click('[data-act=kb-ask]')
    assert parsed.page.get_attribute('[data-act=help-view][data-v=qa]', 'aria-selected') == 'true'
    assert parsed.page.input_value('#help-input') == 'Раздел «API сброса пароля»: '
    assert parsed.state('document.activeElement.id') == 'help-input'


# ---------- поиск ----------
def test_search_filters_sections_and_counts(parsed):
    parsed.page.fill('#kb-q', 'API')
    assert titles(parsed) == ['API сброса пароля']
    assert '1 из 2' in parsed.text('.kb-list-h')
    assert parsed.count('#kb-rows mark') >= 1
    parsed.page.fill('#kb-q', '')
    assert len(titles(parsed)) == 2


def test_search_looks_into_descriptions(parsed):
    parsed.page.fill('#kb-q', 'ссылке из письма')   # слова только из описания раздела
    assert titles(parsed) == ['Восстановление пароля']


def test_search_without_matches(parsed):
    parsed.page.fill('#kb-q', 'нет такого раздела')
    assert titles(parsed) == [] and 'Ничего не найдено' in parsed.text('#kb-body')


# ---------- удаление ----------
def remove_doc(app, name):
    btn = f'#doc-list li:has-text("{name}") [data-doc-act=remove]'
    app.page.click(btn)
    app.page.click(btn)   # удаление из продукта подтверждается вторым нажатием
    app.wait_idle()


def test_deleting_a_document_removes_sections_made_only_from_it(limits, tmp_path):
    add_docs(limits, tmp_path, ('отчёты.md', '# Отчёты\n## Отчёты по операциям\n- Формат выгрузки: CSV\n'))
    assert 'Отчёты по операциям' in titles(limits)
    remove_doc(limits, 'отчёты.md')
    limits.page.wait_for_function("() => !window.__qa.S.kb.index.blocks.some((b) => b.title === 'Отчёты по операциям')")
    assert 'Отчёты по операциям' not in titles(limits)


def test_deleting_a_document_removes_its_fragments_from_shared_sections(limits):
    remove_doc(limits, 'созвон')
    assert limits.state("S.kb.index.blocks.find((b) => b.title === 'Восстановление пароля').docIds.length") == 2
    open_section(limits, 'Восстановление пароля')
    assert 'Слишком много попыток' not in limits.text('.kb-synth')


def test_deleting_a_document_rebuilds_summaries_of_its_sections(limits):
    before = limits.model.kb.synth_calls
    remove_doc(limits, 'созвон')
    limits.page.wait_for_function('(n) => true', arg=before)
    assert limits.model.kb.synth_calls > before
    assert limits.state("S.kb.index.blocks.every((b) => b.sh && b.sh === b.ph)")


def test_deleting_a_section(parsed):
    open_section(parsed, 'API сброса пароля')
    bid = parsed.state("S.kb.index.blocks.find((b) => b.title === 'API сброса пароля').id")
    pid = parsed.state('S.productId')
    parsed.page.click('[data-act=kb-del]')
    assert parsed.count('.kb-art') == 1   # первое нажатие только просит подтверждения
    parsed.page.click('[data-act=kb-del]')
    parsed.page.wait_for_function("() => !window.__qa.S.kb.index.blocks.some((b) => b.title === 'API сброса пароля')")
    assert titles(parsed) == ['Восстановление пароля']
    assert parsed.db.get(f'products/{pid}/kb/{bid}') is None


# ---------- выгрузка продукта ----------
def test_product_export_contains_knowledge_base(limits):
    limits.page.click('[data-act=prod-export]')
    limits.page.wait_for_function('() => (window.__downloads || []).length > 0')
    data = json.loads(limits.downloads()[-1].get('text') or limits.js('window.__dlData'))
    assert sorted(b['title'] for b in data['kb']['blocks']) == ['API сброса пароля', 'Восстановление пароля']
    assert len(data['kb']['index']['docs']) == 3


def test_imported_product_keeps_sections(limits, tmp_path):
    limits.page.click('[data-act=prod-export]')
    limits.page.wait_for_function('() => (window.__downloads || []).length > 0')
    path = files.write(tmp_path / 'product.json', limits.js('window.__dlData'))
    limits.import_product(path)
    limits.page.wait_for_function('() => window.__qa.S.products.length === 2 && window.__qa.S.kb.loaded && window.__qa.S.kb.index.blocks.length === 2')
    limits.mode('help')
    assert titles(limits) == ['API сброса пароля', 'Восстановление пароля']
    open_section(limits, 'Восстановление пароля')
    assert 'Расхождения между документами · 1' in limits.text('.kb-conf')


# ---------- сводка по всем документам, расхождения ----------
def test_summary_is_built_from_all_documents(limits):
    row = dict(limits.page.evaluate('() => ' + ROWS))['Восстановление пароля']
    assert row.startswith('3 документа')
    assert limits.state("S.kb.index.blocks.find((b) => b.title === 'Восстановление пароля').docIds.length") == 3
    prompt = limits.model.prompts_of('promptKbSynth')[-1]
    for name in ('Пример — ТЗ восстановление пароля.md', EXTRA, CALL):
        assert f'<excerpt document="{name}"' in prompt


def test_conflicting_values_are_reported_not_chosen(limits):
    open_section(limits, 'Восстановление пароля')
    conf = limits.text('.kb-conf')
    assert 'Расхождения между документами · 1' in conf and 'не более 3 за 15 минут' in conf and 'не более 5 за 15 минут' in conf
    assert 'kb_extra' in conf and 'kb_созвон-call' in conf    # у каждого значения указан документ
    body = limits.text('.kb-synth .md')
    assert 'не более 3' not in body and 'не более 5' not in body   # спорное значение не выдаётся за факт


def test_conflicts_are_shown_once(limits):
    open_section(limits, 'Восстановление пароля')
    assert 'Расхождения' not in limits.text('.kb-synth .md')


def test_section_row_shows_conflict_count(limits):
    row = dict(limits.page.evaluate('() => ' + ROWS))['Восстановление пароля']
    assert 'расхождений 1' in row
    assert 'расхождений между документами 1' in limits.text('.kb-line')


def test_sources_are_listed_after_each_point(limits):
    open_section(limits, 'Восстановление пароля')
    assert '(kb_созвон-call)' in limits.text('.kb-synth .md')


def test_summary_without_conflict_when_documents_agree(parsed, tmp_path):
    add_docs(parsed, tmp_path, (EXTRA, model_kb.limits_doc(3)), ('лимиты-2.md', model_kb.limits_doc(3, title='Ещё лимиты')))
    open_section(parsed, 'Восстановление пароля')
    assert parsed.count('.kb-conf') == 0
    body = parsed.text('.kb-synth .md')
    assert 'не более 3 за 15 минут' in body and 'kb_extra; лимиты-2' in body   # одинаковые сведения объединены, источники перечислены


def test_extracts_are_listed_and_stay_open(limits):
    open_section(limits, 'Восстановление пароля')
    assert 'Выдержки из документов · 3' in limits.text('.kb-parts summary')
    limits.page.click('.kb-parts summary')
    limits.page.click('#help-head [data-v=blocks]')   # перерисовка статьи
    assert limits.state("document.querySelector('.kb-parts').open") is True


def test_related_sections_are_linked(parsed, tmp_path):
    parsed.model.kb.links = {'Восстановление пароля': ['API сброса пароля']}
    parsed.page.click('[data-act=kb-synth-one][data-id], #kb-rows .kb-row') if False else None
    open_section(parsed, 'Восстановление пароля')
    parsed.page.click('[data-act=kb-synth-one]')
    parsed.page.wait_for_selector('.kb-synth .chip-link')
    assert parsed.text('.kb-synth .hq-src') == 'Связанные разделы:\nAPI сброса пароля'
    parsed.page.click('.kb-synth .chip-link')
    parsed.page.wait_for_function("() => document.querySelector('.kb-art h3')?.textContent === 'API сброса пароля'")


def test_stale_sections_offer_to_build_summaries(limits):
    limits.js("() => { for (const b of window.__qa.S.kb.index.blocks) b.sh = ''; }")
    limits.page.click('#help-head [data-v=qa]')
    limits.page.click('#help-head [data-v=blocks]')
    banner = limits.text('#kb-job')
    assert 'Сводки по всем документам: 2 раздела без свежей сводки' in banner
    before = limits.model.kb.synth_calls
    limits.page.click('[data-act=kb-synth]')
    limits.wait_idle()
    assert limits.model.kb.synth_calls - before == 2
    assert limits.count('#kb-job .banner') == 0 and limits.state('window.__qa.S.kb.index.blocks.every((b) => b.sh === b.ph)')


def test_summary_of_one_section_can_be_rebuilt(limits):
    open_section(limits, 'Восстановление пароля')
    before = limits.model.kb.synth_calls
    limits.page.click('[data-act=kb-synth-one]')
    limits.wait_idle()
    assert limits.model.kb.synth_calls == before + 1


# ---------- прогресс разбора ----------
@pytest.fixture
def progress_app(make_app, tmp_path):
    app = make_app(init=model_kb.SNAPSHOT_INIT)
    model_kb.install(app.model)
    app.mode('help')
    app.state('S.settings.kbAuto = false')
    app.page.set_input_files('#file-input', [files.write(tmp_path / EXTRA, model_kb.limits_doc(3)), files.write(tmp_path / CALL, model_kb.call_doc(5))])
    app.wait_docs()
    return app


def snaps(app, head_kind):
    return [s['p'] for s in app.js('window.__snaps') if s['p'] and head_kind in s['p']['title']]


def test_split_progress_counts_documents(progress_app):
    progress_app.page.click('[data-act=kb-run]')
    progress_app.wait_idle()
    titles_ = [p['title'] for p in snaps(progress_app, 'Разбираю')]
    assert titles_ == ['Разбираю документы по разделам: 0 из 3', 'Разбираю документы по разделам: 1 из 3', 'Разбираю документы по разделам: 2 из 3']


def test_split_progress_names_current_document_and_percent(progress_app):
    progress_app.page.click('[data-act=kb-run]')
    progress_app.wait_idle()
    ps = snaps(progress_app, 'Разбираю')
    assert 'сейчас «Пример — ТЗ восстановление пароля.md»' in ps[0]['line'] and 'фрагментов разобрано: 0 из 3' in ps[0]['line']
    assert [p['pct'] for p in ps] == [0, 33, 67]
    assert 'разделов: 2, новых 2' in ps[1]['line']


def test_summary_progress_counts_sections_and_documents(progress_app):
    progress_app.page.click('[data-act=kb-run]')
    progress_app.wait_idle()
    ps = snaps(progress_app, 'Собираю')
    assert [p['title'] for p in ps] == ['Собираю сводки разделов: 0 из 2', 'Собираю сводки разделов: 1 из 2']
    assert 'документов сведено полностью: 0 из 3' in ps[0]['line']
    assert 'документов сведено полностью: 2 из 3' in ps[1]['line']   # третий — пример ТЗ: он ещё и во втором разделе


def test_progress_is_shown_under_the_document_list(progress_app):
    progress_app.js('window.__sampleDelay = 400')
    progress_app.page.click('[data-act=kb-run]')
    progress_app.page.wait_for_function("() => /Разбираю документы по разделам/.test(document.querySelector('#docs-note').textContent)", timeout=10000)
    progress_app.wait_idle()
    assert 'Разбираю' not in progress_app.text('#docs-note')
