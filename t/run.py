import asyncio, os, json
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
html=open(os.path.join(ROOT,'tc-agent.html')).read()
skel='<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light;padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)}body{margin:0;font:14px system-ui;background:#fafafa}img{max-width:100%}[hidden]{display:none!important}</style></head><body>'+html+'</body></html>'
LIB={'mammoth@1.8.0/mammoth.browser.min.js':'mammoth-1.8.0/package/mammoth.browser.min.js','pdfjs-dist@3.11.174/build/pdf.min.js':'pdfjs-dist-3.11.174/package/build/pdf.min.js','pdfjs-dist@3.11.174/build/pdf.worker.min.js':'pdfjs-dist-3.11.174/package/build/pdf.worker.min.js','xlsx@0.18.5/dist/xlsx.full.min.js':'xlsx-0.18.5/package/dist/xlsx.full.min.js'}
async def route(r):
    u=r.request.url
    if u.startswith('http://app.test/'): return await r.fulfill(body=skel, content_type='text/html')
    for k,v in LIB.items():
        if k in u: return await r.fulfill(path=os.path.join(ROOT,'libs',v), content_type='application/javascript')
    await r.abort()
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        errs=[]
        for mode in ['desktop','mobile']:
            ctx=await b.new_context(viewport={'width':1360,'height':900} if mode=='desktop' else {'width':400,'height':860}, color_scheme='light' if mode=='desktop' else 'dark')
            await ctx.add_init_script(path=os.path.join(D,'mock.js'))
            pg=await ctx.new_page(); await pg.route('**/*', route)
            pg.on('pageerror', lambda e: errs.append('PAGEERR '+str(e)))
            pg.on('console', lambda m: errs.append('CONSOLE '+m.text) if m.type=='error' and 'net::' not in m.text and 'Failed to load resource' not in m.text else None)
            await pg.goto('http://app.test/'); await pg.wait_for_timeout(600)
            if mode=='desktop':
                await pg.screenshot(path=os.path.join(D,'s1_initial.png'))
                await pg.set_input_files('#file-input',[os.path.join(D,f) for f in ['cart.docx','req.xlsx','spec.pdf']])
                await pg.wait_for_function("() => ![...document.querySelectorAll('.doc-meta')].some(e=>e.textContent.includes('разбор'))", timeout=20000)
                print('DOCS:', await pg.inner_text('#doc-list'))
                for i in range(3):
                    await pg.click(f'#doc-list li:nth-child({i+2}) [data-doc-act=preview]')
                print('PREVIEWS:', [t[:160] for t in await pg.locator('.doc-preview').all_inner_texts()])
                for i in range(3): await pg.click(f'#doc-list li:nth-child({i+2}) [data-doc-act=preview]')
            await pg.click('#btn-run')
            await pg.wait_for_selector('#btn-run:not([hidden])', timeout=30000)
            await pg.wait_for_timeout(300)
            print(mode,'CALLS', len(await pg.evaluate('window.__calls')))
            await pg.screenshot(path=os.path.join(D,f's2_agent_{mode}.png'), full_page=True)
            await pg.click('#tab-cases'); await pg.click('.case-h'); await pg.wait_for_timeout(100)
            await pg.screenshot(path=os.path.join(D,f's3_cases_{mode}.png'), full_page=True)
            if mode=='desktop':
                await pg.click('[data-act=refine-case]'); await pg.fill('textarea[data-field=comment]','Сделай короче'); await pg.click('[data-act=do-refine]'); await pg.wait_for_timeout(700)
                print('REFINED:', (await pg.inner_text('#case-list article:first-child .case-t')))
                await pg.click('#tab-reqs'); await pg.click('tr.req-row'); await pg.screenshot(path=os.path.join(D,'s4_reqs.png'), full_page=True)
                await pg.click('#tab-json'); await pg.click('[data-act=download]'); await pg.wait_for_timeout(200)
                print('DL', await pg.evaluate('window.__dl'))
                await pg.screenshot(path=os.path.join(D,'s5_json.png'))
                await pg.click('#tab-templates'); await pg.fill('#tpl-prefix','PRJ-API-'); await pg.click('[data-act=tpl-save]'); await pg.wait_for_timeout(200)
                await pg.screenshot(path=os.path.join(D,'s6_tpl.png'), full_page=True)
                await pg.click('#tab-history'); await pg.wait_for_timeout(2500); await pg.click('#tab-agent'); await pg.click('#tab-history'); await pg.wait_for_timeout(300)
                print('HIST:', (await pg.inner_text('#tab-body'))[:300])
                keys=await pg.evaluate('[...window.__store.keys()]'); print('STORE', keys)
                print('BODY_W', await pg.evaluate('document.documentElement.scrollWidth'))
            else:
                print('MOBILE_W', await pg.evaluate('document.documentElement.scrollWidth'))
            await ctx.close()
        print('ERRORS', errs)
        await b.close()
asyncio.run(main())
