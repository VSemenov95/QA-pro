"""Модель по этапам (Настройки → Модель): выбор уровня для этапа, рекомендации, какая модель реально уходит в запрос."""
import json

import pytest

RECOMMENDED = {'analyze': 'default', 'generate': 'default', 'review': 'quick', 'aux': 'quick'}
STEPS = ['analyze', 'plan', 'map', 'generate', 'actualize', 'review', 'knowledge', 'help', 'export', 'other']


def conn(pid, kind, model, base):
    return {'id': pid, 'preset': pid.replace('p-', ''), 'kind': kind, 'name': pid, 'baseUrl': base, 'apiKey': 'k', 'auth': 'Bearer', 'model': model, 'headers': '', 'tools': False, 'noTemp': kind == 'openai'}


def settings(gen, **kw):
    s = {'outputs': {'cases': True, 'checklist': False}, 'types': {'api': True, 'ui': True, 'e2e': True}, 'depth': 'full', 'genAI': gen, 'reviewAI': 'same',
         'agentTools': False, 'mode': 'generate', 'economy': False, 'reuseAnalysis': True, 'kbAuto': False}
    s.update(kw)
    return s


def stages_ui(app):
    app.open_settings('model')
    return app.page


class Api:
    """Подмена API ключевых провайдеров: запоминает тела запросов."""
    def __init__(self, app, openai=False):
        self.bodies = []
        app.ctx.route('https://api.openai.com/**' if openai else 'https://api.anthropic.com/**', self.handle)
        self.openai = openai

    CORS = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': 'POST, OPTIONS'}

    def handle(self, route):
        if route.request.method == 'OPTIONS':   # предзапрос браузера (CORS)
            return route.fulfill(status=204, headers=self.CORS)
        body = json.loads(route.request.post_data)
        self.bodies.append(body)
        if self.openai:
            res = {'choices': [{'message': {'role': 'assistant', 'content': '{"ok":1}'}}], 'usage': {'prompt_tokens': 1, 'completion_tokens': 1}}
        else:
            res = {'content': [{'type': 'text', 'text': '{"ok":1}'}], 'stop_reason': 'end_turn', 'usage': {'input_tokens': 10, 'output_tokens': 5}}
        route.fulfill(status=200, content_type='application/json', body=json.dumps(res), headers=self.CORS)


@pytest.fixture
def claude_key_app(make_app):
    # подключения по ключу работают только в автономной версии (в артефакте страница изолирована от интернета)
    return make_app(kind='standalone', local_storage={'qapro.conns': [conn('p-claude', 'anthropic', 'claude-opus-5-5', 'https://api.anthropic.com')]}, settings=settings('conn:p-claude'))


def ask_steps(app, steps=STEPS):
    app.call("(async () => { for (const step of arg) await a.ask('x', { step, role: step === 'review' ? 'rev' : 'gen' }); })()", steps)


def set_stages(app, **kw):
    app.call('Object.assign(S.settings.stages, arg)', kw)


# ---------- интерфейс ----------
def rows(app):
    return app.page.evaluate("() => [...document.querySelectorAll('#stage-models .stage-row')].map((r) => ({ title: r.querySelector('label').innerText, value: r.querySelector('select').value, disabled: r.querySelector('select').disabled, why: r.querySelector('.stage-why').innerText }))")


def test_four_stages_default_to_main_model(claude_key_app):
    app = claude_key_app
    stages_ui(app)
    r = rows(app)
    assert [x['value'] for x in r] == ['same'] * 4 and not any(x['disabled'] for x in r)
    assert [x['title'] for x in r] == ['Анализ, план и сверка', 'Тест-кейсы', 'Ревью', 'Служебные шаги']


def test_each_stage_explains_its_recommendation(claude_key_app):
    app = claude_key_app
    stages_ui(app)
    for x in rows(app):
        assert x['why'].startswith('Рекомендуем: ') and len(x['why']) > 120


def test_info_message_follows_selection(claude_key_app):
    app = claude_key_app
    stages_ui(app)
    assert 'Рекомендуемая раскладка' in app.text('#stage-note')
    app.page.click('[data-stage-act=apply]')
    assert app.state('S.settings.stages') == RECOMMENDED
    assert 'Выбрана рекомендуемая раскладка' in app.text('#stage-note')
    assert app.page.is_disabled('[data-stage-act=apply]') and not app.page.is_disabled('[data-stage-act=reset]')
    app.page.select_option('#stage-review', 'complex')
    assert 'отличается' in app.text('#stage-note')


def test_choice_is_saved_and_restored(make_app):
    st = settings('conn:p-claude', stages={'analyze': 'default', 'generate': 'default', 'review': 'complex', 'aux': 'bogus'})
    a = make_app(kind='standalone', local_storage={'qapro.conns': [conn('p-claude', 'anthropic', 'claude-opus-5-5', 'https://api.anthropic.com')]}, settings=st)
    assert a.state('S.settings.stages') == {'analyze': 'default', 'generate': 'default', 'review': 'complex', 'aux': 'same'}


def test_old_settings_without_stages(claude_key_app):
    assert claude_key_app.state('Object.values(S.settings.stages)') == ['same'] * 4


def test_reset_returns_all_to_main(claude_key_app):
    app = claude_key_app
    stages_ui(app)
    app.page.click('[data-stage-act=apply]')
    app.page.click('[data-stage-act=reset]')
    assert app.state('Object.values(S.settings.stages)') == ['same'] * 4
    assert app.call("JSON.parse(localStorage.getItem('tca.settings')).stages") == {'analyze': 'same', 'generate': 'same', 'review': 'same', 'aux': 'same'}


