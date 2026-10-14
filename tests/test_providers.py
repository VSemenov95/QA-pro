"""Подключение к ИИ (шестерёнка → Модель): карточки провайдеров, ключи, проверка подключения, сохранение, выбор для генерации и ревью.
Подключения по ключу работают только в автономной версии; в артефакте claude.ai страница изолирована от интернета, там только аккаунт Claude."""
import pytest

from tests.support.api_gateway import Gateway

CARDS = "[...document.querySelectorAll('#prov-list .prov')].map((e) => [e.querySelector('b').textContent, e.classList.contains('on'), e.querySelector('.prov-st').textContent])"
CHECK_DONE = "() => { const n = document.querySelector('#prov-test-note'); return !!n && n.textContent !== 'Проверяю…'; }"
HOST = {'claude': 'api.anthropic.com', 'openai': 'api.openai.com', 'innocode': 'chat.aicenter.inno.tech'}
STORED = "JSON.parse(localStorage.getItem('qapro.conns') || '[]').map((c) => [c.id, c.model, c.baseUrl, c.apiKey])"
SETTINGS = "JSON.parse(localStorage.getItem('tca.settings'))"


@pytest.fixture
def sa(make_app):
    """Автономная версия без подключений; запросы к провайдерам перехватывает app.gw."""
    app = make_app(kind='standalone')
    app.gw = Gateway(app)
    app.open_settings('model')
    return app


def select(app, pid):
    app.page.click(f'#prov-list [data-prov={pid}] .prov-h')


def set_key(app, pid, key):
    select(app, pid)
    app.page.fill(f'#pk-{pid}', key)


def check(app, pid):
    app.page.click(f'[data-prov-test={pid}]')
    app.page.wait_for_function(CHECK_DONE, timeout=15000)
    return app.text('#prov-test-note')


# ---------- до настройки ----------
def test_run_note_asks_for_key(make_app):
    app = make_app(kind='standalone')
    assert 'укажите ключ API Claude, ChatGPT или Иннокода' in app.text('#run-note')
    assert 'err' in app.page.get_attribute('#run-note', 'class')


def test_three_cards_in_order_all_need_key(sa):
    assert [(c[0], c[2]) for c in sa.page.evaluate('() => ' + CARDS)] == [('Аккаунт Claude', 'Нужен ключ'), ('ChatGPT (OpenAI)', 'Нужен ключ'), ('Иннокод', 'Нужен ключ')]


def test_claude_card_is_selected_and_asks_for_api_key(sa):
    assert [c[1] for c in sa.page.evaluate('() => ' + CARDS)] == [True, False, False]
    assert sa.visible('#pk-claude') and sa.page.input_value('#pm-claude') == 'claude-opus-5-5'
    assert 'Anthropic не разрешает' in sa.text('#prov-list [data-prov=claude]')


def test_hint_in_settings_asks_for_key(sa):
    assert sa.visible('#ai-hint') and 'ключ API' in sa.text('#ai-hint')


def test_hint_names_selected_provider(sa):
    select(sa, 'openai')
    assert sa.text('#ai-hint') == 'Укажите ключ API для подключения «ChatGPT (OpenAI)»: шестерёнка → Модель.'


# ---------- выбор провайдера ----------
@pytest.mark.parametrize('pid,model', [('claude', 'claude-opus-5-5'), ('openai', 'gpt-5.5'), ('innocode', 'qwen')])
def test_select_provider(sa, pid, model):
    if pid == 'claude':
        select(sa, 'openai')   # карточка Claude выбрана с самого начала
    select(sa, pid)
    assert sa.state('S.settings.genAI') == f'conn:p-{pid}'
    assert [c[1] for c in sa.page.evaluate('() => ' + CARDS)] == [p == pid for p in ('claude', 'openai', 'innocode')]
    assert sa.page.input_value(f'#pm-{pid}') == model


def test_only_innocode_has_address_field(sa):
    select(sa, 'openai')
    assert sa.count('#pu-openai') == 0
    select(sa, 'innocode')
    assert sa.page.input_value('#pu-innocode') == 'https://chat.aicenter.inno.tech/v1'


def test_check_button_is_disabled_without_key(sa):
    select(sa, 'openai')
    assert sa.page.is_disabled('[data-prov-test=openai]')


def test_key_marks_provider_ready(sa):
    set_key(sa, 'openai', 'sk-test')
    assert sa.text('#prov-st-openai') == 'Ключ указан' and not sa.page.is_disabled('[data-prov-test=openai]')
    assert sa.page.is_hidden('#ai-hint')


