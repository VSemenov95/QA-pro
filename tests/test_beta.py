"""Бета-функции: матрица покрытия, ревью ТЗ, регресс к релизу, автотесты, дефект в Сфера.Задачи."""
from tests.support.model import ModelError

CASES = [
    {'r': 'run1', 'i': 'API-001', 't': 'api', 'n': 'Запрос сброса пароля для существующего email'},
    {'r': 'run1', 'i': 'API-002', 't': 'api', 'n': 'Лимит запросов сброса'},
    {'r': 'run1', 'i': 'UI-001', 't': 'ui', 'n': 'Ссылка «Забыли пароль?» на экране входа'},
]


def generated(app):
    app.add_sample()
    app.generate()
    return app


# ---------- матрица покрытия ----------
def test_coverage_counts_cases_by_type(app):
    generated(app)
    rows = app.state('a.covRows(S.run).map((x) => [x.q.id, x.by, x.state])')
    by = {r[0]: r for r in rows}
    assert by['R-002'][1]['api'] == 1 and by['R-002'][2] == 'ok'   # API-001; E2E-001 тоже ссылается на R-002, но это кейс другого вида
    app.tab('cov')
    assert app.count('table.cov tbody tr') == len(rows)


def test_coverage_shows_gap_and_filters(app):
    generated(app)
    app.call("(S.run.cases = S.run.cases.filter((c) => !c.requirementIds.includes('R-001')), true)")
    app.tab('cov')
    assert 'нет кейсов' in app.text('table.cov')
    gaps = app.state("a.covRows(S.run).filter((x) => x.state !== 'ok').length")
    app.page.click('[data-act=cov-filter][data-f=gaps]')
    assert gaps >= 1 and app.count('table.cov tbody tr') == gaps
    assert app.visible('table.cov [data-act=cover-req]')


def test_coverage_xlsx(app):
    generated(app)
    app.tab('cov')
    app.page.click('[data-act=cov-xlsx]')
    app.page.wait_for_function('() => (window.__downloads || []).length === 1')
    assert app.downloads()[0]['filename'].startswith('coverage_')


# ---------- ревью ТЗ ----------
def run_spec(app):
    generated(app)
    app.tab('specrev')
    app.page.click('[data-act=spec-run]')
    app.page.wait_for_selector('.spec-item')


def test_spec_review_findings_are_normalized(app):
    run_spec(app)
    items = app.state('S.run.specReview.items')
    assert len(items) == 3
    assert items[0]['reqIds'] == ['R-003', 'R-004']          # выдуманный R-999 отброшен
    assert items[2]['kind'] == 'ambiguity' and items[2]['severity'] == 'major'
    prompt = app.model.prompts_of('promptSpecReview')[0]
    assert 'R-001' in prompt and '<document name=' in prompt


def test_spec_review_ask_adds_question_and_letter(app):
    run_spec(app)
    n = app.state('S.run.questions.length')
    app.page.click('.spec-item[data-id="T-01"] [data-st=ask]')
    assert app.state('S.run.questions.length') == n + 1
    letter = app.call('a.specLetter(S.run)')
    assert 'Какой срок действия ссылки' in letter and '«ссылка действует 30 минут / 24 часа»' in letter
    app.page.click('.spec-item[data-id="T-01"] [data-st=ask]')       # повторное нажатие снимает
    assert app.state('S.run.questions.length') == n


def test_spec_review_accept_adds_criterion(app):
    run_spec(app)
    app.page.click('.spec-item[data-id="T-01"] [data-st=accepted]')
    assert app.state("S.run.reqById['R-003'].criteria.includes('Ссылка действует 30 минут, повторный запрос аннулирует предыдущую')")


def test_spec_review_dismiss_becomes_lesson(app):
    run_spec(app)
    app.page.click('.spec-item[data-id="T-02"] [data-st=dismissed]')
    app.page.wait_for_function("() => window.__qa.S.lessons.some((l) => l.text.includes('«Быстро» не проверяется'))")


def test_spec_review_survives_reload(app):
    run_spec(app)
    app.page.click('.spec-item[data-id="T-01"] [data-st=ask]')
    app.page.wait_for_timeout(2500)
    rid = app.state('S.run.id')
    app.reload()
    app.call('a.openHistory(arg)', rid)
    app.page.wait_for_function('() => window.__qa.S.run && window.__qa.S.run.specReview')
    assert app.state('S.run.specReview.items[0].status') == 'ask'


# ---------- регресс ----------
def seed_index(app):
    app.call('(S.prodIndex = { pid: S.productId, cases: arg, checklist: [] }, true)', CASES)


