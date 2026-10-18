"""Мост qa-pro-bridge без браузера: настоящие Node-процессы (обёртка MCP и фоновое ядро), «загрузчик» — WebSocket-клиент из тестов.

Что проверяется: список инструментов, задания (очередь, доставка, результат, отмена, хранение на диске), переживание выхода из приложения Claude,
защита порта (секрет, Origin, только 127.0.0.1), переход на новое ядро.
"""
import json
import os
import re
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from tests.support.bridge import BRIDGE_SRC, ROOT, Bridge, free_port, http, until

with open(os.path.join(BRIDGE_SRC, 'manifest.json'), encoding='utf-8') as _f:
    MANIFEST = json.load(_f)
APP2 = open(os.path.join(ROOT, 'app2.js'), encoding='utf-8').read()


def cases(n=1, **kw):
    return [dict({'ref': f'r{i}', 'name': f'Кейс {i}', 'suites': ['smoke']}, **kw) for i in range(n)]


def upload(br, n=1, **kw):
    return br.tool('sfera_upload', {'title': 'T', 'cases': cases(n, **kw)})


def job_msg(ws):
    return ws.wait(lambda m: m['t'] == 'job')


# ---------- инструменты и манифест ----------
def test_tool_names(bridge):
    assert {t['name'] for t in bridge.tools()} == {'ping', 'sfera_upload', 'sfera_job', 'sfera_cancel', 'sfera_call', 'project_list', 'project_read', 'project_write'}


def test_manifest_lists_the_same_tools(bridge):
    assert {t['name'] for t in MANIFEST['tools']} == {t['name'] for t in bridge.tools()}


@pytest.mark.parametrize('name,ro', [('ping', True), ('sfera_job', True), ('sfera_upload', False), ('sfera_cancel', False)])
def test_only_reading_tools_are_marked_read_only(bridge, name, ro):
    """Приложение Claude не спрашивает подтверждение только у инструментов чтения (ping, sfera_job)."""
    t = next(t for t in bridge.tools() if t['name'] == name)
    assert bool(t['annotations'].get('readOnlyHint')) is ro


def test_job_wait_is_limited_to_25_seconds_in_schema(bridge):
    t = next(t for t in bridge.tools() if t['name'] == 'sfera_job')
    assert t['inputSchema']['properties']['waitMs']['maximum'] == 25000


def test_initialize_reports_name_and_version(bridge):
    info = bridge.rpc('initialize', {'protocolVersion': '2025-06-18'})['result']['serverInfo']
    assert info['name'] == 'qa-pro-bridge' and info['version'] == MANIFEST['version']
    assert info['title'] == MANIFEST['display_name']


def test_unknown_method_is_an_error(bridge):
    assert bridge.rpc('no/such/method')['error']['code'] == -32601


def test_unknown_tool_is_a_tool_error(bridge):
    r = bridge.call('no_such_tool')
    assert r['isError'] and 'Неизвестный инструмент' in r['content'][0]['text']


def test_host_name_is_built_from_display_name():
    """Приложение Claude называет мост по отображаемому имени: всё, кроме [A-Za-z0-9_-], — «_» (35 символов после host:); его же ищет QA pro."""
    host = 'host:' + re.sub(r'[^A-Za-z0-9_-]', '_', MANIFEST['display_name'])
    assert host == 'host:QA_pro_____________________________' and len(host) - 5 == 35
    assert re.search(r"HOST_DISPLAY = '([^']+)'", APP2).group(1) == MANIFEST['display_name']


# ---------- состояние ----------
def test_ping(bridge):
    p = bridge.tool('ping')
    assert p['ok'] and p['name'] == 'qa-pro-bridge' and p['version'] == MANIFEST['version']
    assert p['listening'] is True and p['port'] == bridge.port and p['pending'] == 0
    assert p['extension']['connected'] is False


def test_core_runs_as_separate_background_process(bridge):
    """С версии 1.1 ядро — отдельный процесс (переживает приложение), а не часть обёртки."""
    assert bridge.tool('ping')['core'] == 'background'
    assert bridge.health()['pid'] != bridge.proc.pid


def test_secret_is_saved_for_the_wrapper(bridge):
    assert re.fullmatch(r'[a-f0-9]{64}', bridge.token())


# ---------- задания ----------
def test_upload_without_uploader_waits_in_the_bridge(bridge):
    j = upload(bridge, 2)
    assert j['status'] == 'queued' and j['count'] == 2 and j['jobId'].startswith('mj-') and j['title'] == 'T'
    assert bridge.tool('ping')['pending'] == 1


