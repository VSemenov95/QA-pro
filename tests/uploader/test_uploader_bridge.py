"""Загрузка из приложения Claude через настоящий мост: страница (host:…) → мост → загрузчик в Chrome (WebSocket) → окно → Сфера (мок).

Приложение Claude — отдельный браузер без расширений с UA Electron; вызовы mcp уходят в настоящий Node-процесс моста.
"""
from types import SimpleNamespace

import pytest

from tests.support.extension import case_marks, manifest, wait_window_ready
from tests.uploader.test_uploader_flow import pick_section_from_tab, run_upload, wait_log
from tests.uploader.test_uploader_relay import upload_click, wait_until

FOUND = "() => /Мост: работает/.test(document.querySelector('#tms-body .banner')?.innerText || '')"


def open_tms(desk):
    desk.open_settings('tms')
    desk.page.wait_for_function(FOUND, timeout=15000)
    return desk


@pytest.fixture(scope='module')
def done(new_host):
    h = new_host()
    f = SimpleNamespace(h=h)
    desk = h.open_desk()
    f.n = desk.state('S.run.cases.length')
    f.bar = desk.text('#tms-bar')
    f.ext_state = h.ext.bridge_state()
    open_tms(desk)
    f.banner = desk.text('#tms-body .banner')
    desk.page.click('[data-tmb=test]')
    desk.page.wait_for_function("() => /Мост работает/.test(document.querySelector('#tms-body .case-note')?.innerText || '')", timeout=15000)
    f.check = desk.text('#tms-body .case-note')
    desk.page.keyboard.press('Escape')
    desk.page.wait_for_selector('#set-ov', state='hidden')
    win = upload_click(h, desk)
    wait_window_ready(win)
    f.source = win.inner_text('#source')
    f.rows = win.locator('#rows input[data-i]').count()
    f.log_opened = wait_log(desk, 'Chrome открылось окно')
    pick_section_from_tab(win)
    run_upload(win)
    f.summary = win.inner_text('#summary')
    f.log_done = wait_log(desk, 'загружено')
    desk.page.wait_for_function("() => [...document.querySelectorAll('#case-list article')].every((a) => /в ТМС/.test(a.textContent))")
    f.marks = case_marks(desk)
    f.posts = list(h.sfera.posts)
    f.calls = list(h.mcp.log)
    f.job = h.bridge.tool('ping')['pending']
    return f


def test_uploader_connects_to_the_bridge_by_itself(done):
    assert done.ext_state['connected'] is True and done.ext_state['version'] == '1.2.0'


def test_app_bar_says_upload_goes_through_the_bridge(done):
    assert f'Загрузить в Сферу ФТ ({done.n})' in done.bar


def test_settings_show_bridge_and_uploader(done):
    assert 'Мост: работает · версия 1.2.0' in done.banner
    assert f'Загрузчик в Chrome: подключён · версия {manifest()["version"]}' in done.banner


def test_connection_check(done):
    assert done.check == f'Мост работает (1.2.0), загрузчик в Chrome подключён ({manifest()["version"]}). Можно загружать.'


def test_window_opens_in_chrome_with_the_apps_cases(done):
    assert done.source.startswith('Из QA pro · Мой продукт') and done.source.endswith('· из приложения Claude') and done.rows == done.n


def test_app_is_told_that_the_window_is_open(done):
    assert 'В Chrome открылось окно загрузчика: выберите раздел Сферы ФТ и нажмите «Загрузить».' in done.log_opened


def test_window_summary(done):
    assert f'Создано в Сфере ФТ: {done.n} из {done.n}' in done.summary


def test_app_gets_the_result(done):
    assert f'Сфера ФТ (через мост): загружено {done.n} · проект PPAN, раздел 124' in done.log_done


def test_app_cases_are_marked(done):
    assert len(done.marks) == done.n and all(any(c.startswith('в ТМС · PPAN-T') for c in chips) for _, chips in done.marks)


def test_posts_follow_the_usual_rules(done):
    assert len(done.posts) == done.n and any(p['labels'] == ['SMOKE'] for p in done.posts) and all('AI_gen' not in p['labels'] and p['ti_regressive'] for p in done.posts)


def test_app_called_ping_upload_and_job_status(done):
    assert {'ping', 'sfera_upload', 'sfera_job'} <= set(done.calls)


def test_nothing_is_left_pending_in_the_bridge(done):
    assert done.job == 0


# ---------- окно закрыто / отмена из приложения ----------
@pytest.fixture
def desk(make_host):
    h = make_host()
    return SimpleNamespace(h=h, app=h.open_desk())


def test_closed_window_is_reported(desk):
    win = upload_click(desk.h, desk.app)
    wait_window_ready(win)
    win.close()
    assert 'Окно загрузчика закрыто без загрузки или задание отменено.' in wait_log(desk.app, 'закрыто без загрузки')


def test_cancel_in_the_app_closes_the_uploader_window(desk):
    win = upload_click(desk.h, desk.app)
    wait_window_ready(win)
    desk.app.page.click('[data-act=tms-stop]')
    assert wait_log(desk.app, 'Задание отменено') == 'Задание отменено.'
    wait_until(desk.app.page, win.is_closed, what='окно загрузчика закрыто')
    assert desk.h.bridge.tool('ping')['pending'] == 0


