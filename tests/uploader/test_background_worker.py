"""Фоновый исполнитель (шестерёнка → «Фон»): вкладка браузера доделывает работу, начатую в окне, которое закрыли.

Два окна с общей базой артефакта: «приложение Claude» (UA Electron, модель отвечает медленно) и обычная вкладка браузера с включённым фоном.
"""
import time
from types import SimpleNamespace

import pytest

from tests.support import files, model_kb
from tests.support.app import open_app
from tests.support.db import MemoryDB

DESK_INIT = """Object.defineProperty(navigator, 'userAgent', { get: () => 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Claude/1.0.0 Chrome/138.0.0.0 Electron/37.2.0 Safari/537.36' }); window.__sampleDelay = 1500;"""
WORKER_INIT = "window.__sampleDelay = 700;"   # модель отвечает не мгновенно: доделка генерации видна не один миг
PAGEHIDE = "window.dispatchEvent(new PageTransitionEvent('pagehide', { persisted: false }))"


def wait_db(page, pred, timeout=60, what='условие'):
    end = time.time() + timeout
    while time.time() < end:
        v = pred()
        if v:
            return v
        page.wait_for_timeout(100)
    raise AssertionError('не дождались: ' + what)


def worker_doc(db):
    return next((d for k, d in db.store.items() if k.endswith('/worker')), None)


def run_meta(db):
    return [v for k, v in db.store.items() if '/runs/' in k and k.count('/') == 3]


class Windows:
    def __init__(self, browser, db=None):
        self.browser, self.db = browser, db or MemoryDB()
        self.apps = []

    def open(self, desk=False, worker=False, **kw):
        a = open_app(self.browser, db=self.db, init=DESK_INIT if desk else WORKER_INIT if worker else None, local_storage={'qapro.worker': True} if worker else None, **kw)
        self.apps.append(a)
        return a

    def close(self):
        errs = [e for a in self.apps for e in a.errors]
        for a in self.apps:
            try:
                a.ctx.close()
            except Exception:
                pass
        assert not errs, 'ошибки на странице: ' + '; '.join(errs[:3])


@pytest.fixture
def win(browser):
    w = Windows(browser)
    yield w
    w.close()


@pytest.fixture(scope='module')
def abandoned(browser, tmp_path_factory):
    """Генерацию начали в приложении и закрыли окно посреди работы; фоновая вкладка её доделала; потом приложение открыли снова."""
    w = Windows(browser)
    f = SimpleNamespace(w=w)
    worker = w.open(worker=True)
    wait_db(worker.page, lambda: worker_doc(w.db), 20, 'присутствие исполнителя')
    f.presence = dict(worker_doc(w.db))
    desk = w.open(desk=True)
    desk.open_settings('bg')
    desk.page.wait_for_function("() => /Фоновый исполнитель на связи/.test(document.querySelector('#bg-body')?.innerText || '')", timeout=15000)
    f.bg_text = desk.text('#bg-body')
    desk.page.keyboard.press('Escape')
    desk.page.click('#btn-run')
    desk.page.wait_for_function("() => /Окно можно закрыть/.test(document.querySelector('#run-note')?.innerText || '')", timeout=15000)
    f.run_note = desk.text('#run-note')
    desk.page.wait_for_function("() => document.querySelector('#tab-cases .cnt') && +document.querySelector('#tab-cases .cnt').textContent >= 1", timeout=60000)
    f.cases_before = int(desk.text('#tab-cases .cnt'))
    desk.page.evaluate(PAGEHIDE)
    desk.page.wait_for_timeout(300)   # окно успевает записать «закрываюсь» (hb: 0) до закрытия
    desk.ctx.close()
    f.meta_at_close = [(m.get('status'), m.get('hb')) for m in run_meta(w.db)]
    wait_db(worker.page, lambda: worker_doc(w.db).get('doing') == 'генерация', 60, 'исполнитель взялся за генерацию')
    f.doing = worker_doc(w.db).get('doing')
    f.running = worker.state('S.running')
    f.toasts = worker.toast_texts()
    wait_db(worker.page, lambda: run_meta(w.db)[0].get('status') == 'done', 90, 'генерация завершена')
    worker.page.wait_for_selector('#btn-run:not([hidden])', timeout=30000)
    worker.page.wait_for_timeout(500)
    f.cases_after = int(worker.text('#tab-cases .cnt'))
    f.meta_after = [(m.get('status'), m.get('counts'), m.get('hbTab')) for m in run_meta(w.db)]
    f.worker_tab = worker_doc(w.db)['tab']
    f.worker = worker
    f.reopened = w.open(desk=True)
    f.reopened.page.wait_for_selector('#tab-cases .cnt', timeout=30000)
    f.reopened_cases = f.reopened.text('#tab-cases .cnt')
    yield f
    w.close()


def test_worker_announces_itself(abandoned):
    p = abandoned.presence
    assert p['kind'] == 'worker' and p['aiReady'] is True and p['ai'].startswith('Claude')


