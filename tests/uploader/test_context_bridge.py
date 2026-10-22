"""Мост qa-pro-bridge как источник контекста QA pro: инструменты context_read, context_write, context_git (настоящие Node-процессы и git).

Что проверяется: разрешённые папки (настройка моста, загрузчик, --allow), запрет выхода за папку и не-текстовых файлов, конфликт при
записи поверх чужой правки, git: clone (только https/ssh), pull, commit в ветку qa-pro/<дата>, push, запрет отправки в main;
вызовы из загрузчика по WebSocket (ctx, ctx_allow) и режим --keep для QA pro в браузере.
"""
import json
import os
import shutil
import subprocess

import pytest

from tests.support.bridge import BRIDGE_SRC, SERVER, BridgeError, clean_env, until

pytestmark = pytest.mark.skipif(shutil.which('git') is None, reason='нет git')


def sh(*args, cwd=None):
    return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@t', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


@pytest.fixture
def ctxdir(tmp_path):
    d = tmp_path / 'ctx'
    (d / 'rules').mkdir(parents=True)
    (d / 'rules' / 'generation.md').write_text('# Правила для агента\n\nПРАВИЛО\n', encoding='utf-8')
    (d / 'products' / 'moi' / 'kb').mkdir(parents=True)
    (d / 'products' / 'moi' / 'kb' / 'a.md').write_text('# Раздел\n\nтекст', encoding='utf-8')
    (d / 'image.png').write_bytes(b'\x89PNG')
    (d / '.hidden').mkdir()
    (d / '.hidden' / 'x.md').write_text('скрыто', encoding='utf-8')
    return d


@pytest.fixture
def br(make_bridge, ctxdir):
    return make_bridge(env={'QA_PRO_CONTEXT_DIR': str(ctxdir)})


@pytest.fixture
def remote(tmp_path):
    """«Удалённый» репозиторий (bare) с одним коммитом в main."""
    origin = tmp_path / 'origin.git'
    sh('init', '-q', '--bare', '-b', 'main', str(origin))
    seed = tmp_path / 'seed'
    sh('clone', '-q', str(origin), str(seed))
    (seed / 'rules').mkdir()
    (seed / 'rules' / 'generation.md').write_text('# Правила для агента\n\nИЗ-GIT\n', encoding='utf-8')
    sh('add', '.', cwd=seed)
    sh('commit', '-qm', 'init', cwd=seed)
    sh('push', '-q', 'origin', 'HEAD:main', cwd=seed)
    return origin, seed


# ---------- инструменты и манифест ----------
def test_context_tools_are_listed(bridge):
    names = {t['name'] for t in bridge.tools()}
    assert {'context_read', 'context_write', 'context_git'} <= names
    ro = {t['name']: t['annotations'].get('readOnlyHint') for t in bridge.tools()}
    assert ro['context_read'] is True and ro['context_write'] is False and ro['context_git'] is False


def test_manifest_declares_context_tools_and_folder_setting():
    with open(os.path.join(BRIDGE_SRC, 'manifest.json'), encoding='utf-8') as f:
        m = json.load(f)
    assert {'context_read', 'context_write', 'context_git'} <= {t['name'] for t in m['tools']}
    assert m['user_config']['context_dir']['type'] == 'directory'
    assert m['server']['mcp_config']['env']['QA_PRO_CONTEXT_DIR'] == '${user_config.context_dir}'


# ---------- разрешённые папки ----------
def test_folder_from_bridge_settings_is_listed(br, ctxdir):
    r = br.tool('context_read', {'op': 'list', 'root': str(ctxdir)})
    assert [f['path'] for f in r['files']] == ['products/moi/kb/a.md', 'rules/generation.md']   # без картинок и скрытых папок
    assert r['git'] == {'repo': False}


