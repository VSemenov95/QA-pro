"""Бета-инструменты моста: операции Сферы через загрузчик (sfera_call) и локальный репозиторий автотестов (project_*)."""
import os
import threading

import pytest

from tests.support.bridge import BridgeError


def ws_answer(ws, ok=True, data=None, error=''):
    """«Загрузчик»: ждёт операцию и отвечает на неё."""
    def run():
        m = ws.wait(lambda m: m['t'] == 'call', timeout=15)
        ws.send({'t': 'call_result', 'id': m['id'], 'ok': ok, 'data': data, 'error': error, 'code': '' if ok else 'not_configured'})
        ws.last_call = m
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def test_sfera_call_goes_to_uploader_and_back(bridge):
    ws = bridge.ws()
    t = ws_answer(ws, data={'key': 'RECOV-326', 'url': 'https://sfera/x'})
    r = bridge.tool('sfera_call', {'op': 'tasks.create', 'args': {'project': 'RECOV', 'title': 'Дефект'}})
    t.join(5)
    assert r == {'ok': True, 'data': {'key': 'RECOV-326', 'url': 'https://sfera/x'}}
    assert ws.last_call['op'] == 'tasks.create' and ws.last_call['args']['project'] == 'RECOV'


def test_sfera_call_error_is_reported(bridge):
    ws = bridge.ws()
    ws_answer(ws, ok=False, error='Операция «tasks.create» не описана')
    with pytest.raises(BridgeError, match='не описана'):
        bridge.tool('sfera_call', {'op': 'tasks.create', 'args': {}})


def test_sfera_call_without_uploader(bridge):
    with pytest.raises(BridgeError, match='не подключён'):
        bridge.tool('sfera_call', {'op': 'tasks.search', 'args': {}})


def test_sfera_call_rejects_unknown_op(bridge):
    bridge.ws()
    with pytest.raises(BridgeError, match='Неизвестная операция'):
        bridge.tool('sfera_call', {'op': 'fs.delete', 'args': {}})


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / 'autotests'
    (root / 'src/test/java/ru/t').mkdir(parents=True)
    (root / 'src/test/java/ru/t/LoginTests.java').write_text('class LoginTests {}', encoding='utf-8')
    (root / 'build.gradle').write_text("plugins { id 'java' }", encoding='utf-8')
    (root / 'build').mkdir()
    (root / 'build/Gen.java').write_text('skip', encoding='utf-8')
    (root / '.git').mkdir()
    (root / '.git/config').write_text('x', encoding='utf-8')
    (root / 'img.png').write_bytes(b'\x89PNG')
    return root


def test_project_list_skips_build_and_binaries(bridge, repo):
    r = bridge.tool('project_list', {'root': str(repo)})
    assert sorted(f['path'] for f in r['files']) == ['build.gradle', 'src/test/java/ru/t/LoginTests.java']


def test_project_read_and_write(bridge, repo):
    r = bridge.tool('project_read', {'root': str(repo), 'paths': ['src/test/java/ru/t/LoginTests.java']})
    assert r['files'][0]['text'] == 'class LoginTests {}'
    w = bridge.tool('project_write', {'root': str(repo), 'files': [{'path': 'src/test/java/ru/t/NewTests.java', 'content': 'class NewTests {}'}, {'path': 'src/test/java/ru/t/LoginTests.java', 'content': 'class LoginTests { void a() {} }'}]})
    assert w['written'] == [{'path': 'src/test/java/ru/t/NewTests.java', 'created': True}, {'path': 'src/test/java/ru/t/LoginTests.java', 'created': False}]
    assert (repo / 'src/test/java/ru/t/NewTests.java').read_text(encoding='utf-8') == 'class NewTests {}'


@pytest.mark.parametrize('bad', ['../outside.java', '/etc/x.java', 'src/../../x.java'])
def test_project_write_stays_inside_root(bridge, repo, bad):
    with pytest.raises(BridgeError, match='вне папки|за пределы'):
        bridge.tool('project_write', {'root': str(repo), 'files': [{'path': bad, 'content': 'x'}]})
    assert not os.path.exists(os.path.join(str(repo.parent), 'outside.java'))


def test_project_write_refuses_other_files(bridge, repo):
    with pytest.raises(BridgeError, match='не разрешена'):
        bridge.tool('project_write', {'root': str(repo), 'files': [{'path': 'run.sh', 'content': 'rm -rf /'}]})


def test_project_needs_absolute_existing_root(bridge, tmp_path):
    with pytest.raises(BridgeError, match='полный путь'):
        bridge.tool('project_list', {'root': 'autotests'})
    with pytest.raises(BridgeError, match='не найдена'):
        bridge.tool('project_list', {'root': str(tmp_path / 'nope')})


def test_symlink_out_of_root_is_refused(bridge, repo, tmp_path):
    outside = tmp_path / 'secret'
    outside.mkdir()
    os.symlink(outside, repo / 'link')
    with pytest.raises(BridgeError, match='за пределы'):
        bridge.tool('project_write', {'root': str(repo), 'files': [{'path': 'link/x.java', 'content': 'x'}]})
    assert not (outside / 'x.java').exists()
