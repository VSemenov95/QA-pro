"""База знаний в генерации: сводки разделов по теме идут в анализ, чек-лист, план, кейсы и ревью; инструменты агента; лимиты на объём."""
from types import SimpleNamespace

import pytest

from tests.support import files, model_kb
from tests.support.app import open_app

BLOCK = '## База знаний продукта — разделы по теме'
SECTION = 'Раздел «Восстановление пароля»'


def settle(app, n):
    app.page.wait_for_function("(n) => { const S = window.__qa.S; return Object.keys(S.kb.index.docs).length >= n && !S.kb.job.busy && !S.kb.queue.length; }", arg=n, timeout=60000)
    app.wait_idle()


def prepare(app, tmp_path):
    """Пример ТЗ и два документа с разными лимитами разобраны в базу знаний; открыт режим генерации."""
    kb = model_kb.install(app.model)
    app.mode('help')
    app.page.click('[data-act=kb-run]')
    app.wait_idle()
    app.upload(files.write(tmp_path / 'kb_extra.md', model_kb.limits_doc(3)), files.write(tmp_path / 'kb_созвон-call.md', model_kb.call_doc(5)))
    settle(app, 3)
    app.mode('generate')
    app.model.reset()
    return kb


@pytest.fixture(scope='module')
def scenario(browser, tmp_path_factory):
    """Один раз: генерация с базой знаний и ревью. Тесты ниже только читают собранные запросы."""
    app = open_app(browser)
    prepare(app, tmp_path_factory.mktemp('kbgen'))
    intro = app.page.eval_on_selector_all('#tab-body .banner', 'els => els.map(e => e.innerText)')
    app.generate()
    gen = {k: app.model.prompts_of(k) for k in ('promptAnalyze', 'promptChecklist', 'promptPlan', 'promptGenerate')}
    log = app.state('S.run.steps.parse.log.map((l) => l.text)')
    app.tab('review')
    app.page.click('[data-act=start-review]')
    app.wait_idle()
    rev = {k: app.model.prompts_of(k) for k in ('promptReviewCases', 'promptReviewChecklist')}
    yield SimpleNamespace(app=app, intro=intro, gen=gen, log=log, rev=rev)
    errors = list(app.errors)
    app.ctx.close()
    assert not errors, 'ошибки на странице: ' + '; '.join(errors[:3])


def kb_part(prompt):
    return prompt[prompt.index(BLOCK):]


# ---------- что агент говорит перед запуском и в журнале ----------
def test_run_screen_tells_what_will_be_used(scenario):
    banner = next(t for t in scenario.intro if t.startswith('База знаний продукта'))
    assert 'База знаний продукта: 2 раздела · расхождений между документами 1.' in banner
    assert 'агент учтёт на анализе, в чек-листе, плане, тест-кейсах и ревью; по расхождениям задаст вопросы' in banner


def test_run_log_mentions_knowledge_base(scenario):
    assert any(l.startswith('База знаний: 2 раздела из всех документов продукта') for l in scenario.log)


# ---------- в какие запросы попадает ----------
@pytest.mark.parametrize('kind', ['promptAnalyze', 'promptChecklist', 'promptPlan', 'promptGenerate'])
def test_generation_requests_carry_matching_sections(scenario, kind):
    prompts = scenario.gen[kind]
    assert prompts and all(BLOCK in p for p in prompts)
    assert all(SECTION in kb_part(p) for p in prompts)


def test_review_requests_carry_matching_sections(scenario):
    prompts = scenario.rev['promptReviewCases']
    assert prompts and all(SECTION in kb_part(p) for p in prompts)


def test_review_gets_its_own_instruction(scenario):
    p = kb_part(scenario.rev['promptReviewCases'][0])
    assert 'Если кейс противоречит и требованиям, и базе знаний — это замечание' in p


def test_analysis_is_asked_to_raise_questions_on_conflicts(scenario):
    assert 'задай конкретный вопрос в questions' in kb_part(scenario.gen['promptAnalyze'][0])


def test_generation_is_told_to_follow_requirements_on_conflicts(scenario):
    assert 'Приоритет — у требований; спорное из «Расхождений между документами» не используй как ожидаемый результат' in kb_part(scenario.gen['promptGenerate'][0])
    assert 'следуй требованиям; спорное из «Расхождений между документами» не выдавай за факт' in kb_part(scenario.gen['promptPlan'][0])


