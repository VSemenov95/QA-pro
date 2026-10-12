"""Как кейс QA pro превращается в запрос Сферы ФТ (функции фоновой части расширения, вызываются напрямую)."""
import pytest

META = {'sectionId': '124', 'projectCode': 'PPAN'}


@pytest.fixture(scope='module')
def sfera_item(new_env):
    ext = new_env(sfera_tab=False).ext

    def run(tc, meta=META):
        return ext.sw_eval('(a) => toSferaItem(a.tc, a.meta)', {'tc': tc, 'meta': meta})
    return run


@pytest.mark.parametrize('suites,labels,regress', [
    (['smoke'], ['SMOKE'], False),
    (['regression'], [], True),
    (['smoke', 'regression'], ['SMOKE'], True),
    (['Смоук', 'Регресс'], ['SMOKE'], True),
    (['Smoke-test'], ['SMOKE'], False),
    ([], [], False),
])
def test_suites_become_label_and_regression_field(sfera_item, suites, labels, regress):
    """Смоук → метка SMOKE, регресс → поле «Регрессионный» (ti_regressive)."""
    it = sfera_item({'name': 'Кейс', 'suites': suites})
    assert it['labels'] == labels and it['ti_regressive'] is regress


def test_regressive_flag_of_the_case_is_kept(sfera_item):
    assert sfera_item({'name': 'Кейс', 'ti_regressive': True})['ti_regressive'] is True


def test_ai_gen_label_is_dropped_and_others_are_kept(sfera_item):
    assert sfera_item({'name': 'Кейс', 'labels': ['API', 'AI_gen'], 'suites': ['smoke']})['labels'] == ['API', 'SMOKE']


def test_labels_do_not_repeat(sfera_item):
    assert sfera_item({'name': 'Кейс', 'labels': ['SMOKE'], 'suites': ['smoke']})['labels'] == ['SMOKE']


@pytest.mark.parametrize('prio,expected', [('P4_CRITICAL', 'P4_CRITICAL'), ('P1_LOW', 'P1_LOW'), ('high', 'P3_HIGH'), ('High', 'P3_HIGH'), ('Высокий', 'P3_HIGH'),
                                           ('низкий', 'P1_LOW'), ('critical', 'P4_CRITICAL'), ('средний', 'P2_MEDIUM'), ('', 'P2_MEDIUM'), ('срочно!', 'P2_MEDIUM')])
def test_priority(sfera_item, prio, expected):
    assert sfera_item({'name': 'Кейс', 'priority': prio})['priority'] == expected


def test_name_is_cut_to_256_characters(sfera_item):
    assert len(sfera_item({'name': 'я' * 300})['name']) == 256


def test_target_section_and_type(sfera_item):
    it = sfera_item({'name': 'Кейс'})
    assert it['sectionId'] == 124 and it['projectCode'] == 'PPAN' and it['type'] == 'T1_TEST_CASE'


def test_steps_keep_action_and_expected_result(sfera_item):
    it = sfera_item({'name': 'Кейс', 'steps': [{'action': '<p>a</p>', 'expectedResult': '<p>b</p>'}, {'action': '<p>только действие</p>'}, 'мусор', None],
                     'preConditions': [{'action': '<p>пред</p>', 'expectedResult': '<p></p>'}], 'postConditions': [{'action': '<p>пост</p>'}]})
    assert it['steps'] == [{'action': '<p>a</p>', 'expectedResult': '<p>b</p>'}, {'action': '<p>только действие</p>', 'expectedResult': ''}]
    assert it['preConditions'] == [{'action': '<p>пред</p>', 'expectedResult': '<p></p>'}] and it['postConditions'] == [{'action': '<p>пост</p>', 'expectedResult': ''}]


def test_missing_fields_are_empty_not_undefined(sfera_item):
    it = sfera_item({'name': 'Кейс'})
    assert it['description'] == '' and it['steps'] == [] and it['preConditions'] == [] and it['postConditions'] == []
