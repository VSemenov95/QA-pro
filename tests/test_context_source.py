"""Источник контекста: правила, шаблоны, память агента, паспорт, доп. контекст и база знаний из папки, git-репозитория или GitHub.

Загрузчик и мост здесь «понарошку» (tests/support/fake_ctx.js): страница говорит с ними тем же протоколом CTX_*, что и с настоящим
расширением, а файлы лежат в памяти страницы (window.__repo, window.__gh). Сквозной путь через настоящие расширение и мост —
tests/uploader/test_context_e2e.py.
"""
import json
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
FAKE = open(os.path.join(HERE, 'support', 'fake_ctx.js'), encoding='utf-8').read()
TPL_API = open(os.path.join(os.path.dirname(HERE), 'templates', 'api.md'), encoding='utf-8').read().replace('idPrefix: API-', 'idPrefix: BE-')

REPO = {
    'rules/generation.md': '# Правила для агента\n\nПРАВИЛО-ИЗ-РЕПО: шаги в повелительном наклонении.\n',
    'rules/review.md': '# Правила ревью\n\nРЕВЬЮ-ИЗ-РЕПО: у каждого шага ожидаемый результат.\n',
    'templates/api.md': TPL_API,
    'products/moi/passport.md': '## Термины\n- ПАСПОРТ-ИЗ-РЕПО: личный кабинет клиента\n',
    'products/moi/context.md': '# Доп. контекст QA\n\n## Для всех\n\nОКРУЖЕНИЕ-ИЗ-РЕПО stage\n\n## UI\n\nЭКРАН-ИЗ-РЕПО Главная → Профиль\n',
    'products/moi/memory.md': '# Память агента\n\n- [генерация] УРОК-ГЕН: email в шагах — test@example.ru\n- [ревью] УРОК-РЕВЬЮ\n- УРОК-БЕЗ-МЕТКИ\n',
    'products/moi/kb/vosstanovlenie.md': '# Восстановление пароля\n\nСсылка на восстановление пароля действует 30 минут. ЗНАНИЕ-ИЗ-РЕПО: повторный запрос ссылки — не чаще раза в минуту.\n',
    'knowledge/glossary.md': '# Глоссарий\n\nЛК — личный кабинет. ОБЩЕЕ-ЗНАНИЕ.\n',
    'other/notes.md': 'не контекст — не читается',
}


def init(files=None, gh=None):
    pre = 'window.__ctxAutoDelay = window.__ctxAutoDelay ?? 600000;'   # автозапись проверяется в test_context_autowrite
    pre += f'window.__repo = {{ root: "/home/qa/ctx", files: {json.dumps(files if files is not None else REPO, ensure_ascii=False)}, git: {{ repo: true, branch: "main", remote: "https://git.test/qa/ctx.git", ahead: 0, behind: 0, changed: [] }}, calls: [], pulls: 0 }};'
    if gh is not None:
        pre += f'window.__gh = {{ repo: "team/qa-context", branch: "main", files: {json.dumps(gh, ensure_ascii=False)}, branches: {{}}, calls: [] }};'
    return pre + FAKE


def repo(app, path=None):
    files = app.page.evaluate('() => window.__repo.files')
    return files if path is None else files.get(path)


def wait_repo(app, path, needle, timeout=8000):
    app.page.wait_for_function('([p, n]) => (window.__repo.files[p] || "").includes(n)', arg=[path, needle], timeout=timeout)
    return repo(app, path)


def connect(app, kind='local', **fields):
    app.open_settings('ctx')
    app.page.click('[data-ctx-act=edit]')
    app.page.click(f'label:has([data-ctxk={kind}])')
    vals = {'root': '/home/qa/ctx', 'slug': 'moi'} if kind == 'local' else {'slug': 'moi'}
    vals.update(fields)
    for k, v in vals.items():
        app.page.fill(f'#ctx-{k}', v)
    app.page.click('[data-ctx-act=connect]')
    app.page.wait_for_function('() => { const C = window.__qa.S.ctx; return !C.busy && (C.on && C.loadedAt > 0 || !!C.error); }', timeout=15000)
    return app


