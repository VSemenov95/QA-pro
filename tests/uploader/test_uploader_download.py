"""Скачивание загрузчика (.zip) и моста (.mcpb) из QA pro: архивы собираются из исходников репозитория и совпадают с ними."""
import base64
import json
import os
import shutil
import subprocess
import zipfile

import pytest

from tests.support.bridge import BRIDGE_SRC, Bridge, clean_env, have_node
from tests.support.extension import EXT_SRC


def files_of(root):
    return {os.path.relpath(os.path.join(r, f), root).replace(os.sep, '/'): os.path.join(r, f) for r, _, fs in os.walk(root) for f in fs}


def save_download(app, click, tmp_path):
    """В артефакте файл отдаётся через возможность «downloads»: тест забирает его из страницы."""
    app.page.evaluate('() => { window.__dlBlob = null; window.__dl = null; }')
    click()
    app.page.wait_for_function('() => window.__dl && window.__dlBlob', timeout=10000)
    name = app.page.evaluate('window.__dl.filename')
    b64 = app.page.evaluate("window.__dlBlob.arrayBuffer().then((a) => { let s = ''; new Uint8Array(a).forEach((x) => { s += String.fromCharCode(x); }); return btoa(s); })")
    path = tmp_path / name
    path.write_bytes(base64.b64decode(b64))
    return name, path


@pytest.fixture
def uploader_zip(app, tmp_path):
    app.open_settings('tms')
    app.page.wait_for_selector('#tms-body [data-act=sfera-zip]')
    name, path = save_download(app, lambda: app.page.click('#tms-body [data-act=sfera-zip]'), tmp_path)
    return name, zipfile.ZipFile(path)


@pytest.fixture
def bridge_mcpb(app, tmp_path):
    app.mode('help')
    app.page.click('#help-head [data-act=help-view][data-v=mat]')
    app.page.wait_for_selector('#mat-asr [data-act=bridge-mcpb]')
    name, path = save_download(app, lambda: app.page.click('#mat-asr [data-act=bridge-mcpb]'), tmp_path)
    return name, path


# ---------- загрузчик ----------
def test_uploader_zip_is_named_and_valid(uploader_zip):
    name, zf = uploader_zip
    assert name == 'qa-pro-sfera-uploader.zip' and zf.testzip() is None


def test_uploader_zip_has_a_folder_with_all_extension_files(uploader_zip):
    _, zf = uploader_zip
    files = [f for f in os.listdir(EXT_SRC) if os.path.isfile(os.path.join(EXT_SRC, f))]
    assert sorted(zf.namelist()) == sorted('qa-pro-sfera-uploader/' + f for f in files)


def test_uploader_zip_files_are_identical_to_the_repository(uploader_zip):
    _, zf = uploader_zip
    for n in zf.namelist():
        with open(os.path.join(EXT_SRC, n.split('/', 1)[1]), 'rb') as f:
            assert zf.read(n) == f.read(), n


def test_uploader_zip_manifest_is_loadable(uploader_zip):
    _, zf = uploader_zip
    m = json.loads(zf.read('qa-pro-sfera-uploader/manifest.json'))
    assert m['manifest_version'] == 3 and all(zf.getinfo('qa-pro-sfera-uploader/' + f) for f in [m['background']['service_worker'], m['options_page']])


# ---------- мост ----------
def test_bridge_package_is_named_and_valid(bridge_mcpb):
    name, path = bridge_mcpb
    assert name == 'qa-pro-bridge.mcpb' and zipfile.ZipFile(path).testzip() is None


def test_bridge_package_has_manifest_in_the_root(bridge_mcpb):
    """.mcpb — архив с manifest.json в корне."""
    _, path = bridge_mcpb
    assert 'manifest.json' in zipfile.ZipFile(path).namelist()


def test_bridge_package_has_the_same_files_as_the_repository(bridge_mcpb):
    _, path = bridge_mcpb
    zf = zipfile.ZipFile(path)
    src = files_of(BRIDGE_SRC)
    assert sorted(zf.namelist()) == sorted(src)
    for n in zf.namelist():
        with open(src[n], 'rb') as f:
            assert zf.read(n) == f.read(), n


def test_bridge_package_manifest_points_to_a_packed_entry_point(bridge_mcpb):
    _, path = bridge_mcpb
    zf = zipfile.ZipFile(path)
    m = json.loads(zf.read('manifest.json'))
    assert m['server']['entry_point'] in zf.namelist() and m['display_name'] == 'QA pro — мост к загрузчику Сферы ФТ'


@pytest.mark.skipif(not have_node(), reason='нет Node.js: распакованный мост не запустить')
def test_bridge_unpacked_from_the_page_starts_and_answers(bridge_mcpb, tmp_path):
    """Мост, распакованный из скачанного файла, запускается и отвечает на ping (так его запускает приложение Claude)."""
    _, path = bridge_mcpb
    out = tmp_path / 'unpacked'
    zipfile.ZipFile(path).extractall(out)
    b = Bridge(tmp_path / 'data')
    try:
        b.proc = subprocess.Popen(['node', str(out / 'server' / 'index.js')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=b.env, text=True, encoding='utf-8')
        import threading
        threading.Thread(target=b._read_out, daemon=True).start()
        threading.Thread(target=b._read_err, daemon=True).start()
        b.rpc('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 't', 'version': '1'}})
        p = b.tool('ping')
        assert p['ok'] and p['listening'] and p['core'] == 'background'
    finally:
        b.stop()


@pytest.mark.skipif(shutil.which('mcpb') is None, reason='нет утилиты mcpb (npm i -g @anthropic-ai/mcpb): проверка архива её командой info/unpack пропущена')
def test_bridge_package_is_accepted_by_the_mcpb_tool(bridge_mcpb, tmp_path):
    _, path = bridge_mcpb
    info = subprocess.run(['mcpb', 'info', str(path)], capture_output=True, text=True, env=clean_env())
    assert info.returncode == 0 and 'qa-pro-bridge' in info.stdout
    un = subprocess.run(['mcpb', 'unpack', str(path), str(tmp_path / 'u')], capture_output=True, text=True, env=clean_env())
    assert un.returncode == 0 and (tmp_path / 'u' / 'server' / 'index.js').exists()
