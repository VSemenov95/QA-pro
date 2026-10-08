# Лимиты: оглавление базы знаний страницами (тысячи разделов), оглавление по теме в запросе разбора,
# «Что агент знает о продукте» до 40 000 знаков отдельной записью, больше базы знаний в генерации.
import asyncio, os, sys, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run27 import dbop, serve, IDX, wait_idle, D, STORE
from playwright.async_api import async_playwright
def nbytes(x): return len(json.dumps(x, ensure_ascii=False).encode('utf-8'))
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
        await pg.evaluate('__qa.S.settings.kbAuto = false')
        pid=await pg.evaluate('__qa.S.productId')
        # 1500 разделов — оглавление страницами
        await pg.evaluate("""async () => { const blocks = Array.from({length: 1500}, (_, i) => ({ id: 'kbz' + i.toString(36).padStart(4, '0'), title: 'Модуль ' + i + ' — ' + ['Отчёты', 'Платежи', 'Профиль', 'Уведомления', 'Склад'][i % 5], summary: 'Описание функциональности номер ' + i + ': ' + 'экраны, поля, правила и ограничения модуля. '.repeat(5), docIds: ['d1'], parts: 1, size: 100, updatedAt: 1, ph: 'x', sh: 'x', conf: 0 }));
          await __qa.kbIdxWrite(__qa.S.productId, blocks, { d1: { hash: 'h' } }, null); await __qa.loadKb(__qa.S.productId); }""")
        pages=[k for k in STORE if k.startswith(f'products/{pid}/meta/kb')]
        print('E1 index pages:', sorted(pages), '| bytes:', [nbytes(STORE[k]) for k in sorted(pages)], '| loaded blocks:', await pg.evaluate('__qa.S.kb.index.blocks.length'))
        # разбор документа при 1500 разделах: в запросе — ближайшие разделы с описаниями и остальные названиями
        await pg.click('[data-mode=help]'); await pg.wait_for_timeout(300)
        await pg.evaluate('window.__prompts = []')
        await pg.click('[data-act=kb-run]'); await pg.wait_for_timeout(500); await wait_idle(pg, 120000)
        sp=[x for x in await pg.evaluate('window.__prompts') if 'Раздели фрагмент' in x]
        outline=sp[0].split('## Разделы, которые уже есть в базе знаний\n')[1].split('\n## Правила')[0] if sp else ''
        lines=outline.split('\n')
        print('E2 split prompt chars:', len(sp[0]) if sp else 0, '| outline lines:', len(lines), '| with summary:', sum(1 for l in lines if ' — Описание' in l), '| tail:', lines[-1][:90])
        print('E2 index after run:', await pg.evaluate('__qa.S.kb.index.blocks.length'), '| pages:', STORE[f'products/{pid}/meta/kb'].get('pages'), '| new sections:', [x['t'] for x in await pg.evaluate(IDX) if not x['t'].startswith('Модуль')])
        # оглавление по теме: «Платежи» для текста про оплату
        o=await pg.evaluate("__qa.kbOutline(__qa.S.kb.index.blocks, 'Платежи оплата картой', { top: 20, cap: 3000 })")
        print('E3 outline top lines:', [l[:40] for l in o.split('\n')[:3]], '| total lines:', len(o.split('\n')))
        # знания о продукте: 39 000 знаков — отдельной записью
        big='## Бизнес-правила и ограничения\n' + '\n'.join(f'- Правило {i}: лимит {i} операций, экран «Платёж {i}», сообщение «Превышен лимит {i}» (ТЗ)' for i in range(470))
        await pg.evaluate("(t) => __qa.savePassport(__qa.S.productId, t, null)", big[:39000])
        await pg.evaluate("(t) => __qa.savePassport(__qa.S.productId, t + '\\n- Новое правило', null)", big[:39000])
        prod=STORE[f'products/{pid}']; mp=STORE.get(f'products/{pid}/meta/passport') or {}
        print('E4 passport: product field:', {k: v for k, v in prod['passport'].items() if k != 'by'}, '| product bytes:', nbytes(prod), '| meta text:', len(mp.get('text','')), '| prev:', len(((mp.get('prev') or {}).get('text') or '')), '| local text:', await pg.evaluate("__qa.S.products.find(p => p.id === __qa.S.productId).passport.text.length"))
        blk=await pg.evaluate("__qa.productBlock(null, 'single', 'Платёж 400 лимит операций')")
        print('E5 product block (single):', len(blk), '| has Правило 400:', 'Правило 400' in blk)
        await pg.reload(); await pg.wait_for_timeout(3500)
        print('E6 after reload: passport len:', await pg.evaluate("__qa.S.products.find(p => p.id === __qa.S.productId)?.passport?.text?.length || 0"), '| KB blocks:', await pg.evaluate('__qa.S.kb.index.blocks.length'))
        await b.close(); print('ERRORS:', errs or 'none')
asyncio.run(main())
