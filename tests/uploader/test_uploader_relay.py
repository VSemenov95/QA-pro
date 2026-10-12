"""Загрузка из приложения Claude без моста: задание идёт через базу артефакта в QA pro, открытый во вкладке Chrome с загрузчиком.

Два окна с общей базой: «Chrome» (расширение, QA pro во вкладке, вкладка Сферы) и «приложение Claude» (другой браузер без расширений).
"""
import time
from types import SimpleNamespace

import pytest

from tests.support.extension import case_marks, wait_window_ready
from tests.uploader.test_uploader_flow import pick_section_from_tab, run_upload, wait_log


def wait_until(page, pred, timeout=20, what='условие'):
    """Опрос с передышками для браузера: page.wait_for_timeout даёт событиям Playwright обработаться."""
    end = time.time() + timeout
    while time.time() < end:
        v = pred()
        if v:
            return v
        page.wait_for_timeout(50)
    raise AssertionError('не дождались: ' + what)


def upload_click(r, desk):
    return r.ext.window_from(lambda: desk.page.click('[data-act=tms-upload]'))


@pytest.fixture(scope='module')
def done(new_relay):
    """Весь путь: задание из приложения → Chrome принял → окно загрузчика → загрузка → отметки в приложении."""
    r = new_relay()
    chrome = r.open_chrome()
    f = SimpleNamespace(r=r)
    wait_until(chrome.page, r.presence, what='вкладка Chrome отметилась в базе')
    f.presence = dict(r.db.store[r.presence()[0]])
    desk = r.open_desk()
    f.bar = desk.text('#tms-bar')
    desk.open_settings('tms')
    desk.page.wait_for_function("() => /на связи/.test(document.querySelector('#tms-body .banner')?.innerText || '')", timeout=15000)
    f.banner = desk.text('#tms-body .banner')
    desk.page.click('[data-tmb=test]')
    desk.page.wait_for_function("() => /Загрузчика в этом окне нет/.test(document.querySelector('#tms-body .case-note')?.innerText || '')", timeout=15000)
    f.check = desk.text('#tms-body .case-note')
    desk.page.keyboard.press('Escape')
    desk.page.wait_for_selector('#set-ov', state='hidden')
    f.n = desk.state('S.run.cases.length')
    win = upload_click(r, desk)
    wait_window_ready(win)
    f.source = win.inner_text('#source')
    f.rows = win.locator('#rows input[data-i]').count()
    f.log_opened = wait_log(desk, 'Chrome открылось окно')
    f.job_status = [r.db.store[k]['status'] for k in r.jobs()]
    pick_section_from_tab(win)
    run_upload(win)
    f.summary = win.inner_text('#summary')
    f.log_done = wait_log(desk, 'загружено')
    desk.page.wait_for_function("() => [...document.querySelectorAll('#case-list article')].every((a) => /в ТМС/.test(a.textContent))")
    f.marks = case_marks(desk)
    f.posts = list(r.sfera.posts)
    f.jobs_left = r.jobs()
    f.chrome_log = chrome.page.evaluate("document.querySelector('#tms-bar .log')?.innerText || ''")
    return f


def test_chrome_tab_announces_itself_in_the_database(done):
    assert done.presence['kind'] == 'sfera_relay' and done.presence['version'] == '1.5.0'


def test_app_bar_says_upload_goes_through_chrome(done):
    assert f'Загрузить в Сферу ФТ ({done.n})' in done.bar and 'Сфера ФТ · через QA pro в Chrome' in done.bar


def test_app_settings_explain_the_route(done):
    assert 'Вы в приложении Claude: расширений браузера здесь нет' in done.banner
    assert 'QA pro в Chrome: на связи · загрузчик 1.5.0' in done.banner


def test_app_connection_check_sees_chrome(done):
    assert done.check == 'Загрузчика в этом окне нет — загрузка пойдёт через QA pro в Chrome (на связи, загрузчик 1.5.0).'


def test_window_opens_in_chrome_with_the_apps_cases(done):
    assert done.source.startswith('Из QA pro · Мой продукт') and done.source.endswith('· из приложения Claude') and done.rows == done.n


def test_app_is_told_that_the_window_is_open(done):
    assert 'В Chrome открылось окно загрузчика: выберите раздел Сферы ФТ и нажмите «Загрузить».' in done.log_opened
    assert done.job_status == ['opened']


