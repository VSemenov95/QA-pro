"""Список разделов базы знаний — по страницам: на экране не больше 25 строк, остальные — кнопками пагинации."""
import pytest

from tests.test_kb_limits import SEED, kb  # noqa: F401 — фикстура базы знаний

ROWS = "[...document.querySelectorAll('#kb-rows .kb-row-t')].map((e) => e.textContent)"


@pytest.fixture
def sixty(kb):  # noqa: F811
    kb.state('S.settings.kbAuto = false')
    kb.call(SEED, 60)
    kb.page.click('[data-act=help-view][data-v=blocks]')
    kb.page.wait_for_selector('#kb-rows')
    return kb


def info(app):
    return app.text('#kb-body .pg-info')


def test_first_page_shows_25_of_all(sixty):
    rows = sixty.state(ROWS)
    assert len(rows) == 25 and info(sixty) == '1–25 из 60'
    assert sixty.text('#kb-body .kb-list-h .cnt') == '60'
    assert sixty.page.is_disabled('#kb-body .pg-btn[aria-label="Предыдущая страница"]')
    assert sixty.page.get_attribute('#kb-body .pg-btn.on', 'aria-current') == 'page'


def test_pages_cover_every_section_once(sixty):
    seen = []
    for p in (1, 2, 3):
        sixty.page.click(f'#kb-body .pg-btn[aria-label="Страница {p}"]')
        seen += sixty.state(ROWS)
    assert len(seen) == 60 and len(set(seen)) == 60
    assert info(sixty) == '51–60 из 60' and sixty.page.is_disabled('#kb-body .pg-btn[aria-label="Следующая страница"]')


def test_next_and_previous(sixty):
    first = sixty.state(ROWS)
    sixty.page.click('#kb-body .pg-btn[aria-label="Следующая страница"]')
    assert info(sixty) == '26–50 из 60' and sixty.state(ROWS)[0] != first[0]
    sixty.page.click('#kb-body .pg-btn[aria-label="Предыдущая страница"]')
    assert sixty.state(ROWS) == first


def test_search_starts_from_the_first_page(sixty):
    sixty.page.click('#kb-body .pg-btn[aria-label="Страница 3"]')
    sixty.page.fill('#kb-q', 'Платежи')
    rows = sixty.state(ROWS)
    assert len(rows) == 12 and all('Платежи' in r for r in rows)
    assert sixty.count('#kb-body .pager') == 0   # всё уместилось на одной странице


def test_page_is_kept_after_opening_a_section(sixty):
    sixty.page.click('#kb-body .pg-btn[aria-label="Страница 2"]')
    title = sixty.state(ROWS)[0]
    sixty.page.click('#kb-rows .kb-row >> nth=0')
    sixty.page.wait_for_timeout(300)
    assert sixty.state('S.kb.open')
    sixty.state('(S.kb.open = null, window.__qa.renderAll(), true)')
    sixty.page.wait_for_selector('#kb-rows')
    assert info(sixty) == '26–50 из 60' and sixty.state(ROWS)[0] == title


def test_short_list_has_no_pager(kb):  # noqa: F811
    kb.state('S.settings.kbAuto = false')
    kb.call(SEED, 10)
    kb.page.click('[data-act=help-view][data-v=blocks]')
    kb.page.wait_for_selector('#kb-rows')
    assert len(kb.state(ROWS)) == 10 and kb.count('#kb-body .pager') == 0


@pytest.mark.parametrize('page,pages,expected', [
    (1, 1, [1]), (1, 3, [1, 2, 3]), (1, 10, [1, 2, 0, 10]), (5, 10, [1, 0, 4, 5, 6, 0, 10]),
    (10, 10, [1, 0, 9, 10]), (3, 10, [1, 2, 3, 4, 0, 10]), (4, 10, [1, 2, 3, 4, 5, 0, 10])])
def test_page_numbers_with_gaps(app, page, pages, expected):
    assert app.call('a.pageNums(arg[0], arg[1])', [page, pages]) == expected