def test_parse_defect_lines(app):
    out = app.call("a.parseDefectLines('RECOV-311 — Ссылка не аннулируется\\nAUTH-7: Счётчик\\nпросто текст')")
    assert out == [{'key': 'RECOV-311', 'title': 'Ссылка не аннулируется'}, {'key': 'AUTH-7', 'title': 'Счётчик'}, {'key': '', 'title': 'просто текст'}]


def test_regress_mode_selects_cases(app):
    seed_index(app)
    app.mode('regress')
    assert not app.page.is_visible('#tabs')
    app.page.fill('#reg-defects', 'RECOV-318 — 500 при «+» в email')
    app.page.dispatch_event('#reg-defects', 'input')
    app.page.click('[data-act=reg-run]')
    app.page.wait_for_selector('table.reg-t')
    res = app.state('S.regress.result')
    ids = {c['id']: c for c in res['cases']}
    assert set(ids) == {'API-001', 'UI-001', 'API-002'}           # API-999 выдуман, API-002 — устарел, значит обязателен
    assert ids['API-002']['decision'] == 'must' and ids['API-002']['outdated']
    prompt = app.model.prompts_of('promptRegress')[0]
    assert 'RECOV-318: 500 при «+» в email' in prompt and 'API-001 [API]' in prompt
    assert 'Вход по SMS' in app.text('.reg-gaps')


def test_regress_uses_product_defects(app):
    seed_index(app)
    app.call("(S.defects = { pid: S.productId, items: [{ id: 'D-001', title: 'Сохранение правила возвращает 500', severity: 'critical', actual: '500', location: 'TimeBasedRuleDto' }], loaded: true, open: null }, true)")
    app.mode('regress')
    app.page.check('.reg-pick[data-id="D-001"]')
    app.page.click('[data-act=reg-run]')
    app.page.wait_for_selector('table.reg-t')
    assert 'D-001: Сохранение правила возвращает 500 | было: 500 | место сбоя: TimeBasedRuleDto' in app.model.prompts_of('promptRegress')[0]


def test_regress_result_survives_reload(app):
    seed_index(app)
    app.mode('regress')
    app.page.fill('#reg-defects', 'RECOV-318 — 500')
    app.page.dispatch_event('#reg-defects', 'input')
    app.page.click('[data-act=reg-run]')
    app.page.wait_for_selector('table.reg-t')
    app.page.wait_for_timeout(500)
    app.reload()
    app.page.wait_for_selector('table.reg-t')


def test_regress_needs_product_cases(app):
    app.mode('regress')
    assert app.page.is_disabled('[data-act=reg-run]')


# ---------- автотесты ----------
PROJECT = [
    {'path': 'build.gradle', 'text': "plugins { id 'java' }\njava { toolchain { languageVersion = JavaLanguageVersion.of(17) } }\ndependencies { testImplementation 'io.rest-assured:rest-assured:5.4.0'\n testImplementation 'org.junit.jupiter:junit-jupiter:5.10.0'\n testImplementation 'io.qameta.allure:allure-junit5:2.25.0' }"},
    {'path': 'src/test/java/ru/team/api/AuthApi.java', 'text': 'package ru.team.api;\npublic class AuthApi {\n    public static Response requestReset(String email) { return null; }\n    public static Response login(String user, String pass) { return null; }\n}'},
    {'path': 'src/test/java/ru/team/api/Specs.java', 'text': 'package ru.team.api;\npublic class Specs {\n    public static ResponseSpecification responseSpec(int code) { return null; }\n}'},
    {'path': 'src/test/java/ru/team/tests/api/PasswordResetTests.java', 'text': 'package ru.team.tests.api;\n\nimport org.junit.jupiter.api.Test;\n\npublic class PasswordResetTests extends ApiTestBase {\n    @Test\n    @DisplayName("Сброс для неизвестного email")\n    void unknownEmail() {\n        AuthApi.requestReset("x@y.ru");\n    }\n}\n'},
]


def test_scan_project(app):
    scan = app.call('a.scanProject(arg)', PROJECT)
    assert 'Java 17' in scan['stack'] and 'RestAssured' in scan['stack'] and 'JUnit 5' in scan['stack'] and 'Allure' in scan['stack']
    cat = {c['cls']: c for c in scan['catalog']}
    assert cat['AuthApi']['kind'] == 'API-клиенты' and 'requestReset(String email)' in cat['AuthApi']['methods']
    assert cat['Specs']['kind'] == 'Спецификации'
    assert scan['testClasses'][0]['cls'] == 'PasswordResetTests'


