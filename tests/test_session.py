"""История запусков, восстановление сессии после закрытия страницы, «следящая» вкладка, блокировка выбора продукта и остановка генерации."""
import time

import pytest

from tests.support import files, seed
from tests.support.db import MemoryDB
from tests.support.model_generation import HOLD_JS, Hold, connect_ai, second_page, standalone, wait_until


@pytest.fixture
def held(make_app):
    """Страница, на которой запросы к модели можно задержать (Hold)."""
    return make_app(init=HOLD_JS)


def pid(app):
    return app.state('S.productId')


def run_path(app):
    return f'products/{pid(app)}/runs/{app.state("S.run.id")}'


def run_meta(app):
    return app.db.get(run_path(app)) or {}


def session(app):
    return app.db.get('data/users/u_test/session') or {}


def finish_saving(app):
    """Дождаться, пока запуск и сессия записаны в базу после окончания генерации."""
    wait_until(app, lambda: run_meta(app).get('status') == 'done' and run_meta(app).get('hb') == 0 and session(app).get('runId') == app.state('S.run.id'))


def start_held(app, kind):
    """Запустить генерацию и остановить её на первом запросе вида kind."""
    h = Hold(app.page).on(kind)
    app.generate(wait=False)
    h.wait()
    return h


def close_like_user(app):
    """Страницу закрывают посреди работы: браузер шлёт pagehide, приложение успевает записать состояние."""
    app.page.evaluate("() => window.dispatchEvent(new PageTransitionEvent('pagehide', { persisted: false }))")
    wait_until(app, lambda: run_meta(app).get('hb') == 0 and not session(app).get('runningBy'))
    app.page.close()


# ---------- история запусков ----------
def test_run_is_saved_into_product_history(app):
    app.generate()
    finish_saving(app)
    m = run_meta(app)
    assert (m['status'], m['stage'], m['mode'], m['coverage'], m['partsCount']) == ('done', 'draft', 'generate', 100, 1)
    assert m['counts'] == {'api': 2, 'ui': 1, 'e2e': 1, 'checklist': 4} and [d['name'] for d in m['docs']] == ['Пример — ТЗ восстановление пароля.md']
    assert [c['dispId'] for c in app.db.get(run_path(app) + '/parts/p0')['cases']] == ['API-001', 'API-002', 'UI-001', 'E2E-001']


def test_history_tab_lists_the_run(app):
    app.generate()
    finish_saving(app)
    app.tab('history')
    app.page.wait_for_selector('.hrow')
    row = app.text('.hrow')
    assert 'Пример — ТЗ восстановление пароля.md' in row and 'API 2 · UI 1 · E2E 1 · чек-лист 4' in row and 'покрытие 100%' in row and 'открыт' in row
    assert 'Запуски продукта «Мой продукт»' in app.text('#tab-body')


def test_empty_history_says_so(app):
    app.tab('history')
    app.page.wait_for_selector('.empty')
    assert 'Запусков пока нет' in app.text('#tab-body')


def test_history_list_updates_after_a_new_run(app):
    app.tab('history')
    app.page.wait_for_selector('.empty')
    app.tab('agent')
    app.generate()
    finish_saving(app)
    app.tab('history')
    app.page.wait_for_selector('.hrow')
    assert app.count('.hrow') == 1


def test_second_run_is_listed_first(app, tmp_path):
    app.generate()
    finish_saving(app)
    first = app.state('S.run.id')
    app.page.click('#btn-newses')
    app.upload(files.spec_file(tmp_path))
    app.generate()
    wait_until(app, lambda: run_meta(app).get('status') == 'done' and run_meta(app).get('hb') == 0)
    app.tab('history')
    app.page.wait_for_function("() => document.querySelectorAll('.hrow').length === 2")
    assert app.state('S.run.id') != first
    assert 'открыт' in app.text('.hrow:first-child') and 'открыт' not in app.text('.hrow:last-child')


