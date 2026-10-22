"""База знаний: сбои и лимиты. Обрезанный ответ при сводке, остановка по лимиту, большой раздел без обрезки,
оглавление из тысяч разделов, длинные знания о продукте, размеры записей в базе."""
import json
import re

import pytest

from tests.support import files, model_kb, seed

REC_LIMIT = 262144   # предел одной записи в базе артефакта — 256 КиБ


def nbytes(x):
    return len(json.dumps(x, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


@pytest.fixture
def kb(app):
    model_kb.install(app.model)
    app.mode('help')
    return app


def parse_sample(app):
    app.page.click('[data-act=kb-run]')
    app.wait_idle()


def banner(app):
    return app.state("document.querySelector('#kb-job').innerText.replace(/\\n+/g, ' ')")


# ---------- обрезанный ответ при сводке ----------
def test_truncated_summary_is_retried_shorter(kb):
    kb.model.kb.mode = 'trunc'
    parse_sample(kb)
    prompts = kb.model.prompts_of('promptKbSynth')
    assert len(prompts) == 4   # на каждый из двух разделов — запрос и сжатый повтор
    assert sum('не больше 6000 знаков' in p for p in prompts) == 2 and sum('не больше 3000 знаков' in p for p in prompts) == 2
    assert all('не больше 3000' in p for p in prompts[1::2])   # повтор идёт сразу за неудачным запросом, с меньшим объёмом


def test_shorter_retry_gives_fresh_summaries_without_report(kb):
    kb.model.kb.mode = 'trunc'
    parse_sample(kb)
    assert kb.state('S.kb.index.blocks.every((b) => b.sh && b.sh === b.ph)')
    assert kb.state('S.kb.synthReport') is None and kb.count('#kb-job .banner') == 0


def test_summary_failing_twice_is_reported_with_reason(kb):
    kb.model.on('promptKbSynth', model_kb.ModelError('invalid_json', 'Модель ответила не в формате JSON.'))
    parse_sample(kb)
    rep = kb.state('S.kb.synthReport')
    assert rep['ok'] == 0 and rep['fail'] == 2 and rep['left'] == 0 and rep['reasons'] == {'Модель ответила не в формате JSON.': 2}
    assert 'Сводки: собрано 0 из 2, не получилось 2' in banner(kb)
    assert len(kb.model.calls_of('promptKbSynth')) == 4   # у каждого раздела — две попытки, не больше


# ---------- лимит запросов ----------
def test_rate_limit_stops_summaries_and_explains(kb):
    kb.model.kb.mode = 'limit'
    parse_sample(kb)
    assert kb.model.kb.synth_calls == 1   # на лимите не повторяем и не берёмся за следующий раздел
    text = banner(kb)
    assert 'Сводки: собрано 0 из 2, не получилось 1, не дошла очередь до 1.' in text
    assert 'Сбор остановлен: Слишком много запросов или исчерпан лимит использования' in text
    assert 'Продолжу сам через 10 минут' in text and 'Собрать оставшиеся (2)' in text


def test_sections_stay_available_after_rate_limit(kb):
    kb.model.kb.mode = 'limit'
    parse_sample(kb)
    assert kb.state('S.kb.index.blocks.length') == 2 and kb.state('S.kb.index.blocks.every((b) => b.ph && !b.sh)')   # выдержки есть, сводок нет
    assert 'без сводки' in kb.text('#kb-body')


def test_remaining_summaries_are_built_by_the_report_button(kb):
    kb.model.kb.mode = 'limit'
    parse_sample(kb)
    kb.model.kb.mode = ''
    kb.page.click('#kb-job [data-act=kb-synth]')
    kb.wait_idle()
    assert kb.state('S.kb.index.blocks.every((b) => b.sh && b.sh === b.ph)') and kb.state('S.kb.synthReport') is None
    assert kb.count('#kb-job .banner') == 0


def test_report_can_be_hidden(kb):
    kb.model.kb.mode = 'limit'
    parse_sample(kb)
    kb.page.click('[data-act=kb-report-hide]')
    assert 'Собрать оставшиеся' not in banner(kb) and 'Сводки по всем документам: 2 раздела без свежей сводки' in banner(kb)


def test_failure_of_one_section_does_not_stop_the_others(kb):
    def handler(call):
        if 'сводку раздела «API сброса пароля»' in call.prompt:
            raise model_kb.ModelError('refused', '')
        return kb.model.kb.synth(call)
    kb.model.on('promptKbSynth', handler)
    parse_sample(kb)
    rep = kb.state('S.kb.synthReport')
    assert rep['ok'] == 1 and rep['fail'] == 1 and rep['left'] == 0
    assert 'Модель отказалась обрабатывать этот фрагмент' in json.dumps(rep, ensure_ascii=False)
    assert [b['title'] for b in kb.state('S.kb.index.blocks.filter((b) => b.sh).map((b) => ({ title: b.title }))')] == ['Восстановление пароля']


# ---------- большой раздел ----------
DOCS = 16


@pytest.fixture
def big(kb, tmp_path):
    """16 документов об одном разделе «Общие сведения»; в документе 11 у факта F2-7 другое значение. Весь раздел — больше 13 тысяч знаков."""
    paths = [files.write(tmp_path / f'b{k}.md', model_kb.big_doc(k, conflict=(2, 7, 5) if k == 11 else None)) for k in range(1, DOCS + 1)]
    kb.upload(*paths)
    kb.page.wait_for_function("(n) => { const S = window.__qa.S; return Object.keys(S.kb.index.docs).length >= n && !S.kb.job.busy && !S.kb.queue.length; }", arg=DOCS, timeout=120000)
    kb.wait_idle()
    return kb


def general(app):
    pid = app.state('S.productId')
    meta = app.state("S.kb.index.blocks.find((b) => b.title === 'Общие сведения')")
    main = app.db.get(f'products/{pid}/kb/{meta["id"]}')
    return meta, main, pid


def facts_wanted():
    return [f'F{si}-{j}' for si in range(4) for j in range(24)] + [f'U{k}-{si}' for k in range(1, DOCS + 1) for si in range(4)]


def test_big_section_is_summarized_in_steps(big):
    cond, part, one = big.model.kb.cond_calls, big.model.kb.part_calls, len(big.model.calls_of('promptKbSynth'))
    assert cond > 0 and part > 0 and one == 0   # сжатие подзаголовков, затем сводка по частям; единым запросом такой раздел не собрать
    meta, main, _ = general(big)
    assert main['big'] > 13000 and main['synthV'] == 2 and meta['sh'] == meta['ph']


def test_big_section_prompts_stay_within_request_size(big):
    sizes = [len(c.prompt) for c in big.model.calls_of('promptKbCondense', 'promptKbSynthPart')]
    assert max(sizes) < 40000   # материал до 24 тысяч знаков, остальное — правила и оглавление


def test_big_section_loses_no_facts(big):
    _, main, _ = general(big)
    text = main['synth'] + ' ' + ' '.join(main['conflicts'])
    missing = [f for f in facts_wanted() if not re.search(r'Факт ' + re.escape(f) + ':', text)]
    assert missing == []


def test_big_section_lists_sources_of_each_fact(big):
    _, main, _ = general(big)
    line = re.search(r'- Факт F0-0: [^\n]*', main['synth']).group(0)
    assert line.endswith('(' + '; '.join(sorted(f'b{k}' for k in range(1, DOCS + 1))) + ')')
    own = re.search(r'- Факт U3-1: [^\n]*', main['synth']).group(0)
    assert own.endswith('(b3)')


def test_big_section_reports_disagreement_of_documents(big):
    _, main, _ = general(big)
    assert len(main['conflicts']) == 1
    c = main['conflicts'][0]
    assert c.startswith('Факт F2-7:') and 'b11 — поле «Поле 7» на экране «Профиль» — до 5 символов' in c and 'до 80 символов' in c
    assert not re.search(r'(?m)^- Факт F2-7:', main['synth'].split('### Расхождения между документами')[0])   # спорное значение не выдаётся за факт


def test_big_section_article_says_nothing_was_cut(big):
    big.page.click('#kb-rows .kb-row:has-text("Общие сведения")')
    big.page.wait_for_selector('.kb-synth')
    assert 'без обрезки' in big.text('.kb-synth-h') and f'Выдержки из документов · {DOCS}' in big.text('.kb-parts summary')
    assert 'Расхождения между документами · 1' in big.text('.kb-conf')


def test_big_section_survives_reload(big):
    big.reload()
    big.mode('help')
    big.page.click('#kb-rows .kb-row:has-text("Общие сведения")')
    big.page.wait_for_selector('.kb-synth')
    assert f'Выдержки из документов · {DOCS}' in big.text('.kb-parts summary')


def test_summary_progress_names_steps_of_a_big_section(make_app, tmp_path):
    app = make_app(init=model_kb.SNAPSHOT_INIT)
    model_kb.install(app.model)
    app.mode('help')
    app.state('S.settings.kbAuto = false')
    app.page.set_input_files('#file-input', [str(files.write(tmp_path / f'b{k}.md', model_kb.big_doc(k))) for k in range(1, DOCS + 1)])
    app.wait_docs()
    app.page.click('[data-act=kb-run]')
    app.wait_idle()
    lines = [s['p']['line'] for s in app.js('window.__snaps') if s['p'] and 'большой раздел «Общие сведения»' in s['p']['line']]
    assert lines and re.search(r'большой раздел «Общие сведения» — шаг 1 из \d+', lines[0])
    steps = [int(re.search(r'шаг (\d+) из', l).group(1)) for l in lines]
    assert steps == sorted(steps) and steps[-1] > steps[0]


# ---------- хранение раздела: записи не больше 256 КиБ ----------
def export_with_section(n_parts, chars=11000):
    """Выгрузка продукта с одним разделом базы знаний из n_parts выдержек по chars знаков (кириллица — 2 байта на знак)."""
    parts = [{'docId': f'd{i}', 'docName': f'Документ {i}.md', 'chunk': 0, 'sections': [], 'md': f'{i}' + 'я' * chars, 'h': f'h{i}', 'at': 1000 + i} for i in range(n_parts)]
    blk = {'kind': 'kbblock', 'id': 'kbbig', 'title': 'Большой раздел', 'summary': '', 'parts': parts, 'by': ''}
    meta = {'id': 'kbbig', 'title': 'Большой раздел', 'summary': '', 'docIds': [p['docId'] for p in parts], 'parts': n_parts, 'size': n_parts * chars, 'updatedAt': 1, 'ph': '', 'sh': '', 'conf': 0}
    data = seed.product_export(runs=[])
    data['kb'] = {'index': {'blocks': [meta], 'docs': {}}, 'blocks': [blk]}
    return data


def test_section_larger_than_one_record_is_split_into_continuations(app, tmp_path):
    """20 выдержек по 22 КБ — это 440 КБ: в одну запись (предел 256 КиБ) они не помещаются, хвост уходит в записи-продолжения."""
    app.import_product(seed.write(tmp_path, export_with_section(20)))
    app.page.wait_for_function('() => window.__qa.S.products.length === 2 && window.__qa.S.kb.index.blocks.length === 1')
    pid = app.state('S.productId')
    recs = {k: v for k, v in app.db.store.items() if k.startswith(f'products/{pid}/kb/')}
    main = recs[f'products/{pid}/kb/kbbig']
    assert main['more'] >= 1 and len(recs) == main['more'] + 1
    assert all(nbytes(v) <= REC_LIMIT for v in recs.values())
    assert len(main['parts']) < 20 and sum(len(v['parts']) for v in recs.values()) == 20   # выдержки разложены по записям без потерь


def test_section_is_read_back_whole_from_continuations(app, tmp_path):
    app.import_product(seed.write(tmp_path, export_with_section(20)))
    app.page.wait_for_function('() => window.__qa.S.products.length === 2 && window.__qa.S.kb.index.blocks.length === 1')
    got = app.call("(async () => { const d = await a.kbRead(S.productId, 'kbbig'); return { n: d.parts.length, docs: d.parts.map((p) => p.docId), lens: d.parts.map((p) => p.md.length) }; })()")
    assert got == {'n': 20, 'docs': [f'd{i}' for i in range(20)], 'lens': [11000 + len(str(i)) for i in range(20)]}


def test_deleting_such_a_section_removes_all_its_records(app, tmp_path):
    app.import_product(seed.write(tmp_path, export_with_section(20)))
    app.page.wait_for_function('() => window.__qa.S.products.length === 2 && window.__qa.S.kb.index.blocks.length === 1')
    app.mode('help')
    app.page.click('#kb-rows .kb-row')
    app.page.wait_for_selector('.kb-art')
    app.page.click('[data-act=kb-del]')
    app.page.click('[data-act=kb-del]')
    app.page.wait_for_function('() => window.__qa.S.kb.index.blocks.length === 0')
    pid = app.state('S.productId')
    assert [k for k in app.db.store if k.startswith(f'products/{pid}/kb/')] == []


# ---------- размер раздела в базе (kbFit) ----------
KBFIT = """(() => {
  const big = 'Ж'.repeat(22000);
  const parts = Array.from({ length: 80 }, (_, i) => ({ docId: 'd' + i, docName: 'doc' + i + '.md', chunk: 0, md: big + i, at: i < 60 ? 100 : 300 }));
  const bytes = (o) => new TextEncoder().encode(JSON.stringify(o)).length;
  const withV = { id: 'x', title: 'X', parts, synth: '### Описание\\n- x', synthV: 2, synthAt: 200 };
  const ph = a.kbPartsHash(withV.parts);
  a.kbFit(withV);
  const old = { id: 'y', title: 'Y', parts: parts.map((p) => ({ ...p })), synth: 'x', synthAt: 200 };
  a.kbFit(old);
  return { bytes: bytes(withV), cut: withV.parts.filter((p) => p.cut).length, cutOld: withV.parts.filter((p) => p.cut && p.at === 100).length,
    freshKept: withV.parts.filter((p) => p.at === 300 && p.md).length, lost: withV.lost || 0, samePh: a.kbPartsHash(withV.parts) === ph,
    oldLost: old.lost || 0, oldBytes: bytes(old), total: 240000 * 13 };
})()"""


@pytest.fixture(scope='module')
def fit_result(browser):
    """kbFit на разделе из 80 больших выдержек (3,5 МБ при пределе раздела 3,1 МБ): считаем один раз для нескольких проверок."""
    from tests.support.app import open_app
    app = open_app(browser)
    try:
        return app.call(KBFIT)
    finally:
        app.ctx.close()


def test_section_over_the_limit_drops_summarized_extracts_first(fit_result):
    r = fit_result
    assert r['bytes'] <= r['total']
    assert r['cut'] > 0 and r['cut'] == r['cutOld'] and r['lost'] == 0   # убраны только уже сведённые в сводку, и только самые старые
    assert r['freshKept'] == 20   # свежие выдержки на месте


def test_trimmed_extracts_keep_the_fingerprint(fit_result):
    assert fit_result['samePh'] is True   # сводка не считается устаревшей из-за убранных выдержек


def test_extracts_not_yet_summarized_are_dropped_as_last_resort(fit_result):
    assert fit_result['oldLost'] > 0 and fit_result['oldBytes'] <= fit_result['total']


def test_fit_does_not_modify_data_read_from_the_database(app):
    r = app.call("""(() => {
      const parts = Object.freeze(Array.from({ length: 20 }, (_, i) => Object.freeze({ docId: 'd' + i, docName: 'Док ' + i, chunk: 0, md: 'Ж'.repeat(12000), at: 1000 + i })));
      const next = { ...Object.freeze({ title: 'Из базы', parts }), synth: 'x' };
      try { a.kbFit(next); return { ok: true, parts: next.parts.length, source: parts.length }; } catch (e) { return { ok: false, error: String(e) }; }
    })()""")
    assert r == {'ok': True, 'parts': 20, 'source': 20}


def test_synthesis_text_is_capped(app):
    r = app.call("(() => { const n = { title: 'T', parts: [], synth: 'Я'.repeat(50000) }; a.kbFit(n); return n.synth.length; })()")
    assert r == 24000


# ---------- вспомогательные разбивки ----------
def test_pages_keep_text_and_stay_within_limit(app):
    text = '\n'.join(f'- строка {i} ' + 'x' * 40 for i in range(400))
    pages = app.call('a.kbPages(arg, 6000)', text)
    assert len(pages) > 1 and all(len(p) <= 6000 for p in pages) and '\n'.join(pages) == text


def test_a_single_long_line_is_split_into_pages(app):
    pages = app.call("a.kbPages('я'.repeat(14000), 6000)")
    assert [len(p) for p in pages] == [6000, 6000, 2000]


@pytest.mark.parametrize('text', ['', '   '])
def test_empty_text_gives_one_empty_page(app, text):
    assert len(app.call('a.kbPages(arg, 6000)', text)) == 1


def test_pack_splits_material_by_size_without_losing_text(app):
    items = [{'sub': 'Описание', 'doc': f'd{i}', 'text': ('Слово ' * 1500).strip()} for i in range(5)] + [{'sub': 'Описание', 'doc': 'длинный', 'text': 'Ы' * 30000}]
    packs = app.call('a.kbPack(arg, 24000)', items)
    assert all(sum(len(x['text']) for x in p) <= 24000 for p in packs) and len(packs) >= 3
    assert sum(len(x['text']) for p in packs for x in p) == sum(len(x['text']) for x in items)


def test_by_subheads_groups_text_under_known_headings(app):
    md = 'Вводная строка\n### Поля и элементы\n- поле Email\n### Своя тема\n- осталось в «Полях»\n### Сообщения и ошибки\n- «Введите корректный email»'
    got = app.call('Object.fromEntries(a.kbBySubs(arg))', md)
    # неизвестный заголовок не теряется: остаётся строкой текста под прежним подзаголовком
    assert got == {'Описание': 'Вводная строка', 'Поля и элементы': '- поле Email\n### Своя тема\n- осталось в «Полях»', 'Сообщения и ошибки': '- «Введите корректный email»'}


# ---------- оглавление из тысяч разделов ----------
TOPICS = "['Отчёты', 'Платежи', 'Профиль', 'Уведомления', 'Склад']"
SEED = """(async () => {
  const blocks = Array.from({ length: arg }, (_, i) => ({ id: 'kbz' + i.toString(36).padStart(4, '0'), title: 'Модуль ' + i + ' — ' + @@TOPICS@@[i % 5],
    summary: 'Описание функциональности номер ' + i + ': ' + 'экраны, поля, правила и ограничения модуля. '.repeat(5), docIds: ['d1'], parts: 1, size: 100, updatedAt: 1, ph: 'x', sh: 'x', conf: 0 }));
  await a.kbIdxWrite(S.productId, blocks, { d1: { hash: 'h' } }, null);
  await a.loadKb(S.productId);
})()""".replace('@@TOPICS@@', TOPICS)


@pytest.fixture
def many(kb):
    kb.state('S.settings.kbAuto = false')
    kb.call(SEED, 1500)
    return kb


def index_pages(app):
    pid = app.state('S.productId')
    return {k: v for k, v in app.db.store.items() if re.fullmatch(rf'products/{pid}/meta/kb(_\d+)?', k)}


def test_table_of_contents_is_stored_in_pages(many):
    pages = index_pages(many)
    assert len(pages) > 1 and all(nbytes(v) <= REC_LIMIT for v in pages.values())
    pid = many.state('S.productId')
    assert pages[f'products/{pid}/meta/kb']['pages'] == len(pages)
    assert sum(len(v['blocks']) for v in pages.values()) == 1500


def test_all_sections_are_loaded_from_pages(many):
    assert many.state('S.kb.index.blocks.length') == 1500
    many.reload()
    assert many.state('S.kb.index.blocks.length') == 1500


def test_big_list_is_filtered_by_search(many):
    many.page.click('[data-act=help-view][data-v=blocks]')
    many.page.fill('#kb-q', 'Модуль 777 ')
    assert many.state("[...document.querySelectorAll('#kb-rows .kb-row-t')].map((e) => e.textContent)") == ['Модуль 777 — Профиль']


def test_split_request_lists_nearest_sections_with_descriptions_and_the_rest_by_title(many):
    many.page.click('[data-act=kb-run]')
    many.wait_idle()
    prompt = many.model.prompts_of('promptKbSplit')[0]
    outline = prompt.split('## Разделы, которые уже есть в базе знаний\n')[1].split('\n## Правила')[0]
    lines = outline.strip().split('\n')
    tail = re.search(r'\(ещё (\d+) раздел', lines[-1])
    listed = len(lines) - (1 if tail else 0)
    assert len(outline) <= 90000 + 200
    assert 0 < sum('Описание функциональности' in l for l in lines) <= 120   # описания только у ближайших
    assert listed + (int(tail.group(1)) if tail else 0) == 1500             # остальные либо названы, либо посчитаны


def test_parsing_with_many_sections_adds_the_new_ones(many):
    many.page.click('[data-act=kb-run]')
    many.wait_idle()
    titles = many.state('S.kb.index.blocks.filter((b) => !b.title.startsWith("Модуль")).map((b) => b.title)')
    assert sorted(titles) == ['API сброса пароля', 'Восстановление пароля'] and many.state('S.kb.index.blocks.length') == 1502
    assert index_pages(many)[f'products/{many.state("S.productId")}/meta/kb']['pages'] >= 2


def test_outline_puts_sections_near_the_topic_first(many):
    o = many.call("a.kbOutline(S.kb.index.blocks, 'Платежи оплата картой', { top: 20, cap: 3000 })")
    lines = o.split('\n')
    assert all('Платежи' in l for l in lines[:3]) and 'Описание функциональности' in lines[0]
    assert len(o) <= 3000 + 120 and re.search(r'\(ещё \d+ разделов? далеки от темы и не показаны\)', lines[-1])


def test_outline_of_a_short_list_shows_everything(app):
    o = app.call("a.kbOutline(Array.from({ length: 5 }, (_, i) => ({ id: 'kb' + i, title: 'Раздел ' + i, summary: 'О разделе ' + i })), 'что угодно', { top: 150 })")
    assert o.split('\n') == [f'- kb{i} · Раздел {i} — О разделе {i}' for i in range(5)]


# ---------- знания о продукте: без ограничения длины ----------
RULES = '## Бизнес-правила и ограничения\n' + '\n'.join(f'- Правило {i}: лимит {i} операций, экран «Платёж {i}», сообщение «Превышен лимит {i}» (ТЗ)' for i in range(470))


def test_long_passport_is_stored_apart_from_the_product_card(app):
    app.call('a.savePassport(S.productId, arg, null)', RULES[:39000])
    app.call('a.savePassport(S.productId, arg, null)', RULES[:39000] + '\n- Новое правило')
    pid = app.state('S.productId')
    prod, rec = app.db.get(f'products/{pid}'), app.db.get(f'products/{pid}/meta/passport')
    assert prod['passport']['ext'] is True and prod['passport']['len'] == len(RULES[:39000]) + len('\n- Новое правило') and prod['passport']['text'] == ''
    assert nbytes(prod) < 20000   # карточка продукта остаётся маленькой
    assert len(rec['text']) == prod['passport']['len'] and len(rec['prev']['text']) == 39000 and nbytes(rec) <= REC_LIMIT


def test_long_passport_is_available_to_the_page_and_after_reload(app):
    app.call('a.savePassport(S.productId, arg, null)', RULES[:39000])
    assert app.state('S.products.find((p) => p.id === S.productId).passport.text.length') == 39000
    app.reload()
    app.page.wait_for_function('() => (window.__qa.S.products.find((p) => p.id === window.__qa.S.productId).passport.text || "").length === 39000')


def test_passport_is_not_cut(app):
    app.call('a.savePassport(S.productId, arg, null)', RULES)
    app.page.click('[data-act=pass-edit]')
    app.page.fill('#pass-text', 'я' * 45000)
    app.page.click('[data-act=pass-save]')
    app.page.wait_for_function('() => (window.__qa.S.products.find((p) => p.id === window.__qa.S.productId).passport.len) === 45000')
    assert app.state('S.products.find((p) => p.id === S.productId).passport.text') == 'я' * 45000


BIG = '## Бизнес-правила и ограничения\n' + '\n'.join(f'- Правило {i}: лимит {i} операций, экран «Платёж {i}», сообщение «Превышен лимит {i}» (ТЗ)' for i in range(3000))


def test_very_long_passport_is_stored_in_parts_within_record_limit(app):
    assert len(BIG) > 250000
    app.call('a.savePassport(S.productId, arg, null)', BIG)
    app.call('a.savePassport(S.productId, arg, null)', BIG + '\n- Новое правило')
    pid = app.state('S.productId')
    recs = {k: v for k, v in app.db.store.items() if k.startswith(f'products/{pid}/meta/passport')}
    assert len(recs) > 2 and all(nbytes(v) <= REC_LIMIT for v in recs.values())
    main = recs[f'products/{pid}/meta/passport']
    assert main['parts'] == 5 and main['prev']['parts'] == 5 and main['prev']['text'] == ''
    assert app.db.get(f'products/{pid}')['passport']['len'] == len(BIG) + len('\n- Новое правило')


def test_very_long_passport_reads_back_after_reload_with_previous_version(app):
    app.call('a.savePassport(S.productId, arg, null)', BIG)
    app.call('a.savePassport(S.productId, arg, null)', BIG + '\n- Новое правило')
    app.reload()
    n = len(BIG) + len('\n- Новое правило')
    app.page.wait_for_function('(n) => (window.__qa.S.products.find((p) => p.id === window.__qa.S.productId).passport.text || "").length === n', arg=n)
    p = app.call('a.readProduct(S.productId)')
    assert p['passport']['text'].endswith('- Новое правило') and p['passportPrev']['text'] == BIG
    block = app.call("a.productBlock(null, 'single', 'Платёж 2999 лимит операций')")
    assert 'Правило 2999' in block and len(block) < 8000 + 400   # в запрос — только пункты по теме


def test_short_passport_stays_in_one_record(app):
    app.call('a.savePassport(S.productId, arg, null)', RULES[:39000])
    pid = app.state('S.productId')
    assert [k for k in app.db.store if k.startswith(f'products/{pid}/meta/passport')] == [f'products/{pid}/meta/passport']


def test_only_lines_on_the_topic_of_a_long_passport_go_into_the_request(app):
    app.call('a.savePassport(S.productId, arg, null)', RULES[:39000])
    block = app.call("a.productBlock(null, 'single', 'Платёж 400 лимит операций')")
    assert 'Правило 400' in block and 'пункты по теме запроса' in block
    assert len(block) < 8000 + 400   # предел для одного запроса — 8000 знаков и заголовок
    assert block.count('- Правило ') < 470 and 'Правило 469' not in block
