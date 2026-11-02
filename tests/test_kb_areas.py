"""База знаний по частям: API — раздел на эндпоинт, UI и E2E — по функциональности; карта знаний в README.md папки
контекста; генерация и актуализация берут из карты и базы знаний части своего вида тестов."""
import pytest

from tests.support import model_kb
from tests.test_context_kb import kb_files, kbapp  # noqa: F401 — фикстура папки контекста
from tests.test_context_source import repo


def test_area_of_section_by_title(app):
    area = lambda t, a='': app.call(f"a.kbAreaOf({{ title: {t!r}, area: {a!r} }})")
    assert area('POST /api/v1/orders — создание заказа') == 'api'
    assert area('API администрирования: справочники') == 'api'
    assert area('Восстановление пароля') == 'ui'
    assert area('Список сервисов: UI, права и API-контракты') == 'ui'   # про интерфейс, хоть и с API
    assert area('Сквозной сценарий: заказ от корзины до оплаты') == 'e2e'
    assert area('Общие сведения') == 'common'
    assert area('Восстановление пароля', 'e2e') == 'e2e'   # отметка разбора главнее названия


def test_endpoint_key_ignores_base_url_and_param_names(app):
    a = app.call("a.kbEndpoint('POST /api/v1/orders/{orderId}/items — добавление позиции')")
    b = app.call("a.kbEndpoint('Вызвать POST {baseURL}/api/v1/orders/:id/items с телом:')")
    assert a == b == 'POST /api/v1/orders/{}/items'


SECTIONS = """(() => {
  S.productId = 'p1'; S.kb.pid = 'p1';
  const mk = (id, title, area, text) => ({ b: { id, title, area, summary: '' }, d: { id, title, area, synth: text, parts: [], conflicts: [], links: [] } });
  const xs = [
    mk('k1', 'POST /api/v1/orders — создание заказа', 'api', '### Описание\\n- Создаёт заказ ORDER-API-ТЕКСТ'),
    mk('k2', 'GET /api/v1/orders/{id} — заказ по id', 'api', '### Описание\\n- Возвращает заказ ORDER-GET-ТЕКСТ'),
    mk('k3', 'Оформление заказа', 'ui', '### Описание\\n- Экран оформления заказа ORDER-UI-ТЕКСТ'),
    mk('k4', 'Заказ от корзины до оплаты', 'e2e', '### Описание\\n- Сквозной путь заказа ORDER-E2E-ТЕКСТ'),
  ];
  S.kb.index = { ...S.kb.index, blocks: xs.map((x) => x.b) };
  S.kb.cache = Object.fromEntries(xs.map((x) => [x.b.id, x.d]));
  return true;
})()"""


def test_generation_reads_sections_of_its_part(app):
    app.call(SECTIONS)
    run = "{ productId: 'p1' }"
    api = app.call(f"a.kbGenBlock({run}, 'batch', 'создание заказа POST /api/v1/orders', 'api')")
    ui = app.call(f"a.kbGenBlock({run}, 'batch', 'оформление заказа', 'ui')")
    e2e = app.call(f"a.kbGenBlock({run}, 'batch', 'заказ оформление создание', 'e2e')")
    assert 'ORDER-API-ТЕКСТ' in api and 'ORDER-UI-ТЕКСТ' not in api and 'ORDER-E2E-ТЕКСТ' not in api
    assert 'ORDER-UI-ТЕКСТ' in ui and 'ORDER-API-ТЕКСТ' not in ui
    assert 'ORDER-E2E-ТЕКСТ' in e2e and 'ORDER-UI-ТЕКСТ' in e2e   # E2E видит все части


def test_named_endpoint_section_comes_first(app):
    app.call(SECTIONS)
    r = app.call("a.kbGenBlock({ productId: 'p1' }, 'batch', 'Вызвать GET {baseURL}/api/v1/orders/42 — создание заказа', 'api')")
    assert r.index('ORDER-GET-ТЕКСТ') < r.index('ORDER-API-ТЕКСТ')


def test_map_for_a_type_lists_only_its_parts(app):
    app.call(SECTIONS)
    api = app.call("a.kbMapFor({ productId: 'p1' }, 'api')")
    ui = app.call("a.kbMapFor({ productId: 'p1' }, 'ui')")
    assert '## Карта знаний продукта' in api and '`POST /api/v1/orders` — создание заказа' in api and 'Оформление заказа' not in api
    assert '#### UI — по функциональности (1)' in ui and 'POST /api/v1/orders' not in ui


def test_map_markdown_groups_sections(app):
    app.call(SECTIONS)
    md = app.call("a.kbMapMd('Магазин', 'shop', S.kb.index.blocks, (id) => 'products/shop/kb/x/' + id + '.md')")
    assert md.startswith('<!-- qa-pro:kbmap shop -->') and md.endswith('<!-- /qa-pro:kbmap shop -->')
    for h in ('#### API — по эндпоинтам (2)', '#### UI — по функциональности (1)', '#### E2E — сквозные сценарии (1)'):
        assert h in md
    assert '- `GET /api/v1/orders/{id}` — заказ по id → [k2.md](products/shop/kb/x/k2.md)' in md


# ---------- папка контекста ----------
def readme(app):
    app.page.wait_for_function('() => !window.__qa.S.ctx.pending.size', timeout=15000)
    return repo(app, 'README.md') or ''


def test_connecting_folder_does_not_write_readme(kbapp):
    kbapp.page.wait_for_function("() => document.querySelectorAll('#kb-rows .kb-row').length === 2")
    assert 'README.md' not in kbapp.state('[...S.ctx.pending]')


def test_readme_gets_product_knowledge_map_after_parsing(kbapp):
    kbapp.page.click('[data-act=kb-run]')
    kbapp.wait_idle()
    md = readme(kbapp)
    assert '## Карта знаний' in md and '<!-- qa-pro:kbmap moi -->' in md and '<!-- /qa-pro:kbmap moi -->' in md
    assert 'Восстановление пароля' in md and '#### UI — по функциональности' in md


def test_parsed_sections_go_to_folders_of_their_part(kbapp):
    before = set(kb_files(kbapp))
    kbapp.page.click('[data-act=kb-run]')
    kbapp.wait_idle()
    kbapp.page.wait_for_function('() => !window.__qa.S.ctx.pending.size', timeout=15000)
    new = [k for k in kb_files(kbapp) if k not in before]
    assert new and all(k.split('/')[3] in ('api', 'ui', 'e2e', 'common') for k in new), new


def test_kb_list_filters_by_part(kbapp):
    kbapp.page.wait_for_function("() => document.querySelectorAll('#kb-rows .kb-row').length === 2")
    assert 'UI' in kbapp.text('.kb-areas')
    kbapp.page.click('.kb-areas [data-a=ui]')
    n = kbapp.page.evaluate("() => document.querySelectorAll('#kb-rows .kb-row').length")
    assert n == kbapp.call("S.kb.index.blocks.filter((b) => a.kbAreaOf(b) === 'ui').length")
