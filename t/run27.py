# База знаний: сводки разделов по всем документам (расхождения, связи), автообновление «Что агент знает о продукте»,
# поиск по смыслу в ответах и база знаний в генерации (анализ, чек-лист, план, кейсы, ревью, инструменты агента).
import asyncio, os, json, time, re
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
SKEL='<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>[hidden]{display:none!important}body{margin:0}</style></head><body>'+html+'</body></html>'
async def serve(r): await r.fulfill(body=SKEL, content_type='text/html; charset=utf-8')
STORE={}; LEASES={}
def dbop(source, op, path, payload=None):
    if op=='get': return STORE.get(path)
    if op=='set': STORE[path]=payload; return True
    if op=='update':
        if path not in STORE: return 'missing'
        STORE[path]={**STORE[path], **payload}; return True
    if op=='delete': STORE.pop(path,None); return True
    if op=='list':
        rows=[[p,d] for p,d in STORE.items() if p.startswith(path+'/') and '/' not in p[len(path)+1:]]
        for f,o,v in payload['filters']:
            if o=='==': rows=[r for r in rows if r[1].get(f)==v]
        if payload.get('ord'):
            f,d=payload['ord']; rows.sort(key=lambda r: (r[1].get(f) is None, r[1].get(f) or 0), reverse=(d=='desc'))
        return rows[:payload.get('lim') or 1000]
    if op=='acquire':
        now=time.time(); e=LEASES.get(path)
        if e and e[0]>now and e[1]!=payload['holder']: return {'acquired':False}
        LEASES[path]=(now+(payload.get('ttlMs') or 30000)/1000, payload['holder']); return {'acquired':True}
