import asyncio, os, json
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
skel='<!doctype html><html><head><meta charset=utf8><style>[hidden]{display:none!important}</style></head><body>'+html+'</body></html>'
async def route(r):
    u=r.request.url
    if u.startswith('http://app.test/'): return await r.fulfill(body=skel, content_type='text/html; charset=utf-8')
    if 'xlsx.full.min.js' in u:
        for root,_,fs in os.walk(os.path.join(ROOT,'libs')):
            if 'xlsx.full.min.js' in fs: return await r.fulfill(path=os.path.join(root,'xlsx.full.min.js'), content_type='application/javascript')
    await r.abort()
async def idle(pg):
    await pg.wait_for_timeout(400); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=60000); await pg.wait_for_timeout(1200)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock.js'))
        await ctx.add_init_script(script='window.__QA_DEBUG = 1;')
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: errs.append('CONSOLE '+m.text) if m.type=='error' and 'net::' not in m.text else None)
        await pg.goto('http://app.test/'); await pg.wait_for_timeout(1500)
        await pg.click('#btn-run'); await idle(pg)
        await pg.wait_for_timeout(400)
        btn = await pg.inner_text('[data-act=know-learn]')
        print('K1 learn button:', btn)
        await pg.evaluate('window.__prompts = []')
        await pg.click('[data-act=know-learn]'); await pg.wait_for_timeout(1500)
        P = await pg.evaluate("window.__prompts.filter(p => p.includes('паспорт продукта»')).map(p => p.includes('Верни только изменения паспорта') ? 'DELTA' : 'FULL')")
        print('K2 passport prompts:', P)
        md = await pg.inner_text('#prod-info .md')
        print('K2 passport has delta:', 'дельта 1' in md, '| term added:', 'Токен сброса' in md, '| open question removed:', 'Что происходит при 4-м' not in md)
        print('K3 button now:', await pg.inner_text('#prod-info .pp-card .pp-acts'))
        # export local mapping
        await pg.click('#btn-settings'); await pg.click('#settab-export'); await pg.fill('#cfg-export', 'CSV для Test IT: шаг на строку, разделитель ;'); await pg.wait_for_timeout(300)
        print('E0 gear dirty:', await pg.eval_on_selector('#btn-settings', 'e => e.classList.contains("dirty")'))
        await pg.click('#set-ov [data-close]')
        await pg.click('#tab-export'); await pg.wait_for_timeout(300)
        print('E1 hint:', [l for l in (await pg.inner_text('#tab-body')).split('\n') if 'шаблон' in l.lower()][:1])
        await pg.evaluate('window.__prompts = []')
        await pg.click('[data-act=run-export]'); await pg.wait_for_timeout(1500)
        exp_prompts = await pg.evaluate("window.__prompts.map(p => p.includes('спецификацию') ? 'SPEC' : p.includes('Преобразуй тест-кейсы') ? 'ITEMS' : 'OTHER')")
        body = await pg.inner_text('#tab-body')
        print('E2 export prompts:', exp_prompts, '| header ok:', 'ID;Название;Предусловия;Шаг;Ожидаемый результат;Приоритет;Теги' in body, '| prio ru:', 'Высокий' in body, '| local note:', 'без модели' in body)
        print('E2 sample rows:', [l for l in body.split('\n') if l.startswith(('API-001','UI-001',';;;2.'))][:3])
        # edit a case → rebuild without model
        await pg.evaluate('window.__prompts = []')
        await pg.click('#tab-cases'); await pg.click('.case-h >> nth=0'); await pg.click('[data-act=case-suite][data-s=smoke]'); await pg.wait_for_timeout(300)
        await pg.click('#tab-export'); await pg.wait_for_timeout(300)
        if await pg.is_visible('[data-act=run-export]'): await pg.click('[data-act=run-export]'); await pg.wait_for_timeout(800)
        print('E3 rebuild prompts after edit:', await pg.evaluate('window.__prompts.length'))
        # product export
        await pg.wait_for_timeout(300)
        await pg.click('[data-act=prod-export]'); await pg.wait_for_timeout(1500)
        dl = await pg.evaluate('window.__dl'); data = await pg.evaluate('window.__dlData')
        j = json.loads(data)
        print('X1 export:', dl['filename'], '| docs', len(j['docs']), '| runs', len(j['runs']), '| passport', bool(j['product']['passport']), '| index', len(j['index']['cases']))
        path = os.path.join(D, 'prod-export.json'); open(path, 'w', encoding='utf-8').write(data)
        await pg.set_input_files('#prod-import-file', path); await pg.wait_for_timeout(2500)
        print('X2 after import select:', await pg.eval_on_selector('#prod-select', 'e => e.selectedOptions[0].textContent'), '| options:', (await pg.inner_text('#prod-select')).replace('\n',' / '))
        print('X2 product panel:', (await pg.inner_text('#prod-info'))[:260].replace('\n',' | '))
        await pg.click('#tab-history'); await pg.wait_for_timeout(700)
        print('X3 history:', (await pg.inner_text('#tab-body'))[:200].replace('\n',' | '))
        # economy mode: update run uses quick tier for map
        await pg.click('#btn-settings'); await pg.click('#settab-model'); await pg.click('label:has(#economy)'); await pg.wait_for_timeout(100)
        print('Y1 eco hint:', await pg.inner_text('#eco-hint'))
        await pg.click('#set-ov [data-close]')
        await pg.click('[data-mode=update]'); await pg.set_input_files('#upd-input', os.path.join(D,'tests.xlsx')); await pg.wait_for_timeout(1200)
        await pg.evaluate('window.__tiers = []')
        await pg.click('#btn-run'); await idle(pg)
        tiers = await pg.evaluate('window.__tiers.map(t => (t[0].includes("Сопоставь") ? "map" : t[0].includes("Перепиши") ? "act" : t[0].includes("паспорт") ? "know" : t[0].includes("Напиши") ? "gen" : "other") + ":" + t[1])')
        print('Y2 tiers:', tiers)
        print('Y3 stats tokens:', [l for l in (await pg.inner_text('.stats')).split('\n')][-3:])
        print('ERRORS', errs); await b.close()
asyncio.run(main())
