"""Настройки загрузчика (страница параметров), диагностика «загрузчик не видит QA pro» и вкладка QA pro, которую загрузчик держит открытой."""
import os
from types import SimpleNamespace

import pytest

from tests.support.bridge import free_port
from tests.support.extension import AppHost, manifest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QA_URL = 'https://claude.ai/artifact/TrWQGTAs4Wqe5XjZBcQFCp'


def options(ext):
    p = ext.ext_page('options.html')
    p.wait_for_function("() => document.querySelector('#base').value !== ''")
    return p


# ---------- значения по умолчанию ----------
def test_defaults(ext):
    d = ext.sw_eval('() => DEFAULTS')
    assert d['baseUrl'] == 'https://sfera-t1.ru' and d['bridgePort'] == 47321 and d['desktopBridge'] is True
    assert d['anySite'] is False and d['keepQaPro'] is False and d['qaProOrigins'] == [] and d['qaProUrl'] == QA_URL


def test_default_sfera_is_allowed_without_asking():
    m = manifest()
    assert 'https://sfera-t1.ru/*' in m['host_permissions'] and 'https://claude.ai/*' in m['host_permissions']


def test_other_sites_need_permission_from_the_user():
    assert 'https://*/*' in manifest()['optional_host_permissions'] and 'https://*/*' not in manifest()['host_permissions']


# ---------- страница параметров ----------
def test_options_show_saved_values(ext, env):
    o = options(ext)
    assert o.input_value('#base') == env.sfera.base and o.input_value('#bridge-port') == '47321' and o.is_checked('#bridge-on')


def test_wrong_sfera_address_is_refused(ext):
    o = options(ext)
    o.fill('#base', 'не адрес')
    o.click('#save')
    assert o.inner_text('#note') == 'Укажите адрес Сферы вида https://sfera.company.ru'


def test_default_sfera_address_is_saved_without_permission_request(ext):
    o = options(ext)
    o.fill('#base', 'https://sfera-t1.ru/')
    o.click('#save')
    o.wait_for_function("() => document.querySelector('#note').textContent === 'Сохранено.'")
    assert ext.sw_eval('() => getSettings().then((s) => s.baseUrl)') == 'https://sfera-t1.ru'


@pytest.mark.parametrize('port', ['80', '70000', 'abc', ''])
def test_bridge_port_is_validated(ext, port):
    o = options(ext)
    o.fill('#bridge-port', port)
    o.dispatch_event('#bridge-port', 'change')
    assert o.inner_text('#keep-note') == 'Порт — число от 1024 до 65535.'


def test_bridge_port_is_saved(ext):
    o = options(ext)
    port = free_port()
    o.fill('#bridge-port', str(port))
    o.dispatch_event('#bridge-port', 'change')
    o.wait_for_function("() => document.querySelector('#keep-note').textContent === 'Сохранено.'")
    assert ext.sw_eval('() => getSettings().then((s) => s.bridgePort)') == port


def test_bridge_switch(ext):
    o = options(ext)
    o.uncheck('#bridge-on')
    o.wait_for_function("() => document.querySelector('#bridge-state').textContent === 'Связь с приложением Claude выключена.'")
    assert ext.sw_eval('() => getSettings().then((s) => s.desktopBridge)') is False


def test_missing_bridge_is_explained(ext):
    ext.settings(bridgePort=free_port())
    o = options(ext)
    o.wait_for_function("() => /Мост не найден/.test(document.querySelector('#bridge-state').textContent)")
    assert 'Установите его в приложении Claude' in o.inner_text('#bridge-state') and 'раз в 30 секунд' in o.inner_text('#bridge-state')


def test_found_bridge_is_shown_as_connected(ext, make_bridge):
    b = make_bridge()
    ext.settings(bridgePort=b.port)
    o = options(ext)
    o.wait_for_function("() => /Мост подключён/.test(document.querySelector('#bridge-state').textContent)", timeout=15000)
    assert b.tool('ping')['extension']['connected'] is True


