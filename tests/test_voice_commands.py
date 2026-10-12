"""Голосовые команды: разбор фраз, запись с микрофона (фейковое устройство Chrome), ответ моста распознавания речи, выполнение команд.

Распознавание идёт через мост qa-pro-bridge; здесь вместо загрузчика и моста в странице стоит «двойник» (support/fake_uploader.js),
который отвечает на вызовы и возвращает заданный текст. Настоящий Whisper не нужен.
"""
import os
import types

import pytest

from tests.support.app import open_app
from tests.support.chromium import launch_kwargs

FAKE_UPLOADER = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'support', 'fake_uploader.js'), encoding='utf-8').read()
SECURE = '--unsafely-treat-insecure-origin-as-secure=http://app.test'   # getUserMedia работает только на защищённом адресе
HELP = 'Скажите: «открой требования» (или вопросы, черновик, тест-кейсы, чек-лист, экспорт, историю), «запусти генерацию», «запусти ревью», «остановить», «помощь». Генерация стартует после «да».'

PARSE = [
    # (фраза, действие, вкладка)
    ('открой требования', 'tab', 'reqs'), ('Открой вопросы', 'tab', 'questions'), ('покажи тест-кейсы', 'tab', 'cases'), ('перейди в черновик', 'tab', 'draft'),
    ('вкладка чек-лист', 'tab', 'checklist'), ('открой экспорт', 'tab', 'export'), ('история', 'tab', 'history'), ('открой ревью', 'tab', 'review'), ('открой агент', 'tab', 'agent'),
    ('черновик', 'tab', 'draft'), ('вопросы', 'tab', 'questions'), ('экспорт', 'tab', 'export'), ('чеклист', 'tab', 'checklist'), ('кейсы', 'tab', 'cases'),
    ('Открой, ТРЕБОВАНИЯ!', 'tab', 'reqs'), ('запусти генерацию', 'run', None), ('сгенерируй', 'run', None), ('начни генерацию', 'run', None),
    ('запусти ревью', 'review', None), ('остановить', 'stop', None), ('стоп', 'stop', None), ('отмена', 'stop', None), ('остановить генерацию', 'stop', None),
    ('помощь', 'help', None), ('что ты умеешь', 'help', None), ('да', 'confirm', None), ('подтверждаю', 'confirm', None), ('поехали', 'confirm', None),
]
NOT_COMMANDS = ['абракадабра', '', '   ', '...', 'погода сегодня хорошая']


