# Тест-кейсы продукта по документам: после загрузки продукта они видны на вкладке «Тест-кейсы», разделы можно переименовать.
import asyncio, os, json, tempfile
from playwright.async_api import async_playwright
from run27 import dbop, serve, D
TMP = tempfile.mkdtemp(prefix='qa-run44-')
def mkrun(rid, doc, cases, reqs):
    meta = dict(id=rid, kind='run', status='done', stage='added', createdAt=1700000000000, finishedAt=1700000100000, partsCount=1, srcParts=0, docs=[dict(id='d-' + rid, name=doc)],
                requirements=reqs, questions=[], plan=[], settings=dict(types=['api', 'ui', 'e2e']), counters=dict(api=0, ui=0, e2e=0, cl=0), mode='generate', by='local', updatedAt=1700000100000)
    return dict(meta=meta, parts=[dict(cases=cases)], src=[])
def case(uid, ty, did, title, reqs):
    return dict(uid=uid, type=ty, planItem='P-01', requirementIds=reqs, suites=['regression'], dispId=did, testCase={'id': did, 'title': title, 'priority': 'High', 'steps': [{'step': 1, 'action': 'a', 'expected': 'b'}]})
req = lambda i, doc: dict(id=i, title='Требование ' + i, description='d', criteria=[], types=['ui'], priority='High', doc=doc, section='1', quote='', inScope=True)
r1 = mkrun('run_a', 'ТЗ-Авторизация.docx', [case('u1', 'ui', 'UI-001', '[FE] Вход с верным паролем', ['R-001']), case('u2', 'api', 'API-001', '[BE] POST /login — успех', ['R-001']), case('u3', 'ui', 'UI-002', '[FE] Вход без пароля', ['R-002'])], [req('R-001', 'ТЗ-Авторизация.docx'), req('R-002', 'ТЗ-Авторизация.docx')])
r2 = mkrun('run_b', 'ТЗ-Платежи.md', [case('u4', 'api', 'API-002', '[BE] POST /pay — оплата картой', ['R-001']), case('u5', 'ui', 'UI-003', '[FE] Оплата: ошибка карты', ['R-001']), case('u6', 'e2e', 'E2E-001', '[E2E] Покупка от корзины до чека', ['R-001', 'R-002']), case('u7', 'ui', 'UI-004', 'Ручной кейс без требований', [])], [req('R-001', 'ТЗ-Платежи.md'), req('R-002', 'ТЗ-Платежи.md')])
idx = [dict(r='run_a', i='UI-001', t='ui', n='[FE] Вход с верным паролем'), dict(r='run_a', i='API-001', t='api', n='[BE] POST /login — успех'), dict(r='run_a', i='UI-002', t='ui', n='[FE] Вход без пароля'),
       dict(r='run_b', i='API-002', t='api', n='[BE] POST /pay — оплата картой'), dict(r='run_b', i='UI-003', t='ui', n='[FE] Оплата: ошибка карты'), dict(r='run_b', i='E2E-001', t='e2e', n='[E2E] Покупка от корзины до чека'), dict(r='run_b', i='UI-004', t='ui', n='Ручной кейс без требований')]
EXP = dict(format='qa-pro-product', version=1, exportedAt='2026-10-12T00:00:00Z', product=dict(name='Магазин', description='', qaCtx={}, passport=None, passportPrev=None, counters=dict(api=2, ui=4, e2e=1, cl=0), stats=dict(cases=7, checklist=0, lastRunAt=1700000100000), createdAt=1700000000000),
           docs=[], index=dict(cases=idx, checklist=[]), known=None, runs=[r1, r2], kb=dict(index=None, blocks=[]))
SECS = "() => [...document.querySelectorAll('#pcase-list .sec, #case-list .sec')].map(s => [s.querySelector('.sec-t')?.innerText, s.querySelectorAll('.case').length])"
bad = 0
def check(name, ok, detail=''):
    global bad; bad += 0 if ok else 1; print(('OK   ' if ok else 'FAIL ') + name, '|', str(detail)[:200])
