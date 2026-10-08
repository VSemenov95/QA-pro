# Сводки разделов: обрезанный ответ → сжатый повтор; лимит → остановка, отчёт с причиной, «Собрать оставшиеся»
import asyncio, os, json, time, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run27 import dbop, serve, IDX, wait_idle, D
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script="window.__qaTest = true; window.__sampleDelay = 10; window.__synthMode = 'trunc';")
        for f in ('mockgen.js','mock_shared.js'): await ctx.add_init_script(path=os.path.join(D,f))
        await ctx.route('http://kb2.test/**', serve)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://kb2.test/'); await pg.wait_for_timeout(2500)
        await pg.click('[data-mode=help]'); await pg.wait_for_timeout(400)
        await pg.click('[data-act=kb-run]'); await pg.wait_for_timeout(300); await wait_idle(pg)
        print('T1 truncated → compact retry:', await pg.evaluate(IDX), '| first attempts failed:', await pg.evaluate('window.__synthTrunc'), '| report:', await pg.evaluate('__qa.S.kb.synthReport'))
        sp = await pg.evaluate("(window.__prompts || []).filter(p => p.includes('Собери единую сводку')).map(p => p.length)")
        print('T1 synth prompt sizes:', sp)
        await pg.evaluate("window.__synthMode = 'limit'; for (const b of __qa.S.kb.index.blocks) b.sh = '';")
        await pg.click('#help-head [data-v=qa]'); await pg.click('#help-head [data-v=blocks]'); await pg.wait_for_timeout(200)
        await pg.click('[data-act=kb-synth]'); await pg.wait_for_timeout(300); await wait_idle(pg)
        print('T2 rate limit:', await pg.evaluate('__qa.S.kb.synthReport'))
        print('T2 banner:', (await pg.inner_text('#kb-job')).replace('\n', ' | '))
        await pg.screenshot(path=os.path.join(D,'v30_kb_report.png'))
        await pg.evaluate("window.__synthMode = ''")
        await pg.click('#kb-job [data-act=kb-synth]'); await pg.wait_for_timeout(300); await wait_idle(pg)
        print('T3 retry ok:', await pg.evaluate(IDX), '| report:', await pg.evaluate('__qa.S.kb.synthReport'), '| banner:', repr((await pg.inner_text('#kb-job')).strip()[:80]))
        await b.close(); print('ERRORS:', errs or 'none')
asyncio.run(main())
