"""Окно загрузчика, открытое вручную (значок расширения): файл или вставленный JSON, выбор раздела, выбор кейсов, ошибки."""
import json

import pytest

from tests.support.extension import wait_window_ready

CASES = [
    {'name': 'Вход с верным паролем', 'qaId': 'UI-001', 'priority': 'P3_HIGH', 'suites': ['smoke', 'regression'], 'steps': [{'action': '<p>Открыть /login</p>', 'expectedResult': '<p>Страница входа</p>'}]},
    {'name': 'Вход без пароля', 'qaId': 'UI-002', 'priority': 'P2_MEDIUM', 'suites': ['regression'], 'steps': []},
    {'name': 'Выход из кабинета', 'qaId': 'UI-003', 'priority': 'P1_LOW', 'suites': ['smoke'], 'steps': []},
]


def open_window(ext, query=''):
    w = ext.ext_page('upload.html' + query)
    wait_window_ready(w, cases=False)
    return w


def paste(w, cases=CASES, raw=None):
    w.evaluate("() => { document.querySelector('details').open = true; }")
    w.fill('#paste', raw if raw is not None else json.dumps(cases, ensure_ascii=False))
    w.click('#paste-apply')


def set_section(w, env, section='124'):
    w.fill('#sect-url', f'{env.sfera.base}/project/PPAN?section={section}')
    w.dispatch_event('#sect-url', 'change')
    w.wait_for_function("(s) => document.querySelector('#sect').value === s", arg=section)


def go(w):
    w.click('#go')
    w.wait_for_selector('#summary:not([hidden])')


# ---------- пустое окно ----------
def test_empty_window_asks_for_a_file(ext):
    w = open_window(ext)
    assert w.is_visible('#manual') and w.inner_text('#source') == 'Откройте файл, выгруженный из QA pro'
    assert w.is_disabled('#go') and w.inner_text('#go-note') == 'Нет тест-кейсов.'


def test_outdated_job_is_explained(ext):
    w = ext.ext_page('upload.html?job=net-takogo')
    w.wait_for_function("() => /устарело/.test(document.querySelector('#source').textContent)")
    assert w.inner_text('#source') == 'Задание устарело — отправьте кейсы из QA pro ещё раз.'


# ---------- вход в Сферу ----------
def test_window_shows_login(ext):
    w = open_window(ext)
    assert w.inner_text('#login') == 'Вход в Сферу найден' and w.is_hidden('#login-warn')


def test_without_sfera_login_the_window_explains_what_to_do(make_env):
    env = make_env(login=False)
    w = open_window(env.ext)
    paste(w)
    assert w.inner_text('#login') == 'Нет входа в Сферу'
    assert env.sfera.base in w.inner_text('#login-warn') and 'войдите' in w.inner_text('#login-warn')
    assert w.is_disabled('#go') and w.inner_text('#go-note') == 'Войдите в Сферу ФТ в этом браузере.'


# ---------- ввод кейсов ----------
def test_pasted_cases_are_listed_with_marks(ext):
    w = open_window(ext)
    paste(w)
    rows = w.eval_on_selector_all('#rows tr', 'rs => rs.map((r) => [r.children[1].innerText.split("\\n")[0], r.children[2].innerText, r.children[3].innerText.replace(/\\s+/g, " ").trim()])')
    assert rows == [['Вход с верным паролем', 'Высокий', 'SMOKE РЕГРЕССИОННЫЙ'], ['Вход без пароля', 'Средний', 'РЕГРЕССИОННЫЙ'], ['Выход из кабинета', 'Низкий', 'SMOKE']]
    assert w.inner_text('#source') == 'Из вставленного JSON'


def test_object_with_cases_field_is_accepted_and_nameless_cases_are_skipped(ext):
    w = open_window(ext)
    paste(w, raw=json.dumps({'cases': CASES[:2] + [{'qaId': 'X'}, {'name': '  '}]}))
    assert w.locator('#rows input[data-i]').count() == 2


def test_broken_json_is_reported(ext):
    w = open_window(ext)
    paste(w, raw='{не json')
    assert 'Не удалось разобрать' in w.inner_text('#file-name')


def test_json_without_cases_is_reported(ext):
    w = open_window(ext)
    paste(w, raw='{"x": 1}')
    assert 'Ожидается массив тест-кейсов или объект с полем cases.' in w.inner_text('#file-name')


def test_file_is_read(ext, tmp_path):
    p = tmp_path / 'набор.json'
    p.write_text(json.dumps({'format': 'qa-pro/sfera-v1', 'cases': CASES}, ensure_ascii=False), encoding='utf-8')
    w = open_window(ext)
    w.set_input_files('#file', str(p))
    w.wait_for_selector('#rows input[data-i]')
    assert w.inner_text('#source') == 'Из файла набор.json' and w.locator('#rows input[data-i]').count() == 3


# ---------- раздел ----------
def test_bad_section_link_is_explained(ext):
    w = open_window(ext)
    w.fill('#sect-url', 'https://example.com/nothing')
    w.dispatch_event('#sect-url', 'change')
    assert w.inner_text('#tabs-note') == 'В ссылке не нашёл /project/<код>?section=<id>.'


