"""Тема оформления (светлая, тёмная, как в системе) и нумерация шагов в левой колонке."""
import pytest

BG = "getComputedStyle(document.body).backgroundColor"
LIGHT, DARK = 'rgb(244, 245, 247)', 'rgb(13, 15, 19)'
THEME = "document.documentElement.dataset.theme || 'system'"


def label(app):
    return app.page.get_attribute('#btn-theme', 'aria-label')


def system(app, scheme):
    """Тема операционной системы меняется; страница должна заметить это сама."""
    app.page.emulate_media(color_scheme=scheme)
    app.page.wait_for_function('(l) => document.querySelector("#btn-theme").getAttribute("aria-label") === l', arg='Светлая тема' if scheme == 'dark' else 'Тёмная тема')


def lum(rgb):
    r, g, b = (int(x) / 255 for x in rgb[rgb.index('(') + 1:rgb.index(')')].split(',')[:3])
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4   # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


@pytest.fixture
def light_app(app):
    app.page.emulate_media(color_scheme='light')
    return app


# ---------- по умолчанию — как в системе ----------
def test_default_follows_light_system(light_app):
    assert light_app.js(THEME) == 'system' and light_app.js(BG) == LIGHT and label(light_app) == 'Тёмная тема'


def test_default_follows_dark_system(light_app):
    system(light_app, 'dark')
    assert light_app.js(THEME) == 'system' and light_app.js(BG) == DARK


def test_system_change_is_noticed_both_ways(light_app):
    system(light_app, 'dark')
    system(light_app, 'light')
    assert light_app.js(BG) == LIGHT


def test_button_title_matches_label(light_app):
    assert light_app.page.get_attribute('#btn-theme', 'title') == label(light_app)


# ---------- переключение ----------
def test_click_makes_it_dark(light_app):
    light_app.page.click('#btn-theme')
    assert light_app.js(THEME) == 'dark' and light_app.js(BG) == DARK and label(light_app) == 'Светлая тема'


def test_second_click_makes_it_light_again(light_app):
    light_app.page.click('#btn-theme')
    light_app.page.click('#btn-theme')
    assert light_app.js(THEME) == 'light' and light_app.js(BG) == LIGHT and label(light_app) == 'Тёмная тема'


def test_click_under_dark_system_makes_it_light(light_app):
    system(light_app, 'dark')
    light_app.page.click('#btn-theme')
    assert light_app.js(THEME) == 'light' and light_app.js(BG) == LIGHT


def test_icon_changes_with_theme(light_app):
    before = light_app.page.inner_html('#btn-theme')
    light_app.page.click('#btn-theme')
    assert light_app.page.inner_html('#btn-theme') != before


# ---------- запоминание ----------
def test_choice_is_stored_in_browser(light_app):
    light_app.page.click('#btn-theme')
    assert light_app.call("localStorage.getItem('qapro.theme')") == '"dark"'


def test_choice_survives_reload(light_app):
    light_app.page.click('#btn-theme')
    light_app.reload()
    assert light_app.js(THEME) == 'dark' and light_app.js(BG) == DARK and label(light_app) == 'Светлая тема'


def test_explicit_choice_beats_system(light_app):
    light_app.page.click('#btn-theme')   # тёмная при светлой системе
    light_app.page.emulate_media(color_scheme='dark')
    light_app.page.emulate_media(color_scheme='light')
    assert light_app.js(BG) == DARK


def test_light_choice_stays_under_dark_system(light_app):
    system(light_app, 'dark')
    light_app.page.click('#btn-theme')
    light_app.reload()
    assert light_app.js(THEME) == 'light' and light_app.js(BG) == LIGHT


@pytest.mark.parametrize('mode', ['update', 'help', 'generate'])
def test_theme_stays_when_mode_changes(light_app, mode):
    light_app.page.click('#btn-theme')
    light_app.mode(mode)
    assert light_app.js(THEME) == 'dark' and light_app.js(BG) == DARK


@pytest.mark.parametrize('dark', [False, True])
def test_page_text_is_readable(light_app, dark):
    if dark:
        light_app.page.click('#btn-theme')
    bg, fg = light_app.js(BG), light_app.js('getComputedStyle(document.body).color')
    hi, lo = sorted([lum(bg), lum(fg)], reverse=True)
    assert (hi + 0.05) / (lo + 0.05) >= 4.5


# ---------- нумерация шагов слева ----------
STEPS = "[...document.querySelectorAll('.rail .step-n')].filter((e) => e.offsetParent).map((e) => e.textContent)"


@pytest.mark.parametrize('mode,steps', [('generate', ['01', '02', '03', '04']), ('update', ['01', '02', '03', '04', '05']), ('help', ['01'])])
def test_step_numbers_follow_visible_panels(app, mode, steps):
    app.mode(mode)
    assert app.js(STEPS) == steps
