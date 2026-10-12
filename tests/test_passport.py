"""Знания о продукте («паспорт»): изучение документов, правки вместо полной перезаписи, ручное редактирование, предыдущая версия, паспорт в запросах."""
import re

import pytest

from tests.support import files, model_kb
from tests.support.model import ModelError

PASSPORT = """## Назначение и границы
- Восстановление пароля в личном кабинете (ТЗ v1.3)
## Бизнес-правила и ограничения
- Не более 3 запросов на сброс за 15 минут
## Открытые вопросы
- Что происходит при 4-м запросе через UI?"""


def passport(app):
    return app.state("S.products.find((p) => p.id === S.productId).passport?.text || ''")


def save(app, text):
    app.call('a.savePassport(S.productId, arg, null)', text)
    app.page.wait_for_function('(t) => (window.__qa.S.products.find((p) => p.id === window.__qa.S.productId).passport?.text || "") === t', arg=text)


def learn(app):
    app.page.click('[data-act=know-learn]')
    app.page.wait_for_function('() => !window.__qa.S.know.busy && window.__qa.S.know.log.length > 0 || window.__qa.S.know.error')
    app.wait_idle()


def log(app):
    return app.state('S.know.log.map((l) => l.text)')


def acts(app):
    """Кнопки карточки «Что агент знает о продукте»."""
    return app.page.evaluate("() => { const c = [...document.querySelectorAll('#prod-info .pp-card')].find((x) => /Что агент знает/.test(x.textContent)); return [...c.querySelectorAll('.pp-acts button')].map((e) => e.textContent.replace(/\\s+/g, ' ').trim()); }")


@pytest.fixture
def pa(app):
    model_kb.install(app.model)
    return app


# ---------- пустой паспорт ----------
def test_empty_passport_offers_learning_and_manual_entry(pa):
    assert 'Пока пусто' in pa.text('#prod-info .pp-empty') and pa.count('[data-act=pass-new]') == 1
    assert acts(pa) == ['Изучить документы']
    assert pa.text('#prod-info .pp-stats .stat:last-child').split('\n')[0].upper() == 'ЗНАНИЯ' and '—' in pa.text('#prod-info .pp-stats .stat:last-child')


def test_learning_writes_the_first_passport_with_a_full_request(pa):
    learn(pa)
    assert len(pa.model.calls_of('promptPassportFull')) == 1 and pa.model.calls_of('promptPassportDelta') == []
    p = pa.model.prompts_of('promptPassportFull')[0]
    assert 'Пока пуст — составь первую версию.' in p and '<document name="Пример — ТЗ восстановление пароля.md" part="1/1">' in p
    assert 'Версия знаний 1' in passport(pa) and len(log(pa)) == 1 and log(pa)[0].startswith('Документы: паспорт ')


def test_learning_is_done_by_the_service_model_tier(pa):
    learn(pa)
    assert pa.model.calls_of('promptPassportFull')[0].info['modelTier'] == 'default'


def test_learning_in_economy_mode_uses_the_fast_model(pa):
    pa.state('S.settings.economy = true')
    learn(pa)
    assert pa.model.calls_of('promptPassportFull')[0].info['modelTier'] == 'quick'


def test_prompt_carries_product_name_and_description(pa):
    pa.page.click('[data-act=prod-edit]')
    pa.page.fill('#prod-desc', 'Веб-кабинет клиента')
    pa.page.click('[data-pact=save]')
    pa.page.wait_for_function("() => window.__qa.S.products[0].description === 'Веб-кабинет клиента'")
    learn(pa)
    p = pa.model.prompts_of('promptPassportFull')[0]
    assert 'паспорт продукта «Мой продукт»' in p and 'Описание продукта от команды: Веб-кабинет клиента' in p


def test_learned_documents_are_remembered(pa):
    learn(pa)
    pid = pa.state('S.productId')
    assert len(pa.db.get(f'products/{pid}/meta/known')['docs']) == 1
    assert acts(pa)[0] == 'Изучить заново' and 'Изучить документы' not in acts(pa)


