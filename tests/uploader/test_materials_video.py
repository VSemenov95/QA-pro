"""«Материалы» → расшифровка видео в базу знаний (docs/sfera-uploader.md): нарезка звука по паузам, конвейер звук → речь → кадры → экран → итоги → документ,
выбор пути к мосту (загрузчик в Chrome или приложение Claude), ошибки.

Распознавание речи (Whisper) подменено: в странице стоит «двойник» загрузчика, который возвращает заданные фразы (support/fake_uploader.js),
а настоящий мост без модели проверяется в путях приложения Claude (host). Видео создаёт ffmpeg (VP9 + Opus); нет ffmpeg — тесты с видео пропускаются.
Распознавание настоящим Whisper здесь не проверяется: см. test_real_whisper_transcribes_a_video.
"""
import os
import re
from types import SimpleNamespace

import pytest

from tests.support import model_kb
from tests.support.app import open_app
from tests.support.media import make_video, need_ffmpeg

FAKE = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'support', 'fake_uploader.js'), encoding='utf-8').read()
IMAGES = 'window.__sampleImages = true;'
SAYS = ['Сначала открываем страницу входа', 'Потом вводим неверный пароль три раза']


def frames_answer(call):
    return {'frames': [{'n': int(a), 'skip': False, 'screen': 'Экран ' + b, 'details': 'Описание кадра ' + a} for a, b in re.findall(r'кадр (\d+) — \[([\d:]+)\]', call.prompt)]}


def summary_answer(call):
    return {'summary': 'Демо восстановления пароля.', 'points': ['Вход', 'Восстановление'], 'requirements': ['Блокировка на 30 минут после трёх попыток'], 'decisions': ['Ссылка живёт 30 минут'], 'questions': ['Что с SMS?']}


def mat_page(browser, script='', init=None):
    a = open_app(browser, init=(init if init is not None else IMAGES + FAKE) + script)
    a.model.on('promptVidFrames', frames_answer)
    a.model.on('vidSummary', summary_answer)
    open_materials(a)
    return a


def open_materials(a):
    a.mode('help')
    a.page.click('#help-head [data-act=help-view][data-v=mat]')
    a.page.wait_for_function('() => window.__qa.S.mat.checked && !window.__qa.S.mat.checking', timeout=20000)


def add_video(a, path, timeout=90000):
    a.page.set_input_files('#mat-file', str(path))
    a.page.wait_for_function("() => window.__qa.vidDocs().length > 0 || (window.__qa.S.mat.jobs[0] && window.__qa.S.mat.jobs[0].stage === 'error')", timeout=timeout)


def job_error(a):
    return a.state("(S.mat.jobs[0] || {}).error || ''")


def doc(a):
    return a.state("(() => { const d = a.vidDocs()[0]; return d && { id: d.id, name: d.name, source: d.source, video: d.video, text: d.text, status: d.status }; })()")


def section(text, title):
    m = re.search(r'^## ' + re.escape(title) + r'\n(.*?)(?=^## |\Z)', text, re.S | re.M)
    return m.group(1).strip() if m else None


@pytest.fixture
def pages(browser):
    made = []

    def make(**kw):
        a = mat_page(browser, **kw)
        made.append(a)
        return a
    yield make
    errs = [e for a in made for e in a.errors]
    for a in made:
        a.ctx.close()
    assert not errs, 'ошибки на странице: ' + '; '.join(errs[:3])


# ---------- нарезка звука по паузам (чистая функция над энергией, 50 значений в секунду) ----------
SEGS = """(spans) => { const e = []; for (const [sec, loud] of spans) for (let i = 0; i < sec * 50; i++) e.push(loud ? -20 : -80);
  return window.__qa.vidSegments(e).map((g) => [g.s / 50, g.e / 50]); }"""


def segs(app, spans):
    return app.page.evaluate(SEGS, spans)


def test_one_phrase_is_one_fragment_with_a_small_margin(app):
    got = segs(app, [[2, 0], [10, 1], [3, 0]])
    assert len(got) == 1 and 1.7 <= got[0][0] <= 2.0 and 12.0 <= got[0][1] <= 12.4


def test_silence_alone_gives_no_fragments(app):
    assert segs(app, [[30, 0]]) == []


def test_no_sound_gives_no_fragments(app):
    assert app.page.evaluate('window.__qa.vidSegments([])') == []


