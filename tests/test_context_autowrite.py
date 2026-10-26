"""Автозапись в источник: обновили базу знаний, шаблоны, правила, память агента — изменения сами уходят в источник.

Правки копятся, пока агент работает, и уходят одним вызовом после паузы (в тестах — 300 мс вместо 4 с).
Git-репозиторий (клон через мост) и GitHub ещё и фиксируются и отправляются — в ветку qa-pro/<дата>.
"""
from tests.test_context_source import REPO, connect, init as base_init, repo, wait_repo

FAST = 'window.__ctxAutoDelay = 300;'
KB = 'products/moi/kb/novyi-razdel.md'


def init(**kw):
    return FAST + base_init(**kw)


def writes(app, tool='context_write', op=None):
    return app.page.evaluate('([t, o]) => window.__repo.calls.filter((c) => c[0] === t && (!o || c[1] === o)).length', [tool, op])


def idle(app, timeout=8000):
    app.page.wait_for_function('() => window.__qa.S.ctx.pending.size === 0 && !window.__qa.S.ctx.busy', timeout=timeout)


def in_app(make_app):
    app = connect(make_app(init=init()))
    app.call('(S.ctx.channel = "app", true)')   # мост в приложении Claude: каждая запись — подтверждение приложения
    app.close_settings()
    return app


def test_claude_app_writes_changes_by_itself_in_one_call(make_app):
    app = in_app(make_app)
    app.call('a.ctxPut(arg, "# Новый раздел\\n\\nАВТО-БЗ\\n")', KB)
    app.call('a.addLesson("АВТО-УРОК", "generation")')
    app.call('a.savePassport(S.productId, "## Термины\\n- АВТО-ПАСПОРТ", null)')
    idle(app)
    assert writes(app) == 1   # одна пачка — одно подтверждение в приложении
    assert 'АВТО-БЗ' in repo(app, KB) and 'АВТО-УРОК' in repo(app, 'products/moi/memory.md')
    assert 'АВТО-ПАСПОРТ' in repo(app, 'products/moi/passport.md')
    assert not any('ждут записи' in t for t in app.toast_texts())
    app.open_settings('ctx')
    assert app.page.is_checked('#ctx-auto') and 'последняя' in app.text('#ctx-body')


def test_waits_until_the_agent_finishes(make_app):
    app = in_app(make_app)
    app.call('(S.kb.job.busy = true, true)')   # агент разбирает документы в базу знаний
    app.call('a.ctxPut(arg, "# Раздел 1\\n\\nПЕРВЫЙ\\n")', KB)
    app.page.wait_for_timeout(700)
    app.call('a.ctxPut("products/moi/kb/vtoroi.md", "# Раздел 2\\n\\nВТОРОЙ\\n")')
    app.page.wait_for_timeout(900)
    assert writes(app) == 0 and app.state('S.ctx.pending.size') == 2
    app.call('(S.kb.job.busy = false, true)')
    idle(app)
    assert writes(app) == 1 and 'ВТОРОЙ' in repo(app, 'products/moi/kb/vtoroi.md')


def test_declined_in_app_pauses_until_manual_write(make_app):
    app = in_app(make_app)
    app.page.evaluate('() => { window.__repo.failWrite = "Вызов моста отклонён в окне подтверждения приложения."; }')
    app.call('a.addLesson("ПОСЛЕ-ОТКАЗА", "generation")')
    app.page.wait_for_function('() => window.__qa.S.ctx.autoPaused === true', timeout=8000)
    assert any('приостановлена' in t for t in app.toast_texts())
    app.call('a.addLesson("ЕЩЁ-УРОК", "generation")')
    app.page.wait_for_timeout(900)
    assert writes(app) == 1   # после отказа сама больше не спрашивает
    app.open_settings('ctx')
    assert 'приостановлена' in app.text('#ctx-body')
    app.page.click('[data-ctx-act=flush]')
    idle(app)
    assert 'ЕЩЁ-УРОК' in repo(app, 'products/moi/memory.md') and app.state('S.ctx.autoPaused') is False