def test_conflicts_are_marked_in_the_section_header(scenario):
    assert f'### {SECTION} · расхождений между документами: 1' in kb_part(scenario.gen['promptPlan'][0])


def test_documents_outside_the_run_are_visible_through_the_base(scenario):
    """В запуске только пример ТЗ, но сведения из остальных документов продукта попадают в запрос — через базу знаний."""
    p = kb_part(scenario.gen['promptPlan'][0])
    assert '(kb_созвон-call)' in p and 'kb_extra' in p
    assert 'kb_созвон-call' not in scenario.gen['promptPlan'][0].split(BLOCK)[0]


def test_nothing_is_added_when_no_section_matches_the_request(scenario):
    app = scenario.app
    assert app.call("a.kbLoadAll(S.productId).then(() => a.kbGenBlock(null, 'batch', 'квантовая телепортация сырников'))") == ''


def test_request_without_topic_gets_no_block(scenario):
    assert scenario.app.call("a.kbGenBlock(null, 'batch', '')") == ''


# ---------- без базы знаний ----------
def test_no_block_when_the_base_is_empty(app):
    model_kb.install(app.model)
    app.generate()
    assert all(BLOCK not in p for k in ('promptAnalyze', 'promptChecklist', 'promptPlan', 'promptGenerate') for p in app.model.prompts_of(k))
    assert any('База знаний продукта пока пуста' in l for l in app.state('S.run.steps.parse.log.map((l) => l.text)'))


# ---------- инструменты агента ----------
def make_tools(app):
    """Инструменты агента для нового запуска — после загрузки разделов, как перед генерацией."""
    return app.call("""(async () => {
      await a.kbLoadAll(S.productId);
      const run = a.newRun();
      return a.makeTools(run, 'gen_api').map((t) => t.name);
    })()""")


def call_tool(app, name, arg):
    return app.call("""(async () => {
      const t = a.makeTools(a.newRun(), 'gen_api').find((x) => x.name === arg.name);
      return await t.execute(arg.input);
    })()""", {'name': name, 'input': arg})


def test_agent_tools_include_knowledge_base_when_sections_exist(scenario):
    assert make_tools(scenario.app) == ['search_documents', 'read_document', 'search_knowledge_base', 'read_knowledge_section']


def test_agent_has_only_document_tools_without_a_base(app):
    assert app.call("a.makeTools(a.newRun(), 'gen_api').map((t) => t.name)") == ['search_documents', 'read_document']


def test_search_returns_the_best_section_with_conflicts(scenario):
    make_tools(scenario.app)
    found = call_tool(scenario.app, 'search_knowledge_base', {'query': 'лимит запросов на сброс пароля'})
    assert found[0]['title'] == 'Восстановление пароля' and len(found[0]['conflicts']) == 1 and 'не более 3' in found[0]['conflicts'][0]
    assert len(found[0]['text']) <= 1500 and set(found[0]) == {'id', 'title', 'summary', 'conflicts', 'text'}


def test_search_without_matches(scenario):
    make_tools(scenario.app)
    assert call_tool(scenario.app, 'search_knowledge_base', {'query': 'квантовая телепортация'}) == 'Ничего не найдено. Попробуй другие слова.'


def test_read_section_by_id_gives_summary_conflicts_and_links(scenario):
    make_tools(scenario.app)
    sec = call_tool(scenario.app, 'search_knowledge_base', {'query': 'лимит запросов на сброс пароля'})[0]
    one = call_tool(scenario.app, 'read_knowledge_section', {'id': sec['id']})
    assert one['title'] == 'Восстановление пароля' and one['part'] == 1 and one['parts'] == 1
    assert 'Сообщение при превышении' in one['text'] and len(one['conflicts']) == 1 and one['links'] == []


def test_read_section_by_title(scenario):
    make_tools(scenario.app)
    assert call_tool(scenario.app, 'read_knowledge_section', {'id': 'api сброса пароля'})['title'] == 'API сброса пароля'


def test_read_unknown_section(scenario):
    make_tools(scenario.app)
    assert call_tool(scenario.app, 'read_knowledge_section', {'id': 'нет такого'}) == 'Раздел не найден — возьми id из search_knowledge_base.'