def test_relearning_asks_for_confirmation_and_reads_everything_again(pa):
    learn(pa)
    pa.page.click('[data-act=know-relearn]')
    assert pa.model.calls_of('promptPassportDelta') == []   # первое нажатие только просит подтверждения
    pa.page.click('[data-act=know-relearn]')
    pa.page.wait_for_function('() => window.__qa.S.know.log.some((l) => /правк|новых фактов нет/.test(l.text))')
    pa.wait_idle()
    assert len(pa.model.calls_of('promptPassportDelta')) == 1


def test_new_document_is_counted_separately(pa, tmp_path):
    learn(pa)
    pa.state('S.settings.kbAuto = false')
    pa.mode('help')
    pa.upload(files.write(tmp_path / 'правила.md', '# Правила\n- Роль: Оператор\n'))
    assert acts(pa) == ['Изучить документы · новых 1', 'Править']


# ---------- правки вместо перезаписи ----------
def test_existing_passport_is_updated_by_changes_only(pa):
    save(pa, PASSPORT)
    learn(pa)
    assert pa.model.calls_of('promptPassportFull') == [] and len(pa.model.calls_of('promptPassportDelta')) == 1
    p = pa.model.prompts_of('promptPassportDelta')[0]
    assert 'Верни только изменения паспорта' in p and '- Не более 3 запросов на сброс за 15 минут' in p   # текущий паспорт передан целиком


def test_changes_are_applied_to_the_passport(pa):
    save(pa, PASSPORT)
    learn(pa)
    text = passport(pa)
    assert '- Не более 3 запросов на сброс за 15 минут (дельта 1)' in text    # новый пункт в нужный раздел
    assert '- Токен сброса — одноразовая ссылка на 30 минут' in text and '## Термины' in text   # новый раздел создан
    assert 'Что происходит при 4-м запросе через UI?' not in text and '## Открытые вопросы' not in text   # вопрос снят, пустой раздел убран
    assert '- Восстановление пароля в личном кабинете (ТЗ v1.3)' in text   # остальное на месте
    assert re.search(r'Документы: \d+ правк', log(pa)[0])


def test_new_section_goes_to_its_place_in_the_standard_order(pa):
    save(pa, PASSPORT)
    learn(pa)
    heads = re.findall(r'(?m)^## (.+)$', passport(pa))
    assert heads == ['Назначение и границы', 'Бизнес-правила и ограничения', 'Термины']


def test_previous_version_is_kept_after_an_update(pa):
    save(pa, PASSPORT)
    learn(pa)
    pid = pa.state('S.productId')
    rec = pa.db.get(f'products/{pid}/meta/passport')
    assert rec['prev']['text'] == PASSPORT and 'Предыдущая версия' in acts(pa)