def test_typing_key_does_not_lose_focus(sa):
    set_key(sa, 'openai', 'sk-test')
    assert sa.state('document.activeElement.id') == 'pk-openai'
    sa.page.keyboard.type('-more')
    assert sa.page.input_value('#pk-openai') == 'sk-test-more'


def test_key_and_model_are_stored_in_browser_only(sa):
    set_key(sa, 'openai', 'sk-test')
    sa.page.fill('#pm-openai', 'gpt-5.5-mini')
    assert sa.call(STORED) == [['p-openai', 'gpt-5.5-mini', 'https://api.openai.com/v1', 'sk-test']]


def test_empty_model_returns_default(sa):
    set_key(sa, 'openai', 'sk-test')
    sa.page.fill('#pm-openai', 'gpt-x')
    sa.page.fill('#pm-openai', '')
    assert sa.call(STORED)[0][1] == 'gpt-5.5'


def test_review_choices_list_only_providers_with_key(sa):
    options = lambda: sa.page.eval_on_selector_all('#review-ai option', 'os => os.map((o) => o.textContent)')   # noqa: E731
    assert options() == ['Тот же, что для генерации']
    set_key(sa, 'openai', 'sk-test')
    set_key(sa, 'innocode', 'inno-key')
    assert options() == ['Тот же, что для генерации', 'ChatGPT (OpenAI) · gpt-5.5', 'Иннокод · qwen']


def test_all_cards_ready_after_all_keys(sa):
    for pid, key in (('openai', 'sk-1'), ('innocode', 'inno'), ('claude', 'sk-ant-x')):
        set_key(sa, pid, key)
    select(sa, 'innocode')
    assert sa.page.evaluate('() => ' + CARDS) == [['Аккаунт Claude', False, 'Ключ указан'], ['ChatGPT (OpenAI)', False, 'Ключ указан'], ['Иннокод', True, 'Ключ указан']]


def test_run_note_names_selected_provider(sa):
    set_key(sa, 'innocode', 'inno-key')
    sa.close_settings()
    assert 'уходят в «Иннокод»' in sa.text('#run-note') and 'err' not in sa.page.get_attribute('#run-note', 'class')


def test_status_pill_names_provider_after_reload(sa):
    set_key(sa, 'innocode', 'inno-key')
    sa.reload()
    assert sa.text('#st-claude') == 'Автономная версия · Иннокод'


def test_status_pill_follows_selection(sa):
    set_key(sa, 'innocode', 'inno-key')
    assert sa.text('#st-claude') == 'Автономная версия · Иннокод'


# ---------- проверка подключения ----------
def test_check_openai(sa):
    set_key(sa, 'openai', 'sk-test')
    assert 'Связь есть, модель отвечает' in check(sa, 'openai')
    r = sa.gw.to(HOST['openai'])[-1]
    assert r.url == 'https://api.openai.com/v1/chat/completions' and r.headers['authorization'] == 'Bearer sk-test'
    assert r.body['model'] == 'gpt-5.5' and 'temperature' not in r.body


def test_check_innocode(sa):
    set_key(sa, 'innocode', 'inno-key')
    check(sa, 'innocode')
    r = sa.gw.to(HOST['innocode'])[-1]
    assert r.url == 'https://chat.aicenter.inno.tech/v1/chat/completions' and r.headers['authorization'] == 'Bearer inno-key'
    assert r.body['model'] == 'qwen' and r.body['temperature'] == 0.2


def test_check_innocode_uses_edited_address(sa):
    set_key(sa, 'innocode', 'inno-key')
    sa.page.fill('#pu-innocode', 'https://chat.aicenter.inno.tech/v2/')
    check(sa, 'innocode')
    assert sa.gw.to(HOST['innocode'])[-1].url == 'https://chat.aicenter.inno.tech/v2/chat/completions'


def test_check_claude(sa):
    set_key(sa, 'claude', 'sk-ant-x')
    assert 'Связь есть' in check(sa, 'claude')
    r = sa.gw.to(HOST['claude'])[-1]
    assert r.url == 'https://api.anthropic.com/v1/messages' and r.headers['x-api-key'] == 'sk-ant-x' and r.headers['anthropic-version']
    assert r.body['model'] == 'claude-opus-5-5' and 'temperature' not in r.body


def test_check_note_is_green_on_success(sa):
    set_key(sa, 'openai', 'sk-test')
    check(sa, 'openai')
    assert 'ok' in sa.page.get_attribute('#prov-test-note', 'class')