@pytest.fixture
def cx(make_app):
    return connect(make_app(init=init()))


# ---------- подключение и применение ----------
def test_settings_have_context_tab_with_qa_base_by_default(make_app):
    app = make_app(init=init())
    app.open_settings('ctx')
    assert 'База QA pro' in app.text('#ctx-body') and app.state('S.ctx.src.kind') == 'qa'
    assert app.page.eval_on_selector_all('#set-tabs button', 'bs => bs.map((b) => b.textContent)')[1] == 'Контекст'


def test_local_folder_supplies_rules_templates_and_review(cx):
    assert cx.state('S.ctx.on') and cx.state('S.ctx.channel') == 'ext'
    assert cx.state('S.cfg.rules') == 'ПРАВИЛО-ИЗ-РЕПО: шаги в повелительном наклонении.'
    assert cx.state('S.cfg.reviewRules').startswith('РЕВЬЮ-ИЗ-РЕПО')
    assert cx.state('S.cfg.tpl.api.idPrefix') == 'BE-' and cx.state('S.cfg.tpl.ui.idPrefix') == 'UI-'   # шаблона UI в папке нет — действует шаблон команды


def test_memory_context_and_passport_come_from_the_product_folder(cx):
    assert cx.state('S.lessons.map((l) => [l.text.split(":")[0], l.scope])') == [['УРОК-ГЕН', 'generation'], ['УРОК-РЕВЬЮ', 'review'], ['УРОК-БЕЗ-МЕТКИ', 'generation']]
    assert cx.state('S.qaCtx.all') == 'ОКРУЖЕНИЕ-ИЗ-РЕПО stage' and cx.state('S.qaCtx.ui') == 'ЭКРАН-ИЗ-РЕПО Главная → Профиль'
    assert 'ПАСПОРТ-ИЗ-РЕПО' in cx.call('a.curProduct().passport.text')


def test_knowledge_base_sections_from_product_and_shared_folders(cx):
    titles = cx.call('a.kbSections(S.productId).map((x) => x.b.title)')
    assert 'Восстановление пароля' in titles and 'Глоссарий' in titles


def test_only_context_files_are_read(cx):
    reads = cx.page.evaluate('() => window.__repo.calls.filter((c) => c[1] === "read").length')
    assert reads >= 1 and cx.state('[...S.ctx.files.keys()].includes("other/notes.md")') is False


def test_pane_shows_what_was_found(cx):
    t = cx.text('#ctx-body')
    assert 'Папка на компьютере' in t and '/home/qa/ctx' in t and 'Шаблоны: 1 из 3' in t and 'База знаний: 2 раздела' in t
    assert 'загрузчик в браузере → мост' in t and 'Память агента' in t and '3 правила' in t


def test_generation_prompts_carry_the_repository_context(cx):
    cx.close_settings()
    cx.add_sample()
    cx.generate()
    gen = '\n'.join(c.prompt for c in cx.model.calls_of('promptGenerate'))
    for needle in ('ПРАВИЛО-ИЗ-РЕПО', 'УРОК-ГЕН', 'ОКРУЖЕНИЕ-ИЗ-РЕПО', 'ПАСПОРТ-ИЗ-РЕПО', 'ЗНАНИЕ-ИЗ-РЕПО'):
        assert needle in gen, needle
    assert 'ЭКРАН-ИЗ-РЕПО' in '\n'.join(c.prompt for c in cx.model.calls_of('promptGenerate') if 'вида UI' in c.prompt)
    assert 'BE-' in json.dumps(cx.state('S.run.cases.filter((c) => c.type === "api").map((c) => c.testCase.id)'))


def test_review_uses_repository_review_rules_and_lessons(cx):
    assert 'РЕВЬЮ-ИЗ-РЕПО' in cx.call('a.S.cfg.reviewRules') and any(l['scope'] == 'review' for l in cx.state('S.lessons'))


