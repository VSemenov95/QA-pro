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