def test_check_shows_wrong_key(sa):
    sa.gw.fail(HOST['openai'], 401)
    set_key(sa, 'openai', 'sk-bad')
    assert check(sa, 'openai').startswith('ИИ api.openai.com ответил 401 — проверьте ключ или токен')
    assert 'err' in sa.page.get_attribute('#prov-test-note', 'class')


def test_check_shows_network_error(sa):
    sa.gw.down(HOST['openai'])
    set_key(sa, 'openai', 'sk-test')
    assert 'api.openai.com недоступен' in check(sa, 'openai')


def test_changing_key_clears_old_check_result(sa):
    set_key(sa, 'openai', 'sk-test')
    check(sa, 'openai')
    sa.page.fill('#pk-openai', 'sk-test2')
    assert sa.count('#prov-test-note') == 0


def test_check_does_not_start_generation_requests(sa):
    set_key(sa, 'openai', 'sk-test')
    check(sa, 'openai')
    assert len(sa.gw.requests) == 1


# ---------- сохранение ----------
@pytest.fixture
def configured(sa):
    """ChatGPT для ревью, Иннокод для генерации; настройки закрыты."""
    set_key(sa, 'openai', 'sk-test')
    set_key(sa, 'innocode', 'inno-key')
    sa.page.select_option('#review-ai', 'conn:p-openai')
    sa.close_settings()
    return sa


def test_choice_is_saved_in_settings(configured):
    assert configured.call(SETTINGS + '.genAI') == 'conn:p-innocode' and configured.call(SETTINGS + '.reviewAI') == 'conn:p-openai'


def test_keys_and_models_survive_reload(configured):
    configured.reload()
    assert sorted(configured.call(STORED)) == [['p-innocode', 'qwen', 'https://chat.aicenter.inno.tech/v1', 'inno-key'], ['p-openai', 'gpt-5.5', 'https://api.openai.com/v1', 'sk-test']]


def test_choice_survives_reload(configured):
    configured.reload()
    assert configured.state('[S.settings.genAI, S.settings.reviewAI]') == ['conn:p-innocode', 'conn:p-openai']
    assert 'уходят в «Иннокод»' in configured.text('#run-note')


def test_cards_after_reload_show_saved_state(configured):
    configured.reload()
    configured.open_settings('model')
    assert configured.page.evaluate('() => ' + CARDS) == [['Аккаунт Claude', False, 'Нужен ключ'], ['ChatGPT (OpenAI)', False, 'Ключ указан'], ['Иннокод', True, 'Ключ указан']]
    assert configured.page.input_value('#pk-innocode') == 'inno-key' and configured.page.input_value('#review-ai') == 'conn:p-openai'


# ---------- генерация и ревью идут выбранным ИИ ----------
def test_generation_goes_only_to_selected_provider(configured):
    configured.generate()
    assert configured.state('S.run.status') == 'done' and configured.state('S.run.cases.length') > 0
    assert {r.host for r in configured.gw.requests} == {HOST['innocode']}


def test_generation_requests_carry_key_and_temperature(configured):
    configured.generate()
    assert all(r.headers['authorization'] == 'Bearer inno-key' and r.body['temperature'] == 0.2 for r in configured.gw.requests)


def test_review_goes_to_review_provider(configured):
    configured.generate()
    n = len(configured.gw.to(HOST['innocode']))
    configured.page.click('#btn-review')
    configured.wait_idle()
    assert configured.gw.to(HOST['openai']) and len(configured.gw.to(HOST['innocode'])) == n
    assert all(r.headers['authorization'] == 'Bearer sk-test' for r in configured.gw.to(HOST['openai']))


def test_review_without_own_provider_uses_generation_one(sa):
    set_key(sa, 'innocode', 'inno-key')
    sa.close_settings()
    sa.generate()
    sa.page.click('#btn-review')
    sa.wait_idle()
    assert {r.host for r in sa.gw.requests} == {HOST['innocode']}


def test_generation_error_of_provider_is_shown(sa):
    sa.gw.fail(HOST['innocode'], 401)
    set_key(sa, 'innocode', 'bad')
    sa.close_settings()
    sa.generate()
    assert sa.state('S.run.status') == 'error' and 'ответил 401' in sa.state('S.run.error')


def test_generation_without_key_is_refused(sa):
    select(sa, 'openai')
    sa.close_settings()
    sa.page.click('#btn-run')
    assert not sa.state('S.running') and not sa.gw.requests
    assert sa.text('#run-note') == 'Укажите ключ API для подключения «ChatGPT (OpenAI)»: шестерёнка → Модель.'