# ---------- запись в источник ----------
def test_saving_rules_writes_the_file(cx):
    cx.close_settings()
    cx.page.fill('#cfg-rules', 'НОВОЕ-ПРАВИЛО: проверять коды ответа')
    cx.page.wait_for_selector('#rules-foot [data-cfg=save]')
    assert 'Сохранить в источник' in cx.text('#rules-foot')
    cx.page.click('#rules-foot [data-cfg=save]')
    text = wait_repo(cx, 'rules/generation.md', 'НОВОЕ-ПРАВИЛО')
    assert text == '# Правила для агента\n\nНОВОЕ-ПРАВИЛО: проверять коды ответа\n'
    assert 'Из источника' in cx.text('#rules-foot')
    assert cx.db.store.get('config/rules') is None   # версия команды в хранилище не тронута


def test_template_saved_in_repository_format(cx):
    cx.call('(a.S.cfg.tpl.ui = { ...a.S.cfg.tpl.ui, idPrefix: "FE-" }, a.S.cfgDirty.ui = true, a.saveCfg("ui"))')
    text = wait_repo(cx, 'templates/ui.md', 'idPrefix: FE-')
    assert '## Правила' in text and '```json' in text
    assert cx.call('a.ctxParseTpl(arg, "ui").idPrefix', text) == 'FE-'


def test_new_lesson_goes_to_lessons_file(cx):
    cx.call('a.addLesson("НОВЫЙ-УРОК для ревью", "review")')
    assert '- [ревью] НОВЫЙ-УРОК для ревью' in wait_repo(cx, 'products/moi/memory.md', 'НОВЫЙ-УРОК')
    assert cx.db.store.get('lessons') is None and not [k for k in cx.db.store if k.startswith('lessons/')]


def test_qa_context_edit_goes_to_context_file(cx):
    cx.close_settings()
    cx.page.click('[data-ctx=api]')
    cx.page.fill('#qa-ctx', 'БАЗОВЫЙ-URL https://stage/api')
    text = wait_repo(cx, 'products/moi/context.md', 'БАЗОВЫЙ-URL')
    assert '## API\n\nБАЗОВЫЙ-URL https://stage/api' in text and '## UI\n\nЭКРАН-ИЗ-РЕПО' in text


def test_passport_update_is_written_to_the_repository(cx):
    cx.call('a.savePassport(S.productId, "## Термины\\n- ПАСПОРТ-ОБНОВЛЁН", null)')
    assert wait_repo(cx, 'products/moi/passport.md', 'ПАСПОРТ-ОБНОВЛЁН').startswith('## Термины')
    assert 'ПАСПОРТ-ОБНОВЛЁН' in cx.call('a.curProduct().passport.text')


