"""Вопросы к базе знаний (режим «База знаний» → «Вопросы»): ответ только по базе с источниками, «нет в базе», частичный ответ, история, открытые вопросы."""
import re

import pytest

from tests.support import model_kb
from tests.support.model import ModelError

PASSPORT = """## Назначение и границы
- Восстановление пароля в личном кабинете
## Бизнес-правила и ограничения
- Не более 3 запросов на сброс за 15 минут
## Открытые вопросы
- Что происходит при 4-м запросе через UI?"""
SUGGEST_LIMITS = 'Какие ограничения и лимиты описаны?'
Q_PAY = 'Как работает оплата картой?'
Q_ROLES = 'Какие роли есть?'
Q_FLOW = 'Как работает восстановление пароля?'


def answered(app, n):
    app.page.wait_for_function("(n) => document.querySelectorAll('#help-list .hq-a:not(.st-pending)').length >= n", arg=n, timeout=30000)
    app.wait_idle()


def ask(app, text, n):
    app.page.fill('#help-input', text)
    app.page.press('#help-input', 'Enter')
    answered(app, n)


def last(app):
    return app.page.evaluate("() => { const q = [...document.querySelectorAll('#help-list .hq')].pop(); return { text: q.innerText, status: [...q.querySelector('.hq-a').classList].find((c) => c.startsWith('st-')), badge: q.querySelector('.hq-badge')?.textContent, answer: q.querySelector('.md')?.innerText || '', sources: [...q.querySelectorAll('.hq-src .chip')].map((e) => e.textContent), foot: q.querySelector('.hq-foot')?.innerText || '', hint: [...q.querySelectorAll('.hint')].map((e) => e.textContent) }; }")


def help_prompts(app):
    return app.model.prompts_of('promptHelp')


def add_draft(app):
    app.tab('draft')
    app.page.click('[data-act=draft-add]')
    app.page.wait_for_function('() => window.__qa.S.prodIndex.cases.length > 0')


@pytest.fixture
def qa(app):
    """Продукт с примером ТЗ, сделанной генерацией (кейсы в продукте), разделами базы знаний и знаниями о продукте. Открыта вкладка «Вопросы»."""
    model_kb.install(app.model)
    app.generate()
    add_draft(app)
    app.mode('help')
    app.page.click('[data-act=kb-run]')
    app.wait_idle()
    app.call('a.savePassport(S.productId, arg, null)', PASSPORT)   # паспорт известен точно: автоматическое изучение документов его уже менялось
    app.page.click('[data-act=help-view][data-v=qa]')
    app.page.wait_for_selector('#help-input')
    app.model.reset()
    return app


# ---------- режим ----------
def test_help_mode_hides_generation_panels(app):
    app.mode('help')
    hidden = app.page.evaluate("() => ({ tabs: document.querySelector('#tabs').hidden, run: document.querySelector('.run-panel').hidden, rules: document.querySelector('#rules-panel').hidden, params: document.querySelector('#outs').closest('.field').hidden, newses: document.querySelector('#btn-newses').hidden, docs: document.querySelector('#docs-panel').hidden })")
    assert hidden == {'tabs': True, 'run': True, 'rules': True, 'params': True, 'newses': True, 'docs': False}


def test_leaving_help_mode_returns_generation_panels(app):
    app.mode('help')
    app.mode('generate')
    assert app.visible('#tabs') and app.visible('#btn-run')


def test_empty_history_offers_suggestions(qa):
    assert qa.count('[data-act=help-suggest]') == 5
    assert 'Какие роли и права есть в продукте?' in qa.text('#help-list')


def test_header_summarizes_what_the_base_has(qa):
    line = qa.text('.kb-line')
    for part in ('разделов 2', 'знания о продукте', 'документов 1', 'тест-кейсов 4', 'пунктов чек-листа 4'):
        assert part in line, line


# ---------- ответ по базе знаний ----------
def test_suggestion_click_asks_the_question(qa):
    qa.page.click(f'[data-act=help-suggest][data-q="{SUGGEST_LIMITS}"]')
    answered(qa, 1)
    a = last(qa)
    assert SUGGEST_LIMITS in a['text'] and a['status'] == 'st-answered' and a['badge'] == 'Ответ по базе знаний'
    assert 'Не более 3 запросов на сброс за 15 минут' in a['answer'] and qa.count('[data-act=help-suggest]') == 0


