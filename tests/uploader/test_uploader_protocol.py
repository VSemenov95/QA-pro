"""Мост между страницей QA pro и расширением (bridge.js): сообщения, два канала ответа, изолированная рамка, пульс, лимиты."""
import pytest

from tests.support.extension import manifest, wait_window_ready

COLLECT = """
(() => {
  window.__got = [];
  window.addEventListener('message', (e) => { if (e.data && e.data.source === 'qa-pro-sfera-uploader') window.__got.push(Object.assign({ ch: 'msg' }, e.data)); });
  document.addEventListener('qa-pro:from-uploader', (e) => window.__got.push(Object.assign({ ch: 'evt' }, JSON.parse(e.detail))));
  window.__post = (m) => window.postMessage(Object.assign({ source: 'qa-pro' }, m), '*');
  window.__evt = (m) => document.dispatchEvent(new CustomEvent('qa-pro:to-uploader', { detail: JSON.stringify(Object.assign({ source: 'qa-pro' }, m)) }));
})()
"""
GOT = "(id) => window.__got.filter((m) => m.id === id).map((m) => m.ch + ':' + m.type)"


@pytest.fixture
def page(env):
    env.sfera.serve('/blank.html', '<!doctype html><meta charset=utf-8><title>blank</title>')
    p = env.ext.page(env.sfera.base + '/blank.html')
    p.evaluate(COLLECT)
    return p


def wait_for(page, id, type, timeout=15000):
    page.wait_for_function("([id, t]) => window.__got.some((m) => m.id === id && m.type === t)", arg=[id, type], timeout=timeout)
    return page.evaluate("([id, t]) => window.__got.find((m) => m.id === id && m.type === t)", [id, type])


# ---------- пинг ----------
def test_ping_gets_hello_then_pong(page):
    page.evaluate("__post({ id: 'p1', type: 'SFERA_PING' })")
    wait_for(page, 'p1', 'SFERA_PONG')
    assert [x.split(':')[1] for x in page.evaluate(GOT, 'p1') if x.startswith('msg')] == ['SFERA_HELLO', 'SFERA_PONG']


def test_pong_tells_version_sfera_address_and_bridge(page, env):
    page.evaluate("__post({ id: 'p1', type: 'SFERA_PING' })")
    pong = wait_for(page, 'p1', 'SFERA_PONG')
    assert pong['version'] == manifest()['version'] and pong['baseUrl'] == env.sfera.base
    assert pong['bridge'] is False and pong['bridgeVersion'] == ''


def test_replies_come_by_both_channels(page):
    """Если окружение страницы глушит postMessage, ответ всё равно доходит событием документа."""
    page.evaluate("__post({ id: 'p1', type: 'SFERA_PING' })")
    wait_for(page, 'p1', 'SFERA_PONG')
    got = page.evaluate(GOT, 'p1')
    assert {'msg:SFERA_PONG', 'evt:SFERA_PONG', 'msg:SFERA_HELLO', 'evt:SFERA_HELLO'} <= set(got)


def test_ping_by_document_event(page):
    page.evaluate("__evt({ id: 'e1', type: 'SFERA_PING' })")
    assert wait_for(page, 'e1', 'SFERA_PONG')['version'] == manifest()['version']


def test_message_that_arrives_by_both_channels_is_handled_once(page):
    page.evaluate("(() => { const m = { id: 'd1', type: 'SFERA_PING' }; __post(m); __evt(m); __post({ id: 'd2', type: 'SFERA_PING' }); })()")
    wait_for(page, 'd2', 'SFERA_PONG')
    wait_for(page, 'd1', 'SFERA_PONG')
    got = page.evaluate(GOT, 'd1')
    assert got.count('msg:SFERA_PONG') == 1 and got.count('evt:SFERA_PONG') == 1


def test_foreign_messages_get_no_reply(page):
    page.evaluate("""(() => {
      window.postMessage({ source: 'other-script', id: 'x1', type: 'SFERA_PING' }, '*');
      window.postMessage({ source: 'qa-pro', id: 5, type: 'SFERA_PING' }, '*');
      window.postMessage({ source: 'qa-pro', id: 'x3' }, '*');
      __post({ id: 'ok', type: 'SFERA_PING' });
    })()""")
    wait_for(page, 'ok', 'SFERA_PONG')
    assert [m['id'] for m in page.evaluate('window.__got') if m['id'] != 'ok'] == []


# ---------- задание ----------
def test_upload_without_cases_is_refused(page, env):
    n = len(env.ctx.pages)
    page.evaluate("__post({ id: 'u0', type: 'SFERA_UPLOAD', cases: [], title: 'x' })")
    err = wait_for(page, 'u0', 'SFERA_ERROR')
    assert err['error'] == 'Нет тест-кейсов для загрузки.' and len(env.ctx.pages) == n   # окно загрузчика не открывалось