IDX = "(() => __qa.S.kb.index.blocks.map(b => ({ t: b.title, docs: b.docIds.length, ph: !!b.ph, fresh: !!b.sh && b.sh === b.ph, conf: b.conf || 0 })))()"
async def wait_idle(pg, t=60000):
    await pg.wait_for_function("() => !__qa.S.kb.job.busy && !__qa.S.know.busy && !__qa.S.kb.queue.length", timeout=t)
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script='window.__qaTest = true; window.__sampleDelay = 15;')
        for f in ('mockgen.js','mock_shared.js'): await ctx.add_init_script(path=os.path.join(D,f))
        await ctx.route('http://kb2.test/**', serve)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://kb2.test/'); await pg.wait_for_timeout(2500)
        await pg.click('[data-mode=help]'); await pg.wait_for_timeout(500)
        # 1) разбор примера ТЗ: разделы → сводки → знания о продукте
        await pg.click('[data-act=kb-run]'); await pg.wait_for_timeout(300); await wait_idle(pg)
        print('S1 sections:', await pg.evaluate(IDX), '| synth calls:', await pg.evaluate('window.__synthCalls || 0'))
        print('S1 knowledge auto-updated:', await pg.evaluate("({ passport: (__qa.S.products.find(p => p.id === __qa.S.productId)?.passport?.text || '').length, learned: (__qa.S.prodKnown?.docs || []).length })"))
        # 2) два документа с разными лимитами: раздел сводится по всем документам и показывает расхождение
        await pg.set_input_files('#file-input', [os.path.join(D,'kb_extra.md'), os.path.join(D,'kb_созвон-call.md')]); await pg.wait_for_timeout(1500); await wait_idle(pg)
        print('S2 sections:', await pg.evaluate(IDX), '| synth calls:', await pg.evaluate('window.__synthCalls || 0'), '| learned docs:', await pg.evaluate("(__qa.S.prodKnown?.docs || []).length"))
        print('S2 rows:', await pg.eval_on_selector_all('#kb-rows .kb-row', "els => els.map(e => e.querySelector('.kb-row-t').textContent + ' [' + e.querySelector('.kb-row-m').textContent + ']')"))
        print('S2 kb line:', await pg.inner_text('.kb-line'))
        await pg.screenshot(path=os.path.join(D,'v29_kb_rows.png'), full_page=True)
        await pg.click('#kb-rows .kb-row:has-text("Восстановление пароля")'); await pg.wait_for_selector('.kb-synth', timeout=10000)
        art = await pg.evaluate("""(() => ({ head: document.querySelector('.kb-synth-h').innerText.replace(/\\n/g, ' '), conf: document.querySelector('.kb-conf')?.innerText.replace(/\\n/g, ' | ') || '',
          synthHasConfSection: /Расхождени/.test(document.querySelector('.kb-synth .md').innerText), body: document.querySelector('.kb-synth .md').innerText.replace(/\\n/g, ' | ').slice(0, 400),
          links: [...document.querySelectorAll('.kb-synth .chip-link')].map(x => x.textContent), parts: document.querySelector('.kb-parts summary')?.textContent, partsOpen: document.querySelector('.kb-parts')?.open }))()""")
        print('S3 article:', json.dumps(art, ensure_ascii=False))
        await pg.screenshot(path=os.path.join(D,'v29_kb_article.png'), full_page=True)
        await pg.click('.kb-parts summary'); await pg.wait_for_timeout(200)
        await pg.evaluate("__qa.S.kb.job.log.push({text:'x', kind:''})"); await pg.click('#help-head [data-v=blocks]'); await pg.wait_for_timeout(200)
        print('S3 parts stay open after re-render:', await pg.evaluate("document.querySelector('.kb-parts')?.open"))
        await pg.click('.kb-synth .chip-link'); await pg.wait_for_timeout(500)
        print('S3 link opens:', await pg.inner_text('.kb-art h3'))
        await pg.click('[data-act=kb-back]'); await pg.wait_for_timeout(200)
        # 3) поиск по смыслу: в вопросе нет слов из документов — раздел находит модель
        await pg.click('#help-head [data-v=qa]'); await pg.wait_for_timeout(200)
        q = 'Что делать пользователю, который не помнит секрет для авторизации?'
        await pg.fill('#help-input', q); await pg.click('#help-send')
        await pg.wait_for_function("() => !__qa.S.help.busy && __qa.S.help.items.length && __qa.S.help.items.at(-1).status !== 'pending'", timeout=20000)
        hp = await pg.evaluate("(window.__prompts || []).filter(p => p.includes('справочная служба QA-команды')).at(-1) || ''")
        item = await pg.evaluate("__qa.S.help.items.at(-1)")
        print('S4 expand calls:', await pg.evaluate('window.__expandCalls || 0'), '| terms:', item.get('terms'), '| status:', item['status'])
        print('S4 help prompt blocks:', re.findall(r'\n\[(B\d|K\d|D\d|QA|TC|CL)\] ([^\n]{0,60})', hp)[:6])
        print('S4 section text in prompt is the synthesis:', 'Сводка' in hp or '(kb_extra' in hp or '(Пример' in hp, '| has conflicts:', 'Расхождени' in hp)
        # 4) генерация учитывает базу знаний
        await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(400)
        print('S5 intro:', [t.replace('\n', ' ')[:300] for t in await pg.eval_on_selector_all('#tab-body .banner', 'els => els.map(e => e.innerText)') if 'База знаний' in t])
        n0 = await pg.evaluate('(window.__prompts || []).length')
        await pg.click('#btn-run'); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=90000); await pg.wait_for_timeout(800)
        prompts = await pg.evaluate(f'(window.__prompts || []).slice({n0})')
        kinds = {'анализ': 'Выдели из проектной документации', 'чек-лист': 'Составь чек-лист', 'план': 'Составь план', 'кейсы': 'Напиши тест-кейсы', 'ревью': 'строгий ревьюер'}
        for k, marker in kinds.items():
            ps = [x for x in prompts if marker in x]
            withkb = [x for x in ps if '## База знаний продукта — разделы по теме' in x]
            print(f'S5 {k}: запросов {len(ps)}, с базой знаний {len(withkb)}', '| раздел «Восстановление пароля»:', any('Раздел «Восстановление пароля»' in x for x in withkb), '| расхождения:', any('Расхождени' in x for x in withkb))
        log = await pg.evaluate("__qa.S.run.steps.parse.log.map(l => l.text).filter(t => /База знаний/.test(t))")
        print('S5 run log:', log)
        plan = [x for x in prompts if 'Составь план' in x][0]
        print('S5 plan prompt KB block:\n' + plan[plan.index('## База знаний продукта'):][:900])
        tools = await pg.evaluate("""(async () => { const t = __qa.makeTools(__qa.S.run, 'generate'); const s = t.find(x => x.name === 'search_knowledge_base'), r = t.find(x => x.name === 'read_knowledge_section');
          const found = await s.execute({ query: 'лимит запросов на сброс пароля' }); const one = await r.execute({ id: found[0].id }); const miss = await r.execute({ id: 'нет такого' });
          return { names: t.map(x => x.name), found: found.map(x => [x.title, x.conflicts.length, x.text.length]), read: [one.title, one.text.length, one.links], miss }; })()""")
        print('S5 agent tools:', tools['names'], '| search →', tools['found'], '| read →', tools['read'], '| unknown id →', tools['miss'])
        # 5) документ удалён — сводка пересобирается без него, расхождение уходит
        await pg.click('[data-mode=help]'); await pg.wait_for_timeout(400)
        sc0 = await pg.evaluate('window.__synthCalls || 0')
        btn = '#doc-list li:has-text("созвон") [data-doc-act=remove]'
        await pg.click(btn); await pg.wait_for_timeout(150); await pg.click(btn); await pg.wait_for_timeout(800); await wait_idle(pg)
        print('S6 after delete:', await pg.evaluate(IDX), '| re-synth calls:', await pg.evaluate('window.__synthCalls || 0') - sc0)
        # 6) старые разделы без сводки — баннер и «Собрать сводки»
        await pg.evaluate("""(() => { for (const b of __qa.S.kb.index.blocks) b.sh = ''; })()""")
        await pg.click('#help-head [data-v=qa]'); await pg.click('#help-head [data-v=blocks]'); await pg.wait_for_timeout(300)
        print('S7 banner:', (await pg.inner_text('#kb-job')).replace('\n', ' ')[:260])
        await pg.screenshot(path=os.path.join(D,'v29_kb_stale.png'))
        await pg.click('[data-act=kb-synth]'); await pg.wait_for_timeout(300); await wait_idle(pg)
        print('S7 after «Собрать сводки»:', await pg.evaluate(IDX), '| banner left:', bool((await pg.inner_text('#kb-job')).strip()))
        # 7) размер раздела: самые старые выдержки уходят, документ базы ≤ 240 КБ
        fit = await pg.evaluate("""(() => { const parts = Array.from({ length: 20 }, (_, i) => ({ docId: 'd' + i, docName: 'Док ' + i, chunk: 0, md: 'Ж'.repeat(12000), at: 1000 + i }));
          const next = { title: 'Большой', parts, synth: 'Я'.repeat(20000) }; __qa.kbFit(next);
          return { parts: next.parts.length, oldestKept: Math.min(...next.parts.map(p => p.at)), bytes: new TextEncoder().encode(JSON.stringify(next)).length, synth: next.synth.length }; })()""")
        print('S8 kbFit:', fit)
        frozen = await pg.evaluate("""(() => { const parts = Object.freeze(Array.from({ length: 20 }, (_, i) => Object.freeze({ docId: 'd' + i, docName: 'Док ' + i, chunk: 0, md: 'Ж'.repeat(12000), at: 1000 + i })));
          const next = { ...Object.freeze({ title: 'Из базы', parts }), synth: 'x' }; try { __qa.kbFit(next); return { ok: true, parts: next.parts.length, sourceUntouched: parts.length === 20 }; } catch (e) { return { ok: false, error: String(e) }; } })()""")
        print('S8 kbFit on frozen DB data:', frozen)
        cap = await pg.evaluate("(() => { const b = __qa.kbGenBlock(__qa.S.run, 'batch', 'восстановление пароля сброс лимит запросов API'); return { len: b.length, sections: (b.match(/### Раздел/g) || []).length }; })()")
        print('S8 batch block size:', cap)
        await b.close()
        print('ERRORS:', errs or 'none')
if __name__ == "__main__": asyncio.run(main())
