# «Сократить количество тестов»: выбор набора (покрытие требований, ровно N кейсов) и предупреждение при невозможном покрытии.
import asyncio, os, json
from playwright.async_api import async_playwright
from run27 import dbop, serve, D
UNIT = """() => {
  const C = (id, reqs, prio) => ({ dispId: id, requirementIds: reqs, testCase: { priority: prio }, type: 'api' });
  const cases = [C('A', ['R1', 'R2'], 'High'), C('B', ['R1'], 'Medium'), C('C', ['R2'], 'Low'), C('D', ['R3'], 'High'), C('E', ['R3'], 'Low')];
  const covered = (ids) => new Set(cases.filter((c) => ids.includes(c.dispId)).flatMap((c) => c.requirementIds));
  const out = {};
  for (const [name, keep, t] of [['t3', ['A', 'B', 'C'], 3], ['t2', [], 2], ['model_bad', ['B', 'C'], 2], ['t1', [], 1]]) {
    const r = __qa.reduceSelect(cases, keep, t);
    out[name] = { warn: !!r.warn, error: r.error || null, n: (r.keep || []).length, covers: r.keep ? covered(r.keep).size === 3 : null, min: r.min ?? null, uncovered: r.uncovered ?? null };
  }
  return out;
}"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(); errs = []
        ctx = await b.new_context(viewport={'width': 1360, 'height': 900})
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script='window.__qaTest = true;')
        for f in ('mockgen.js', 'mock_shared.js'): await ctx.add_init_script(path=os.path.join(D, f))
        await ctx.route('http://localhost/**', serve)
        pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost/'); await pg.wait_for_timeout(2000)
        print('U unit:', json.dumps(await pg.evaluate(UNIT), ensure_ascii=False))
        await pg.click('[data-mode=generate]'); await pg.wait_for_timeout(300)
        await pg.set_input_files('#file-input', '/tmp/claude-0/-home-claude/7234b2d8-b9b5-5dab-b74e-1b755a5e008b/scratchpad/spec.txt'); await pg.wait_for_timeout(1500)
        await pg.click('#btn-run')
        await pg.wait_for_timeout(500); await pg.wait_for_function("() => !__qa.S.running", timeout=90000); await pg.wait_for_timeout(600)
        n0 = await pg.evaluate('__qa.S.run.cases.length')
        print('S1 cases before:', n0, '| reduce button visible:', await pg.evaluate("!document.querySelector('#btn-reduce').hidden"))
        await pg.click('#btn-reduce'); await pg.wait_for_timeout(200)
        print('S2 form visible, default value:', await pg.evaluate("[!document.querySelector('#reduce-form').hidden, document.querySelector('#reduce-n').value]"))
        await pg.fill('#reduce-n', str(n0 + 3)); await pg.click('#reduce-go'); await pg.wait_for_timeout(300)
        print('S3 invalid hint:', await pg.inner_text('#reduce-hint'))
        await pg.fill('#reduce-n', '2'); await pg.click('#reduce-go')
        await pg.wait_for_function("() => !document.querySelector('#reduce-go').disabled", timeout=90000); await pg.wait_for_timeout(400)
        n1 = await pg.evaluate('__qa.S.run.cases.length')
        print('S4 after reduce to 2:', n1, '| form hidden:', await pg.evaluate("document.querySelector('#reduce-form').hidden"), '| hint:', await pg.inner_text('#reduce-hint'))
        print('S5 button label:', await pg.inner_text('#reduce-go'))
        await pg.click('#reduce-go')
        await pg.wait_for_function("() => !document.querySelector('#reduce-go').disabled", timeout=90000); await pg.wait_for_timeout(400)
        n2 = await pg.evaluate('__qa.S.run.cases.length')
        print('S6 after confirm:', n2, '| form hidden:', await pg.evaluate("document.querySelector('#reduce-form').hidden"), '| label:', await pg.inner_text('#reduce-go'))
        print('ERRORS:', errs or 'none')
        await b.close()
asyncio.run(main())