def reopen_from_history(app):
    app.generate()
    finish_saving(app)
    app.page.click('#btn-newses')
    app.tab('history')
    app.page.click('[data-act=open-hist]')
    app.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.cases.length === 4")


def test_run_from_history_comes_back_with_results(app):
    reopen_from_history(app)
    assert app.state('S.tab') == 'cases' and app.state('S.run.requirements.length') == 4 and app.state('S.run.checklist.groups.length') == 2
    assert app.state('S.run.cases.map((c) => c.dispId)') == ['API-001', 'API-002', 'UI-001', 'E2E-001']
    assert 'Запуск загружен из истории' in ' '.join(app.toast_texts())


def test_run_from_history_keeps_steps_log_and_questions(app):
    reopen_from_history(app)
    app.tab('agent')
    assert 'Запуск загружен из истории.' in app.text('.banner.info') and 'Итого 4 требования' in app.text('.timeline')
    assert app.state('S.run.questions.length') == 1


def test_run_opened_from_history_can_be_edited_and_saved(app):
    reopen_from_history(app)
    app.page.click('#case-list article:first-child .case-h')
    app.page.click('#case-list [data-act=form-case]')
    app.page.fill('.case-form input[data-fp="title"]', '[BE] Правка после истории')
    app.page.click('[data-act=ff-save]')
    wait_until(app, lambda: 'Правка после истории' in str(app.db.get(run_path(app) + '/parts/p0')))


def test_edit_is_saved_in_history(app):
    app.generate()
    finish_saving(app)
    app.tab('cases')
    app.page.click('#case-list article:has(.case-id:text-is("UI-001")) .case-h')
    app.page.click('#case-list [data-act=form-case]')
    app.page.fill('.case-form input[data-fp="title"]', '[FE] Сохранено в историю')
    app.page.click('[data-act=ff-save]')
    wait_until(app, lambda: '[FE] Сохранено в историю' in str(app.db.get(run_path(app) + '/parts/p0')))


def test_delete_from_history_asks_twice_and_clears_database(app):
    app.generate()
    finish_saving(app)
    base = run_path(app)
    app.tab('history')
    app.page.wait_for_selector('.hrow')
    app.page.click('[data-act=del-hist]')
    assert app.db.get(base) is not None   # первое нажатие только просит подтверждение
    app.page.click('[data-act=del-hist]')
    wait_until(app, lambda: app.db.get(base) is None)
    assert app.db.get(base + '/parts/p0') is None and app.count('.hrow') == 0
    assert 'Запуск удалён из истории' in ' '.join(app.toast_texts())


def test_deleted_open_run_becomes_read_only(app):
    app.generate()
    finish_saving(app)
    app.tab('history')
    app.page.wait_for_selector('.hrow')
    app.page.click('[data-act=del-hist]')
    app.page.click('[data-act=del-hist]')
    wait_until(app, lambda: app.state('S.run.fromHistory') == 'readonly')


def test_deleted_open_run_is_not_restored_after_reload(app):
    app.generate()
    finish_saving(app)
    app.tab('history')
    app.page.wait_for_selector('.hrow')
    app.page.click('[data-act=del-hist]')
    app.page.click('[data-act=del-hist]')
    wait_until(app, lambda: session(app).get('runId') is None)
    app.reload()
    assert app.state('S.run') is None and 'Сессия восстановлена' not in ' '.join(app.toast_texts())


def test_deleted_run_disappears_from_product_cases(app):
    app.generate()
    app.tab('draft')
    app.page.click('[data-act=draft-add]')
    app.page.wait_for_function("() => window.__qa.S.prodIndex.cases.length === 4")
    finish_saving(app)
    app.tab('history')
    app.page.wait_for_selector('.hrow')
    app.page.click('[data-act=del-hist]')
    app.page.click('[data-act=del-hist]')
    app.page.wait_for_function("() => window.__qa.S.prodIndex.cases.length === 0")