@pytest.mark.parametrize('ops,expect_in,expect_not_in', [
    ([{'op': 'add', 'section': 'Бизнес-правила и ограничения', 'text': '- Ссылка действует 30 минут'}], ['- Не более 3 запросов на сброс за 15 минут\n- Ссылка действует 30 минут'], []),
    ([{'op': 'add', 'section': 'Роли и пользователи', 'text': 'Оператор видит заявки смены'}], ['## Роли и пользователи\n- Оператор видит заявки смены'], []),   # текст без маркера получает «- »
    ([{'op': 'add', 'section': 'Бизнес-правила и ограничения', 'text': '- не более 3 запросов на сброс за 15 минут'}], [], ['запросов на сброс за 15 минут\n- не более']),   # повтор не добавляется
    ([{'op': 'replace', 'old': '- Не более 3 запросов на сброс за 15 минут', 'text': '- Не более 5 запросов на сброс за 15 минут (уточнено: созвон)'}], ['- Не более 5 запросов на сброс за 15 минут (уточнено: созвон)'], ['Не более 3 запросов']),
    ([{'op': 'replace', 'old': 'Восстановление пароля в личном кабинете', 'text': '- Восстановление пароля в личном кабинете и приложении'}], ['- Восстановление пароля в личном кабинете и приложении'], ['(ТЗ v1.3)']),   # строка найдена по части текста
    ([{'op': 'replace', 'old': 'Такой строки нет совсем нигде', 'section': 'Термины', 'text': '- Токен — ссылка'}], ['## Термины\n- Токен — ссылка'], []),   # не нашли, что заменять — добавляем
    ([{'op': 'remove', 'old': 'Что происходит при 4-м запросе через UI?'}], ['## Бизнес-правила и ограничения'], ['Что происходит при 4-м', '## Открытые вопросы']),
    ([{'op': 'remove', 'old': 'Такой строки нет совсем нигде'}], ['- Что происходит при 4-м запросе через UI?'], []),
    ([{'op': 'delete', 'old': 'Не более 3 запросов на сброс за 15 минут'}], ['## Открытые вопросы'], ['Не более 3 запросов']),   # delete — то же, что remove
    ([{'op': 'unknown', 'text': 'мусор'}, {'op': 'add', 'section': 'Термины'}, None], [], ['мусор']),
])
def test_change_kinds(pa, ops, expect_in, expect_not_in):
    save(pa, PASSPORT)
    pa.model.on('promptPassportDelta', {'ops': ops})
    learn(pa)
    text = passport(pa)
    for x in expect_in:
        assert x in text, text
    for x in expect_not_in:
        assert x not in text, text


def test_no_new_facts_leave_the_passport_untouched(pa):
    save(pa, PASSPORT)
    pid = pa.state('S.productId')
    before = pa.db.get(f'products/{pid}/meta/passport')
    pa.model.on('promptPassportDelta', {'ops': []})
    learn(pa)
    assert log(pa) == ['Документы: новых фактов нет'] and pa.db.get(f'products/{pid}/meta/passport') == before


def test_model_may_return_the_whole_passport_instead_of_changes(pa):
    save(pa, PASSPORT)
    pa.model.on('promptPassportDelta', {'passport': '## Термины\n- Токен — ссылка'})
    learn(pa)
    assert passport(pa) == '## Термины\n- Токен — ссылка' and log(pa) == ['Документы: паспорт переписан']


def test_nearly_full_passport_asks_to_shorten(pa):
    save(pa, '## Правила\n' + '\n'.join(f'- Правило {i}: лимит {i} операций за {i} минут, экран «Платёж {i}»' for i in range(560))[:38000])
    learn(pa)
    assert 'Паспорт почти заполнен' in pa.model.prompts_of('promptPassportDelta')[0] and 'стал короче хотя бы на 3000 знаков' in pa.model.prompts_of('promptPassportDelta')[0]


def test_passport_not_nearly_full_does_not_ask_to_shorten(pa):
    save(pa, PASSPORT)
    learn(pa)
    assert 'Паспорт почти заполнен' not in pa.model.prompts_of('promptPassportDelta')[0]


# ---------- сбои ----------
def test_model_error_is_shown_and_passport_stays(pa):
    save(pa, PASSPORT)
    pa.model.on('promptPassportDelta', ModelError('rate_limited'))
    learn(pa)
    assert 'исчерпан лимит использования' in pa.text('#prod-info .case-note.err') and passport(pa) == PASSPORT
    assert acts(pa)[0] == 'Изучить документы'   # можно повторить


def test_empty_first_passport_is_an_error(pa):
    pa.model.on('promptPassportFull', {'passport': ''})
    learn(pa)
    assert 'Модель не вернула паспорт продукта.' in pa.text('#prod-info .case-note.err') and passport(pa) == ''


def test_learning_without_documents_says_so(app):
    btn = '#doc-list [data-doc-act=remove]'
    app.mode('help')
    app.page.click(btn)
    app.page.click(btn)
    app.page.wait_for_function('() => window.__qa.S.docs.length === 0')
    assert app.count('[data-act=know-learn]') == 0 and app.count('[data-act=know-relearn]') == 0