def test_upload_opens_the_window_with_cases(page, env):
    win = env.ext.window_from(lambda: page.evaluate("__post({ id: 'u1', type: 'SFERA_UPLOAD', title: 'Мой набор', cases: [{ ref: 'r1', name: 'Кейс А', suites: ['smoke'], steps: [] }, { ref: 'r2', name: 'Кейс Б', suites: ['regression'] }] })"))
    wait_window_ready(win)
    opened = wait_for(page, 'u1', 'SFERA_OPENED')
    assert opened['jobId'] and f'job={opened["jobId"]}' in win.url
    assert win.inner_text('#source') == 'Из QA pro · Мой набор' and win.locator('#rows input[data-i]').count() == 2


def test_closing_the_window_tells_the_page(page, env):
    win = env.ext.window_from(lambda: page.evaluate("__post({ id: 'u1', type: 'SFERA_UPLOAD', cases: [{ ref: 'r1', name: 'Кейс' }] })"))
    wait_window_ready(win)
    win.close()
    res = wait_for(page, 'u1', 'SFERA_RESULT')
    assert res['cancelled'] is True and res['results'] == []


def test_upload_takes_at_most_2000_cases(page, env):
    win = env.ext.window_from(lambda: page.evaluate("__post({ id: 'u1', type: 'SFERA_UPLOAD', cases: Array.from({ length: 2005 }, (_, i) => ({ ref: 'r' + i, name: 'К' + i })) })"))
    job = wait_for(page, 'u1', 'SFERA_OPENED')['jobId']
    stored = env.ext.sw_eval("(id) => chrome.storage.session.get('job:' + id).then((r) => r['job:' + id].cases.length)", job)
    assert stored == 2000
    win.close()


# ---------- изолированная рамка (так открыт артефакт на claude.ai) ----------
FRAME = """<!doctype html><meta charset=utf-8><body><script>
window.__log = [];
window.addEventListener('message', (e) => { if (e.data && e.data.source === 'qa-pro-sfera-uploader') window.__log.push(e.data); });
window.__origin = origin;
window.__post = (m) => window.postMessage(Object.assign({ source: 'qa-pro' }, m), '*');
</script>"""


@pytest.fixture
def frame(env):
    sf = env.sfera
    sf.serve('/frame.html', FRAME)
    sf.serve('/host.html', f'<!doctype html><meta charset=utf-8><h3>Хост</h3><iframe id=f sandbox="allow-scripts allow-popups" src="{sf.base}/frame.html" width=600 height=200></iframe>')
    env.ext.settings(lastSectionUrl=sf.base + '/project/PPAN?section=124')
    pg = env.ext.page(f'http://localhost:{sf.port}/host.html')
    pg.wait_for_selector('#f')
    fr = next(f for f in pg.frames if f.url.endswith('/frame.html'))
    fr.wait_for_function("() => window.__post")
    return fr


def frame_wait(fr, type, timeout=15000):
    fr.wait_for_function("(t) => window.__log.some((m) => m.type === t)", arg=type, timeout=timeout)
    return fr.evaluate("(t) => window.__log.find((m) => m.type === t)", type)


def test_frame_without_origin_gets_pong(frame):
    assert frame.evaluate('window.__origin') == 'null'   # рамка изолирована: у неё нет своего адреса
    frame.evaluate("__post({ id: 'p1', type: 'SFERA_PING' })")
    assert frame_wait(frame, 'SFERA_PONG')['version'] == manifest()['version']
    assert [m['type'] for m in frame.evaluate('window.__log')][:2] == ['SFERA_HELLO', 'SFERA_PONG']


def test_frame_can_upload_and_get_the_result(frame, env):
    win = env.ext.window_from(lambda: frame.evaluate("__post({ id: 'u1', type: 'SFERA_UPLOAD', title: 'из рамки', cases: [{ ref: 'r1', qaId: 'API-001', name: 'Кейс из рамки', suites: ['smoke'], steps: [{ action: '<p>a</p>', expectedResult: '<p>b</p>' }] }] })"))
    wait_window_ready(win)
    assert frame_wait(frame, 'SFERA_OPENED')['jobId']
    win.wait_for_function("() => document.querySelector('#sect').value === '124'")   # раздел запомнен с прошлой загрузки
    win.click('#go')
    win.wait_for_selector('#summary:not([hidden])')
    res = frame_wait(frame, 'SFERA_RESULT')
    assert [r['ok'] for r in res['results']] == [True] and res['results'][0]['ref'] == 'r1' and res['section'] == {'projectCode': 'PPAN', 'sectionId': '124'}
    assert [p['labels'] for p in env.sfera.posts] == [['SMOKE']]


# ---------- пульс ----------
def test_uploader_wakes_qa_pro_tabs_with_a_tick(page, env):
    """Загрузчик раз в 20–30 секунд шлёт вкладкам QA pro SFERA_TICK: фоновая вкладка просыпается."""
    env.ext.sw_eval('() => { lastTick = 0; return tickQaPro(); }')
    page.wait_for_function("() => window.__got.some((m) => m.type === 'SFERA_TICK')", timeout=15000)


# ---------- вызовы моста через загрузчик ----------