def test_prompt_has_the_question_and_labelled_knowledge_blocks(qa):
    ask(qa, Q_FLOW, 1)
    p = help_prompts(qa)[0]
    assert Q_FLOW in p.split('## Вопрос\n')[1]
    labels = re.findall(r'(?m)^\[([A-Z]+\d*)\] (.+)$', p)
    ids = {l[0] for l in labels}
    assert {'B1', 'K1', 'D1'} <= ids   # раздел базы знаний, знания о продукте, фрагмент документа
    assert any(l[1].startswith('Раздел «Восстановление пароля»') for l in labels)
    assert any(l[1].startswith('Знания о продукте — «') for l in labels)


def test_enter_sends_and_shift_enter_does_not(qa):
    qa.page.fill('#help-input', 'Первая строка')
    qa.page.press('#help-input', 'Shift+Enter')
    assert qa.count('#help-list .hq') == 0 and qa.model.calls_of('promptHelp') == []
    qa.page.press('#help-input', 'Enter')
    answered(qa, 1)
    assert qa.page.input_value('#help-input') == ''


def test_sources_are_listed_and_unknown_ids_dropped(qa):
    def handler(call):
        case_id = re.search(r'\n(API-\d+|UI-\d+|E2E-\d+) \[', call.prompt).group(1)
        return {'status': 'answered', 'answer': 'Ответ', 'sources': ['B1', 'K1', case_id, 'X-999'], 'missing': ''}
    qa.model.on('promptHelp', handler)
    ask(qa, Q_FLOW, 1)
    src = last(qa)['sources']
    assert src[0] == 'Раздел «Восстановление пароля»' and src[1].startswith('Знания о продукте — «')
    assert re.fullmatch(r'Кейс (API|UI|E2E)-\d+', src[2]) and len(src) == 3   # выдуманный X-999 в источники не попал


def test_section_source_opens_the_section(qa):
    qa.model.on('promptHelp', {'status': 'answered', 'answer': 'Ответ', 'sources': ['B1'], 'missing': ''})
    ask(qa, Q_FLOW, 1)
    qa.page.click('#help-list .hq-src .chip-link')
    qa.page.wait_for_selector('.kb-art h3')
    assert qa.text('.kb-title-row h3') == 'Восстановление пароля'


def test_answer_without_sources_is_marked_partial(qa):
    qa.model.on('promptHelp', {'status': 'answered', 'answer': 'Лимит 3 запроса', 'sources': [], 'missing': ''})
    ask(qa, Q_FLOW, 1)
    a = last(qa)
    assert a['status'] == 'st-partial' and a['badge'] == 'Частичный ответ'
    assert any('Модель не указала источник' in h for h in a['hint'])


def test_not_found_answer(qa):
    ask(qa, Q_PAY, 1)
    a = last(qa)
    assert a['status'] == 'st-not_found' and a['badge'] == 'Нет в базе знаний'
    assert 'нет сведений об оплате картой' in a['answer'] and 'Не хватает в базе знаний: Описание оплаты' in ' '.join(a['hint'])


def test_partial_answer_says_what_is_missing(qa):
    ask(qa, Q_ROLES, 1)
    a = last(qa)
    assert a['status'] == 'st-partial' and a['badge'] == 'Частичный ответ'
    assert 'Известно только про экран' in a['answer'] and 'Не хватает в базе знаний: Нет описания ролей' in ' '.join(a['hint'])


def test_unknown_status_is_treated_as_partial(qa):
    qa.model.on('promptHelp', {'status': 'maybe', 'answer': 'Возможно', 'sources': ['K1'], 'missing': ''})
    ask(qa, Q_FLOW, 1)
    assert last(qa)['status'] == 'st-partial'


def test_model_error_is_shown_and_not_cached(qa):
    qa.model.on('promptHelp', ModelError('rate_limited'))
    ask(qa, Q_FLOW, 1)
    assert last(qa)['status'] == 'st-error' and 'лимит' in last(qa)['answer'].lower()
    qa.model.on('promptHelp', {'status': 'answered', 'answer': 'Теперь работает', 'sources': ['K1'], 'missing': ''})
    ask(qa, Q_FLOW, 2)
    assert last(qa)['status'] == 'st-answered' and len(help_prompts(qa)) == 2


