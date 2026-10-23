"""Баг-репорт по трассировке: оформление по шаблону команды, правка, копирование, сохранение в продукт, поиск дублей."""
from tests.test_trace import STACK, run_trace

CASES = [
    {'r': 'run1', 'i': 'API-001', 't': 'api', 'n': 'Создание правила корреляции по времени с числовым интервалом'},
    {'r': 'run1', 'i': 'UI-004', 't': 'ui', 'n': 'Экран профиля: смена аватара'},
]


def seed_cases(app):
    app.call('(S.prodIndex = { pid: S.productId, cases: arg, checklist: [] }, true)', CASES)


def make_defect(app, stack=''):
    run_trace(app, stack=stack)
    app.page.click('[data-act=defect-run]')
    app.page.wait_for_selector('#def-title', timeout=30000)


def test_defect_button_appears_only_after_trace(app):
    app.mode('trace')
    assert app.count('[data-act=defect-run]') == 0
    run_trace(app)
    assert app.visible('[data-act=defect-run]')


def test_defect_form_is_filled_and_normalized(app):
    make_defect(app)
    assert 'возвращает 500' in app.page.input_value('#def-title')
    assert app.page.input_value('#def-severity') == 'critical'      # «Critical» → нижний регистр
    assert app.page.input_value('#def-priority') == 'high'
    steps = app.page.input_value('#def-steps').split('\n')
    assert steps[0] == 'Открыть раздел «Правила корреляции»'         # номер «1.» снят
    assert len(steps) == 3
    assert app.page.input_value('#def-f0') == 'нет данных'           # поле из шаблона команды


def test_trace_and_candidates_go_into_the_prompt(app):
    seed_cases(app)
    make_defect(app, stack=STACK)
    prompt = app.model.prompts_of('promptDefect')[0]
    assert STACK in prompt
    assert 'Место сбоя: ClassCastException' in prompt
    assert 'API-001: Создание правила корреляции' in prompt
    assert 'UI-004' not in prompt          # нерелевантный кейс не отправляется модели


def test_related_cases_only_from_candidates(app):
    seed_cases(app)
    make_defect(app)
    assert app.state('S.trace.defect.relatedCases') == ['API-001']   # API-999 модель выдумала — отброшен


def test_team_template_goes_into_the_prompt(app):
    app.call("(S.cfg.defectTpl = 'Обязательное поле: Версия сборки', true)")
    make_defect(app)
    assert 'Обязательное поле: Версия сборки' in app.model.prompts_of('promptDefect')[0]


def test_edits_go_into_copied_text(app):
    make_defect(app)
    app.page.fill('#def-title', 'Мой заголовок')
    app.page.fill('#def-steps', 'Шаг один\nШаг два')
    app.page.select_option('#def-severity', 'minor')
    text = app.call('a.defectText(S.trace.defect, false)')
    assert text.startswith('Мой заголовок')
    assert '1. Шаг один\n2. Шаг два' in text
    assert 'Незначительный' in text
    md = app.call('a.defectText(S.trace.defect, true)')
    assert md.startswith('## Мой заголовок') and '**Фактический результат**' in md


def test_download_markdown(app):
    make_defect(app)
    app.page.click('[data-act=defect-dl]')
    app.page.wait_for_function('() => (window.__downloads || []).length === 1')
    d = app.downloads()[0]
    assert d['filename'].startswith('defect_') and d['filename'].endswith('.md')
    assert d['text'].startswith('## Сохранение правила')


def test_save_numbers_and_lists_defects(app):
    make_defect(app)
    app.page.click('[data-act=defect-save]')
    app.page.wait_for_function('() => window.__qa.S.trace.defect.id === "D-001"')
    app.page.wait_for_selector('.defect-list')
    assert 'D-001' in app.text('.defect-list')
    # второй дефект получает следующий номер
    app.call('(S.trace.defect = null, true)')
    app.call('(a.renderTab(), true)')
    app.page.click('[data-act=defect-run]')
    app.page.wait_for_selector('#def-title')
    app.page.click('[data-act=defect-save]')
    app.page.wait_for_function('() => window.__qa.S.trace.defect.id === "D-002"')


def test_saved_defects_survive_reload_and_open(app):
    make_defect(app)
    app.page.fill('#def-title', 'Сохранённый дефект')
    app.page.click('[data-act=defect-save]')
    app.page.wait_for_function('() => window.__qa.S.trace.defect.id === "D-001"')
    app.reload()
    app.mode('trace')
    app.page.wait_for_selector('.defect-list')
    app.page.click('.defect-list [data-act=defect-open]')
    app.page.wait_for_selector('#def-title')
    assert app.page.input_value('#def-title') == 'Сохранённый дефект'
    assert app.count('.trace-steps > li') == 2      # трассировка восстановлена вместе с дефектом


def test_existing_defects_are_offered_as_duplicates(app):
    make_defect(app)
    app.page.click('[data-act=defect-save]')
    app.page.wait_for_function('() => window.__qa.S.trace.defect.id === "D-001"')
    app.model.on('promptDefect', lambda c: {'title': 'Повторный дефект', 'severity': 'major', 'priority': 'medium', 'steps': ['Сохранить правило'], 'expected': 'ок', 'actual': '500',
                                            'duplicates': [{'id': 'D-001', 'reason': 'то же место сбоя'}, {'id': 'D-777', 'reason': 'выдуман'}]})
    app.call('(S.trace.defect = null, a.renderTab(), true)')
    app.page.click('[data-act=defect-run]')
    app.page.wait_for_selector('.defect-dups')
    prompt = app.model.prompts_of('promptDefect')[-1]
    assert 'D-001: Сохранение правила корреляции' in prompt
    banner = app.text('.defect-dups')
    assert 'D-001' in banner and 'то же место сбоя' in banner and 'D-777' not in banner


def test_delete_defect(app):
    make_defect(app)
    app.page.click('[data-act=defect-save]')
    app.page.wait_for_selector('.defect-list')
    btn = app.page.locator('.defect-list [data-act=defect-del]')
    btn.click()
    btn.click()      # второе нажатие подтверждает
    app.page.wait_for_function('() => !document.querySelector(".defect-list")')
    assert app.state('S.defects.items.length') == 0


def test_template_setting_tab(app):
    app.page.click('#btn-settings')
    app.page.click('[data-settab=defect]')
    app.page.fill('#cfg-defect', 'Поле: Стенд')
    assert app.state('S.cfg.defectTpl') == 'Поле: Стенд'
    assert app.state('S.cfgDirty.defect') is True
