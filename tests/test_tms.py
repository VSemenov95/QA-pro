"""ТМС в настройках и загрузка кейсов в Test IT, Qase, TestRail и свой API (автономная версия: на claude.ai страница изолирована от интернета)."""
import base64
import json

import pytest

from tests.support.model_generation import TmsRoute, connect_ai, standalone

TESTIT = {'kind': 'testit', 'baseUrl': 'http://tms.test', 'token': 'tok', 'project': 'proj-uuid'}
QASE = {'kind': 'qase', 'baseUrl': 'http://tms.test', 'token': 'qtok', 'project': 'DEMO'}
TESTRAIL = {'kind': 'testrail', 'baseUrl': 'http://tms.test', 'token': 'trkey', 'user': 'qa@company.ru', 'section': '123'}
CUSTOM = {'kind': 'custom', 'url': 'http://tms.test/api/test-cases', 'token': 'ctok', 'mode': 'case'}


def configure(app, cfg):
    """Настройки ТМС через окно «Шестерёнка → ТМС»: выбрать систему, заполнить поля, сохранить."""
    if app.page.is_visible('#set-ov'):
        app.page.click('#settab-tms')
    else:
        app.open_settings('tms')
    app.page.select_option('#tm-kind', cfg['kind'])
    for k, v in cfg.items():
        if k == 'kind':
            continue
        if k in ('mode', 'state'):
            app.page.select_option(f'#tm-{k}', v)
        else:
            app.page.fill(f'#tm-{k}', str(v))
    app.page.click('[data-tmb=save]')


@pytest.fixture
def alone(make_app):
    """Автономная версия: кейсы сгенерированы через подключение; ТМС «отвечает» на http://tms.test."""
    app = make_app(**standalone())
    connect_ai(app)
    app.tms = TmsRoute(app)
    app.add_sample()
    app.generate()
    return app


def upload(app, cfg):
    configure(app, cfg)
    app.close_settings()
    app.tab('cases')
    app.page.click('[data-act=tms-upload]')
    app.page.wait_for_function("() => !window.__qa.S.tmsBusy")


def case_marks(app):
    return app.state("Object.fromEntries(S.run.cases.map((c) => [c.dispId, c.tms ? [c.tms.kind, c.tms.id] : null]))")


def log_text(app):
    return app.text('#tms-bar .log')


# ---------- окно настроек ----------
def test_gear_on_cases_tab_opens_tms_settings(app):
    app.add_sample()
    app.generate()
    app.tab('cases')
    app.page.click('[data-act=tms-settings]')
    assert app.visible('#set-tms') and app.page.eval_on_selector('#set-tabs [aria-selected=true]', 'e => e.textContent') == 'ТМС'


def test_sfera_is_default_system(app):
    app.open_settings('tms')
    assert app.page.input_value('#tm-kind') == 'sfera' and app.state('S.tms.kind') == 'sfera'
    assert app.count('#tm-baseUrl') == 0 and 'Скачать загрузчик (.zip)' in app.text('#tms-body')


@pytest.mark.parametrize('kind,fields', [
    ('testit', ['baseUrl', 'token', 'project', 'section', 'duration']),
    ('qase', ['baseUrl', 'token', 'project', 'section']),
    ('testrail', ['baseUrl', 'user', 'token', 'section']),
    ('custom', ['url', 'token', 'headers'])])
def test_kind_shows_its_fields(app, kind, fields):
    app.open_settings('tms')
    app.page.select_option('#tm-kind', kind)
    shown = app.page.eval_on_selector_all('#tms-body [data-tm]', 'els => els.map((e) => e.dataset.tm)')
    assert [f for f in shown if f != 'kind' and f != 'state' and f != 'mode'] == fields


def test_token_field_is_hidden_text(app):
    app.open_settings('tms')
    app.page.select_option('#tm-kind', 'testit')
    assert app.page.get_attribute('#tm-token', 'type') == 'password'


def test_unsaved_tms_changes_are_marked(make_app):
    app = make_app(kind='standalone')
    app.open_settings('tms')
    app.page.select_option('#tm-kind', 'testit')
    app.page.fill('#tm-baseUrl', 'http://tms.test')
    assert app.count('#settab-tms .dot-d') == 1 and app.page.evaluate("() => document.querySelector('#btn-settings').classList.contains('dirty')")
    app.page.click('[data-tmb=save]')
    assert app.count('#settab-tms .dot-d') == 0 and not app.page.evaluate("() => document.querySelector('#btn-settings').classList.contains('dirty')")
    assert 'Настройки ТМС сохранены' in ' '.join(app.toast_texts())


