# Документы с расхождениями: «расхождений N · Показать» → окно с расхождениями по разделам → «Открыть раздел»
import asyncio, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run27 import dbop, serve, IDX, wait_idle, D
from playwright.async_api import async_playwright
ROWS = "els => els.map(e => ({ name: e.querySelector('.doc-name').textContent, conf: e.querySelector('.doc-meta .warn')?.textContent || '', btn: !!e.querySelector('[data-doc-act=conf]') }))"
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script="window.__qaTest = true; window.__sampleDelay = 15;")
        for f in ('mockgen.js','mock_shared.js'): await ctx.add_init_script(path=os.path.join(D,f))
        await ctx.route('http://kb2.test/**', serve)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://kb2.test/'); await pg.wait_for_timeout(2500)
        await pg.click('[data-act=kb-run]') if await pg.locator('[data-act=kb-run]').count() else None
        await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(300)
        await pg.set_input_files('#file-input', [os.path.join(D,'kb_extra.md'), os.path.join(D,'kb_созвон-call.md')]); await pg.wait_for_timeout(1500); await wait_idle(pg)
        print('C1 generate mode rows:', await pg.eval_on_selector_all('#doc-list .doc', ROWS))
        await pg.click('#doc-list li:has-text("созвон") [data-doc-act=conf]'); await pg.wait_for_timeout(300)
        dlg = await pg.evaluate("({ open: !document.querySelector('#mat-ov').hidden, title: document.querySelector('#mat-title').textContent, body: document.querySelector('#mat-body').innerText.replace(/\\n/g, ' | '), marks: [...document.querySelectorAll('#mat-body mark')].map(m => m.textContent) })")
        print('C2 dialog:', json.dumps(dlg, ensure_ascii=False))
        await pg.screenshot(path=os.path.join(D, 'v32_doc_conflicts.png'))
        await pg.click('#mat-body [data-conf-open]'); await pg.wait_for_timeout(500)
        print('C3 open section:', await pg.evaluate("({ mode: __qa.S.settings.mode, dialogClosed: document.querySelector('#mat-ov').hidden, title: document.querySelector('.kb-art h3')?.textContent })"))
        # старые разделы: расхождения есть только в самом разделе — подгружаются
        await pg.evaluate("(() => { for (const b of __qa.S.kb.index.blocks) delete b.cf; __qa.S.kb.cache = {}; })()")
        await pg.click('#help-head [data-v=qa]'); await pg.wait_for_timeout(800)
        print('C4 legacy index (loaded lazily):', await pg.eval_on_selector_all('#doc-list .doc', ROWS))
        await b.close(); print('ERRORS:', errs or 'none')
asyncio.run(main())