def test_history_is_separate_for_each_product(app):
    app.generate()
    finish_saving(app)
    app.create_product('Второй продукт')
    app.tab('history')
    app.page.wait_for_selector('.empty')
    assert 'Запусков пока нет' in app.text('#tab-body') and 'Запуски продукта «Второй продукт»' in app.text('#tab-body')
    app.page.select_option('#prod-select', app.db.paths('products/')[0].split('/')[1])
    app.tab('history')
    app.page.wait_for_selector('.hrow')


@pytest.fixture
def legacy(make_app):
    """Страница пользователя, у которого в личной части базы лежит запуск, сделанный до появления продуктов."""
    db = MemoryDB()
    r = seed.run('run_old', 'Старое ТЗ.md', [seed.case('o1', 'ui', 'UI-001', '[FE] Старый кейс', ['R-001']), seed.case('o2', 'api', 'API-001', '[BE] Старый API', ['R-001'])], [seed.req('R-001', 'Старое ТЗ.md')])
    r['meta']['productId'] = None
    db.op('set', 'data/users/u_test/run_old', r['meta'])
    db.op('set', 'data/users/u_test/run_old/parts/p0', r['parts'][0])
    return make_app(db=db)


def test_personal_runs_without_product_are_listed_separately(legacy):
    legacy.tab('history')
    legacy.page.wait_for_selector('.hrow')
    assert 'Личные запуски без продукта' in legacy.text('#tab-body') and 'Старое ТЗ.md' in legacy.text('.hrow') and legacy.count('[data-act=move-hist]') == 1


def test_personal_run_can_be_moved_into_product(legacy):
    legacy.tab('history')
    legacy.page.wait_for_selector('[data-act=move-hist]')
    legacy.page.click('[data-act=move-hist]')
    wait_until(legacy, lambda: legacy.db.get(f'products/{pid(legacy)}/runs/run_old') and not legacy.db.get('data/users/u_test/run_old'))
    assert legacy.db.get(f'products/{pid(legacy)}/runs/run_old/parts/p0') and not legacy.db.get('data/users/u_test/run_old/parts/p0')
    legacy.page.wait_for_function("() => window.__qa.S.prodIndex.cases.length === 2")
    assert sorted(legacy.state('S.prodIndex.cases.map((x) => x.i)')) == ['API-001', 'UI-001']
    assert 'Запуск перенесён в продукт «Мой продукт»' in ' '.join(legacy.toast_texts())
    legacy.page.wait_for_function("() => !document.querySelector('[data-act=move-hist]') && document.querySelectorAll('.hrow').length === 1")


def test_stopped_run_is_marked_unfinished_in_history(held):
    h = start_held(held, 'promptGenerate')
    held.page.click('#btn-stop')
    h.release()
    held.wait_idle()
    wait_until(held, lambda: run_meta(held).get('status') == 'stopped' and run_meta(held).get('hb') == 0)
    held.page.click('#btn-newses')
    held.tab('history')
    held.page.wait_for_selector('.hrow')
    assert 'не завершён' in held.text('.hrow')


def test_actualization_row_in_history_shows_status_counts(app, tmp_path):
    app.mode('update')
    app.upload_tests(files.cases_json(tmp_path))
    app.upload(files.spec_file(tmp_path, version='2.0'))
    app.generate()
    wait_until(app, lambda: run_meta(app).get('status') == 'done' and run_meta(app).get('hb') == 0)
    app.tab('history')
    app.page.wait_for_selector('.hrow')
    row = app.text('.hrow')
    assert 'Актуализация: cases.json' in row and 'изменено 1' in row and 'устарело 1' in row and 'без изменений 6' in row