def test_tms_settings_are_kept_in_this_browser_only(make_app):
    app = make_app(kind='standalone')
    configure(app, TESTIT)
    stored = json.loads(app.page.evaluate("() => localStorage.getItem('qapro.tms')"))
    assert stored['kind'] == 'testit' and stored['token'] == 'tok' and stored['project'] == 'proj-uuid'
    app.reload()
    assert app.state('S.tms.kind') == 'testit' and app.state('S.tms.project') == 'proj-uuid'
    app.open_settings('tms')
    assert 'Токен хранится только в этом браузере.' in app.text('#tms-body') and app.page.input_value('#tm-token') == 'tok'


def test_nothing_is_saved_without_save_button(make_app):
    app = make_app(kind='standalone')
    app.open_settings('tms')
    app.page.select_option('#tm-kind', 'qase')
    app.close_settings()
    assert app.state('S.tms.kind') == 'sfera'


@pytest.mark.parametrize('cfg,message', [
    ({'kind': 'testit'}, 'Укажите адрес API в настройках ТМС.'),
    ({'kind': 'testit', 'baseUrl': 'http://tms.test'}, 'Укажите токен в настройках ТМС.'),
    ({'kind': 'testit', 'baseUrl': 'http://tms.test', 'token': 't'}, 'Укажите ID проекта Test IT.'),
    ({'kind': 'qase', 'token': 't'}, 'Укажите код проекта Qase.'),
    ({'kind': 'testrail', 'baseUrl': 'http://tms.test', 'token': 't'}, 'Укажите логин и ID раздела TestRail.')])
def test_incomplete_settings_are_explained(make_app, cfg, message):
    app = make_app(kind='standalone')
    app.open_settings('tms')
    app.page.select_option('#tm-kind', cfg['kind'])
    for k, v in cfg.items():
        if k != 'kind':
            app.page.fill(f'#tm-{k}', v)
    app.page.click('[data-tmb=test]')
    assert app.text('#tms-body .case-note') == message


def test_connection_check_testit(alone):
    configure(alone, TESTIT)
    alone.page.click('[data-tmb=test]')
    alone.page.wait_for_function("() => document.querySelector('#tms-body .case-note')?.textContent.includes('Проект найден')")
    assert alone.text('#tms-body .case-note') == 'Проект найден: Демо-проект'
    r = alone.tms.requests[-1]
    assert r['method'] == 'GET' and r['path'] == '/api/v2/projects/proj-uuid' and r['headers']['authorization'] == 'PrivateToken tok'


def test_connection_check_qase_and_testrail(alone):
    configure(alone, QASE)
    alone.page.click('[data-tmb=test]')
    alone.page.wait_for_function("() => document.querySelector('#tms-body .case-note')?.textContent.includes('Проект найден')")
    assert alone.text('#tms-body .case-note') == 'Проект найден: Демо Qase' and alone.tms.requests[-1]['headers']['token'] == 'qtok'
    configure(alone, TESTRAIL)
    alone.page.click('[data-tmb=test]')
    alone.page.wait_for_function("() => document.querySelector('#tms-body .case-note')?.textContent.includes('Раздел найден')")
    assert alone.text('#tms-body .case-note') == 'Раздел найден: Раздел TestRail'
    assert alone.tms.requests[-1]['headers']['authorization'] == 'Basic ' + base64.b64encode(b'qa@company.ru:trkey').decode()


def test_connection_check_reports_wrong_token(alone):
    alone.tms.deny = 401
    configure(alone, TESTIT)
    alone.page.click('[data-tmb=test]')
    alone.page.wait_for_function("() => document.querySelector('#tms-body .case-note.err')")
    assert 'ответил 401 — проверьте ключ или токен' in alone.text('#tms-body .case-note')


def test_custom_api_cannot_be_checked(alone):
    configure(alone, CUSTOM)
    alone.page.click('[data-tmb=test]')
    alone.page.wait_for_function("() => document.querySelector('#tms-body .case-note')?.textContent.includes('Для своего API')")
    assert alone.tms.requests == []


