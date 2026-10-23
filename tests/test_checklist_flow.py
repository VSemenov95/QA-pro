"""Чек-лист: название и ожидаемый результат, лимит проверок, тест-кейсы по чек-листу, выгрузка таблицей (.pdf, .xlsx, .md)."""
import re

import pytest

from tests.support.model import generate_per_check
from tests.test_generation import set_outputs

def item(check, kind, prio, typ='ui', req='R-001', expected=None):
    return {'check': check, 'expected': expected or f'Результат: {check}', 'kind': kind, 'type': typ, 'priority': prio, 'suites': ['regression'], 'requirementIds': [req]}


MIXED = {'groups': [
    {'title': 'Форма', 'items': [
        item('Низкий позитив', 'positive', 'low'),
        item('Критичный негатив', 'negative', 'critical'),
        item('Высокий позитив', 'positive', 'high')]},
    {'title': 'API', 'items': [
        item('Критичный позитив', 'positive', 'critical', 'api', 'R-002'),
        item('Средний позитив', 'positive', 'medium', 'api', 'R-002'),
        item('Высокий негатив', 'negative', 'high', 'api', 'R-002')]},
]}


def set_target(app, n):
    app.page.fill('#target-n', str(n))
    app.page.press('#target-n', 'Tab')
    app.page.wait_for_timeout(150)


@pytest.fixture
def both(app):
    """Пример ТЗ, выбраны и чек-лист, и тест-кейсы; модель пишет кейс на каждый пункт."""
    app.model.on('promptGenerate', generate_per_check)
    app.add_sample()
    app.generate()
    assert app.state('S.run.status') == 'done', app.state('S.run.error')
    return app


# ---------- пункт: название, ожидаемый результат, позитивная/негативная ----------
def test_items_have_name_expected_result_and_kind(both):
    its = both.state('S.run.checklist.groups.flatMap((g) => g.items.map((i) => [i.check, i.expected, i.kind]))')
    assert its[0] == ['Отображение ссылки «Забыли пароль?»', 'Ссылка видна под полем пароля', 'positive']
    assert its[1][2] == 'negative'
    prompt = both.model.calls_of('promptChecklist')[0].prompt
    assert 'expected' in prompt and 'kind' in prompt and 'Каждое требование должно попасть' in prompt
    both.tab('checklist')
    assert 'Ожидаемый результат: Ссылка видна под полем пароля' in both.text('#tab-body') and 'Негативная' in both.text('#tab-body')


def test_edit_saves_expected_result_and_kind(both):
    both.tab('checklist')
    both.page.click('[data-act=cl-edit][data-id=CL-001]')
    both.page.fill('#cl-exp', 'Ссылка ведёт на /restore')
    both.page.select_option('#cl-kind', 'negative')
    both.page.click('[data-act=cl-save]')
    assert both.state('S.run.checklist.groups[0].items[0].expected') == 'Ссылка ведёт на /restore'
    assert both.state('S.run.checklist.groups[0].items[0].kind') == 'negative'


# ---------- лимит проверок ----------
def test_limit_takes_the_most_important_positive_checks_first(app):
    app.model.on('promptChecklist', lambda c: MIXED)
    app.add_sample()
    set_outputs(app, cases=False)
    set_target(app, 3)
    app.generate()
    got = app.state('S.run.checklist.groups.flatMap((g) => g.items.map((i) => i.check))')
    assert sorted(got) == sorted(['Критичный позитив', 'Высокий позитив', 'Средний позитив'])
    prompt = app.model.calls_of('promptChecklist')[0].prompt
    assert 'Не больше 3 пунктов' in prompt and 'позитивные' in prompt
    log = app.state('S.run.steps.checklist.log.map((l) => l.text).join("\\n")')
    assert 'ограничен числом проверок: 3 (было 6)' in log


def test_negative_checks_follow_positive_by_priority(app):
    app.model.on('promptChecklist', lambda c: MIXED)
    app.add_sample()
    set_outputs(app, cases=False)
    set_target(app, 5)
    app.generate()
    got = app.state('S.run.checklist.groups.flatMap((g) => g.items.map((i) => i.check))')
    # 4 позитивных + самый приоритетный негатив; внутри группы — по важности
    assert sorted(got) == sorted(['Критичный позитив', 'Высокий позитив', 'Средний позитив', 'Низкий позитив', 'Критичный негатив'])
    assert app.state('S.run.checklist.groups[0].items.map((i) => i.check)') == ['Высокий позитив', 'Низкий позитив', 'Критичный негатив']


def test_without_limit_nothing_is_cut(app):
    app.model.on('promptChecklist', lambda c: MIXED)
    app.add_sample()
    set_outputs(app, cases=False)
    app.generate()
    assert app.state('S.run.checklist.groups.flatMap((g) => g.items).length') == 6
    assert 'Не больше' not in app.model.calls_of('promptChecklist')[0].prompt