def test_pause_longer_than_two_seconds_splits_and_is_skipped(app):
    got = segs(app, [[5, 1], [3, 0], [5, 1]])
    assert len(got) == 2 and got[0][1] < 5.5 and got[1][0] > 7.5   # тишина между ними ни в один фрагмент не попала


def test_short_pause_does_not_split_a_short_fragment(app):
    assert len(segs(app, [[2, 0], [5, 1], [1, 0], [5, 1], [2, 0]])) == 1


def test_after_18_seconds_even_a_short_pause_is_a_cut(app):
    got = segs(app, [[2, 0], [20, 1], [0.5, 0], [10, 1], [2, 0]])
    assert len(got) == 2 and 22.0 <= got[0][1] <= 22.5   # речь шла с 2-й секунды, к 20-й набралось 18 с — первая же пауза режет


def test_fragments_are_never_longer_than_28_seconds(app):
    speech = [[2, 0]] + [x for _ in range(35) for x in ([1.72, 1], [0.28, 0])] + [[2, 0]]   # 70 с речи с короткими (меньше 0,3 с) провалами, режущей паузы нет
    got = segs(app, speech)
    assert len(got) >= 3 and all(e - s <= 28.0 for s, e in got)
    assert all(got[i + 1][0] <= got[i][1] + 0.01 for i in range(len(got) - 1))   # непрерывная речь режется без потерь (соседние фрагменты чуть перекрываются)


def test_a_click_is_not_speech(app):
    assert segs(app, [[5, 0], [0.2, 1], [20, 0]]) == []


# ---------- разбор MP4 ----------
INFO = """async (b64) => { const bin = atob(b64), u8 = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
  const i = await window.__qa.mp4Info(new File([u8], 'v.mp4'));
  return { dur: Math.round(i.duration * 10) / 10, frag: i.frag, hasAudio: i.hasAudio, hasVideo: i.hasVideo, codec: i.audio && i.audio.codec }; }"""


def info_of(app, path):
    import base64
    return app.page.evaluate(INFO, base64.b64encode(open(path, 'rb').read()).decode())


def test_mp4_with_sound_and_picture_is_read(app, tmp_path):
    i = info_of(app, make_video(tmp_path / 'a.mp4'))
    assert i['dur'] == 17.0 and i['frag'] is False and i['hasAudio'] and i['hasVideo'] and i['codec'] == 'opus'


def test_fragmented_mp4_is_recognized(app, tmp_path):
    assert info_of(app, make_video(tmp_path / 'f.mp4', fragmented=True))['frag'] is True


def test_mp4_without_sound(app, tmp_path):
    i = info_of(app, make_video(tmp_path / 'v.mp4', audio=False))
    assert i['hasVideo'] and not i['hasAudio']


def test_mp4_without_picture(app, tmp_path):
    i = info_of(app, make_video(tmp_path / 's.mp4', video=False))
    assert i['hasAudio'] and not i['hasVideo']


# ---------- весь конвейер (речь подменена) ----------
@pytest.fixture(scope='module')
def done(browser, tmp_path_factory):
    """Видео 17 с: речь 6 с, тишина 5 с, речь 6 с; картинка: три разных экрана. Двойник распознавания отвечает двумя фразами."""
    need_ffmpeg()
    tmp = tmp_path_factory.mktemp('video')
    a = mat_page(browser)
    model_kb.install(a.model)
    a.model.on('promptVidFrames', frames_answer)
    a.model.on('vidSummary', summary_answer)
    f = SimpleNamespace(a=a)
    a.page.evaluate('(t) => { window.__asrTexts = t; }', SAYS)
    f.route = a.state('S.mat.route')
    f.asr_row = a.text('#mat-asr .mat-asr-row')
    a.page.evaluate("""() => { const S = window.__qa.S; window.__stages = [];   // каждое присвоение этапа задания записывается, ничего не пропускается
      S.mat.jobs = new Proxy([], { set(arr, k, v) { if (/^\\d+$/.test(k) && v && typeof v === 'object') v = new Proxy(v, { set(t, p, val) { if (p === 'stage') window.__stages.push(val); t[p] = val; return true; } }); arr[k] = v; return true; } }); }""")
    a.page.set_input_files('#mat-file', make_video(tmp / 'demo_call.mp4'))
    a.page.wait_for_function("() => window.__qa.vidDocs().length > 0 || (window.__qa.S.mat.jobs[0] && window.__qa.S.mat.jobs[0].stage === 'error')", timeout=90000)
    f.stages = a.page.evaluate('window.__stages')
    f.error = job_error(a)
    f.doc = doc(a)
    f.calls = a.page.evaluate('window.__asrCalls')
    f.model_calls = [(c.kind, c.info.get('images', 0)) for c in a.model.calls]
    a.page.wait_for_function("() => { const d = window.__qa.vidDocs()[0]; return d && window.__qa.S.kb.index.docs && window.__qa.S.kb.index.docs[d.id]; }", timeout=60000)
    f.in_kb = True
    f.list_text = a.text('#mat-list')
    f.db_docs = [d for v in a.db.store.values() if isinstance(v, dict) and v.get('kind') == 'product' for d in v.get('docs', []) if d.get('source') == 'video']
    a.mode('generate')
    n = len(a.model.calls)
    a.generate()
    f.gen_prompts = [c.prompt for c in a.model.calls[n:] if c.kind in ('promptAnalyze', 'promptPlan', 'promptGenerate')]
    f.docs_panel = a.text('#doc-list')
    yield f
    errs = list(a.errors)
    a.ctx.close()
    assert not errs, 'ошибки на странице: ' + '; '.join(errs[:3])


