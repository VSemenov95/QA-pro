"""Swagger / OpenAPI как документ: выбираются эндпоинты по полю «API», дальше — все правила генерации."""
import pytest

from tests.support import files


def doc_of(app, name):
    return app.state(f"S.docs.find((d) => d.name === '{name}')")


def set_filter(app, value):
    """Поле «API» активно после загрузки спецификации; код пересчитывает текст и пишет итог в подсказку поля."""
    app.page.fill('#api-filter', value)
    app.page.dispatch_event('#api-filter', 'input')
    app.page.wait_for_function("() => /Фильтр (применён|применится)/.test(document.querySelector('#api-hint').textContent)", timeout=10000)


def test_api_field_is_always_active(app, tmp_path):
    assert not app.page.is_disabled('#api-filter')
    app.upload(files.openapi_spec(tmp_path))
    assert not app.page.is_disabled('#api-filter')


def test_only_the_named_api_goes_into_the_document(app, tmp_path):
    app.upload(files.openapi_spec(tmp_path))
    set_filter(app, 'password-reset')
    d = doc_of(app, 'auth-api.json')
    assert d['status'] == 'ready', d
    assert '## POST /api/v1/password-reset' in d['text'] and '/api/v1/users' not in d['text']
    assert 'email (string, обязательное' in d['text']


def test_parameters_bodies_and_responses_are_described(app, tmp_path):
    app.upload(files.openapi_spec(tmp_path))
    set_filter(app, 'password-reset')
    text = doc_of(app, 'auth-api.json')['text']
    assert 'Тело запроса (application/json):' in text
    assert 'обязательное' in text and 'Email, указанный при регистрации' in text
    assert '- 202 — Ссылка отправлена' in text and '- 400 — Неверный формат email' in text
    assert 'INVALID_EMAIL' in text and 'Базовый адрес: https://api.example.ru' in text


def test_empty_field_takes_every_endpoint_with_a_warning(app, tmp_path):
    app.upload(files.openapi_spec(tmp_path))
    d = doc_of(app, 'auth-api.json')
    assert d['status'] == 'ready' and '/api/v1/users/{id}' in d['text'] and '/api/v1/password-reset' in d['text']
    assert 'Поле «API» не заполнено' in d['warn']


def test_no_matching_endpoint_is_an_error(app, tmp_path):
    app.upload(files.openapi_spec(tmp_path))
    set_filter(app, 'payments')
    d = doc_of(app, 'auth-api.json')
    assert d['status'] == 'error' and 'нет эндпоинтов, подходящих под «payments»' in d['error']


def test_several_values_separated_by_comma(app, tmp_path):
    app.upload(files.openapi_spec(tmp_path))
    set_filter(app, 'users, reset')
    text = doc_of(app, 'auth-api.json')['text']
    assert '## POST /api/v1/password-reset' in text and '## GET /api/v1/users/{id}' in text


@pytest.mark.needs_libs
def test_yaml_spec_is_read(app, tmp_path):
    app.upload(files.openapi_spec(tmp_path, yaml=True))
    set_filter(app, 'password-reset')
    d = doc_of(app, 'auth-api.yaml')
    assert d['status'] == 'ready' and '## POST /api/v1/password-reset' in d['text']


def test_json_that_is_not_a_spec_is_a_plain_document(app, tmp_path):
    p = files.write(tmp_path / 'data.json', '{"hello": "мир"}')
    app.upload(p)
    d = doc_of(app, 'data.json')
    assert d['status'] == 'ready' and 'hello' in d['text']
    assert not app.page.is_disabled('#api-filter')


def test_generation_applies_the_same_rules_to_spec_documents(app, tmp_path):
    """Спецификация — обычный документ: анализ видит эндпоинты, в генерации работают те же правила."""
    app.upload(files.openapi_spec(tmp_path))
    set_filter(app, 'password-reset')
    app.add_sample()
    app.generate()
    analyze = app.model.prompts_of('promptAnalyze')
    assert analyze and any('## POST /api/v1/password-reset' in p for p in analyze)
    gen = app.model.prompts_of('promptGenerate')[0]
    assert 'Приоритет указывай только одним из четырёх значений' in gen and 'Сообщение в Kafka описывай без метода' in gen


def test_api_field_stays_on_after_reload(app, tmp_path):
    """Регрессия: поле «API» выключалось само, пока спецификация подгружалась из базы после перезагрузки."""
    app.upload(files.openapi_spec(tmp_path))
    app.reload()
    assert not app.page.is_disabled('#api-filter')
