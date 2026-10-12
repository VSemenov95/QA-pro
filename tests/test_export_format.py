"""Настройки под шестерёнкой (несохранённые изменения) и формат экспорта: описание словами → спецификация → файл, пересборка."""
import json
import re

import pytest

from tests.support.model import ModelError

FMT = 'CSV для Test IT: шаг на строку, разделитель ;'
HEADER = 'ID;Название;Предусловия;Шаг;Ожидаемый результат;Приоритет;Теги'
SPEC = {'fileType': 'csv', 'filename': 'testit-import', 'mode': 'map', 'rowMode': 'step', 'delimiter': ';', 'notes': 'CSV для Test IT, шаг на строку.',
        'cols': [{'header': 'ID', 'value': '{{id}}', 'firstOnly': True}, {'header': 'Название', 'value': '{{title}}', 'firstOnly': True},
                 {'header': 'Предусловия', 'value': '{{preconditions|; }}', 'firstOnly': True}, {'header': 'Шаг', 'value': '{{step.n}}. {{step.action}}'},
                 {'header': 'Ожидаемый результат', 'value': '{{step.expected}}'}, {'header': 'Приоритет', 'value': '{{priority=high:Высокий,medium:Средний,low:Низкий}}', 'firstOnly': True},
                 {'header': 'Теги', 'value': '{{suites|, }}', 'firstOnly': True}], 'itemRules': 'по шаблону'}
AI_SPEC = {'fileType': 'csv', 'filename': 'ai-import', 'mode': 'ai', 'delimiter': ';', 'columns': ['Название', 'Шаги'], 'itemRules': 'Название — как есть, шаги одной ячейкой'}


def two_steps(call):
    """Кейсы с двумя шагами: в строке на шаг видно, какие поля заполняются только в первой строке."""
    out = []
    for pid in re.findall(r'### ([A-Z]+-\d+)\.', call.prompt):
        out.append({'planItem': pid, 'requirementIds': [], 'suites': ['smoke', 'regression'] if not out else ['regression'], 'testCase': {
            'title': f'Проверка {pid}', 'id': '', 'priority': 'High', 'preconditions': ['Пользователь зарегистрирован'], 'expectedResult': 'ok', 'tags': ['t'],
            'steps': [{'step': 1, 'action': 'Открыть /login', 'expected': 'Открыта страница'}, {'step': 2, 'action': 'Нажать «Забыли пароль?»', 'expected': 'Открыт экран'}]}})
    return {'cases': out}


def set_format(app, text):
    app.open_settings('export')
    app.page.fill('#cfg-export', text)
    app.close_settings()


@pytest.fixture
def run(app):
    """Готовый запуск с четырьмя кейсами (у каждого два шага)."""
    app.model.on('promptExportSpec', SPEC).on('promptGenerate', two_steps)
    app.generate()
    return app


def build(app):
    app.tab('export')
    app.page.click('[data-act=run-export]')
    app.page.wait_for_function("() => window.__qa.S.exp && window.__qa.S.exp.status !== 'running'")


def output(app):
    return app.page.eval_on_selector('.json-pre', 'e => e.textContent').replace('\r\n', '\n')


def calls(app, *kinds):
    return len(app.model.calls_of(*kinds))


def edit_first_case(app):
    app.tab('cases')
    app.page.click('.case-h >> nth=0')
    app.page.click('[data-act=case-suite][data-s=smoke]')
    app.page.wait_for_timeout(300)
    app.tab('export')


# ---------- шестерёнка: несохранённые настройки ----------
def gear_dirty(app):
    return app.state("document.querySelector('#btn-settings').classList.contains('dirty')")


def test_gear_is_clean_by_default(app):
    assert gear_dirty(app) is False


def test_unsaved_export_format_marks_the_gear(app):
    set_format(app, FMT)
    assert gear_dirty(app) is True


def test_dialog_tab_and_footer_show_unsaved_state(app):
    app.open_settings('export')
    app.page.fill('#cfg-export', FMT)
    assert app.count('#settab-export .dot-d') == 1
    foot = app.text('#cfg-foot')
    assert 'Формат экспорта:' in foot and 'Изменено в этом окне' in foot
    assert app.count('#cfg-foot [data-cfg=save]') == 1 and app.count('#cfg-foot [data-cfg=revert]') == 1


