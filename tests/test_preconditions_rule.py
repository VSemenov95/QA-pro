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