# ---------- восстановление сессии ----------
def test_reload_brings_back_run_and_tab(app):
    app.generate()
    app.tab('reqs')
    finish_saving(app)
    wait_until(app, lambda: session(app).get('tab') == 'reqs')
    app.reload()
    app.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.cases.length === 4")
    assert app.state('S.tab') == 'reqs' and app.state('S.run.requirements.length') == 4
    assert 'Сессия восстановлена' in ' '.join(app.toast_texts())


def test_reloaded_run_is_not_marked_as_interrupted(app):
    app.generate()
    finish_saving(app)
    app.reload()
    app.page.wait_for_function("() => window.__qa.S.run")
    assert app.state('S.run.status') == 'done' and app.state('S.resume') is None


def test_answer_to_question_is_saved_and_survives_reload(app):
    app.generate()
    finish_saving(app)
    app.tab('questions')
    app.page.fill('textarea[data-q="Q-01"]', 'Показываем таймер обратного отсчёта')
    wait_until(app, lambda: run_meta(app).get('questions', [{}])[0].get('answer') == 'Показываем таймер обратного отсчёта')
    app.reload()
    app.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.questions.length === 1")
    app.tab('questions')
    assert app.page.input_value('textarea[data-q="Q-01"]') == 'Показываем таймер обратного отсчёта' and app.text('#qst-Q-01') == 'не учтён'


def test_new_run_closes_result_but_keeps_documents(app):
    app.generate()
    finish_saving(app)
    app.page.click('#btn-newses')
    assert app.state('S.run') is None and app.state('S.tab') == 'agent'
    assert app.state('S.docs.length') == 1 and app.state('[...S.runDocs].length') == 0
    assert app.count('#doc-list li.doc') == 0 and 'Загрузите ТЗ и другие документы для этого запуска' in app.text('#docs-note')
    assert 'Результат сохранён в «Истории»' in ' '.join(app.toast_texts())


def test_new_run_stays_closed_after_reload(app):
    app.generate()
    finish_saving(app)
    app.page.click('#btn-newses')
    wait_until(app, lambda: session(app).get('runId') is None)
    app.reload()
    assert app.state('S.run') is None


def test_uploaded_document_is_back_after_reload(app, tmp_path):
    app.upload(files.spec_file(tmp_path, name='Доп-лимиты.md'))
    wait_until(app, lambda: any('Доп-лимиты.md' in str(v) for v in app.db.store.values()))
    app.reload()
    assert 'Доп-лимиты.md' in app.text('#doc-list')
    app.page.click('#btn-run')
    app.wait_idle()
    assert 'Доп-лимиты.md' in app.model.prompts_of('promptAnalyze')[0]


# ---------- закрытая страница ----------
def interrupted_page(app):
    """Первая страница закрыта на запросе кейсов; возвращает вторую, открытую после закрытия."""
    start_held(app, 'promptGenerate')
    close_like_user(app)
    return second_page(app)


def test_closed_page_leaves_interrupted_run_with_banner(held):
    p2 = interrupted_page(held)
    p2.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.status === 'interrupted'")
    p2.tab('agent')
    b = p2.text('.banner.warn')
    assert 'Генерация прервалась, когда страница была закрыта.' in b and 'требований 4, тест-кейсов 0, пунктов чек-листа 4' in b
    assert p2.count('[data-act=resume-run]') == 1 and p2.count('#resume-left') == 1


def test_interrupted_step_is_marked_in_the_log(held):
    p2 = interrupted_page(held)
    p2.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.status === 'interrupted'")
    assert p2.state('S.run.steps.generate.status') == 'stopped'
    assert any('прервано при закрытии страницы' in t for t in p2.state('S.run.steps.generate.log.map((l) => l.text)'))
    assert p2.state('S.running') is False


