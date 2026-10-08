# Перегенерация по правилам не трогает базу знаний и паспорт; сокращение получает текст документации.
import asyncio, os, json
from playwright.async_api import async_playwright
from run27 import dbop, serve, D
SP = '/tmp/claude-0/-home-claude/7234b2d8-b9b5-5dab-b74e-1b755a5e008b/scratchpad/spec.txt'
async def wait_idle(pg):
    await pg.wait_for_timeout(500)
    await pg.wait_for_function("() => !__qa.S.running", timeout=90000); await pg.wait_for_timeout(600)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); errs = []
        ctx = await b.new_context(viewport={'width': 1360, 'height': 900})
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script='window.__qaTest = true;')
        for f in ('mockgen.js', 'mock_shared.js'): await ctx.add_init_script(path=os.path.join(D, f))
        await ctx.route('http://localhost/**', serve)
        pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost/'); await pg.wait_for_timeout(2000)
        await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(300)
        await pg.set_input_files('#file-input', SP); await pg.wait_for_timeout(1500)
        await pg.click('#btn-run'); await wait_idle(pg)
        # в паспорт/базу знаний попадают только при наличии; проверим, что регенерация их не запрашивает
        await pg.evaluate("window.__prompts = []")
        await pg.click('#btn-regen'); await pg.wait_for_timeout(200); await pg.click('#btn-regen')
        await wait_idle(pg)
        ps = await pg.evaluate("window.__prompts || []")
        kb = [x for x in ps if 'База знаний продукта' in x or 'Знания о продукте' in x]
        print('G1 regen prompts:', len(ps), '| with KB/passport:', len(kb), '| noKb flag:', await pg.evaluate('__qa.S.run.noKb'))
        await pg.evaluate("window.__prompts = []")
        await pg.click('#btn-reduce'); await pg.wait_for_timeout(200)
        n = await pg.evaluate('__qa.S.run.cases.length')
        await pg.fill('#reduce-n', str(max(1, n - 1))); await pg.click('#reduce-go')
        await wait_idle(pg)
        ps = await pg.evaluate("window.__prompts || []")
        red = [x for x in ps if 'Сократи набор тест-кейсов' in x]
        print('G2 reduce prompt found:', len(red), '| has document text:', bool(red) and ('Документ «spec.txt»' in red[0]) and ('Регистрация' in red[0]))
        print('ERRORS:', errs or 'none')
        await b.close()
asyncio.run(main())
