"""Статус выполнения пункта чек-листа и правила формирования чек-листа в промпте."""
import pytest


@pytest.fixture
def checklist(app):
    app.add_sample()
    app.generate()
    app.tab('checklist')
    return app


def first_id(app):
    return app.state("S.run.checklist.groups.find((g) => g.items.length).items[0].id")


def test_each_item_offers_four_statuses(checklist):
    sel = f'select.cl-status[data-id="{first_id(checklist)}"]'
    options = checklist.page.eval_on_selector_all(f'{sel} option', 'els => els.map((e) => e.textContent)')
    assert options == ['Не проставлен', 'Passed (пройдено)', 'Failed (ошибка)', 'Blocked (заблокировано)', 'Skipped (пропущено)']


def test_chosen_status_is_saved_on_the_item(checklist):
    item_id = first_id(checklist)
    checklist.page.select_option(f'select.cl-status[data-id="{item_id}"]', 'failed')
    assert checklist.state(f"S.run.checklist.groups.flatMap((g) => g.items).find((i) => i.id === '{item_id}').status") == 'failed'


def test_status_can_be_cleared(checklist):
    item_id = first_id(checklist)
    checklist.page.select_option(f'select.cl-status[data-id="{item_id}"]', 'passed')
    checklist.page.select_option(f'select.cl-status[data-id="{item_id}"]', '')
    assert checklist.state(f"S.run.checklist.groups.flatMap((g) => g.items).find((i) => i.id === '{item_id}').status") is None


def test_checklist_prompt_carries_formation_rules(checklist):
    p = checklist.model.prompts_of('promptChecklist')[0]
    for rule in ['1 пункт = 1 действие', 'Опора на требования', 'Единообразие формулировок', 'Группируй пункты по блокам', 'от 5 до 30', 'Тестовые данные']:
        assert rule in p, rule
