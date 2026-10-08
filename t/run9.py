import asyncio, os, json
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
skel='<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>[hidden]{display:none!important}body{margin:0}</style></head><body>'+html+'</body></html>'
standalone=open(os.path.join(ROOT,'qa-pro.html'),encoding='utf-8').read()
LIBS={'xlsx.full.min.js':os.path.join(ROOT,'libs')}
async def route(r):
    u=r.request.url
    if u.startswith('http://app.test/'): return await r.fulfill(body=skel, content_type='text/html; charset=utf-8')
    if u.startswith('http://local.test/'): return await r.fulfill(body=standalone, content_type='text/html; charset=utf-8')
    if 'xlsx.full.min.js' in u:
        for root,_,fs in os.walk(os.path.join(ROOT,'libs')):
            if 'xlsx.full.min.js' in fs: return await r.fulfill(path=os.path.join(root,'xlsx.full.min.js'), content_type='application/javascript')
    await r.abort()
async def wait_idle(pg, t=60000):
    await pg.wait_for_timeout(300)
    await pg.wait_for_selector('#btn-run:not([hidden])', timeout=t)
    await pg.wait_for_timeout(1200)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        def hook(pg, tag):
            pg.on('pageerror', lambda e: errs.append(tag+' PAGEERR '+str(e)))
            pg.on('console', lambda m: errs.append(tag+' CONSOLE '+m.text) if m.type=='error' and 'net::' not in m.text and 'Failed to load' not in m.text else None)
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock.js'))
        await ctx.add_init_script(script='window.__QA_DEBUG = 1;')
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); hook(pg,'A')
        await pg.goto('http://app.test/'); await pg.wait_for_timeout(1500)
        await pg.click('[data-mode=update]'); await pg.wait_for_timeout(200)
        print('A1 upd panel:', await pg.is_visible('#upd-panel'), '| steps:', await pg.eval_on_selector_all('.rail .step-n', 'els => els.filter(e => e.offsetParent).map(e => e.textContent).join(",")'))
        print('A1 run btn:', await pg.inner_text('#btn-run'), '| disabled', await pg.eval_on_selector('#btn-run','e=>e.disabled'), '| note:', await pg.inner_text('#run-note'))
        print('A1 intro:', [l for l in (await pg.inner_text('#tab-body')).split('\n') if 'Сверка' in l or 'Актуализация' in l][:3])
        await pg.set_input_files('#upd-input', os.path.join(D,'bad.json')); await pg.wait_for_timeout(500)
        print('A2 bad json:', (await pg.inner_text('#upd-info')).replace('\n',' | '))
        await pg.set_input_files('#upd-input', os.path.join(D,'tests.xlsx')); await pg.wait_for_timeout(1500)
        print('A3 xlsx:', (await pg.inner_text('#upd-info')).replace('\n',' | '))
        await pg.click('[data-upd-act=preview]'); await pg.wait_for_timeout(200)
        print('A3 preview:', (await pg.inner_text('.upd-preview')).replace('\n',' | '))
        print('A3 note:', await pg.inner_text('#run-note'), '| btn', await pg.inner_text('#btn-run'))
        await pg.click('#btn-run'); await wait_idle(pg)
        tl=(await pg.click('#tab-agent'), await pg.inner_text('.timeline'))[1]
        print('A4 timeline:', [l for l in tl.split('\n') if l.startswith(('Сверка','Актуализация','План','Новые','Итого','Не покрыты','Все ')) or 'Файл с кейсами' in l][:14])
        print('A4 stats:', (await pg.inner_text('.stats')).replace('\n',' | '))
        await pg.click('#tab-cases'); await pg.wait_for_timeout(300)
        print('A5 toolbar:', (await pg.inner_text('.toolbar')).replace('\n',' '))
        heads=await pg.eval_on_selector_all('.case-h', 'els => els.map(e => e.querySelector(".case-id").textContent + " " + (e.querySelector(".chip[class*=ust-]")||{}).textContent)')
        print('A5 cases:', heads)
        # open changed case
        await pg.click('[data-act=fstatus][data-s=changed]'); await pg.wait_for_timeout(200)
        await pg.click('.case-h >> nth=0'); await pg.wait_for_timeout(200)
        print('A6 changed box:', (await pg.inner_text('.upd-box')).replace('\n',' | '))
        await pg.click('[data-act=toggle-src]'); await pg.wait_for_timeout(200)
        print('A6 source shown:', 'Неверный email' in await pg.inner_text('.upd-box'))
        # obsolete toggle on a same case
        await pg.click('[data-act=fstatus][data-s=changed]'); await pg.click('[data-act=fstatus][data-s=same]'); await pg.wait_for_timeout(200)
        await pg.click('.case-h >> nth=0'); await pg.wait_for_timeout(200)
        await pg.click('[data-act=case-obsolete]'); await pg.wait_for_timeout(300)
        await pg.click('[data-act=fstatus][data-s=same]'); await pg.wait_for_timeout(200)
        print('A7 after mark obsolete:', (await pg.inner_text('.toolbar')).replace('\n',' '))
        print('A7 tms hint:', [l for l in (await pg.inner_text('#tms-bar')).split('\n') if 'Устаревшие' in l or 'Загрузить' in l])
        # export default JSON
        await pg.click('#tab-export'); await pg.wait_for_timeout(400)
        body=await pg.inner_text('#tab-body')
        print('A8 export has actualization:', '"actualization"' in body, '| statusRu:', '"Устарел"' in body)
        # reqs: coverage
        await pg.click('#tab-reqs'); await pg.wait_for_timeout(200)
        print('A9 reqs head:', (await pg.inner_text('.sec-h')).replace('\n',' '))
        await pg.click('#tab-history'); await pg.wait_for_timeout(600)
        print('A10 history:', (await pg.inner_text('#tab-body'))[:240].replace('\n',' | '))
        await pg.screenshot(path=os.path.join(D,'v9_hist.png'))
        await pg.click('#tab-cases'); await pg.wait_for_timeout(300)
        await pg.click('[data-act=fstatus][data-s=changed]'); await pg.click('.case-h >> nth=0'); await pg.wait_for_timeout(200)
        await pg.screenshot(path=os.path.join(D,'v9_cases.png'), full_page=True)
        # generate mode still works
        await pg.click('[data-mode=generate]'); await pg.click('#btn-newses'); await pg.wait_for_timeout(300)
        print('A11 gen btn:', await pg.inner_text('#btn-run'), '| upd panel hidden:', not await pg.is_visible('#upd-panel'))
        await ctx.close()
        # ---------- B: standalone JSON + reload restore ----------
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock_ext.js'))
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); hook(pg,'B')
        await pg.goto('http://local.test/')
        await pg.evaluate("""() => { localStorage.clear(); localStorage.setItem('qapro.conns', JSON.stringify([{id:'aiX', kind:'openai', name:'LLM', baseUrl:'http://ai.test/v1', model:'m', apiKey:'k', auth:'Bearer', headers:'', tools:false}])); localStorage.setItem('tca.settings', JSON.stringify({genAI:'conn:aiX', mode:'update'})); }""")
        await pg.reload(); await pg.wait_for_timeout(1500)
        print('B1 mode remembered:', await pg.is_visible('#upd-panel'))
        await pg.set_input_files('#upd-input', os.path.join(D,'tests.json')); await pg.wait_for_timeout(600)
        print('B2 json:', (await pg.inner_text('#upd-info')).replace('\n',' | '))
        await pg.click('#btn-run'); await wait_idle(pg)
        await pg.click('#tab-cases'); await pg.wait_for_timeout(300)
        print('B3 cases:', await pg.eval_on_selector_all('.case-h', 'els => els.map(e => e.querySelector(".case-id").textContent + " " + (e.querySelector(".chip[class*=ust-]")||{}).textContent)'))
        await pg.reload(); await pg.wait_for_timeout(1800)
        await pg.click('#tab-cases'); await pg.wait_for_timeout(300)
        print('B4 after reload:', await pg.eval_on_selector_all('.case-h', 'els => els.map(e => e.querySelector(".case-id").textContent + " " + (e.querySelector(".chip[class*=ust-]")||{}).textContent)'))
        await pg.click('.case-h >> nth=0'); await pg.wait_for_timeout(200)
        await pg.click('[data-act=toggle-src]'); await pg.wait_for_timeout(200)
        print('B4 source after reload:', 'POST' in await pg.inner_text('.upd-box'))
        await ctx.close()
        print('ERRORS', errs); await b.close()
asyncio.run(main())
