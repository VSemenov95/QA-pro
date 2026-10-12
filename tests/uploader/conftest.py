"""Фикстуры для загрузчика в Сферу ФТ, расширения Chrome и моста приложения Claude.

Расширению нужен launch_persistent_context с --load-extension, поэтому здесь своя «среда» (Env): мок Сферы, Chrome с расширением и
страницы QA pro. Мост — настоящий Node.js-процесс; нет Node — тесты моста пропускаются.
"""
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.support import bridge as bridge_mod  # noqa: E402
from tests.support.db import MemoryDB  # noqa: E402
from tests.support.extension import DESK_UA, AppHost, ExtChrome, prepare_cases, watch_errors  # noqa: E402
from tests.support.model import MockModel  # noqa: E402
from tests.support.sfera import SferaMock  # noqa: E402

SFERA_SECTION = '/project/PPAN?section=124'


class Env:
    """Chrome с загрузчиком + мок Сферы (+ «модель» для автономной QA pro). Закрывается через close()."""

    def __init__(self, browser, tmp, hosts=(), matches=(), login=True, sfera_tab=False):
        self.model = MockModel()
        self.sfera = SferaMock(model=self.model).start()
        self.ext = ExtChrome(browser.browser_type, tmp, hosts, matches)
        self.ext.settings(baseUrl=self.sfera.base)
        if login:
            self.ext.login(self.sfera.base)
        self.sfera_tab = self.ext.page(self.sfera.base + SFERA_SECTION) if sfera_tab else None
        self._standalone = None

    @property
    def ctx(self):
        return self.ext.ctx

    def standalone(self):
        """Хост автономной версии QA pro, открываемой с адреса мока Сферы (http://127.0.0.1:порт/qa-pro.html)."""
        if self._standalone is None:
            self._standalone = AppHost(self.ctx, kind='standalone', model=self.model, url=self.sfera.base + '/qa-pro.html',
                                       local_storage={'qapro.conns': [self.sfera.conn()]}, settings={'genAI': 'conn:p-mock'})
        return self._standalone

    def qa(self):
        """Автономная QA pro с готовыми кейсами на вкладке «Тест-кейсы»."""
        app = self.standalone().open()
        return prepare_cases(app)

    def close(self):
        errs = list(self.ext.errors)
        self.ext.close()
        self.sfera.stop()
        assert not errs, 'ошибки на страницах: ' + '; '.join(errs[:3])


class Relay:
    """Два окна с общей базой артефакта: QA pro в Chrome с загрузчиком и QA pro в «приложении Claude» (другой браузер без расширений, UA Electron)."""

    def __init__(self, browser, tmp, **mcp_kw):
        self.env = Env(browser, tmp, hosts=['http://app.test/*'], matches=['http://app.test/*'], sfera_tab=True)
        self.db = MemoryDB()
        self.chrome_host = AppHost(self.env.ctx, kind='artifact', db=self.db, model=self.env.model)
        self.desk_ctx = browser.new_context(user_agent=DESK_UA, viewport={'width': 1360, 'height': 900}, accept_downloads=True)
        self.desk_errors = watch_errors(self.desk_ctx)
        self.desk_host = AppHost(self.desk_ctx, kind='artifact', db=self.db, model=MockModel(), **mcp_kw)
        self.chrome = None

    @property
    def ext(self):
        return self.env.ext

    @property
    def sfera(self):
        return self.env.sfera

    def open_chrome(self):
        """QA pro во вкладке Chrome с загрузчиком — принимает задания из приложения."""
        self.chrome = self.chrome_host.open()
        return self.chrome

    def open_desk(self):
        return prepare_cases(self.desk_host.open())

    def jobs(self):
        return sorted(k for k in self.db.store if '/sfjob-' in k and k.count('/') == 3)

    def presence(self):
        return [k for k in self.db.store if k.endswith('/sfera-relay')]

    def close(self):
        errs = list(self.desk_errors)
        try:
            self.desk_ctx.close()
        finally:
            self.env.close()
        assert not errs, 'ошибки на страницах приложения: ' + '; '.join(errs[:3])


