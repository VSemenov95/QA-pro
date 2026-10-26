"""Вопрос агенту по кейсу: почему кейс составлен так. Ответ сохраняется вместе с кейсом."""
from tests.test_reduce_regen import draft  # noqa: F401  (фикстура черновика)


def test_question_about_a_case_is_answered_and_kept(draft):
    draft.model.on('promptAskCase', {'answer': 'Два запроса: требование описывает повторную отправку.'})
    draft.tab('cases')
    uid = draft.state('S.run.cases[0].uid')
    draft.page.click(f'#case-{uid} .case-h')
    draft.page.click(f'#case-{uid} [data-act=ask-case]')
    draft.page.fill(f'#ask-{uid}', 'Почему два запроса?')
    draft.page.dispatch_event(f'#ask-{uid}', 'change')
    draft.page.click(f'#case-{uid} [data-act=do-ask]')
    draft.wait_idle()
    assert 'Почему два запроса?' in draft.text(f'#case-{uid} .ask-log')
    assert 'повторную отправку' in draft.text(f'#case-{uid} .ask-log')
    assert draft.state(f"S.run.cases.find((c) => c.uid === '{uid}').askLog.length") == 1


def test_empty_question_is_not_sent(draft):
    draft.tab('cases')
    uid = draft.state('S.run.cases[0].uid')
    draft.page.click(f'#case-{uid} .case-h')
    draft.page.click(f'#case-{uid} [data-act=ask-case]')
    draft.page.click(f'#case-{uid} [data-act=do-ask]')
    assert draft.model.calls_of('promptAskCase') == []