def test_app_sees_the_worker_in_settings(abandoned):
    assert 'Фоновый исполнитель на связи' in abandoned.bg_text and 'загрузчик: нет' in abandoned.bg_text


def test_app_tells_the_window_may_be_closed(abandoned):
    assert 'Окно можно закрыть — генерацию доделает фоновый исполнитель.' in abandoned.run_note


def test_closing_window_marks_the_run_as_left(abandoned):
    """Окно при закрытии пишет hb: 0 — исполнитель не ждёт, пока пульс устареет (HB_STALE = 90 с)."""
    assert abandoned.meta_at_close == [('running', 0)]


def test_worker_continues_the_generation(abandoned):
    assert abandoned.doing == 'генерация' and abandoned.running is True
    assert any('Фоновый исполнитель продолжает генерацию из закрытого окна' in t for t in abandoned.toasts)


def test_generation_is_finished_by_the_worker(abandoned):
    status, counts, tab = abandoned.meta_after[0]
    assert status == 'done' and abandoned.cases_after >= abandoned.cases_before > 0 and counts['checklist'] > 0
    assert tab == abandoned.worker_tab   # последнюю отметку «работаю» поставила вкладка исполнителя


def test_result_is_in_place_when_the_app_is_opened_again(abandoned):
    assert abandoned.reopened_cases == str(abandoned.cases_after)


def test_worker_goes_back_to_waiting(abandoned):
    wait_db(abandoned.worker.page, lambda: worker_doc(abandoned.w.db) and worker_doc(abandoned.w.db).get('doing') == '', 20, 'исполнитель свободен')


# ---------- документы в базу знаний ----------
def test_worker_parses_documents_added_in_a_closed_window(browser, tmp_path):
    w = Windows(browser)
    try:
        worker = w.open(worker=True)
        model_kb.install(worker.model)
        wait_db(worker.page, lambda: worker_doc(w.db), 20, 'присутствие исполнителя')
        wait_db(worker.page, lambda: worker.state("S.kb.index.blocks.length > 0 && !S.kb.job.busy && !S.know.busy") and worker_doc(w.db).get('doing') == '', 60, 'исполнитель разобрал пример ТЗ и свободен')
        desk = w.open(desk=True)
        model_kb.install(desk.model)
        desk.page.set_input_files('#file-input', files.write(tmp_path / 'лимиты.md', model_kb.limits_doc()))
        desk.page.wait_for_function("() => window.__qa.S.docs.some((d) => d.name === 'лимиты.md')")
        desk.page.evaluate(PAGEHIDE)
        desk.ctx.close()
        for k in [k for k in w.db.leases if k.endswith('/meta/kbjob')]:
            w.db.leases.pop(k)   # аренда закрытого окна истекла (в жизни — через 2 минуты)
        wait_db(worker.page, lambda: len(worker.state('Object.keys(S.kb.index.docs || {})')) == 2, 60, 'новый документ разобран в базу знаний')
        sections = dict(worker.state('S.kb.index.blocks.map((b) => [b.title, b.docIds.length])'))
        assert sections['Восстановление пароля'] == 2   # раздел теперь собран из двух документов
        index = next(v for k, v in w.db.store.items() if k.endswith('/meta/kb'))
        assert len(index['docs']) == 2
    finally:
        w.close()


# ---------- включение и выключение ----------
def test_switch_on_makes_the_tab_a_worker(win):
    a = win.open()
    a.open_settings('bg')
    a.page.click('#bg-body label.switch')
    wait_db(a.page, lambda: worker_doc(win.db), 10, 'присутствие исполнителя')
    assert a.page.evaluate("localStorage.getItem('qapro.worker')") == 'true'
    assert any('Эта вкладка — фоновый исполнитель' in t for t in a.toast_texts())
    assert 'Эта вкладка — фоновый исполнитель' in a.text('#bg-body')


def test_switch_off_removes_the_worker(win):
    a = win.open(worker=True)
    wait_db(a.page, lambda: worker_doc(win.db), 10, 'присутствие исполнителя')
    a.open_settings('bg')
    a.page.click('#bg-body label.switch')
    wait_db(a.page, lambda: worker_doc(win.db) is None, 10, 'присутствие удалено')
    assert a.page.evaluate("localStorage.getItem('qapro.worker')") == 'false'


def test_desktop_app_cannot_be_a_worker(win):
    """Окно приложения Claude при закрытии останавливается — фоновым исполнителем его не сделать, даже если флаг стоит."""
    a = win.open(desk=True, worker=True)
    a.open_settings('bg')
    a.page.wait_for_function("() => /фоновым исполнителем делают QA pro в Chrome/.test(document.querySelector('#bg-body')?.innerText || '')", timeout=10000)
    assert a.count('#bg-worker') == 0 and worker_doc(win.db) is None


def test_standalone_version_has_no_background_mode(win):
    a = open_app(win.browser, kind='standalone')
    win.apps.append(a)
    a.open_settings('bg')
    assert 'Фоновая работа доступна в QA pro на claude.ai.' in a.text('#bg-body') and a.count('#bg-worker') == 0