def test_nothing_relevant_is_answered_without_model(qa):
    """Если по теме вопроса нет ни фрагментов знаний, ни документов, ни кейсов — модель не нужна."""
    qa.call('a.savePassport(S.productId, arg, null)', ('## Назначение и границы\n' + '\n'.join(f'- Пункт {i}: экран «Профиль», роль Оператор, поле Email до 254 символов' for i in range(120))))
    qa.model.reset()
    ask(qa, 'Квантовая телепортация сырников', 1)
    a = last(qa)
    assert a['status'] == 'st-not_found' and 'нет сведений по этому вопросу' in a['answer'] and 'без запроса к модели' in a['foot']
    assert help_prompts(qa) == []


def test_empty_knowledge_base_is_answered_without_model(app):
    model_kb.install(app.model)
    app.mode('help')
    btn = '#doc-list li [data-doc-act=remove]'
    app.page.click(btn)
    app.page.click(btn)
    app.page.wait_for_function('() => window.__qa.S.docs.length === 0')
    app.page.click('[data-act=help-view][data-v=qa]')
    ask(app, 'Что умеет продукт?', 1)
    assert 'База знаний продукта пуста' in last(app)['answer'] and app.model.calls_of('promptHelp') == []


def test_previous_question_is_given_as_context(qa):
    ask(qa, Q_FLOW, 1)
    ask(qa, Q_ROLES, 2)
    first, second = help_prompts(qa)
    assert 'Предыдущий вопрос в этом диалоге' not in first
    assert 'Предыдущий вопрос в этом диалоге' in second and f'Вопрос: {Q_FLOW}' in second


# ---------- повторный вопрос ----------
def test_repeated_question_is_answered_from_history(qa):
    ask(qa, SUGGEST_LIMITS, 1)
    ask(qa, SUGGEST_LIMITS.upper(), 2)   # регистр и пробелы не важны
    a = last(qa)
    assert a['status'] == 'st-answered' and 'из истории: база знаний не менялась, без запроса к модели' in a['foot']
    assert len(help_prompts(qa)) == 1


def test_changed_knowledge_base_invalidates_repeated_answer(qa):
    ask(qa, SUGGEST_LIMITS, 1)
    qa.call('a.savePassport(S.productId, arg, null)', PASSPORT + '\n- Ссылка действует 30 минут')
    ask(qa, SUGGEST_LIMITS, 2)
    assert len(help_prompts(qa)) == 2 and 'из истории' not in last(qa)['foot']


def test_history_survives_reload(qa):
    ask(qa, SUGGEST_LIMITS, 1)
    ask(qa, Q_PAY, 2)
    qa.reload()
    qa.mode('help')
    qa.page.click('[data-act=help-view][data-v=qa]')
    assert qa.count('#help-list .hq') == 2 and 'Нет в базе знаний' in qa.state("document.querySelector('#help-list').textContent")
    assert qa.text('[data-act=help-view][data-v=qa] .cnt') == '2'


def test_history_is_cleared_with_confirmation(qa):
    ask(qa, Q_ROLES, 1)
    qa.page.click('[data-act=help-clear]')
    assert qa.count('#help-list .hq') == 1   # первое нажатие только просит подтверждения
    qa.page.click('[data-act=help-clear]')
    qa.page.wait_for_function("() => document.querySelectorAll('#help-list .hq').length === 0")
    qa.reload()
    qa.mode('help')
    qa.page.click('[data-act=help-view][data-v=qa]')
    assert qa.count('#help-list .hq') == 0


# ---------- открытые вопросы ----------
def test_open_questions_of_the_product_are_listed(qa):
    assert 'Открытые вопросы продукта · 1' in qa.text('#help-open') and 'Что происходит при 4-м запросе через UI?' in qa.text('#help-open')


def test_unanswered_question_goes_to_open_questions(qa):
    ask(qa, Q_PAY, 1)
    qa.page.click('#help-list .hq:last-child [data-act=help-open-add]')
    qa.page.wait_for_function("() => /Открытые вопросы продукта · 2/.test(document.querySelector('#help-open').textContent)")
    assert 'в открытых вопросах' in last(qa)['foot']
    passport = qa.state('S.products.find((p) => p.id === S.productId).passport.text')
    assert re.search(r'## Открытые вопросы\n- Что происходит при 4-м запросе через UI\?\n- Как работает оплата картой\? \(из базы знаний, \d\d\.\d\d\.\d{4}\)$', passport)


def test_answered_question_cannot_be_added_to_open_questions(qa):
    ask(qa, SUGGEST_LIMITS, 1)
    assert qa.count('[data-act=help-open-add]') == 0