def test_file_changed_in_source_is_not_overwritten(cx):
    cx.page.evaluate('() => { window.__repo.files["rules/generation.md"] = "ЧУЖАЯ ПРАВКА"; }')
    cx.call('(a.S.cfg.rules = "МОЯ ПРАВКА", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    cx.page.wait_for_function('() => window.__qa.S.ctx.conflicts.length === 1', timeout=8000)
    assert repo(cx, 'rules/generation.md') == 'ЧУЖАЯ ПРАВКА'
    assert 'изменились в источнике' in cx.text('#ctx-body') and cx.count('#settab-ctx .dot-d') == 1
    cx.page.click('[data-ctx-act=mine]')
    assert 'МОЯ ПРАВКА' in wait_repo(cx, 'rules/generation.md', 'МОЯ ПРАВКА')
    cx.page.wait_for_function('() => window.__qa.S.ctx.conflicts.length === 0')


def test_take_their_version_on_conflict(cx):
    cx.page.evaluate('() => { window.__repo.files["rules/generation.md"] = "# Правила для агента\\n\\nИХ ВЕРСИЯ"; }')
    cx.call('(a.S.cfg.rules = "МОЯ", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    cx.page.wait_for_selector('[data-ctx-act=theirs]', timeout=8000)
    cx.page.click('[data-ctx-act=theirs]')
    cx.page.wait_for_function('() => window.__qa.S.cfg.rules === "ИХ ВЕРСИЯ"')
    assert repo(cx, 'rules/generation.md').endswith('ИХ ВЕРСИЯ')


# ---------- приложение Claude: автоматические записи копятся ----------
def as_app(app):
    """Канал «мост в приложении Claude»: каждая запись там — отдельное подтверждение приложения."""
    app.call('(S.ctx.channel = "app", true)')
    return app


def test_claude_app_collects_automatic_writes(cx):
    """Автозапись выключена: правки копятся до кнопки «Записать в источник» (автозапись — test_context_autowrite)."""
    as_app(cx)
    cx.call('(S.ctx.src = { ...S.ctx.src, auto: false }, true)')
    cx.close_settings()
    cx.page.click('[data-ctx=api]')
    cx.page.fill('#qa-ctx', 'БАЗОВЫЙ-URL https://stage/api')
    cx.page.wait_for_function('() => window.__qa.S.ctx.pending.size === 1', timeout=8000)
    cx.call('a.addLesson("УРОК-В-ОЧЕРЕДИ", "generation")')
    cx.call('a.savePassport(S.productId, "## Термины\\n- ПАСПОРТ-В-ОЧЕРЕДИ", null)')
    cx.page.wait_for_timeout(1500)
    assert cx.state('[...S.ctx.pending].sort()') == ['products/moi/context.md', 'products/moi/memory.md', 'products/moi/passport.md']
    assert 'БАЗОВЫЙ-URL' not in repo(cx, 'products/moi/context.md')   # в источник ещё не ушло
    writes = lambda: cx.page.evaluate('() => window.__repo.calls.filter((c) => c[0] === "context_write").length')
    assert writes() == 0
    assert any('ждут записи' in t for t in cx.toast_texts())
    assert cx.state("document.querySelector('#btn-settings').classList.contains('dirty')")
    cx.open_settings('ctx')
    assert 'Ждут записи в источник: 3' in cx.text('#ctx-body') and cx.count('#settab-ctx .dot-d') == 1
    cx.page.click('[data-ctx-act=flush]')
    cx.page.wait_for_function('() => window.__qa.S.ctx.pending.size === 0 && !window.__qa.S.ctx.busy', timeout=8000)
    assert writes() == 1   # одна запись — одно подтверждение
    assert 'БАЗОВЫЙ-URL' in repo(cx, 'products/moi/context.md') and 'УРОК-В-ОЧЕРЕДИ' in repo(cx, 'products/moi/memory.md')
    assert 'ПАСПОРТ-В-ОЧЕРЕДИ' in repo(cx, 'products/moi/passport.md')


def test_claude_app_writes_explicit_save_at_once(cx):
    as_app(cx)
    cx.call('(a.S.cfg.rules = "СОХРАНЕНО-ЯВНО", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    assert 'СОХРАНЕНО-ЯВНО' in wait_repo(cx, 'rules/generation.md', 'СОХРАНЕНО-ЯВНО')


def test_claude_app_queue_survives_reload(cx):
    as_app(cx)
    cx.call('a.addLesson("УРОК-ДО-ПЕРЕЗАГРУЗКИ", "generation")')
    cx.page.wait_for_timeout(600)
    cx.reload()
    cx.page.wait_for_function('() => window.__qa.S.ctx.on && !window.__qa.S.ctx.busy && window.__qa.S.ctx.files.size > 0', timeout=15000)
    assert cx.state('[...S.ctx.pending]') == ['products/moi/memory.md']
    assert 'УРОК-ДО-ПЕРЕЗАГРУЗКИ' in cx.state('S.lessons.map((l) => l.text).join(" ")')


def test_declined_write_keeps_changes_and_offers_retry(cx):
    cx.page.evaluate('() => { window.__repo.failWrite = "Вызов моста отклонён в окне подтверждения приложения."; }')
    cx.call('(a.S.cfg.rules = "ПОСЛЕ-ОТКАЗА", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    cx.page.wait_for_function('() => !!window.__qa.S.ctx.error && !window.__qa.S.ctx.busy', timeout=8000)
    assert 'Повторить запись' in cx.text('#ctx-body') and 'отклонён' in cx.text('#ctx-body')
    assert cx.state('[...S.ctx.pending]') == ['rules/generation.md'] and repo(cx, 'rules/generation.md') == REPO['rules/generation.md']
    cx.page.click('[data-ctx-act=flush]')
    assert 'ПОСЛЕ-ОТКАЗА' in wait_repo(cx, 'rules/generation.md', 'ПОСЛЕ-ОТКАЗА')
    cx.page.wait_for_function('() => !window.__qa.S.ctx.error && window.__qa.S.ctx.pending.size === 0')


# ---------- выгрузка, обновление, отправка ----------
def test_export_qa_base_into_empty_repository(make_app):
    app = make_app(init=init(files={}))
    app.call('(a.S.cfg.rules = "ПРАВИЛА-КОМАНДЫ", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    app.page.wait_for_function('() => !window.__qa.S.cfgDirty.rules')
    app.call('a.addLesson("УРОК-КОМАНДЫ", "generation")')
    connect(app)
    assert app.state('S.cfg.rules') == 'ПРАВИЛА-КОМАНДЫ'   # файла нет — действует версия команды
    app.page.click('[data-ctx-act=export]')
    app.page.wait_for_selector('[data-ctx-act=export-run]')
    app.page.click('[data-ctx-act=export-run]')
    app.page.wait_for_function('() => !!window.__repo.files["CLAUDE.md"] && !window.__qa.S.ctx.pending.size', timeout=10000)
    files = repo(app)
    assert files['rules/generation.md'] == '# Правила для агента\n\nПРАВИЛА-КОМАНДЫ\n'
    assert {'templates/api.md', 'templates/ui.md', 'templates/e2e.md'} <= set(files)
    assert '- [генерация] УРОК-КОМАНДЫ' in files['products/moi/memory.md']
    assert 'products/moi/' in files['CLAUDE.md']
    assert app.call('a.ctxParseTpl(arg, "e2e").example', files['templates/e2e.md']) == app.state('S.cfg.tpl.e2e.example')


def test_export_warns_before_overwriting(cx):
    cx.page.click('[data-ctx-act=export]')
    cx.page.wait_for_selector('[data-ctx-act=export-run]')
    assert 'Будут перезаписаны' in cx.text('#ctx-body') and 'rules/generation.md' in cx.text('#ctx-body')
    cx.page.click('[data-ctx-act=confirm-no]')
    assert repo(cx, 'rules/generation.md') == REPO['rules/generation.md']


def test_refresh_pulls_and_rereads(cx):
    cx.page.evaluate('() => { window.__repo.onPull = (r) => { r.files["rules/generation.md"] = "# Правила для агента\\n\\nПОСЛЕ-PULL"; }; }')
    cx.page.click('[data-ctx-act=refresh]')
    cx.page.wait_for_function('() => window.__qa.S.cfg.rules === "ПОСЛЕ-PULL"', timeout=8000)
    assert cx.page.evaluate('() => window.__repo.pulls') == 1


def test_commit_and_push_from_settings(cx):
    cx.call('(a.S.cfg.rules = "К ОТПРАВКЕ", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    wait_repo(cx, 'rules/generation.md', 'К ОТПРАВКЕ')
    cx.page.click('[data-ctx-act=send]')
    cx.page.wait_for_function('() => !!window.__qa.S.ctx.lastPush', timeout=8000)
    assert cx.state('S.ctx.lastPush.branch') == 'qa-pro/2026-10-22-1830'
    assert 'открыть запрос на слияние' in cx.text('#ctx-body')


# ---------- отключение, перезагрузка ----------
def test_disconnect_returns_to_team_settings(make_app):
    app = make_app(init=init())
    app.call('(a.S.cfg.rules = "ПРАВИЛА-КОМАНДЫ", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    app.page.wait_for_function('() => !window.__qa.S.cfgDirty.rules')
    connect(app)
    assert app.state('S.cfg.rules').startswith('ПРАВИЛО-ИЗ-РЕПО')
    app.page.click('[data-ctx-act=off]')
    app.page.wait_for_function('() => window.__qa.S.ctx.src.kind === "qa"')
    assert app.state('S.cfg.rules') == 'ПРАВИЛА-КОМАНДЫ' and app.state('S.lessons.length') == 0
    assert 'Восстановление пароля' not in app.call('a.kbSections(S.productId).map((x) => x.b.title)')
    assert 'ПАСПОРТ-ИЗ-РЕПО' not in (app.call('a.curProduct().passport?.text || ""'))


def test_source_survives_reload(cx):
    cx.reload()
    cx.page.wait_for_function('() => window.__qa.S.ctx.on && window.__qa.S.ctx.files.size > 0 && !window.__qa.S.ctx.busy', timeout=15000)
    assert cx.state('S.cfg.rules').startswith('ПРАВИЛО-ИЗ-РЕПО') and cx.state('S.ctx.src.root') == '/home/qa/ctx'


def test_offline_source_falls_back_to_saved_copy(cx):
    cx.ctx.add_init_script(script='window.__ctxOffline = true;')
    cx.reload()
    cx.page.wait_for_function('() => window.__qa.S.ctx.on && !window.__qa.S.ctx.busy && !!window.__qa.S.ctx.error', timeout=20000)
    assert cx.state('S.ctx.fromCache') and cx.state('S.cfg.rules').startswith('ПРАВИЛО-ИЗ-РЕПО')
    assert 'работаю с копией' in cx.state('S.ctx.error') and 'Загрузчик QA pro версии 1.8 не видит' in cx.state('S.ctx.error')


def test_settings_are_personal_per_product(cx):
    pid = cx.state('S.productId')
    uid = cx.state('S.caps.uid')
    doc = cx.db.store.get(f'data/users/{uid}/ctx_{pid}')
    assert doc and doc['src']['kind'] == 'local' and doc['src']['root'] == '/home/qa/ctx'
    cx.close_settings()
    cx.create_product('Второй продукт')
    cx.page.wait_for_timeout(300)
    assert cx.state('S.ctx.on') is False and not cx.state('S.cfg.rules').startswith('ПРАВИЛО-ИЗ-РЕПО')


# ---------- проверки ввода ----------
@pytest.mark.parametrize('kind,field,value,msg', [
    ('local', 'root', 'ctx', 'полный путь'),
    ('git', 'url', 'ftp://host/repo', 'https://'),
    ('github', 'repo', 'просто-имя', 'владелец/название'),
])
def test_bad_input_is_explained(make_app, kind, field, value, msg):
    app = make_app(init=init())
    connect(app, kind=kind, **{field: value})
    assert msg in app.text('#ctx-body') and app.state('S.ctx.on') is False


def test_folder_outside_allowed_is_reported(make_app):
    app = connect(make_app(init=init()), root='/etc/secret')
    assert 'не разрешена' in app.text('#ctx-body') and app.state('S.ctx.on') is False
    assert app.count('#ctx-root') == 1   # форма осталась открытой для исправления


# ---------- git-репозиторий по адресу ----------
def test_git_url_is_cloned_by_the_bridge(make_app):
    app = connect(make_app(init=init()), kind='git', url='https://git.test/qa/ctx.git')
    assert app.state('S.ctx.src.cloned') == '/home/qa/.qa-pro-bridge/repos/qa-ctx'
    assert app.page.evaluate('() => window.__repo.calls[0]') == ['context_git', 'clone', 'https://git.test/qa/ctx.git']
    assert app.state('S.cfg.rules').startswith('ПРАВИЛО-ИЗ-РЕПО')


# ---------- GitHub без моста ----------
def test_github_reads_and_sends_to_a_branch(make_app):
    app = connect(make_app(init=init(files={}, gh=REPO)), kind='github', repo='team/qa-context')
    assert app.state('S.cfg.rules').startswith('ПРАВИЛО-ИЗ-РЕПО') and app.state('S.ctx.src.branch') == 'main'
    app.call('(a.S.cfg.rules = "ИЗ-QA-PRO", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    assert app.state('S.ctx.pending.size') == 1 and app.page.evaluate('() => Object.keys(window.__gh.branches).length') == 0
    app.page.wait_for_selector('#settab-ctx .dot-d')
    app.page.click('[data-ctx-act=send]')
    app.page.wait_for_function('() => !!window.__qa.S.ctx.lastPush', timeout=8000)
    br = app.page.evaluate('() => window.__gh.branches')
    assert list(br) == ['qa-pro/2026-10-22-183000'] and br['qa-pro/2026-10-22-183000']['rules/generation.md'].endswith('ИЗ-QA-PRO\n')
    assert app.state('S.ctx.src.branch') == 'qa-pro/2026-10-22-183000' and app.state('S.ctx.pending.size') == 0
    assert 'compare/main...qa-pro/2026-10-22-183000' in app.state('S.ctx.lastPush.pr')


def test_github_pending_changes_survive_reload(make_app):
    app = connect(make_app(init=init(files={}, gh=REPO)), kind='github', repo='team/qa-context')
    app.call('(a.S.cfg.rules = "НЕ-ОТПРАВЛЕНО", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    app.page.wait_for_timeout(500)
    app.reload()
    app.page.wait_for_function('() => window.__qa.S.ctx.on && !window.__qa.S.ctx.busy && window.__qa.S.ctx.files.size > 0', timeout=15000)
    assert app.state('S.cfg.rules') == 'НЕ-ОТПРАВЛЕНО' and app.state('S.ctx.pending.size') == 1


# ---------- папка только для чтения ----------
def pick(app, files, top='qa-context'):
    return app.call("""a.ctxPickFolder(Object.entries(arg.files).map(([p, t]) => ({ name: p.split('/').pop(), webkitRelativePath: arg.top + '/' + p, size: t.length, text: async () => t })))""", {'files': files, 'top': top})


def test_read_only_folder(make_app):
    app = make_app(init=init())
    app.open_settings('ctx')
    app.page.click('[data-ctx-act=edit]')
    app.page.click('label:has([data-ctxk=folder])')
    app.page.fill('#ctx-slug', 'moi')
    app.page.wait_for_selector('#ctx-pick', state='attached')
    pick(app, REPO)
    assert app.state('S.ctx.src.kind') == 'folder' and app.state('S.cfg.rules').startswith('ПРАВИЛО-ИЗ-РЕПО')
    assert app.state('S.ctx.files.size') == 8
    app.call('(a.S.cfg.rules = "ПОПЫТКА", a.S.cfgDirty.rules = true, a.saveCfg("rules"))')
    assert any('только для чтения' in t for t in app.toast_texts())
    assert 'Выбрать папку заново' in app.text('#ctx-body') and 'Выгрузить' not in app.text('#ctx-body')


# ---------- разбор файлов ----------
def test_lessons_and_qa_context_round_trip(app):
    ls = [{'text': 'один', 'scope': 'generation'}, {'text': 'два', 'scope': 'review'}, {'text': 'три', 'scope': 'both'}]
    back = app.call('a.ctxParseLessons(a.ctxMakeLessons(arg)).map((l) => [l.text, l.scope])', ls)
    assert back == [['один', 'generation'], ['два', 'review'], ['три', 'both']]
    c = {'all': 'общий', 'api': '', 'ui': 'экраны\nвторая строка', 'e2e': 'письма'}
    assert app.call('a.ctxParseQaCtx(a.ctxMakeQaCtx(arg))', c) == c


def test_template_round_trip(app):
    tp = app.state('S.cfg.tpl.api')
    assert app.call('a.ctxParseTpl(a.ctxMakeTpl("api", arg), "api")', tp) == tp


def test_template_without_json_sample_falls_back_with_warning(make_app):
    files = dict(REPO, **{'templates/api.md': '# Шаблон API\n\nidPrefix: X-\n\nбез образца'})
    app = connect(make_app(init=init(files=files)))
    assert app.state('S.cfg.tpl.api.idPrefix') == 'API-' and 'нет образца' in app.text('#ctx-body')
