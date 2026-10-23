"""Оглавление базы знаний ссылается на разделы с расхождениями, а самих записей разделов нет (удалили в другом окне,
перенесли в папку источника). Страница не должна читать их по кругу и зависать."""
import time


SEED = """(async () => {
  const blocks = Array.from({ length: 30 }, (_, i) => ({ id: 'kbx' + i, title: 'Раздел ' + i, summary: 's', docIds: ['d1'], parts: 1, size: 10, updatedAt: 1, ph: 'x', sh: 'x', conf: 2 }));
  await a.kbIdxWrite(S.productId, blocks, {}, null);   // записей разделов нет, у строк оглавления нет cf
  await a.loadKb(S.productId);
  return true;
})()"""


def test_missing_sections_with_conflicts_are_not_read_in_a_loop(app):
    app.add_sample()
    app.call(SEED)
    reads = lambda: app.page.evaluate('() => window.__dbReads || 0')
    app.page.evaluate("""() => { const db = window.__qa.S.caps.db, doc = db.doc.bind(db); window.__dbReads = 0;
      window.__qa.S.caps.db = { ...db, doc: (p) => { const r = doc(p); return /\\/kb\\/kbx/.test(p) ? { ...r, get: async () => { window.__dbReads++; return r.get(); } } : r; } }; }""")
    app.call('(window.__qa.renderAll(), true)')
    app.page.wait_for_timeout(1500)
    first = reads()
    app.page.wait_for_timeout(1500)
    t = time.time(); app.page.evaluate('() => 1'); lag = time.time() - t
    assert reads() == first and first <= 30, (first, reads())   # каждый раздел — не больше одного раза
    assert lag < 1
