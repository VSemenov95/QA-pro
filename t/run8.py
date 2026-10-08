import asyncio, os
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
standalone=open(os.path.join(ROOT,'qa-pro.html'),encoding='utf-8').read()
async def route(r):
    if r.request.url.startswith('http://local.test/'): return await r.fulfill(body=standalone, content_type='text/html; charset=utf-8')
    await r.abort()
SETUP="""() => { localStorage.setItem('qapro.conns', JSON.stringify([{id:'aiX', kind:'openai', name:'LLM', baseUrl:'http://ai.test/v1', model:'m', apiKey:'k', auth:'Bearer', headers:'', tools:false}])); localStorage.setItem('tca.settings', JSON.stringify({genAI:'conn:aiX'})); }"""
HB="""() => { const k = Object.keys(localStorage).find(k => /\\/runs\\/run_[a-z0-9]+$/.test(k)); if (!k) return null; const m = JSON.parse(localStorage.getItem(k)); return { status: m.status, hbAge: m.hb ? Date.now() - m.hb : null, hbTab: !!m.hbTab }; }"""
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context()
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock_ext.js'))
        await ctx.add_init_script(script="window.__delay = 5000;")
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://local.test/'); await pg.evaluate(SETUP); await pg.reload(); await pg.wait_for_timeout(1000)
        await pg.click('#btn-run'); await pg.wait_for_timeout(12000)
        print('DURING RUN:', await pg.evaluate(HB))
        print('SELECT disabled while running:', await pg.eval_on_selector('#prod-select', 'e => e.disabled'))
        await pg.wait_for_selector('#btn-run:not([hidden])', timeout=90000); await pg.wait_for_timeout(1500)
        print('AFTER RUN:', await pg.evaluate(HB))
        print('ERRORS', errs); await b.close()
asyncio.run(main())