# ---------- «Держать QA pro открытым» ----------
@pytest.fixture
def keep(env):
    env.ctx.route('https://claude.ai/artifact/**', lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body='<!doctype html><title>Claude Artifact</title><p>QA pro</p>'))
    o = options(env.ext)
    o.evaluate("() => document.querySelectorAll('details').forEach((d) => { d.open = true; })")
    return SimpleNamespace(env=env, ext=env.ext, o=o)


def qa_tabs(ext):
    return ext.sw_eval("() => chrome.tabs.query({}).then((ts) => ts.filter((t) => (t.url || t.pendingUrl || '').includes('claude.ai')).map((t) => ({ url: t.url || t.pendingUrl, pinned: t.pinned, active: t.active, autoDiscardable: t.autoDiscardable })))")


def test_keep_open_is_off_by_default(keep):
    assert keep.o.input_value('#qa-url') == QA_URL and not keep.o.is_checked('#keep') and qa_tabs(keep.ext) == []


def test_keep_open_opens_a_pinned_background_tab(keep):
    keep.o.check('#keep')
    keep.o.wait_for_function("() => document.querySelector('#keep-note').textContent !== ''")
    assert keep.o.inner_text('#keep-note') == 'Включено: вкладка QA pro открыта и закреплена.'
    tabs = qa_tabs(keep.ext)
    assert len(tabs) == 1 and tabs[0]['url'] == QA_URL and tabs[0]['pinned'] is True and tabs[0]['active'] is False


def test_the_kept_tab_is_never_unloaded_from_memory(keep):
    keep.o.check('#keep')
    keep.o.wait_for_function("() => document.querySelector('#keep-note').textContent !== ''")
    assert qa_tabs(keep.ext)[0]['autoDiscardable'] is False


def test_the_kept_tab_is_not_opened_twice(keep):
    keep.o.check('#keep')
    keep.o.wait_for_function("() => document.querySelector('#keep-note').textContent !== ''")
    keep.ext.sw_eval('() => ensureQaProTab()')
    keep.ext.sw_eval('() => ensureQaProTab()')
    assert len(qa_tabs(keep.ext)) == 1


def test_the_kept_tab_sees_the_uploader(keep):
    with keep.env.ctx.expect_page() as pi:
        keep.o.check('#keep')
    qa = pi.value
    qa.wait_for_load_state()
    answer = qa.evaluate("""() => new Promise((r) => { const id = 't1'; window.addEventListener('message', (e) => { if (e.data && e.data.id === id && e.data.type === 'SFERA_PONG') r('pong'); });
      window.postMessage({ source: 'qa-pro', id, type: 'SFERA_PING' }, '*'); setTimeout(() => r('none'), 8000); })""")
    assert answer == 'pong'


def test_keep_open_needs_an_https_link(keep):
    keep.o.fill('#qa-url', 'http://qa-pro.local/')
    keep.o.check('#keep')
    assert keep.o.inner_text('#keep-note') == 'Укажите ссылку на QA pro вида https://claude.ai/artifact/…'
    assert qa_tabs(keep.ext) == []


# ---------- «загрузчик не видит QA pro»: QA pro на чужом https-адресе ----------
FOREIGN = 'https://qa-pro.example/qa-pro.html'


