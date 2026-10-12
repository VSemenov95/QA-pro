"""Chrome с расширением «загрузчик в Сферу ФТ» и страницы QA pro в произвольном контексте браузера.

    ext = ExtChrome(bt, tmp_path, hosts=['http://app.test/*'], matches=['http://app.test/*'])
    ext.settings(baseUrl=sfera.base)               # настройки загрузчика (как на странице параметров)
    host = AppHost(ext.ctx, kind='standalone', url=sfera.base + '/qa-pro.html')
    qa = host.open()                               # страница QA pro (tests.support.app.App)
    win = ext.window_from(lambda: qa.page.click('[data-act=tms-upload]'))   # окно загрузчика

Обычный (не persistent) Chromium для расширений не годится: нужен launch_persistent_context с --load-extension.
"""
import json
import os
import shutil
import time
import types

from . import libs
from .app import HERE, SKEL, URL, App, _read
from .chromium import launch_kwargs
from .db import MemoryDB
from .model import MockModel

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXT_SRC = os.path.join(ROOT, 'uploader', 'qa-pro-sfera-uploader')
DESK_UA = 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Claude/1.0.0 Chrome/138.0.0.0 Electron/37.2.0 Safari/537.36'


def manifest():
    with open(os.path.join(EXT_SRC, 'manifest.json'), encoding='utf-8') as f:
        return json.load(f)


def extension_copy(dst, hosts=(), matches=()):
    """Копия расширения во временной папке; в манифест добавляются адреса тестовых страниц (исходники не меняются)."""
    shutil.copytree(EXT_SRC, dst, dirs_exist_ok=True)
    path = os.path.join(dst, 'manifest.json')
    with open(path, encoding='utf-8') as f:
        m = json.load(f)
    m['host_permissions'] += list(hosts)
    m['content_scripts'][0]['matches'] += list(matches)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False)
    return str(dst)


def watch_errors(ctx):
    """Необработанные ошибки всех страниц контекста (в том числе страниц расширения)."""
    errs = []
    ctx.on('page', lambda p: p.on('pageerror', lambda e: errs.append(str(e))))
    for p in ctx.pages:
        p.on('pageerror', lambda e: errs.append(str(e)))
    return errs


class ExtChrome:
    def __init__(self, bt, tmp, hosts=(), matches=(), viewport=(1360, 900)):
        tmp = str(tmp)
        self.dir = extension_copy(os.path.join(tmp, 'ext'), hosts, matches)
        kw = launch_kwargs(types.SimpleNamespace(chromium=bt))
        self.ctx = bt.launch_persistent_context(os.path.join(tmp, 'profile'), headless=True, viewport={'width': viewport[0], 'height': viewport[1]},
                                                args=[f'--disable-extensions-except={self.dir}', f'--load-extension={self.dir}'], **kw)
        self.errors = watch_errors(self.ctx)
        self.id, self.origin = None, None
        sw = self._find_sw()
        self.id = sw.url.split('/')[2]
        self.origin = f'chrome-extension://{self.id}'

    def _find_sw(self, wake=False, timeout=40):
        """Фоновая часть, в которой уже выполнен background.js (сразу после запуска функции ещё не объявлены)."""
        end = time.time() + timeout
        pg = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
        woke = False
        while time.time() < end:
            for w in self.ctx.service_workers:
                if w.url.startswith(self.origin or 'chrome-extension://'):
                    try:
                        if w.evaluate("typeof saveSettings === 'function'"):
                            return w
                    except Exception:
                        pass   # работника остановили или он ещё стартует
            if wake and not woke:   # после простоя Chrome останавливает фоновую часть — будим страницей параметров
                woke = True
                p = self.ctx.new_page()
                p.goto(f'{self.origin}/options.html')
                p.close()
            pg.wait_for_timeout(100)
        raise AssertionError('фоновая часть расширения не запустилась')

    @property
    def sw(self):
        return self._find_sw(wake=True)

    def sw_eval(self, expr, arg=None):
        return self.sw.evaluate(expr, arg) if arg is not None else self.sw.evaluate(expr)

    def settings(self, **patch):
        return self.sw_eval('(p) => saveSettings(p)', patch)

    def reconnect_bridge(self):
        """Подключение к мосту сразу, не дожидаясь таймера на 30 секунд."""
        return self.sw_eval("() => { try { bws && bws.close(); } catch (e) {} bws = null; return bridgeConnect(); }")

    def bridge_state(self):
        return self.sw_eval('() => bwsState')

    def login(self, base, token='tok-123'):
        """Вход в Сферу: cookie ACCESS_TOKEN."""
        self.ctx.add_cookies([{'name': 'ACCESS_TOKEN', 'value': token, 'url': base}])

    def page(self, url=None):
        p = self.ctx.new_page()
        if url:
            p.goto(url)
        return p

    def ext_page(self, name):
        p = self.ctx.new_page()
        p.goto(f'{self.origin}/{name}')
        return p

    def window_from(self, action, timeout=20000):
        """Выполняет действие, после которого расширение открывает окно; возвращает это окно."""
        with self.ctx.expect_page(timeout=timeout) as pi:
            action()
        w = pi.value
        w.wait_for_load_state()
        return w

    def pages_with(self, text):
        return [p for p in self.ctx.pages if text in p.url]

    def close(self):
        try:
            self.ctx.close()
        except Exception:
            pass