def test_queued_job_is_sent_when_uploader_connects(bridge):
    j = upload(bridge)
    m = job_msg(bridge.ws())
    assert m['id'] == j['jobId'] and m['title'] == 'T' and m['cases'][0]['name'] == 'Кейс 0'
    until(lambda: bridge.tool('sfera_job', {'jobId': j['jobId']})['status'] == 'sent', what='статус sent')


def test_job_is_sent_at_once_when_uploader_is_connected(bridge):
    ws = bridge.ws()
    until(lambda: bridge.tool('ping')['extension']['connected'], what='загрузчик подключён')
    j = upload(bridge)
    assert j['status'] == 'sent' and job_msg(ws)['id'] == j['jobId']


def test_uploader_hello_is_visible_in_ping(bridge):
    bridge.ws(hello='1.5.0')
    e = until(lambda: bridge.tool('ping')['extension'].get('version'), what='версия загрузчика')
    assert e == '1.5.0' and bridge.tool('ping')['extension']['connected']


def test_opened_window_and_result_are_tracked(bridge):
    ws = bridge.ws()
    j = upload(bridge, 2)
    jid = job_msg(ws)['id']
    ws.send({'t': 'opened', 'id': jid})
    assert ws.wait(lambda m: m['t'] == 'ack' and m['kind'] == 'opened')['id'] == jid
    assert until(lambda: bridge.tool('sfera_job', {'jobId': jid})['status'] == 'opened', what='статус opened')
    ws.send({'t': 'result', 'id': jid, 'results': [{'ref': 'r0', 'ok': True, 'code': 'PPAN-T7'}, {'ref': 'r1', 'ok': False, 'status': 400, 'error': 'bad'}], 'section': {'projectCode': 'PPAN', 'sectionId': 124}})
    assert ws.wait(lambda m: m['t'] == 'ack' and m['kind'] == 'result')
    done = until(lambda: (lambda p: p if p['status'] == 'done' else None)(bridge.tool('sfera_job', {'jobId': jid})), what='статус done')
    assert done['results'] == [{'ref': 'r0', 'ok': True, 'code': 'PPAN-T7', 'status': 0, 'error': ''}, {'ref': 'r1', 'ok': False, 'code': '', 'status': 400, 'error': 'bad'}]
    assert done['section'] == {'projectCode': 'PPAN', 'sectionId': 124} and j['jobId'] == jid


def test_result_error_text_is_shortened(bridge):
    ws = bridge.ws()
    jid = upload(bridge)['jobId']
    job_msg(ws)
    ws.send({'t': 'result', 'id': jid, 'results': [{'ref': 'r0', 'ok': False, 'error': 'x' * 500}]})
    r = until(lambda: bridge.tool('sfera_job', {'jobId': jid})['results'], what='результат')
    assert len(r[0]['error']) == 300


def test_uploader_closed_window_cancels_the_job(bridge):
    ws = bridge.ws()
    jid = upload(bridge)['jobId']
    job_msg(ws)
    ws.send({'t': 'cancelled', 'id': jid})
    assert until(lambda: bridge.tool('sfera_job', {'jobId': jid})['status'] == 'cancelled', what='cancelled')


def test_uploader_error_is_reported(bridge):
    ws = bridge.ws()
    jid = upload(bridge)['jobId']
    job_msg(ws)
    ws.send({'t': 'error', 'id': jid, 'error': 'Нет входа в Сферу'})
    j = until(lambda: (lambda p: p if p['status'] == 'error' else None)(bridge.tool('sfera_job', {'jobId': jid})), what='error')
    assert j['error'] == 'Нет входа в Сферу'


def test_finished_job_does_not_change_after_late_messages(bridge):
    ws = bridge.ws()
    jid = upload(bridge)['jobId']
    job_msg(ws)
    ws.send({'t': 'result', 'id': jid, 'results': [{'ref': 'r0', 'ok': True, 'code': 'A-1'}]})
    until(lambda: bridge.tool('sfera_job', {'jobId': jid})['status'] == 'done', what='done')
    ws.send({'t': 'cancelled', 'id': jid})
    ws.send({'t': 'hb'})
    ws.wait(lambda m: m['t'] == 'ack' and m['kind'] == 'cancelled')
    assert bridge.tool('sfera_job', {'jobId': jid})['status'] == 'done'


def test_unknown_job_is_an_error(bridge):
    r = bridge.call('sfera_job', {'jobId': 'mj-nope'})
    assert r['isError'] and 'Задание не найдено' in r['content'][0]['text']


