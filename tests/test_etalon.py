"""Сравнение черновика с эталонными тест-кейсами: выбор кейсов, загрузка эталона, правила по видам тестов, «Добавить» и «Отклонить».

Флоу: генерация (или актуализация) → вкладка «Черновик» → отметить кейсы или взять все → «Сравнить с эталоном» → загрузить эталон
(форматы как у документов) → «Сравнить с эталоном» → список правил по видам API, UI, E2E → «Добавить» дописывает правило в
«Особенности оформления» шаблона этого вида и сохраняет (для команды, в источник контекста или только у себя).
"""
import json
import os

import pytest

from tests.support import files

HERE = os.path.dirname(os.path.abspath(__file__))
ETALON = """# Эталонные тест-кейсы команды

## UI-ЭТ-1. Восстановление пароля: ошибка формата email
Предусловия: пользователь с ролью «Клиент» не авторизован, открыта страница /login.
1. Нажать «Забыли пароль?» — открыт экран «Восстановление пароля».
2. Ввести userexample.ru, нажать «Отправить ссылку» — под полем текст «Введите корректный email».

## API-ЭТ-1. POST /api/v1/password-reset — 400 INVALID_EMAIL
1. Отправить {"email": "bad"} — 400, тело {"code": "INVALID_EMAIL", "message": "Некорректный email"}.
"""


def write_etalon(tmp_path, name='эталон.md', text=ETALON):
    p = tmp_path / name
    p.write_text(text, encoding='utf-8')
    return str(p)


@pytest.fixture
def drafted(app):
    app.add_sample()
    app.generate()
    app.tab('draft')
    return app


def open_dialog(app):
    app.page.click('[data-act=etalon-open]')
    app.page.wait_for_selector('#etalon-ov:not([hidden]) #etalon-body')
    return app


def load(app, *paths):
    app.page.set_input_files('#etalon-file', list(paths))
    app.page.wait_for_function('() => window.__qa.S.etalon.files.length && window.__qa.S.etalon.files.every((f) => f.status !== "parsing")', timeout=20000)


def compare(app):
    app.page.click('[data-eact=run]')
    app.page.wait_for_function('() => !window.__qa.S.etalon.busy && window.__qa.S.etalon.view === "result"', timeout=30000)


@pytest.fixture
def compared(drafted, tmp_path):
    open_dialog(drafted)
    load(drafted, write_etalon(tmp_path))
    compare(drafted)
    return drafted


def rules(app):
    return app.state('S.run.etalon.rules.map((x) => ({ type: x.type, text: x.text, status: x.status }))')


# ---------- кнопка и выбор кейсов ----------
def test_draft_has_compare_button(drafted):
    assert 'Сравнить с эталоном' in drafted.text('#tab-body .draft-acts')


def test_button_counts_selected_cases(drafted):
    uid = drafted.state('S.run.cases.find((c) => c.type === "ui").uid')
    drafted.page.check(f'.case-sel[data-uid="{uid}"]')
    assert 'Сравнить с эталоном (1)' in drafted.text('#tab-body .draft-acts')


def test_dialog_takes_all_cases_when_nothing_is_selected(drafted):
    open_dialog(drafted)
    n = drafted.state('S.run.cases.length')
    assert drafted.state('S.etalon.uids.length') == n
    assert f'все {n}' in drafted.text('#etalon-body')


def test_dialog_takes_only_selected_cases(drafted):
    ui = drafted.state('S.run.cases.filter((c) => c.type === "ui").map((c) => c.uid)')
    for u in ui:
        drafted.page.check(f'.case-sel[data-uid="{u}"]')
    open_dialog(drafted)
    assert sorted(drafted.state('S.etalon.uids')) == sorted(ui)
    assert 'выбранные' in drafted.text('#etalon-body') and 'UI' in drafted.text('#etalon-body') and 'API' not in drafted.text('#etalon-body .hint')


# ---------- загрузка эталона ----------
def test_upload_accepts_document_formats(drafted):
    open_dialog(drafted)
    accept = drafted.page.get_attribute('#etalon-file', 'accept')
    assert accept == drafted.page.get_attribute('#file-input', 'accept')


def test_compare_is_disabled_until_a_file_is_loaded(drafted, tmp_path):
    open_dialog(drafted)
    assert drafted.page.is_disabled('[data-eact=run]')
    load(drafted, write_etalon(tmp_path))
    assert drafted.page.is_enabled('[data-eact=run]') and 'эталон.md' in drafted.text('#etalon-body .et-files')


def test_unreadable_file_is_reported_and_can_be_removed(drafted, tmp_path):
    open_dialog(drafted)
    bad = tmp_path / 'старый.doc'
    bad.write_bytes(b'\xd0\xcf')
    load(drafted, str(bad))
    assert 'не поддерживается' in drafted.text('#etalon-body .et-files') and drafted.page.is_disabled('[data-eact=run]')
    drafted.page.click('[data-eact=drop]')
    assert drafted.count('#etalon-body .et-files li') == 0


