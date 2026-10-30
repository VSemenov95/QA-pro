"""Приоритет — только четыре значения: P1_LOW, P2_MEDIUM, P3_HIGH, P4_CRITICAL. Старые записи приводятся к ним."""
import pytest

ALLOWED = {'P1_LOW', 'P2_MEDIUM', 'P3_HIGH', 'P4_CRITICAL'}


@pytest.mark.parametrize('raw,expected', [
    ('P1_LOW', 'P1_LOW'), ('P2_MEDIUM', 'P2_MEDIUM'), ('P3_HIGH', 'P3_HIGH'), ('P4_CRITICAL', 'P4_CRITICAL'),
    ('High', 'P3_HIGH'), ('Medium', 'P2_MEDIUM'), ('Low', 'P1_LOW'), ('high', 'P3_HIGH'), ('low', 'P1_LOW'),
    ('Critical', 'P4_CRITICAL'), ('высокий', 'P3_HIGH'), ('низкий', 'P1_LOW'), ('критический', 'P4_CRITICAL'),
    ('', 'P2_MEDIUM'), (None, 'P2_MEDIUM'), ('что-то другое', 'P2_MEDIUM'),
])
def test_normalizes_to_one_of_four(app, raw, expected):
    assert app.call('a.normPrio(arg)', raw) == expected


def test_only_four_values_are_in_the_list(app):
    assert app.call('a.PRIOS') == ['P4_CRITICAL', 'P3_HIGH', 'P2_MEDIUM', 'P1_LOW']


def test_russian_labels(app):
    assert app.call("[a.prioRu('P4_CRITICAL'), a.prioRu('P1_LOW')]") == ['Критический', 'Низкий']


def test_rule_is_in_generation_prompt(app):
    app.add_sample()
    app.generate()
    p = app.model.prompts_of('promptGenerate')[0]
    assert 'Приоритет — только одно из четырёх значений' in p and 'P4_CRITICAL' in p


def test_generated_cases_have_only_allowed_priorities(app):
    """Мок-модель отвечает «High» — приложение приводит значение к P3_HIGH при сохранении."""
    app.add_sample()
    app.generate()
    prios = app.state("S.run.cases.map((c) => c.testCase.priority)")
    assert prios and set(prios) <= ALLOWED, prios


def test_saved_template_with_old_priority_is_sent_as_code(app):
    """Пример шаблона, сохранённый раньше (с «Medium»), в запросах уходит с P2_MEDIUM."""
    app.call("S.cfg.tpl.ui = { ...S.cfg.tpl.ui, example: JSON.stringify({ title: 'x', priority: 'Medium', steps: [] }) }")
    assert app.state("a.tplInfo('ui').structure.priority") == 'P2_MEDIUM'
    app.add_sample()
    app.generate()
    p = app.model.prompts_of('promptGenerate')[0]
    assert '"priority": "Medium"' not in p and '"priority":"Medium"' not in p


def test_saved_template_rules_with_old_priority_words_are_sent_as_codes(app):
    """Правила оформления, сохранённые раньше, тоже уходят в запросы с четырьмя значениями приоритета."""
    app.call("S.cfg.tpl.ui = { ...S.cfg.tpl.ui, rules: '- priority: High — основной путь, Medium — валидации, Low — косметика' }")
    text = app.call("a.templateBlock('ui')")
    assert 'priority: P3_HIGH — основной путь, P2_MEDIUM — валидации, P1_LOW — косметика' in text
    assert 'High —' not in text and 'Medium —' not in text and 'Low —' not in text


def test_critical_checks_are_smoke_in_suites_rule(app):
    """Правило наборов: проверки с P4_CRITICAL входят в смоук и регресс."""
    app.add_sample()
    app.generate()
    p = app.model.prompts_of('promptGenerate')[0]
    assert 'Проверки с приоритетом P4_CRITICAL всегда входят в смоук и в регресс.' in p