def test_mark_stays_after_the_dialog_is_closed_and_reopened(app):
    set_format(app, FMT)
    app.open_settings('export')
    assert app.page.input_value('#cfg-export') == FMT and gear_dirty(app)


def test_saving_for_the_team_clears_the_mark(app):
    app.open_settings('export')
    app.page.fill('#cfg-export', FMT)
    app.page.click('#cfg-foot [data-cfg=save]')
    app.page.wait_for_function("() => !document.querySelector('#btn-settings').classList.contains('dirty')")
    assert app.db.get('config/export')['format'] == FMT
    assert 'Версия команды' in app.text('#cfg-foot') and app.count('#settab-export .dot-d') == 0


def test_revert_returns_the_default_and_clears_the_mark(app):
    app.open_settings('export')
    app.page.fill('#cfg-export', FMT)
    app.page.click('#cfg-foot [data-cfg=revert]')
    assert app.page.input_value('#cfg-export') == '' and not gear_dirty(app)


def test_revert_returns_the_team_version(app):
    app.db.store['config/export'] = {'format': 'Версия команды: JSON', 'updatedAt': 1700000000000, 'updatedBy': 'x'}
    app.reload()
    app.open_settings('export')
    app.page.fill('#cfg-export', FMT)
    app.page.click('#cfg-foot [data-cfg=revert]')
    assert app.page.input_value('#cfg-export') == 'Версия команды: JSON' and not gear_dirty(app)


def test_unsaved_format_survives_reload(app):
    set_format(app, FMT)
    app.page.wait_for_function("() => (localStorage.getItem('qapro.cfgDraft') || '').includes('export')")   # черновик записывается через 0,4 с после правки
    app.reload()
    assert gear_dirty(app) and app.state('S.cfg.exportFormat') == FMT


@pytest.mark.parametrize('tab,field,text', [('review', '#cfg-review', 'Каждый кейс проверяет одно требование'), ('tpl', '#cfg-tplrules', 'Шаги в повелительном наклонении')])
def test_review_rules_and_templates_mark_the_gear(app, tab, field, text):
    app.open_settings(tab)
    app.page.fill(field, text)
    assert gear_dirty(app) and app.count(f'#settab-{tab} .dot-d') == 1


def test_rules_in_the_left_column_have_their_own_mark(app):
    app.page.fill('#cfg-rules', 'Не пиши тесты на SQL')
    assert app.visible('#h-rules-dot') and not gear_dirty(app)


# ---------- формат экспорта ----------
def test_without_format_the_standard_json_is_offered(run):
    run.tab('export')
    assert 'Стандартный JSON' in run.text('#tab-body') and run.count('[data-act=cfg-export]') == 1
    data = json.loads(run.page.eval_on_selector('.json-pre', 'e => e.textContent'))
    assert set(data['testCases']) == {'api', 'ui', 'e2e'} and len(data['testCases']['api']) == 2


def test_standard_json_is_downloaded_under_a_dated_name(run):
    run.tab('export')
    run.page.click('[data-act=dl-out]')
    run.page.wait_for_function('() => (window.__downloads || []).length > 0')
    assert re.fullmatch(r'test-cases_\d{4}-\d\d-\d\d\.json', run.downloads()[-1]['filename'])


def test_export_tab_is_empty_before_generation(app):
    app.tab('export')
    assert 'Экспорт появится после генерации тест-кейсов' in app.text('#tab-body')


def test_format_card_shows_the_description_and_offers_to_build(run):
    set_format(run, FMT)
    run.tab('export')
    assert FMT in run.text('.exp-fmt') and run.count('[data-act=run-export]') == 1
    assert 'Агент один раз разберёт описание формата' in run.text('.exp-card .hint')


def test_build_asks_for_the_spec_once_and_assembles_without_the_model(run):
    set_format(run, FMT)
    build(run)
    assert calls(run, 'promptExportSpec') == 1 and calls(run, 'promptExportItems') == 0
    assert 'Файл собирается по шаблону полей, без модели' in run.text('.exp-card')


def test_spec_request_has_the_description_and_sample_cases(run):
    set_format(run, FMT)
    build(run)
    p = run.model.prompts_of('promptExportSpec')[0]
    assert FMT in p.split('## Описание формата от пользователя')[1].split('## Исходные данные')[0]
    sample = p.split('Два примера:')[1]
    assert '"id":"API-001"' in sample and '"id":"API-002"' in sample and 'API-002' in sample and 'UI-001' not in sample.split('Также доступны')[0]


