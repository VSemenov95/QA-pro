"""Важность проверок: рубрика приоритета, бюджет проверок по приоритету требования, объединение похожих проверок,
ревью ценности, обучение на правках черновика, метрика по эталону и максимальная модель на анализе."""
from tests.support import model_draft as md
from tests.test_draft_review import draft, twice  # noqa: F401
from tests.test_generation import set_outputs

RUN = ("({ settings: { depth: 'standard' }, reqById: { 'R-1': { priority: 'P4_CRITICAL' }, "
       "'R-2': { priority: 'P2_MEDIUM' }, 'R-3': { priority: 'P1_LOW' } } })")


def wait_calls(app, kind):
    for _ in range(100):   # урок учится в фоне: ждём запроса к модели, а не таймаута
        if app.model.calls_of(kind):
            break
        app.page.wait_for_timeout(100)
    return app.model.prompts_of(kind)


# ---------- приоритет задаётся на анализе ----------
def test_check_priority_is_not_above_requirement(app):
    assert app.call(f"a.capPrio({RUN}, 'P4_CRITICAL', ['R-2'])") == 'P2_MEDIUM'
    assert app.call(f"a.capPrio({RUN}, 'P1_LOW', ['R-1'])") == 'P1_LOW'
    assert app.call(f"a.capPrio({RUN}, 'P3_HIGH', ['R-2', 'R-1'])") == 'P3_HIGH'
    assert app.call(f"a.capPrio({RUN}, 'P3_HIGH', [])") == 'P3_HIGH'


def test_prompts_carry_priority_rubric_budget_and_merge_rule(app):
    app.add_sample()
    set_outputs(app, checklist=True)
    app.generate()
    analyze = app.model.prompts_of('promptAnalyze')[0]
    assert 'ломает основной путь' in analyze and 'наследуют его' in analyze
    checklist = app.model.prompts_of('promptChecklist')[0]
    assert 'Бюджет проверок на одно требование' in checklist and 'P4_CRITICAL — до 6' in checklist
    assert 'классу эквивалентности' in checklist and 'ломает основной путь' in checklist


def test_plan_prompt_has_budget_and_merge_rule(app):
    app.add_sample()
    set_outputs(app, checklist=False)
    app.generate()
    plan = app.model.prompts_of('promptPlan')[0]
    assert 'Бюджет проверок на одно требование' in plan and 'классу эквивалентности' in plan
    assert '2–5 проверок на требование' not in plan


# ---------- бюджет проверок ----------
def test_plan_budget_by_requirement_priority(app):
    res = app.call(f"""(() => {{ const run = {RUN}; const items = [
      {{ requirementIds: ['R-1'], checks: Array.from({{ length: 9 }}, (_, k) => 'c' + k) }},
      {{ requirementIds: ['R-2'], checks: ['a', 'b', 'c', 'd'] }},
      {{ requirementIds: ['R-3'], checks: ['x', 'y'] }} ];
      const cut = a.budgetPlan(run, items); return [cut, items.map((i) => i.checks)]; }})()""")
    assert res == [6, [['c0', 'c1', 'c2', 'c3', 'c4', 'c5'], ['a', 'b'], ['x']]]


def test_budget_depends_on_depth(app):
    assert app.call("a.budgetRule('full')").count('P4_CRITICAL — до 10') == 1
    assert app.call("a.CHECK_BUDGET.smoke.P2_MEDIUM") == 1


def test_checklist_budget_keeps_positive_and_single_coverage(app):
    res = app.call(f"""(() => {{ const run = {RUN};
      const it = (check, kind, ids, priority = 'P2_MEDIUM') => ({{ check, kind, type: 'ui', priority, requirementIds: ids }});
      const groups = [{{ title: 'G', items: [it('n1', 'negative', ['R-2']), it('n2', 'negative', ['R-2']), it('p1', 'positive', ['R-2']),
        it('low', 'negative', ['R-3'], 'P1_LOW'), it('free', 'positive', [])] }}];
      const b = a.budgetChecklist(run, groups); return [b.cut, b.groups[0].items.map((i) => i.check)]; }})()""")
    assert res == [1, ['n1', 'p1', 'low', 'free']]


