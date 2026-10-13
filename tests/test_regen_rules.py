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