def test_big_documents_are_learned_in_parts(pa, tmp_path):
    """Пример ТЗ и большой документ (33 тыс. знаков) — три запроса: первый строит паспорт целиком, остальные дополняют его правками."""
    pa.state('S.settings.kbAuto = false')
    para = '\n\n'.join(f'{i}. Поле «Поле {i}» на экране «Профиль» принимает до {i} символов и сохраняется кнопкой «Сохранить».' for i in range(1, 330))
    pa.mode('help')
    pa.upload(files.write(tmp_path / 'большой.md', para))
    learn(pa)
    assert len(pa.model.calls_of('promptPassportFull')) == 1 and len(pa.model.calls_of('promptPassportDelta')) == 2
    assert [l.split(':')[0] for l in log(pa)] == ['Часть 1/3', 'Часть 2/3', 'Часть 3/3']
    pid = pa.state('S.productId')
    assert len(pa.db.get(f'products/{pid}/meta/known')['docs']) == 2


# ---------- ручная правка ----------
def test_edit_opens_current_text(pa):
    save(pa, PASSPORT)
    pa.page.click('[data-act=pass-edit]')
    assert pa.page.input_value('#pass-text') == PASSPORT and 'До 40' in pa.text('#prod-info .case-edit .hint')


def test_manual_edit_is_saved_for_the_team_and_keeps_the_previous_version(pa):
    save(pa, PASSPORT)
    pa.page.click('[data-act=pass-edit]')
    pa.page.fill('#pass-text', '## Термины\n- Счёт — документ на оплату')
    pa.page.click('[data-act=pass-save]')
    pa.page.wait_for_function("() => !window.__qa.S.passEdit")
    pid = pa.state('S.productId')
    rec = pa.db.get(f'products/{pid}/meta/passport')
    assert rec['text'] == '## Термины\n- Счёт — документ на оплату' and rec['prev']['text'] == PASSPORT
    assert 'Счёт — документ на оплату' in pa.text('#prod-info .pp-md') and 'после генерации' not in pa.text('#prod-info .pp-card-h')


def test_edit_can_be_cancelled(pa):
    save(pa, PASSPORT)
    pa.page.click('[data-act=pass-edit]')
    pa.page.fill('#pass-text', 'другое')
    pa.page.click('[data-act=pass-cancel]')
    assert passport(pa) == PASSPORT and pa.count('#pass-text') == 0


def test_edit_is_not_overwritten_by_background_refresh(pa):
    save(pa, PASSPORT)
    pa.page.click('[data-act=pass-edit]')
    pa.page.fill('#pass-text', 'правка в процессе')
    pa.page.wait_for_timeout(700)   # подписка на продукты обновляет панель
    assert pa.page.input_value('#pass-text') == 'правка в процессе'


def test_write_manually_starts_from_a_template(pa):
    pa.page.click('[data-act=pass-new]')
    text = pa.page.input_value('#pass-text')
    assert text.startswith('## Назначение и границы\n- ') and text.count('## ') == 4


def test_previous_version_is_restored_with_confirmation(pa):
    save(pa, PASSPORT)
    save(pa, '## Термины\n- Счёт — документ на оплату')
    pa.page.click('[data-act=pass-prev]')
    assert passport(pa).startswith('## Термины')   # первое нажатие только просит подтверждения
    pa.page.click('[data-act=pass-prev]')
    pa.page.wait_for_function('(t) => (window.__qa.S.products.find((p) => p.id === window.__qa.S.productId).passport?.text || "") === t', arg=PASSPORT)
    assert pa.count('[data-act=pass-prev]') == 1   # теперь «предыдущая» — только что заменённая версия


# ---------- после генерации ----------
def test_first_generation_writes_the_passport(pa):
    pa.generate()
    assert len(pa.model.calls_of('promptPassportFull')) == 1 and 'Версия знаний 1' in passport(pa)
    assert 'после генерации' in pa.text('#prod-info .pp-card-h')
    assert pa.state('S.run.steps.knowledge.log.map((l) => l.text)')[-1].startswith('Знания о продукте обновлены: паспорт')


