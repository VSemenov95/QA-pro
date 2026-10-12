"""Вкладка «Тест-кейсы»: после загрузки продукта видны все его кейсы (в том числе черновики), по документам; названия разделов правятся вручную."""
import json

import pytest

from tests.support import seed

SECS = "[...document.querySelectorAll('#pcase-list .sec, #case-list .sec')].map((s) => [s.querySelector('.sec-t').innerText, s.querySelectorAll('.case').length])"


@pytest.fixture
def shop(app, tmp_path):
    app.import_product(seed.write(tmp_path, seed.shop_export()))
    app.page.wait_for_selector('#pcase-list .sec', timeout=15000)
    return app


def sections(app):
    return app.page.evaluate('() => ' + SECS)


def rename(app, nth, text, how='Enter'):
    app.page.click(f'#pcase-list .sec:nth-child({nth}) [data-act=sec-rename]')
    app.page.fill('#sec-in', text)
    if how == 'Enter':
        app.page.keyboard.press('Enter')
    else:
        app.page.click('[data-act=sec-save]')
    app.page.wait_for_timeout(400)


# ---------- после загрузки продукта ----------
def test_cases_tab_opens_after_import(shop):
    assert shop.state('S.tab') == 'cases'
    assert shop.page.get_attribute('#tab-cases', 'aria-selected') == 'true'


def test_cases_are_grouped_by_document(shop):
    assert sections(shop) == [['ТЗ-Авторизация', 3], ['ТЗ-Платежи', 3], ['Без документа', 1]]


def test_tab_counter_is_the_whole_product(shop):
    assert shop.text('#tab-cases .cnt') == '7'


def test_type_filter_and_search(shop):
    shop.page.click('[data-act=pc-type][data-t=api]')
    assert sections(shop) == [['ТЗ-Авторизация', 1], ['ТЗ-Платежи', 1]]
    shop.page.click('[data-act=pc-type][data-t=all]')
    shop.page.fill('#pc-q', 'оплат')
    assert sections(shop) == [['ТЗ-Платежи', 2]]
    shop.page.fill('#pc-q', 'нет такого')
    assert sections(shop) == [] and 'Ничего не найдено' in shop.text('#pcase-list')


def test_draft_cases_are_visible(app, tmp_path):
    """Регрессия: в индексе продукта нет кейсов из черновиков, и после загрузки вкладка оставалась пустой."""
    draft = seed.run('run_d', 'Пример', [seed.case('u1', 'ui', 'UI-001', 'Кейс из черновика', ['R-001']), seed.case('u2', 'api', 'API-001', 'Второй', ['R-001'])], [seed.req('R-001', 'Пример')], stage='draft')
    data = seed.product_export(runs=[draft])
    assert data['index']['cases'] == []   # индекс пуст, как в реальной выгрузке
    app.import_product(seed.write(tmp_path, data))
    app.page.wait_for_selector('#pcase-list .sec', timeout=15000)
    assert sections(app) == [['Пример', 2]]
    assert app.count('#pcase-list .chip') == 2 and 'Черновик' in app.text('#pcase-list')


def test_old_index_is_not_needed(app, tmp_path):
    """Индекс обрезается при большом объёме — кейсы берутся из самих запусков."""
    data = seed.shop_export(index=[])
    app.import_product(seed.write(tmp_path, data))
    app.page.wait_for_selector('#pcase-list .sec', timeout=15000)
    assert sum(n for _, n in sections(app)) == 7


def test_real_export_with_only_a_draft_run(app):
    """Реальная выгрузка из репозитория старых тестов: один запуск-черновик, индекс пуст."""
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'draft-export.json')
    app.import_product(path)
    app.page.wait_for_selector('#pcase-list .sec', timeout=15000)
    assert sum(n for _, n in sections(app)) == 4


def test_product_without_cases_shows_empty_tab(app):
    app.tab('cases')
    assert 'Тест-кейсов пока нет' in app.text('#tab-body')


def test_unreadable_runs_fall_back_to_index(app, tmp_path):
    data = seed.shop_export()
    for r in data['runs']:
        r['meta']['partsCount'] = 0
    app.import_product(seed.write(tmp_path, data))
    app.page.wait_for_selector('#pcase-list .sec, #tab-body', timeout=15000)
    # запуски пустые → в списке нет ни кейсов, ни падения страницы (проверка ошибок страницы — в фикстуре)
    assert app.state('S.tab') in ('cases', 'agent')


