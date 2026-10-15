"""Покрыть требование тремя вариантами: кейсы сразу в черновике; требование можно отредактировать."""
import re

import pytest

from tests.support.model import case_body

CHECKS = [
    {'check': 'Основной сценарий: письмо со ссылкой отправлено', 'kind': 'positive', 'type': 'ui'},
    {'check': 'Второй позитивный: повторная отправка доступна', 'kind': 'positive', 'type': 'ui'},
    {'check': 'Пустой email — ошибка «Введите адрес»', 'kind': 'negative', 'type': 'ui'},
    {'check': 'Email из 254 символов принимается', 'kind': 'boundary', 'type': 'ui'},
]


def one_case_per_check(call):
    """Мок модели: по одному кейсу на каждую проверку пункта плана."""
    out = []
    for block in re.split(r'(?=### [A-Z]+-\d+\.)', call.prompt):
        m = re.match(r'### ([A-Z]+-\d+)\.', block)
        if not m:
            continue
        for k, _ in enumerate(re.findall(r'^\d+\. ', block, re.M)):
            out.append({'planItem': m.group(1), 'requirementIds': [], 'suites': ['regression'], 'testCase': case_body(f'Кейс {m.group(1)}-{k + 1}')})
    return {'cases': out}


def cover_cases(app):
    return app.state("S.run.cases.filter((c) => c.planItem.startsWith('V-')).length")


@pytest.fixture
def run(app):
    app.model.on('promptCoverRequirement', lambda call: {'checks': CHECKS})
    app.model.on('promptGenerate', one_case_per_check)
    app.add_sample()
    app.generate()
    app.tab('reqs')
    return app


def req_id(app):
    return app.state('S.run.requirements[0].id')


def open_req(app):
    """Открывает карточку требования, если она закрыта (повторный клик по строке её закрывает)."""
    if not app.page.is_visible(f'[data-act=cover-req][data-id="{req_id(app)}"]'):
        app.page.click(f'[data-act=toggle-req][data-id="{req_id(app)}"]')


def cover(app, variant):
    before = cover_cases(app)
    open_req(app)
    app.page.click(f'[data-act=cover-req][data-id="{req_id(app)}"][data-variant="{variant}"]')
    app.wait_idle()
    return cover_cases(app) - before


def test_requirement_offers_three_variants_and_edit(run):
    open_req(run)
    for label in ['Один тест (happy path)', 'Только позитивные проверки', 'Полное покрытие']:
        assert run.page.is_visible(f'button:has-text("{label}")'), label
    assert run.page.is_visible('button:has-text("Редактировать требование")')


def test_one_test_variant_adds_one_case_to_draft(run):
    assert cover(run, 'one') == 1
    assert run.state('S.run.stage') == 'draft'
    assert run.state(f"S.run.cases.filter((c) => c.planItem.startsWith('V-') && c.requirementIds.includes('{req_id(run)}')).length") == 1


def test_positive_variant_keeps_only_positive_checks(run):
    assert cover(run, 'positive') == 2


def test_full_variant_adds_every_check(run):
    assert cover(run, 'full') == 4


def test_extra_cases_from_model_are_trimmed(run):
    def three_per_check(call):
        base = one_case_per_check(call)['cases']
        return {'cases': [dict(c, testCase=case_body(f'Кейс {k}')) for c in base for k in range(3)]}
    run.model.on('promptGenerate', three_per_check)
    assert cover(run, 'one') == 1


def test_same_requirement_can_be_covered_again(run):
    assert cover(run, 'one') == 1
    assert cover(run, 'one') == 1


def test_cover_is_disabled_once_run_is_added_to_project(run):
    run.call("(() => { S.run.stage = 'added'; S.run.addedAt = Date.now(); return true; })()")
    run.tab('agent')
    run.tab('reqs')
    open_req(run)
    assert run.page.is_disabled(f'[data-act=cover-req][data-id="{req_id(run)}"][data-variant="one"]')


def test_edit_requirement_saves_changes(run):
    rid = req_id(run)
    open_req(run)
    run.page.click(f'[data-act=req-edit][data-id="{rid}"]')
    run.page.fill('#req-ed-title', 'Восстановление пароля по email')
    run.page.fill('#req-ed-crit', 'Письмо приходит в течение минуты\n\nСсылка действует 24 часа ')
    run.page.click(f'[data-act=req-save][data-id="{rid}"]')
    assert run.state(f"S.run.reqById['{rid}'].title") == 'Восстановление пароля по email'
    assert run.state(f"S.run.reqById['{rid}'].criteria") == ['Письмо приходит в течение минуты', 'Ссылка действует 24 часа']
    assert 'Восстановление пароля по email' in run.text('.req-row')


def test_cancel_edit_keeps_requirement(run):
    rid = req_id(run)
    before = run.state(f"S.run.reqById['{rid}'].title")
    open_req(run)
    run.page.click(f'[data-act=req-edit][data-id="{rid}"]')
    run.page.fill('#req-ed-title', 'Другое название')
    run.page.click('[data-act=req-cancel]')
    assert run.state(f"S.run.reqById['{rid}'].title") == before


def test_empty_title_is_rejected(run):
    rid = req_id(run)
    before = run.state(f"S.run.reqById['{rid}'].title")
    open_req(run)
    run.page.click(f'[data-act=req-edit][data-id="{rid}"]')
    run.page.fill('#req-ed-title', '   ')
    run.page.click(f'[data-act=req-save][data-id="{rid}"]')
    assert run.state(f"S.run.reqById['{rid}'].title") == before
    assert run.page.is_visible('#req-ed-title')


def test_cover_uses_edited_requirement(run):
    rid = req_id(run)
    open_req(run)
    run.page.click(f'[data-act=req-edit][data-id="{rid}"]')
    run.page.fill('#req-ed-title', 'Восстановление пароля по email')
    run.page.click(f'[data-act=req-save][data-id="{rid}"]')
    cover(run, 'one')
    assert 'Восстановление пароля по email' in run.model.prompts_of('promptCoverRequirement')[-1]