def wait_window_ready(w, cases=True):
    """Окно загрузчика готово: вход проверен и кейсы показаны."""
    w.wait_for_function("() => !/Проверяю/.test(document.querySelector('#login').textContent)", timeout=15000)
    if cases:
        w.wait_for_selector('#rows input[data-i]', timeout=15000)
    return w


class AppHost:
    """Страницы QA pro в одном контексте браузера: общая база и модель, возможности артефакта, ошибки страниц."""

    def __init__(self, ctx, kind='artifact', db=None, model=None, url=URL, init=None, local_storage=None, settings=None, mcp=None, sample_delay=15, qa_test=True, pre_init=None):
        self.ctx, self.kind, self.url = ctx, kind, url
        self.db = db if db is not None else MemoryDB()
        self.model = model if model is not None else MockModel()
        self.apps = []
        if kind == 'artifact':
            ctx.expose_function('__dbop', self.db.op)
            ctx.expose_function('__model', self.model.handle)
        if mcp is not None:
            ctx.expose_function('__mcp', mcp)
        ls = dict(local_storage or {})
        if settings is not None:
            ls['tca.settings'] = settings
        seed = ''.join(f'try {{ localStorage.setItem({json.dumps(k)}, {json.dumps(json.dumps(v))}); }} catch (e) {{}}' for k, v in ls.items())
        pre = (f'window.__qaTest = {"true" if qa_test else "false"}; window.__sampleDelay = {sample_delay};'
               + (f'try {{ if (!localStorage.getItem("__seeded")) {{ localStorage.setItem("__seeded", "1"); {seed} }} }} catch (e) {{}}' if seed else ''))
        ctx.add_init_script(script=pre + (pre_init or ''))   # pre_init выполняется до возможностей артефакта (caps.js, mcp.js)
        if kind == 'artifact':
            ctx.add_init_script(path=os.path.join(HERE, 'support', 'caps.js'))
            if mcp is not None:
                ctx.add_init_script(path=os.path.join(HERE, 'support', 'mcp.js'))
        if init:
            ctx.add_init_script(script=init)
        if url == URL:
            html = _read('tc-agent.html' if kind == 'artifact' else 'qa-pro.html')

            def route(r):
                u = r.request.url
                if u.startswith(URL):
                    return r.fulfill(body=SKEL.replace('@@BODY@@', html) if kind == 'artifact' else html, content_type='text/html; charset=utf-8')
                f = libs.local_file(u)
                if f:
                    return r.fulfill(path=f, content_type='application/javascript')
                return r.abort()
            ctx.route(URL + '**', route)

    def open(self, url=None, ready=True, wait=20000):
        page = self.ctx.new_page()
        app = App(self.ctx, page, self.db, self.model, self.kind)
        self.apps.append(app)
        page.goto(url or self.url)
        if ready:
            app.ready(wait)
        return app


def prepare_cases(app, tab='cases'):
    """Сгенерировать кейсы на примере ТЗ и открыть вкладку с панелью загрузки в ТМС."""
    app.generate()
    assert app.state('S.run.status') == 'done', app.state('S.run.error')
    app.tab(tab)
    app.page.wait_for_selector('#tms-bar .tms-row', timeout=15000)
    app.page.wait_for_function("() => !/проверяю загрузчик/.test(document.querySelector('#tms-bar').innerText)", timeout=15000)   # загрузчик ответил на пинг
    return app


def case_marks(app):
    """Список «ИД кейса → названия чипов» с вкладки «Тест-кейсы» запуска."""
    return app.page.evaluate("() => [...document.querySelectorAll('#case-list article')].map(a => [a.querySelector('.case-id').textContent, [...a.querySelectorAll('.case-sub .chip')].map(c => c.textContent)])")
