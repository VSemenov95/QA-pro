"""Настройка источника контекста переживает перезагрузку и публикацию новой версии страницы.

Хранилище — как настоящее (window.__dbLimit: запись больше 256 КиБ отклоняется). Новая версия страницы может открыться
с пустой памятью браузера (localStorage), поэтому настройка должна лежать в хранилище страницы.
"""
import json

import pytest

from tests.test_context_source import FAKE, REPO, connect

LIMIT = 262144
KB = {f'products/moi/kb/razdel-{i:03d}.md': f'# Раздел {i}\n\n' + ('Пользователь восстанавливает пароль по ссылке из письма. ' * 60) for i in range(200)}


def init(files, offline=False, extra=''):
    pre = 'window.__dbLimit = true;' + extra
    pre += f'window.__repo = {{ root: "/home/qa/ctx", files: {json.dumps(files, ensure_ascii=False)}, git: {{ repo: false }}, calls: [], pulls: 0 }};'
    if offline:
        pre += 'window.__ctxOffline = true;'
    return pre + FAKE


def restored(app, timeout=20000):
    app.page.wait_for_function('() => { const C = window.__qa.S.ctx; return C.pid === window.__qa.S.productId && C.src.kind !== "qa" && !C.busy; }', timeout=timeout)


def new_version(app):
    """Новая версия страницы: другая память браузера (localStorage пуст), хранилище страницы то же."""
    app.ctx.add_init_script(script='try { localStorage.clear(); } catch (e) {}')
    app.reload()
    restored(app)


def ctx_records(app):
    uid, pid = app.state('S.caps.uid'), app.state('S.productId')
    return {k: v for k, v in app.db.store.items() if k.startswith(f'data/users/{uid}/ctx_{pid}')}


def size(v):
    return len(json.dumps(v, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


@pytest.fixture
def big(make_app):
    app = make_app(init=init({**REPO, **KB}))
    connect(app)
    assert app.state('S.ctx.files.size') > 200
    return app


def test_big_context_records_fit_the_limit(big):
    recs = ctx_records(big)
    assert recs and all(size(v) <= LIMIT for v in recs.values())
    main = next(v for k, v in recs.items() if k.endswith(f'ctx_{big.state("S.productId")}'))
    assert main['src']['kind'] == 'local' and 'pending' not in main


def test_settings_survive_new_version_of_the_page(big):
    new_version(big)
    assert big.state('S.ctx.src.root') == '/home/qa/ctx' and big.state('S.ctx.src.slug') == 'moi'
    big.page.wait_for_function('() => window.__qa.S.ctx.files.size > 200', timeout=20000)
    assert big.state('S.cfg.rules').startswith('ПРАВИЛО-ИЗ-РЕПО')


def test_without_source_page_works_from_saved_copy(big):
    big.ctx.add_init_script(script='window.__ctxOffline = true; try { localStorage.clear(); } catch (e) {}')
    big.reload()
    restored(big)
    big.page.wait_for_function('() => !!window.__qa.S.ctx.error', timeout=20000)
    assert big.state('S.ctx.fromCache') and big.state('S.ctx.files.size') > 200
    assert 'Восстановление' not in big.state('S.ctx.error') and big.state('S.cfg.rules').startswith('ПРАВИЛО-ИЗ-РЕПО')


def test_big_queue_of_unsaved_changes_does_not_lose_settings(big):
    big.call('(S.ctx.channel = "app", true)')   # приложение Claude: правки копятся
    for i in range(40):
        big.call(f'a.ctxPut("products/moi/kb/novyi-{i:02d}.md", arg)', f'# Новый {i}\n\n' + 'Длинный раздел базы знаний. ' * 400)
    big.page.wait_for_timeout(800)
    assert big.state('S.ctx.pending.size') == 40
    recs = ctx_records(big)
    assert all(size(v) <= LIMIT for v in recs.values()) and any('_q' in k for k in recs)
    new_version(big)
    big.page.wait_for_function('() => window.__qa.S.ctx.pending.size === 40', timeout=20000)
    assert 'Длинный раздел' in big.state('S.ctx.files.get("products/moi/kb/novyi-39.md").text')


def test_settings_restore_even_if_product_data_fails_to_load(make_app):
    app = connect(make_app(init=init(dict(REPO))))
    app.ctx.add_init_script(script="window.__dbFailGet = 'meta/(kb|index|known)';")
    app.reload()
    restored(app)
    assert app.state('S.ctx.src.root') == '/home/qa/ctx'


def test_one_failed_read_of_settings_is_retried(make_app):
    app = connect(make_app(init=init(dict(REPO))))
    # первое чтение настройки падает, второе — проходит
    app.ctx.add_init_script(script="""(() => { let n = 0; Object.defineProperty(window, '__dbFailGet', { configurable: true, get() { return n++ === 0 ? '/ctx_[^_/]+$' : null; } }); })(); try { localStorage.clear(); } catch (e) {}""")
    app.reload()
    restored(app)
    assert app.state('S.ctx.src.kind') == 'local'


def test_settings_saved_only_in_browser_move_to_storage(make_app):
    app = connect(make_app(init=init(dict(REPO))))
    uid, pid = app.state('S.caps.uid'), app.state('S.productId')
    app.db.store.pop(f'data/users/{uid}/ctx_{pid}')   # запись в хранилище тогда не прошла
    app.reload()
    restored(app)
    app.page.wait_for_timeout(500)
    assert app.db.get(f'data/users/{uid}/ctx_{pid}')['src']['root'] == '/home/qa/ctx'


def test_old_format_with_inline_queue_still_reads(make_app):
    app = connect(make_app(init=init(dict(REPO))))
    uid, pid = app.state('S.caps.uid'), app.state('S.productId')
    app.db.store[f'data/users/{uid}/ctx_{pid}'] = {'src': app.state('S.ctx.src'), 'pending': [['rules/generation.md', '# Правила для агента\n\nИЗ-ОЧЕРЕДИ\n']], 'lastPush': None, 'updatedAt': 1}
    app.reload()
    restored(app)
    app.page.wait_for_function('() => window.__qa.S.cfg.rules === "ИЗ-ОЧЕРЕДИ"', timeout=15000)


def test_storage_failure_is_reported_once(make_app):
    app = connect(make_app(init=init(dict(REPO))))
    app.page.evaluate("() => { window.__dbLimit = true; }")
    app.call("""(() => { const db = S.caps.db, orig = db.doc; S.caps.db = { ...db, doc: (p) => { const r = orig(p); return /ctx_/.test(p) ? { ...r, set: async () => { throw { code: 'quota_exceeded' }; } } : r; } }; return true; })()""")
    app.call('(S.cfg.rules = "X", S.cfgDirty.rules = true, a.saveCfg("rules"))')
    app.page.wait_for_timeout(800)
    app.call('(S.cfg.rules = "Y", S.cfgDirty.rules = true, a.saveCfg("rules"))')
    app.page.wait_for_timeout(800)
    msgs = [t for t in app.toast_texts() if 'не удалось сохранить в хранилище' in t]
    assert len(msgs) == 1 and 'quota_exceeded' in msgs[0]
