"""Скриншоты в документах: распознаются и в PDF с текстом, в несколько потоков, в фоне, повторы и уже распознанные — без OCR.
Движок OCR в тестах — заглушка (tests/support/tesseract_stub.js): «текст» картинки — её цвет."""
import pytest

from tests.support import files

pytestmark = pytest.mark.needs_libs

RED, GREEN, BLUE = 'Экран цвета 200-30-30', 'Экран цвета 20-150-60', 'Экран цвета 0-0-255'


@pytest.fixture(autouse=True)
def fresh_cache(app):
    """Распознанное хранится в браузере между тестами — каждый тест начинает с пустой памятью."""
    app.page.evaluate("localStorage.removeItem('qapro.ocrCache')")
    app.reload()


def doc(app, name):
    return app.state(f"S.docs.find((d) => d.name === {name!r})")


def wait_ocr(app):
    app.page.wait_for_function("() => window.__qa.ocrJobs.size === 0", timeout=20000)


def test_screenshots_inside_text_pdf_are_recognized(app, tmp_path):
    app.upload(files.pdf_with_screens(tmp_path))
    wait_ocr(app)
    d = doc(app, 'ТЗ-со-скриншотами.pdf')
    t = d['text']
    assert 'Section 1. Login form' in t and 'Section 2. Profile screen' in t
    assert t.count(RED) == 1 and t.count(GREEN) == 1   # повтор на второй странице — один раз
    assert BLUE not in t                                # значок 24×24 не распознаётся
    assert t.index(RED) < t.index('--- Страница 2 ---') < t.index(GREEN)   # текст скриншота — на своей странице
    assert 'скриншотов: 2' in d['warn']
    assert app.state('window.__ocr.calls') == 2


def test_text_is_ready_before_screenshots(app, tmp_path):
    app.page.evaluate('window.__ocr = { calls: 0, now: 0, max: 0, workers: 0, delay: 1500 }')
    app.upload(files.pdf_with_screens(tmp_path))
    d = doc(app, 'ТЗ-со-скриншотами.pdf')
    assert d['status'] == 'ready' and 'Section 1. Login form' in d['text'] and RED not in d['text']
    assert 'скриншоты' in app.text('#doc-list')
    wait_ocr(app)
    assert RED in doc(app, 'ТЗ-со-скриншотами.pdf')['text']


def test_run_waits_for_screenshots(app, tmp_path):
    app.page.evaluate('window.__ocr = { calls: 0, now: 0, max: 0, workers: 0, delay: 1500 }')
    app.upload(files.pdf_with_screens(tmp_path))
    app.generate(wait=False)
    assert 'Распознаю скриншоты' in app.text('#run-note')
    wait_ocr(app)
    app.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.status !== 'running' && !window.__qa.S.running", timeout=90000)
    p = app.model.prompts_of('promptAnalyze')[0]
    assert RED in p and GREEN in p


def test_screenshots_are_recognized_in_parallel(app, tmp_path):
    cores = app.page.evaluate('navigator.hardwareConcurrency || 2')
    pics = [(240, 160, (10 * i, 40, 90)) for i in range(1, 7)]
    app.page.evaluate('window.__ocr = { calls: 0, now: 0, max: 0, workers: 0, delay: 300 }')
    app.upload(files.pdf_with_screens(tmp_path, pages=[('Section 1. Many screens of the settings dialog follow below. ' * 6, pics)]))
    wait_ocr(app)
    o = app.state('window.__ocr')
    assert o['calls'] == 6
    assert o['max'] == min(3, max(1, cores - 1)) and o['workers'] == o['max']


def test_known_screenshots_are_not_recognized_again(app, tmp_path):
    app.upload(files.pdf_with_screens(tmp_path))
    wait_ocr(app)
    calls = app.state('window.__ocr.calls')
    # другой файл с тем же скриншотом: распознанный текст берётся из памяти браузера
    app.upload(files.pdf_with_screens(tmp_path, name='новая-версия.pdf', pages=[('Section 7. The same login screen in a new version of the spec.', [(240, 160, (200, 30, 30))])]))
    wait_ocr(app)
    assert RED in doc(app, 'новая-версия.pdf')['text']
    assert app.state('window.__ocr.calls') == calls