def test_team_answer_closes_the_open_question(qa):
    ask(qa, Q_PAY, 1)
    qa.page.click('#help-list .hq:last-child [data-act=help-open-add]')
    qa.page.wait_for_function("() => /Открытые вопросы продукта · 2/.test(document.querySelector('#help-open').textContent)")
    qa.page.click('[data-act=help-ans-open] >> nth=-1')
    qa.page.fill('[data-help-ans]', 'Оплата картой в этом релизе не поддерживается')
    qa.page.press('[data-help-ans]', 'Enter')
    qa.page.wait_for_function("() => /Открытые вопросы продукта · 1/.test(document.querySelector('#help-open').textContent)")
    passport = qa.state('S.products.find((p) => p.id === S.productId).passport.text')
    assert 'Как работает оплата картой?' not in passport.split('## Уточнения команды')[0]
    assert re.search(r'## Уточнения команды\n- Как работает оплата картой\? — Оплата картой в этом релизе не поддерживается \(ответ команды, \d\d\.\d\d\.\d{4}\)', passport)


def test_empty_team_answer_is_not_saved(qa):
    qa.page.click('[data-act=help-ans-open]')
    qa.page.click('[data-act=help-ans-save]')
    assert 'Что происходит при 4-м запросе через UI?' in qa.state('S.products.find((p) => p.id === S.productId).passport.text')


# ---------- поиск по смыслу ----------
Q_SENSE = 'Что делать пользователю, который не помнит секрет для авторизации?'


def test_search_by_meaning_adds_synonyms_and_sections(qa):
    """В вопросе нет слов из документов — раздел и термины подсказывает быстрая модель."""
    ask(qa, Q_SENSE, 1)
    assert qa.model.kb.expand_calls == 1
    p = help_prompts(qa)[0]
    assert 'Раздел «Восстановление пароля»' in p and '«Забыли пароль?»' in p   # термины из подсказки нашли фрагмент документа
    assert qa.state('S.help.items.at(-1).terms') == qa.model.kb.expand_terms


def test_search_by_meaning_runs_on_the_fast_model(qa):
    ask(qa, Q_SENSE, 1)
    expand = qa.model.calls_of('promptHelpExpand')[0]
    assert expand.info['modelTier'] == 'quick'
    assert Q_SENSE in expand.prompt.split('## Вопрос\n')[1] and 'Восстановление пароля' in expand.prompt   # модель видит названия разделов


def test_question_without_hints_still_gets_an_answer(qa):
    qa.model.on('promptHelpExpand', ModelError('invalid_json', 'ответ не JSON'))
    ask(qa, Q_FLOW, 1)
    assert last(qa)['status'] == 'st-partial' and 'Известно только про экран' in last(qa)['answer']
    assert len(help_prompts(qa)) == 1   # поиск по словам вопроса сработал без подсказки


# ---------- автономная версия ----------
@pytest.fixture
def standalone_qa(make_app):
    app = make_app(kind='standalone', local_storage={'qapro.conns': [model_kb.CONN]}, settings={'genAI': 'conn:aiX', 'mode': 'help'})
    model_kb.install(app.model)
    model_kb.serve_openai(app)
    app.page.click('[data-act=help-view][data-v=qa]')
    return app


def test_standalone_answers_from_documents_when_there_is_no_passport(standalone_qa):
    app = standalone_qa
    ask(app, 'Какой лимит запросов на сброс?', 1)
    a = last(app)
    assert a['status'] == 'st-answered' and a['sources'] == ['Документ «Пример — ТЗ восстановление пароля.md»']
    p = help_prompts(app)[0]
    assert '[D1] Документ «Пример — ТЗ восстановление пароля.md»' in p and 'Знания о продукте' not in p


def test_standalone_history_survives_reload(standalone_qa):
    app = standalone_qa
    ask(app, 'Какой лимит запросов на сброс?', 1)
    app.reload()
    app.page.click('[data-act=help-view][data-v=qa]')
    assert app.count('#help-list .hq') == 1


def test_help_fits_a_phone_screen(make_app):
    app = make_app(viewport=(390, 860))
    model_kb.install(app.model)
    app.mode('help')
    app.page.click('[data-act=help-view][data-v=qa]')
    ask(app, Q_ROLES, 1)
    assert app.state('document.documentElement.scrollWidth <= window.innerWidth')
