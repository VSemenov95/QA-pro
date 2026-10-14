"""Схема ответа на ключе Claude: генерация отдаёт кейсы через инструмент со схемой, приоритет и наборы ограничены enum."""
import pytest

from tests.support.api_gateway import Gateway

PRIOS = ['P4_CRITICAL', 'P3_HIGH', 'P2_MEDIUM', 'P1_LOW']
CLAUDE = {'id': 'p-claude', 'preset': 'claude', 'kind': 'anthropic', 'name': 'Claude', 'baseUrl': 'https://api.anthropic.com',
          'apiKey': 'sk-ant-x', 'auth': 'Bearer', 'model': 'claude-opus-5-5', 'headers': '', 'tools': True, 'noTemp': False}


@pytest.fixture
def key_app(make_app):
    app = make_app(kind='standalone', local_storage={'qapro.conns': [CLAUDE]}, settings={'genAI': 'conn:p-claude'})
    app.gw = Gateway(app)
    return app


def schema_calls(app):
    return [r for r in app.gw.to('api.anthropic.com') if r.body.get('tool_choice')]


def test_generation_asks_for_result_through_schema_tool(key_app):
    key_app.add_sample()
    key_app.generate()
    calls = schema_calls(key_app)
    assert calls, 'генерация должна идти с принудительным инструментом'
    tool = calls[0].body['tools'][0]
    assert calls[0].body['tool_choice'] == {'type': 'tool', 'name': tool['name']}
    assert 'temperature' not in calls[0].body


def test_schema_limits_priority_and_suites(key_app):
    key_app.add_sample()
    key_app.generate()
    schema = schema_calls(key_app)[0].body['tools'][0]['input_schema']
    item = schema['properties']['cases']['items']['properties']
    assert item['testCase']['properties']['priority']['enum'] == PRIOS
    assert item['suites']['items']['enum'] == ['smoke', 'regression']
    assert schema['required'] == ['cases']


def test_cases_come_back_from_schema_result(key_app):
    key_app.add_sample()
    key_app.generate()
    assert key_app.state('S.run.cases.length') > 0
    assert not key_app.state("S.run.failed.length")