def test_without_an_open_sfera_tab(make_env):
    w = open_window(make_env().ext)
    w.click('#from-tab')
    w.wait_for_function("() => document.querySelector('#tabs-note').textContent !== ''")
    assert w.inner_text('#tabs-note') == 'Не нашёл открытой вкладки Сферы ФТ с разделом проекта.'


def test_several_sfera_tabs_are_offered_to_choose_from(env):
    env.ext.page(env.sfera.base + '/project/PPAN?section=123')
    w = open_window(env.ext)
    w.click('#from-tab')
    w.wait_for_selector('#tabs-note [data-tab-url]')
    assert w.locator('#tabs-note [data-tab-url]').count() == 2
    w.click('#tabs-note [data-tab-url]:first-child')
    assert '/project/PPAN?section=' in w.input_value('#sect-url') and w.input_value('#proj') == 'PPAN'


def test_project_code_can_be_typed(ext):
    w = open_window(ext)
    paste(w)
    w.fill('#proj', 'PPAN')
    w.dispatch_event('#proj', 'change')
    w.wait_for_function("() => document.querySelectorAll('#sect option').length === 3")
    w.select_option('#sect', '124')
    assert w.inner_text('#go-note') == 'в проект PPAN, раздел Восстановление пароля' and w.inner_text('#go') == 'Загрузить 3'


def test_unavailable_sections_do_not_block_the_upload(env):
    """Список разделов не загрузился (Сфера ответила 500) — раздел из ссылки остаётся, загрузить можно."""
    env.sfera.fail_sections = True
    w = open_window(env.ext)
    paste(w)
    set_section(w, env)
    assert 'Сфера ответила 500 при получении разделов проекта PPAN.' in w.inner_text('#tabs-note')
    assert w.eval_on_selector('#sect', 'e => e.selectedOptions[0].textContent') == 'Раздел #124'
    go(w)
    assert 'Создано в Сфере ФТ: 3 из 3' in w.inner_text('#summary') and all(p['sectionId'] == 124 for p in env.sfera.posts)


def test_last_section_is_remembered(env):
    w = open_window(env.ext)
    paste(w)
    set_section(w, env)
    go(w)
    again = open_window(env.ext)
    again.wait_for_function("() => document.querySelector('#sect').value === '124'")
    assert again.input_value('#proj') == 'PPAN' and again.input_value('#sect-url').endswith('/project/PPAN?section=124')


# ---------- выбор кейсов ----------
def test_all_cases_are_checked_by_default(ext):
    w = open_window(ext)
    paste(w)
    assert w.is_checked('#all') and w.locator('#rows input[data-i]:checked').count() == 3


def test_unchecked_case_is_not_uploaded(env):
    w = open_window(env.ext)
    paste(w)
    set_section(w, env)
    w.uncheck('#rows input[data-i="1"]')
    assert w.inner_text('#go') == 'Загрузить 2' and not w.is_checked('#all')
    go(w)
    assert sorted(p['name'] for p in env.sfera.posts) == ['Вход с верным паролем', 'Выход из кабинета']


def test_select_all_toggle(ext):
    w = open_window(ext)
    paste(w)
    w.uncheck('#all')
    assert w.locator('#rows input[data-i]:checked').count() == 0 and w.is_disabled('#go') and w.inner_text('#go-note') == 'Отметьте тест-кейсы.'
    w.check('#all')
    assert w.locator('#rows input[data-i]:checked').count() == 3


# ---------- загрузка ----------
def test_manual_upload_has_no_report_back_to_qa_pro(env):
    w = open_window(env.ext)
    paste(w)
    set_section(w, env)
    go(w)
    assert 'Создано в Сфере ФТ: 3 из 3' in w.inner_text('#summary') and 'Результат отправлен в QA pro' not in w.inner_text('#summary')


def test_uploaded_rows_show_the_sfera_code(env):
    w = open_window(env.ext)
    paste(w)
    set_section(w, env)
    go(w)
    assert w.eval_on_selector_all('#rows tr', 'rs => rs.map((r) => r.children[4].innerText.trim())') == ['✓ PPAN-T1', '✓ PPAN-T2', '✓ PPAN-T3']


def test_sfera_down_is_a_row_error_not_a_crash(env):
    w = open_window(env.ext)
    paste(w)
    set_section(w, env)
    env.sfera.stop()
    go(w)
    assert 'Создано в Сфере ФТ: 0 из 3' in w.inner_text('#summary') and 'С ошибкой: 3' in w.inner_text('#summary')
    assert w.eval_on_selector_all('#rows tr', 'rs => rs.map((r) => r.children[4].innerText.trim())') == ['✗ ошибка'] * 3
    assert 'Сетевая ошибка' in w.eval_on_selector('#rows tr .res-bad', 'e => e.title')


def test_close_button_closes_the_window(env):
    w = open_window(env.ext)
    paste(w)
    set_section(w, env)
    go(w)
    with w.expect_event('close'):
        w.click('#close')
    assert w.is_closed()


def test_every_sfera_api_request_carries_the_cookie_token(env):
    """Вход берётся из cookie ACCESS_TOKEN: токен вводить не нужно, он уходит заголовком Bearer."""
    w = open_window(env.ext)
    paste(w)
    set_section(w, env)
    go(w)
    assert env.sfera.requests and {r['auth'] for r in env.sfera.requests if r['path'].startswith('/app/')} == {'Bearer tok-123'}
