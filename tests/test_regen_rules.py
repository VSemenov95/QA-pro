"""«Перегенерировать по правилам» учитывает все правила из папки rules/."""
import glob
import os

import pytest

RULES = sorted(glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'rules', '*.md')))


@pytest.fixture
def regenerated(app):
    app.add_sample()
    app.generate()
    app.model.reset()
    app.page.click('#btn-regen')
    app.page.wait_for_timeout(300)
    app.page.click('#btn-regen')
    app.wait_idle()
    return app


def test_regeneration_asks_the_model_for_cases(regenerated):
    assert regenerated.model.prompts_of('promptGenerate'), 'после перегенерации нет запроса на кейсы'


@pytest.mark.parametrize('path', RULES, ids=[os.path.basename(p) for p in RULES])
def test_each_rule_file_reaches_regeneration_prompt(regenerated, path):
    text = open(path, encoding='utf-8').read().strip()
    head = ' '.join(text.split())[:60]
    prompts = regenerated.model.prompts_of('promptGenerate')
    assert prompts and any(head in ' '.join(p.split()) for p in prompts), head


def test_coverage_audit_gets_team_rules_and_rule_files(app):
    """Сверка покрытия видит правила команды и правила из папки rules/ — и при генерации, и при перегенерации."""
    app.page.fill('#cfg-rules', 'ПРАВИЛО-РАЗДЕЛА-XYZ: модуль оплаты не тестируем')
    app.page.dispatch_event('#cfg-rules', 'input')
    app.add_sample()
    app.generate()
    audits = app.model.prompts_of('promptCoverageAudit')
    assert audits, 'нет сверки покрытия'
    assert any('ПРАВИЛО-РАЗДЕЛА-XYZ' in p for p in audits)
    for path in RULES:
        head = ' '.join(open(path, encoding='utf-8').read().split())[:60]
        assert any(head in ' '.join(p.split()) for p in audits), os.path.basename(path)


def test_regeneration_uses_agent_rules_section(app):
    """Текст из раздела «Правила для агента» попадает в перегенерацию кейсов."""
    app.page.fill('#cfg-rules', 'ПРАВИЛО-РАЗДЕЛА-XYZ: модуль оплаты не тестируем')
    app.page.dispatch_event('#cfg-rules', 'input')
    app.add_sample()
    from tests.test_generation import set_outputs
    set_outputs(app, checklist=False)   # план по требованиям
    app.generate()
    app.model.reset()
    app.page.click('#btn-regen')
    app.page.wait_for_timeout(300)
    app.page.click('#btn-regen')
    app.wait_idle()
    assert any('ПРАВИЛО-РАЗДЕЛА-XYZ' in p for p in app.model.prompts_of('promptGenerate'))
    assert not app.model.prompts_of('promptPlan')   # перегенерация переписывает тот же набор кейсов — план не строится заново


# ---------- правки шаблонов после генерации ----------
def regen(app):
    app.model.reset()
    app.page.click('#btn-regen')
    app.page.wait_for_timeout(300)
    app.page.click('#btn-regen')
    app.wait_idle()


def api_prompts(app):
    return [p for p in app.model.prompts_of('promptGenerate') if 'тест-кейсы вида API' in p]


def edit_api_rules(app, extra, save=True):
    app.open_settings('tpl')
    app.page.click('[data-cfgtype=api]')
    cur = app.page.input_value('#cfg-tplrules')
    app.page.fill('#cfg-tplrules', cur + '\n- ' + extra)
    app.page.dispatch_event('#cfg-tplrules', 'input')
    if save:
        app.page.click('#cfg-foot [data-cfg=save], [data-cfg=save]')
        app.page.wait_for_timeout(300)
    app.close_settings()


def test_saved_template_rule_reaches_regeneration(app):
    app.add_sample()
    app.generate()
    edit_api_rules(app, 'НОВОЕ-ПРАВИЛО-ШАБЛОНА: SQL-запрос целиком в блоке кода')
    regen(app)
    assert api_prompts(app) and all('НОВОЕ-ПРАВИЛО-ШАБЛОНА' in p for p in api_prompts(app))
    log = ' '.join(app.state('S.run.steps.plan.log.map((l) => l.text)'))
    assert 'Перегенерация по текущим шаблонам · API: правил оформления' in log and 'НОВОЕ-ПРАВИЛО-ШАБЛОНА' in log


