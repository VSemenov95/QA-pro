"""«Перегенерировать по правилам» учитывает все правила из папки rules/."""
import glob
import os

import pytest

RULES = sorted(glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rules', '*.md')))


@pytest.fixture
def regenerated(app):
    app.add_sample()
    app.generate()
    app.model.reset()
    app.page.click('#btn-regen')
    app.page.wait_for_timeout(300)
    app.page.click('#btn-regen')
    app.wait_idle()
    return app


def test_regeneration_asks_the_model_for_cases(regenerated):
    assert regenerated.model.prompts_of('promptGenerate'), 'после перегенерации нет запроса на кейсы'


@pytest.mark.parametrize('path', RULES, ids=[os.path.basename(p) for p in RULES])
def test_each_rule_file_reaches_regeneration_prompt(regenerated, path):
    text = open(path, encoding='utf-8').read().strip()
    head = ' '.join(text.split())[:60]
    prompts = regenerated.model.prompts_of('promptGenerate')
    assert prompts and any(head in ' '.join(p.split()) for p in prompts), head


def test_regeneration_rebuilds_checklist_with_agent_rules(app):
    """Перегенерация по правилам касается и чек-листа: он пересоздаётся, и правила раздела попадают в запрос."""
    app.page.fill('#cfg-rules', 'ПРАВИЛО-РАЗДЕЛА-XYZ: модуль оплаты не тестируем')
    app.page.dispatch_event('#cfg-rules', 'input')
    app.add_sample()
    app.generate()
    app.model.reset()
    app.page.click('#btn-regen')
    app.page.wait_for_timeout(300)
    app.page.click('#btn-regen')
    app.wait_idle()
    assert any('ПРАВИЛО-РАЗДЕЛА-XYZ' in p for p in app.model.prompts_of('promptChecklist'))
    ids = app.state('S.run.checklist.groups.flatMap((g) => g.items.map((i) => i.id))')
    assert ids and ids[0] == 'CL-001', ids


def test_regeneration_coverage_audit_gets_rules(app):
    """Сверка покрытия при перегенерации видит правила команды и правила из папки rules/."""
    app.page.fill('#cfg-rules', 'ПРАВИЛО-РАЗДЕЛА-XYZ: модуль оплаты не тестируем')
    app.page.dispatch_event('#cfg-rules', 'input')
    app.add_sample()
    app.generate()
    app.model.reset()
    app.page.click('#btn-regen')
    app.page.wait_for_timeout(300)
    app.page.click('#btn-regen')
    app.wait_idle()
    audits = app.model.prompts_of('promptCoverageAudit')
    assert audits, 'после перегенерации нет сверки покрытия'
    assert any('ПРАВИЛО-РАЗДЕЛА-XYZ' in p for p in audits)
    for path in RULES:
        head = ' '.join(open(path, encoding='utf-8').read().split())[:60]
        assert any(head in ' '.join(p.split()) for p in audits), os.path.basename(path)


def test_regeneration_uses_agent_rules_section(app):
    """Текст из раздела «Правила для агента» попадает в перегенерацию (и в план, и в кейсы)."""
    app.page.fill('#cfg-rules', 'ПРАВИЛО-РАЗДЕЛА-XYZ: модуль оплаты не тестируем')
    app.page.dispatch_event('#cfg-rules', 'input')
    app.add_sample()
    app.generate()
    app.model.reset()
    app.page.click('#btn-regen')
    app.page.wait_for_timeout(300)
    app.page.click('#btn-regen')
    app.wait_idle()
    assert any('ПРАВИЛО-РАЗДЕЛА-XYZ' in p for p in app.model.prompts_of('promptGenerate'))
    assert any('ПРАВИЛО-РАЗДЕЛА-XYZ' in p for p in app.model.prompts_of('promptPlan'))