@pytest.mark.needs_libs
def test_etalon_from_xlsx(drafted, tmp_path):
    open_dialog(drafted)
    load(drafted, files.cases_xlsx(tmp_path))
    compare(drafted)
    etalon = '\n'.join(drafted.model.prompts_of('promptEtalon'))
    assert 'cases.xlsx' in etalon and len(drafted.state('S.run.etalon.rules')) > 0


# ---------- сравнение ----------
def test_one_request_per_test_type(compared):
    prompts = compared.model.prompts_of('promptEtalon')
    types = compared.state('[...new Set(S.run.cases.map((c) => c.type))]')
    assert len(prompts) == len(types) == 3
    assert [('вида API' in p, 'вида UI' in p, 'вида E2E' in p) for p in prompts] == [(True, False, False), (False, True, False), (False, False, True)]


def test_request_has_etalon_cases_of_its_type_and_current_rules(compared):
    ui = next(p for p in compared.model.prompts_of('promptEtalon') if 'вида UI' in p)
    ui_ids = compared.state('S.run.cases.filter((c) => c.type === "ui").map((c) => c.dispId)')
    api_ids = compared.state('S.run.cases.filter((c) => c.type === "api").map((c) => c.dispId)')
    assert all(f'"id":"{i}"' in ui for i in ui_ids) and not any(f'"id":"{i}"' in ui for i in api_ids)
    assert 'UI-ЭТ-1' in ui and 'Файл «эталон.md»' in ui
    assert 'Названия элементов — как в интерфейсе' in ui   # действующие правила оформления UI — чтобы не предлагать повторы


def test_only_selected_cases_are_compared(drafted, tmp_path):
    uid = drafted.state('S.run.cases.find((c) => c.type === "api").uid')
    drafted.page.check(f'.case-sel[data-uid="{uid}"]')
    open_dialog(drafted)
    load(drafted, write_etalon(tmp_path))
    compare(drafted)
    prompts = drafted.model.prompts_of('promptEtalon')
    assert len(prompts) == 1 and 'вида API' in prompts[0]
    assert {r['type'] for r in rules(drafted)} == {'api'}


def test_rules_are_grouped_by_type_without_existing_ones(compared):
    rs = rules(compared)
    assert [r['type'] for r in rs] == ['api', 'api', 'ui', 'ui', 'e2e', 'e2e']
    assert not any(r['text'].startswith('Один тест-кейс проверяет один эндпоинт') for r in rs)   # уже есть в шаблоне API
    body = compared.text('#etalon-body')
    assert 'API · ' in body and 'UI · ' in body and 'E2E · ' in body and 'Эталон UI конкретнее' in body
    assert compared.count('#etalon-body [data-eact=add]') == 6 and compared.count('#etalon-body [data-eact=reject]') == 6


def test_long_etalon_is_cut_to_relevant_fragments(app):
    noise = '\n\n'.join(f'Раздел {i}: про платежи и карты, не про пароль.' * 20 for i in range(200))
    text = noise + '\n\nВосстановление пароля: письмо со ссылкой приходит за минуту.\n\n' + noise
    r = app.call('a.etalonFit(arg, "восстановление пароля письмо ссылка", 5000)', text)
    assert r['cut'] and len(r['text']) <= 5000 and 'письмо со ссылкой приходит за минуту' in r['text']


def test_model_error_is_shown_and_can_be_retried(drafted, tmp_path):
    from tests.support.model import ModelError
    drafted.model.on('promptEtalon', ModelError('overloaded', 'Модель перегружена'))
    open_dialog(drafted)
    load(drafted, write_etalon(tmp_path))
    drafted.page.click('[data-eact=run]')
    drafted.page.wait_for_function('() => !window.__qa.S.etalon.busy && !!window.__qa.S.etalon.error', timeout=30000)
    assert 'Не удалось сравнить' in drafted.text('#etalon-body') and drafted.state('S.run.etalon') is None
    from tests.support.model import DEFAULTS
    drafted.model.on('promptEtalon', DEFAULTS['promptEtalon'])
    compare(drafted)
    assert len(rules(drafted)) == 6


# ---------- «Добавить» и «Отклонить» ----------
def add_first(app, t):
    rid = app.state(f'S.run.etalon.rules.find((x) => x.type === "{t}").id')
    app.page.click(f'#et-{rid} [data-eact=add]')
    app.page.wait_for_function(f'(id) => window.__qa.S.run.etalon.rules.find((x) => x.id === id).status === "added"', arg=rid)
    return app.state(f'S.run.etalon.rules.find((x) => x.id === "{rid}").text')


def test_add_appends_rule_to_its_type_template_and_saves_for_team(compared):
    before = compared.state('S.cfg.tpl.ui.rules')
    text = add_first(compared, 'ui')
    assert compared.state('S.cfg.tpl.ui.rules') == before.rstrip() + '\n- ' + text
    assert text not in compared.state('S.cfg.tpl.api.rules') and text not in compared.state('S.cfg.tpl.e2e.rules')
    compared.page.wait_for_function('(t) => (window.__qa.S.cfgTeam.ui?.value?.rules || "").includes(t)', arg=text)
    saved = compared.db.store.get('config/tpl_ui')
    assert saved and saved['rules'].endswith('- ' + text) and compared.state('S.cfgDirty.ui') is False
    assert 'добавлено в правила UI' in compared.text('#etalon-body')


