"""Отдельные этапы генерации API, UI, E2E и выгрузка вопросов аналитику (с загрузкой ответов обратно)."""
import openpyxl


def generated(app):
    app.add_sample()
    app.generate()
    return app


# ---------- этапы генерации по видам тестов ----------
def test_generation_runs_type_by_type(app):
    generated(app)
    st = app.state('S.run.steps')
    assert st['gen_api']['t1'] <= st['gen_ui']['t0'] and st['gen_ui']['t1'] <= st['gen_e2e']['t0']   # этапы идут друг за другом
    logs = {t: ' '.join(app.state(f"S.run.steps.gen_{t}.log.map((l) => l.text)")) for t in ('api', 'ui', 'e2e')}
    assert 'API · P-02, P-04' in logs['api'] and 'UI ·' not in logs['api']
    assert 'UI · P-01' in logs['ui'] and 'E2E · P-03' in logs['e2e']


def test_agent_tab_shows_three_generation_steps(app):
    generated(app)
    app.tab('agent')
    text = app.text('#tab-body .timeline')
    assert text.index('Тест-кейсы API') < text.index('Тест-кейсы UI') < text.index('Тест-кейсы E2E') < text.index('Проверка покрытия')
    assert 'Генерация тест-кейсов' not in text


def test_unselected_type_step_is_skipped(app):
    app.add_sample()
    app.page.click('.type-opt[data-t=e2e]')
    app.generate()
    assert app.state('S.run.steps.gen_e2e.status') == 'skipped'
    assert app.state('S.run.steps.gen_api.status') == 'done' and app.state('S.run.status') == 'done'
    assert not any('E2E ·' in c.prompt[:4000] for c in app.model.calls_of('promptGenerate') if 'P-03' in c.prompt)


def test_failed_type_marks_only_its_step(app):
    app.add_sample()
    from tests.support.model import DEFAULTS
    app.model.on('promptGenerate', lambda c: {'cases': []} if c.index == 1 else DEFAULTS['promptGenerate'](c))   # второй запрос — этап UI
    app.generate()
    assert app.state('S.run.steps.gen_ui.status') == 'error'
    assert app.state('S.run.steps.gen_api.status') == 'done' and app.state('S.run.steps.gen_e2e.status') == 'done'


def test_legacy_run_with_single_generate_step_opens_as_done(app):
    generated(app)
    app.page.wait_for_timeout(2500)
    rid = app.state('S.run.id')
    # запуск, сохранённый до разделения этапов: вместо gen_* — один этап «generate»
    app.call("""(async () => {
      const db = S.caps.db, ref = db.doc(`products/${S.productId}/runs/${arg}`), m = (await ref.get()).data();
      const g = m.steps.gen_api; g.log = [...m.steps.gen_api.log, ...m.steps.gen_ui.log, ...m.steps.gen_e2e.log];
      m.steps.generate = g; delete m.steps.gen_api; delete m.steps.gen_ui; delete m.steps.gen_e2e;
      await ref.set(m); return true; })()""", rid)
    app.reload()
    app.call('a.openHistory(arg)', rid)
    app.page.wait_for_function('() => window.__qa.S.run && window.__qa.S.run.id === ' + repr(rid))
    assert [app.state(f'S.run.steps.gen_{t}.status') for t in ('api', 'ui', 'e2e')] == ['done'] * 3
    assert 'UI · P-01' in ' '.join(app.state('S.run.steps.gen_ui.log.map((l) => l.text)'))
    assert app.state('a.S.run && !window.__qa.S.running') and app.count('#tab-body [data-act=resume-run]') == 0


# ---------- вопросы аналитику ----------
def test_questions_letter_and_markdown(app):
    generated(app)
    app.tab('questions')
    letter = app.call('a.questionsLetter(S.run)')
    q = app.state('S.run.questions[0]')
    assert f"1. [{q['id']}] {q['text']}" in letter and 'Пример — ТЗ восстановление пароля.md' in letter
    md = app.call('a.questionsMarkdown(S.run)')
    assert f"## {q['id']}" in md and '_нет ответа_' in md


def test_questions_xlsx_download(app):
    generated(app)
    app.tab('questions')
    app.page.click('[data-act=q-xlsx]')
    app.page.wait_for_function('() => (window.__downloads || []).length === 1')
    assert app.downloads()[0]['filename'].startswith('questions_') and app.downloads()[0]['filename'].endswith('.xlsx')
    exp = app.call('a.questionsExport(S.run)')
    assert exp['columns'][:4] == ['ID', 'Вопрос', 'Ответ', 'Статус'] and exp['rows'][0][3] == 'Нет ответа'


def test_letter_lists_only_unanswered(app):
    generated(app)
    app.call("(S.run.questions.push({ id: 'Q-99', text: 'Второй вопрос', answer: 'Уже ответили', appliedAnswer: '' }), true)")
    letter = app.call('a.questionsLetter(S.run)')
    assert 'Второй вопрос' not in letter


def test_answers_are_loaded_back_from_xlsx(app, tmp_path):
    generated(app)
    app.tab('questions')
    q = app.state('S.run.questions[0]')
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(['ID', 'Вопрос', 'Ответ', 'Статус'])
    ws.append([q['id'], q['text'], 'Лимит — 3 запроса в час', 'Нет ответа'])
    ws.append(['Q-77', 'Чужой вопрос', 'игнор', ''])
    path = tmp_path / 'answers.xlsx'
    wb.save(path)
    app.page.set_input_files('#q-file', str(path))
    app.page.wait_for_function("() => window.__qa.S.run.questions[0].answer === 'Лимит — 3 запроса в час'")
    assert app.page.input_value(f"textarea[data-q='{q['id']}']") == 'Лимит — 3 запроса в час'
    assert 'не учтён' in app.text(f"#q-{q['id']}")