def test_pipeline_finishes_without_error(done):
    assert done.error == '' and done.doc and done.doc['status'] == 'ready'


def test_pipeline_goes_through_the_stages(done):
    assert list(dict.fromkeys(done.stages)) == ['audio', 'speech', 'frames', 'screen', 'summary', 'save']


def test_bridge_is_found_through_the_uploader(done):
    assert done.route == 'ext' and 'Whisper small готова · мост 1.2.0 через загрузчик в этом браузере.' in done.asr_row


def test_only_speech_fragments_are_sent_to_recognition(done):
    """Фрагменты без речи не отправляются: 17 с видео, 5 с тишины — два фрагмента."""
    assert len(done.calls) == 2 and all(c['language'] == 'russian' for c in done.calls)
    assert all(8000 < c['bytes'] < 200000 for c in done.calls)   # ≈ 6 с звука 16 кГц, 1 байт на отсчёт, в base64


def test_transcript_has_time_marks(done):
    sp = section(done.doc['text'], 'Расшифровка речи')
    lines = [x for x in sp.split('\n\n') if x]
    assert len(lines) == 2 and lines[0] == f'[00:00] {SAYS[0]}' and re.fullmatch(r'\[00:1[01]\] ' + SAYS[1], lines[1])


def test_screens_are_described_by_the_model(done):
    sc = section(done.doc['text'], 'Что показано на экране')
    assert len(re.findall(r'^- \[\d\d:\d\d\] \*\*', sc, re.M)) == 3
    assert ('promptVidFrames', 3) in done.model_calls   # кадры ушли в модель картинками


def test_summary_sections(done):
    t = done.doc['text']
    main = section(t, 'Главное из видео')
    assert 'Демо восстановления пароля.' in main
    for h in ('### Что обсуждали и показали', '### Требования и правила', '### Решения и договорённости', '### Открытые вопросы'):
        assert h in main
    assert '- Блокировка на 30 минут после трёх попыток' in main


def test_document_sections_come_in_the_documented_order(done):
    heads = re.findall(r'^## (.+)$', done.doc['text'], re.M)
    assert heads == ['Главное из видео', 'Что показано на экране', 'Расшифровка речи']


def test_document_says_the_video_is_not_saved(done):
    assert 'Само видео не сохранено.' in done.doc['text'] and done.doc['text'].startswith('# Видео «demo_call»')


def test_document_is_a_product_document_with_video_meta(done):
    d = done.doc
    assert d['name'] == 'Видео — demo_call.md' and d['source'] == 'video'
    assert d['video']['duration'] == 17 and d['video']['speech'] == 2 and d['video']['screens'] == 3 and d['video']['lang'] == 'russian' and d['video']['file'] == 'demo_call.mp4'


def test_document_is_saved_in_the_product(done):
    assert [m['name'] for m in done.db_docs] == ['Видео — demo_call.md']


def test_document_goes_to_the_knowledge_base(done):
    assert done.in_kb and 'в базе знаний' in done.list_text


def test_transcript_list_shows_duration_and_screens(done):
    assert 'demo_call' in done.list_text and '0:17' in done.list_text and 'экранов 3' in done.list_text