def test_upload_without_cases_is_an_error(bridge):
    r = bridge.call('sfera_upload', {'cases': []})
    assert r['isError'] and 'Нет тест-кейсов' in r['content'][0]['text']


def test_default_title(bridge):
    ws = bridge.ws()
    bridge.tool('sfera_upload', {'cases': cases()})
    assert job_msg(ws)['title'] == 'QA pro'


def test_case_fields_are_limited_and_cleaned(bridge):
    ws = bridge.ws()
    bridge.tool('sfera_upload', {'cases': [{'ref': 'a', 'name': 'н' * 300, 'evil': 'x', 'steps': [{'action': '<p>a</p>', 'expectedResult': '<p>b</p>'}]}]})
    c = job_msg(ws)['cases'][0]
    assert len(c['name']) == 256 and 'evil' not in c
    assert c['steps'] == [{'action': '<p>a</p>', 'expectedResult': '<p>b</p>'}]


def test_job_takes_at_most_2000_cases(bridge):
    assert upload(bridge, 2001)['count'] == 2000


# ---------- ожидание изменения (долгий опрос) ----------
def test_job_poll_waits_when_nothing_changes(bridge):
    j = upload(bridge)
    t0 = time.time()
    p = bridge.tool('sfera_job', {'jobId': j['jobId'], 'since': j['updatedAt'], 'waitMs': 1200})
    assert time.time() - t0 >= 1.0 and p['status'] == 'queued'


def test_job_poll_without_since_answers_at_once(bridge):
    j = upload(bridge)
    t0 = time.time()
    bridge.tool('sfera_job', {'jobId': j['jobId'], 'waitMs': 5000})
    assert time.time() - t0 < 2


def test_job_poll_wakes_up_on_change(bridge):
    ws = bridge.ws()
    j = upload(bridge)
    job_msg(ws)
    j = bridge.tool('sfera_job', {'jobId': j['jobId']})
    out = {}
    th = threading.Thread(target=lambda: out.update(p=bridge.tool('sfera_job', {'jobId': j['jobId'], 'since': j['updatedAt'], 'waitMs': 20000}), t=time.time()))
    t0 = time.time()
    th.start()
    time.sleep(0.3)   # опрос уже ждёт на стороне ядра
    ws.send({'t': 'opened', 'id': j['jobId']})
    th.join(15)
    assert out['p']['status'] == 'opened' and out['t'] - t0 < 8


# ---------- отмена ----------
def test_cancel_queued_job(bridge):
    j = upload(bridge)
    assert bridge.tool('sfera_cancel', {'jobId': j['jobId']})['status'] == 'cancelled'
    ws = bridge.ws(hello='1.5.0')
    until(lambda: bridge.tool('ping')['extension'].get('version'), what='hello обработан')
    assert ws.of('job') == []


def test_cancel_sent_job_tells_the_uploader(bridge):
    ws = bridge.ws()
    j = upload(bridge)
    job_msg(ws)
    assert bridge.tool('sfera_cancel', {'jobId': j['jobId']})['status'] == 'cancelled'
    assert ws.wait(lambda m: m['t'] == 'cancel')['id'] == j['jobId']


def test_result_after_cancel_is_ignored(bridge):
    ws = bridge.ws()
    j = upload(bridge)
    job_msg(ws)
    bridge.tool('sfera_cancel', {'jobId': j['jobId']})
    ws.send({'t': 'result', 'id': j['jobId'], 'results': [{'ref': 'r0', 'ok': True, 'code': 'X'}]})
    ws.wait(lambda m: m['t'] == 'ack' and m['kind'] == 'result')
    p = bridge.tool('sfera_job', {'jobId': j['jobId']})
    assert p['status'] == 'cancelled' and p['results'] is None


def test_cancel_finished_job_keeps_it_finished(bridge):
    ws = bridge.ws()
    j = upload(bridge)
    job_msg(ws)
    ws.send({'t': 'result', 'id': j['jobId'], 'results': [{'ref': 'r0', 'ok': True, 'code': 'X'}]})
    until(lambda: bridge.tool('sfera_job', {'jobId': j['jobId']})['status'] == 'done', what='done')
    assert bridge.tool('sfera_cancel', {'jobId': j['jobId']})['status'] == 'done'


def test_cancel_unknown_job_is_an_error(bridge):
    assert bridge.call('sfera_cancel', {'jobId': 'mj-nope'})['isError']


