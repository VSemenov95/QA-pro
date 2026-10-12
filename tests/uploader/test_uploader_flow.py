"""Сквозная загрузка: QA pro (автономная версия в Chrome) → расширение → окно загрузчика → Сфера ФТ (мок).

Один проход выполняется один раз на файл (фикстура flow), каждый тест проверяет свою сторону результата.
Остальные сценарии — отмена, сбой одного кейса, ручная загрузка файла, настройки — со своей средой.
"""
import json
import re
from types import SimpleNamespace

import pytest

from tests.support.extension import case_marks, manifest, wait_window_ready
from tests.support.model import case_body

CASE_INFO = """() => S.run.cases.filter((c) => c.status !== 'obsolete').map((c) => {
  const su = (c.suites || []).map((x) => String(x).toLowerCase());
  return { uid: c.uid, id: c.dispId, name: a.tmsCase(c).title, smoke: su.some((x) => /smoke|смоук/.test(x)), regress: su.some((x) => /regress|регресс/.test(x)) };
})"""
ROWS = "() => [...document.querySelectorAll('#rows tr')].map((r) => [r.children[1].innerText.split('\\n')[0], r.children[3].innerText.replace(/\\s+/g, ' ').trim()])"


def case_info(app):
    return app.page.evaluate("() => { const a = window.__qa, S = a.S; return (" + CASE_INFO + ")(); }")


def log_text(app):
    return app.page.evaluate("() => document.querySelector('#tms-bar .log')?.innerText || ''")


def wait_log(app, pattern, timeout=20000):
    app.page.wait_for_function("(p) => new RegExp(p).test(document.querySelector('#tms-bar .log')?.innerText || '')", arg=pattern, timeout=timeout)
    return log_text(app)


def pick_section_from_tab(win):
    win.click('#from-tab')
    win.wait_for_function("() => document.querySelector('#sect').value === '124'", timeout=15000)


def run_upload(win):
    win.click('#go')
    win.wait_for_selector('#summary:not([hidden])', timeout=20000)
    win.wait_for_function("() => !document.querySelector('#go').textContent.startsWith('Загружаю')")


@pytest.fixture(scope='module')
def flow(new_env):
    env = new_env()
    qa = env.qa()
    f = SimpleNamespace(env=env, qa=qa, ver=manifest()['version'])
    f.cases = case_info(qa)
    f.bar_before = qa.text('#tms-bar')
    f.marks_before = case_marks(qa)
    win = env.ext.window_from(lambda: qa.page.click('[data-act=tms-upload]'))
    wait_window_ready(win)
    f.win = win
    f.win_url = win.url
    f.source = win.inner_text('#source')
    f.login = win.inner_text('#login')
    f.rows = win.evaluate(ROWS)
    f.log_opened = wait_log(qa, 'Открылось окно загрузчика')
    f.go_before = (win.inner_text('#go'), win.is_disabled('#go'), win.inner_text('#go-note'))
    pick_section_from_tab(win)
    f.sect_url, f.proj = win.input_value('#sect-url'), win.input_value('#proj')
    f.sect_text = win.eval_on_selector('#sect', 'e => e.selectedOptions[0].textContent')
    f.go = (win.inner_text('#go'), win.inner_text('#go-note'))
    run_upload(win)
    f.summary = win.inner_text('#summary')
    f.log_done = wait_log(qa, 'загружено')
    qa.page.wait_for_function("() => [...document.querySelectorAll('#case-list article')].every((a) => /в ТМС/.test(a.textContent))")
    f.marks_after = case_marks(qa)
    f.posts = list(env.sfera.posts)
    f.requests = list(env.sfera.requests)
    return f


def by_name(f):
    return {c['name']: c for c in f.cases}


# ---------- до загрузки ----------
def test_cases_exist(flow):
    assert len(flow.cases) >= 3


def test_upload_button_counts_all_cases(flow):
    assert f'Загрузить в Сферу ФТ ({len(flow.cases)})' in flow.bar_before


def test_bar_names_the_uploader_version(flow):
    assert f'через загрузчик {flow.ver}' in flow.bar_before