def test_auto_write_can_be_switched_off_and_the_choice_is_kept(make_app):
    app = in_app(make_app)
    app.open_settings('ctx')
    app.page.click('label.ctx-auto')
    app.call('a.addLesson("ВРУЧНУЮ", "generation")')
    app.page.wait_for_timeout(900)
    assert writes(app) == 0 and app.state('S.ctx.pending.size') == 1
    uid, pid = app.state('S.caps.uid'), app.state('S.productId')
    assert app.db.get(f'data/users/{uid}/ctx_{pid}')['src']['auto'] is False
    app.page.click('label.ctx-auto')
    idle(app)
    assert writes(app) == 1 and 'ВРУЧНУЮ' in repo(app, 'products/moi/memory.md')


def test_queue_left_before_reload_is_written_after_it(make_app):
    app = in_app(make_app)
    app.open_settings('ctx')
    app.page.click('label.ctx-auto')
    app.call('a.addLesson("ДО-ПЕРЕЗАГРУЗКИ", "generation")')
    app.page.wait_for_timeout(500)
    uid, pid = app.state('S.caps.uid'), app.state('S.productId')
    doc = app.db.get(f'data/users/{uid}/ctx_{pid}')
    app.db.store[f'data/users/{uid}/ctx_{pid}'] = {**doc, 'src': {**doc['src'], 'auto': True}}
    app.reload()
    wait_repo(app, 'products/moi/memory.md', 'ДО-ПЕРЕЗАГРУЗКИ', timeout=15000)


def test_git_repository_is_committed_and_pushed_by_itself(make_app):
    app = connect(make_app(init=init()), kind='git', url='https://git.test/qa/ctx.git')
    app.call('(a.S.cfg.rules = "АВТО-ПРАВИЛО", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    app.page.wait_for_function('() => !!window.__qa.S.ctx.lastPush && !window.__qa.S.ctx.busy', timeout=8000)
    assert repo(app, 'rules/generation.md').endswith('АВТО-ПРАВИЛО\n')
    assert writes(app, 'context_git', 'commit') == 1 and writes(app, 'context_git', 'push') == 1
    assert app.state('S.ctx.lastPush.branch').startswith('qa-pro/')   # не в main


def test_local_folder_is_written_but_not_pushed(make_app):
    cx = connect(make_app(init=init()))
    cx.call('(a.S.cfg.rules = "ТОЛЬКО-ЗАПИСЬ", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    wait_repo(cx, 'rules/generation.md', 'ТОЛЬКО-ЗАПИСЬ')
    cx.page.wait_for_timeout(900)
    assert writes(cx, 'context_git', 'push') == 0   # свою папку пользователь отправляет сам


def test_github_is_sent_to_a_branch_by_itself(make_app):
    app = connect(make_app(init=init(files={}, gh=REPO)), kind='github', repo='team/qa-context')
    app.call('(a.S.cfg.rules = "В-GITHUB", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    app.page.wait_for_function('() => Object.keys(window.__gh.branches).length === 1 && window.__qa.S.ctx.pending.size === 0', timeout=8000)
    br = app.page.evaluate('() => window.__gh.branches')
    (name, files), = br.items()
    assert name.startswith('qa-pro/') and files['rules/generation.md'].endswith('В-GITHUB\n')
    app.call('a.addLesson("ВТОРАЯ-ПРАВКА", "generation")')
    app.page.wait_for_function('() => window.__qa.S.ctx.pending.size === 0 && !window.__qa.S.ctx.busy', timeout=8000)
    br = app.page.evaluate('() => window.__gh.branches')
    assert list(br) == [name] and 'ВТОРАЯ-ПРАВКА' in br[name]['products/moi/memory.md']   # та же ветка
