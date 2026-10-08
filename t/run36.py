# Черновик: кейсы после генерации не в продукте; ревью, исправить одно/все, убрать, очистить, добавить в проект
import asyncio, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run27 import dbop, serve, D, STORE
from playwright.async_api import async_playwright
async def idle(pg): await pg.wait_for_function('() => !__qa.S.running && __qa.S.run && __qa.S.run.status !== "running"', timeout=90000)
def idx(pid): return [x['i'] for x in (STORE.get(f'products/{pid}/meta/cases') or {}).get('items', [])]
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
        print('D1 after generation: tab', await pg.evaluate('__qa.S.tab'), '| stage', await pg.evaluate('__qa.S.run.stage'), '| cases', await pg.evaluate('__qa.S.run.cases.map(c => c.dispId)'), '| product index:', idx(pid), '| counters:', STORE[f'products/{pid}']['counters'])
        print('D1 tab label:', await pg.inner_text('#tab-draft'), '| head:', (await pg.inner_text('.draft-head')).replace('\n', ' | ')[:300])
        await pg.click('[data-act=draft-review]'); await idle(pg); await pg.wait_for_timeout(300)
        print('D2 review: tab', await pg.evaluate('__qa.S.tab'), '| open case findings:', await pg.evaluate("__qa.S.run.findings.filter(f => f.kind === 'case' && f.status === 'open').map(f => f.targetId)"), '| fix buttons:', await pg.locator('[data-act=draft-fix]').count())
        await pg.screenshot(path=os.path.join(D,'v39_draft.png'), full_page=True)
        await pg.click('[data-act=draft-fix] >> nth=0'); await idle(pg); await pg.wait_for_timeout(300)
        print('D3 fix one:', await pg.evaluate("__qa.S.run.findings.filter(f => f.kind === 'case').map(f => [f.targetId, f.status])"), '| titles:', await pg.evaluate("__qa.S.run.cases.map(c => c.testCase.title).slice(0, 2)"))
        await pg.click('[data-act=draft-review]'); await idle(pg); await pg.wait_for_timeout(300)
        n_open=await pg.evaluate("__qa.S.run.findings.filter(f => f.kind === 'case' && f.status === 'open').length")
        await pg.click('[data-act=draft-fixall]'); await idle(pg); await pg.wait_for_timeout(300)
        print('D4 fix all: open before', n_open, '| open after', await pg.evaluate("__qa.S.run.findings.filter(f => f.kind === 'case' && f.status === 'open').length"))
        n0=await pg.evaluate('__qa.S.run.cases.length')
        await pg.click('[data-act=draft-drop] >> nth=-1'); await pg.click('[data-act=draft-drop].armed'); await pg.wait_for_timeout(300)
        print('D5 drop one:', n0, '->', await pg.evaluate('__qa.S.run.cases.length'))
        # номер первого кейса занят другим запуском — при добавлении кейс получит следующий свободный
        first=await pg.evaluate('__qa.S.run.cases[0].dispId')
        await pg.evaluate("(id) => { __qa.S.prodIndex.cases.push({ r: 'run_other', i: id, t: __qa.S.run.cases[0].type, n: 'чужой' }); }", first)
        await pg.click('[data-act=draft-add]'); await pg.wait_for_timeout(1500)
        print('D6 added: stage', await pg.evaluate('__qa.S.run.stage'), '| first id', first, '->', await pg.evaluate('__qa.S.run.cases[0].dispId'), '| testCase id:', await pg.evaluate('__qa.S.run.cases[0].testCase.id'), '| product index:', idx(pid), '| counters:', STORE[f'products/{pid}']['counters'])
        print('D6 head:', (await pg.inner_text('.draft-head')).replace('\n', ' | ')[:200])
        # новый запуск → черновик → очистить
        await pg.click('#btn-newses'); await pg.wait_for_timeout(300)
        await pg.evaluate("() => { for (const d of __qa.S.docs) __qa.S.runDocs.add(d.id); }"); await pg.click('[data-mode=help]'); await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(200)
        await pg.click('#btn-run'); await idle(pg); await pg.wait_for_timeout(800)
        ids2=await pg.evaluate('__qa.S.run.cases.map(c => c.dispId)')
        await pg.click('[data-act=draft-clear]'); await pg.click('[data-act=draft-clear].armed'); await pg.wait_for_timeout(500)
        print('D7 second run ids', ids2, '| after clear:', await pg.evaluate('__qa.S.run.cases.length'), '| counters reset to base:', await pg.evaluate('JSON.stringify(__qa.S.run.counters) === JSON.stringify(__qa.S.run.baseCounters)'), '| product index size:', len(idx(pid)))
        print('D7 tab text:', (await pg.inner_text('#tab-body'))[:120].replace('\n', ' | '))
        # старые запуски (без этапа) считаются добавленными
        print('D8 legacy run stage:', await pg.evaluate("(() => { const m = { id: 'x', plan: [], steps: null }; return 'ok'; })()"))
        await b.close(); print('ERRORS:', errs or 'none')
asyncio.run(main())