def test_review_provider_without_key_is_flagged(sa):
    set_key(sa, 'innocode', 'inno-key')
    set_key(sa, 'openai', 'sk-test')   # для генерации — ChatGPT
    sa.page.select_option('#review-ai', 'conn:p-innocode')
    select(sa, 'innocode')
    sa.page.fill('#pk-innocode', '')   # ключ Иннокода стёрт, а ревью по-прежнему на нём
    select(sa, 'openai')
    assert sa.text('#ai-hint') == 'Укажите ключ API для подключения «Иннокод»: шестерёнка → Модель.'
    assert sa.page.input_value('#review-ai') == 'conn:p-innocode'


# ---------- прежнее подключение innoGPT ----------
OLD = {'id': 'p-innogpt', 'preset': 'innogpt', 'kind': 'openai', 'name': 'Иннокод', 'baseUrl': 'https://api.innogpt.de/v1', 'apiKey': 'old', 'model': 'gpt-4o', 'tools': True, 'noTemp': True}


@pytest.fixture
def migrated(make_app):
    return make_app(kind='standalone', local_storage={'qapro.conns': [OLD]}, settings={'genAI': 'conn:p-innogpt', 'reviewAI': 'conn:p-innogpt'})


def test_old_innogpt_connection_is_removed(migrated):
    assert [c[0] for c in migrated.call(STORED)] == ['p-innocode']


def test_old_selection_moves_to_new_innocode(migrated):
    assert migrated.state('[S.settings.genAI, S.settings.reviewAI]') == ['conn:p-innocode', 'same']
    assert migrated.call(SETTINGS + '.genAI') == 'conn:p-innocode'


def test_new_innocode_has_new_address_and_asks_for_key(migrated):
    assert migrated.call(STORED) == [['p-innocode', 'qwen', 'https://chat.aicenter.inno.tech/v1', '']]
    assert migrated.text('#run-note') == 'Укажите ключ API для подключения «Иннокод»: шестерёнка → Модель.'


# ---------- артефакт claude.ai: только аккаунт Claude ----------
def test_artifact_claude_card_is_connected(app):
    app.open_settings('model')
    cards = app.page.evaluate('() => ' + CARDS)
    assert cards[0] == ['Аккаунт Claude', True, 'Подключено']


def test_artifact_key_providers_are_disabled(app):
    app.open_settings('model')
    assert [c[2] for c in app.page.evaluate('() => ' + CARDS)[1:]] == ['Автономная версия', 'Автономная версия']
    assert app.count('#prov-list .prov.dis') == 2 and app.page.is_disabled('#prov-list [data-prov=openai] input[type=radio]')
    assert 'страница на claude.ai не выходит в интернет' in app.text('#prov-list [data-prov=innocode]')
    assert app.count('#prov-list [data-act=standalone]') == 2


def test_artifact_key_providers_cannot_be_selected(app):
    app.open_settings('model')
    app.page.click('#prov-list [data-prov=openai] .prov-h', force=True)
    assert app.state('S.settings.genAI').startswith('claude:')


def test_artifact_has_no_key_fields(app):
    app.open_settings('model')
    assert app.count('#pk-claude') == 0 and app.count('[data-prov-test]') == 0


def test_artifact_tier_choice(app):
    app.open_settings('model')
    assert app.page.eval_on_selector_all('#pc-tier option', 'os => os.map((o) => o.textContent)') == ['Claude · быстрая', 'Claude · стандартная', 'Claude · максимальная']
    app.page.select_option('#pc-tier', 'quick')
    assert app.state('S.settings.genAI') == 'claude:quick'
    assert app.call(SETTINGS + '.genAI') == 'claude:quick'


def test_artifact_review_choices_are_claude_tiers(app):
    app.open_settings('model')
    assert app.page.eval_on_selector_all('#review-ai option', 'os => os.map((o) => o.textContent)') == ['Тот же, что для генерации', 'Claude · быстрая', 'Claude · стандартная', 'Claude · максимальная']


def test_artifact_run_note_mentions_account_limit(app):
    assert 'расходуют лимит вашего аккаунта Claude' in app.text('#run-note')


# ---------- узкий экран ----------
@pytest.mark.parametrize('tab', ['model', 'tms'])
def test_settings_fit_phone_width(make_app, tab):
    app = make_app(kind='standalone', viewport=(390, 860))
    app.page.emulate_media(color_scheme='dark')
    app.open_settings(tab)
    assert app.page.evaluate('() => document.documentElement.scrollWidth') <= 390
    box = app.page.locator('#set-ov .ov-card').bounding_box()
    assert box['x'] >= 0 and box['x'] + box['width'] <= 390