def test_window_summary(done):
    assert f'Создано в Сфере ФТ: {done.n} из {done.n}' in done.summary


def test_app_gets_the_result(done):
    assert f'Сфера ФТ (через Chrome): загружено {done.n} · проект PPAN, раздел 124' in done.log_done


def test_app_cases_are_marked_with_sfera_codes(done):
    codes = {p['name']: f'PPAN-T{i + 1}' for i, p in enumerate(done.posts)}
    assert len(done.marks) == done.n and all(any(c.startswith('в ТМС · PPAN-T') for c in chips) for _, chips in done.marks) and len(codes) == done.n


def test_smoke_label_and_regression_flag_are_set_as_usual(done):
    assert any(p['labels'] == ['SMOKE'] for p in done.posts) and all(p['ti_regressive'] is True for p in done.posts)


def test_finished_job_is_removed_from_the_database(done):
    assert done.jobs_left == [] and [k for k in done.r.db.store if '/sfjob-' in k] == []


def test_chrome_tab_does_not_show_the_apps_log(done):
    assert done.chrome_log == ''


# ---------- окно закрыли без загрузки ----------
def test_closing_the_window_in_chrome_cancels_the_job(make_relay):
    r = make_relay()
    wait_until(r.open_chrome().page, r.presence)
    desk = r.open_desk()
    win = upload_click(r, desk)
    wait_window_ready(win)
    win.close()
    assert 'Окно загрузчика в Chrome закрыто без загрузки.' in wait_log(desk, 'закрыто без загрузки')
    wait_until(desk.page, lambda: r.jobs() == [], what='задание удалено')
    assert r.sfera.posts == []


# ---------- Chrome не открыт ----------
@pytest.fixture
def waiting(make_relay):
    r = make_relay()
    chrome = r.open_chrome()
    wait_until(chrome.page, r.presence)
    desk = r.open_desk()
    chrome.page.close()   # Chrome с QA pro закрыли
    r.db.store.pop(r.presence()[0], None)
    desk.page.click('[data-act=tms-upload]')
    desk.page.wait_for_selector('[data-act=tms-stop]')
    return SimpleNamespace(r=r, desk=desk)


def test_job_waits_for_chrome(waiting):
    d = waiting.desk
    d.page.wait_for_function("() => /Задание ждёт QA pro в Chrome/.test(document.querySelector('#tms-bar .log')?.innerText || '')")
    assert d.text('[data-act=tms-stop]') == 'Отменить задание'
    assert [waiting.r.db.store[k]['status'] for k in waiting.r.jobs()] == ['pending']
    assert 'Открыть QA pro в браузере' in d.text('#tms-bar')


def test_waiting_job_is_picked_up_after_the_app_is_reloaded(waiting):
    d = waiting.desk
    d.reload()
    d.tab('cases')
    d.page.wait_for_function("() => /Задание ждёт QA pro в Chrome/.test(document.querySelector('#tms-bar .log')?.innerText || '')", timeout=20000)
    assert len(waiting.r.jobs()) == 1


def test_waiting_job_is_done_when_chrome_opens_qa_pro(waiting):
    r, d = waiting.r, waiting.desk
    d.page.wait_for_function("() => /Задание ждёт QA pro в Chrome/.test(document.querySelector('#tms-bar .log')?.innerText || '')")
    r.chrome_host.open(ready=False)
    win = wait_until(d.page, lambda: next((p for p in r.ext.ctx.pages if '/upload.html' in p.url), None), timeout=30, what='окно загрузчика')
    wait_window_ready(win)
    pick_section_from_tab(win)
    run_upload(win)
    wait_log(d, 'загружено')
    n = d.state('S.run.cases.length')
    wait_until(d.page, lambda: r.jobs() == [], what='задание удалено')
    assert len(r.sfera.posts) == n and 'Сфера ФТ (через Chrome): загружено' in d.text('#tms-bar .log')


def test_sender_can_cancel_a_waiting_job(waiting):
    d = waiting.desk
    d.page.click('[data-act=tms-stop]')
    assert wait_log(d, 'Задание отменено') == 'Задание отменено.'
    wait_until(d.page, lambda: waiting.r.jobs() == [], what='задание удалено')