# ---------- тест-кейсы по чек-листу ----------
def test_cases_are_written_from_the_checklist(both):
    kinds = {c.kind for c in both.model.calls}
    assert 'promptPlan' not in kinds   # плана по требованиям нет — план из чек-листа
    gen = '\n'.join(c.prompt for c in both.model.calls_of('promptGenerate'))
    assert 'CL-001 · Отображение ссылки «Забыли пароль?». Ожидаемый результат: Ссылка видна под полем пароля' in gen
    assert 'checklistId' in gen
    linked = both.state('S.run.cases.filter((c) => c.checklistId).map((c) => [c.checklistId, c.type, c.testCase.priority])')
    assert sorted(linked) == [['CL-001', 'ui', 'P3_HIGH'], ['CL-002', 'ui', 'P2_MEDIUM'], ['CL-003', 'api', 'P3_HIGH'], ['CL-004', 'api', 'P2_MEDIUM']]
    log = both.state('S.run.steps.plan.log.map((l) => l.text).join("\\n")')
    assert 'План — по чек-листу: 4 пункта → 4 тест-кейса' in log


def test_case_opens_its_checklist_item(both):
    both.tab('cases')
    both.page.click('[data-act=go-cl][data-id=CL-003]')
    both.page.wait_for_timeout(200)
    assert both.state('S.tab') == 'checklist'


def test_without_checklist_cases_follow_the_plan(app):
    app.add_sample()
    set_outputs(app, checklist=False)
    app.generate()
    assert app.model.calls_of('promptPlan') and app.state('S.run.cases.some((c) => c.checklistId)') is False
    assert 'CL-' not in '\n'.join(c.prompt for c in app.model.calls_of('promptGenerate'))


def test_limit_applies_to_checklist_and_its_cases(app):
    app.model.on('promptChecklist', lambda c: MIXED)
    app.model.on('promptGenerate', generate_per_check)
    app.add_sample()
    set_target(app, 3)
    app.generate()
    assert app.state('S.run.checklist.groups.flatMap((g) => g.items).length') == 3
    cl = app.state('S.run.cases.map((c) => c.checklistId)')
    assert len(cl) == 3 and sorted(cl) == sorted(app.state('S.run.checklist.groups.flatMap((g) => g.items.map((i) => i.id))'))


def test_empty_checklist_falls_back_to_the_plan(app):
    app.model.on('promptChecklist', lambda c: {'groups': []})
    app.add_sample()
    app.generate()
    assert app.model.calls_of('promptPlan')
    assert 'Чек-лист пуст' in app.state('S.run.steps.plan.log.map((l) => l.text).join("\\n")')


# ---------- выгрузка таблицей ----------
ROWS = [['1', 'Отображение ссылки «Забыли пароль?»', 'высокий', 'FE', 'Ссылка видна под полем пароля'],
        ['2', 'Email без @ в форме восстановления', 'средний', 'FE', 'Сообщение «Введите корректный email»'],
        ['3', 'Запрос сброса с корректным email', 'высокий', 'BE', 'POST /api/v1/password-reset — 202'],
        ['4', 'Четвёртый запрос за 15 минут', 'средний', 'BE', '429 RATE_LIMIT']]


def test_export_rows_one_check_per_row(both):
    assert both.state('a.checklistRows(S.run)') == ROWS


def test_component_e2e(both):
    both.call('(S.run.checklist.groups[0].items[0].type = "e2e", true)')
    assert both.state('a.checklistRows(S.run)[0][3]') == 'E2E'


def test_markdown_is_a_table(both):
    md = both.state('a.checklistMarkdown(S.run)')
    assert '| № | Название | Приоритет | Компонент | Ожидаемый результат |' in md
    assert '| 1 | Отображение ссылки «Забыли пароль?» | высокий | FE | Ссылка видна под полем пароля |' in md


def test_pdf_download_is_a_table_with_cyrillic(both):
    both.tab('checklist')
    both.page.click('[data-act=cl-dl-pdf]')
    both.page.wait_for_function('() => (window.__downloads || []).some((d) => d.filename.endsWith(".pdf"))', timeout=30000)
    name = both.page.evaluate('() => window.__downloads.find((d) => d.filename.endsWith(".pdf")).filename')
    assert re.fullmatch(r'checklist_\d{4}-\d{2}-\d{2}\.pdf', name)
    text = both.page.evaluate('async () => (await window.__qa.parsePdf(await window.__dlBlob.arrayBuffer())).text')
    for h in ('№', 'Название', 'Приоритет', 'Компонент', 'Ожидаемый результат'):
        assert h in text
    for row in ROWS:
        assert row[1].split()[0] in text and row[3] in text
    assert 'высокий' in text and 'POST /api/v1/password-reset' in text


def test_xlsx_download_is_a_table(both):
    both.tab('checklist')
    both.page.click('[data-act=cl-dl-xlsx]')
    both.page.wait_for_function('() => (window.__downloads || []).some((d) => d.filename.endsWith(".xlsx"))', timeout=30000)
    sheets = both.page.evaluate('async () => await window.__qa.parseSheet(await window.__dlBlob.arrayBuffer())')
    text = str(sheets)
    assert '| № | Название | Приоритет | Компонент | Ожидаемый результат |' in text
    assert '| 1 | Отображение ссылки «Забыли пароль?» | высокий | FE | Ссылка видна под полем пароля |' in text


def test_json_keeps_new_fields(both):
    j = both.state('a.checklistJSON(S.run).groups[0].items[0]')
    assert j['expected'] == 'Ссылка видна под полем пароля' and j['kind'] == 'positive' and j['component'] == 'FE'