def test_cases_show_suite_marks(flow):
    marks = dict(flow.marks_before)
    for c in flow.cases:
        chips = marks[c['id']]
        assert ('Смоук' in chips) is c['smoke'] and ('Регресс' in chips) is c['regress']
    assert not any('в ТМС' in ' '.join(chips) for chips in marks.values())


# ---------- окно загрузчика ----------
def test_window_is_the_uploader_page(flow):
    assert re.search(r'^chrome-extension://[a-p]{32}/upload\.html\?job=', flow.win_url)


def test_window_says_where_cases_come_from(flow):
    assert flow.source.startswith('Из QA pro') and 'Мой продукт' in flow.source


def test_window_sees_the_sfera_login(flow):
    assert flow.login == 'Вход в Сферу найден'


def test_qa_pro_tells_that_the_window_is_open(flow):
    assert 'Открылось окно загрузчика: выберите раздел Сферы ФТ' in flow.log_opened


def test_window_lists_every_case(flow):
    assert sorted(n for n, _ in flow.rows) == sorted(c['name'] for c in flow.cases)


def test_window_marks_smoke_and_regression(flow):
    """Смоук — метка SMOKE, регресс — «Регрессионный»."""
    cs = by_name(flow)
    for name, tags in flow.rows:
        assert ('SMOKE' in tags) is cs[name]['smoke'] and ('РЕГРЕССИОННЫЙ' in tags) is cs[name]['regress']


def test_upload_is_blocked_until_a_section_is_chosen(flow):
    text, disabled, note = flow.go_before
    assert disabled is True and note == 'Укажите проект и раздел.'


def test_section_is_taken_from_the_open_sfera_tab(flow):
    assert flow.sect_url.endswith('/project/PPAN?section=124') and flow.proj == 'PPAN'
    assert flow.sect_text.endswith('Восстановление пароля')


def test_sections_are_shown_as_a_tree(flow):
    opts = flow.win.eval_on_selector_all('#sect option', 'els => els.map((e) => e.textContent)')
    assert opts[1:] == ['Личный кабинет', '  └ Восстановление пароля']


def test_go_button_names_the_target(flow):
    assert flow.go == (f'Загрузить {len(flow.cases)}', 'в проект PPAN, раздел Восстановление пароля')


# ---------- результат ----------
def test_window_summary(flow):
    n = len(flow.cases)
    assert f'Создано в Сфере ФТ: {n} из {n}' in flow.summary and 'Результат отправлен в QA pro' in flow.summary


def test_qa_pro_gets_the_result(flow):
    assert f'Сфера ФТ: загружено {len(flow.cases)} · проект PPAN, раздел 124' in flow.log_done


def test_cases_get_the_sfera_code(flow):
    """У каждого кейса отметка «в ТМС · <код>», код — тот, что выдала Сфера именно этому кейсу."""
    code = {p['name']: f'PPAN-T{i + 1}' for i, p in enumerate(flow.posts)}
    marks = dict(flow.marks_after)
    for c in flow.cases:
        assert f'в ТМС · {code[c["name"]]}' in marks[c['id']]


def test_one_request_per_case(flow):
    assert sorted(p['name'] for p in flow.posts) == sorted(c['name'] for c in flow.cases)


def test_smoke_cases_get_the_smoke_label_and_nothing_else(flow):
    cs = by_name(flow)
    assert all(p['labels'] == (['SMOKE'] if cs[p['name']]['smoke'] else []) for p in flow.posts)


def test_ai_gen_label_is_never_set(flow):
    assert all('AI_gen' not in p['labels'] for p in flow.posts)


def test_regression_cases_get_the_regression_field(flow):
    cs = by_name(flow)
    assert all(p['ti_regressive'] is cs[p['name']]['regress'] for p in flow.posts)
    assert any(p['ti_regressive'] for p in flow.posts)


def test_cases_go_to_the_chosen_section(flow):
    assert all(p['sectionId'] == 124 and p['projectCode'] == 'PPAN' for p in flow.posts)


def test_new_cases_get_default_values_from_the_sfera_catalogs(flow):
    assert all(p['statusId'] == 'st-created' and p['ti_status'] == 'tis-def' and p['ti_priority'] == 'tip-def' and p['type'] == 'T1_TEST_CASE' for p in flow.posts)