# ---------- загрузчик: подключение ----------
def test_new_uploader_connection_replaces_the_old_one(bridge):
    first = bridge.ws(hello='1.4.0')
    until(lambda: bridge.tool('ping')['extension'].get('version') == '1.4.0', what='первый загрузчик')
    bridge.ws(hello='1.5.0')
    assert first.wait_closed(5)
    assert until(lambda: bridge.tool('ping')['extension'].get('version') == '1.5.0', what='второй загрузчик')


def test_ping_after_uploader_left(bridge):
    ws = bridge.ws()
    until(lambda: bridge.tool('ping')['extension']['connected'], what='подключён')
    ws.close()
    e = until(lambda: (lambda x: x if not x['connected'] else None)(bridge.tool('ping')['extension']), what='отключён')
    assert e['lastSeen']


def test_uploader_is_sent_only_jobs_once(bridge):
    ws = bridge.ws()
    upload(bridge)
    job_msg(ws)
    ws.send({'t': 'hello', 'version': '1.5.0'})   # повторное приветствие не отправляет задание заново
    ws.send({'t': 'hb'})
    until(lambda: bridge.tool('ping')['extension'].get('version') == '1.5.0', what='hello')
    assert len(ws.of('job')) == 1


# ---------- ядро переживает приложение ----------
def test_core_survives_closing_the_app_and_still_delivers(bridge):
    j = upload(bridge)
    bridge.close_app()
    assert bridge.proc.poll() is not None
    assert bridge.health() is not None
    assert job_msg(bridge.ws())['id'] == j['jobId']


def test_result_is_stored_when_the_app_is_closed(bridge):
    ws = bridge.ws()
    j = upload(bridge)
    job_msg(ws)
    bridge.close_app()
    ws.send({'t': 'result', 'id': j['jobId'], 'results': [{'ref': 'r0', 'ok': True, 'code': 'PPAN-T7'}]})
    ws.wait(lambda m: m['t'] == 'ack' and m['kind'] == 'result')
    path = os.path.join(bridge.dir, 'jobs.json')
    until(lambda: os.path.exists(path) and any(x['id'] == j['jobId'] and x['status'] == 'done' for x in json.load(open(path, encoding='utf-8'))), what='задание на диске')


def test_jobs_survive_core_restart(make_bridge):
    b1 = make_bridge()
    ws = b1.ws()
    j = upload(b1)
    job_msg(ws)
    ws.send({'t': 'result', 'id': j['jobId'], 'results': [{'ref': 'r0', 'ok': True, 'code': 'PPAN-T7'}], 'section': {'projectCode': 'PPAN', 'sectionId': 1}})
    until(lambda: b1.tool('sfera_job', {'jobId': j['jobId']})['status'] == 'done', what='done')
    until(lambda: os.path.exists(os.path.join(b1.dir, 'jobs.json')) and 'PPAN-T7' in open(os.path.join(b1.dir, 'jobs.json'), encoding='utf-8').read(), what='запись на диск')
    b1.close_app()
    b1.shutdown_core()
    assert b1.health() is None
    b2 = Bridge(b1.dir, port=b1.port).start()
    try:
        p = b2.tool('sfera_job', {'jobId': j['jobId']})
        assert p['status'] == 'done' and p['results'][0]['code'] == 'PPAN-T7' and b2.tool('ping')['core'] == 'background'
    finally:
        b2.stop()


def test_jobs_older_than_a_day_are_dropped(make_bridge):
    b = make_bridge(start=False)
    now = int(time.time() * 1000)
    mk = lambda i, age: {'id': i, 'title': 't', 'cases': [{'name': 'x'}], 'status': 'queued', 'createdAt': now - age, 'updatedAt': now - age}  # noqa: E731
    with open(os.path.join(b.dir, 'jobs.json'), 'w', encoding='utf-8') as f:
        json.dump([mk('mj-old', 25 * 3600e3), mk('mj-new', 3600e3)], f)
    b.start()
    assert b.tool('sfera_job', {'jobId': 'mj-new'})['status'] == 'queued'
    r = b.call('sfera_job', {'jobId': 'mj-old'})
    assert r['isError'] and 'Задание не найдено' in r['content'][0]['text']


# ---------- защита порта ----------
def test_rpc_needs_the_secret(bridge):
    assert http(bridge.port, 'POST', '/rpc', {'tool': 'ping'})[0] == 403


def test_rpc_with_wrong_secret(bridge):
    assert http(bridge.port, 'POST', '/rpc', {'tool': 'ping'}, {'x-qa-pro-bridge-token': 'a' * 64})[0] == 403


def test_rpc_with_secret_works(bridge):
    code, body = http(bridge.port, 'POST', '/rpc', {'tool': 'ping'}, {'x-qa-pro-bridge-token': bridge.token()})
    assert code == 200 and body['ok'] and body['result']['name'] == 'qa-pro-bridge'