# ---------- на claude.ai ----------
def test_artifact_explains_that_tms_needs_standalone_version(app):
    app.open_settings('tms')
    app.page.select_option('#tm-kind', 'testit')
    assert 'автономной версии' in app.text('#tms-body') and app.page.is_disabled('[data-tmb=test]')


def test_artifact_does_not_upload_to_external_tms(app):
    app.add_sample()
    app.generate()
    configure(app, TESTIT)
    app.close_settings()
    app.tab('cases')
    app.page.click('[data-act=tms-upload]')
    assert 'На claude.ai страница изолирована от интернета, поэтому загрузка в ТМС работает в автономной версии QA pro.' in log_text(app)
    assert case_marks(app) == {k: None for k in ('API-001', 'API-002', 'UI-001', 'E2E-001')}


# ---------- загрузка: Test IT ----------
def test_testit_upload_sends_a_work_item_per_case(alone):
    upload(alone, TESTIT)
    posts = alone.tms.posts
    assert len(posts) == 4 and {p['path'] for p in posts} == {'/api/v2/workItems'}
    p = next(p for p in posts if p['body']['name'].startswith('[BE] Кейс для P-02'))
    b = p['body']
    assert p['headers']['authorization'] == 'PrivateToken tok'
    assert (b['projectId'], b['entityTypeName'], b['state'], b['priority'], b['duration']) == ('proj-uuid', 'TestCases', 'NotReady', 'High', 600000)
    assert b['steps'] == [{'action': 'Открыть /login', 'expected': 'Открыта страница', 'testData': '', 'comments': ''}]
    assert b['preconditionSteps'] == [{'action': 'Пользователь зарегистрирован', 'expected': '', 'testData': '', 'comments': ''}]
    assert [t['name'] for t in b['tags']] == ['t', 'smoke', 'regression', 'api'] and 'sectionId' not in b


def test_testit_section_state_and_duration_are_sent(alone):
    upload(alone, {**TESTIT, 'section': 'sec-uuid', 'duration': '25'})
    b = alone.tms.posts[0]['body']
    assert b['sectionId'] == 'sec-uuid' and b['duration'] == 25 * 60000


def test_uploaded_cases_are_marked_with_tms_number(alone):
    upload(alone, TESTIT)
    marks = case_marks(alone)
    assert all(v and v[0] == 'testit' and v[1].isdigit() for v in marks.values()) and len(set(v[1] for v in marks.values())) == 4
    assert 'Test IT: загружено 4' in log_text(alone)
    assert alone.page.locator('#case-list article').first.locator('.case-sub').inner_text().count('в ТМС') == 1


def test_uploaded_cases_are_not_sent_twice(alone):
    upload(alone, TESTIT)
    assert alone.page.is_disabled('[data-act=tms-upload]') and 'уже загружено 4' in alone.text('#tms-bar')
    alone.page.click('#tms-reup')
    assert not alone.page.is_disabled('[data-act=tms-upload]') and alone.text('[data-act=tms-upload]') == 'Загрузить в ТМС (4)'
    alone.page.click('[data-act=tms-upload]')
    alone.page.wait_for_function("() => !window.__qa.S.tmsBusy")
    assert len(alone.tms.posts) == 8


def test_upload_follows_case_filters(alone):
    configure(alone, TESTIT)
    alone.close_settings()
    alone.tab('cases')
    alone.page.click('[data-act=ftype][data-t=api]')
    assert alone.text('[data-act=tms-upload]') == 'Загрузить в ТМС (2)'
    alone.page.click('[data-act=tms-upload]')
    alone.page.wait_for_function("() => !window.__qa.S.tmsBusy")
    assert sorted(p['body']['name'][:4] for p in alone.tms.posts) == ['[BE]', '[BE]']
    assert [k for k, v in case_marks(alone).items() if v] == ['API-001', 'API-002']


def test_rejected_case_is_reported_and_others_are_uploaded(alone):
    alone.tms.fail = {'P-04': 400}
    upload(alone, TESTIT)
    assert 'Test IT: загружено 3, с ошибкой 1' in log_text(alone) and 'API-002: Test IT tms.test ответил 400' in log_text(alone)
    assert case_marks(alone)['API-002'] is None and sum(1 for v in case_marks(alone).values() if v) == 3


def test_wrong_token_stops_the_upload(alone):
    alone.tms.deny = 401
    upload(alone, TESTIT)
    assert 'проверьте ключ или токен' in log_text(alone) and len(alone.tms.posts) <= 2
    assert not any(case_marks(alone).values())