# ---------- какая модель уходит в запрос ----------
def models(api):
    return [b['model'] for b in api.bodies]


def test_main_model_everywhere_by_default(claude_key_app):
    api = Api(claude_key_app)
    ask_steps(claude_key_app)
    assert set(models(api)) == {'claude-opus-5-5'} and len(api.bodies) == 10


def test_recommended_layout_by_step(claude_key_app):
    api = Api(claude_key_app)
    set_stages(claude_key_app, **RECOMMENDED)
    ask_steps(claude_key_app)
    sonnet, haiku = 'claude-sonnet-5-5', 'claude-haiku-5-5'
    assert dict(zip(STEPS, models(api))) == {'analyze': sonnet, 'plan': sonnet, 'map': sonnet, 'generate': sonnet, 'actualize': sonnet,
                                             'review': haiku, 'knowledge': haiku, 'help': haiku, 'export': haiku, 'other': haiku}


def test_custom_layout(claude_key_app):
    api = Api(claude_key_app)
    set_stages(claude_key_app, analyze='complex', generate='quick', review='default', aux='complex')
    ask_steps(claude_key_app)
    opus, sonnet, haiku = 'claude-opus-5-5', 'claude-sonnet-5-5', 'claude-haiku-5-5'
    assert models(api) == [opus] * 3 + [haiku] * 2 + [sonnet] + [opus] * 4


def test_follow_up_generation_steps_belong_to_cases_stage(claude_key_app):
    """fix (исправление после ревью), coverage (дописывание кейсов) и answers — это написание кейсов, а не служебные шаги."""
    api = Api(claude_key_app)
    set_stages(claude_key_app, generate='quick', aux='complex')
    ask_steps(claude_key_app, ['fix', 'answers', 'coverage', 'video'])
    assert models(api) == ['claude-haiku-5-5'] * 3 + ['claude-opus-5-5']


def test_coverage_audit_is_aux_stage(claude_key_app):
    api = Api(claude_key_app)
    set_stages(claude_key_app, generate='complex', aux='quick')
    claude_key_app.call("a.ask('x', { step: 'coverage', stage: 'aux' })")
    assert models(api) == ['claude-haiku-5-5']


def test_claude_5_models_get_no_temperature(claude_key_app):
    api = Api(claude_key_app)
    ask_steps(claude_key_app, ['generate'])
    assert 'temperature' not in api.bodies[0]


def test_legacy_model_keeps_temperature(make_app):
    a = make_app(kind='standalone', local_storage={'qapro.conns': [conn('p-claude', 'anthropic', 'claude-3-7-sonnet-20250219', 'https://api.anthropic.com')]}, settings=settings('conn:p-claude'))
    api = Api(a)
    ask_steps(a, ['generate'])
    set_stages(a, generate='default')
    ask_steps(a, ['generate'])
    assert api.bodies[0]['model'].startswith('claude-3') and api.bodies[0].get('temperature') == 0.2
    assert api.bodies[1]['model'] == 'claude-sonnet-5-5' and 'temperature' not in api.bodies[1]


@pytest.fixture
def openai_app(make_app):
    st = settings('conn:p-openai', stages={'analyze': 'quick', 'generate': 'complex', 'review': 'default', 'aux': 'quick'})
    return make_app(kind='standalone', local_storage={'qapro.conns': [conn('p-openai', 'openai', 'gpt-5.5', 'https://api.openai.com/v1')]}, settings=st)


def test_chatgpt_ignores_stage_levels(openai_app):
    api = Api(openai_app, openai=True)
    ask_steps(openai_app, ['analyze', 'generate', 'review', 'help'])
    assert set(models(api)) == {'gpt-5.5'}


def test_chatgpt_selects_are_disabled_with_explanation(openai_app):
    stages_ui(openai_app)
    assert all(x['disabled'] for x in rows(openai_app))
    assert 'не переключается' in openai_app.text('#stage-note')


# ---------- аккаунт Claude (возможность sample приложения) ----------
def tiers(app, steps=('analyze', 'generate', 'review', 'help', 'coverage', 'fix', 'video'), **stage_kw):
    set_stages(app, **stage_kw)
    app.model.reset()
    app.call("(async () => { for (const s of arg) await a.ask('x', { step: s, role: s === 'review' ? 'rev' : 'gen', tier: s === 'help' ? 'quick' : undefined, stage: s === 'coverage' ? 'aux' : undefined }); })()", list(steps))
    return [c.info.get('modelTier') for c in app.model.calls]


@pytest.fixture
def account_app(make_app):
    return make_app(settings=settings('claude:default'))


def test_account_main_tier_unless_step_has_its_own(account_app):
    assert tiers(account_app, analyze='same', generate='same', review='same', aux='same') == ['default', 'default', 'default', 'quick', 'default', 'default', 'default']


def test_account_recommended_layout(account_app):
    assert tiers(account_app, **RECOMMENDED) == ['default', 'default', 'quick', 'quick', 'quick', 'default', 'quick']


def test_account_stage_choice_beats_step_tier_and_economy_mode(account_app):
    assert tiers(account_app, analyze='complex', generate='complex', review='complex', aux='complex') == ['complex'] * 7
    account_app.call('S.settings.economy = true')
    assert tiers(account_app, analyze='default', generate='default', review='same', aux='same')[:2] == ['default', 'default']