def test_steps_and_priority_are_passed(flow):
    for p in flow.posts:
        assert p['priority'] == 'P3_HIGH' and p['steps'] and all(s['action'].startswith('<p>') for s in p['steps'])


def test_login_comes_from_the_sfera_cookie(flow):
    """Токен берётся из cookie ACCESS_TOKEN Сферы и уходит заголовком Bearer во все запросы к её API."""
    api = [r for r in flow.requests if r['path'].startswith('/app/testing/')]
    assert api and all(r['auth'] == 'Bearer tok-123' for r in api)


# ---------- отмена: окно закрыли без загрузки ----------
def test_closing_the_window_cancels_the_upload(env):
    qa = env.qa()
    win = env.ext.window_from(lambda: qa.page.click('[data-act=tms-upload]'))
    wait_window_ready(win)
    win.close()
    assert 'Окно загрузчика закрыто без загрузки.' in wait_log(qa, 'закрыто без загрузки')
    assert env.sfera.posts == [] and 'в ТМС' not in qa.text('#case-list')


def test_stop_button_while_waiting(env):
    qa = env.qa()
    env.ext.window_from(lambda: qa.page.click('[data-act=tms-upload]'))
    qa.page.wait_for_selector('[data-act=tms-stop]')
    qa.page.click('[data-act=tms-stop]')
    assert 'Перестал ждать загрузчик' in wait_log(qa, 'Перестал ждать')


# ---------- один кейс Сфера отклонила ----------
@pytest.fixture(scope='module')
def partial(new_env):
    env = new_env()

    def gen(call):
        ids = re.findall(r'### ([A-Z]+-\d+)\.', call.prompt)
        return {'cases': [{'planItem': pid, 'requirementIds': [], 'suites': ['regression'], 'testCase': case_body(f'Кейс {pid} проверка' + (' сбой' if pid == 'P-01' else ''))} for pid in ids]}
    env.model.on('promptGenerate', gen)
    qa = env.qa()
    f = SimpleNamespace(env=env, qa=qa, n=len(case_info(qa)))
    win = env.ext.window_from(lambda: qa.page.click('[data-act=tms-upload]'))
    wait_window_ready(win)
    pick_section_from_tab(win)
    run_upload(win)
    f.summary = win.inner_text('#summary')
    f.row_results = win.eval_on_selector_all('#rows tr', 'rs => rs.map((r) => [r.children[1].innerText.split("\\n")[0], r.children[4].innerText.trim()])')
    f.log = wait_log(qa, 'загружено')
    f.qa_marks = case_marks(qa)
    f.posts_first = len(env.sfera.posts)
    win.click('#retry')
    win.wait_for_function("() => document.querySelector('#summary').textContent.includes('из 1')")
    f.retry_summary = win.inner_text('#summary')
    f.posts_after_retry = env.sfera.posts[f.posts_first:]
    return f


def test_failed_case_is_counted(partial):
    assert f'Создано в Сфере ФТ: {partial.n - 1} из {partial.n}' in partial.summary and 'С ошибкой: 1' in partial.summary


def test_failed_case_shows_the_http_status(partial):
    bad = [r for n, r in partial.row_results if 'сбой' in n]
    assert bad == ['✗ HTTP 400'] and sum(r.startswith('✓ PPAN-T') for _, r in partial.row_results) == partial.n - 1


def test_qa_pro_reports_partial_success(partial):
    assert f'Сфера ФТ: загружено {partial.n - 1}, с ошибкой 1' in partial.log
    assert 'Сфера ответила 400' in partial.qa.text('#tms-bar .log')


def test_only_uploaded_cases_are_marked(partial):
    marked = [i for i, chips in partial.qa_marks if any('в ТМС' in c for c in chips)]
    assert len(marked) == partial.n - 1


def test_retry_sends_only_the_failed_case(partial):
    assert [p['name'] for p in partial.posts_after_retry if 'сбой' not in p['name']] == [] and len(partial.posts_after_retry) == 1
    assert 'Создано в Сфере ФТ: 0 из 1' in partial.retry_summary


