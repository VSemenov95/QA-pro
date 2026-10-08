import asyncio, os, json
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
skel='<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light}body{margin:0;font:14px system-ui;background:#fafafa}img{max-width:100%}[hidden]{display:none!important}</style></head><body>'+html+'</body></html>'
standalone=open(os.path.join(ROOT,'qa-pro.html'),encoding='utf-8').read()
LIB={'mammoth@1.8.0/mammoth.browser.min.js':'mammoth-1.8.0/package/mammoth.browser.min.js','pdfjs-dist@3.11.174/build/pdf.min.js':'pdfjs-dist-3.11.174/package/build/pdf.min.js','pdfjs-dist@3.11.174/build/pdf.worker.min.js':'pdfjs-dist-3.11.174/package/build/pdf.worker.min.js','xlsx@0.18.5/dist/xlsx.full.min.js':'xlsx-0.18.5/package/dist/xlsx.full.min.js'}
async def route(r):
    u=r.request.url
    if u=='http://app.test/qa-pro.html': return await r.fulfill(body=standalone, content_type='text/html; charset=utf-8')
    if u.startswith('http://app.test/'): return await r.fulfill(body=skel, content_type='text/html; charset=utf-8')
    if u.startswith('http://local.test/'): return await r.fulfill(body=standalone, content_type='text/html; charset=utf-8')
    for k,v in LIB.items():
        if k in u: return await r.fulfill(path=os.path.join(ROOT,'libs',v), content_type='application/javascript')
    await r.abort()
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        def hook(pg):
            pg.on('pageerror', lambda e: errs.append('PAGEERR '+str(e)))
            pg.on('console', lambda m: errs.append('CONSOLE '+m.text) if m.type=='error' and 'net::' not in m.text and 'Failed to load' not in m.text else None)
        # ---------- claude.ai mode
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock.js'))
        pg=await ctx.new_page(); await pg.route('**/*', route); hook(pg)
        await pg.goto('http://app.test/'); await pg.wait_for_timeout(600)
        await pg.click('#btn-run'); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=30000); await pg.wait_for_timeout(300)
        print('REVIEW BTN visible:', await pg.is_visible('#btn-review'))
        # manual edit case via form
        await pg.click('#tab-cases'); await pg.click('.case-h'); await pg.click('[data-act=form-case]')
        await pg.fill('.case-form input[data-fp="title"]', 'Ручная правка названия')
        await pg.click('[data-act=ff-row][data-op=add]'); 
        rows=await pg.locator('.ff-table tbody tr').count(); print('FORM ROWS after add:', rows)
        await pg.locator('.ff-table tbody tr').nth(rows-1).locator('textarea').first.fill('Новый шаг')
        await pg.click('[data-act=ff-save]'); await pg.wait_for_timeout(100)
        print('TITLE after form save:', await pg.inner_text('#case-list article:first-child .case-t'))
        # add manual case
        await pg.click('.cases-foot [data-act=add-case][data-t=api]'); await pg.wait_for_timeout(100)
        await pg.locator('.case-form input[data-fp="title"]').last.fill('Ручной API-кейс'); await pg.locator('[data-act=ff-save]').last.click()
        print('CASES COUNT:', await pg.locator('#case-list article').count())
        await pg.screenshot(path=os.path.join(D,'v3_cases.png'), full_page=True)
        # refine with AI -> lesson
        await pg.click('#case-list article:first-child [data-act=refine-case]')
        await pg.fill('textarea[data-field=comment]','Укажи код ответа в ожидаемом результате'); await pg.click('[data-act=do-refine]'); await pg.wait_for_timeout(1200)
        print('LESSONS:', await pg.evaluate('JSON.stringify([...window.__store.keys()].filter(k=>k.startsWith("lessons")))'))
        # checklist manual
        await pg.click('#tab-checklist'); await pg.click('[data-act=cl-add][data-gi="0"]'); await pg.fill('#cl-input','Ручной пункт'); await pg.select_option('#cl-group','1'); await pg.click('[data-act=cl-save]')
        await pg.click('[data-act=cl-refine][data-id=CL-001]'); await pg.fill('#clr-input','Укажи конкретный лимит'); await pg.click('[data-act=cl-refine-go]'); await pg.wait_for_timeout(800)
        print('CL-001 text:', await pg.inner_text('#cl-CL-001 .cl-text'))
        await pg.screenshot(path=os.path.join(D,'v3_checklist.png'), full_page=True)
        # review
        await pg.click('#btn-review'); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=30000); await pg.wait_for_timeout(300)
        print('REVIEW TAB:', (await pg.inner_text('#tab-body'))[:300].replace('\n',' | '))
        await pg.screenshot(path=os.path.join(D,'v3_review.png'), full_page=True)
        await pg.locator('[data-act=fd-dismiss]').first.click(); await pg.locator('textarea[data-fd]').first.fill('У нас коды ответа проверяются в отдельном наборе'); await pg.click('[data-act=fd-dismiss-ok]'); await pg.wait_for_timeout(800)
        await pg.click('[data-act=fd-fixall]'); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=30000); await pg.wait_for_timeout(300)
        print('AFTER FIXALL:', (await pg.inner_text('.toolbar'))[:200].replace('\n',' '))
        # cfg review tab with md upload
        await pg.click('#btn-settings'); await pg.click('#settab-review')
        open(os.path.join(D,'rules.md'),'w').write('# Правила ревью\n- Каждый кейс — одно требование\n')
        await pg.click('[data-cfg=load-md]') if False else None
        await pg.set_input_files('#cfg-md', os.path.join(D,'rules.md')); await pg.wait_for_timeout(200)
        print('REVIEW RULES:', await pg.input_value('#cfg-review'))
        await pg.screenshot(path=os.path.join(D,'v17_settings_review.png'))
        await pg.click('#set-ov [data-close]')
        await pg.locator('.rail').screenshot(path=os.path.join(D,'v3_rail.png'))
        # tms in claude mode
        await pg.click('#tab-cases'); await pg.click('[data-act=tms-settings]'); await pg.wait_for_timeout(100)
        print('TMS in settings:', await pg.is_visible('#set-tms'), '| tab:', await pg.eval_on_selector('#set-tabs [aria-selected=true]', 'e=>e.textContent'))
        await pg.screenshot(path=os.path.join(D,'v3_tms_claude.png'))
        await pg.click('#set-ov [data-close]')
        await pg.click('[data-act=tms-upload]'); await pg.wait_for_timeout(100); print('TMS LOG claude:', await pg.inner_text('#tms-bar .log'))
        await pg.click('#btn-settings'); await pg.click('#settab-model'); await pg.wait_for_timeout(100); await pg.screenshot(path=os.path.join(D,'v3_conns_claude.png'))
        print('PROV claude.ai:', await pg.eval_on_selector_all('#prov-list .prov', 'els=>els.map(e=>e.querySelector("b").textContent+":"+(e.querySelector("input").disabled?"off":"on")+":"+e.querySelector(".prov-st").textContent)'))
        await pg.click('#prov-list [data-prov=openai] [data-act=standalone]'); await pg.wait_for_timeout(500); print('STANDALONE DL:', await pg.evaluate('window.__dl'))
        await pg.click('#set-ov [data-close]')
        print('W', await pg.evaluate('document.documentElement.scrollWidth'))
        await ctx.close()
        # ---------- standalone mode with external AI + TMS
        ctx=await b.new_context(viewport={'width':1360,'height':900}, accept_downloads=True)
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock_ext.js'))
        pg=await ctx.new_page(); await pg.route('**/*', route); hook(pg)
        await pg.goto('http://local.test/qa-pro.html'); await pg.wait_for_timeout(600)
        print('SA status:', await pg.inner_text('.top-right'))
        print('SA run note:', await pg.inner_text('#run-note'))
        await pg.click('#btn-settings'); await pg.click('#settab-model')
        await pg.click('#prov-list [data-prov=innocode] .prov-h')
        await pg.fill('#pu-innocode','http://ai.test/v1'); await pg.fill('#pm-innocode','corp-llm'); await pg.fill('#pk-innocode','secret')
        await pg.click('[data-prov-test=innocode]'); await pg.wait_for_timeout(400); print('CONN TEST:', await pg.inner_text('#prov-test-note'))
        print('GEN AI:', await pg.evaluate("JSON.parse(localStorage.getItem('tca.settings')).genAI"), '| status:', await pg.inner_text('#prov-st-innocode'))
        await pg.click('#set-ov [data-close]')
        await pg.click('#btn-run'); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=30000); await pg.wait_for_timeout(300)
        print('SA tabs:', await pg.inner_text('#tabs'))
        await pg.click('#tab-cases'); await pg.click('[data-act=tms-settings]')
        await pg.select_option('#tm-kind','testit'); await pg.wait_for_timeout(100)
        await pg.fill('#tm-baseUrl','http://tms.test'); await pg.fill('#tm-token','tok'); await pg.fill('#tm-project','proj-uuid')
        print('TMS dirty dot:', await pg.evaluate("!!document.querySelector('#settab-tms .dot-d')"), '| gear:', await pg.evaluate("document.querySelector('#btn-settings').classList.contains('dirty')"))
        await pg.click('[data-tmb=test]'); await pg.wait_for_timeout(300); print('TMS TEST:', await pg.inner_text('#tms-body .case-note'))
        await pg.click('[data-tmb=save]'); await pg.wait_for_timeout(100)
        print('TMS dirty after save:', await pg.evaluate("!!document.querySelector('#settab-tms .dot-d')"))
        await pg.click('#set-ov [data-close]')
        await pg.click('[data-act=tms-upload]'); await pg.wait_for_timeout(1500)
        print('TMS LOG:', await pg.inner_text('#tms-bar .log'))
        ext=await pg.evaluate('window.__ext'); wi=[e for e in ext if 'workItems' in e['u']]
        print('EXT AI calls:', len([e for e in ext if 'ai.test' in e['u']]), 'auth', ext[0].get('auth'), '| workItems:', len(wi))
        print('WI body sample:', json.dumps(wi[0]['body'], ensure_ascii=False)[:500])
        await pg.screenshot(path=os.path.join(D,'v3_standalone_cases.png'), full_page=True)
        async with pg.expect_download() as dl:
            await pg.click('#tab-export'); await pg.click('[data-act=dl-out]')
        d=await dl.value; print('SA DOWNLOAD:', d.suggested_filename)
        await ctx.close()
        print('ERRORS', errs); await b.close()
asyncio.run(main())