def test_unknown_folder_is_refused(br, tmp_path):
    other = tmp_path / 'other'
    other.mkdir()
    with pytest.raises(BridgeError, match='не разрешена'):
        br.tool('context_read', {'op': 'list', 'root': str(other)})


def test_settings_placeholder_is_ignored(make_bridge, ctxdir):
    b = make_bridge(env={'QA_PRO_CONTEXT_DIR': '${user_config.context_dir}'})
    assert b.tool('context_read', {'op': 'roots'})['roots'] == []


def test_allow_from_command_line(bridge, ctxdir):
    out = subprocess.run(['node', os.path.join(SERVER, 'core.js'), '--allow', str(ctxdir)], env=clean_env(QA_PRO_BRIDGE_DIR=bridge.dir), capture_output=True, text=True, check=True).stdout
    assert 'Разрешена папка контекста' in out
    assert bridge.tool('context_read', {'op': 'list', 'root': str(ctxdir)})['files']


@pytest.mark.parametrize('path', ['../x.md', '/etc/passwd.md', 'rules/../../x.md', '.git/config.md', 'C:/x.md'])
def test_paths_outside_the_folder_are_refused(br, ctxdir, path):
    r = br.tool('context_read', {'op': 'read', 'root': str(ctxdir), 'paths': [path]})
    assert 'error' in r['files'][0]
    with pytest.raises(BridgeError, match='вне папки|за пределы'):
        br.tool('context_write', {'root': str(ctxdir), 'files': [{'path': path, 'text': 'x', 'base': None}]})


