# Обрезанный ответ при генерации кейсов: пачка делится пополам, пока не уместится; повтор дописывает только недостающее
import asyncio, os, sys, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run27 import dbop, serve, wait_idle, D, STORE
from playwright.async_api import async_playwright
CASES="() => __qa.S.run.cases.map(c => c.testCase.title)"
async def finish(pg): await pg.wait_for_function('() => !__qa.S.running && __qa.S.run && __qa.S.run.status !== "running"', timeout=90000)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script="window.__qaTest = true; window.__sampleDelay = 10; window.__genMax = 1;")
        for f in ('mockgen.js','mock_shared.js'): await ctx.add_init_script(path=os.path.join(D,f))
        await ctx.route('http://kb2.test/**', serve)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://kb2.test/'); await pg.wait_for_timeout(2500)
        await pg.evaluate('__qa.S.settings.kbAuto = false; __qa.S.settings.outputs.checklist = false;')
        await pg.click('#btn-run'); await finish(pg)
        plan=await pg.evaluate("__qa.S.run.plan.map(p => [p.id, p.type, p.checks.length])")
        cases=await pg.evaluate(CASES)
        print('G1 plan:', plan, '| checks total:', sum(x[2] for x in plan), '| cases:', len(cases), '| unique:', len(set(cases)), '| failed:', await pg.evaluate('__qa.S.run.failed.length'), '| status:', await pg.evaluate('__qa.S.run.status'))
        print('G1 request sizes (checks per request):', await pg.evaluate('window.__genLog'))
        log=(await pg.click('#tab-agent'), await pg.inner_text('.timeline'))[1]
        print('G1 log:', [l for l in log.split('\n') if 'не уместился' in l or '(часть' in l][:4])
        # одна проверка обрывается всегда → запуск частичный; повтор дописывает только её
        await pg.click('#btn-newses'); await pg.wait_for_timeout(300)
        await pg.evaluate("() => { for (const d of __qa.S.docs) __qa.S.runDocs.add(d.id); window.__genMax = 1; window.__genFail = '429 на четвёртый'; window.__genLog = []; }")
        await pg.click('[data-mode=help]'); await pg.wait_for_timeout(150); await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(300)
        await pg.click('#btn-run'); await finish(pg)
        c1=await pg.evaluate(CASES)
        print('G2 partial:', await pg.evaluate('__qa.S.run.plan.map(p => p.checks)'), await pg.evaluate('window.__genLog'), await pg.evaluate('__qa.S.run.status'), '| cases:', len(c1), '| failed:', await pg.evaluate('__qa.S.run.failed.map(f => f.error)'), '| doneChecks:', await pg.evaluate('(__qa.S.run.doneChecks || []).length'))
        print('G3 pending parts left for resume:', await pg.evaluate("__qa.S.run.plan.filter(p => !(__qa.S.run.doneKeys||[]).some(k => k.startsWith(p.id + '#'))).map(p => p.id)"))
        await b.close(); print('ERRORS:', errs or 'none')
asyncio.run(main())