def test_file_follows_the_field_template(run):
    set_format(run, FMT)
    build(run)
    lines = output(run).split('\n')
    assert lines[0] == HEADER and len(lines) == 1 + 4 * 2   # заголовок и по строке на шаг каждого из четырёх кейсов
    assert lines[1] == 'API-001;[BE] Проверка P-02;Пользователь зарегистрирован;1. Открыть /login;Открыта страница;Высокий;smoke, regression'


def test_case_level_columns_are_filled_only_in_the_first_row(run):
    set_format(run, FMT)
    build(run)
    assert output(run).split('\n')[2] == ';;;2. Нажать «Забыли пароль?»;Открыт экран;;'


def test_download_has_the_name_from_the_spec_and_a_bom(run):
    set_format(run, FMT)
    build(run)
    run.page.click('[data-act=dl-out]')
    run.page.wait_for_function('() => (window.__downloads || []).length > 0')
    d = run.downloads()[-1]
    assert d['filename'] == 'testit-import.csv' and d['text'].startswith('﻿' + HEADER + '\r\n')


def test_edited_case_marks_the_file_stale_and_rebuild_needs_no_model(run):
    set_format(run, FMT)
    build(run)
    before = len(run.model.calls)
    edit_first_case(run)
    assert 'Кейсы изменились после сборки — пересоберите файл.' in run.text('#tab-body')
    assert 'Формат собирается по шаблону — без запросов к модели.' in run.text('.exp-card')
    run.page.click('[data-act=run-export]')
    run.page.wait_for_function("() => !/Кейсы изменились/.test(document.querySelector('#tab-body').textContent)")
    assert len(run.model.calls) == before   # ни одного нового запроса к модели


def test_rebuild_from_scratch_asks_for_the_spec_again(run):
    set_format(run, FMT)
    build(run)
    run.page.click('[data-act=rebuild-export]')
    run.page.wait_for_function("() => window.__qa.S.exp && window.__qa.S.exp.status === 'done'")
    run.wait_idle()
    assert calls(run, 'promptExportSpec') == 2


def test_changing_the_description_requires_a_new_spec(run):
    set_format(run, FMT)
    build(run)
    set_format(run, FMT + ' Теги в одной колонке.')
    run.tab('export')
    assert run.count('[data-act=run-export]') == 1 and run.count('.json-pre') == 0   # прежнего файла для нового описания нет
    run.page.click('[data-act=run-export]')
    run.page.wait_for_function("() => window.__qa.S.exp && window.__qa.S.exp.status === 'done'")
    assert calls(run, 'promptExportSpec') == 2


def test_json_format_is_assembled_from_wrapper_and_item_template(run):
    run.model.on('promptExportSpec', {'fileType': 'json', 'filename': 'cases', 'mode': 'map', 'wrapper': {'generatedAt': '%%GENERATED_AT%%', 'api': '%%API%%', 'smoke': '%%SMOKE%%'},
                                      'item': {'key': '{{id}}', 'name': '{{title}}', 'steps': {'$each': 'steps', 'item': '{{action}}'}}})
    set_format(run, 'JSON: объект с массивами api и smoke')
    build(run)
    data = json.loads(output(run))
    assert [x['key'] for x in data['api']] == ['API-001', 'API-002']
    assert [x['key'] for x in data['smoke']] == ['API-001', 'UI-001', 'E2E-001']   # в смоуке только кейсы с отметкой «Смоук» (API-002 — только регресс)
    assert data['api'][0]['steps'] == ['Открыть /login', 'Нажать «Забыли пароль?»'] and re.fullmatch(r'\d{4}-\d\d-\d\dT.*', data['generatedAt'])


def test_text_format_is_assembled_from_item_template(run):
    run.model.on('promptExportSpec', {'fileType': 'md', 'filename': 'cases', 'mode': 'map', 'wrapper': '# Кейсы\n\n%%ALL%%\n', 'separator': '\n\n', 'itemText': '## {{id}} {{title}}\n{{#steps}}{{n}}. {{action}} → {{expected}}\n{{/steps}}'})
    set_format(run, 'Markdown со списком шагов')
    build(run)
    text = output(run)
    assert text.startswith('# Кейсы\n\n## API-001 [BE] Проверка P-02\n1. Открыть /login → Открыта страница\n2. Нажать «Забыли пароль?» → Открыт экран')
    assert text.count('## ') == 4