def test_symlink_out_of_the_folder_is_refused(br, ctxdir, tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    (outside / 'secret.md').write_text('секрет', encoding='utf-8')
    os.symlink(outside, ctxdir / 'link')
    r = br.tool('context_read', {'op': 'read', 'root': str(ctxdir), 'paths': ['link/secret.md']})
    assert 'за пределы' in r['files'][0]['error']


def test_only_text_files_are_written(br, ctxdir):
    with pytest.raises(BridgeError, match='только .md'):
        br.tool('context_write', {'root': str(ctxdir), 'files': [{'path': 'run.sh', 'text': 'rm -rf /', 'base': None}]})


# ---------- чтение и запись ----------
def test_read_returns_text_and_fingerprint(br, ctxdir):
    r = br.tool('context_read', {'op': 'read', 'root': str(ctxdir), 'paths': ['rules/generation.md', 'нет.md']})
    assert r['files'][0]['text'] == '# Правила для агента\n\nПРАВИЛО\n' and len(r['files'][0]['hash']) == 40
    assert r['files'][1] == {'path': 'нет.md', 'missing': True}


def test_write_new_and_changed_files(br, ctxdir):
    h = br.tool('context_read', {'op': 'read', 'root': str(ctxdir), 'paths': ['rules/generation.md']})['files'][0]['hash']
    r = br.tool('context_write', {'root': str(ctxdir), 'files': [{'path': 'rules/generation.md', 'text': 'НОВОЕ', 'base': h}, {'path': 'products/moi/passport.md', 'text': 'П', 'base': None}]})
    assert [w['path'] for w in r['written']] == ['rules/generation.md', 'products/moi/passport.md'] and r['conflicts'] == []
    assert (ctxdir / 'rules' / 'generation.md').read_text(encoding='utf-8') == 'НОВОЕ'
    assert (ctxdir / 'products' / 'moi' / 'passport.md').read_text(encoding='utf-8') == 'П'


def test_write_over_someone_elses_change_is_a_conflict(br, ctxdir):
    h = br.tool('context_read', {'op': 'read', 'root': str(ctxdir), 'paths': ['rules/generation.md']})['files'][0]['hash']
    (ctxdir / 'rules' / 'generation.md').write_text('ЧУЖАЯ', encoding='utf-8')
    r = br.tool('context_write', {'root': str(ctxdir), 'files': [{'path': 'rules/generation.md', 'text': 'МОЯ', 'base': h}, {'path': 'new.md', 'text': 'n', 'base': None}]})
    assert r['written'] == [] and r['conflicts'][0]['path'] == 'rules/generation.md' and r['conflicts'][0]['text'] == 'ЧУЖАЯ'
    assert not (ctxdir / 'new.md').exists()   # ничего не записано, пока есть конфликт
    r = br.tool('context_write', {'root': str(ctxdir), 'force': True, 'files': [{'path': 'rules/generation.md', 'text': 'МОЯ', 'base': h}]})
    assert r['written'] and (ctxdir / 'rules' / 'generation.md').read_text(encoding='utf-8') == 'МОЯ'


# ---------- git ----------
@pytest.fixture
def gbr(make_bridge, ctxdir):
    return make_bridge(env={'QA_PRO_CONTEXT_DIR': str(ctxdir), 'QA_PRO_BRIDGE_ALLOW_FILE_URLS': '1'})


def test_clone_pull_commit_push(gbr, remote, tmp_path):
    origin, seed = remote
    c = gbr.tool('context_git', {'op': 'clone', 'url': 'file://' + str(origin)})
    root = c['root']
    assert c['cloned'] and root.startswith(os.path.realpath(gbr.dir)) and '/repos/' in root
    assert gbr.tool('context_read', {'op': 'read', 'root': root, 'paths': ['rules/generation.md']})['files'][0]['text'].endswith('ИЗ-GIT\n')
    # коллега отправил правку — pull её получает
    (seed / 'rules' / 'review.md').write_text('РЕВЬЮ', encoding='utf-8')
    sh('add', '.', cwd=seed)
    sh('commit', '-qm', 'review', cwd=seed)
    sh('push', '-q', 'origin', 'HEAD:main', cwd=seed)
    p = gbr.tool('context_git', {'op': 'pull', 'root': root})
    assert p['updated'] and os.path.exists(os.path.join(root, 'rules', 'review.md'))
    # правка QA pro → коммит в ветку qa-pro/<дата> → push
    open(os.path.join(root, 'rules', 'generation.md'), 'w', encoding='utf-8').write('ИЗ-QA-PRO')
    st = gbr.tool('context_read', {'op': 'status', 'root': root})
    assert st['branch'] == 'main' and st['changed'] == [{'code': 'M', 'path': 'rules/generation.md'}]
    cm = gbr.tool('context_git', {'op': 'commit', 'root': root, 'message': 'QA pro: правила'})
    assert cm['committed'] and cm['branch'].startswith('qa-pro/') and cm['files'] == ['rules/generation.md']
    ps = gbr.tool('context_git', {'op': 'push', 'root': root})
    assert ps['branch'] == cm['branch']
    assert cm['branch'] in sh('branch', '--list', cwd=str(origin))
    assert sh('log', '-1', '--format=%s', cm['branch'], cwd=str(origin)).strip() == 'QA pro: правила'
    # второй коммит идёт в ту же ветку
    open(os.path.join(root, 'rules', 'generation.md'), 'w', encoding='utf-8').write('ЕЩЁ')
    assert gbr.tool('context_git', {'op': 'commit', 'root': root, 'message': 'ещё'})['branch'] == cm['branch']


def test_clone_twice_reuses_the_clone(gbr, remote):
    origin, _ = remote
    a = gbr.tool('context_git', {'op': 'clone', 'url': 'file://' + str(origin)})
    b = gbr.tool('context_git', {'op': 'clone', 'url': 'file://' + str(origin)})
    assert a['root'] == b['root'] and b['cloned'] is False


def test_nothing_to_commit(gbr, remote):
    origin, _ = remote
    root = gbr.tool('context_git', {'op': 'clone', 'url': 'file://' + str(origin)})['root']
    assert gbr.tool('context_git', {'op': 'commit', 'root': root, 'message': 'x'})['committed'] is False


def test_push_to_main_is_refused(gbr, remote):
    origin, _ = remote
    root = gbr.tool('context_git', {'op': 'clone', 'url': 'file://' + str(origin)})['root']
    with pytest.raises(BridgeError, match='не отправляет изменения прямо в main'):
        gbr.tool('context_git', {'op': 'push', 'root': root})


@pytest.mark.parametrize('url', ['ext::sh -c id', '--upload-pack=touch /tmp/x', 'file:///etc', '/home/me/repo', 'http://insecure/repo.git'])
def test_only_https_and_ssh_urls(br, url):
    with pytest.raises(BridgeError, match='Поддерживаются адреса|Некорректный адрес'):
        br.tool('context_git', {'op': 'clone', 'url': url})


def test_folder_without_git(br, ctxdir):
    with pytest.raises(BridgeError, match='не является git-репозиторием'):
        br.tool('context_git', {'op': 'pull', 'root': str(ctxdir)})


# ---------- из загрузчика по WebSocket ----------
def test_extension_allows_a_folder_and_calls_tools(bridge, ctxdir):
    ws = bridge.ws()
    ws.send({'t': 'ctx', 'id': 'c1', 'tool': 'context_read', 'args': {'op': 'list', 'root': str(ctxdir)}})
    r = ws.wait(lambda m: m.get('id') == 'c1')
    assert r['t'] == 'ctx_result' and r['ok'] is False and r['code'] == 'root_not_allowed'
    ws.send({'t': 'ctx_allow', 'id': 'a1', 'root': str(ctxdir)})
    assert ws.wait(lambda m: m.get('id') == 'a1')['ok'] is True
    ws.send({'t': 'ctx', 'id': 'c2', 'tool': 'context_read', 'args': {'op': 'read', 'root': str(ctxdir), 'paths': ['rules/generation.md']}})
    r = ws.wait(lambda m: m.get('id') == 'c2')
    assert r['ok'] and r['data']['files'][0]['text'].endswith('ПРАВИЛО\n')
    with open(os.path.join(bridge.dir, 'context.json'), encoding='utf-8') as f:
        assert os.path.realpath(str(ctxdir)) in json.load(f)['roots']
    assert ws.of('ack') == []   # вызовы контекста — не задания загрузчика


def test_extension_cannot_call_other_tools(bridge):
    ws = bridge.ws()
    ws.send({'t': 'ctx', 'id': 'x', 'tool': 'sfera_upload', 'args': {'cases': [{'name': 'a'}]}})
    r = ws.wait(lambda m: m.get('id') == 'x')
    assert r['ok'] is False and r['code'] == 'bad_tool'
    assert bridge.tool('ping')['pending'] == 0


def test_forget_folder(bridge, ctxdir):
    ws = bridge.ws()
    ws.send({'t': 'ctx_allow', 'id': 'a', 'root': str(ctxdir)})
    ws.wait(lambda m: m.get('id') == 'a')
    ws.send({'t': 'ctx_forget', 'id': 'f', 'root': str(ctxdir)})
    ws.wait(lambda m: m.get('id') == 'f')
    with pytest.raises(BridgeError, match='не разрешена'):
        bridge.tool('context_read', {'op': 'list', 'root': str(ctxdir)})


# ---------- ядро без приложения Claude ----------
def test_core_with_keep_runs_on_its_own(tmp_path, need_node):
    from tests.support.bridge import free_port, http
    port = free_port()
    p = subprocess.Popen(['node', os.path.join(SERVER, 'core.js'), '--keep'], env=clean_env(QA_PRO_BRIDGE_PORT=port, QA_PRO_BRIDGE_DIR=str(tmp_path / 'b')), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        def health():
            try:
                code, body = http(port, 'GET', '/health', timeout=1)
                return body if code == 200 else None
            except OSError:
                return None
        h = until(health, timeout=10)
        assert h['keep'] is True and h['mode'] == 'standalone' and h['version'] == '1.5.0'
    finally:
        p.kill()
