"""Актуализация: файл с кейсами сверяется с новой версией ТЗ, кейсы переписываются по шаблонам."""
import pytest

from tests.support import files
from tests.support.model import Call, src_blocks


@pytest.fixture
def upd(app, tmp_path):
    """Актуализация на тестовых файлах: ТЗ новой версии + 8 кейсов (3 API, 4 UI, 1 E2E)."""
    app.mode('update')
    app.upload_tests(files.cases_json(tmp_path))
    app.upload(files.spec_file(tmp_path, version='2.0', link_minutes=60, limit=5, timer=False))
    return app


def run_update(app):
    app.generate()
    return app


# ---------- сопоставление ответов модели с кейсами пакета (ошибка «Модель вернула не все кейсы») ----------
def match(app, items, answers):
    return app.call('a.matchBatch(arg.items, arg.answers).map((x) => x && x.index)', {'items': items, 'answers': answers})


def test_match_by_header_number(app):
    items = [{'index': 11}, {'index': 12}, {'index': 13}]
    assert match(app, items, [{'index': 13}, {'index': 11}, {'index': 12}]) == [11, 12, 13]


def test_match_when_model_renumbers_from_one(app):
    """Модель вернула 1..N вместо номеров из заголовков (11..13) — ответы всё равно находят свои кейсы."""
    items = [{'index': 11}, {'index': 12}, {'index': 13}]
    assert match(app, items, [{'index': 1}, {'index': 2}, {'index': 3}]) == [1, 2, 3]


def test_match_by_position_when_numbers_are_missing(app):
    items = [{'index': 21}, {'index': 22}]
    got = app.call('a.matchBatch(arg.items, arg.answers).map((x) => x && x.tag)', {'items': items, 'answers': [{'tag': 'a'}, {'tag': 'b'}]})
    assert got == ['a', 'b']


def test_match_gives_each_answer_to_one_case_only(app):
    items = [{'index': 5}, {'index': 6}]
    got = app.call('a.matchBatch(arg.items, arg.answers).map((x) => x && x.tag)', {'items': items, 'answers': [{'index': 5, 'tag': 'a'}, {'index': 5, 'tag': 'dup'}]})
    assert got == ['a', None]


def test_match_missing_answers_stay_empty(app):
    items = [{'index': 1}, {'index': 2}, {'index': 3}]
    assert match(app, items, [{'index': 2}]) == [None, 2, None]


def test_match_ignores_garbage(app):
    assert match(app, [{'index': 1}], [None, 'x', 5, {'index': 1}]) == [1]


# ---------- сквозная актуализация ----------
def test_file_is_parsed(upd):
    f = upd.state('[S.upd.file.status, S.upd.file.cases.length]')
    assert f == ['ready', 8]


def test_all_cases_are_processed_and_statuses_follow_the_model(upd):
    run_update(upd)
    assert upd.state('S.run.status') == 'done', upd.state('S.run.error')
    assert upd.state('S.run.failed.length') == 0
    cases = upd.state("S.run.cases.filter((c) => c.sourceId).map((c) => [c.sourceId, c.status])")
    assert len(cases) == 8
    st = dict(cases)
    assert st['UI-001'] == 'changed' and st['UI-002'] == 'obsolete'
    assert all(v == 'same' for k, v in st.items() if k not in ('UI-001', 'UI-002'))


def test_changed_case_keeps_the_reason(upd):
    run_update(upd)
    ch = upd.state("S.run.cases.find((c) => c.sourceId === 'UI-001')")
    assert ch['status'] == 'changed' and ch['changes'] and 'Введите корректный email' in ch['changes'][0]
    assert 'текст ошибки' in ch['note']


def test_source_ids_are_kept(upd):
    run_update(upd)
    ids = set(upd.state("S.run.cases.filter((c) => c.sourceId).map((c) => c.dispId)"))
    assert {'API-001', 'UI-001', 'E2E-001'} <= ids


def test_title_tags_are_added_to_rewritten_cases(upd):
    run_update(upd)
    for ty, title in upd.state("S.run.cases.filter((c) => c.sourceId).map((c) => [c.type, a.pickTitleText(c.testCase)])"):
        assert title.startswith({'api': '[BE]', 'ui': '[FE]', 'e2e': '[E2E]'}[ty] + ' '), (ty, title)