def test_added_rule_reaches_next_generation(compared):
    text = add_first(compared, 'api')
    compared.page.evaluate("() => document.querySelector('#etalon-ov [data-close]').click()")
    compared.model.reset()
    compared.page.click('#tab-agent')
    compared.generate()
    api = [c.prompt for c in compared.model.calls_of('promptGenerate') if 'вида API' in c.prompt]
    assert api and all(text in p for p in api)
    assert not any(text in c.prompt for c in compared.model.calls_of('promptGenerate') if 'вида UI' in c.prompt)


def test_reject_leaves_rules_unchanged(compared):
    before = compared.state('S.cfg.tpl')
    rid = compared.state('S.run.etalon.rules.find((x) => x.type === "e2e").id')
    compared.page.click(f'#et-{rid} [data-eact=reject]')
    assert compared.state(f'S.run.etalon.rules.find((x) => x.id === "{rid}").status') == 'rejected'
    assert compared.state('S.cfg.tpl') == before and 'отклонено' in compared.text(f'#et-{rid}')


def test_decision_is_final_for_the_rule(compared):
    rid = compared.state('S.run.etalon.rules[0].id')
    compared.page.click(f'#et-{rid} [data-eact=reject]')
    assert compared.count(f'#et-{rid} [data-eact]') == 0
    compared.call(f'a.etalonDecide("{rid}", true)')
    assert compared.state(f'S.run.etalon.rules.find((x) => x.id === "{rid}").status') == 'rejected'


def test_adding_same_rule_twice_does_not_duplicate(compared):
    text = add_first(compared, 'ui')
    other = compared.state('S.run.etalon.rules.find((x) => x.type === "ui" && x.status === "new").id')
    compared.call(f'(S.run.etalon.rules.find((x) => x.id === "{other}").text = {json.dumps(text)}, a.etalonDecide("{other}", true))')
    n = compared.state(f'S.cfg.tpl.ui.rules.split("\\n").filter((l) => l.includes({json.dumps(text)})).length')
    assert n == 1


def test_without_edit_rights_rule_stays_local(make_app, tmp_path):
    app = make_app(init="window.__noEdit = true;")
    app.call('(S.caps.canEdit = false, true)')
    app.add_sample()
    app.generate()
    app.tab('draft')
    open_dialog(app)
    load(app, write_etalon(tmp_path))
    compare(app)
    text = add_first(app, 'ui')
    assert text in app.state('S.cfg.tpl.ui.rules') and app.state('S.cfgDirty.ui') is True
    assert app.db.store.get('config/tpl_ui') is None
    assert any('только у вас' in t for t in app.toast_texts())


# ---------- результат сохраняется ----------
def test_result_survives_reload_and_reopens(compared):
    compared.page.wait_for_timeout(2000)
    compared.reload()
    compared.page.wait_for_function('() => !!(window.__qa.S.run && window.__qa.S.run.etalon)', timeout=15000)
    compared.tab('draft')
    assert 'Правила из эталона · ждут решения 6' in compared.text('#tab-body .draft-acts')
    compared.page.click('[data-act=etalon-result]')
    compared.page.wait_for_selector('#etalon-body .et-rule')
    assert compared.count('#etalon-body .et-rule') == 6


def test_new_comparison_from_result(compared, tmp_path):
    compared.page.click('[data-eact=again]')
    assert compared.count('#etalon-body [data-eact=run]') == 1 and 'эталон.md' in compared.text('#etalon-body')


# ---------- актуализация ----------
def test_works_in_update_mode(app, tmp_path):
    app.mode('update')
    app.upload_tests(files.cases_json(tmp_path))
    app.upload(files.spec_file(tmp_path, version='2.0', link_minutes=60, limit=5, timer=False))
    app.generate()
    app.tab('draft')
    open_dialog(app)
    load(app, write_etalon(tmp_path))
    compare(app)
    assert app.state('S.run.mode') == 'update' and len(app.state('S.run.etalon.rules')) > 0


# ---------- источник контекста: правило пишется в templates/<вид>.md ----------
def test_with_context_source_rule_goes_to_template_file(make_app, tmp_path):
    from tests.test_context_source import connect, init, wait_repo
    app = connect(make_app(init=init()))
    app.close_settings()
    app.add_sample()
    app.generate()
    app.tab('draft')
    open_dialog(app)
    load(app, write_etalon(tmp_path))
    compare(app)
    assert 'источнике контекста' in app.text('#etalon-body')
    text = add_first(app, 'ui')
    assert '- ' + text in wait_repo(app, 'templates/ui.md', text)
    assert app.db.store.get('config/tpl_ui') is None
