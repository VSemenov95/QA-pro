"""Правило: сообщение в Kafka описывается без метода (POST, PUT, «методом…») — везде, не только в блоке кода."""
from tests.support import files

RULE = 'Сообщение в Kafka описывай без метода'


def test_rule_is_in_generation_prompt(app):
    app.add_sample()
    app.generate()
    p = app.model.prompts_of('promptGenerate')[0]
    assert RULE in p and 'в блоке кода' in p


def test_rule_is_in_actualization_prompt(app, tmp_path):
    app.mode('update')
    app.upload_tests(files.cases_json(tmp_path))
    app.upload(files.spec_file(tmp_path))
    app.generate()
    assert RULE in app.model.prompts_of('promptActualize')[0]
