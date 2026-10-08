import asyncio, os
from playwright.async_api import async_playwright
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'shot17.py')).read().split('async def main')[0])
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':1000}, color_scheme='light')
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock.js'))
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://app.test/'); await pg.wait_for_timeout(1300)
        bg = lambda: pg.evaluate("getComputedStyle(document.body).backgroundColor")
        print('T1 initial:', await pg.evaluate("document.documentElement.dataset.theme || 'system'"), await bg(), await pg.get_attribute('#btn-theme','aria-label'))
        await pg.click('#btn-theme'); await pg.wait_for_timeout(200)
        print('T2 after click:', await pg.evaluate("document.documentElement.dataset.theme"), await bg(), await pg.get_attribute('#btn-theme','aria-label'))
        await pg.reload(); await pg.wait_for_timeout(1300)
        print('T3 after reload:', await pg.evaluate("document.documentElement.dataset.theme"), await bg(), await pg.get_attribute('#btn-theme','aria-label'))
        await pg.click('[data-mode=help]'); await pg.wait_for_timeout(400)
        await pg.screenshot(path=os.path.join(D,'v19_dark_help.png'))
        await pg.click('#btn-theme'); await pg.wait_for_timeout(200)
        print('T4 back:', await pg.evaluate("document.documentElement.dataset.theme"), await bg())
        print('step-n:', await pg.eval_on_selector_all('.rail .step-n', 'els => els.filter(e => e.offsetParent).map(e => e.textContent)'))
        print('ERRORS', errs); await b.close()
asyncio.run(main())