async def main():
    path = os.path.join(TMP, 'shop.json'); json.dump(EXP, open(path, 'w', encoding='utf-8'), ensure_ascii=False)
    async with async_playwright() as p:
        b = await p.chromium.launch(); errs = []
        ctx = await b.new_context(viewport={'width': 1360, 'height': 900}, accept_downloads=True)
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script='window.__qaTest = true;')
        for f in ('mockgen.js', 'mock_shared.js'): await ctx.add_init_script(path=os.path.join(D, f))
        await ctx.route('http://sec.test/**', serve)
        pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://sec.test/'); await pg.wait_for_timeout(2500)
        await pg.set_input_files('#prod-import-file', path); await pg.wait_for_selector('#pcase-list .sec', timeout=20000); await pg.wait_for_timeout(500)
        check('G1 после загрузки продукта открыта вкладка «Тест-кейсы»', await pg.evaluate("() => __qa.S.tab") == 'cases')
        s = await pg.evaluate(SECS); check('G2 разделы по документам', s == [['ТЗ-Авторизация', 3], ['ТЗ-Платежи', 3], ['Без документа', 1]], s)
        await pg.click('[data-act=pc-type][data-t=api]'); await pg.wait_for_timeout(200)
        s = await pg.evaluate(SECS); check('G3 фильтр по виду', s == [['ТЗ-Авторизация', 1], ['ТЗ-Платежи', 1]], s)
        await pg.click('[data-act=pc-type][data-t=all]')
        await pg.click('#pcase-list .sec:nth-child(2) [data-act=sec-rename]'); await pg.fill('#sec-in', '  Оплата   и возвраты '); await pg.keyboard.press('Enter'); await pg.wait_for_timeout(500)
        s = await pg.evaluate(SECS); check('G4 название раздела изменено вручную', s[1] == ['Оплата и возвраты', 3], s)
        await pg.click('#pcase-list .sec:nth-child(1) [data-act=sec-rename]'); await pg.keyboard.press('Escape'); await pg.wait_for_timeout(200)
        check('G5 Esc отменяет переименование', await pg.evaluate("() => !document.querySelector('#sec-in')"))
        await pg.reload(); await pg.wait_for_timeout(3000); await pg.click('#tab-cases'); await pg.wait_for_selector('#pcase-list .sec', timeout=20000)
        s = await pg.evaluate(SECS); check('G6 название сохранилось после перезагрузки', [x[0] for x in s] == ['ТЗ-Авторизация', 'Оплата и возвраты', 'Без документа'], s)
        await pg.click('#pcase-list [data-i=E2E-001]'); await pg.wait_for_selector('#case-list .sec', timeout=20000); await pg.wait_for_timeout(500)
        st = await pg.evaluate("() => ({ tab: __qa.S.tab, run: __qa.S.run?.id, open: document.querySelectorAll('.case-b').length })")
        check('G7 клик по кейсу открывает запуск и кейс', st == {'tab': 'cases', 'run': 'run_b', 'open': 1}, st)
        s = await pg.evaluate(SECS); check('G8 в запуске кейсы по разделам', s == [['Оплата и возвраты', 3], ['Без документа', 1]], s)
        sw = await pg.evaluate("() => [...document.querySelectorAll('.scope-sw .fchip')].map(b => b.innerText.replace(/\\s+/g, ' '))"); check('G9 переключатель области', sw == ['Этот запуск 4', 'Весь продукт 7'], sw)
        await pg.click('[data-act=cases-scope][data-s=product]'); await pg.wait_for_selector('#pcase-list .sec'); await pg.wait_for_timeout(500)
        s = await pg.evaluate(SECS); check('G10 весь продукт', [x[0] for x in s] == ['ТЗ-Авторизация', 'Оплата и возвраты', 'Без документа'], s)
        await pg.click('[data-act=prod-export]'); await pg.wait_for_timeout(2500)
        data = await pg.evaluate('window.__dlData'); out = json.loads(data)
        check('G11 экспорт продукта содержит названия разделов', list((out['product'].get('caseSections') or {}).values()) == ['Оплата и возвраты'], out['product'].get('caseSections'))
        path2 = os.path.join(TMP, 'shop2.json'); open(path2, 'w', encoding='utf-8').write(data)
        await pg.set_input_files('#prod-import-file', path2); await pg.wait_for_selector('#pcase-list .sec', timeout=20000); await pg.wait_for_timeout(800)
        s = await pg.evaluate(SECS); check('G12 копия продукта: кейсы и названия разделов на месте', s == [['ТЗ-Авторизация', 3], ['Оплата и возвраты', 3], ['Без документа', 1]], s)
        print('ERRORS:', errs or 'none'); await b.close()
    print('FAILED:', bad)
asyncio.run(main())