# ---------- ревью: важный сценарий ----------
def test_important_requirement_with_only_negative_checks_is_a_gap(app):
    expr = """(() => { const run = { requirements: [{ id: 'R-1', inScope: true, priority: 'P4_CRITICAL', title: 'Оплата' }, { id: 'R-2', inScope: true, priority: 'P2_MEDIUM', title: 'Фильтр' }],
      checklist: { groups: [{ title: 'G', items: [{ id: 'CL-001', kind: 'negative' }, { id: 'CL-002', kind: 'negative' }, { id: 'CL-003', kind: '%s' }] }] },
      cases: [{ requirementIds: ['R-1'], checklistId: 'CL-001' }, { requirementIds: ['R-1'], checklistId: 'CL-003' }, { requirementIds: ['R-2'], checklistId: 'CL-002' }] };
      return a.mainPathGaps(run).map((r) => r.id); })()"""
    assert app.call(expr % 'negative') == ['R-1']   # P2 с одними негативными — не пропуск важного
    assert app.call(expr % 'positive') == []


# ---------- обучение на правках ----------
def test_dropped_case_becomes_a_lesson_on_add(draft):
    draft.model.on('promptLesson', {'rule': 'Не составляй отдельные кейсы на сквозные сценарии без бизнес-результата', 'scope': 'generation'})
    twice(draft, '.draft-case:has(.mono:text-is("E2E-001")) [data-act=draft-drop]')
    assert draft.state('S.run.edits.dropped.length') == 1
    md.add_to_project(draft)
    prompts = wait_calls(draft, 'promptLesson')
    assert len(prompts) == 1 and 'Удалено как ненужное: [E2E]' in prompts[0]
    assert draft.state('S.run.edits.dropped.length') == 0


def test_priority_change_is_noted_and_untouched_draft_teaches_nothing(app):
    assert app.call("""(() => { const run = {}; a.notePrio(run, 'Кейс', 'P3_HIGH', 'P1_LOW'); a.notePrio(run, 'Кейс', 'P2_MEDIUM', 'medium'); a.notePrio(run, 'Ручной', '', 'P1_LOW'); return run.edits.prio; })()""") == [
        {'title': 'Кейс', 'from': 'P3_HIGH', 'to': 'P1_LOW'}]


def test_add_without_edits_asks_no_lesson(draft):
    md.add_to_project(draft)
    draft.page.wait_for_timeout(300)
    assert draft.model.calls_of('promptLesson') == []


# ---------- метрика по эталону ----------
def test_etalon_metrics_are_normalized_and_summed(app):
    m = app.call("""a.etalonMetrics({ metrics: { etalonChecks: 10, matched: 12, missed: ['Оплата картой'], extra: ['UI-001', 'XX-9'] } }, [{ dispId: 'UI-001' }, { dispId: 'UI-002' }])""")
    assert m == {'total': 10, 'matched': 10, 'missed': ['Оплата картой'], 'extra': ['UI-001']}
    tot = app.call("""a.etalonTotals({ byType: { ui: { n: 2, metrics: { total: 10, matched: 7, missed: [], extra: ['UI-001'] } }, api: { n: 3, metrics: { total: 0, matched: 0, missed: [], extra: [] } } } })""")
    assert tot == {'total': 10, 'matched': 7, 'n': 5, 'extra': 1, 'recall': 70}
    assert app.call("a.etalonTotals({ byType: { ui: { n: 1 } } })") is None


# ---------- модель на анализе ----------
def test_analysis_defaults_to_the_strongest_model_once(app):
    assert app.call("a.stageDefault('analyze', {})") == 'complex'
    assert app.call("a.stageDefault('analyze', { stages: { analyze: 'same' } })") == 'complex'   # прежнее значение по умолчанию
    assert app.call("a.stageDefault('analyze', { stages: { analyze: 'quick' } })") == 'quick'    # выбор пользователя
    assert app.call("a.stageDefault('analyze', { stagesRev: 2, stages: { analyze: 'same' } })") == 'same'   # выбрано после перехода
    assert app.call("a.stageDefault('review', {})") == 'same'
