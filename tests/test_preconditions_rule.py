"""В предусловиях не пишем, что сервис работает: это подразумевается."""


def test_rule_is_in_generation_prompt(app):
    app.add_sample()
    app.generate()
    assert 'В предусловиях не пиши, что сервис' in app.model.prompts_of('promptGenerate')[0]


def test_rule_is_in_actualization_prompt(app, tmp_path):
    from tests.support import files
    app.mode('update')
    app.upload_tests(files.cases_json(tmp_path))
    app.upload(files.spec_file(tmp_path))
    app.generate()
    assert 'В предусловиях не пиши, что сервис' in app.model.prompts_of('promptActualize')[0]


API_PRE = 'создавай в предусловиях через API'


def test_ui_and_e2e_preconditions_go_through_api(app):
    """UI и E2E: данные и объекты для кейса создаются в предусловиях вызовами API; кейсам API правило не нужно."""
    app.add_sample()
    app.generate()
    seen = set()
    for p in app.model.prompts_of('promptGenerate'):
        head = p.split('\n', 1)[0]
        kind = next(t for t in ('API', 'UI', 'E2E') if f'вида {t}' in head)
        seen.add(kind)
        if kind == 'API':
            assert API_PRE not in p
        else:
            assert API_PRE in p and 'не выдумывай их' in p
    assert {'UI', 'E2E'} & seen


def test_api_preconditions_rule_in_refine_prompt(app):
    app.add_sample()
    app.generate()
    uid = app.call("a.S.run.cases.find((c) => c.type === 'ui' || c.type === 'e2e')?.uid")
    assert uid
    p = app.call(f"a.promptRefine(a.S.run, a.S.run.cases.find((c) => c.uid === {uid!r}), 'добавь проверку')")
    assert API_PRE in p
