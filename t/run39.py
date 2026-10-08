import asyncio, os, sys, json
sys.path.insert(0, '/tmp/claude-0/-home-claude/7234b2d8-b9b5-5dab-b74e-1b755a5e008b/scratchpad/t')
from run27 import dbop, serve, D
from playwright.async_api import async_playwright
TC = {
  'title': 'Вход',
  'preconditions': ['<p>Пользователь user@example.ru зарегистрирован</p>', '<p>Открыта страница /login\\nПользователь не авторизован</p>', 'Тестовый пользователь\\r\\nактивен'],
  'postconditions': '<p>Сессия создана</p>\\n<p>Лог записан</p>',
  'steps': [{'n': 1, 'action': '<p>Ввести логин</p>', 'expected': '&lt;p&gt;Поле видно&lt;/p&gt;', 'data': ''}],
  'description': 'Проверка <b>входа</b>',
}
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(); ctx=await b.new_context()
        await ctx.expose_binding('__dbop', dbop); await ctx.add_init_script(script="window.__qaTest = true;")
        for f in ('mockgen.js','mock_shared.js'): await ctx.add_init_script(path=os.path.join(D,f))
        await ctx.route('http://kb2.test/**', serve)
        pg=await ctx.new_page(); errs=[]; pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://kb2.test/'); await pg.wait_for_timeout(1500)
        r=await pg.evaluate("(tc) => { const c = {uid:'x', type: 'api', testCase: tc, suites: [], requirementIds: []}; const t = __qa.tmsCase(c); return { clean: __qa.cleanCase(tc), tms: { pre: t.pre, post: t.post, steps: t.steps, description: t.description } }; }", TC)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        print('errors', errs)
        await b.close()
asyncio.run(main())
