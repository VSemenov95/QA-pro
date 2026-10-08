# Прогресс базы знаний: «документы N из M» при разборе, «сводки N из M · документов сведено X из Y» при сводках
import asyncio, os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run27 import dbop, serve, IDX, wait_idle, D
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script="window.__qaTest = true; window.__sampleDelay = 700;")
        for f in ('mockgen.js','mock_shared.js'): await ctx.add_init_script(path=os.path.join(D,f))
        await ctx.route('http://kb2.test/**', serve)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://kb2.test/'); await pg.wait_for_timeout(2500)
        await pg.click('[data-mode=help]'); await pg.wait_for_timeout(300)
        await pg.evaluate('__qa.S.settings.kbAuto = false')
        await pg.set_input_files('#file-input', [os.path.join(D,'kb_extra.md'), os.path.join(D,'kb_созвон-call.md')]); await pg.wait_for_timeout(1500)
        await pg.click('[data-act=kb-run]')
        seen, notes, shot = [], [], False
        for _ in range(200):
            t = (await pg.inner_text('#kb-job')).split('\n')[0]
            n = await pg.inner_text('#docs-note')
            if t and (not seen or seen[-1] != t): seen.append(t)
            m = re.search(r'(Разбираю[^.]*|Собираю[^.]*)', n)
            if m and (not notes or notes[-1] != m.group(1)): notes.append(m.group(1))
            if not shot and 'Собираю сводки' in t:
                await pg.screenshot(path=os.path.join(D, 'v31_kb_progress.png')); shot = True
            if not await pg.evaluate('__qa.S.kb.job.busy'): break
            await pg.wait_for_timeout(150)
        print('P1 banner progress:'); [print('   ', x[:200]) for x in seen]
        print('P2 docs panel note:'); [print('   ', x[:200]) for x in notes]
        await wait_idle(pg)
        print('P3 done:', await pg.evaluate(IDX))
        await b.close(); print('ERRORS:', errs or 'none')
asyncio.run(main())