@pytest.mark.xfail(strict=True, reason='БАГ: расшифровка видео не отмечена для генерации (docs/sfera-uploader.md: «по умолчанию отмечен для генерации»): vidRun добавляет документ в S.docs, но не в S.runDocs (app2.js), в списке документов запуска её нет')
def test_document_is_selected_for_generation(done):
    assert 'Видео — demo_call' in done.docs_panel


def test_generation_sees_the_transcript(done):
    assert any('Расшифровка речи' in p and SAYS[0] in p for p in done.gen_prompts)


# ---------- особые видео ----------
def test_silent_video_sends_nothing_to_recognition(pages, tmp_path):
    a = pages()
    add_video(a, make_video(tmp_path / 'silent.mp4', speech=((8, False), (5, False))))
    assert a.page.evaluate('window.__asrCalls.length') == 0 and job_error(a) == ''
    t = doc(a)['text']
    assert 'В звуке не нашлось речи.' in t and section(t, 'Что показано на экране') and section(t, 'Расшифровка речи') is None


def test_video_without_a_sound_track(pages, tmp_path):
    a = pages()
    add_video(a, make_video(tmp_path / 'mute.mp4', audio=False))
    assert 'В видео нет звуковой дорожки.' in doc(a)['text'] and a.page.evaluate('window.__asrCalls.length') == 0


def test_sound_only_file_gives_a_transcript_without_screens(pages, tmp_path):
    a = pages()
    a.page.evaluate('(t) => { window.__asrTexts = t; }', SAYS)
    add_video(a, make_video(tmp_path / 'call.mp4', video=False))
    t = doc(a)['text']
    assert SAYS[0] in t and SAYS[1] in t and section(t, 'Что показано на экране') is None and 'длительность 0:17' in t


def test_nothing_to_extract_is_an_error_not_an_empty_document(pages, tmp_path):
    a = pages()
    add_video(a, make_video(tmp_path / 'empty.mp4', speech=((6, False),), video=False))
    assert 'В звуке не нашлось речи.' in job_error(a) and a.state('a.vidDocs().length') == 0
    assert a.state("S.mat.jobs[0].stage") == 'error'


def test_fragmented_mp4_goes_through_the_fallback_path(pages, tmp_path):
    a = pages()
    a.page.evaluate('(t) => { window.__asrTexts = t; }', SAYS)
    add_video(a, make_video(tmp_path / 'frag.mp4', fragmented=True))
    assert len(a.page.evaluate('window.__asrCalls')) == 2 and SAYS[1] in doc(a)['text']


def test_video_with_codecs_the_browser_lacks_ends_clearly(pages, tmp_path):
    """H.264 + AAC: в Chrome и приложении Claude они есть, в тестовом Chromium — нет; в любом случае разбор заканчивается (документом или понятной ошибкой), а не зависает."""
    a = pages()
    a.page.evaluate('(t) => { window.__asrTexts = t; }', SAYS)
    add_video(a, make_video(tmp_path / 'h264.mp4', codecs='h264-aac'), timeout=60000)
    if a.state('a.vidDocs().length'):
        assert SAYS[0] in doc(a)['text']
    else:
        assert 'кодек' in job_error(a)


def test_mixed_language_mode_is_passed_to_the_bridge(pages, tmp_path):
    a = pages()
    a.page.select_option('#mat-lang', 'auto')
    assert a.page.evaluate("localStorage.getItem('qapro.asrLang')") == '"auto"'
    add_video(a, make_video(tmp_path / 'mix.mp4'))
    assert {c['language'] for c in a.page.evaluate('window.__asrCalls')} == {'auto'} and doc(a)['video']['lang'] == 'auto'


def test_same_name_gets_a_number(pages, tmp_path):
    a = pages()
    p = make_video(tmp_path / 'dup.mp4', speech=((6, True),))
    add_video(a, p)
    a.page.set_input_files('#mat-file', p)
    a.page.wait_for_function('() => window.__qa.vidDocs().length === 2', timeout=90000)
    assert sorted(d for d in a.state('a.vidDocs().map((d) => d.name)')) == ['Видео — dup (2).md', 'Видео — dup.md']


def test_recognition_failure_is_an_error_after_retries(pages, tmp_path):
    a = pages()
    a.page.evaluate("window.__asrFail = 'Поток распознавания завершился'")
    add_video(a, make_video(tmp_path / 'bad.mp4', speech=((2, False), (6, True), (2, False))), timeout=120000)
    assert job_error(a) == 'Распознавание прервалось: Поток распознавания завершился' and a.page.evaluate('window.__asrCalls.length') == 3


