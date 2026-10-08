import asyncio, os, json
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
skel='<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0;font:14px system-ui;background:#fafafa}img{max-width:100%}[hidden]{display:none!important}</style></head><body>'+html+'</body></html>'
LIB={'mammoth@1.8.0/mammoth.browser.min.js':'mammoth-1.8.0/package/mammoth.browser.min.js','pdfjs-dist@3.11.174/build/pdf.min.js':'pdfjs-dist-3.11.174/package/build/pdf.min.js','pdfjs-dist@3.11.174/build/pdf.worker.min.js':'pdfjs-dist-3.11.174/package/build/pdf.worker.min.js','xlsx@0.18.5/dist/xlsx.full.min.js':'xlsx-0.18.5/package/dist/xlsx.full.min.js'}
async def route(r):
    u=r.request.url
    if u.startswith('http://app.test/'): return await r.fulfill(body=skel, content_type='text/html; charset=utf-8')
    for k,v in LIB.items():
        if k in u: return await r.fulfill(path=os.path.join(ROOT,'libs',v), content_type='application/javascript')
    await r.abort()
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        for mode in ['desktop','mobile']:
            ctx=await b.new_context(viewport={'width':1360,'height':900} if mode=='desktop' else {'width':400,'height':860}, color_scheme='light' if mode=='desktop' else 'dark')
            await ctx.add_init_script(path=os.path.join(D,'mock.js'))
            pg=await ctx.new_page(); await pg.route('**/*', route)
            pg.on('pageerror', lambda e: errs.append('PAGEERR '+str(e)))
            pg.on('console', lambda m: errs.append('CONSOLE '+m.text) if m.type=='error' and 'net::' not in m.text and 'Failed to load' not in m.text else None)
            await pg.goto('http://app.test/'); await pg.wait_for_timeout(600)
            if mode=='desktop':
                await pg.screenshot(path=os.path.join(D,'v2_initial.png'))
                await pg.set_input_files('#file-input',[os.path.join(D,f) for f in ['cart.docx','req.xlsx','spec.pdf']])
                await pg.wait_for_function("() => ![...document.querySelectorAll('.doc-meta')].some(e=>e.textContent.includes('разбор'))", timeout=20000)
            print(mode, 'RUN BTN:', await pg.inner_text('#btn-run'))
            await pg.click('#btn-run')
            await pg.wait_for_selector('#btn-run:not([hidden])', timeout=30000); await pg.wait_for_timeout(300)
            await pg.screenshot(path=os.path.join(D,f'v2_agent_{mode}.png'), full_page=True)
            if mode=='mobile':
                print('MOBILE_W', await pg.evaluate('document.documentElement.scrollWidth')); await ctx.close(); continue
            await pg.click('#tab-checklist'); await pg.wait_for_timeout(100)
            await pg.click('[data-act=cl-suite][data-id=CL-002][data-s=smoke]')
            await pg.screenshot(path=os.path.join(D,'v2_checklist.png'), full_page=True)
            await pg.click('[data-act=cl-dl-md]'); await pg.wait_for_timeout(100); print('CL DL', await pg.evaluate('window.__dl'))
            await pg.click('#tab-cases'); await pg.click('.case-h'); await pg.click('[data-act=fsuite][data-s=smoke]'); await pg.wait_for_timeout(100)
            print('SMOKE FILTER COUNT', await pg.locator('#case-list article').count())
            await pg.click('[data-act=fsuite][data-s=smoke]')
            await pg.screenshot(path=os.path.join(D,'v2_cases.png'), full_page=True)
            await pg.click('#tab-questions'); await pg.fill('textarea[data-q="Q-01"]','При 4-м запросе показываем таймер обратного отсчёта')
            print('APPLY BTN:', await pg.inner_text('[data-act=apply-answers]'))
            await pg.click('[data-act=apply-answers]'); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=30000); await pg.wait_for_timeout(300)
            await pg.screenshot(path=os.path.join(D,'v2_questions.png'), full_page=True)
            print('Q LOG:', await pg.locator('#tab-body .log').inner_text())
            await pg.click('#tab-export'); await pg.click('[data-act=dl-out]'); await pg.wait_for_timeout(100); print('DEFAULT DL', await pg.evaluate('window.__dl'))
            await pg.click('#cfgtab-export'); await pg.fill('#cfg-export','CSV для импорта в Test IT, шаг на строку')
            await pg.click('[data-act=run-export]'); await pg.wait_for_selector('[data-act=dl-out]', timeout=20000); await pg.wait_for_timeout(200)
            await pg.click('[data-act=dl-out]'); await pg.wait_for_timeout(100); print('CSV DL', await pg.evaluate('window.__dl'))
            print('CSV PREVIEW', (await pg.locator('.json-pre').inner_text())[:200])
            await pg.screenshot(path=os.path.join(D,'v2_export.png'), full_page=True)
            await pg.fill('#cfg-export','Excel для Test IT'); await pg.click('[data-act=run-export]'); await pg.wait_for_selector('.exp-card ~ .sec-h [data-act=dl-out]', timeout=20000); await pg.wait_for_timeout(300)
            await pg.click('[data-act=dl-out]'); await pg.wait_for_timeout(1500); print('XLSX DL', await pg.evaluate('window.__dl'))
            await pg.click('#cfgtab-tpl'); await pg.click('[data-cfgtype=ui]'); await pg.fill('#cfg-prefix','UI-PRJ-')
            await pg.click('[data-cfg=save]'); await pg.wait_for_timeout(200)
            await pg.click('[data-cfg=expand]'); await pg.wait_for_timeout(100)
            await pg.screenshot(path=os.path.join(D,'v2_overlay.png'))
            await pg.keyboard.press('Escape')
            await pg.click('#cfgtab-rules'); await pg.fill('#cfg-rules','Больше негативных'); await pg.click('[data-cfg=save]'); await pg.wait_for_timeout(200)
            await pg.click('#cfgtab-tpl'); await pg.wait_for_timeout(100)
            await pg.locator('.rail').screenshot(path=os.path.join(D,'v2_rail.png'))
            await pg.click('#tab-history'); await pg.wait_for_timeout(2600); await pg.click('#tab-agent'); await pg.click('#tab-history'); await pg.wait_for_timeout(300)
            print('HIST:', (await pg.inner_text('#tab-body'))[:200].replace('\n',' | '))
            print('STORE', await pg.evaluate('[...window.__store.keys()]'))
            print('W', await pg.evaluate('document.documentElement.scrollWidth'))
            await ctx.close()
        print('ERRORS', errs); await b.close()
asyncio.run(main())
