# База знаний: сворачиваемый список документов (по режимам, с перетаскиванием на свёрнутую панель)
# и разделы строками по алфавиту со сворачиванием, поиском и подсветкой.
import asyncio, os, json, time
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
EXTRA=[('Отчёты','Выгрузка отчётов по операциям'),('авторизация','Вход по логину и паролю'),('«Личный кабинет»','Главная страница клиента'),
       ('Ёлка-проверка','Проверка буквы Ё'),('Есть ли права','Роли и доступ'),('10 Настройки','Параметры системы'),('2 Профиль','Данные клиента'),('Zeta интеграция','Внешний сервис')]
async def rows(pg): return await pg.eval_on_selector_all('#kb-rows .kb-row-t', 'els => els.map(e => e.textContent)')
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script='window.__qaTest = true; window.__sampleDelay = 20;')
        for f in ('mockgen.js','mock_shared.js'): await ctx.add_init_script(path=os.path.join(D,f))
        await ctx.route('http://kb.test/**', serve)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://kb.test/'); await pg.wait_for_timeout(2500)
        await pg.evaluate('__qa.S.settings.kbAuto = false')
        await pg.click('[data-mode=help]'); await pg.wait_for_timeout(600)
        # разбор примера ТЗ → два раздела; второй документ не разобран
        await pg.click('[data-act=kb-run]'); await pg.wait_for_function('() => !__qa.S.kb.job.busy && __qa.S.kb.index.blocks.length >= 2', timeout=20000)
        await pg.set_input_files('#file-input', os.path.join(D,'rules.md')); await pg.wait_for_timeout(1500)
        print('K1 docs in KB mode:', await pg.eval_on_selector_all('#doc-list .doc', "els => els.map(e => ({name: e.querySelector('.doc-name').textContent, kb: e.querySelector('.kb-st')?.textContent || '', checkbox: !!e.querySelector('.doc-use')}))"))
        print('K1 note:', await pg.inner_text('#docs-note'))
        # разделы: добавляем ещё, проверяем алфавит и строки
        await pg.evaluate('(x) => { const ids = __qa.S.docs.map(d => d.id); for (const [t, s] of x) __qa.S.kb.index.blocks.push({ id: "kb" + Math.random().toString(36).slice(2, 8), title: t, summary: s, docIds: ids.slice(0, 1 + (t.length % 2)), size: 1200 + t.length * 37 }); }', EXTRA)
        await pg.click('#help-head [data-v=qa]'); await pg.click('#help-head [data-v=blocks]'); await pg.wait_for_timeout(300)
        r = await rows(pg)
        print('K2 rows (alphabetical):', r)
        import functools, locale
        print('K2 header:', (await pg.inner_text('.kb-list-h')).replace('\n',' '), '| cards left:', await pg.locator('.kb-card').count(), '| row height px:', await pg.evaluate("Math.round(document.querySelector('.kb-row').getBoundingClientRect().height)"))
        await pg.screenshot(path=os.path.join(D,'v28_kb_rows.png'), full_page=True)
        # поиск: фильтр, подсветка, счётчик
        await pg.fill('#kb-q', 'парол'); await pg.wait_for_timeout(300)
        print('K3 search:', await rows(pg), '| marks:', await pg.locator('#kb-rows mark').count(), '| header:', (await pg.inner_text('.kb-list-h')).replace('\n',' '))
        await pg.fill('#kb-q', ''); await pg.wait_for_timeout(200)
        # сворачивание разделов
        await pg.click('.kb-list-h .fold-btn'); await pg.wait_for_timeout(200)
        print('K4 folded:', await pg.get_attribute('.kb-list-h .fold-btn', 'aria-expanded'), '| rows:', await pg.locator('#kb-rows').count(), '| summary:', await pg.inner_text('.kb-list-sum'), '| stored:', await pg.evaluate("localStorage.getItem('qapro.kbFold')"))
        await pg.screenshot(path=os.path.join(D,'v28_kb_folded.png'))
        # открыть раздел из строки и вернуться
        await pg.click('.kb-list-sum .fold-sum'); await pg.wait_for_timeout(200)
        await pg.click('#kb-rows .kb-row:has-text("Восстановление пароля")'); await pg.wait_for_selector('.kb-art h3', timeout=10000)
        print('K5 opened:', (await pg.inner_text('.kb-art h3')), '| back →', end=' ')
        await pg.click('[data-act=kb-back]'); await pg.wait_for_timeout(300); print(len(await rows(pg)), 'rows')
        # клавиатура: Enter на заголовке сворачивает и возвращает фокус на него
        await pg.focus('.kb-list-h .fold-btn'); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(200)
        print('K6 keyboard fold:', await pg.get_attribute('.kb-list-h .fold-btn', 'aria-expanded'), '| focus on header:', await pg.evaluate("document.activeElement?.matches('.kb-list-h .fold-btn')"))
        # поиск разворачивает свёрнутый список
        await pg.fill('#kb-q', 'проф'); await pg.wait_for_timeout(300)
        print('K7 search unfolds:', await rows(pg), '| stored:', await pg.evaluate("localStorage.getItem('qapro.kbFold')"))
        await pg.fill('#kb-q', '')
        # список документов: сворачивание в режиме «База знаний»
        await pg.click('#docs-fold'); await pg.wait_for_timeout(200)
        print('D1 folded:', await pg.get_attribute('#docs-fold', 'aria-expanded'), '| body hidden:', await pg.evaluate("document.querySelector('#docs-body').hidden"), '| summary:', (await pg.inner_text('#docs-sum')).replace('\n',' | '), '| header:', (await pg.inner_text('#docs-fold')).replace('\n',' '))
        await pg.screenshot(path=os.path.join(D,'v28_docs_folded.png'))
        # в генерации — своё состояние: развёрнут, есть выбор «в запуск»
        await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(400)
        print('D2 generate mode:', await pg.get_attribute('#docs-fold', 'aria-expanded'), '| checkboxes:', await pg.locator('#doc-list .doc-use').count(), '| header:', (await pg.inner_text('#docs-fold')).replace('\n',' '))
        await pg.click('#docs-fold'); await pg.wait_for_timeout(200)
        print('D3 generate folded summary:', (await pg.inner_text('#docs-sum')).replace('\n',' | '))
        await pg.click('#docs-fold'); await pg.click('[data-mode=help]'); await pg.wait_for_timeout(400)
        print('D4 back in KB:', await pg.get_attribute('#docs-fold', 'aria-expanded'), '| stored:', await pg.evaluate("localStorage.getItem('qapro.docsFold')"))
        # перетаскивание файла на свёрнутую панель
        n0 = await pg.evaluate('__qa.S.docs.length')
        await pg.evaluate("""() => { const dt = new DataTransfer(); dt.items.add(new File(['# Лимиты\\nНе более 3 запросов за 15 минут.'], 'limits.md', { type: 'text/markdown' }));
          const t = document.querySelector('#docs-sum .fold-sum'); for (const type of ['dragenter', 'dragover', 'drop']) t.dispatchEvent(new DragEvent(type, { bubbles: true, cancelable: true, dataTransfer: dt })); }""")
        await pg.wait_for_timeout(1200)
        print('D5 dropped on folded panel:', n0, '->', await pg.evaluate('__qa.S.docs.length'), '| still folded:', await pg.get_attribute('#docs-fold', 'aria-expanded'), '| summary:', (await pg.inner_text('#docs-sum')).replace('\n',' | '))
        # «+» открывает выбор файлов
        async with pg.expect_file_chooser(timeout=3000) as fc: await pg.click('#docs-sum [data-docs-act=add]')
        print('D6 add button opens chooser:', (await fc.value).is_multiple())
        # после перезагрузки состояние сохраняется
        await pg.reload(); await pg.wait_for_timeout(2500)
        print('D7 after reload: docs', await pg.get_attribute('#docs-fold', 'aria-expanded'), '| sections', await pg.evaluate("document.querySelector('.kb-list-h .fold-btn')?.getAttribute('aria-expanded')"), '| mode', await pg.evaluate('__qa.S.settings.mode'))
        await pg.click('#docs-sum .fold-sum'); await pg.wait_for_timeout(200)
        print('D8 summary click expands:', await pg.get_attribute('#docs-fold', 'aria-expanded'), '| focus:', await pg.evaluate("document.activeElement?.id"))
        await pg.screenshot(path=os.path.join(D,'v28_kb_docs_open.png'), full_page=True)
        # телефон, тёмная тема
        m=await b.new_context(viewport={'width':400,'height':860}, color_scheme='dark')
        await m.expose_binding('__dbop', dbop)
        await m.add_init_script(script='window.__qaTest = true;')
        for f in ('mockgen.js','mock_shared.js'): await m.add_init_script(path=os.path.join(D,f))
        await m.route('http://kb.test/**', serve)
        pm=await m.new_page(); pm.on('pageerror', lambda e: errs.append('M '+str(e)))
        await pm.goto('http://kb.test/'); await pm.wait_for_timeout(2500)
        await pm.click('[data-mode=help]'); await pm.wait_for_timeout(500)
        await pm.evaluate('(x) => { const ids = __qa.S.docs.map(d => d.id); for (const [t, s] of x) __qa.S.kb.index.blocks.push({ id: "m" + Math.random().toString(36).slice(2, 8), title: t, summary: s, docIds: ids, size: 2400 }); __qa.S.kb.loaded = true; }', EXTRA)
        await pm.click('#help-head [data-v=qa]'); await pm.click('#help-head [data-v=blocks]'); await pm.wait_for_timeout(300)
        print('M1 mobile rows:', len(await rows(pm)), '| page overflow-x:', await pm.evaluate('document.documentElement.scrollWidth > innerWidth'))
        await pm.evaluate("document.querySelector('.kb-list-h').scrollIntoView()"); await pm.screenshot(path=os.path.join(D,'v28_kb_mobile.png'))
        await m.close()
        await b.close()
        print('ERRORS:', errs or 'none')
asyncio.run(main())
