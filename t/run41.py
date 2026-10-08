# «Перегенерировать по правилам» под «Сгенерировать»: видна только для черновика с кейсами, пересоздаёт кейсы черновика.
import asyncio, os
from playwright.async_api import async_playwright
from run27 import dbop, serve, D
async def wait_idle(pg, t=90000):
    await pg.wait_for_timeout(500)
    await pg.wait_for_function("() => !__qa.S.running", timeout=t); await pg.wait_for_timeout(600)
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
        st = "() => ({ running: __qa.S.running, stage: __qa.S.run && __qa.S.run.stage, cases: __qa.S.run ? __qa.S.run.cases.length : -1, id: __qa.S.run && __qa.S.run.id })"
        print('R0 before any run, regen visible:', await pg.evaluate("!document.querySelector('#btn-regen').hidden"))
        await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(300)
        await pg.set_input_files('#file-input', '/tmp/claude-0/-home-claude/7234b2d8-b9b5-5dab-b74e-1b755a5e008b/scratchpad/spec.txt'); await pg.wait_for_timeout(1500)
        await pg.click('#btn-run'); await wait_idle(pg)
        s1 = await pg.evaluate(st); print('R1 after run:', s1)
        print('R2 regen visible/enabled:', await pg.evaluate("[!document.querySelector('#btn-regen').hidden, !document.querySelector('#btn-regen').disabled, document.querySelector('#btn-regen').textContent]"))
        u1 = await pg.evaluate('__qa.S.run.cases.map(c => c.uid)')
        await pg.click('#btn-regen'); await pg.wait_for_timeout(300)
        print('R3 armed label:', await pg.inner_text('#btn-regen'))
        await pg.click('#btn-regen'); await pg.wait_for_timeout(400)
        print('R4 running right after confirm:', await pg.evaluate("__qa.S.running"))
        await wait_idle(pg)
        s2 = await pg.evaluate(st); print('R5 after regen:', s2, '| same run:', s1['id'] == s2['id'], '| cases ok:', s2['cases'] > 0)
        u2 = await pg.evaluate('__qa.S.run.cases.map(c => c.uid)')
        print('R5b cases replaced (uids differ):', u1 != u2, '| counts', len(u1), len(u2), '| draft tab visible:', await pg.evaluate("document.querySelector('[role=tab][aria-selected=true]')?.id"))
        print('R6 status note:', await pg.inner_text('#run-note'))
        print('ERRORS:', errs or 'none')
        await b.close()
asyncio.run(main())