def test_upload_marks_are_saved_with_the_run(alone):
    upload(alone, TESTIT)
    run = alone.state('S.run.id')
    path = f'products/{alone.state("S.productId")}/runs/{run}/parts/p0'
    # в автономной версии база — localStorage страницы
    alone.page.wait_for_function("(p) => (JSON.parse(localStorage.getItem('qapro.db:' + p) || '{}').cases || []).every((c) => c.tms)", arg=path, timeout=15000)


def test_obsolete_cases_are_not_uploaded(make_app, tmp_path):
    from tests.support import files
    app = make_app(**standalone())
    connect_ai(app)
    tms = TmsRoute(app)
    app.mode('update')
    app.upload_tests(files.cases_json(tmp_path))
    app.upload(files.spec_file(tmp_path, version='2.0'))
    app.generate()
    upload(app, TESTIT)
    total = app.state('S.run.cases.length')
    assert len(tms.posts) == total - 1 and 'Устаревшие кейсы (1) в ТМС не загружаются' in app.text('#tms-bar')


# ---------- загрузка: Qase, TestRail, свой API ----------
def test_qase_upload_sends_cases_in_one_bulk_request(alone):
    upload(alone, {**QASE, 'section': '12'})
    assert [p['path'] for p in alone.tms.posts] == ['/case/DEMO/bulk']
    b = alone.tms.posts[0]['body']['cases']
    assert len(b) == 4 and b[0]['title'].startswith('[BE]') and b[0]['priority'] == 1 and b[0]['suite_id'] == 12
    assert b[0]['steps'] == [{'action': 'Открыть /login', 'expected_result': 'Открыта страница', 'data': ''}] and b[0]['preconditions'] == 'Пользователь зарегистрирован'
    assert alone.tms.posts[0]['headers']['token'] == 'qtok'
    assert sorted(v[1] for v in case_marks(alone).values()) == ['500', '501', '502', '503'] and 'Qase: загружено 4' in log_text(alone)


def test_qase_bulk_is_split_by_twenty(alone):
    alone.call("(() => { for (let i = 0; i < 21; i++) S.run.cases.push({ ...S.run.cases[0], uid: 'x' + i, dispId: 'API-9' + i }); })()")
    configure(alone, QASE)
    alone.close_settings()
    alone.tab('cases')
    alone.page.click('[data-act=tms-upload]')
    alone.page.wait_for_function("() => !window.__qa.S.tmsBusy")
    assert sorted(len(p['body']['cases']) for p in alone.tms.posts) == [5, 20]


def test_testrail_upload(alone):
    upload(alone, TESTRAIL)
    p = next(p for p in alone.tms.posts if p['body']['title'].startswith('[BE] Кейс для P-02'))
    assert p['path'] == '/index.php?/api/v2/add_case/123' and p['headers']['authorization'] == 'Basic ' + base64.b64encode(b'qa@company.ru:trkey').decode()
    b = p['body']
    assert (b['priority_id'], b['custom_preconds'], b['refs']) == (3, 'Пользователь зарегистрирован', 'R-002')
    assert b['custom_steps_separated'] == [{'content': 'Открыть /login', 'expected': 'Открыта страница'}]
    assert all(v[1].startswith('C7') for v in case_marks(alone).values())


def test_custom_api_gets_one_request_per_case(alone):
    upload(alone, {**CUSTOM, 'headers': '{"X-Project": "QA"}'})
    assert len(alone.tms.posts) == 4
    r = alone.tms.posts[0]
    assert r['headers']['authorization'] == 'Bearer ctok' and r['headers']['x-project'] == 'QA'
    assert r['body']['normalized']['title'] and r['body']['id'] in ('API-001', 'API-002', 'UI-001', 'E2E-001') and r['body']['testCase']['title'] == r['body']['normalized']['title']
    assert all(v[1].startswith('CUS-') for v in case_marks(alone).values())


def test_custom_api_can_get_all_cases_in_one_request(alone):
    upload(alone, {**CUSTOM, 'mode': 'all'})
    assert len(alone.tms.posts) == 1 and len(alone.tms.posts[0]['body']['cases']) == 4 and 'generatedAt' in alone.tms.posts[0]['body']
    assert all(v for v in case_marks(alone).values())