# ---------- загрузчик не подключён ----------
def test_job_waits_in_the_bridge_and_is_delivered_when_the_uploader_connects(desk):
    h, app = desk.h, desk.app
    h.ext.settings(desktopBridge=False)
    h.ext.reconnect_bridge()
    wait_until(app.page, lambda: not h.bridge.tool('ping')['extension']['connected'], what='загрузчик отключился от моста')
    app.page.click('[data-act=tms-upload]')
    assert 'Задание у моста, но загрузчик в Chrome сейчас не подключён' in wait_log(app, 'не подключён')
    win = h.ext.window_from(lambda: (h.ext.settings(desktopBridge=True), h.ext.reconnect_bridge()))
    wait_window_ready(win)
    wait_log(app, 'Chrome открылось окно')
    pick_section_from_tab(win)
    run_upload(win)
    n = app.state('S.run.cases.length')
    assert f'загружено {n}' in wait_log(app, 'загружено') and len(h.sfera.posts) == n


# ---------- приложение закрыли посреди загрузки ----------
def test_upload_finishes_while_the_app_is_closed_and_marks_appear_on_reopen(desk):
    h, app = desk.h, desk.app
    n = app.state('S.run.cases.length')
    win = upload_click(h, app)
    wait_window_ready(win)
    app.page.close()
    h.bridge.close_app()
    assert h.bridge.health() is not None and h.ext.bridge_state()['connected'] is True   # ядро и связь с загрузчиком живы без приложения
    pick_section_from_tab(win)
    run_upload(win)
    assert len(h.sfera.posts) == n
    wait_until(win, lambda: h.ext.sw_eval("() => chrome.storage.local.get('bridgeOutbox').then((r) => (r.bridgeOutbox || []).length)") == 0, what='мост подтвердил результат')
    h.bridge.start()
    again = h.desk_host.open()
    again.tab('cases')
    assert f'Сфера ФТ (через мост): загружено {n}' in wait_log(again, 'загружено')


# ---------- моста нет / нет доступа ----------
def test_missing_bridge_is_explained(desk):
    desk.h.mcp.up = False
    app = desk.app
    app.open_settings('tms')
    app.page.click('[data-tmb=test]')
    app.page.wait_for_function("() => /не найден/.test(document.querySelector('#tms-body .case-note')?.innerText || '')", timeout=15000)
    assert app.text('#tms-body .case-note').startswith('Мост qa-pro-bridge не найден в приложении Claude: установите его')
    assert 'Запасной путь — QA pro во вкладке Chrome — тоже не на связи.' in app.text('#tms-body .case-note')


def test_declined_confirmation_is_reported(desk):
    desk.h.mcp.deny['sfera_upload'] = 'cancelled'
    desk.app.page.click('[data-act=tms-upload]')
    assert 'Вызов моста отклонён в окне подтверждения приложения.' in wait_log(desk.app, 'отклонён')
    assert desk.app.state('S.tmsBusy') is False


def test_tool_not_allowed_for_the_page_is_explained(desk):
    desk.h.mcp.deny['sfera_upload'] = 'not_in_manifest'
    desk.app.page.click('[data-act=tms-upload]')
    assert 'Доступ QA pro к мосту выключен' in wait_log(desk.app, 'выключен')


def test_page_finds_the_bridge_under_the_manual_config_name(make_host):
    """Мост, подключённый вручную (claude_desktop_config.json), виден под ключом конфига; страница пробует оба имени и запоминает рабочее."""
    h = make_host(pre_init="window.__mcpServerName = 'host:qa-pro-bridge';")
    app = h.open_desk()
    open_tms(app)
    assert app.page.evaluate("localStorage.getItem('qapro.hostname')") == 'host:qa-pro-bridge'
    assert 'Мост: работает' in app.text('#tms-body .banner')


def test_page_remembers_the_default_bridge_name(desk):
    open_tms(desk.app)
    assert desk.app.page.evaluate("localStorage.getItem('qapro.hostname')") == 'host:QA_pro_____________________________'


# ---------- загрузчик в настройках ----------
def test_uploader_options_show_connected_bridge(desk):
    o = desk.h.ext.ext_page('options.html')
    o.wait_for_function("() => /Мост подключён: задания из QA pro в приложении Claude откроют окно загрузчика здесь\\./.test(document.querySelector('#bridge-state').textContent)", timeout=15000)


# ---------- связь загрузчика с мостом ----------
def outbox(h):
    return h.ext.sw_eval("() => chrome.storage.local.get('bridgeOutbox').then((r) => (r.bridgeOutbox || []).length)")


def test_messages_for_the_bridge_wait_until_it_confirms_them(desk):
    """Результат не теряется: пока связи с мостом нет, он лежит в хранилище загрузчика; мост подтвердил — ушёл."""
    h = desk.h
    h.ext.settings(desktopBridge=False)
    h.ext.reconnect_bridge()
    wait_until(desk.app.page, lambda: not h.bridge.tool('ping')['extension']['connected'], what='загрузчик отключился')
    h.ext.sw_eval("() => bridgeSend({ t: 'cancelled', id: 'mj-ждёт' })")
    assert outbox(h) == 1
    h.ext.settings(desktopBridge=True)
    h.ext.reconnect_bridge()
    wait_until(desk.app.page, lambda: outbox(h) == 0, what='мост подтвердил сообщение')


def test_uploader_checks_the_bridge_again_every_30_seconds(ext):
    assert ext.sw_eval("() => chrome.alarms.get('qa-pro-bridge')")['periodInMinutes'] == 0.5


def test_uploader_looks_for_the_bridge_quietly(ext):
    """Сначала обычный запрос /health: если моста нет, WebSocket не открывается (иначе браузер пишет ошибку каждые 30 секунд)."""
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    hits = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            hits.append((self.path, self.headers.get('Upgrade')))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"name":"other"}')
    srv = HTTPServer(('127.0.0.1', 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        ext.settings(bridgePort=srv.server_address[1])
        ext.reconnect_bridge()
        state = ext.bridge_state()
        assert state['connected'] is False and state['error'] == 'Мост не найден'
        assert hits and all(path == '/health' and up is None for path, up in hits)
    finally:
        srv.shutdown()
        srv.server_close()
