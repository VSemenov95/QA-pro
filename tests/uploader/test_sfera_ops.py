"""Операции API Сферы в загрузчике (callOp): подстановка аргументов, query, тело, pick/map, ошибки.
background.js выполняется в Node с заглушками chrome и fetch — без браузера."""
import json
import os
import subprocess

import pytest

from tests.support.bridge import ROOT

BG = os.path.join(ROOT, 'uploader', 'qa-pro-sfera-uploader', 'background.js')

HARNESS = r"""
const fs = require('fs');
const stored = { settings: __SETTINGS__ };
const noop = () => {};
const ev = { addListener: noop };
global.chrome = {
  storage: { local: { get: async (k) => ({ [k]: stored[k] }), set: async (o) => Object.assign(stored, o) }, session: { get: async () => ({}), set: async () => {}, remove: async () => {} } },
  cookies: { get: async () => (__TOKEN__ ? { value: __TOKEN__ } : null) },
  runtime: { getManifest: () => ({ version: '1.7.0', content_scripts: [{ matches: [] }] }), onInstalled: ev, onStartup: ev, onMessage: ev, sendMessage: async () => {} },
  windows: { onRemoved: ev, create: async () => ({}) }, action: { onClicked: ev }, alarms: { create: noop, onAlarm: ev },
  scripting: {}, tabs: { query: async () => [] },
};
global.WebSocket = function () {}; global.WebSocket.OPEN = 1;
const calls = [];
global.fetch = async (url, opt = {}) => {
  if (String(url).includes('127.0.0.1')) throw new Error('no bridge');
  calls.push({ url, method: opt.method, body: opt.body ? JSON.parse(opt.body) : null, auth: opt.headers?.Authorization });
  return { ok: __STATUS__ < 400, status: __STATUS__, text: async () => JSON.stringify(__RESPONSE__) };
};
eval(fs.readFileSync(__BG__, 'utf8'));
callOp(__OP__, __ARGS__).then((r) => console.log(JSON.stringify({ ok: true, r, calls })), (e) => console.log(JSON.stringify({ ok: false, error: e.message, code: e.code, calls })));
"""


def run(op, args, ops, response=None, status=200, token='tok'):
    code = (HARNESS.replace('__SETTINGS__', json.dumps({'baseUrl': 'https://sfera.test', 'sferaOps': ops}))
            .replace('__TOKEN__', json.dumps(token)).replace('__STATUS__', str(status)).replace('__RESPONSE__', json.dumps(response))
            .replace('__OP__', json.dumps(op)).replace('__ARGS__', json.dumps(args)).replace('__BG__', json.dumps(BG)))
    out = subprocess.run(['node', '-e', code], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr[-500:]
    return json.loads(out.stdout.strip().splitlines()[-1])


@pytest.fixture(autouse=True)
def _node(need_node):
    pass


def test_create_task_fills_body_and_maps_result():
    ops = {'tasks.create': {'method': 'POST', 'path': '/app/tasks/api/v1/projects/{project}/entities', 'body': {'name': '{title}', 'labels': '{labels}', 'text': 'Дефект: {title}'}, 'map': {'key': 'number', 'url': 'links.self'}}}
    r = run('tasks.create', {'project': 'RE COV', 'title': 'Сломалось', 'labels': ['QA_pro']}, ops, {'number': 'RECOV-1', 'links': {'self': 'https://x'}})
    assert r['ok'] and r['r'] == {'key': 'RECOV-1', 'url': 'https://x'}
    c = r['calls'][0]
    assert c['url'] == 'https://sfera.test/app/tasks/api/v1/projects/RE%20COV/entities'
    assert c['body'] == {'name': 'Сломалось', 'labels': ['QA_pro'], 'text': 'Дефект: Сломалось'}
    assert c['auth'] == 'Bearer tok'


def test_search_query_and_list_mapping():
    ops = {'tasks.search': {'path': '/api/tasks', 'query': {'q': '{text}', 'release': '{release}'}, 'pick': 'content', 'map': {'key': 'code', 'status': 'status.name'}}}
    r = run('tasks.search', {'text': 'email +', 'release': ''}, ops, {'content': [{'code': 'A-1', 'status': {'name': 'Исправлен'}}]})
    assert r['r'] == [{'key': 'A-1', 'status': 'Исправлен'}]
    assert r['calls'][0]['url'] == 'https://sfera.test/api/tasks?q=email%20%2B' and r['calls'][0]['method'] == 'GET'


def test_not_configured():
    r = run('repo.tree', {}, {})
    assert not r['ok'] and r['code'] == 'not_configured' and 'API Сферы для QA pro' in r['error'] and not r['calls']


def test_no_login():
    r = run('tasks.get', {'key': 'A-1'}, {'tasks.get': {'path': '/t/{key}'}}, token=None)
    assert not r['ok'] and r['code'] == 'auth'


def test_http_error():
    r = run('tasks.get', {'key': 'A-1'}, {'tasks.get': {'path': '/t/{key}'}}, {'message': 'нет прав'}, status=403)
    assert not r['ok'] and r['code'] == 'http_403' and 'нет прав' in r['error']


def test_unknown_op():
    r = run('admin.drop', {}, {'admin.drop': {'path': '/x'}})
    assert not r['ok'] and r['code'] == 'bad_op'