def test_engines_stay_open_between_files(app, tmp_path):
    app.upload(files.pdf_with_screens(tmp_path))
    wait_ocr(app)
    workers = app.state('window.__ocr.workers')
    app.upload(files.pdf_with_screens(tmp_path, name='другой.pdf', pages=[('Section 9. Another dialog with a different screenshot inside.', [(240, 160, (90, 90, 90))])]))
    wait_ocr(app)
    assert app.state('window.__ocr.workers') == workers   # движок не пересоздаётся для следующего файла


def test_bytes_key_tells_images_apart(app):
    a = app.call("a.bytesKey(new Uint8Array([1, 2, 3]))")
    assert a == app.call("a.bytesKey(new Uint8Array([1, 2, 3]))")
    assert a != app.call("a.bytesKey(new Uint8Array([1, 2, 4]))")


# ---------- движок распознавания не загрузился или завис: запуск генерации не должен вставать ----------
# Сроки распознавания в тестах — короткие (window.__ocrMs), иначе ждать пришлось бы минутами, как и пользователю
HANG = "window.__ocrMs = 600; window.__ocr = { calls: 0, now: 0, max: 0, workers: 0, delay: 30, inits: 0, %s: true }"
MANY = [(240, 160, (10 * i, 40, 90)) for i in range(1, 13)]   # 12 разных скриншотов
LONG = 'Section 1. Many screens of the settings dialog follow below. ' * 6


def test_engine_that_never_loads_is_tried_once_not_per_screenshot(app, tmp_path):
    app.page.evaluate(HANG % 'hangInit')
    app.upload(files.pdf_with_screens(tmp_path, pages=[(LONG, MANY)]))
    app.page.wait_for_function("() => window.__qa.ocrJobs.size === 0", timeout=8000)   # раньше — 12 попыток по 3 минуты
    o = app.state('window.__ocr')
    assert o['inits'] <= 3   # первая волна потоков; дальше движок считается недоступным
    d = doc(app, 'ТЗ-со-скриншотами.pdf')
    assert d['status'] == 'ready' and 'Section 1.' in d['text'] and 'движок OCR не загрузился' in d['warn']


def test_scan_only_pdf_does_not_block_run_button_when_engine_hangs(app, tmp_path):
    app.page.evaluate(HANG % 'hangInit')
    app.upload(files.pdf_with_screens(tmp_path, pages=[('', [(600, 800, (250, 250, 250))]), ('', [(600, 800, (240, 240, 240))])]))
    app.page.wait_for_function("() => !document.querySelector('#btn-run').disabled", timeout=8000)
    assert doc(app, 'ТЗ-со-скриншотами.pdf')['status'] in ('ready', 'error')


def test_document_recognition_has_a_time_limit(app, tmp_path):
    app.page.evaluate(HANG % 'hangRecognize')
    app.upload(files.pdf_with_screens(tmp_path, pages=[(LONG, MANY)]))
    app.page.wait_for_function("() => window.__qa.ocrJobs.size === 0", timeout=10000)
    assert 'Section 1.' in doc(app, 'ТЗ-со-скриншотами.pdf')['text']


def test_second_click_starts_run_without_waiting_for_screenshots(app, tmp_path):
    app.page.evaluate('window.__ocr = { calls: 0, now: 0, max: 0, workers: 0, delay: 20000 }')
    app.upload(files.pdf_with_screens(tmp_path))
    app.generate(wait=False)
    assert 'Распознаю скриншоты' in app.text('#run-note') and 'ещё раз' in app.text('#run-note')
    assert not app.page.is_disabled('#btn-run')
    app.page.click('#btn-run')   # не ждать распознавания
    app.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.status !== 'running' && !window.__qa.S.running", timeout=60000)
    p = app.model.prompts_of('promptAnalyze')[0]
    assert 'Section 1. Login form' in p and RED not in p


# ---------- предупреждение называет причину; «Распознать оставшиеся» распознаёт только нераспознанное ----------
def test_warning_names_engine_failure(app, tmp_path):
    app.page.evaluate(HANG % 'hangInit')
    app.upload(files.pdf_with_screens(tmp_path, pages=[(LONG, MANY)]))
    wait_ocr(app)
    w = doc(app, 'ТЗ-со-скриншотами.pdf')['warn']
    assert 'из 12' in w and 'движок OCR не загрузился' in w and 'не хватило времени' not in w


