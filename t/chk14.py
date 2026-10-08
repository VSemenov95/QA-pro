import asyncio, os
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
skel='<!doctype html><html><head><meta charset=utf8><style>[hidden]{display:none!important}</style></head><body>'+html+'</body></html>'
async def route(r):
    if r.request.url.startswith('http://app.test/'): return await r.fulfill(body=skel, content_type='text/html; charset=utf-8')
    await r.abort()
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context()
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock.js'))
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://app.test/'); await pg.wait_for_timeout(1200)
        for m in ['generate','update','help','generate']:
            await pg.click(f'[data-mode={m}]'); await pg.wait_for_timeout(200)
            print(m, 'qa-ctx visible:', await pg.is_visible('#qa-ctx-box'))
        print('ERRORS', errs); await b.close()
asyncio.run(main())