@pytest.fixture(scope='module')
def mic_browser(browser):
    bt = browser.browser_type
    b = bt.launch(args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', SECURE], **launch_kwargs(types.SimpleNamespace(chromium=bt)))
    yield b
    b.close()


@pytest.fixture
def voice(mic_browser):
    """QA pro с «загрузчиком и мостом» (двойник) и микрофоном."""
    apps = []

    def make(**kw):
        a = open_app(mic_browser, init=FAKE_UPLOADER + kw.pop('script', ''), **kw)
        apps.append(a)
        return a
    yield make
    errs = [e for a in apps for e in a.errors]
    for a in apps:
        a.ctx.close()
    assert not errs, 'ошибки на странице: ' + '; '.join(errs[:3])


def say(app, text):
    """Фраза, уже распознанная мостом, выполняется как команда."""
    app.call('a.voiceExecute(arg)', text)
    return app.text('#voice-status')


def status(app):
    return app.text('#voice-status')


def record(app, text, wait=True):
    """Нажать микрофон, «сказать», нажать ещё раз; текст возвращает двойник моста."""
    app.page.evaluate('(t) => { window.__voiceText = t; }', text)
    n = app.page.evaluate('window.__asrCalls.length')
    app.page.click('#btn-voice')
    app.page.wait_for_function("() => document.querySelector('#btn-voice').getAttribute('aria-pressed') === 'true'")
    app.page.wait_for_timeout(700)   # фейковое устройство должно успеть записать звук
    app.page.click('#btn-voice')
    if wait:
        app.page.wait_for_function('(n) => window.__asrCalls.length > n && !document.querySelector("#btn-voice").classList.contains("rec")', arg=n, timeout=20000)
        app.page.wait_for_function("() => !/Распознаю/.test(document.querySelector('#voice-status').textContent)", timeout=10000)


# ---------- разбор фраз ----------
@pytest.mark.parametrize('phrase,action,tab', PARSE)
def test_phrase_is_understood(app, phrase, action, tab):
    got = app.call('a.voiceParse(arg)', phrase)
    assert got and got['action'] == action and (tab is None or got['tab'] == tab)


@pytest.mark.parametrize('phrase', NOT_COMMANDS)
def test_other_speech_is_not_a_command(app, phrase):
    assert app.call('a.voiceParse(arg)', phrase) is None


def test_stop_wins_over_run(app):
    assert app.call('a.voiceParse(arg)', 'остановить генерацию')['action'] == 'stop'


def test_review_is_run_review_not_tab(app):
    assert app.call('a.voiceParse(arg)', 'запусти ревью')['action'] == 'review' and app.call('a.voiceParse(arg)', 'открой ревью')['action'] == 'tab'


@pytest.mark.xfail(strict=True, reason='БАГ: подсказка «помощь» учит говорить «…историю» (винительный падеж), а разбор знает только «история»: «открой историю» не распознаётся (VOICE_TABS в app3.js)')
@pytest.mark.parametrize('phrase', ['открой историю', 'покажи историю'])
def test_history_is_understood_the_way_the_help_says_it(app, phrase):
    got = app.call('a.voiceParse(arg)', phrase)
    assert got and got['action'] == 'tab' and got['tab'] == 'history'


# ---------- выполнение команд ----------
def test_tab_command_switches_the_tab(app):
    app.generate()
    assert say(app, 'открой требования') == 'Открыл вкладку.'
    assert app.page.get_attribute('#tab-reqs', 'aria-selected') == 'true'


@pytest.mark.parametrize('phrase,tab', [('открой вопросы', 'questions'), ('покажи тест-кейсы', 'cases'), ('черновик', 'draft'), ('чек-лист', 'checklist'), ('экспорт', 'export'), ('история', 'history')])
def test_every_tab_of_the_list_opens(app, phrase, tab):
    app.generate()
    say(app, phrase)
    assert app.page.get_attribute(f'#tab-{tab}', 'aria-selected') == 'true'


def test_generation_asks_for_confirmation_first(app):
    assert say(app, 'запусти генерацию') == 'Запустить генерацию? Скажите «да» в течение 10 секунд.'
    assert app.state('S.running') is False and app.model.calls == []


def test_yes_starts_the_generation(app):
    say(app, 'запусти генерацию')
    assert say(app, 'да') == 'Запустил генерацию.'
    app.wait_idle()
    assert app.state('S.run.status') == 'done' and app.state('S.run.cases.length') > 0


def test_yes_without_a_question_does_nothing(app):
    assert say(app, 'да') == 'Нечего подтверждать. ' + HELP
    assert app.model.calls == []


def test_confirmation_expires_after_ten_seconds(app):
    say(app, 'запусти генерацию')
    app.page.evaluate('() => { const d = Date.now; Date.now = () => d() + 11000; }')   # прошло 11 секунд
    assert say(app, 'да').startswith('Нечего подтверждать.')
    assert app.state('S.running') is False and app.model.calls == []


def test_another_command_cancels_the_question(app):
    say(app, 'запусти генерацию')
    say(app, 'помощь')
    assert say(app, 'да').startswith('Нечего подтверждать.')
    assert app.model.calls == []


def test_review_asks_for_confirmation_too(app):
    app.generate()
    assert say(app, 'запусти ревью') == 'Запустить ревью? Скажите «да» в течение 10 секунд.'
    n = len(app.model.calls)
    assert say(app, 'да') == 'Запустил ревью.'
    app.wait_idle()
    assert len(app.model.calls) > n and app.model.calls_of('promptReviewCases')


@pytest.mark.xfail(strict=True, reason='БАГ: без результатов кнопка ревью скрыта, но «запусти ревью» + «да» отвечает «Запустил ревью.»: voiceRun проверяет только disabled, не hidden, и нажимает скрытую кнопку (app3.js)')
def test_review_without_a_run_is_refused(app):
    say(app, 'запусти ревью')
    assert say(app, 'да') == 'Ревью сейчас нельзя запустить.'
    assert app.model.calls == []


def test_generation_without_documents_is_refused(app):
    app.create_product('Пустой продукт')
    say(app, 'запусти генерацию')
    assert say(app, 'да') == 'Генерацию сейчас нельзя запустить: нет документов или запуск уже идёт.'
    assert app.model.calls == []


@pytest.mark.xfail(strict=True, reason='БАГ: пока генерация идёт, кнопка запуска скрыта, но «запусти генерацию» + «да» отвечает «Запустил генерацию.» вместо «…запуск уже идёт»: voiceRun не смотрит на hidden (app3.js)')
def test_generation_while_one_is_running_is_refused(make_app):
    app = make_app(init='window.__sampleDelay = 600;')
    say(app, 'запусти генерацию')
    say(app, 'да')
    app.page.wait_for_selector('#btn-stop:not([hidden])')
    say(app, 'запусти генерацию')
    assert say(app, 'да') == 'Генерацию сейчас нельзя запустить: нет документов или запуск уже идёт.'


def test_stop_when_nothing_runs(app):
    assert say(app, 'остановить') == 'Сейчас ничего не запущено.'


def test_stop_interrupts_a_running_generation(make_app):
    app = make_app(init='window.__sampleDelay = 600;')
    say(app, 'запусти генерацию')
    say(app, 'да')
    app.page.wait_for_selector('#btn-stop:not([hidden])')
    assert say(app, 'стоп') == 'Остановил.'
    app.page.wait_for_function('() => !window.__qa.S.running', timeout=30000)
    assert app.state('S.run.status') != 'done'


def test_help_lists_the_commands(app):
    assert say(app, 'помощь') == HELP


def test_unknown_phrase_is_reported_with_the_help(app):
    assert say(app, 'абракадабра') == f'Не понял: «абракадабра». {HELP}'
    assert 'warn' in app.page.get_attribute('#voice-status', 'class')


# ---------- запись с микрофона ----------
def test_microphone_button_starts_recording(voice):
    app = voice()
    app.page.click('#btn-voice')
    app.page.wait_for_function("() => document.querySelector('#btn-voice').getAttribute('aria-pressed') === 'true'")
    assert status(app) == 'Слушаю… скажите команду и нажмите микрофон ещё раз.'
    assert app.page.get_attribute('#btn-voice', 'title') == 'Остановить запись' and 'rec' in app.page.get_attribute('#btn-voice', 'class')


def test_recorded_sound_goes_to_the_bridge_as_russian_speech(voice):
    app = voice()
    record(app, 'открой требования')
    calls = app.page.evaluate('window.__asrCalls')
    assert len(calls) == 1 and calls[0]['language'] == 'russian' and calls[0]['bytes'] > 10000   # звук: 16 кГц, 1 байт на отсчёт, в base64
    assert 'asr_status' in app.page.evaluate('window.__asrTools') and 'asr_transcribe' in app.page.evaluate('window.__asrTools')


def test_spoken_command_is_executed(voice):
    app = voice()
    record(app, 'открой требования')
    assert app.page.get_attribute('#tab-reqs', 'aria-selected') == 'true' and status(app) == 'Открыл вкладку.'
    assert app.page.get_attribute('#btn-voice', 'aria-pressed') == 'false'


def test_spoken_generation_needs_a_spoken_yes(voice):
    app = voice()
    record(app, 'запусти генерацию')
    assert status(app).startswith('Запустить генерацию?') and app.state('S.running') is False
    record(app, 'да')
    assert status(app) == 'Запустил генерацию.'
    app.wait_idle()
    assert app.state('S.run.status') == 'done'


def test_unrecognized_phrase_is_reported(voice):
    app = voice()
    record(app, 'абракадабра')
    assert status(app).startswith('Не понял: «абракадабра».')


def test_silence_is_reported(voice):
    app = voice()
    record(app, '')
    assert status(app) == 'Ничего не услышал. Скажите команду ещё раз.'


def test_bridge_error_is_reported(voice):
    app = voice(script="window.__asrFail = 'Распознаватель не запущен';")
    record(app, 'открой требования')
    assert status(app) == 'Распознавание не удалось: Распознаватель не запущен'


# ---------- моста нет / не подходит ----------
def test_without_uploader_and_bridge_the_microphone_explains(voice, mic_browser):
    a = open_app(mic_browser)   # без двойника загрузчика
    try:
        a.page.click('#btn-voice')
        a.page.wait_for_function("() => /мост qa-pro-bridge/.test(document.querySelector('#voice-status').textContent) && !/Проверяю/.test(document.querySelector('#voice-status').textContent)")
        assert 'Распознавание речи идёт на вашем компьютере через мост qa-pro-bridge' in status(a)
        assert a.page.get_attribute('#btn-voice', 'aria-pressed') == 'false' and 'err' in a.page.get_attribute('#voice-status', 'class')
    finally:
        a.ctx.close()


@pytest.mark.parametrize('script,expected', [
    ("window.__extVersion = '1.4.0';", 'Загрузчик 1.4.0 не умеет передавать звук мосту — обновите его до 1.5.0'),
    ("window.__bridgeVersion = '1.1.0';", 'Мост 1.1.0 не умеет распознавать речь — установите мост 1.2.0'),
    ("window.__bridgeUp = false;", 'Загрузчик на месте, но мост qa-pro-bridge не запущен.'),
])
def test_old_or_missing_bridge_is_explained(voice, script, expected):
    app = voice(script=script)
    app.page.click('#btn-voice')
    app.page.wait_for_function("() => document.querySelector('#voice-status').classList.contains('err')")
    assert expected in status(app) and app.page.get_attribute('#btn-voice', 'aria-pressed') == 'false'


@pytest.mark.parametrize('error,expected', [("new DOMException('Permission denied', 'NotAllowedError')", 'Нет доступа к микрофону: разрешите его в браузере.'),
                                             ("new Error('нет устройства')", 'Нет доступа к микрофону: нет устройства')])
def test_microphone_errors_are_explained(voice, error, expected):
    app = voice(script=f"navigator.mediaDevices.getUserMedia = () => Promise.reject({error});")
    app.page.click('#btn-voice')
    app.page.wait_for_function("() => /Нет доступа к микрофону/.test(document.querySelector('#voice-status').textContent)", timeout=20000)
    assert status(app) == expected and app.page.get_attribute('#btn-voice', 'aria-pressed') == 'false'
