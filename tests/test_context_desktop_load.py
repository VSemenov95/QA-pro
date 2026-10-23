"""Открытие страницы с большой папкой контекста (как в приложении Claude): папка не читается целиком каждый раз,
копия в хранилище не перезаписывается без изменений, автозапись не отправляет старую очередь и большие пачки,
обрезанный паспорт не затирает полный."""
import json

from tests.test_context_source import FAKE, REPO, connect

BIG = {f'products/moi/kb/razdel-{i:03d}.md': f'# Раздел {i}\n\n' + ('Пользователь настраивает метрику и проверяет статус. ' * 120) for i in range(120)}
LONG_PASSPORT = '## Назначение и границы\n' + ''.join(f'- Пункт паспорта номер {i}: длинное описание правила продукта.\n' for i in range(900))


def init(files, extra=''):
    return f'window.__ctxAutoDelay = 300; {extra} window.__repo = {{ root: "/home/qa/ctx", files: {json.dumps(files, ensure_ascii=False)}, git: {{ repo: false }}, calls: [], pulls: 0 }};' + FAKE


def reads(app):
    return app.page.evaluate('() => window.__repo.reads || []')


def restored(app):
    app.page.wait_for_function('() => { const C = window.__qa.S.ctx; return C.on && C.pid === window.__qa.S.productId && !C.busy && C.files.size > 0 && C.loadedAt; }', timeout=20000)
    app.page.wait_for_timeout(500)


def cache_writes(app):
    uid, pid = app.state('S.caps.uid'), app.state('S.productId')
    return {k: v for k, v in app.db.store.items() if k.startswith(f'data/users/{uid}/ctx_{pid}_c')}


def test_folder_is_read_in_small_portions(make_app):
    app = connect(make_app(init=init({**REPO, **BIG})))
    sizes = [sum(len(BIG.get(p, REPO.get(p, ''))) for p in batch) for batch in reads(app)]
    assert len(reads(app)) > 1 and max(sizes) <= 300000 + 7000
    got = [p for b in reads(app) for p in b]
    assert len(got) == len(set(got)) and set(BIG) <= set(got)   # каждый файл — один раз


def test_reopening_reads_only_changed_files(make_app):
    app = connect(make_app(init=init({**REPO, **BIG})))
    # память страницы при перезагрузке сбрасывается — правку в «редакторе» вносим скриптом при открытии
    app.ctx.add_init_script(script='window.__repo.files["products/moi/kb/razdel-007.md"] = "# Раздел 7\\n\\nИЗМЕНЁН В РЕДАКТОРЕ\\n";')
    app.reload()
    restored(app)
    last = reads(app)
    assert last == [['products/moi/kb/razdel-007.md']]   # остальные 125 файлов — из копии
    assert 'ИЗМЕНЁН В РЕДАКТОРЕ' in app.state('S.ctx.files.get("products/moi/kb/razdel-007.md").text')


def test_unchanged_copy_is_not_rewritten(make_app):
    app = connect(make_app(init=init({**REPO, **BIG})))
    before = {k: id(v) for k, v in cache_writes(app).items()}
    app.db.store.update({k: dict(v, mark='old') for k, v in cache_writes(app).items()})
    app.reload()
    restored(app)
    assert all(v.get('mark') == 'old' for v in cache_writes(app).values()) and before


def test_queue_from_previous_session_waits_for_the_button_in_claude_app(make_app):
    app = connect(make_app(init=init(dict(REPO))))
    app.call('(S.ctx.src = { ...S.ctx.src, auto: false }, S.ctx.channel = "app", true)')
    app.call('a.addLesson("УРОК-С-ПРОШЛОГО-РАЗА", "generation")')   # осталось в очереди
    app.page.wait_for_timeout(500)
    app.reload()
    restored(app)
    assert app.state('S.ctx.pending.size') == 1
    app.call('(S.ctx.src = { ...S.ctx.src, auto: true }, S.ctx.channel = "app", true)')
    app.call('a.ctxAutoRun()')
    app.page.wait_for_timeout(800)
    assert app.page.evaluate('() => window.__repo.calls.filter((c) => c[0] === "context_write").length') == 0
    assert app.state('S.ctx.pending.size') == 1 and app.state('S.ctx.autoHeld') is True
    app.open_settings('ctx')
    assert 'по кнопке' in app.text('#ctx-body')
    app.page.click('[data-ctx-act=flush]')
    app.page.wait_for_function('() => window.__qa.S.ctx.pending.size === 0 && !window.__qa.S.ctx.busy', timeout=8000)


def test_big_batch_waits_for_the_button_in_claude_app(make_app):
    app = connect(make_app(init=init(dict(REPO))))
    app.call('(S.ctx.channel = "app", true)')
    for i in range(3):
        app.call(f'a.ctxPut("products/moi/kb/bolshoi-{i}.md", arg)', f'# Большой {i}\n\n' + 'Очень длинный раздел. ' * 4000)
    app.page.wait_for_timeout(1200)
    assert app.page.evaluate('() => window.__repo.calls.filter((c) => c[0] === "context_write").length') == 0
    assert app.state('S.ctx.pending.size') == 3 and app.state('S.ctx.autoHeld') is True


def test_small_change_of_this_session_is_written_in_claude_app(make_app):
    app = connect(make_app(init=init(dict(REPO))))
    app.call('(S.ctx.channel = "app", true)')
    app.call('a.addLesson("УРОК-СЕЙЧАС", "generation")')
    app.page.wait_for_function('() => window.__qa.S.ctx.pending.size === 0 && !window.__qa.S.ctx.busy', timeout=8000)
    assert 'УРОК-СЕЙЧАС' in app.page.evaluate('() => window.__repo.files["products/moi/lessons.md"]')


def test_long_passport_is_written_whole(make_app):
    """Паспорт без предела: QA pro пишет его в источник целиком, без обрезки до 40 000 знаков."""
    app = connect(make_app(init=init(dict(REPO))))
    app.call('a.savePassport(S.productId, arg, null)', LONG_PASSPORT)
    app.page.wait_for_function('(n) => (window.__repo.files["products/moi/passport.md"] || "").length >= n', arg=len(LONG_PASSPORT) - 10, timeout=10000)
    assert app.page.evaluate('() => window.__repo.files["products/moi/passport.md"]').strip() == LONG_PASSPORT.strip()


def test_truncated_passport_left_in_queue_is_dropped(make_app):
    app = connect(make_app(init=init({**REPO, 'products/moi/passport.md': LONG_PASSPORT})))
    uid, pid = app.state('S.caps.uid'), app.state('S.productId')
    # очередь прошлого сеанса: паспорт, обрезанный до 40 000 знаков
    app.db.store[f'data/users/{uid}/ctx_{pid}_q0'] = {'s': json.dumps([['products/moi/passport.md', LONG_PASSPORT[:40000]]], ensure_ascii=False)}
    doc = app.db.get(f'data/users/{uid}/ctx_{pid}')
    app.db.store[f'data/users/{uid}/ctx_{pid}'] = {**doc, 'pendingParts': 1}
    app.reload()
    restored(app)
    assert app.state('S.ctx.pending.size') == 0
    assert app.state('S.ctx.files.get("products/moi/passport.md").text') == LONG_PASSPORT
    assert app.page.evaluate('() => window.__repo.files["products/moi/passport.md"]') == LONG_PASSPORT