def test_requirements_are_sent_to_the_passport_only_once(pa):
    pa.generate()
    pid = pa.state('S.productId')
    assert len(pa.db.get(f'products/{pid}/meta/known')['reqs']) == 4
    pa.page.click('#btn-newses')
    pa.page.wait_for_function('() => !window.__qa.S.run')
    pa.js("() => { const S = window.__qa.S; for (const d of S.docs) S.runDocs.add(d.id); window.__qa.renderAll(); }")
    pa.model.reset()
    pa.generate()
    assert pa.model.calls_of('promptPassportFull', 'promptPassportDelta') == []
    assert 'Новых сведений нет' in ' '.join(pa.state('S.run.steps.knowledge.log.map((l) => l.text)'))


def test_generation_after_manual_edit_sends_only_changes(pa):
    save(pa, PASSPORT)
    pa.generate()
    assert pa.model.calls_of('promptPassportFull') == [] and len(pa.model.calls_of('promptPassportDelta')) == 1
    p = pa.model.prompts_of('promptPassportDelta')[0]
    assert '### Требования, которых ещё нет в паспорте' in p and 'Вопросы без ответа' in p and '- Что происходит при 4-м запросе через UI?' in p.split('### Вопросы без ответа')[1]


# ---------- паспорт в запросах ----------
@pytest.mark.parametrize('kind', ['promptAnalyze', 'promptChecklist', 'promptPlan', 'promptGenerate'])
def test_passport_goes_into_generation_requests(pa, kind):
    save(pa, PASSPORT)
    pa.generate()
    ps = pa.model.prompts_of(kind)
    assert ps and all('## Знания о продукте «Мой продукт»' in p and '- Не более 3 запросов на сброс за 15 минут' in p for p in ps)


def test_documents_win_over_the_passport_in_generation(pa):
    save(pa, PASSPORT)
    pa.generate()
    assert 'Если текущие документы противоречат знаниям — приоритет у документов.' in pa.model.prompts_of('promptGenerate')[0]
    assert 'требования выделяй только из документов этого фрагмента' in pa.model.prompts_of('promptAnalyze')[0]


def test_review_gets_the_passport_with_its_own_instruction(pa):
    save(pa, PASSPORT)
    pa.generate()
    pa.tab('review')
    pa.page.click('[data-act=start-review]')
    pa.wait_idle()
    p = pa.model.prompts_of('promptReviewCases')[0]
    assert '## Знания о продукте «Мой продукт»' in p and 'Если кейс противоречит этим знаниям и документам — это замечание' in p


def test_only_lines_on_the_topic_go_into_the_request_when_the_passport_is_long(pa):
    pa.call('a.savePassport(S.productId, arg, null)', '## Правила\n' + '\n'.join(f'- Правило {i}: лимит {i} операций, экран «Платёж {i}»' for i in range(400)))
    pa.page.wait_for_function('() => window.__qa.S.products[0].passport.text.length > 15000')
    block = pa.call("a.productBlock(null, 'analyze', 'Платёж 123 лимит 123')")
    assert 'пункты по теме запроса' in block and 'Правило 123' in block and len(block) < 3000 + 400


def test_economy_mode_cuts_the_passport_in_requests(pa):
    pa.call('a.savePassport(S.productId, arg, null)', '## Правила\n' + '\n'.join(f'- Правило {i}: лимит операций, экран «Платёж»' for i in range(400)))
    pa.page.wait_for_function('() => window.__qa.S.products[0].passport.text.length > 15000')
    normal = len(pa.call("a.productBlock(null, 'single', 'лимит операций экран Платёж')"))
    pa.state('S.settings.economy = true')
    assert len(pa.call("a.productBlock(null, 'single', 'лимит операций экран Платёж')")) < normal * 0.7


def test_passport_is_not_sent_when_empty(pa):
    pa.generate()
    assert all('## Знания о продукте' not in p for k in ('promptAnalyze', 'promptChecklist', 'promptPlan', 'promptGenerate') for p in pa.model.prompts_of(k))