def test_continue_now_repeats_only_unfinished_requests(held):
    p2 = interrupted_page(held)
    p2.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.status === 'interrupted'")
    p2.tab('agent')
    p2.page.click('[data-act=resume-run]')
    p2.wait_idle()
    assert p2.state('S.run.status') == 'done' and p2.state('S.run.cases.length') == 4
    assert [len(p2.model.calls_of(k)) for k in ('promptAnalyze', 'promptChecklist', 'promptPlan')] == [1, 1, 1]
    assert 'Продолжаю с места остановки — готовые шаги и запросы не повторяются' in ' '.join(p2.state('S.run.steps.generate.log.map((l) => l.text)'))


def test_resumed_cases_have_unique_numbers(held):
    p2 = interrupted_page(held)
    p2.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.status === 'interrupted'")
    p2.page.click('[data-act=resume-run]') if p2.state('S.tab') == 'agent' else (p2.tab('agent'), p2.page.click('[data-act=resume-run]'))
    p2.wait_idle()
    ids = p2.state('S.run.cases.map((c) => c.dispId)')
    assert sorted(ids) == ['API-001', 'API-002', 'E2E-001', 'UI-001']


def test_interrupted_run_resumes_itself_after_countdown(held):
    p2 = interrupted_page(held)
    p2.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.status === 'interrupted'")
    assert p2.state('S.resume.left') <= 5
    p2.page.wait_for_function("() => window.__qa.S.running === true", timeout=15000)
    p2.wait_idle()
    assert p2.state('S.run.status') == 'done' and p2.state('S.run.cases.length') == 4


def test_auto_resume_can_be_cancelled(held):
    p2 = interrupted_page(held)
    p2.page.wait_for_selector('[data-act=resume-cancel]')
    p2.page.click('[data-act=resume-cancel]')
    assert p2.state('S.resume') is None and p2.count('#resume-left') == 0 and p2.state('S.run.status') == 'interrupted'
    assert p2.count('[data-act=resume-run]') == 1


def test_auto_resume_can_be_switched_off(held):
    held.page.uncheck('#auto-resume')
    p2 = interrupted_page(held)
    p2.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.status === 'interrupted'")
    assert p2.state('S.resume') is None and p2.count('#resume-left') == 0 and p2.count('[data-act=resume-run]') == 1


def test_interrupted_actualization_has_its_own_banner_and_keeps_finished_steps(held, tmp_path):
    held.mode('update')
    held.upload_tests(files.cases_json(tmp_path))
    held.upload(files.spec_file(tmp_path, version='2.0'))
    start_held(held, 'promptActualize')
    close_like_user(held)
    p2 = second_page(held)
    p2.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.status === 'interrupted'")
    p2.tab('agent')
    assert 'Актуализация прервалась, когда страница была закрыта.' in p2.text('.banner.warn')
    assert p2.state('S.run.steps.map.status') == 'done'
    p2.page.click('[data-act=resume-run]')
    p2.wait_idle()
    assert p2.state('S.run.status') == 'done' and len(p2.model.calls_of('promptMap')) == 1
    assert p2.state("S.run.cases.filter((c) => c.sourceId).length") == 8


# ---------- вторая вкладка следит за идущей генерацией ----------
def test_second_tab_follows_running_generation(held):
    h = start_held(held, 'promptGenerate')
    p2 = second_page(held)
    p2.page.wait_for_function("() => window.__qa.S.follow !== null")
    p2.tab('agent')
    assert 'Генерация идёт в другой вкладке или на другом устройстве.' in p2.text('.banner.info')
    assert p2.page.is_disabled('#btn-run') and p2.page.is_disabled('#prod-select')
    assert 'Генерация идёт в другой вкладке — дождитесь окончания или остановите её там.' in p2.text('#run-note')
    h.release()
    held.wait_idle()


def test_follower_shows_progress_of_the_running_tab(held):
    start_held(held, 'promptGenerate')
    p2 = second_page(held)
    p2.page.wait_for_function("() => window.__qa.S.follow && window.__qa.S.run && window.__qa.S.run.requirements.length === 4")
    assert p2.state('S.run.steps.analyze.status') == 'done' and p2.state('S.run.status') == 'running'
    assert p2.state('S.run.fromHistory') == 'follow'
    Hold(held.page).release()
    held.wait_idle()