class HostEnv(Relay):
    """Приложение Claude с настоящим мостом: страница → host:… → мост → загрузчик в Chrome (подключён к мосту по WebSocket) → Сфера (мок)."""

    def __init__(self, browser, tmp, pre_init=None):
        self.bridge = bridge_mod.Bridge(os.path.join(str(tmp), 'bridge')).start()
        self.mcp = bridge_mod.McpHost(self.bridge)
        super().__init__(browser, tmp, mcp=self.mcp, pre_init=pre_init)
        self.ext.settings(bridgePort=self.bridge.port, desktopBridge=True)
        self.ext.reconnect_bridge()
        self.wait_ext_connected()

    def wait_ext_connected(self, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            if self.bridge.tool('ping')['extension']['connected'] and self.ext.bridge_state()['connected']:
                return
            self.ext.ctx.pages[0].wait_for_timeout(100)
        raise AssertionError('загрузчик не подключился к мосту')

    def close(self):
        try:
            super().close()
        finally:
            self.bridge.stop()


@pytest.fixture
def make_host(browser, tmp_path_factory, need_node):
    made = []

    def factory(**kw):
        h = HostEnv(browser, tmp_path_factory.mktemp('host'), **kw)
        made.append(h)
        return h
    yield factory
    for h in made:
        h.close()


@pytest.fixture(scope='module')
def new_host(browser, tmp_path_factory):
    if not bridge_mod.have_node():
        pytest.skip('нет Node.js: мост qa-pro-bridge не запустить')
    made = []

    def factory(**kw):
        h = HostEnv(browser, tmp_path_factory.mktemp('host'), **kw)
        made.append(h)
        return h
    yield factory
    for h in made:
        h.close()


@pytest.fixture
def make_relay(browser, tmp_path_factory):
    made = []

    def factory(**kw):
        r = Relay(browser, tmp_path_factory.mktemp('relay'), **kw)
        made.append(r)
        return r
    yield factory
    for r in made:
        r.close()


@pytest.fixture(scope='module')
def new_relay(browser, tmp_path_factory):
    made = []

    def factory(**kw):
        r = Relay(browser, tmp_path_factory.mktemp('relay'), **kw)
        made.append(r)
        return r
    yield factory
    for r in made:
        r.close()


@pytest.fixture
def make_env(browser, tmp_path_factory):
    envs = []

    def factory(**kw):
        e = Env(browser, tmp_path_factory.mktemp('env'), **kw)
        envs.append(e)
        return e
    yield factory
    for e in envs:
        e.close()


@pytest.fixture
def env(make_env):
    return make_env(sfera_tab=True)


@pytest.fixture
def ext(env):
    return env.ext


@pytest.fixture
def sfera(env):
    return env.sfera


@pytest.fixture(scope='module')
def new_env(browser, tmp_path_factory):
    """Фабрика сред на файл — для сценариев, где разные тесты проверяют разные стороны одного прохода."""
    envs = []

    def factory(**kw):
        kw.setdefault('sfera_tab', True)
        e = Env(browser, tmp_path_factory.mktemp('menv'), **kw)
        envs.append(e)
        return e
    yield factory
    for e in envs:
        e.close()


@pytest.fixture
def need_node():
    if not bridge_mod.have_node():
        pytest.skip('нет Node.js: мост qa-pro-bridge не запустить')


@pytest.fixture
def make_bridge(tmp_path, need_node):
    made = []

    def factory(env=None, port=None, start=True, name='bridge', ping=True):
        b = bridge_mod.Bridge(tmp_path / name, port=port, env=env)
        made.append(b)
        if start:
            b.start(ping=ping)
        return b
    yield factory
    for b in made:
        b.stop()


@pytest.fixture
def bridge(make_bridge):
    return make_bridge()