def test_warning_names_time_limit(app, tmp_path):
    app.page.evaluate(HANG % 'hangRecognize')
    app.upload(files.pdf_with_screens(tmp_path, pages=[(LONG, MANY)]))
    wait_ocr(app)
    w = doc(app, 'ТЗ-со-скриншотами.pdf')['warn']
    assert 'не хватило времени' in w and 'распознано 0 из 12' in w and 'движок' not in w


def test_document_time_limit_grows_with_images(app):
    one, sixty, many = app.call("[a.ocrDocMs(1), a.ocrDocMs(60), a.ocrDocMs(5000)]")
    assert one == 360000 and sixty > 360000 and many == 1800000


def retry(app):
    # список документов перерисовывается во время фоновой работы (база знаний): щелчок — событием, а не мышью
    app.page.locator('[data-doc-act="ocr"]').dispatch_event('click')
    app.page.wait_for_function("() => window.__qa.ocrJobs.size > 0", timeout=5000)
    app.page.wait_for_function("() => window.__qa.ocrJobs.size === 0 && window.__qa.S.docs.every((d) => !d.ocr)", timeout=20000)


def test_retry_after_engine_failure_recognizes_all(app, tmp_path):
    app.page.evaluate(HANG % 'hangInit')
    app.upload(files.pdf_with_screens(tmp_path, pages=[(LONG, MANY)]))
    wait_ocr(app)
    assert app.page.is_visible('[data-doc-act="ocr"]')
    app.page.evaluate("window.__ocr.hangInit = false; window.__ocrMs = 15000")   # сеть восстановилась: движок грузится, не дожидаясь 10 минут
    retry(app)
    d = doc(app, 'ТЗ-со-скриншотами.pdf')
    assert d['warn'].startswith('Распознан текст') and d['ocrLeft'] == 0
    assert 'Экран цвета 10-40-90' in d['text'] and 'Section 1.' in d['text']
    assert not app.page.is_visible('[data-doc-act="ocr"]')


def test_retry_recognizes_only_what_is_left(app, tmp_path):
    app.page.evaluate(HANG % 'hangRecognize' + "; window.__ocr.hangRecognize = false; window.__ocr.hangAfter = 4; window.__ocr.delay = 5")
    app.upload(files.pdf_with_screens(tmp_path, pages=[(LONG, MANY)]))
    wait_ocr(app)
    d = doc(app, 'ТЗ-со-скриншотами.pdf')
    assert d['ocrLeft'] == 8 and 'распознано 4 из 12' in d['warn']
    app.page.evaluate("window.__ocr.hangAfter = null; window.__ocr.calls = 0; window.__ocrMs = 15000")
    retry(app)
    assert app.state('window.__ocr.calls') == 8   # четыре уже распознанных — из памяти браузера
    assert doc(app, 'ТЗ-со-скриншотами.pdf')['ocrLeft'] == 0


# ---------- повторная загрузка документа с нераспознанными картинками заменяет прежнюю копию ----------
NAME = 'ТЗ-со-скриншотами.pdf'


def same_name(app):
    return app.state(f"S.docs.filter((d) => d.name === {NAME!r}).map((d) => ({{ id: d.id, warn: d.warn, text: d.text, ocrLeft: d.ocrLeft }}))")


def test_reupload_replaces_copy_with_unrecognized_images(app, tmp_path):
    app.page.evaluate(HANG % 'hangInit')
    f = files.pdf_with_screens(tmp_path, pages=[(LONG, MANY)])
    app.upload(f)
    wait_ocr(app)
    first = same_name(app)
    assert len(first) == 1 and first[0]['ocrLeft'] == 12
    app.page.evaluate("window.__ocr.hangInit = false; window.__ocrMs = 15000; window.__qa.ocrReset()")
    app.upload(f)
    app.page.wait_for_function(f"() => window.__qa.ocrJobs.size === 0 && window.__qa.S.docs.filter((d) => d.name === {NAME!r}).length === 1 && window.__qa.S.docs.every((d) => d.status !== 'parsing')", timeout=20000)
    now = same_name(app)
    assert len(now) == 1 and now[0]['id'] == first[0]['id']   # тот же документ — в продукте и базе знаний обновляется он, а не появляется второй
    assert now[0]['ocrLeft'] == 0 and 'Экран цвета 10-40-90' in now[0]['text']


