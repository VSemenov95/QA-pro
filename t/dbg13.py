import asyncio, os, json
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
skel='<!doctype html><html><head><meta charset=utf8><style>[hidden]{display:none!important}</style></head><body>'+html+'</body></html>'
async def route(r):
    if r.request.url.startswith('http://app.test/'): return await r.fulfill(body=skel, content_type='text/html; charset=utf-8')
    await r.abort()
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context()
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock.js'))
        await ctx.route('**/*', route)
        pg=await ctx.new_page()
        await pg.goto('http://app.test/'); await pg.wait_for_timeout(1500)
        await pg.click('#btn-run'); await pg.wait_for_timeout(400); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=60000); await pg.wait_for_timeout(800)
        await pg.click('[data-mode=help]'); await pg.wait_for_timeout(300)
        await pg.evaluate('window.__prompts = []')
        await pg.fill('#help-input', 'Какие ограничения и лимиты описаны?'); await pg.click('#help-send'); await pg.wait_for_timeout(1500)
        r = await pg.evaluate("(async () => { const p = window.__prompts.find(x => x.includes('справочная')); return { res: await window.__mockJSON(p), tail: p.slice(-300) }; })()")
        print(json.dumps(r, ensure_ascii=False)[:900])
        await b.close()
asyncio.run(main())
