# Кнопка «Добавить пример ТЗ» видна только в пустом продукте — в базе знаний и в генерации.
import asyncio, os, time
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
SKEL='<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>[hidden]{display:none!important}body{margin:0}</style></head><body>'+html+'</body></html>'
standalone=open(os.path.join(ROOT,'qa-pro.html'),encoding='utf-8').read()
STORE={}
def dbop(source, op, path, payload=None):
    if op=='get': return STORE.get(path)
    if op=='set': STORE[path]=payload; return True
    if op=='update':
        if path not in STORE: return 'missing'
        STORE[path]={**STORE[path], **payload}; return True
    if op=='delete': STORE.pop(path,None); return True
    if op=='list':
        rows=[[p,d] for p,d in STORE.items() if p.startswith(path+'/') and '/' not in p[len(path)+1:]]
        return rows[:payload.get('lim') or 1000]
    if op=='acquire': return {'acquired':True}
async def state(pg):
    return await pg.evaluate("({ docs: __qa.S.docs.map(d => d.name), sample: !document.querySelector('#btn-sample').hidden, mode: __qa.S.settings.mode })")
async def remove_all(pg):
    while await pg.locator('#doc-list [data-doc-act=remove]').count():
        await pg.click('#doc-list [data-doc-act=remove] >> nth=0'); await pg.wait_for_timeout(150)
        if await pg.locator('#doc-list [data-doc-act=remove].armed').count(): await pg.click('#doc-list [data-doc-act=remove].armed >> nth=0')
        await pg.wait_for_timeout(500)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script='window.__qaTest = true;')
        for f in ('mockgen.js','mock_shared.js'): await ctx.add_init_script(path=os.path.join(D,f))
        async def serve(r): await r.fulfill(body=SKEL, content_type='text/html; charset=utf-8')
        await ctx.route('http://s.test/**', serve)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://s.test/'); await pg.wait_for_timeout(2500)
        await pg.click('[data-mode=help]'); await pg.wait_for_timeout(400)
        print('S1 KB, sample doc present:', await state(pg))
        await remove_all(pg)
        print('S2 KB, product empty:', await state(pg))
        await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(300)
        print('S3 generate, product empty:', await state(pg))
        await pg.set_input_files('#file-input', os.path.join(D,'rules.md')); await pg.wait_for_timeout(1200)
        print('S4 generate, own doc:', await state(pg))
        await pg.click('[data-mode=help]'); await pg.wait_for_timeout(300)
        print('S5 KB, own doc:', await state(pg))
        await remove_all(pg)
        print('S6 KB, removed again:', await state(pg))
        await pg.click('#btn-sample'); await pg.wait_for_timeout(800)
        print('S7 KB, sample added by button:', await state(pg))
        await pg.reload(); await pg.wait_for_timeout(2500)
        print('S8 after reload:', await state(pg))
        # автономная версия: то же правило
        sa=await b.new_context(viewport={'width':1360,'height':900})
        await sa.add_init_script(script='window.__qaTest = true;')
        async def serve2(r): await r.fulfill(body=standalone, content_type='text/html; charset=utf-8')
        await sa.route('http://local.test/**', serve2)
        ps=await sa.new_page(); ps.on('pageerror', lambda e: errs.append('SA '+str(e)))
        await ps.goto('http://local.test/'); await ps.wait_for_timeout(2500)
        print('S9 standalone start:', await state(ps))
        await remove_all(ps)
        print('S10 standalone empty:', await state(ps))
        await b.close()
        print('ERRORS:', errs or 'none')
asyncio.run(main())
