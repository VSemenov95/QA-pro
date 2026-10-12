"""Текст кейса без HTML и без буквальных «\\n»: модель или выгрузка из ТМС иногда присылают разметку, а на экране и в ТМС нужен чистый текст."""
import pytest

from tests.support import model_draft as md

TC = {
    'title': 'Вход',
    'preconditions': ['<p>Пользователь user@example.ru зарегистрирован</p>', '<p>Открыта страница /login\\nПользователь не авторизован</p>', 'Тестовый пользователь\\r\\nактивен'],
    'postconditions': '<p>Сессия создана</p>\\n<p>Лог записан</p>',
    'steps': [{'n': 1, 'action': '<p>Ввести логин</p>', 'expected': '&lt;p&gt;Поле видно&lt;/p&gt;', 'data': ''}],
    'description': 'Проверка <b>входа</b>',
}   # \\n и \\r\\n — это два знака (обратная косая черта и n), как их иногда пишет модель


@pytest.fixture
def clean(app):
    return lambda tc: app.call('a.cleanCase(arg)', tc)


@pytest.fixture
def tms(app):
    return lambda tc: app.call("(() => { const t = a.tmsCase({ uid: 'x', type: 'api', testCase: arg, suites: [], requirementIds: [] }); return { pre: t.pre, post: t.post, steps: t.steps, description: t.description, title: t.title }; })()", tc)


# ---------- текст ----------
@pytest.mark.parametrize('src,expected', [
    ('<p>Текст</p>', 'Текст'),
    ('Первая<br>Вторая', 'Первая\nВторая'),
    ('<div>1</div><div>2</div>', '1\n2'),
    ('<ul><li>один</li><li>два</li></ul>', '- один\n- два'),
    ('Проверка <b>входа</b> и <i>выхода</i>', 'Проверка входа и выхода'),
    ('a &amp; b &lt;c&gt; &quot;d&quot;&nbsp;e', 'a & b <c> "d" e'),
    ('&lt;p&gt;Поле видно&lt;/p&gt;', 'Поле видно'),
    ('Цена 5 &lt; 10', 'Цена 5 < 10'),
    ('Обычный текст без разметки', 'Обычный текст без разметки'),
    ('x < 5 и y > 3', 'x < 5 и y > 3'),
    ('ввести <email> в поле', 'ввести <email> в поле'),
], ids=['абзац', 'br', 'div', 'список', 'жирный', 'сущности', 'экранированные-теги', 'меньше', 'без-разметки', 'сравнение', 'не-тег'])
def test_text_is_cleaned(app, src, expected):
    assert app.call('a.deHtml(arg)', src) == expected


def test_code_block_is_not_touched(app):
    src = 'Тело:\n```json\n{"a": "<b>x</b>"}\n```\nконец'
    assert '```json\n{"a": "<b>x</b>"}\n```' in app.call('a.deHtml(arg)', src)


def test_pre_from_tms_becomes_code_block(app):
    out = app.call('a.deHtml(arg)', '<p>Тело</p><pre>{"a": 1}</pre>')
    assert out == 'Тело\n\n```\n{"a": 1}\n```'


def test_cleaning_twice_changes_nothing(clean):
    once = clean(TC)
    assert clean(once) == once


# ---------- поля кейса ----------
def test_preconditions_become_one_item_per_line(clean):
    assert clean(TC)['preconditions'] == ['Пользователь user@example.ru зарегистрирован', 'Открыта страница /login', 'Пользователь не авторизован', 'Тестовый пользователь', 'активен']


def test_postconditions_string_keeps_lines(clean):
    assert clean(TC)['postconditions'] == 'Сессия создана\nЛог записан'


def test_postconditions_list_is_split_too(clean):
    assert clean({'postconditions': ['<p>a</p>', 'b\\r\\nc']})['postconditions'] == ['a', 'b', 'c']


def test_precondition_string_with_escaped_newline(clean):
    assert clean({'preconditions': 'Один\\nДва'})['preconditions'] == 'Один\nДва'


def test_code_block_in_precondition_stays_with_its_item(clean):
    pre = ['Запрос:\n```json\n{"a": 1}\n```', 'Второе']
    assert clean({'preconditions': pre})['preconditions'] == pre


def test_steps_are_cleaned(clean):
    assert clean(TC)['steps'] == [{'n': 1, 'action': 'Ввести логин', 'expected': 'Поле видно', 'data': ''}]


def test_numbers_and_flags_are_kept(clean):
    assert clean({'n': 5, 'ok': True, 'none': None}) == {'n': 5, 'ok': True, 'none': None}


def test_description_is_cleaned(clean):
    assert clean(TC)['description'] == 'Проверка входа'


# ---------- загрузка в ТМС ----------
def test_tms_preconditions_are_a_list_of_lines(tms):
    assert tms(TC)['pre'] == ['Пользователь user@example.ru зарегистрирован', 'Открыта страница /login', 'Пользователь не авторизован', 'Тестовый пользователь', 'активен']


def test_tms_postconditions_are_a_list_of_lines(tms):
    assert tms(TC)['post'] == ['Сессия создана', 'Лог записан']


def test_tms_steps_are_plain_text(tms):
    assert tms(TC)['steps'] == [{'action': 'Ввести логин', 'expected': 'Поле видно', 'data': ''}]


def test_tms_description_is_plain_text(tms):
    assert tms(TC)['description'] == 'Проверка входа'


# ---------- на экране ----------
def test_case_on_screen_has_no_markup(app):
    """Модель прислала разметку в предусловиях — в карточке кейса её нет."""
    def generate(call):
        out = md.generate_by_template(call)
        for c in out['cases']:
            c['testCase']['preconditions'] = ['<p>Пользователь <b>user</b> зарегистрирован</p>', 'Открыта страница /login\\nПользователь не авторизован']
        return out
    app.model.on('promptGenerate', generate)
    app.generate()
    app.tab('cases')
    app.page.click('#case-list .case-h >> nth=0')
    text = app.text('.case-b')
    assert 'Пользователь user зарегистрирован' in text and 'Пользователь не авторизован' in text
    assert '<p>' not in text and '<b>' not in text and '\\n' not in text
