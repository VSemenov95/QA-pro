"""Чек-лист скачивается в Word (.docx) и печатается в PDF: те же пункты, что и в Markdown и JSON."""
import base64
import io
import xml.etree.ElementTree as ET
import zipfile

import pytest


@pytest.fixture
def checklist(app):
    app.add_sample()
    app.generate()
    app.tab('checklist')
    return app


def first_item(app):
    return app.state("S.run.checklist.groups.find((g) => g.items.length).items[0]")


def blob_bytes(app):
    b64 = app.js("""async () => { const b = window.__dlBlob; const u = new Uint8Array(await b.arrayBuffer()); let s = ''; for (const x of u) s += String.fromCharCode(x); return btoa(s); }""")
    return base64.b64decode(b64)


def test_checklist_offers_word_and_pdf(checklist):
    assert checklist.page.is_visible('[data-act=cl-dl-docx]')
    assert checklist.page.is_visible('[data-act=cl-print]')


def test_word_file_is_a_valid_document_with_checklist(checklist):
    n = len(checklist.downloads())
    checklist.page.click('[data-act=cl-dl-docx]')
    checklist.page.wait_for_function('(n) => (window.__downloads || []).length > n', arg=n)
    assert checklist.downloads()[-1]['filename'].endswith('.docx'), checklist.downloads()[-1]
    data = blob_bytes(checklist)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert '[Content_Types].xml' in z.namelist() and 'word/document.xml' in z.namelist()
        root = ET.fromstring(z.read('word/document.xml'))
    text = ''.join(t.text or '' for t in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
    item = first_item(checklist)
    assert 'Чек-лист' in text
    assert f"☐ 1  {item['check']}" in text and 'CL-' not in text and 'R-00' not in text
    import docx  # настоящий разборщик Word: файл должен открываться без ошибок
    paragraphs = [p.text for p in docx.Document(io.BytesIO(data)).paragraphs]
    assert any(p.startswith('☐ 1 ') and item['check'] in p for p in paragraphs)


def test_pdf_print_page_has_checklist(checklist):
    checklist.page.click('[data-act=cl-print]')
    checklist.page.wait_for_function("() => [...document.querySelectorAll('iframe')].some((f) => (f.srcdoc || '').includes('Чек-лист'))")
    srcdoc = checklist.page.evaluate("() => [...document.querySelectorAll('iframe')].map((f) => f.srcdoc || '').find((s) => s.includes('Чек-лист'))")
    item = first_item(checklist)
    assert '<span class="id">1</span>' in srcdoc and item['check'] in srcdoc and 'CL-' not in srcdoc and 'R-00' not in srcdoc
    assert 'Источники' in srcdoc