@pytest.fixture(scope='module')
def diag(new_env):
    """QA pro открыт на адресе, которого нет в списке расширения; потом включается «Работать на любых сайтах»."""
    env = new_env(hosts=['https://*/*'])   # в тесте разрешение «любые сайты» уже выдано (в Chrome его выдаёт пользователь)
    with open(os.path.join(ROOT, 'qa-pro.html'), 'rb') as f:
        html = f.read()
    env.ctx.route('https://qa-pro.example/**', lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=html))
    host = AppHost(env.ctx, kind='standalone', url=FOREIGN)
    qa = host.open()
    d = SimpleNamespace(env=env, qa=qa, host=host)

    def tms_pane(app):
        app.open_settings('tms')
        app.page.wait_for_function("() => document.querySelector('#tms-body .banner')?.innerText.length > 20 && !/Проверяю/.test(document.querySelector('#tms-body .banner').innerText)", timeout=15000)
        return app.text('#tms-body .banner')

    def check(app):
        app.page.click('[data-tmb=test]')
        app.page.wait_for_function("() => { const n = document.querySelector('#tms-body .case-note'); return n && !/Проверяю/.test(n.innerText); }", timeout=15000)
        return app.text('#tms-body .case-note')
    d.banner_before = tms_pane(qa)
    d.test_before = check(qa)
    d.injected = env.ext.sw_eval('() => saveSettings({ anySite: true }).then(() => syncAnySite(true)).then(() => injectOpenTabs())')
    d.test_after = check(qa)
    d.banner_after = qa.text('#tms-body .banner')
    qa.reload()
    d.banner_reloaded = tms_pane(qa)
    o = env.ext.ext_page('options.html')
    o.wait_for_function("() => document.querySelector('#pings').innerText.includes('qa-pro.example')")
    d.any_checked, d.pings = o.is_checked('#any'), o.inner_text('#pings')
    return d


def test_foreign_page_is_reported_as_not_seen(diag):
    assert 'Загрузчик не видит эту страницу' in diag.banner_before
    assert 'Работать на любых сайтах' in diag.banner_before   # подсказка, что включить


def test_connection_check_explains_the_same(diag):
    assert diag.test_before.startswith('Загрузчик не видит эту страницу. Обновите страницу (Ctrl+F5)')


def test_any_site_mode_connects_to_the_open_tab_without_reload(diag):
    assert diag.injected >= 1 and diag.test_after.startswith('Загрузчик найден, версия ' + manifest()['version'])
    assert 'Загрузчик найден' in diag.banner_after


def test_any_site_mode_survives_page_reload(diag):
    assert 'Загрузчик найден' in diag.banner_reloaded


def test_options_show_any_site_and_the_recent_calls(diag):
    assert diag.any_checked is True and 'qa-pro.example/qa-pro.html' in diag.pings


def test_page_that_filters_postmessage_still_gets_answers(env):
    """Окружение, глушащее входящие postMessage страницы: ответ загрузчика приходит событием документа."""
    host = AppHost(env.ctx, kind='standalone', url=env.sfera.base + '/qa-pro.html', init="""(() => { const orig = EventTarget.prototype.addEventListener;
      EventTarget.prototype.addEventListener = function (type, fn, opts) {
        if (this === window && type === 'message') { const f = fn; fn = function (e) { if (e.data && e.data.source === 'qa-pro-sfera-uploader') return; return f.call(this, e); }; }
        return orig.call(this, type, fn, opts); }; })();""")
    qa = host.open()
    qa.open_settings('tms')
    qa.page.click('[data-tmb=test]')
    qa.page.wait_for_function("() => /Загрузчик найден/.test(document.querySelector('#tms-body .case-note')?.innerText || '')", timeout=15000)


def test_own_qa_pro_address_is_connected_without_the_any_site_mode(new_env):
    """«Где открыт QA pro — если на своём веб-сервере»: адрес из настроек подключается к странице, даже уже открытой."""
    env = new_env(hosts=['https://*/*'])
    with open(os.path.join(ROOT, 'qa-pro.html'), 'rb') as f:
        html = f.read()
    env.ctx.route('https://qa-pro.example/**', lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=html))
    qa = AppHost(env.ctx, kind='standalone', url=FOREIGN).open()
    qa.open_settings('tms')
    qa.page.click('[data-tmb=test]')
    qa.page.wait_for_function("() => /не видит/.test(document.querySelector('#tms-body .case-note')?.innerText || '')", timeout=15000)
    n = env.ext.sw_eval("() => saveSettings({ qaProOrigins: ['https://qa-pro.example'] }).then((s) => syncQaProScripts(s.qaProOrigins)).then(() => injectOpenTabs())")
    qa.page.click('[data-tmb=test]')
    qa.page.wait_for_function("() => /Загрузчик найден/.test(document.querySelector('#tms-body .case-note')?.innerText || '')", timeout=15000)
    assert n >= 1