# ---------- ручная загрузка файла ----------
def test_json_for_uploader_has_the_documented_format(env, tmp_path):
    qa = env.qa()
    with qa.page.expect_download() as d:
        qa.page.click('[data-act=sfera-json]')
    path = tmp_path / 'qa-pro-sfera.json'
    d.value.save_as(str(path))
    j = json.loads(path.read_text(encoding='utf-8'))
    assert d.value.suggested_filename == 'qa-pro-sfera.json' and j['format'] == 'qa-pro/sfera-v1'
    assert len(j['cases']) == len(case_info(qa)) and {'ref', 'qaId', 'name', 'description', 'preConditions', 'steps', 'postConditions', 'priority', 'suites'} <= set(j['cases'][0])
    man = env.ext.ext_page('upload.html')
    man.set_input_files('#file', str(path))
    man.wait_for_selector('#rows input[data-i]')
    assert man.inner_text('#source') == 'Из файла qa-pro-sfera.json' and man.locator('#rows tr').count() == len(j['cases'])


def test_manual_upload_remembers_the_last_section(env, tmp_path):
    qa = env.qa()
    with qa.page.expect_download() as d:
        qa.page.click('[data-act=sfera-json]')
    path = tmp_path / 'qa-pro-sfera.json'
    d.value.save_as(str(path))
    win = env.ext.ext_page('upload.html')
    win.set_input_files('#file', str(path))
    win.wait_for_selector('#rows input[data-i]')
    win.fill('#sect-url', env.sfera.base + '/project/PPAN?section=124')
    win.dispatch_event('#sect-url', 'change')
    win.wait_for_function("() => document.querySelector('#sect').value === '124'")
    win.click('#go')
    win.wait_for_selector('#summary:not([hidden])')
    assert f'Создано в Сфере ФТ: {len(env.sfera.posts)} из {len(env.sfera.posts)}' in win.inner_text('#summary')
    assert 'Результат отправлен в QA pro' not in win.inner_text('#summary')
    again = env.ext.ext_page('upload.html')
    again.wait_for_function("() => document.querySelector('#sect-url').value !== ''")
    assert again.input_value('#sect-url').endswith('/project/PPAN?section=124')


# ---------- настройки QA pro: вкладка ТМС ----------
def test_settings_tab_finds_the_uploader(env):
    qa = env.qa()
    qa.open_settings('tms')
    qa.page.wait_for_function("() => /Загрузчик найден/.test(document.querySelector('#tms-body .banner')?.innerText || '')")
    assert f'Загрузчик найден · версия {manifest()["version"]} · Сфера: {env.sfera.base}' in qa.text('#tms-body .banner')


def test_connection_check_names_version_and_sfera(env):
    qa = env.qa()
    qa.open_settings('tms')
    qa.page.click('[data-tmb=test]')
    qa.page.wait_for_function("() => /Загрузчик найден/.test(document.querySelector('#tms-body .case-note')?.innerText || '')")
    assert qa.text('#tms-body .case-note') == f'Загрузчик найден, версия {manifest()["version"]}. Сфера: {env.sfera.base}. Вход проверяется в окне загрузчика.'


def test_uploader_zip_from_settings_is_a_copy_of_the_extension(env, tmp_path):
    import os
    import zipfile
    from tests.support.extension import EXT_SRC
    qa = env.qa()
    qa.open_settings('tms')
    with qa.page.expect_download() as d:
        qa.page.click('#tms-body [data-act=sfera-zip]')
    z = tmp_path / d.value.suggested_filename
    d.value.save_as(str(z))
    zf = zipfile.ZipFile(z)
    files = [f for f in os.listdir(EXT_SRC) if os.path.isfile(os.path.join(EXT_SRC, f))]
    assert d.value.suggested_filename == 'qa-pro-sfera-uploader.zip' and zf.testzip() is None
    assert sorted(zf.namelist()) == sorted('qa-pro-sfera-uploader/' + f for f in files)
    assert all(zf.read('qa-pro-sfera-uploader/' + f) == open(os.path.join(EXT_SRC, f), 'rb').read() for f in files)
