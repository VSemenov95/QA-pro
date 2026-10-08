# Генерация и актуализация — по документам запуска (загруженным для него) + база знаний; без выбора из всех документов
import asyncio, os, sys, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run27 import dbop, serve, IDX, wait_idle, D, STORE
from playwright.async_api import async_playwright
ROWS="() => [...document.querySelectorAll('#doc-list .doc')].map(e => e.querySelector('.doc-name').textContent)"
async def state(pg):
    return await pg.evaluate("""() => ({ mode: __qa.S.settings.mode, head: document.querySelector('#h-docs-t').textContent, rows: [...document.querySelectorAll('#doc-list .doc .doc-name')].map(e => e.textContent),
      checkboxes: document.querySelectorAll('#doc-list input[type=checkbox]').length, product: (__qa.S.products.find(p => p.id === __qa.S.productId)?.docs || []).map(d => d.name) })""")
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
        await pg.evaluate('__qa.S.settings.kbAuto = true')
        print('J1 fresh product, generate:', await state(pg))
        # база знаний: разбор примера + доп. документ, загруженный в «Базе знаний»
        await pg.click('[data-mode=help]'); await pg.wait_for_timeout(300)
        await pg.set_input_files('#file-input', os.path.join(D,'kb_extra.md')); await pg.wait_for_timeout(1500); await wait_idle(pg)
        print('J2 KB mode:', await state(pg), '| sections:', await pg.evaluate(IDX))
        await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(300)
        print('J3 generate (KB upload not in run):', await state(pg))
        print('J3 note:', await pg.inner_text('#docs-note'))
        # × у примера — убирает из запуска, в продукте остаётся
        await pg.click('#doc-list [data-doc-act=unrun] >> nth=0'); await pg.wait_for_timeout(300)
        print('J4 after unrun:', await state(pg), '| run note:', await pg.inner_text('#run-note'), '| run disabled:', await pg.is_disabled('#btn-run'))
        # загрузка в генерации: документ в запуске и в продукте
        await pg.set_input_files('#file-input', os.path.join(D,'rules.md')); await pg.wait_for_timeout(1500)
        print('J5 uploaded in generate:', await state(pg))
        # тот же файл ещё раз — без копии
        await pg.set_input_files('#file-input', os.path.join(D,'kb_extra.md')); await pg.wait_for_timeout(1500)
        print('J6 re-upload existing kb_extra:', await state(pg), '| toast:', await pg.evaluate("[...document.querySelectorAll('.toast')].map(t => t.textContent).slice(-1)"))
        await wait_idle(pg)
        # запуск: в промптах — только документы запуска, плюс база знаний
        await pg.evaluate('window.__prompts = []')
        await pg.click('#btn-run'); await pg.wait_for_function('() => !__qa.S.running && __qa.S.run && __qa.S.run.status !== "running"', timeout=60000)
        pr=await pg.evaluate("window.__prompts || []")
        an=[x for x in pr if 'Выдели из проектной документации' in x]
        print('J7 run docs:', await pg.evaluate("__qa.S.run.docs.map(d => d.name)"), '| analyze prompts:', len(an), '| has rules.md:', any('rules' in x for x in an), '| doc tags:', sorted(set(n for x in an for n in re.findall(r'<document name="([^"]+)"', x))), '| KB block:', any('База знаний продукта' in x for x in an))
        tools=await pg.evaluate("""() => { const t = __qa.makeTools(__qa.S.run, 'generate'); const s = t.find(x => x.name === 'search_documents'); const r = t.find(x => x.name === 'read_document');
          let err = ''; try { r.execute({ document: 'Пример', offset: 0 }); } catch (e) { err = e.message; }
          return { names: t.map(x => x.name), searchSample: s.execute({ query: 'password-reset' }), readOther: err }; }""")
        print('J8 agent tools:', tools['names'], '| search outside run docs:', tools['searchSample'] if isinstance(tools['searchSample'], str) else [x['document'] for x in tools['searchSample']], '| read outside:', tools['readOther'][:80])
        # перезагрузка: список запуска сохраняется
        await pg.reload(); await pg.wait_for_timeout(3000)
        print('J9 after reload:', await state(pg))
        await pg.click('[data-mode=update]'); await pg.wait_for_timeout(300)
        print('J10 update mode:', await state(pg))
        await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(300)
        # «Новый запуск» очищает список, документы в продукте
        await pg.click('#btn-newses'); await pg.wait_for_timeout(800)
        print('J11 new run:', await state(pg), '| note:', await pg.inner_text('#docs-note'), '| run note:', await pg.inner_text('#run-note'))
        await pg.click('#docs-fold'); await pg.wait_for_timeout(200)
        print('J12 folded summary:', (await pg.inner_text('#docs-sum')).replace('\n', ' | '))
        await pg.click('#docs-fold'); await pg.wait_for_timeout(200)
        await pg.click('#docs-note [data-docs-act=kb]'); await pg.wait_for_timeout(300)
        print('J13 link to KB:', await state(pg))
        await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(300)
        await pg.screenshot(path=os.path.join(D,'v34_run_docs.png'))
        await b.close(); print('ERRORS:', errs or 'none')
asyncio.run(main())