def test_follower_gets_the_result_when_generation_ends(held):
    h = start_held(held, 'promptGenerate')
    p2 = second_page(held)
    p2.page.wait_for_function("() => window.__qa.S.follow !== null")
    h.release()
    held.wait_idle()
    wait_until(held, lambda: run_meta(held).get('status') == 'done' and run_meta(held).get('hb') == 0)
    p2.page.wait_for_function("() => window.__qa.S.follow === null && window.__qa.S.run.status === 'done'", timeout=30000)
    assert p2.state('S.run.cases.length') == 4 and not p2.page.is_disabled('#btn-run') and not p2.page.is_disabled('#prod-select')
    assert 'Генерация в другой вкладке завершена' in ' '.join(p2.toast_texts())


def vanished_tab(app, age_ms):
    """Вкладка с генерацией пропала без прощания (сбой браузера): в базе остался пульс заданной давности."""
    h = start_held(app, 'promptGenerate')
    wait_until(app, lambda: run_meta(app).get('hb') and session(app).get('runningBy'))
    base = run_path(app)
    app.page.close()
    now = int(time.time() * 1000)
    app.db.op('update', base, {'hb': now - age_ms, 'hbTab': 'tab-gone'})
    app.db.op('update', 'data/users/u_test/session', {'runningBy': 'tab-gone', 'heartbeat': now - age_ms})
    return second_page(app), h


def test_tab_that_vanished_long_ago_is_not_followed(held):
    p2, _ = vanished_tab(held, 200000)
    p2.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.status === 'interrupted'")
    assert p2.state('S.follow') is None and p2.state('S.run.fromHistory') is True


def test_tab_with_fresh_pulse_is_still_followed(held):
    p2, _ = vanished_tab(held, 5000)
    p2.page.wait_for_function("() => window.__qa.S.follow !== null")
    assert p2.state('S.run.fromHistory') == 'follow' and p2.page.is_disabled('#btn-run')


def test_closing_page_during_generation_asks_confirmation(held):
    start_held(held, 'promptGenerate')
    with held.page.expect_event('dialog') as ev:
        held.page.close(run_before_unload=True)   # страница не закрывается сама: ждёт ответа на вопрос браузера
    assert ev.value.type == 'beforeunload'
    ev.value.dismiss()
    assert held.state('S.running') is True


def test_closing_idle_page_asks_nothing(app):
    app.generate()
    dialogs = []
    app.page.on('dialog', lambda d: dialogs.append(d.type))
    with app.page.expect_event('close'):
        app.page.close(run_before_unload=True)
    assert dialogs == []


# ---------- блокировка выбора продукта ----------
def test_product_select_is_locked_while_running(held):
    app = held
    app.create_product('Второй продукт')
    app.page.select_option('#prod-select', app.db.paths('products/')[0].split('/')[1])
    app.page.wait_for_function("() => window.__qa.S.docs.length > 0")
    h = start_held(app, 'promptGenerate')
    assert app.page.is_disabled('#prod-select')
    assert app.page.get_attribute('#prod-select', 'title') == 'Переключиться можно после окончания генерации'
    h.release()
    app.wait_idle()
    assert not app.page.is_disabled('#prod-select')


def test_new_run_button_refuses_while_running(held):
    h = start_held(held, 'promptGenerate')
    held.page.click('#btn-newses')
    assert 'Сначала остановите генерацию.' in ' '.join(held.toast_texts()) and held.state('S.run') is not None
    h.release()
    held.wait_idle()