def test_merge_java_adds_method_and_import(app):
    out = app.call("a.mergeJava(arg, '@Test\\nvoid x() {\\n    y();\\n}', ['import static org.assertj.core.api.Assertions.assertThat;', 'import org.junit.jupiter.api.Test;'])", PROJECT[3]['text'])
    assert out.count('import org.junit.jupiter.api.Test;') == 1
    assert 'import static org.assertj.core.api.Assertions.assertThat;' in out
    assert out.rstrip().endswith('}') and '    void x() {' in out and out.index('void x()') > out.index('unknownEmail')


def connect_project(app):
    app.tab('auto')
    # «только чтение» из файлов — тот же путь, что после выбора папки или архива
    app.page.evaluate("(files) => window.__qa.autoConnectFiles(files)", PROJECT)
    app.page.wait_for_function('() => window.__qa.S.autoProj && !window.__qa.S.autoUI.busy', timeout=30000)


def test_auto_profile_and_generation(app):
    generated(app)
    connect_project(app)
    assert 'RestAssured' in app.text('#tab-body')
    prompt = app.model.prompts_of('promptAutoProfile')[0]
    assert 'AuthApi — requestReset(String email)' in prompt and 'PasswordResetTests' in prompt
    app.page.click('[data-act=auto-view][data-v=tests]')
    app.page.click('[data-act=auto-all]')
    app.page.click('[data-act=auto-gen]')
    app.page.wait_for_function('() => !window.__qa.S.autoUI.busy && window.__qa.S.run.auto?.items.length')
    items = app.state('S.run.auto.items')
    assert len(items) == 4
    assert items[0]['mode'] == 'append' and items[0]['reused'] == ['AuthApi.requestReset', 'Specs.responseSpec']   # Ghost.method отброшен
    gen = app.model.prompts_of('promptAutoTest')[0]
    assert 'AuthApi — requestReset(String email)' in gen and 'PasswordResetTests.java (1 тестов)' in gen
    assert app.count('.auto-item .k-re') > 0


def test_auto_files_patch_existing_class(app):
    generated(app)
    connect_project(app)
    app.page.click('[data-act=auto-view][data-v=tests]')
    app.page.click('[data-act=auto-all]')
    app.page.click('[data-act=auto-gen]')
    app.page.wait_for_function('() => !window.__qa.S.autoUI.busy && window.__qa.S.run.auto?.items.length')
    out = app.call('a.autoBuildFiles(S.run.auto.items.slice(0, 1)).then((r) => ({ files: [...r.files], notes: r.notes }))')
    files = dict(out['files'])
    patched = files['src/test/java/ru/team/tests/api/PasswordResetTests.java']
    assert 'unknownEmail' in patched and 'resetReturns200' in patched
    assert 'responseSpec429' in files['src/test/java/ru/team/api/Specs.java'] and 'responseSpec(int code)' in files['src/test/java/ru/team/api/Specs.java']
    assert out['notes'] == []
    out2 = app.call("a.autoBuildFiles([{ ...S.run.auto.items[0], added: [{ what: 'X.y()', why: '', path: 'src/Nope.java', mode: 'append', code: 'void y() {}' }] }]).then((r) => r.notes)")
    assert out2 == ['src/Nope.java: не найден — «X.y()» добавьте вручную']


def test_auto_without_project(app):
    generated(app)
    app.tab('auto')
    assert 'Проект ещё не подключён' in app.text('#tab-body')


# ---------- дефект в Сфера.Задачи ----------
def test_sfera_task_args_and_html(app):
    d = {'title': 'Заголовок', 'severity': 'critical', 'priority': 'high', 'component': 'Backend', 'environment': '', 'preconditions': ['Админ'], 'steps': ['Шаг <1>'], 'expected': 'ок', 'actual': '500', 'analysis': 'NPE', 'fields': [{'name': 'Версия', 'value': '1.2'}], 'relatedCases': ['API-001'], 'stack': ''}
    args = app.call("a.sferaTaskArgs(arg, { project: ' RECOV ', type: '', assignee: '', release: 'R2', labels: 'QA_pro, beta' })", d)
    assert args['project'] == 'RECOV' and args['type'] == 'Дефект' and args['labels'] == ['QA_pro', 'beta'] and args['severityRu'] == 'Критичный'
    assert '<ol><li>Шаг &lt;1&gt;</li></ol>' in args['description'] and 'Версия: 1.2' in args['description']


def test_sfera_task_without_uploader_explains(app):
    from tests.test_defect import make_defect
    make_defect(app)
    app.page.fill('#sf-project', 'RECOV')
    app.page.dispatch_event('#sf-project', 'input')
    app.page.click('[data-act=sf-create]')
    app.page.wait_for_selector('.sfera-task .banner.err', timeout=15000)
    assert 'Нужен загрузчик Сферы' in app.text('.sfera-task')