def test_unsaved_template_rule_reaches_regeneration(app):
    app.add_sample()
    app.generate()
    edit_api_rules(app, 'НЕСОХРАНЁННОЕ-ПРАВИЛО', save=False)
    regen(app)
    assert all('НЕСОХРАНЁННОЕ-ПРАВИЛО' in p for p in api_prompts(app))
    assert 'есть несохранённая правка' in ' '.join(app.state('S.run.steps.plan.log.map((l) => l.text)'))


def test_template_edited_in_source_folder_reaches_regeneration(make_app):
    from tests.test_context_source import connect, init
    app = connect(make_app(init=init()))
    app.close_settings()
    app.add_sample()
    app.generate()
    # шаблон поправили прямо в файле папки (в редакторе), страница об этом ещё не знает
    app.page.evaluate("""() => { const f = window.__repo.files; f['templates/api.md'] = f['templates/api.md'].replace('## Образец', '- ПРАВИЛО-ИЗ-ФАЙЛА: запрос в БД целиком\\n\\n## Образец'); }""")
    regen(app)
    assert api_prompts(app) and all('ПРАВИЛО-ИЗ-ФАЙЛА' in p for p in api_prompts(app))


def test_refresh_keeps_unsaved_settings_edit(make_app):
    from tests.test_context_source import connect, init
    app = connect(make_app(init=init()))
    app.close_settings()
    edit_api_rules(app, 'ПРАВКА-В-НАСТРОЙКАХ', save=False)
    app.call('a.ctxRefresh({ quiet: true })')
    app.page.wait_for_timeout(500)
    assert 'ПРАВКА-В-НАСТРОЙКАХ' in app.state('S.cfg.tpl.api.rules') and app.state('S.cfgDirty.api') is True


# ---------- число кейсов ----------
def test_regeneration_keeps_the_number_and_kinds_of_cases(app):
    app.add_sample()
    app.generate()
    before = app.state('S.run.cases.map((c) => [c.type, c.requirementIds.join(","), c.checklistId || ""]).sort()')
    titles = app.state('S.run.cases.map((c) => a.pickTitleText(c.testCase).replace(/^\\[[^\\]]+\\]\\s*/, ""))')
    regen(app)
    after = app.state('S.run.cases.map((c) => [c.type, c.requirementIds.join(","), c.checklistId || ""]).sort()')
    assert len(after) == len(before) and after == before
    gen = '\n'.join(app.model.prompts_of('promptGenerate'))
    assert all(t in gen for t in titles)   # каждый прежний кейс — проверка в запросе
    assert not app.model.prompts_of('promptPlan') and not app.model.prompts_of('promptCoverageAudit')
    assert 'Кейсов столько же, сколько было' in ' '.join(app.state('S.run.steps.coverage.log.map((l) => l.text)'))


def test_cases_the_model_skipped_are_written_again(app):
    from tests.support.model import _generate
    app.add_sample()
    app.generate()
    n = app.state('S.run.cases.length')
    calls = {'n': 0}

    def lossy(call):   # первый ответ перегенерации теряет все кейсы, кроме первого
        calls['n'] += 1
        res = _generate(call)
        return {'cases': res['cases'][:1]} if calls['n'] == 1 else res
    app.model.on('promptGenerate', lossy)
    regen(app)
    assert app.state('S.run.cases.length') == n
    assert 'дописываю' in ' '.join(app.state('S.run.steps.coverage.log.map((l) => l.text)'))


def test_extra_cases_from_the_model_are_not_added(app):
    from tests.support.model import _generate
    app.add_sample()
    app.generate()
    n = app.state('S.run.cases.length')

    def doubled(call):
        res = _generate(call)
        return {'cases': res['cases'] + res['cases']}
    app.model.on('promptGenerate', doubled)
    regen(app)
    assert app.state('S.run.cases.length') == n
