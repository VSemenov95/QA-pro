"""Автономная версия (qa-pro.html): страница открывается, в ней сразу есть продукт, данные хранятся в браузере."""


def test_standalone_opens_with_default_product(make_app):
    a = make_app(kind='standalone')
    assert a.state('S.caps.ready') is True
    assert a.state('S.products.map((p) => p.name)') == ['Мой продукт']


def test_standalone_keeps_new_product_after_reload(make_app):
    a = make_app(kind='standalone')
    a.create_product('Автономный')
    a.reload()
    names = a.state('S.products.map((p) => p.name)')
    assert 'Автономный' in names and 'Мой продукт' in names and len(names) == 2
