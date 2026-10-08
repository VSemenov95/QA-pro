import asyncio, os
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
CHK = """() => { const P = window.__prompts; const gen = P.filter(p => p.includes('Напиши тест-кейсы'));
  const ui = gen.find(p => p.includes('вида UI')), api = gen.find(p => p.includes('вида API')), e2e = gen.find(p => p.includes('вида E2E'));
  const an = P.find(p => p.includes('Выдели из проектной'));
  const cl = P.find(p => p.includes('Составь чек-лист'));
  return { uiHasUI: !!ui && ui.includes('Для UI-тестов') && ui.includes('экране «Профиль»'), uiHasAll: !!ui && ui.includes('Для всех видов тестов'),
    apiHasUI: !!api && api.includes('Для UI-тестов'), apiHasAll: !!api && api.includes('Для всех видов тестов'),
    e2eHasCtx: !!e2e && e2e.includes('Дополнительный контекст от QA'),
    analyze: !!an && an.includes('Контекст QA'), checklistBoth: !!cl && cl.includes('Для UI-тестов') && cl.includes('Для всех видов') }; }"""
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); errs=[]
        ctx=await b.new_context(viewport={'width':1360,'height':900})
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock.js'))
        await ctx.route('**/*', route)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://app.test/'); await pg.wait_for_timeout(700)
        print('NOTE empty:', await pg.inner_text('#qa-ctx-note'))
        await pg.fill('#qa-ctx', 'Окружение stage, роль Оператор')
        await pg.click('[data-ctx=ui]'); await pg.fill('#qa-ctx', 'Проверки на экране «Профиль». Перейти: Главная → Настройки → Профиль')
        print('TABS:', (await pg.inner_text('#qa-ctx-tabs')).replace('\n',' '), '| NOTE:', await pg.inner_text('#qa-ctx-note'))
        await pg.locator('#qa-ctx-box').screenshot(path=os.path.join(D,'v6_ctx.png'))
        await pg.click('#btn-run'); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=30000)
        print('CHECK:', await pg.evaluate(CHK))
        print('PARSE LOG:', [l for l in ((await pg.click('#tab-agent'), await pg.inner_text('.timeline'))[1]).split('\n') if 'контекст' in l.lower()])
        await pg.click('[data-ctx=all]'); await pg.fill('#qa-ctx', ''); await pg.click('[data-ctx=ui]'); await pg.fill('#qa-ctx', '')
        await pg.evaluate('window.__prompts = []'); await pg.click('#btn-run'); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=30000)
        print('EMPTY: any ctx in prompts:', await pg.evaluate("window.__prompts.some(p => p.includes('Дополнительный контекст от QA'))"))
        print('PARSE LOG empty:', [l for l in ((await pg.click('#tab-agent'), await pg.inner_text('.timeline'))[1]).split('\n') if 'контекст' in l.lower()])
        await ctx.close()
        # standalone persistence
        ctx=await b.new_context(); await ctx.route('**/*', route)
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://local.test/'); await pg.wait_for_timeout(500)
        await pg.click('[data-ctx=api]'); await pg.fill('#qa-ctx', 'Базовый URL https://stage/api'); await pg.wait_for_timeout(1200)
        await pg.reload(); await pg.wait_for_timeout(900)
        await pg.click('[data-ctx=api]')
        print('AFTER RELOAD api ctx:', await pg.input_value('#qa-ctx'), '| tabs:', (await pg.inner_text('#qa-ctx-tabs')).replace('\n',' '))
        await ctx.close()
        print('ERRORS', errs); await b.close()
asyncio.run(main())
