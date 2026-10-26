"""Загрузчик: «GitHub без моста» (uploader/…/context.js) на поддельном API GitHub, без браузера (Node, vm)."""
import json
import os
import subprocess

import pytest

HARNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gh_harness.js')


def run(scenario):
    r = subprocess.run(['node', HARNESS, scenario], capture_output=True, text=True, timeout=60)
    out = json.loads(r.stdout or '{}')
    assert 'fatal' not in out, out.get('fatal')
    return out


@pytest.fixture(scope='module')
def flow(need_node_module):
    return run('flow')


@pytest.fixture(scope='module')
def need_node_module():
    from tests.support.bridge import have_node
    if not have_node():
        pytest.skip('нет Node.js')


def test_first_access_asks_the_user_once(flow):
    assert flow['asks'] == 1 and flow['asksAfter'] == 1
    assert flow['grants'] == {'https://abc.claudeusercontent.com': {'roots': [], 'repos': [], 'gh': ['team/ctx'], 'at': flow['grants']['https://abc.claudeusercontent.com']['at']}}


def test_list_has_only_visible_text_files(flow):
    assert [f['path'] for f in flow['list']['files']] == ['rules/generation.md', 'products/moi/kb/a.md']
    assert flow['list']['branch'] == 'main' and flow['list']['web'] == 'https://github.com/team/ctx'


def test_read_decodes_utf8(flow):
    files = {f['path']: f for f in flow['read']['files']}
    assert files['rules/generation.md']['text'] == 'ПРАВИЛО' and files['нет.md'] == {'path': 'нет.md', 'missing': True}


def test_commit_goes_to_a_new_branch_not_main(flow):
    c = flow['c1']
    assert c['committed'] and c['branch'].startswith('qa-pro/') and c['base'] == 'main'
    assert flow['mainAfter'] == 'ПРАВИЛО'
    assert flow['branchAfter']['rules/generation.md'] == 'НОВОЕ' and flow['branchAfter']['products/moi/memory.md'] == '- урок'
    assert c['pr'] == f"https://github.com/team/ctx/compare/main...{c['branch']}?expand=1"


def test_next_commit_from_own_branch_updates_it(flow):
    assert flow['c2']['branch'] == flow['c1']['branch'] and flow['c2']['base'] == 'main'
    assert flow['branches'] == sorted(['main', flow['c1']['branch']])


def test_commit_over_changed_file_is_a_conflict():
    out = run('conflict')
    assert out['r']['committed'] is False and out['r']['conflicts'][0]['path'] == 'rules/generation.md'
    assert out['branches'] == ['main']


def test_denied_repository():
    out = run('deny')
    assert out['code'] == 'denied' and out['calls'] == 0


def test_bad_paths_are_refused():
    out = run('badpath')
    assert all(v == 'bad_path' for v in out.values()), out


def test_missing_token_is_explained():
    out = run('notoken')
    assert out['code'] == 'gh_no_token' and 'токен GitHub' in out['error']


def test_ping_reports_token_without_revealing_it():
    out = run('pages')
    assert out['ping']['gh'] is True and 'tok' not in json.dumps(out)
