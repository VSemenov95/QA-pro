import asyncio, os, json
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
skel='<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>[hidden]{display:none!important}body{margin:0}</style></head><body>'+html+'</body></html>'
standalone=open(os.path.join(ROOT,'qa-pro.html'),encoding='utf-8').read()
async def route(r):
    u=r.request.url
    if u.startswith('http://app.test/'): return await r.fulfill(body=skel, content_type='text/html; charset=utf-8')
    if u.startswith('http://local.test/'): return await r.fulfill(body=standalone, content_type='text/html; charset=utf-8')
    await r.abort()

STORE = """(() => { const o = {}; for (const [k, v] of window.__store) o[k] = v; return o; })()"""
async def wait_idle(pg, t=40000):
    await pg.wait_for_timeout(300)
    await pg.wait_for_selector('#btn-run:not([hidden])', timeout=t)
    await pg.wait_for_timeout(1200)

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        def hook(pg, tag):
            pg.on('pageerror', lambda e: errs.append(tag+' PAGEERR '+str(e)))
            pg.on('console', lambda m: errs.append(tag+' CONSOLE '+m.text) if m.type=='error' and 'net::' not in m.text and 'Failed to load' not in m.text else None)
        # ---------- A: claude.ai mode ----------
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock.js'))
        await ctx.add_init_script(script='window.__QA_DEBUG = 1; window.__qaTest = true;')
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); hook(pg,'A')
        await pg.goto('http://app.test/'); await pg.wait_for_timeout(1500)
        print('A1 product select:', await pg.is_visible('#prod-switch'), '|', (await pg.inner_text('#prod-select')).replace('\n',' / '))
        print('A1 docs:', (await pg.inner_text('#doc-list')).replace('\n',' | '), '| tabs:', (await pg.inner_text('#tabs')).replace('\n',' '))
        await pg.fill('#qa-ctx', 'Окружение stage, роль Оператор'); await pg.wait_for_timeout(1500)
        st=await pg.evaluate(STORE)
        pk=[k for k in st if k.startswith('products/') and k.count('/')==1]
        print('A2 products in store:', [(k, st[k]['name'], st[k]['qaCtx']['all'], len(st[k]['docs'])) for k in pk])
        pid=pk[0].split('/')[1]
        await pg.click('#btn-run'); await wait_idle(pg); await pg.click('#tab-draft'); await pg.click('[data-act=draft-add]'); await pg.wait_for_timeout(1000)
        tl=(await pg.click('#tab-agent'), await pg.inner_text('.timeline'))[1]
        print('A3 knowledge log:', [l for l in tl.split('\n') if 'знани' in l.lower()])
        st=await pg.evaluate(STORE)
        ids1=[x['i'] for x in st[f'products/{pid}/meta/cases']['items']]
        print('A3 index cases:', ids1, '| checklist idx:', len(st[f'products/{pid}/meta/checklist']['items']))
        print('A3 product counters:', st[f'products/{pid}']['counters'], '| passport:', (st.get(f'products/{pid}/meta/passport') or {}).get('text','')[:60].replace('\n',' '), '| in product card:', st[f'products/{pid}'].get('passport'))
        runs=[k for k in st if k.startswith(f'products/{pid}/runs/') and k.count('/')==3]
        print('A3 runs in product:', len(runs))
        # product tab
        await pg.wait_for_timeout(500)
        print('A4 product panel:', (await pg.inner_text('#prod-info'))[:500].replace('\n',' | '))
        await pg.screenshot(path=os.path.join(D,'v7_product.png'), full_page=True)
        # second run
        await pg.click('#btn-newses'); await pg.wait_for_timeout(300)
        print('A4 new run clears run docs:', await pg.evaluate('__qa.S.runDocs.size'), '| run disabled:', await pg.is_disabled('#btn-run'))
        await pg.evaluate("() => { for (const d of __qa.S.docs) __qa.S.runDocs.add(d.id); }"); await pg.click('[data-mode=help]'); await pg.wait_for_timeout(200); await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(300)
        print('A4 re-added:', await pg.evaluate('__qa.S.runDocs.size'), '| run disabled:', await pg.is_disabled('#btn-run'), '| note:', await pg.inner_text('#run-note'))
        await pg.evaluate('window.__prompts = []')
        await pg.click('#btn-run'); await wait_idle(pg); await pg.click('#tab-draft'); await pg.click('[data-act=draft-add]'); await pg.wait_for_timeout(1000)
        chk=await pg.evaluate("""() => { const P = window.__prompts; const plan = P.find(p => p.includes('Составь план')); const gen = P.filter(p => p.includes('Напиши тест-кейсы')); const cl = P.find(p => p.includes('Составь чек-лист')); const an = P.find(p => p.includes('Выдели из проектной'));
          return { planExisting: !!plan && plan.includes('## Уже есть в продукте'), planKnow: !!plan && plan.includes('## Знания о продукте'), genKnow: gen.length > 0 && gen.every(p => p.includes('## Знания о продукте')), genExisting: gen.some(p => p.includes('## Уже есть в продукте')),
            clExisting: !!cl && cl.includes('## Уже есть в продукте'), anKnow: !!an && an.includes('## Знания о продукте'), passCalls: P.filter(p => p.includes('Ты ведёшь «паспорт продукта»')).length, passHasPrev: P.some(p => p.includes('Ты ведёшь «паспорт продукта»') && p.includes('Версия знаний 1')) }; }""")
        print('A5 prompts:', chk)
        st=await pg.evaluate(STORE)
        items=st[f'products/{pid}/meta/cases']['items']
        runs=sorted(set(x['r'] for x in items))
        print('A5 index after run2:', len(items), 'runs', len(runs), '| ids:', [x['i'] for x in items])
        await pg.click('#tab-reqs'); await pg.wait_for_timeout(300)
        print('A5 reqs:', [l for l in (await pg.inner_text('#tab-body')).split('\n') if 'в продукте' in l or 'R-003' in l][:3])
        tl=await pg.inner_text('#tab-agent'); await pg.click('#tab-agent'); await pg.wait_for_timeout(200)
        print('A5 plan log:', [l for l in ((await pg.click('#tab-agent'), await pg.inner_text('.timeline'))[1]).split('\n') if 'Уже покрыто' in l or 'Без кейсов' in l or 'Все требования' in l])
        # new product via select
        await pg.select_option('#prod-select', '__new'); await pg.wait_for_timeout(200)
        print('A6 dialog visible:', await pg.is_visible('#prod-ov'))
        await pg.fill('#prod-name', 'Биллинг'); await pg.fill('#prod-desc', 'Счета и оплаты'); await pg.press('#prod-name', 'Enter'); await pg.wait_for_timeout(1200)
        print('A6 after create: select=', await pg.eval_on_selector('#prod-select', 'e => e.selectedOptions[0].textContent'), '| docs:', (await pg.inner_text('#doc-list')).replace('\n',' | ') or '(пусто)', '| ctx:', repr(await pg.input_value('#qa-ctx')), '| tab:', await pg.eval_on_selector('.tab[aria-selected=true]', 'e=>e.textContent'))
        await pg.set_input_files('#file-input', os.path.join(D,'extra.txt')); await pg.wait_for_timeout(1200)
        await pg.fill('#qa-ctx', 'Биллинг: роль Бухгалтер'); await pg.wait_for_timeout(1500)
        st=await pg.evaluate(STORE)
        pid2=[k.split('/')[1] for k in st if k.startswith('products/') and k.count('/')==1 and st[k]['name']=='Биллинг'][0]
        print('A6 billing doc meta:', [(d['name'], d['parts']) for d in st[f'products/{pid2}']['docs']], '| docparts:', [k for k in st if k.startswith(f'products/{pid2}/docparts/')])
        await pg.select_option('#prod-select', pid); await pg.wait_for_timeout(1200)
        print('A7 back to first: docs=', (await pg.inner_text('#doc-list')).replace('\n',' | '), '| ctx=', repr(await pg.input_value('#qa-ctx')))
        await pg.click('#tab-history'); await pg.wait_for_timeout(600)
        print('A7 history:', (await pg.inner_text('#tab-body'))[:200].replace('\n',' | '))
        await pg.select_option('#prod-select', pid2); await pg.wait_for_timeout(1200)
        print('A8 billing again: docs=', (await pg.inner_text('#doc-list')).replace('\n',' | '), '| ctx=', repr(await pg.input_value('#qa-ctx')))
        # кнопки «Добавить пример ТЗ» при документах нет — второй документ загружаем файлом → 2 docs → uncheck one
        print('A9 sample button with docs hidden:', await pg.evaluate("document.querySelector('#btn-sample').hidden"))
        await pg.set_input_files('#file-input', os.path.join(D,'rules.md')); await pg.wait_for_timeout(1200)
        await pg.click('#doc-list [data-doc-act=unrun] >> nth=0'); await pg.wait_for_timeout(200)
        print('A9 docs total:', await pg.inner_text('#docs-total'), '| note:', await pg.inner_text('#run-note'))
        await pg.click('#btn-run'); await wait_idle(pg); await pg.click('#tab-draft'); await pg.click('[data-act=draft-add]'); await pg.wait_for_timeout(1000)
        print('A9 run docs:', await pg.evaluate("(() => { const st = window.__store; for (const [k, v] of st) if (k.includes('/runs/') && k.split('/').length === 4 && k.includes('" + pid2 + "')) return v.docs.map(d => d.name); })()"))
        # passport edit
        await pg.wait_for_timeout(300)
        await pg.click('[data-act=pass-edit]'); await pg.fill('#pass-text', '## Термины\n- Счёт — документ на оплату'); await pg.click('[data-act=pass-save]'); await pg.wait_for_timeout(500)
        st=await pg.evaluate(STORE)
        print('A10 passport saved:', repr(st[f'products/{pid2}/meta/passport']['text']), '| prev kept:', bool(st[f'products/{pid2}/meta/passport'].get('prev')))
        print('A10 md:', (await pg.inner_text('#prod-info .md')).replace('\n',' | '))
        # delete product
        await pg.click('[data-act=prod-del]'); await pg.click('[data-act=prod-del]'); await pg.wait_for_timeout(1500)
        st=await pg.evaluate(STORE)
        print('A11 after delete: left keys for billing:', [k for k in st if pid2 in k], '| select:', (await pg.inner_text('#prod-select')).replace('\n',' / '))
        await ctx.close()

        # ---------- B: standalone, legacy migration ----------
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock_ext.js'))
        await ctx.add_init_script(script='window.__QA_DEBUG = 1; window.__qaTest = true;')
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); hook(pg,'B')
        await pg.goto('http://local.test/')
        legacy_text='ТЗ (legacy): лимит 3 запроса за 15 минут, затем 429 RATE_LIMIT.'
        seed={
          'qapro.conns': [{'id':'aiX','kind':'openai','name':'Корп. LLM','baseUrl':'http://ai.test/v1','model':'m','apiKey':'k','auth':'Bearer','headers':'','tools':False}],
          'tca.settings': {'genAI':'conn:aiX'},
          'qapro.db:data/users/local/session': {'kind':'session','docs':[{'id':'dL','name':'legacy.txt','ext':'txt','chars':len(legacy_text),'parts':1}],'qaCtx':{'all':'legacy ctx','api':'','ui':'','e2e':''},'runId':'run_legacy','tab':'cases'},
          'qapro.db:data/users/local/session/docparts/dL_0': {'docId':'dL','i':0,'text':legacy_text},
          'qapro.db:data/users/local/run_legacy': {'kind':'run','id':'run_legacy','createdAt':1700000000000,'updatedAt':1700000000000,'finishedAt':1700000001000,'docs':[{'name':'legacy.txt','chars':10}],'settings':{'outputs':{'cases':True,'checklist':False},'types':['api','ui','e2e']},'requirements':[{'id':'R-001','title':'Лимит','description':'3 запроса','types':['api'],'priority':'high','criteria':[],'inScope':True,'doc':'','section':'','quote':''}],'questions':[],'checklist':None,'plan':[],'counts':{'api':1,'ui':1,'e2e':0,'checklist':0},'partsCount':1,'status':'done','counters':{'api':7,'ui':5,'e2e':0,'cl':0}},
          'qapro.db:data/users/local/run_legacy/parts/p0': {'cases':[{'uid':'c1','type':'api','planItem':'P-01','requirementIds':['R-001'],'suites':['regression'],'testCase':{'id':'API-007','title':'429 на четвёртый запрос'},'dispId':'API-007'},{'uid':'c2','type':'ui','planItem':'P-01','requirementIds':['R-001'],'suites':[],'testCase':{'id':'UI-005','title':'Сообщение о лимите'},'dispId':'UI-005'}]},
        }
        await pg.evaluate('(seed) => { localStorage.clear(); for (const [k, v] of Object.entries(seed)) localStorage.setItem(k, JSON.stringify(v)); }', seed)
        await pg.reload(); await pg.wait_for_timeout(1800)
        print('B1 select:', (await pg.inner_text('#prod-select')).replace('\n',' / '), '| docs:', (await pg.inner_text('#doc-list')).replace('\n',' | '), '| ctx:', repr(await pg.input_value('#qa-ctx')))
        print('B1 tab:', await pg.eval_on_selector('.tab[aria-selected=true]', 'e=>e.textContent'), '| cases cnt:', await pg.inner_text('#tab-cases'))
        await pg.click('#tab-history'); await pg.wait_for_timeout(600)
        print('B2 history:', (await pg.inner_text('#tab-body'))[:400].replace('\n',' | '))
        await pg.click('[data-act=move-hist]'); await pg.wait_for_timeout(1200)
        idx=await pg.evaluate("(() => { const k = Object.keys(localStorage).find(k => k.endsWith('/meta/cases')); return k ? JSON.parse(localStorage.getItem(k)).items.map(x => x.i) : null; })()")
        print('B2 after move: index', idx, '| history:', (await pg.inner_text('#tab-body'))[:200].replace('\n',' | '))
        await pg.click('#btn-newses'); await pg.wait_for_timeout(300)
        await pg.evaluate("() => { for (const d of __qa.S.docs) __qa.S.runDocs.add(d.id); }"); await pg.click('[data-mode=help]'); await pg.wait_for_timeout(200); await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(300)
        await pg.click('#btn-run'); await wait_idle(pg, 60000); await pg.click('#tab-draft'); await pg.click('[data-act=draft-add]'); await pg.wait_for_timeout(1000)
        ids=await pg.evaluate("(() => { const ks = Object.keys(localStorage).filter(k => k.includes('/runs/') && k.endsWith('/parts/p0') && !k.includes('run_legacy')); return ks.flatMap(k => JSON.parse(localStorage.getItem(k)).cases.map(c => c.dispId)); })()")
        print('B3 new run ids (should continue after API-007/UI-005):', ids)
        print('B4 session before reload:', await pg.evaluate("JSON.parse(localStorage.getItem('qapro.db:data/users/local/session'))"))
        await pg.reload(); await pg.wait_for_timeout(1800)
        print('B4 session after reload:', await pg.evaluate("JSON.parse(localStorage.getItem('qapro.db:data/users/local/session'))"))
        print('B4 after reload: select', (await pg.inner_text('#prod-select')).replace('\n',' / '), '| tab', await pg.eval_on_selector('.tab[aria-selected=true]', 'e=>e.textContent'), '| cases', await pg.inner_text('#tab-cases'))
        await pg.wait_for_timeout(500)
        print('B4 product panel:', (await pg.inner_text('#prod-info'))[:300].replace('\n',' | '))
        await ctx.close()
        # mobile layout
        ctx=await b.new_context(viewport={'width':390,'height':860}, color_scheme='dark')
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock.js'))
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); hook(pg,'M')
        await pg.goto('http://app.test/'); await pg.wait_for_timeout(1500)
        await pg.wait_for_timeout(300)
        print('M scrollWidth:', await pg.evaluate('document.documentElement.scrollWidth'))
        await pg.screenshot(path=os.path.join(D,'v7_mobile.png'), full_page=False)
        await ctx.close()
        print('ERRORS', errs); await b.close()
asyncio.run(main())
