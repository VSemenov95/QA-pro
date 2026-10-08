import asyncio, os, json
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
standalone=open(os.path.join(ROOT,'qa-pro.html'),encoding='utf-8').read()
html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
skel='<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>[hidden]{display:none!important}body{margin:0}</style></head><body>'+html+'</body></html>'
async def route(r):
    u=r.request.url
    if u.startswith('http://local.test/'): return await r.fulfill(body=standalone, content_type='text/html; charset=utf-8')
    if u.startswith('http://app.test/'): return await r.fulfill(body=skel, content_type='text/html; charset=utf-8')
    await r.abort()
SETUP="""() => { localStorage.setItem('qapro.conns', JSON.stringify([{id:'aiX', kind:'openai', name:'Корп. LLM', baseUrl:'http://ai.test/v1', model:'m', apiKey:'k', auth:'Bearer', headers:'', tools:false}])); localStorage.setItem('tca.settings', JSON.stringify({genAI:'conn:aiX'})); }"""
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        def hook(pg, tag):
            pg.on('pageerror', lambda e: errs.append(tag+' PAGEERR '+str(e)))
            pg.on('console', lambda m: errs.append(tag+' CONSOLE '+m.text) if m.type=='error' and 'net::' not in m.text and 'Failed to load' not in m.text else None)
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock_ext.js'))
        await ctx.add_init_script(script="window.__delay = 4000;")
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); hook(pg,'A')
        await pg.goto('http://local.test/'); await pg.evaluate(SETUP); await pg.reload(); await pg.wait_for_timeout(800)
        # add a custom text doc so session must persist docs
        open(os.path.join(D,'extra.txt'),'w').write('ТЗ: дополнительный документ про лимиты. Не более 3 запросов за 15 минут.')
        await pg.set_input_files('#file-input', os.path.join(D,'extra.txt')); await pg.wait_for_timeout(500)
        await pg.click('#btn-run')
        # wait until at least 1 case generated, then close
        await pg.wait_for_function("() => document.querySelector('#tab-cases .cnt') && +document.querySelector('#tab-cases .cnt').textContent >= 1", timeout=40000)
        await pg.wait_for_timeout(2800)  # allow checkpoint save
        n_before = await pg.evaluate("+document.querySelector('#tab-cases .cnt').textContent")
        calls_before = len(await pg.evaluate('window.__ext'))
        print('BEFORE CLOSE: cases', n_before, 'ai calls', calls_before)
        await pg.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide', {persisted:false}))"); await pg.wait_for_timeout(400)
        await pg.close()
        # second page: follow-mode check would require running tab; here the run is interrupted
        pg2=await ctx.new_page(); hook(pg2,'B')
        await pg2.goto('http://local.test/'); await pg2.wait_for_timeout(1500)
        print('DOCS RESTORED:', (await pg2.inner_text('#doc-list')).replace('\n',' | '))
        print('BANNER:', (await pg2.inner_text('#tab-body .banner'))[:260].replace('\n',' '))
        await pg2.screenshot(path=os.path.join(D,'v4_interrupted.png'), full_page=True)
        # auto resume countdown 5s → wait completion
        await pg2.wait_for_selector('#btn-stop:not([hidden])', timeout=10000)
        print('RESUMED: running')
        await pg2.wait_for_selector('#btn-run:not([hidden])', timeout=60000); await pg2.wait_for_timeout(500)
        cases = await pg2.evaluate("+document.querySelector('#tab-cases .cnt').textContent")
        ext = await pg2.evaluate('window.__ext')
        print('AFTER RESUME: cases', cases, '| ai calls in new page', len(ext))
        ids = await pg2.evaluate("JSON.parse(localStorage.getItem(Object.keys(localStorage).find(k=>k.includes('/parts/p0')))).cases.map(c=>c.dispId+':'+c.planItem)")
        print('CASE IDS:', ids)
        print('AGENT:', (await pg2.inner_text('#tab-body'))[:400].replace('\n',' | '))
        await pg2.screenshot(path=os.path.join(D,'v4_resumed.png'), full_page=True)
        # follow mode: start a new run in pg2, open pg3 while running
        await pg2.click('#btn-run'); await pg2.wait_for_timeout(1500)
        pg3=await ctx.new_page(); hook(pg3,'C')
        await pg3.goto('http://local.test/'); await pg3.wait_for_timeout(2000)
        print('FOLLOW BANNER:', (await pg3.inner_text('#tab-body .banner'))[:160].replace('\n',' '))
        print('FOLLOW RUN NOTE:', await pg3.inner_text('#run-note'))
        await pg2.wait_for_selector('#btn-run:not([hidden])', timeout=60000)
        await pg3.wait_for_timeout(1000)
        dbg = await pg3.evaluate("(() => { const ks = Object.keys(localStorage).filter(k => k.startsWith('qapro.db:data/users/local/')); const ses = JSON.parse(localStorage.getItem('qapro.db:data/users/local/session')); const runs = ks.filter(k => /run_[a-z0-9]+$/.test(k)).map(k => { const m = JSON.parse(localStorage.getItem(k)); return m.id + ':' + m.status; }); return {ses: {runId: ses.runId, runningBy: ses.runningBy, hb: ses.heartbeat}, runs}; })()")
        print('DBG after finish:', dbg)
        await pg3.wait_for_timeout(8000)
        print('FOLLOW AFTER FINISH tabs:', (await pg3.inner_text('#tabs')).replace('\n',' '))
        print('BODY:', (await pg3.inner_text('#tab-body'))[:300].replace('\n',' | '))
        print('FOLLOW BANNER2:', (await pg3.inner_text('#tab-body .banner'))[:120].replace('\n',' '))
        # new session button
        await pg3.click('#btn-newses'); await pg3.click('#btn-newses'); await pg3.wait_for_timeout(500)
        print('AFTER NEW SESSION docs:', (await pg3.inner_text('#doc-list')).replace('\n',' | ')[:120], '| tabs', (await pg3.inner_text('#tabs')).replace('\n',' '))
        await ctx.close()
        # claude mode smoke
        ctx=await b.new_context(viewport={'width':400,'height':860}, color_scheme='dark')
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock.js'))
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); hook(pg,'CL')
        await pg.goto('http://app.test/'); await pg.wait_for_timeout(800)
        await pg.click('#btn-run'); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=30000)
        print('CLAUDE MODE cases:', await pg.inner_text('#tab-cases .cnt'), 'W', await pg.evaluate('document.documentElement.scrollWidth'))
        await pg.screenshot(path=os.path.join(D,'v4_mobile.png'), full_page=True)
        await ctx.close()
        print('ERRORS', errs); await b.close()
asyncio.run(main())