def test_cancel_in_the_middle_of_recognition(pages, tmp_path):
    a = pages()
    a.page.evaluate("window.__asrHold = true")
    a.page.set_input_files('#mat-file', make_video(tmp_path / 'long.mp4'))
    a.page.wait_for_function("() => window.__qa.S.mat.jobs[0] && window.__qa.S.mat.jobs[0].stage === 'speech' && window.__asrHeld.length > 0", timeout=60000)
    a.page.click('#mat-jobs [data-act=mat-cancel]')
    a.page.evaluate('window.__asrReleaseAll()')
    a.page.wait_for_function('() => !window.__qa.S.mat.jobs.length && !window.__qa.S.mat.busy', timeout=60000)
    assert a.state('a.vidDocs().length') == 0


def test_transcript_is_deleted_with_a_double_click(pages, tmp_path):
    a = pages()
    add_video(a, make_video(tmp_path / 'del.mp4', speech=((6, True),)))
    d = doc(a)
    a.wait_idle()   # база знаний закончила разбор: список больше не перерисовывается
    a.page.click('#mat-list [data-act=mat-del]')
    a.page.wait_for_function("() => document.querySelector('#mat-list [data-act=mat-del]').textContent === 'Удалить из продукта?'")
    assert a.state('a.vidDocs().length') == 1   # первое нажатие только спрашивает
    a.page.click('#mat-list [data-act=mat-del]')
    a.page.wait_for_function('() => window.__qa.vidDocs().length === 0')
    a.page.wait_for_timeout(300)
    left = [m for v in a.db.store.values() if isinstance(v, dict) and v.get('kind') == 'product' for m in v.get('docs', []) if m.get('source') == 'video']
    assert left == [] and not [k for k in a.db.store if '/docparts/' in k and d['id'] in k]


def test_not_an_mp4_is_refused_with_a_hint(pages, tmp_path):
    a = pages()
    p = tmp_path / 'notes.pdf'
    p.write_bytes(b'%PDF-1.4')
    a.page.set_input_files('#mat-file', str(p))
    a.page.wait_for_function("() => [...document.querySelectorAll('#toasts > *, .toast')].some((e) => /не \\.mp4/.test(e.textContent))")
    assert any('«notes.pdf» — не .mp4. Материалы принимают видео .mp4.' in t for t in a.toast_texts()) and a.state('S.mat.jobs.length') == 0


def test_renamed_file_is_not_taken_for_a_video(pages, tmp_path):
    a = pages()
    p = tmp_path / 'fake.mp4'
    p.write_bytes('это текст, а не видео'.encode() * 50)
    a.page.set_input_files('#mat-file', str(p))
    a.page.wait_for_function("() => window.__qa.S.mat.jobs[0] && window.__qa.S.mat.jobs[0].stage === 'error'", timeout=20000)
    assert job_error(a) == 'Файл не похож на видео .mp4 — он повреждён или переименован.'


# ---------- путь к мосту ----------
def test_model_choice_is_remembered(pages):
    a = pages()
    a.page.select_option('#mat-model', 'base')
    assert a.page.evaluate("localStorage.getItem('qapro.asrModel')") == '"base"'
    assert 'Модель Whisper base (≈ 80 МБ) скачается при первом видео' in a.text('#mat-asr .mat-asr-row') or 'Whisper base' in a.text('#mat-asr')


@pytest.mark.parametrize('script,expected', [
    ('', None),
    ("window.__bridgeUp = false;", 'Загрузчик на месте, но мост qa-pro-bridge не запущен.'),
    ("window.__extVersion = '1.4.0';", 'Загрузчик 1.4.0 не умеет передавать звук мосту — обновите его до 1.5.0'),
    ("window.__bridgeVersion = '1.1.0';", 'Мост 1.1.0 не умеет распознавать речь — установите мост 1.2.0'),
])
def test_bridge_problems_are_explained_with_download_buttons(pages, script, expected):
    a = pages(script=script)
    if expected is None:
        assert a.state('S.mat.route') == 'ext' and a.count('#mat-asr [data-act=bridge-mcpb]') == 0
        return
    assert a.state('S.mat.route') == '' and expected in a.text('#mat-asr .mat-asr-row')
    assert a.text('#mat-asr [data-act=bridge-mcpb]') == 'Скачать мост (.mcpb)' and a.text('#mat-asr [data-act=sfera-zip]') == 'Скачать загрузчик (.zip)'


