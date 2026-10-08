import asyncio, os, json, re
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
skel='<!doctype html><html><head><meta charset=utf8><style>[hidden]{display:none!important}</style></head><body>'+html+'</body></html>'
async def route(r):
    if r.request.url.startswith('http://app.test/'): return await r.fulfill(body=skel, content_type='text/html; charset=utf-8')
    await r.abort()
CLS="""() => { const kinds = [['Выдели из проектной','analyze'],['Составь чек-лист','checklist'],['Составь план','plan'],['Напиши тест-кейсы','generate'],['паспорт продукта»','knowledge'],['строгий ревьюер','review'],['Сопоставь каждый','map'],['Перепиши существующие','actualize']];
 const out = {}; for (const p of window.__prompts) { const k = (kinds.find(([s]) => p.includes(s)) || [0,'other'])[1]; out[k] = out[k] || {n:0, chars:0, max:0}; out[k].n++; out[k].chars += p.length; out[k].max = Math.max(out[k].max, p.length); }
 const sec = (p, h) => { const i = p.indexOf(h); if (i < 0) return 0; const j = p.indexOf('\\n## ', i + 4); return (j < 0 ? p.length : j) - i; };
 const g = window.__prompts.filter(p => p.includes('Напиши тест-кейсы'));
 const parts = g.length ? { template: sec(g[0], '## Шаблон'), docs: sec(g[0], '## Исходные документы'), know: sec(g[0], '## Знания о продукте'), existing: sec(g[0], '## Уже есть в продукте'), total: g[0].length } : null;
 return { out, genParts: parts }; }"""
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        ctx=await b.new_context()
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock.js'))
        # большой паспорт как после нескольких запусков
        await ctx.add_init_script(script="window.__bigPassport = 1;")
        await ctx.route('**/*', route)
        pg=await ctx.new_page()
        await pg.goto('http://app.test/'); await pg.wait_for_timeout(1500)
        for i in range(2):
            await pg.evaluate('window.__prompts = []')
            await pg.click('#btn-newses'); await pg.wait_for_timeout(200)
            await pg.click('#btn-run'); await pg.wait_for_timeout(500); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=60000); await pg.wait_for_timeout(1500)
            print('RUN', i+1, json.dumps(await pg.evaluate(CLS), ensure_ascii=False))
            await pg.click('#tab-agent'); await pg.wait_for_timeout(200)
            print('   METER:', [l for l in (await pg.inner_text('#tab-body')).split('\n') if 'Расход по шагам' in l or 'кэша' in l or 'Новых сведений' in l or 'знания' in l.lower()][:4])
        await pg.evaluate('window.__prompts = []')
        await pg.click('#btn-review'); await pg.wait_for_timeout(500); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=60000)
        print('REVIEW', json.dumps(await pg.evaluate(CLS), ensure_ascii=False))
        await pg.evaluate('window.__prompts = []')
        await pg.click('#tab-review'); await pg.wait_for_timeout(200)
        await pg.click('[data-act=start-review]'); await pg.wait_for_timeout(500); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=60000)
        print('REVIEW AGAIN', json.dumps(await pg.evaluate(CLS), ensure_ascii=False), [l for l in (await pg.inner_text('#tab-body')).split('\n') if 'Не менялись' in l])
        await b.close()
asyncio.run(main())