def test_rpc_from_a_web_page_is_refused_even_with_secret(bridge):
    """Страница сайта (заголовок Origin) не может вызывать мост, даже зная секрет."""
    code, _ = http(bridge.port, 'POST', '/rpc', {'tool': 'ping'}, {'x-qa-pro-bridge-token': bridge.token(), 'Origin': 'https://evil.example'})
    assert code == 403


def test_shutdown_needs_the_secret(bridge):
    assert http(bridge.port, 'POST', '/shutdown', {})[0] == 403
    assert bridge.health() is not None


def test_health_is_open_and_unknown_paths_are_404(bridge):
    assert http(bridge.port, 'GET', '/health')[1]['name'] == 'qa-pro-bridge'
    assert http(bridge.port, 'GET', '/secret')[0] == 404


@pytest.mark.parametrize('origin,path', [('https://evil.example', '/ext'), (None, '/ext'), ('http://localhost:3000', '/ext'), ('chrome-extension://abcdefghijklmnopabcdefghijklmnop', '/other')])
def test_websocket_only_from_the_browser_extension(bridge, origin, path):
    assert bridge.ws(origin=origin, path=path, hello=None).status == 403


def test_websocket_from_extension_origin_is_accepted(bridge):
    assert bridge.ws(hello=None).status == 101


def test_bridge_listens_on_loopback_only(bridge):
    """На другом адресе того же компьютера (127.0.0.2) порт моста закрыт: мост не виден из сети."""
    s = socket.socket()
    s.settimeout(2)
    try:
        err = s.connect_ex(('127.0.0.2', bridge.port))
    finally:
        s.close()
    if err not in (0, 111):
        pytest.skip('127.0.0.2 недоступен на этой системе')
    assert err == 111


@pytest.mark.xfail(strict=True, reason='БАГ: запрос к /rpc с секретом из не-ASCII байт (например, 0xE9) остаётся без ответа: timingSafeEqual в authed() (core.js) падает с RangeError, ядро отвечает 403 не всегда')
def test_garbage_secret_gets_403_not_a_hang(bridge):
    s = socket.create_connection(('127.0.0.1', bridge.port), timeout=3)
    s.sendall(b'POST /rpc HTTP/1.1\r\nHost: x\r\nContent-Length: 2\r\nx-qa-pro-bridge-token: ' + b'\xe9' * 40 + b'\r\n\r\n{}')
    try:
        head = s.recv(100)
    except socket.timeout:
        head = b''
    finally:
        s.close()
    assert head.startswith(b'HTTP/1.1 403')


# ---------- порт занят / старое ядро ----------
class _Foreign(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{}')


def test_busy_port_is_explained(make_bridge):
    srv = HTTPServer(('127.0.0.1', 0), _Foreign)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        b = make_bridge(port=srv.server_address[1], ping=False)
        for tool in ('ping', 'sfera_upload'):
            r = b.call(tool, {'cases': cases()})
            assert r['isError'] and 'занят другой программой' in r['content'][0]['text']
    finally:
        srv.shutdown()
        srv.server_close()


def test_old_background_core_is_replaced(make_bridge):
    """Ядро старой версии, оставшееся от прежней установки, обёртка останавливает (/shutdown с секретом) и запускает своё."""
    port = free_port()
    seen = {}
    holder = {}

    class Old(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _j(self, o):
            b = json.dumps(o).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            self._j({'ok': True, 'name': 'qa-pro-bridge', 'version': '1.0.0', 'mode': 'standalone', 'pid': 1})

        def do_POST(self):
            seen['token'] = self.headers.get('x-qa-pro-bridge-token')
            self._j({'ok': True})
            threading.Thread(target=lambda: (holder['srv'].shutdown(), holder['srv'].server_close()), daemon=True).start()

    srv = holder['srv'] = HTTPServer(('127.0.0.1', port), Old)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    b = make_bridge(port=port, start=False)
    token = 'ab' * 32
    with open(os.path.join(b.dir, 'token'), 'w', encoding='utf-8') as f:
        f.write(token)
    b.start()
    assert seen['token'] == token
    p = b.tool('ping')
    assert p['version'] == MANIFEST['version'] and p['core'] == 'background'

def test_wrapper_ignores_notifications_and_bad_lines(bridge):
    bridge.raw('{"jsonrpc":"2.0","method":"notifications/initialized"}')
    bridge.raw('это не json')
    assert bridge.tool('ping')['ok']