def test_video_without_a_bridge_stops_with_a_clear_error(pages, tmp_path):
    a = pages(script='window.__bridgeUp = false;')
    add_video(a, make_video(tmp_path / 'nb.mp4'))
    assert 'Загрузчик на месте, но мост qa-pro-bridge не запущен.' in job_error(a)


# ---------- мост в приложении Claude (настоящий мост без модели) ----------
@pytest.fixture
def desk(make_host):
    h = make_host()
    app = h.desk_host.open()
    app.mode('help')
    app.page.click('#help-head [data-act=help-view][data-v=mat]')
    app.page.wait_for_function('() => window.__qa.S.mat.checked && !window.__qa.S.mat.checking', timeout=20000)
    return SimpleNamespace(h=h, app=app)


def test_desktop_app_finds_the_bridge_directly(desk):
    a = desk.app
    assert a.state('S.mat.route') == 'host' and a.state('S.mat.asr.state') == 'idle'
    assert 'Модель Whisper small (≈ 250 МБ) скачается при первом видео — или нажмите «Скачать модель». Мост 1.2.0 через приложение Claude.' in a.text('#mat-asr .mat-asr-row')


def test_desktop_app_has_no_uploader_download_button(desk):
    assert desk.app.count('#mat-asr [data-act=sfera-zip]') == 0


def test_desktop_app_without_the_bridge(desk):
    desk.h.mcp.up = False
    a = desk.app
    a.page.click('[data-act=mat-check]')
    a.page.wait_for_function("() => window.__qa.S.mat.checked && !window.__qa.S.mat.checking && !window.__qa.S.mat.route")
    assert 'Мост qa-pro-bridge не найден в приложении Claude: установите его' in a.text('#mat-asr .mat-asr-row')
    assert a.text('#mat-asr [data-act=bridge-mcpb]') == 'Скачать мост (.mcpb)' and a.count('#mat-asr [data-act=sfera-zip]') == 0


def test_desktop_page_without_permission_for_speech_tools(make_host, tmp_path):
    """В манифесте страницы asr_* нет (их добавляет только публикация из локальной сессии Claude): страница объясняет, что делать."""
    h = make_host(pre_init="window.__mcpTools = ['ping', 'sfera_upload', 'sfera_job', 'sfera_cancel'];")
    a = h.desk_host.open()
    a.mode('help')
    a.page.click('#help-head [data-act=help-view][data-v=mat]')
    a.page.wait_for_function('() => window.__qa.S.mat.checked && !window.__qa.S.mat.checking', timeout=20000)
    row = a.text('#mat-asr .mat-asr-row')
    assert a.state('S.mat.route') == '' and 'ещё не разрешено вызывать распознавание речи' in row and 'разбирайте видео в QA pro, открытом в Chrome с загрузчиком 1.5' in row


def test_choosing_base_model_and_downloading_reports_the_registry_error(make_host):
    """«Скачать модель» запускает подготовку в мосте; без доступа к реестру npm страница показывает причину."""
    from tests.support.bridge import free_port
    h = make_host(bridge_env={'QA_PRO_BRIDGE_NPM': f'http://127.0.0.1:{free_port()}'})
    a = h.desk_host.open()
    a.mode('help')
    a.page.click('#help-head [data-act=help-view][data-v=mat]')
    a.page.wait_for_function('() => window.__qa.S.mat.checked && !window.__qa.S.mat.checking', timeout=20000)
    a.page.select_option('#mat-model', 'base')
    a.page.click('[data-act=mat-prepare]')
    a.page.wait_for_function("() => /Не удалось скачать распознаватель/.test(document.querySelector('#mat-asr .mat-asr-row')?.innerText || '')", timeout=30000)
    assert h.bridge.tool('asr_status')['model'] == 'base'


# ---------- настоящий Whisper ----------
@pytest.mark.skip(reason='нужны распознаватель из npm (≈36 МБ), модель Whisper (≈80–250 МБ, Hugging Face) и видео с настоящей речью: в окружении и репозитории их нет (старый t/run24.py брал их из /tmp). Конвейер выше проверен с подменой распознавания')
def test_real_whisper_transcribes_a_video():
    pass
