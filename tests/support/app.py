"""Страница приложения под управлением теста: артефакт (tc-agent.html, возможности — через Python) или автономная версия (qa-pro.html)."""
import json
import os

from . import libs
from .chromium import launch_kwargs  # noqa: F401  (используется conftest)
from .db import MemoryDB
from .model import MockModel

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = 'http://app.test/'
SKEL = ('<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{color-scheme:light}body{margin:0;font:14px system-ui;background:#fafafa}img{max-width:100%}[hidden]{display:none!important}</style></head><body>@@BODY@@</body></html>')


def _read(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return f.read()


class App:
    def __init__(self, ctx, page, db, model, kind):
        self.ctx, self.page, self.db, self.model, self.kind = ctx, page, db, model, kind
        self.errors = []
        page.on('pageerror', lambda e: self.errors.append(str(e)))

    # ---------- чтение и запись состояния ----------
    def js(self, expr, arg=None):
        return self.page.evaluate(expr, arg) if arg is not None else self.page.evaluate(expr)

    def state(self, expr):
        """Значение выражения над состоянием приложения: app.state('S.run.cases.length')."""
        return self.page.evaluate('() => { const a = window.__qa, S = a.S; return (' + expr + '); }')

    def call(self, expr, arg=None):
        """Выполнить выражение с доступом к window.__qa (a) и S: app.call('a.tagTitle({...}, "ui")')."""
        return self.page.evaluate('async (arg) => { const a = window.__qa, S = a.S; return (' + expr + '); }', arg)

    def text(self, sel):
        return self.page.inner_text(sel)

    def count(self, sel):
        return self.page.locator(sel).count()

    def visible(self, sel):
        return self.page.locator(sel).first.is_visible() if self.count(sel) else False

    # ---------- ожидания ----------
    def ready(self, timeout=20000):
        try:
            self.page.wait_for_function('() => window.__qa && window.__qa.S.caps.ready && window.__qa.S.prodReady && (!window.__qa.S.caps.db || window.__qa.S.productId)', timeout=timeout)   # у нового пользователя приложение само создаёт «Мой продукт»
        except Exception as e:
            raise AssertionError(f'приложение не готово; ошибки страницы: {self.errors[:3]}') from e   # без этого видно только таймаут
        return self

    def wait_idle(self, timeout=90000):
        self.page.wait_for_timeout(300)
        self.page.wait_for_function('() => { const S = window.__qa.S; return !S.running && !S.help.busy && !S.kb.job.busy && !S.know.busy && !(S.kb.queue || []).length; }', timeout=timeout, polling=100)
        self.page.wait_for_timeout(200)

    def wait_docs(self, timeout=30000):
        self.page.wait_for_function("() => ![...document.querySelectorAll('.doc-meta')].some((e) => /разбор/.test(e.textContent))", timeout=timeout)

    # ---------- действия пользователя ----------
    def reload(self):
        self.page.reload()
        self.ready()
        return self

    def tab(self, name):
        self.page.click(f'#tab-{name}')
        self.page.wait_for_timeout(150)

    def mode(self, name):
        self.page.click(f'[data-mode={name}]')
        self.page.wait_for_timeout(250)

    def upload(self, *paths):
        self.page.set_input_files('#file-input', [str(p) for p in paths])
        self.page.wait_for_timeout(300)
        self.wait_docs()

    def upload_tests(self, path):
        self.page.set_input_files('#upd-input', str(path))
        self.page.wait_for_function("() => window.__qa.S.upd.file && window.__qa.S.upd.file.status !== 'parsing'", timeout=20000)

    def add_sample(self):
        """Пример ТЗ: у нового пользователя он уже лежит в «Моём продукте»; в пустом продукте добавляется кнопкой."""
        if self.visible('#btn-sample'):
            self.page.click('#btn-sample')
            self.page.wait_for_timeout(300)
        assert self.state('S.docs.length') > 0, 'в продукте нет документов'

    def generate(self, wait=True, timeout=90000):
        self.page.click('#btn-run')
        if wait:
            self.wait_idle(timeout)

    def open_settings(self, tab=None):
        self.page.click('#btn-settings')
        self.page.wait_for_timeout(250)
        if tab:
            self.page.click(f'#settab-{tab}')
            self.page.wait_for_timeout(150)

    def close_settings(self):
        self.page.evaluate("() => document.querySelector('#set-ov [data-close]')?.click()")

    def create_product(self, name='Тестовый продукт', description=''):
        """Создаёт продукт через интерфейс (без продукта нет кнопки «Добавить пример ТЗ» и сохранения запусков)."""
        n = self.state('S.products.length')
        self.page.select_option('#prod-select', '__new')
        self.page.wait_for_selector('#prod-name')
        self.page.fill('#prod-name', name)
        if description:
            self.page.fill('#prod-desc', description)
        self.page.click('[data-pact=save]')
        self.page.wait_for_function('(n) => window.__qa.S.products.length > n && window.__qa.S.prodReady && window.__qa.S.productId', arg=n, timeout=15000)
        self.page.wait_for_timeout(300)
        return self.state('S.productId')

    def import_product(self, path):
        self.page.set_input_files('#prod-import-file', str(path))

    def toast_texts(self):
        return self.page.evaluate("() => [...document.querySelectorAll('.toast, #toasts > *')].map((e) => e.innerText.trim()).filter(Boolean)")

    def downloads(self):
        return self.page.evaluate('() => window.__downloads || []')

    def case_titles(self):
        return self.state('S.run.cases.map((c) => a.pickTitleText(c.testCase))')


def open_app(browser, kind='artifact', settings=None, db=None, model=None, viewport=(1360, 900), libs_on=True, init=None, local_storage=None):
    """Создаёт контекст и страницу. kind: 'artifact' — возможности через Python (db, model), 'standalone' — автономная версия."""
    db = db if db is not None else MemoryDB()
    model = model if model is not None else MockModel()
    ctx = browser.new_context(viewport={'width': viewport[0], 'height': viewport[1]}, accept_downloads=True)
    ctx.expose_function('__dbop', db.op)
    ctx.expose_function('__model', model.handle)
    ls = dict(local_storage or {})
    if settings is not None:
        ls['tca.settings'] = settings
    pre = 'window.__qaTest = true; window.__sampleDelay = 15;' + ''.join(f'try {{ localStorage.setItem({json.dumps(k)}, {json.dumps(json.dumps(v))}); }} catch (e) {{}}' for k, v in ls.items())
    ctx.add_init_script(script=pre)
    if kind == 'artifact':
        ctx.add_init_script(path=os.path.join(HERE, 'support', 'caps.js'))
    if init:
        ctx.add_init_script(script=init)
    html = _read('tc-agent.html' if kind == 'artifact' else 'qa-pro.html')

    def route(r):
        u = r.request.url
        if u.startswith(URL):
            return r.fulfill(body=SKEL.replace('@@BODY@@', html) if kind == 'artifact' else html, content_type='text/html; charset=utf-8')
        if libs_on:
            f = libs.local_file(u)
            if f:
                return r.fulfill(path=f, content_type='application/javascript')
        return r.abort()
    ctx.route('**/*', route)
    page = ctx.new_page()
    app = App(ctx, page, db, model, kind)
    page.goto(URL)
    app.ready()
    return app