def test_long_summary_is_read_by_parts(app):
    model_kb.install(app.model)
    app.mode('help')
    app.page.click('[data-act=kb-run]')
    app.wait_idle()
    app.call("a.kbLoadAll(S.productId)")
    got = app.call("""(async () => {
      const id = S.kb.index.blocks.find((b) => b.title === 'API сброса пароля').id;
      S.kb.cache[id].synth = Array.from({ length: 400 }, (_, i) => '- Пункт ' + i + ': ' + 'ы'.repeat(40)).join('\\n');
      const t = a.makeTools(a.newRun(), 'gen_api').find((x) => x.name === 'read_knowledge_section');
      const p1 = await t.execute({ id }), p2 = await t.execute({ id, part: 2 }), far = await t.execute({ id, part: 99 });
      return { n: p1.parts, lens: [p1.text.length, p2.text.length], p2: p2.part, far: far.part, firstOnly: ['conflicts' in p1, 'conflicts' in p2] };
    })()""")
    assert got['n'] >= 3 and max(got['lens']) <= 6000 and got['p2'] == 2 and got['far'] == got['n'] and got['firstOnly'] == [True, False]


# ---------- объём ----------
FILL = """(async () => {
  await a.kbLoadAll(S.productId);
  for (const x of a.kbSections(S.productId)) {
    x.d.synth = Array.from({ length: 300 }, (_, i) => '- Пункт ' + i + ': экран «Профиль клиента», роль Оператор, поле Email до 254 символов, ответ 202/400/429').join('\\n') + '\\n- Лимит платежей: 5000 рублей в сутки';
  }
  S.settings.economy = !!arg.economy;
  return a.kbGenBlock(null, arg.mode, 'лимит платежей');
})()"""
CAPS = {'single': 12000, 'batch': 8000, 'analyze': 5000, 'review': 5000}


@pytest.fixture
def filled(app):
    model_kb.install(app.model)
    app.mode('help')
    app.page.click('[data-act=kb-run]')
    app.wait_idle()
    return app


@pytest.mark.parametrize('mode', list(CAPS))
def test_block_size_is_capped_per_kind_of_request(filled, mode):
    block = filled.call(FILL, {'mode': mode})
    assert len(block) <= CAPS[mode] + 1500   # лимит на сами сводки и заголовки с вводным абзацем
    assert block.count('### Раздел') <= 8


def test_lines_on_the_topic_survive_trimming(filled):
    block = filled.call(FILL, {'mode': 'analyze'})
    assert 'Лимит платежей: 5000 рублей в сутки' in block


def test_economy_mode_shrinks_the_block(filled):
    normal = filled.call(FILL, {'mode': 'batch'})
    eco = filled.call(FILL, {'mode': 'batch', 'economy': True})
    assert len(eco) < len(normal) and len(eco) <= CAPS['batch'] * 0.6 + 1500


def test_sections_are_ranked_by_title_then_body(app):
    secs = [{'b': {'id': 'a', 'title': 'Оплата картой', 'summary': ''}, 'd': {'synth': '- Описание экрана'}},
            {'b': {'id': 'b', 'title': 'Профиль', 'summary': ''}, 'd': {'synth': '- Лимит оплаты на экране профиля'}},
            {'b': {'id': 'c', 'title': 'Склад', 'summary': ''}, 'd': {'synth': '- Остатки'}}]
    assert app.call("a.kbRank('оплата', arg).map((x) => x.b.id)", secs) == ['a', 'b']   # совпадение с названием весит больше, чем с текстом; лишнее не берётся


def test_rare_words_weigh_more_than_common_ones(app):
    secs = [{'b': {'id': 'a', 'title': 'Раздел один', 'summary': ''}, 'd': {'synth': '- экран экран экран кнопка'}},
            {'b': {'id': 'b', 'title': 'Раздел два', 'summary': ''}, 'd': {'synth': '- экран токен'}},
            {'b': {'id': 'c', 'title': 'Раздел три', 'summary': ''}, 'd': {'synth': '- экран поле'}}]
    assert app.call("a.kbRank('экран токен', arg).map((x) => x.b.id)", secs)[0] == 'b'
