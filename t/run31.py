# Большой раздел: сводка без обрезки (по подзаголовкам, сжатие без потери фактов), раздел держится в лимите базы,
# прогресс разбора по фрагментам и шагам большой сводки.
import asyncio, os, sys, re, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run27 import dbop, serve, wait_idle, D, STORE
from playwright.async_api import async_playwright
BIG=sorted(glob.glob(os.path.join(D,'big','big*.md')), key=lambda x: int(re.search(r'big(\d+)', x).group(1)))
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script="window.__qaTest = true; window.__sampleDelay = 40;")
        for f in ('mockgen.js','mock_shared.js'): await ctx.add_init_script(path=os.path.join(D,f))
        await ctx.route('http://kb2.test/**', serve)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://kb2.test/'); await pg.wait_for_timeout(2500)
        await pg.click('[data-mode=help]'); await pg.wait_for_timeout(300)
        await pg.evaluate('__qa.S.settings.kbAuto = false')
        # пример ТЗ убираем, чтобы разбирались только большие документы
        await pg.evaluate("() => { for (const d of __qa.S.docs.filter(x => x.sample)) d.status = 'error'; }")
        await pg.set_input_files('#file-input', BIG); await pg.wait_for_timeout(2500)
        await pg.click('[data-act=kb-run]')
        seen=[]; notes=[]
        for _ in range(3000):
            t=(await pg.inner_text('#kb-job')).split('\n')[0]
            if t and (not seen or seen[-1]!=t): seen.append(t)
            n=await pg.inner_text('#docs-note')
            m=re.search(r'(Разбираю[^\n]*|Собираю[^\n]*)', n)
            if m and (not notes or notes[-1]!=m.group(1)): notes.append(m.group(1))
            if not await pg.evaluate('__qa.S.kb.job.busy'): break
            await pg.wait_for_timeout(120)
        await wait_idle(pg, 120000)
        pick=lambda pat: [x for x in seen if re.search(pat, x)]
        print('B1 split progress samples:', len(seen), 'lines'); [print('   ', x[:230]) for x in (pick('фрагментов разобрано')[:2]+pick('часть 2 из 2')[:1]+pick('свожу разросшийся')[:2]+pick('большой раздел')[:2]+pick('Собираю сводки')[:1])]
        print('B1 docs note sample:', [x[:200] for x in notes if 'фрагментов' in x][:1])
        log=await pg.evaluate("__qa.S.kb.job.log.map(l => l.text)")
        print('B2 log (grown/big):', [l for l in log if re.search('разросся|раздел большой|сведено в|сжимаю', l)][:6])
        pid=await pg.evaluate('__qa.S.productId')
        idx=STORE.get(f'products/{pid}/meta/kb') or {}
        gen=[x for x in idx.get('blocks',[]) if x['title']=='Общие сведения'][0]
        doc=dict(STORE.get(f"products/{pid}/kb/{gen['id']}"))
        size=len(json.dumps(doc, ensure_ascii=False).encode('utf-8'))
        more=[STORE.get(f"products/{pid}/kb/{gen['id']}__p{i}") for i in range(1, (doc.get('more') or 0)+1)]
        msz=[len(json.dumps(m, ensure_ascii=False).encode('utf-8')) for m in more]
        doc['parts']=doc['parts']+[x for m in more for x in m['parts']]
        cut=sum(1 for x in doc['parts'] if not x.get('md')); live=sum(1 for x in doc['parts'] if x.get('md'))
        print('B3 section:', {'bytes': size, 'more': doc.get('more'), 'moreBytes': msz, 'parts': len(doc['parts']), 'live': live, 'cut': cut, 'lost': doc.get('lost',0), 'synthV': doc.get('synthV'), 'big': doc.get('big'), 'fresh': gen.get('sh')==gen.get('ph'), 'docIds': len(gen['docIds']), 'synthLen': len(doc.get('synth',''))})
        synth=doc.get('synth',''); conf=' '.join(doc.get('conflicts',[]))
        want=[f'F{si}-{j}' for si in range(4) for j in range(20)]+[f'U{k}-{si}-{j}' for k in range(1,17) for si in range(4) for j in range(2)]
        miss=[w for w in want if not re.search(re.escape(w)+r':', synth) and w not in conf]
        print('B4 facts kept:', len(want)-len(miss), 'of', len(want), '| missing:', miss[:8])
        f27=re.search(r'- F2-7: [^\n]*', synth)
        print('B5 conflict F2-7:', doc.get('conflicts'), '| F2-7 in synth:', f27.group(0) if f27 else None, '| sources of F0-0:', (re.search(r'- F0-0: [^\n]*', synth) or [None])[0])
        print('B5 subheads:', re.findall(r'^### (.+)$', synth, re.M))
        sizes=await pg.evaluate("(window.__prompts||[]).filter(p => /Сожми материал подраздела|Собери часть|Собери единую сводку/.test(p)).map(p => [p.includes('Сожми') ? 'cond' : p.includes('Собери часть') ? 'part' : 'one', p.length])")
        print('B6 synth requests:', len(sizes), '| cond', sum(1 for x in sizes if x[0]=='cond'), '| part', sum(1 for x in sizes if x[0]=='part'), '| one', sum(1 for x in sizes if x[0]=='one'), '| max prompt chars:', max(x[1] for x in sizes))
        # статья раздела
        await pg.click('#help-head [data-v=qa]'); await pg.click('#help-head [data-v=blocks]'); await pg.wait_for_timeout(200)
        await pg.click('#kb-rows .kb-row:has-text("Общие сведения")'); await pg.wait_for_selector('.kb-art h3', timeout=10000)
        print('B7 article:', (await pg.inner_text('.kb-synth-h')).replace('\n',' '), '|', (await pg.inner_text('.kb-parts summary')))
        await pg.click('.kb-parts summary'); await pg.wait_for_timeout(150)
        await pg.screenshot(path=os.path.join(D,'v33_kb_big.png'))
        # kbFit: сведённые выдержки уходят первыми, отпечаток выдержек не меняется
        r=await pg.evaluate("""() => { const big = 'Ж'.repeat(22000);
          const parts = Array.from({length: 80}, (_, i) => ({ docId: 'd' + i, docName: 'doc' + i + '.md', chunk: 0, md: big + i, at: i < 60 ? 100 : 300 }));
          const next = { id: 'x', title: 'X', parts, synth: '### Описание\\n- x', synthV: 2, synthAt: 200 };
          const ph = __qa.kbPartsHash(next.parts); __qa.kbFit(next);
          const old = { id: 'y', title: 'Y', parts: parts.map(p => ({ ...p })), synth: 'x', synthAt: 200 }; __qa.kbFit(old);
          const bytes = (o) => new TextEncoder().encode(JSON.stringify(o)).length;
          return { bytes: bytes(next), cut: next.parts.filter(p => p.cut).length, freshKept: next.parts.filter(p => p.at === 300 && p.md).length, samePh: __qa.kbPartsHash(next.parts) === ph, oldSynth_lost: old.lost || 0, oldBytes: bytes(old) }; }""")
        print('B8 kbFit:', r)
        print('B9 pages:', await pg.evaluate("__qa.kbPages(Array.from({length: 400}, (_, i) => '- строка ' + i + ' ' + 'x'.repeat(40)).join('\\n'), 6000).map(p => p.length)"))
        await b.close(); print('ERRORS:', errs or 'none')
asyncio.run(main())
