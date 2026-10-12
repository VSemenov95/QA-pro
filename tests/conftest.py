"""Общие фикстуры: сборка приложения, браузер, страница. Запуск: python3 -m pytest tests -q"""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from tests.support import libs  # noqa: E402
from tests.support.app import App, open_app  # noqa: E402,F401
from tests.support.chromium import launch_kwargs  # noqa: E402


def pytest_configure(config):
    config.addinivalue_line('markers', 'needs_libs: тест разбирает docx/xlsx/pdf — нужны локальные копии mammoth, xlsx и pdf.js (npm pack)')
    config.addinivalue_line('markers', 'slow: долгий тест (больше 30 секунд)')


@pytest.fixture(scope='session', autouse=True)
def built():
    """Приложение собирается перед тестами (python3 build.py); QA_PRO_NO_BUILD=1 — использовать готовые файлы."""
    if os.environ.get('QA_PRO_NO_BUILD') != '1':
        r = subprocess.run([sys.executable, 'build.py'], cwd=ROOT, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr[-800:]
    for f in ('tc-agent.html', 'qa-pro.html'):
        assert os.path.exists(os.path.join(ROOT, f)), f + ' не собран'


@pytest.fixture(scope='session')
def libs_ok():
    return libs.ensure()


@pytest.fixture(autouse=True)
def _skip_without_libs(request):
    if request.node.get_closest_marker('needs_libs') and not request.getfixturevalue('libs_ok'):
        pytest.skip('нет локальных копий библиотек разбора документов (npm pack не сработал)')


@pytest.fixture(scope='session')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(**launch_kwargs(p))
        yield b
        b.close()


@pytest.fixture
def make_app(browser):
    """Фабрика страниц: app = make_app(kind='artifact', settings={...}). После теста проверяется, что на странице не было необработанных ошибок."""
    apps = []

    def factory(**kw):
        a = open_app(browser, **kw)
        apps.append(a)
        return a
    yield factory
    errs = [e for a in apps for e in a.errors]
    for a in apps:
        a.ctx.close()
    assert not errs, 'ошибки на странице: ' + '; '.join(errs[:3])


@pytest.fixture
def app(make_app):
    """Страница нового пользователя: приложение само создало продукт «Мой продукт»."""
    return make_app()

