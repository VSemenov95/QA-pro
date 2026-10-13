"""Шаг вызова API: «Вызвать МЕТОД ЭНДПОИНТ с телом:» и блок кода с телом."""


def test_rule_is_in_generation_prompt(app):
    app.add_sample()
    app.generate()
    p = app.model.prompts_of('promptGenerate')[0]
    assert 'Вызвать МЕТОД ЭНДПОИНТ с телом:' in p and 'блок кода с телом запроса' in p


def test_api_example_uses_the_call_form(app):
    action = app.state("a.tplInfo('api').structure.steps[0].action")
    assert action.startswith('Вызвать POST /api/v1/password-reset с телом:')
    assert '```json' in action


def test_service_state_rule_is_in_generation_prompt(app):
    app.add_sample()
    app.generate()
    assert 'Не пиши в шагах и предусловиях, что сервис или потребитель запущен' in app.model.prompts_of('promptGenerate')[0]
