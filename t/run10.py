import asyncio, os
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
standalone=open(os.path.join(ROOT,'qa-pro.html'),encoding='utf-8').read()
async def route(r):
    u=r.request.url
    if u.startswith('http://local.test/'): return await r.fulfill(body=standalone, content_type='text/html; charset=utf-8')
    if 'xlsx.full.min.js' in u:
        for root,_,fs in os.walk(os.path.join(ROOT,'libs')):
            if 'xlsx.full.min.js' in fs: return await r.fulfill(path=os.path.join(root,'xlsx.full.min.js'), content_type='application/javascript')
    await r.abort()
SETUP="""() => { localStorage.clear(); localStorage.setItem('qapro.conns', JSON.stringify([{id:'aiX', kind:'openai', name:'LLM', baseUrl:'http://ai.test/v1', model:'m', apiKey:'k', auth:'Bearer', headers:'', tools:false}])); localStorage.setItem('tca.settings', JSON.stringify({genAI:'conn:aiX', mode:'update', outputs:{cases:true, checklist:false}})); }"""
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context()
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock_ext.js'))
        await ctx.add_init_script(script="window.__delay = 3000;")
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://local.test/'); await pg.evaluate(SETUP); await pg.reload(); await pg.wait_for_timeout(1000)
        await pg.set_input_files('#upd-input', os.path.join(D,'tests.xlsx')); await pg.wait_for_timeout(1200)
        await pg.click('#btn-run')
        await pg.wait_for_function("() => /Итого: без изменений/.test(document.querySelector('.timeline')?.innerText || '')", timeout=60000)
        await pg.wait_for_timeout(2800)
        calls1 = await pg.evaluate("window.__ext.length")
        await pg.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide', {persisted:false}))"); await pg.wait_for_timeout(300); await pg.close()
        pg2=await ctx.new_page(); pg2.on('pageerror', lambda e: errs.append(str(e)))
        await pg2.goto('http://local.test/'); await pg2.wait_for_timeout(1500)
        print('BANNER:', (await pg2.inner_text('#tab-body .banner'))[:140].replace('\n',' '))
        await pg2.wait_for_selector('#btn-stop:not([hidden])', timeout=12000)
        await pg2.wait_for_selector('#btn-run:not([hidden])', timeout=90000); await pg2.wait_for_timeout(800)
        prompts = await pg2.evaluate("(window.__prompts||[]).map(p => p.includes('Сопоставь каждый существующий') ? 'MAP' : p.includes('Перепиши существующие') ? 'ACT' : p.includes('Составь план') ? 'PLAN' : p.includes('паспорт продукта') ? 'PASS' : p.includes('Напиши тест-кейсы') ? 'GEN' : 'OTHER')")
        print('CALLS before close:', calls1, '| after resume prompts:', prompts)
        await pg2.click('#tab-cases'); await pg2.wait_for_timeout(300)
        print('CASES:', await pg2.eval_on_selector_all('.case-h', 'els => els.map(e => e.querySelector(".case-id").textContent + " " + (e.querySelector(".chip[class*=ust-]")||{}).textContent)'))
        print('ERRORS', errs); await b.close()
asyncio.run(main())