# ---------- формат, где текст кейсов переписывает модель ----------
def ai_items(call):
    ids = list(dict.fromkeys(re.findall(r'"id": "([A-Z0-9-]+)"', call.prompt)))
    return {'items': [{'caseId': i, 'rows': [[f'Кейс {i}', 'шаги…']]} for i in ids]}


@pytest.fixture
def ai_run(run):
    run.model.on('promptExportSpec', AI_SPEC).on('promptExportItems', ai_items)
    set_format(run, 'CSV: название и шаги одной ячейкой')
    return run


def test_ai_mode_converts_cases_in_batches(ai_run):
    build(ai_run)
    assert calls(ai_run, 'promptExportSpec') == 1 and calls(ai_run, 'promptExportItems') == 1   # четыре кейса — одна пачка (до 8)
    assert output(ai_run).split('\n') == ['Название;Шаги', 'Кейс API-001;шаги…', 'Кейс API-002;шаги…', 'Кейс UI-001;шаги…', 'Кейс E2E-001;шаги…']


def test_ai_request_lists_columns_and_rules(ai_run):
    build(ai_run)
    p = ai_run.model.prompts_of('promptExportItems')[0]
    assert 'Колонки: Название | Шаги' in p and 'Название — как есть, шаги одной ячейкой' in p and 'в каждой строке ровно 2 значений' in p


def test_only_changed_cases_are_converted_again(ai_run):
    build(ai_run)
    edit_first_case(ai_run)
    assert 'Нужно 1 запрос к модели' in ai_run.text('.exp-card')
    ai_run.page.click('[data-act=run-export]')
    ai_run.page.wait_for_function("() => window.__qa.S.exp.status === 'done' && !/Кейсы изменились/.test(document.querySelector('#tab-body').textContent)")
    assert calls(ai_run, 'promptExportItems') == 2
    assert set(re.findall(r'"id": "([A-Z0-9-]+)"', ai_run.model.prompts_of('promptExportItems')[1])) == {'API-001'} and calls(ai_run, 'promptExportSpec') == 1


def test_cases_the_model_skipped_are_reported_and_retried_alone(ai_run):
    ai_run.model.on('promptExportItems', lambda c: {'items': [{'caseId': 'API-001', 'rows': [['Кейс API-001', 'шаги…']]}]})
    build(ai_run)
    assert 'Не удалось преобразовать: API-002, UI-001, E2E-001.' in ai_run.text('#tab-body')
    ai_run.model.on('promptExportItems', ai_items)
    ai_run.page.click('[data-act=run-export]')
    ai_run.page.wait_for_function("() => window.__qa.S.exp.status === 'done' && !window.__qa.S.exp.error")
    last = ai_run.model.prompts_of('promptExportItems')[-1]
    assert sorted(set(re.findall(r'"id": "([A-Z0-9-]+)"', last))) == ['API-002', 'E2E-001', 'UI-001']   # API-001 уже готов, заново не просим
    assert len(output(ai_run).split('\n')) == 5


def test_rows_are_padded_to_the_column_count(ai_run):
    ai_run.model.on('promptExportItems', lambda c: {'items': [{'caseId': i, 'rows': [['Кейс ' + i]]} for i in dict.fromkeys(re.findall(r'"id": "([A-Z0-9-]+)"', c.prompt))]})
    build(ai_run)
    assert output(ai_run).split('\n')[1] == 'Кейс API-001;'


def test_spec_without_columns_is_an_error(run):
    run.model.on('promptExportSpec', {'fileType': 'csv', 'mode': 'ai', 'columns': []})
    set_format(run, 'CSV, колонки на ваше усмотрение')
    build(run)
    assert 'Модель не определила колонки файла. Уточните описание формата.' in run.text('#tab-body') and run.count('.json-pre') == 0


def test_rate_limit_during_export_is_shown(run):
    run.model.on('promptExportSpec', ModelError('rate_limited'))
    set_format(run, FMT)
    build(run)
    assert 'исчерпан лимит использования' in run.text('#tab-body') and run.count('[data-act=run-export]') == 1   # можно повторить


def test_format_edits_from_the_export_tab_open_the_dialog(run):
    run.tab('export')
    run.page.click('[data-act=cfg-export]')
    assert run.visible('#set-ov') and run.page.get_attribute('#settab-export', 'aria-selected') == 'true'