def test_history_cannot_be_opened_while_running(held):
    held.generate()
    finish_saving(held)
    held.tab('history')
    held.page.wait_for_selector('.hrow')
    h = Hold(held.page).on('promptChecklist')   # анализ второго запуска берётся из кэша, поэтому ждём на чек-листе
    held.generate(wait=False)
    h.wait()
    held.call("a.openHistory(S.history[0].id)")
    assert 'Дождитесь окончания текущего запуска.' in ' '.join(held.toast_texts())
    h.release()
    held.wait_idle()


# ---------- пульс запуска ----------
def test_running_run_has_heartbeat_in_database(held):
    h = start_held(held, 'promptGenerate')
    m = wait_until(held, lambda: run_meta(held) if run_meta(held).get('status') == 'running' else None)
    assert m['hbTab'] == held.state('S.tabId') and m['hb'] > 0
    assert abs(m['hb'] - held.js('Date.now()')) < 60000
    s = wait_until(held, lambda: session(held) if session(held).get('runningBy') else None)
    assert s['runningBy'] == held.state('S.tabId') and s['runId'] == held.state('S.run.id')
    h.release()
    held.wait_idle()


def test_heartbeat_is_cleared_when_generation_ends(held):
    held.generate()
    finish_saving(held)
    assert run_meta(held)['hb'] == 0 and not session(held).get('runningBy') and session(held).get('heartbeat') == 0


# ---------- остановка ----------
def test_stop_keeps_finished_work_and_offers_to_continue(held):
    h = start_held(held, 'promptGenerate')
    held.page.click('#btn-stop')
    h.release()
    held.wait_idle()
    assert held.state('S.run.status') == 'stopped' and held.state('S.run.requirements.length') == 4
    held.tab('agent')
    assert 'Остановлено.' in held.text('.banner.warn') and 'Продолжить с места остановки' in held.text('.banner.warn')


def test_continue_after_stop_finishes_the_run(held):
    h = start_held(held, 'promptGenerate')
    held.page.click('#btn-stop')
    h.release()
    held.wait_idle()
    held.tab('agent')
    held.page.click('[data-act=resume-run]')
    held.wait_idle()
    assert held.state('S.run.status') == 'done' and held.state('S.run.cases.length') == 4 and len(held.model.calls_of('promptAnalyze')) == 1


# ---------- автономная версия: база — в браузере ----------
@pytest.fixture
def alone(make_app):
    app = make_app(**standalone())
    connect_ai(app)
    return app


def test_standalone_run_survives_reload(alone):
    alone.generate()
    wait_until(alone, lambda: alone.page.evaluate("() => { const s = JSON.parse(localStorage.getItem('qapro.db:data/users/local/session') || '{}'); return s.runId && !s.runningBy; }"))
    alone.reload()
    alone.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.cases.length === 4")
    assert alone.state('S.run.status') == 'done'


def test_standalone_closed_page_resumes_in_next_tab(alone, tmp_path):
    alone.upload(files.write(tmp_path / 'extra.txt', 'ТЗ: дополнительный документ про лимиты. Не более 3 запросов за 15 минут.'))
    h = start_held(alone, 'promptGenerate')
    alone.page.evaluate("() => window.dispatchEvent(new PageTransitionEvent('pagehide', { persisted: false }))")
    alone.page.wait_for_function("() => { const s = JSON.parse(localStorage.getItem('qapro.db:data/users/local/session') || '{}'); return s.runId && !s.runningBy; }")
    alone.page.close()
    p2 = second_page(alone)
    p2.page.wait_for_function("() => window.__qa.S.run && window.__qa.S.run.status === 'interrupted'")
    assert 'extra.txt' in p2.text('#doc-list')
    p2.tab('agent')
    p2.page.click('[data-act=resume-run]')
    p2.wait_idle()
    assert p2.state('S.run.status') == 'done' and len(p2.model.calls_of('promptAnalyze')) == 1
    ids = p2.state('S.run.cases.map((c) => c.dispId)')
    assert len(ids) == len(set(ids)) >= 4