def test_reupload_that_fails_again_still_keeps_one_copy(app, tmp_path):
    app.page.evaluate(HANG % 'hangInit')
    f = files.pdf_with_screens(tmp_path, pages=[(LONG, MANY)])
    app.upload(f)
    wait_ocr(app)
    app.page.evaluate("window.__qa.ocrReset()")
    app.upload(f)
    app.page.wait_for_function(f"() => window.__qa.ocrJobs.size === 0 && window.__qa.S.docs.filter((d) => d.name === {NAME!r}).length === 1 && window.__qa.S.docs.every((d) => d.status !== 'parsing')", timeout=20000)
    assert app.page.is_visible('[data-doc-act="ocr"]')   # у новой копии файл в памяти — её можно распознать повтором


def test_saved_document_with_unrecognized_images_tells_to_upload_again(app, tmp_path):
    app.page.evaluate(HANG % 'hangInit')
    app.upload(files.pdf_with_screens(tmp_path, pages=[(LONG, MANY)]))
    wait_ocr(app)
    # как документ, прочитанный из продукта: файла в памяти нет, предупреждение — из прежней версии
    app.page.evaluate(f"""() => {{ const a = window.__qa, d = a.S.docs.find((x) => x.name === {NAME!r});
      a.docFiles.delete(d.id); d.ocrLeft = 0; d.warn = 'Не распознано сканов и скриншотов: 37 — не загрузился движок OCR или не хватило времени'; a.renderAll(); }}""")
    assert not app.page.is_visible('[data-doc-act="ocr"]')
    assert 'загрузите файл ещё раз' in app.text('#doc-list')


# ---------- движок и языковые данные — из папки ocr/ рядом со страницей; нет своих файлов — с CDN ----------
def serve_local_engine(app):

    from tests.support import app as app_mod, libs
    stub = libs.STUBS['tesseract.js@5.1.1/dist/tesseract.min.js']
    gz = __import__('base64').b64encode(__import__('gzip').compress(b'traineddata')).decode()   # языковые данные — base64 от .gz

    def serve(r):
        if r.request.url.endswith('.b64.txt'):
            return r.fulfill(body=gz, content_type='text/plain')
        return r.fulfill(path=stub, content_type='application/javascript')
    app.ctx.route(app_mod.URL + 'ocr/**', serve)
    app.reload()


def test_engine_files_come_from_the_app_itself(app, tmp_path):
    serve_local_engine(app)
    app.upload(files.pdf_with_screens(tmp_path))
    wait_ocr(app)
    paths = [p for p in app.state('window.__ocr.paths') if p]
    assert paths and paths[0]['workerPath'].endswith('/ocr/worker.min.js')
    assert paths[0]['corePath'].endswith('/ocr/core')
    assert [x.split(':')[0] for x in paths[0]['langs']] == ['rus', 'eng'] and all(int(x.split(':')[1]) > 10 for x in paths[0]['langs'])
    assert RED in doc(app, 'ТЗ-со-скриншотами.pdf')['text']


def test_without_own_files_engine_comes_from_cdn(app, tmp_path):
    app.upload(files.pdf_with_screens(tmp_path))   # в тестах по адресу ocr/ сервер отдаёт страницу, а не файлы движка
    wait_ocr(app)
    assert all(p is None for p in app.state('window.__ocr.paths'))
    assert RED in doc(app, 'ТЗ-со-скриншотами.pdf')['text']


def test_broken_own_files_fall_back_to_cdn(app, tmp_path):
    serve_local_engine(app)
    app.page.evaluate("window.__ocr = { calls: 0, now: 0, max: 0, workers: 0, delay: 30, failLocal: true }")
    app.upload(files.pdf_with_screens(tmp_path))
    wait_ocr(app)
    d = doc(app, 'ТЗ-со-скриншотами.pdf')
    assert RED in d['text'] and not d['warn'].startswith('Не распознано')
    assert None in app.state('window.__ocr.paths')   # после отказа своих файлов — движок с CDN


def test_engine_failure_with_own_files_does_not_blame_cdn(app):
    w = app.call("a.ocrWarn({ failed: 3, total: 3, ok: 0, engineN: 3, engine: 'ошибка', broken: 0, late: 0, ms: 60000, cdn: false }, 'картинок')")
    assert 'движок OCR не загрузился (ошибка)' in w and 'cdn.jsdelivr.net' not in w
