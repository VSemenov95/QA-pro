"""Экономный режим (Настройки → Модель): быстрая модель для служебных шагов, меньше знаний и фрагментов в запросах."""
from tests.support import files, model_kb


def toggle(app):
    app.open_settings('model')
    app.page.click('label:has(#economy)')
    app.close_settings()


def tiers(app, *kinds):
    return {c.kind: c.info['modelTier'] for c in app.model.calls if c.kind in kinds}


def hint(app):
    app.open_settings('model')
    t = app.text('#eco-hint')
    app.close_settings()
    return t


# ---------- переключатель ----------
def test_economy_is_off_by_default(app):
    app.open_settings('model')
    assert app.page.is_checked('#economy') is False
    app.close_settings()
    assert hint(app).startswith('Всегда: в запрос идут только нужные разделы знаний')


def test_hint_describes_what_economy_does_in_generation(app):
    toggle(app)
    assert hint(app) == 'Включён: быстрая модель для сверки кейсов и знаний о продукте, меньше знаний и фрагментов ТЗ в каждом запросе, без поиска по документам.'


def test_hint_describes_what_economy_does_in_knowledge_base(app):
    app.mode('help')
    toggle(app)
    assert hint(app) == 'Включён: быстрая модель, меньше фрагментов базы знаний в каждом ответе.'


def test_choice_is_saved(app):
    toggle(app)
    app.reload()
    app.open_settings('model')
    assert app.page.is_checked('#economy') is True


# ---------- какая модель отвечает ----------
def test_service_steps_use_the_fast_model(app):
    model_kb.install(app.model)
    toggle(app)
    app.generate()
    assert tiers(app, 'promptPassportFull') == {'promptPassportFull': 'quick'}


def test_main_steps_keep_the_main_model(app):
    toggle(app)
    app.generate()
    t = tiers(app, 'promptAnalyze', 'promptChecklist', 'promptPlan', 'promptGenerate')
    assert set(t.values()) == {'default'} and len(t) == 4


def test_without_economy_service_steps_use_the_main_model(app):
    model_kb.install(app.model)
    app.generate()
    assert tiers(app, 'promptPassportFull') == {'promptPassportFull': 'default'}


def test_reconciliation_in_update_runs_on_the_fast_model(app, tmp_path):
    toggle(app)
    app.mode('update')
    app.upload_tests(files.cases_json(tmp_path))
    app.upload(files.spec_file(tmp_path, version='2.0'))
    app.generate()
    assert tiers(app, 'promptMap') == {'promptMap': 'quick'}
    assert tiers(app, 'promptActualize') == {'promptActualize': 'default'}   # переписывание кейсов — на основной модели


def test_knowledge_base_steps_use_the_fast_model(app):
    model_kb.install(app.model)
    toggle(app)
    app.mode('help')
    app.page.click('[data-act=kb-run]')
    app.wait_idle()
    t = tiers(app, 'promptKbSplit', 'promptKbSynth')
    assert t == {'promptKbSplit': 'quick', 'promptKbSynth': 'quick'}


def test_answers_to_questions_use_the_fast_model(app):
    model_kb.install(app.model)
    toggle(app)
    app.mode('help')
    app.page.click('[data-act=kb-run]')
    app.wait_idle()
    app.page.click('[data-act=help-view][data-v=qa]')
    app.page.fill('#help-input', 'Как работает восстановление пароля?')
    app.page.press('#help-input', 'Enter')
    app.page.wait_for_function("() => document.querySelectorAll('#help-list .hq-a:not(.st-pending)').length >= 1")
    assert set(tiers(app, 'promptHelp', 'promptHelpExpand').values()) == {'quick'}


def test_stage_choice_wins_over_economy(app):
    model_kb.install(app.model)
    toggle(app)
    app.call("Object.assign(S.settings.stages, { aux: 'complex' })")
    app.generate()
    assert tiers(app, 'promptPassportFull') == {'promptPassportFull': 'complex'}


# ---------- меньше контекста ----------
def test_answers_use_fewer_knowledge_sections(app):
    model_kb.install(app.model)
    app.mode('help')
    app.page.click('[data-act=kb-run]')
    app.wait_idle()
    app.page.click('[data-act=help-view][data-v=qa]')

    def ask(q, n):
        app.page.fill('#help-input', q)
        app.page.press('#help-input', 'Enter')
        app.page.wait_for_function("(n) => document.querySelectorAll('#help-list .hq-a:not(.st-pending)').length >= n", arg=n)
        app.wait_idle()
    ask('Что известно про пароля?', 1)
    toggle(app)
    ask('Что известно про пароля в целом?', 2)
    normal, eco = app.model.prompts_of('promptHelp')
    sections = lambda p: [l for l in p.split('\n') if l.startswith('[B') and 'Раздел «' in l]
    assert len(sections(normal)) == 2 and len(sections(eco)) == 1


def test_run_reports_economy_in_usage_line(app):
    toggle(app)
    app.generate()
    app.tab('agent')
    assert app.text('.usage-line').endswith('· экономный режим')
