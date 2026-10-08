# Объём: без исследовательских тестов и ручной работы с БД — правило в запросах и фильтр плана и чек-листа
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run27 import dbop, serve, D
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script="window.__qaTest = true; window.__sampleDelay = 10; window.__scopeMock = true;")
        for f in ('mockgen.js','mock_shared.js'): await ctx.add_init_script(path=os.path.join(D,f))
        await ctx.route('http://kb2.test/**', serve)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://kb2.test/'); await pg.wait_for_timeout(2500)
        await pg.evaluate("__qa.S.settings.outputs.checklist = true; window.__prompts = []")
        await pg.click('#btn-run'); await pg.wait_for_function('() => !__qa.S.running && __qa.S.run && __qa.S.run.status !== "running"', timeout=60000)
        pr=await pg.evaluate('window.__prompts')
        kinds={'анализ':'Выдели из проектной','чек-лист':'Составь чек-лист','план':'Составь план','кейсы':'Напиши тест-кейсы','ревью':'строгий ревьюер'}
        print('S1 rule in prompts:', {k: sum(1 for x in pr if v in x and 'ручных действий в БД' in x or (v in x and 'ручной работы с БД' in x)) for k, v in kinds.items()}, '| totals:', {k: sum(1 for x in pr if v in x) for k, v in kinds.items()})
        print('S2 plan checks:', await pg.evaluate("__qa.S.run.plan.map(p => [p.title, p.checks])"))
        print('S3 checklist:', await pg.evaluate("(__qa.S.run.checklist?.groups || []).flatMap(g => g.items.map(i => i.check))"))
        tl=(await pg.click('#tab-agent'), await pg.inner_text('.timeline'))[1]
        print('S4 log:', [l for l in tl.split('\n') if 'вне объёма' in l])
        await b.close(); print('ERRORS:', errs or 'none')
asyncio.run(main())
