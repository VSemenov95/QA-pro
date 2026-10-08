# Покрытие всех требований: проверка полноты анализа (пропущенные требования и критерии) и сверка покрытия критериев кейсами
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run27 import dbop, serve, D
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script="window.__qaTest = true; window.__sampleDelay = 10; window.__covMock = true;")
        for f in ('mockgen.js','mock_shared.js'): await ctx.add_init_script(path=os.path.join(D,f))
        await ctx.route('http://kb2.test/**', serve)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://kb2.test/'); await pg.wait_for_timeout(2500)
        await pg.evaluate("__qa.S.settings.outputs.checklist = false")
        await pg.click('#btn-run'); await pg.wait_for_function('() => !__qa.S.running && __qa.S.run && __qa.S.run.status !== "running"', timeout=90000)
        print('V1 requirements:', await pg.evaluate("__qa.S.run.requirements.map(r => [r.id, r.title, r.criteria.length])"))
        print('V1 completeness calls:', await pg.evaluate('window.__moreCalls'), '| audit calls:', await pg.evaluate('window.__auditCalls'))
        print('V2 plan C-items:', await pg.evaluate("__qa.S.run.plan.filter(p => p.id.startsWith('C-')).map(p => [p.id, p.type, p.requirementIds, p.checks])"))
        print('V3 uncovered:', await pg.evaluate("__qa.S.run.requirements.filter(r => r.inScope && !__qa.S.run.cases.some(c => c.requirementIds.includes(r.id))).map(r => r.id)"), '| cases:', await pg.evaluate('__qa.S.run.cases.length'), '| auditDone:', await pg.evaluate('__qa.S.run.auditDone'))
        await pg.click('#tab-agent'); await pg.wait_for_timeout(200)
        tl=await pg.inner_text('.timeline')
        print('V4 log:', [l for l in tl.split('\n') if 'полнот' in l or 'Сверк' in l or 'критери' in l][:6])
        await b.close(); print('ERRORS:', errs or 'none')
asyncio.run(main())
