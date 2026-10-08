# Флажки у тест-кейсов: выбрать, выбрать все, удалить выбранные — в «Черновике» и в «Тест-кейсах» (в проекте)
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run27 import dbop, serve, D, STORE
from playwright.async_api import async_playwright
async def idle(pg): await pg.wait_for_function('() => !__qa.S.running && __qa.S.run && __qa.S.run.status !== "running"', timeout=90000)
def idx(pid): return [x['i'] for x in (STORE.get(f'products/{pid}/meta/cases') or {}).get('items', [])]
IDS="__qa.S.run.cases.map(c => c.dispId)"
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script="window.__qaTest = true; window.__sampleDelay = 10;")
        for f in ('mockgen.js','mock_shared.js'): await ctx.add_init_script(path=os.path.join(D,f))
        await ctx.route('http://kb2.test/**', serve)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://kb2.test/'); await pg.wait_for_timeout(2500)
        await pg.evaluate("__qa.S.settings.outputs.checklist = false")
        pid=await pg.evaluate('__qa.S.productId')
        await pg.click('#btn-run'); await idle(pg); await pg.wait_for_timeout(800)
        print('S1 draft:', await pg.evaluate(IDS), '| checkboxes:', await pg.locator('.draft-case .case-sel').count(), '| bar:', await pg.inner_text('.sel-bar'))
        await pg.check('.draft-case .case-sel >> nth=1'); await pg.wait_for_timeout(150)
        print('S2 one selected:', (await pg.inner_text('.sel-bar')).replace('\n', ' | '))
        await pg.click('[data-act=sel-del]'); await pg.click('[data-act=sel-del].armed'); await pg.wait_for_timeout(300)
        print('S3 draft after delete:', await pg.evaluate(IDS))
        await pg.click('[data-act=draft-add]'); await pg.wait_for_timeout(1200)
        print('S4 product index:', idx(pid))
        # «Тест-кейсы»: фильтр API, выбрать все отфильтрованные, удалить
        await pg.click('#tab-cases'); await pg.wait_for_timeout(300)
        print('S5 cases tab checkboxes:', await pg.locator('#case-list .case-sel').count(), '| bar:', await pg.inner_text('#case-selbar'))
        await pg.click('[data-act=ftype][data-t=api]'); await pg.wait_for_timeout(200)
        await pg.check('#case-selbar .sel-all-cb'); await pg.wait_for_timeout(150)
        print('S6 select all API:', (await pg.inner_text('#case-selbar')).replace('\n', ' | '), '| expanded cases:', await pg.locator('.case-b').count())
        await pg.click('#case-selbar [data-act=sel-del]'); await pg.click('#case-selbar [data-act=sel-del].armed'); await pg.wait_for_timeout(1500)
        print('S7 after delete:', await pg.evaluate(IDS), '| product index:', idx(pid))
        # флажок не разворачивает кейс; «Снять выбор»
        await pg.click('[data-act=ftype][data-t=all]'); await pg.wait_for_timeout(200)
        await pg.click('#case-list .case-sel >> nth=0'); await pg.wait_for_timeout(150)
        print('S8 checkbox click: expanded', await pg.locator('.case-b').count(), '| selected', await pg.evaluate('__qa.S.caseSel.size'))
        await pg.click('#case-selbar [data-act=sel-none]'); await pg.wait_for_timeout(150)
        print('S9 none:', await pg.evaluate('__qa.S.caseSel.size'), '|', await pg.inner_text('#case-selbar'))
        await pg.screenshot(path=os.path.join(D,'v40_select.png'))
        await b.close(); print('ERRORS:', errs or 'none')
asyncio.run(main())