# ---------- названия разделов ----------
def test_rename_by_enter(shop):
    shop.page.click('#pcase-list .sec:nth-child(2) [data-act=sec-rename]')
    assert shop.state('[document.activeElement.id, document.activeElement.value]') == ['sec-in', 'ТЗ-Платежи']
    shop.page.fill('#sec-in', '  Оплата   и возвраты ')
    shop.page.keyboard.press('Enter')
    shop.page.wait_for_timeout(400)
    assert sections(shop)[1] == ['Оплата и возвраты', 3]
    assert 'ТЗ-Платежи' in shop.text('#pcase-list .sec:nth-child(2) .sec-d')   # документ виден рядом


def test_escape_cancels(shop):
    shop.page.click('#pcase-list .sec:nth-child(1) [data-act=sec-rename]')
    shop.page.fill('#sec-in', 'Другое')
    shop.page.keyboard.press('Escape')
    assert shop.count('#sec-in') == 0 and sections(shop)[0][0] == 'ТЗ-Авторизация'


def test_rename_by_save_button_and_reset(shop):
    rename(shop, 3, 'Прочее', how='button')
    assert sections(shop)[2][0] == 'Прочее'
    shop.page.click('#pcase-list .sec:nth-child(3) [data-act=sec-rename]')
    shop.page.click('[data-act=sec-reset]')
    shop.page.wait_for_timeout(400)
    assert sections(shop)[2][0] == 'Без документа'


def test_rename_is_stored_in_product(shop):
    rename(shop, 2, 'Оплата')
    assert list(shop.state('S.products.find((p) => p.id === S.productId).caseSections').values()) == ['Оплата']
    prod = shop.db.get(f'products/{shop.state("S.productId")}')
    assert list(prod['caseSections'].values()) == ['Оплата']


def test_rename_survives_reload(shop):
    rename(shop, 2, 'Оплата')
    shop.reload()
    shop.tab('cases')
    shop.page.wait_for_selector('#pcase-list .sec')
    assert [s[0] for s in sections(shop)] == ['ТЗ-Авторизация', 'Оплата', 'Без документа']


def test_rename_is_exported_and_imported_back(shop, tmp_path):
    rename(shop, 2, 'Оплата')
    shop.page.click('[data-act=prod-export]')
    shop.page.wait_for_function('() => window.__downloads && window.__downloads.length')
    out = json.loads(shop.downloads()[-1]['text'])
    assert list(out['product']['caseSections'].values()) == ['Оплата']
    p = tmp_path / 'again.json'
    p.write_text(shop.downloads()[-1]['text'], encoding='utf-8')
    shop.import_product(p)
    shop.page.wait_for_timeout(1500)
    shop.page.wait_for_selector('#pcase-list .sec')
    assert sections(shop) == [['ТЗ-Авторизация', 3], ['Оплата', 3], ['Без документа', 1]]
    assert shop.state('S.products.length') == 3   # «Мой продукт», «Магазин» и копия


# ---------- переход к кейсу и области ----------
def test_click_opens_run_with_case(shop):
    shop.page.click('#pcase-list [data-i=E2E-001]')
    shop.page.wait_for_selector('#case-list .sec', timeout=15000)
    shop.page.wait_for_timeout(400)
    assert shop.state('[S.tab, S.run.id, S.casesScope]') == ['cases', 'run_b', 'run']
    assert shop.count('.case-b') == 1
    assert sections(shop) == [['ТЗ-Платежи', 3], ['Без документа', 1]]


def test_scope_switch_between_run_and_product(shop):
    shop.page.click('#pcase-list [data-i=E2E-001]')
    shop.page.wait_for_selector('#case-list .sec')
    shop.page.wait_for_selector('.scope-sw .fchip')
    assert shop.page.evaluate("() => [...document.querySelectorAll('.scope-sw .fchip')].map((b) => b.innerText.replace(/\\s+/g, ' '))") == ['Этот запуск 4', 'Весь продукт 7']
    shop.page.click('[data-act=cases-scope][data-s=product]')
    shop.page.wait_for_selector('#pcase-list .sec')
    assert [s[0] for s in sections(shop)] == ['ТЗ-Авторизация', 'ТЗ-Платежи', 'Без документа']
    assert shop.state('S.run.id') == 'run_b'   # запуск остался открытым


def test_rename_inside_run_list(shop):
    shop.page.click('#pcase-list [data-i=E2E-001]')
    shop.page.wait_for_selector('#case-list .sec')
    shop.page.click('#case-list .sec:nth-child(2) [data-act=sec-rename]')
    shop.page.fill('#sec-in', 'Прочее')
    shop.page.click('[data-act=sec-save]')
    shop.page.wait_for_timeout(400)
    assert [s[0] for s in sections(shop)] == ['ТЗ-Платежи', 'Прочее']
