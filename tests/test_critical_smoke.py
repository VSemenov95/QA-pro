"""P4_CRITICAL всегда в смоук и в регресс — в коде, при каждом сохранении приоритета."""
import re

import pytest

from tests.support import seed


def test_helper_adds_both_suites_for_critical_only(app):
    assert app.call("a.withCritical('P4_CRITICAL', [])") == ['smoke', 'regression']
    assert app.call("a.withCritical('Critical', ['regression'])") == ['smoke', 'regression']
    assert app.call("a.withCritical('P3_HIGH', ['regression'])") == ['regression']
    assert app.call("a.withCritical('P1_LOW', [])") == []


def test_generated_critical_cases_get_smoke_even_if_model_says_regression(app):
    def critical_cases(call):
        ids = re.findall(r'### ([A-Z]+-\d+)\.', call.prompt)
        return {'cases': [{'planItem': pid, 'requirementIds': [], 'suites': ['regression'],
                           'testCase': {'title': f'[BE] Критичный кейс {pid}', 'id': '', 'priority': 'P4_CRITICAL', 'preconditions': ['—'],
                                        'steps': [{'step': 1, 'action': 'a', 'expected': 'b'}]}} for pid in ids]}
    app.model.on('promptGenerate', critical_cases)
    app.add_sample()
    app.generate()
    suites = app.state('S.run.cases.map((c) => c.suites)')
    assert suites and all(s == ['smoke', 'regression'] for s in suites), suites


def test_edited_priority_to_critical_adds_smoke(app):
    app.add_sample()
    app.generate()
    app.call("(() => { const c = S.run.cases[0]; c.suites = ['regression']; c.testCase.priority = 'P4_CRITICAL'; c.suites = a.withCritical(c.testCase.priority, c.suites); })()")
    assert app.state('S.run.cases[0].suites') == ['smoke', 'regression']