def test_new_requirements_get_new_cases(upd):
    run_update(upd)
    assert upd.state("S.run.cases.filter((c) => c.status === 'new').length") > 0
    assert upd.model.calls_of('promptGenerate')


def renumbering_map(call: Call):
    """Ответ «с единицы»: модель в каждом пакете нумерует кейсы заново, не как в заголовках «### #N»."""
    nums = [i for i, _ in src_blocks(call.prompt)]
    return {'cases': [{'index': k + 1, 'type': 'ui', 'requirementIds': ['R-001'], 'status': 'same', 'reason': 'ок', 'instruction': ''} for k, _ in enumerate(nums)]}


def renumbering_actualize(call: Call):
    nums = [i for i, _ in src_blocks(call.prompt)]
    return {'cases': [{'index': k + 1, 'suites': ['regression'], 'changes': [], 'testCase': {'title': f'Кейс {k + 1}', 'id': '', 'priority': 'High', 'steps': [{'step': 1, 'action': 'a', 'expected': 'b'}]}} for k, _ in enumerate(nums)]}


def test_renumbered_answers_do_not_drop_batches(app, tmp_path):
    """Регрессия: модель нумеровала кейсы с единицы, и приложение отбрасывало пакеты («Модель вернула не все кейсы»)."""
    app.model.on('promptMap', renumbering_map).on('promptActualize', renumbering_actualize)
    app.mode('update')
    app.upload_tests(files.cases_json(tmp_path, n_api=12, n_ui=12, n_e2e=2))
    app.upload(files.spec_file(tmp_path, version='2.0'))
    app.generate()
    assert app.state('S.run.failed.length') == 0, app.state('S.run.failed')
    assert app.state("S.run.cases.filter((c) => c.sourceId).length") == 26
    assert app.state('S.run.steps.map.status') == 'done'


def test_prompts_ask_for_header_numbers(upd):
    run_update(upd)
    for kind in ('promptMap', 'promptActualize'):
        p = upd.model.prompts_of(kind)[0]
        assert 'номер кейса из заголовка' in p or 'номер из заголовка' in p, kind


def test_documents_beat_the_knowledge_base_rule_is_in_map_prompt(upd):
    run_update(upd)
    assert 'приоритет у документов' in upd.model.prompts_of('promptMap')[0]


def test_batches_are_ten_cases_at_most(app, tmp_path):
    app.mode('update')
    app.upload_tests(files.cases_json(tmp_path, n_api=12, n_ui=12, n_e2e=1))
    app.upload(files.spec_file(tmp_path))
    app.generate()
    sizes = [len(src_blocks(p)) for p in app.model.prompts_of('promptMap')]
    assert sum(sizes) == 25 and max(sizes) <= 10


# ---------- плохие файлы ----------
def test_invalid_json_is_rejected_with_message(app, tmp_path):
    app.mode('update')
    bad = files.write(tmp_path / 'bad.json', '{"cases": [')
    app.upload_tests(bad)
    assert app.state('S.upd.file.status') == 'error'
    assert 'JSON' in app.state('S.upd.file.error')


def test_wrong_extension_is_rejected(app, tmp_path):
    app.mode('update')
    app.page.evaluate("() => { const dt = new DataTransfer(); dt.items.add(new File(['x'], 'cases.txt')); const i = document.querySelector('#upd-input'); i.files = dt.files; i.dispatchEvent(new Event('change', { bubbles: true })); }")
    app.page.wait_for_function("() => window.__qa.S.upd.file && window.__qa.S.upd.file.status !== 'parsing'")
    assert app.state('S.upd.file.status') == 'error' and '.xlsx' in app.state('S.upd.file.error')


def test_json_without_cases_is_rejected(app, tmp_path):
    app.mode('update')
    app.upload_tests(files.write(tmp_path / 'empty.json', '{"a": 1}'))
    assert app.state('S.upd.file.status') == 'error'


@pytest.mark.needs_libs
def test_xlsx_with_multirow_cases(app, tmp_path):
    app.mode('update')
    app.upload_tests(files.cases_xlsx(tmp_path, n=4))
    assert app.state('[S.upd.file.status, S.upd.file.cases.length]') == ['ready', 4]
