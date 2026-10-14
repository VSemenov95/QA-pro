"""Строгий режим правил: при ревью нарушения правил исправляются запросом к модели; без режима — замечаниями."""
import re

import pytest

from tests.support.model import case_body

SERVICE_PRE = 'Сервис оплаты запущен'


def fix_first_case(call):
    """Модель исправляет кейс, который ей передали (первый ID в запросе)."""
    dispid = re.search(r'### ([A-Z]+-\d+)', call.prompt).group(1)
    return {'cases': [{'caseId': dispid, 'testCase': case_body('Без нарушений')}]}


@pytest.fixture
def violating(app):
    """Сгенерированный набор, в первом кейсе — нарушение правила (сервис в предусловиях)."""
    app.add_sample()
    app.generate()
    return app.call(f"(() => {{ const c = S.run.cases[0]; c.testCase.preconditions.push('{SERVICE_PRE}'); return c.dispId; }})()")


def review(app):
    app.page.click('#btn-review')
    app.wait_idle()


def rule_findings(app):
    return app.state("S.run.findings.filter((f) => f.category === 'Правило' && f.status === 'open').length")


def test_strict_mode_repairs_violation_with_model(app, violating):
    app.model.on('promptReviseBatch', fix_first_case)
    app.call('(() => { S.settings.strictRules = true; return true; })()')
    review(app)
    assert app.model.prompts_of('promptReviseBatch'), 'строгий режим должен отправить кейс на исправление'
    pre = app.state(f"S.run.cases.find((c) => c.dispId === '{violating}').testCase.preconditions")
    assert SERVICE_PRE not in pre
    assert rule_findings(app) == 0
    assert 'После исправления нарушений правил не осталось' in ' '.join(app.state("S.run.steps.review.log.map((l) => l.text)"))


def test_without_strict_mode_violation_becomes_finding(app, violating):
    app.model.on('promptReviseBatch', fix_first_case)
    review(app)
    assert not app.model.prompts_of('promptReviseBatch'), 'без строгого режима модель на исправление не зовут'
    assert rule_findings(app) >= 1
