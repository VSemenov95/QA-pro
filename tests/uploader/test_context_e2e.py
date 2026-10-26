"""Источник контекста сквозь настоящие расширение и мост.

Браузер: QA pro (артефакт) во вкладке Chrome → загрузчик (bridge.js → фоновая часть) → окно «Доступ к контексту» → ядро моста по WebSocket → папка.
Приложение Claude: QA pro (UA Electron) → host:… (mcp) → обёртка моста → ядро → папка, разрешённая в настройках моста.
"""
import pytest

CONNECTED = '() => { const C = window.__qa.S.ctx; return !C.busy && (C.on && C.loadedAt > 0 || !!C.error); }'


def make_folder(tmp_path):
    d = tmp_path / 'qa-context'
    (d / 'rules').mkdir(parents=True)
    (d / 'rules' / 'generation.md').write_text('# Правила для агента\n\nПРАВИЛО-С-ДИСКА\n', encoding='utf-8')
    (d / 'products' / 'moi' / 'kb').mkdir(parents=True)
    (d / 'products' / 'moi' / 'kb' / 'parol.md').write_text('# Восстановление пароля\n\nСсылка действует 30 минут.\n', encoding='utf-8')
    (d / 'products' / 'moi' / 'memory.md').write_text('- [ревью] УРОК-С-ДИСКА\n', encoding='utf-8')
    return d


def open_form(app, root):
    app.open_settings('ctx')
    app.page.click('[data-ctx-act=edit]')
    app.page.click('label:has([data-ctxk=local])')
    app.page.fill('#ctx-root', str(root))
    app.page.fill('#ctx-slug', 'moi')


@pytest.fixture(scope='module')
def browser_run(new_host, tmp_path_factory):
    h = new_host()
    folder = make_folder(tmp_path_factory.mktemp('ctx'))
    app = h.open_chrome()
    open_form(app, folder)
    win = h.ext.window_from(lambda: app.page.click('[data-ctx-act=connect]'))
    win.wait_for_function("() => document.querySelector('#target').textContent.length > 0")
    ask = {'target': win.inner_text('#target'), 'origin': win.inner_text('#origin'), 'what': win.inner_text('#what')}
    win.click('#allow')
    app.page.wait_for_function(CONNECTED, timeout=20000)
    return h, app, folder, ask


def test_uploader_asks_before_giving_the_page_a_folder(browser_run):
    _, _, folder, ask = browser_run
    assert ask['target'] == str(folder) and ask['origin'] == 'http://app.test' and 'доступ к папке' in ask['what']


def test_page_reads_the_folder_through_the_uploader_and_bridge(browser_run):
    _, app, _, _ = browser_run
    assert app.state('S.ctx.error') == '' and app.state('S.ctx.channel') == 'ext'
    assert app.state('S.cfg.rules') == 'ПРАВИЛО-С-ДИСКА' and app.state('S.lessons.map((l) => l.text)') == ['УРОК-С-ДИСКА']
    assert 'Восстановление пароля' in app.call('a.kbSections(S.productId).map((x) => x.b.title)')


def test_saved_rules_land_on_disk(browser_run):
    _, app, folder, _ = browser_run
    app.call('(a.S.cfg.rules = "ПРАВИЛО-ИЗ-БРАУЗЕРА", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    path = folder / 'rules' / 'generation.md'
    app.page.wait_for_function('() => !window.__qa.S.ctx.pending.size', timeout=10000)
    assert path.read_text(encoding='utf-8') == '# Правила для агента\n\nПРАВИЛО-ИЗ-БРАУЗЕРА\n'


def test_grant_is_remembered_and_visible_in_uploader_settings(browser_run):
    h, app, folder, _ = browser_run
    grants = h.ext.sw_eval('() => getSettings().then((s) => s.ctxGrants)')
    assert grants['http://app.test']['roots'] == [str(folder)]
    app.page.click('[data-ctx-act=refresh]')   # повторное чтение — без нового окна
    app.page.wait_for_function('() => !window.__qa.S.ctx.busy', timeout=10000)
    assert app.state('S.ctx.error') == ''


def test_denied_folder(new_host, tmp_path_factory):
    h = new_host()
    folder = make_folder(tmp_path_factory.mktemp('deny'))
    app = h.open_chrome()
    open_form(app, folder)
    win = h.ext.window_from(lambda: app.page.click('[data-ctx-act=connect]'))
    win.wait_for_function("() => document.querySelector('#target').textContent.length > 0")
    win.click('#deny')
    app.page.wait_for_function(CONNECTED, timeout=20000)
    assert 'не разрешён' in app.state('S.ctx.error') and app.state('S.ctx.on') is False


@pytest.fixture(scope='module')
def desk_run(new_host, tmp_path_factory):
    folder = make_folder(tmp_path_factory.mktemp('desk'))
    h = new_host(bridge_env={'QA_PRO_CONTEXT_DIR': str(folder)})
    desk = h.desk_host.open()
    open_form(desk, folder)
    desk.page.click('[data-ctx-act=connect]')
    desk.page.wait_for_function(CONNECTED, timeout=20000)
    return h, desk, folder


def test_claude_app_reads_the_folder_through_the_bridge(desk_run):
    h, desk, _ = desk_run
    assert desk.state('S.ctx.error') == '' and desk.state('S.ctx.channel') == 'app'
    assert desk.state('S.cfg.rules') == 'ПРАВИЛО-С-ДИСКА'
    assert 'context_read' in h.mcp.log


def h_calls(run):
    return list(run[0].mcp.log)


def test_claude_app_writes_to_the_folder(desk_run):
    _, desk, folder = desk_run
    desk.call('a.addLesson("УРОК-ИЗ-ПРИЛОЖЕНИЯ", "generation")')   # в приложении автоматические записи копятся
    desk.page.wait_for_selector('[data-ctx-act=flush]', timeout=10000)
    assert '- [генерация] УРОК-ИЗ-ПРИЛОЖЕНИЯ' not in (folder / 'products' / 'moi' / 'memory.md').read_text(encoding='utf-8')
    calls = len(h_calls(desk_run))
    desk.page.click('[data-ctx-act=flush]')
    desk.page.wait_for_function('() => !window.__qa.S.ctx.pending.size && !window.__qa.S.ctx.busy', timeout=10000)
    assert h_calls(desk_run)[calls:].count('context_write') == 1
    assert '- [генерация] УРОК-ИЗ-ПРИЛОЖЕНИЯ' in (folder / 'products' / 'moi' / 'memory.md').read_text(encoding='utf-8')


def test_claude_app_page_without_context_tools_explains_what_to_do(make_host, tmp_path):
    folder = make_folder(tmp_path)
    h = make_host(bridge_env={'QA_PRO_CONTEXT_DIR': str(folder)}, pre_init="window.__mcpTools = ['ping', 'sfera_upload', 'sfera_job', 'sfera_cancel'];")
    desk = h.desk_host.open()
    open_form(desk, folder)
    desk.page.click('[data-ctx-act=connect]')
    desk.page.wait_for_function(CONNECTED, timeout=20000)
    assert 'опубликовать заново' in desk.state('S.ctx.error') and desk.state('S.ctx.on') is False
