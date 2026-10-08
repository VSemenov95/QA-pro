# Сквозная проверка загрузчика: QA pro (автономная, http) → мост → окно расширения → мок API Сферы
import asyncio, os, json, threading, shutil, tempfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
EXT_SRC=os.path.join(ROOT,'uploader','qa-pro-sfera-uploader')
STANDALONE=open(os.path.join(ROOT,'qa-pro.html'),'rb').read()
POSTS=[]; AUTH=[]
class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def _json(self, o, code=200):
        b=json.dumps(o).encode(); self.send_response(code); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u=urlparse(self.path); q=parse_qs(u.query)
        if u.path=='/qa-pro.html':
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write(STANDALONE); return
        if u.path.startswith('/project/'):
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write('<title>Сфера ФТ · PPAN</title><h1>Сфера</h1>'.encode()); return
        AUTH.append(self.headers.get('Authorization'))
        if u.path=='/app/testing/api/v1/attributes':
            cat=q.get('categories',[''])[0]
            if cat=='TEST_CASE_STATUS': return self._json({'content':[{'objectType':'TEST_CASE','values':[{'id':'st-new','code':'new'},{'id':'st-created','code':'created'}]}]})
            return self._json({'content':[{'code':'ti_status','objectType':'TEST_CASE','values':[{'id':'tis-def','isDefault':True}]},{'code':'ti_priority','objectType':'TEST_CASE','values':[{'id':'tip-def','isDefault':True}]}]})
        if u.path=='/app/testing/api/v1/projects/PPAN/sections':
            return self._json([{'id':123,'name':'Личный кабинет','parentSectionId':None,'ownElementsCount':0},{'id':124,'name':'Восстановление пароля','parentSectionId':123,'ownElementsCount':3}])
        self._json({'error':'not found'},404)
    def do_POST(self):
        n=int(self.headers.get('Content-Length','0')); body=json.loads(self.rfile.read(n) or b'{}')
        AUTH.append(self.headers.get('Authorization'))
        if self.path=='/app/testing/api/v1/test-issues':
            POSTS.append(body)
            if 'сбой' in body.get('name',''): return self._json({'message':'bad'},400)
            return self._json({'testIssueCode':f'PPAN-T{len(POSTS)}'})
        self._json({},404)
srv=ThreadingHTTPServer(('127.0.0.1',0),H); PORT=srv.server_address[1]; BASE=f'http://127.0.0.1:{PORT}'
threading.Thread(target=srv.serve_forever,daemon=True).start()


async def main():
    ext=tempfile.mkdtemp(); shutil.copytree(EXT_SRC, ext, dirs_exist_ok=True)
    m=json.load(open(os.path.join(ext,'manifest.json'),encoding='utf-8'))
    m['host_permissions'] += ['http://127.0.0.1/*', 'https://*/*']   # в тесте считаем, что разрешение «любые сайты» уже выдано
    json.dump(m,open(os.path.join(ext,'manifest.json'),'w',encoding='utf-8'),ensure_ascii=False)
    async with async_playwright() as p:
        errs=[]
        ctx=await p.chromium.launch_persistent_context(tempfile.mkdtemp(), channel='chromium', headless=True, viewport={'width':1360,'height':900},
            args=[f'--disable-extensions-except={ext}', f'--load-extension={ext}'])
        sw = ctx.service_workers[0] if ctx.service_workers else await ctx.wait_for_event('serviceworker')
        ext_id = sw.url.split('/')[2]
        await sw.evaluate(f"chrome.storage.local.set({{settings:{{baseUrl:'{BASE}'}}}})")
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock_ext.js'))
        # QA pro на «чужом» https-адресе, которого нет в списке расширения
        await ctx.route('https://qa-pro.example/**', lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=STANDALONE))
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append('PAGE '+str(e)))
        await pg.goto('https://qa-pro.example/qa-pro.html'); await pg.wait_for_timeout(1000)
        await pg.click('#btn-settings'); await pg.click('#settab-tms'); await pg.wait_for_timeout(2200)
        print('D1 banner:', (await pg.inner_text('#tms-body .banner')).replace('\n',' | ')[:400])
        await pg.screenshot(path=os.path.join(D,'v22_diag.png'))
        await pg.click('[data-tmb=test]'); await pg.wait_for_timeout(2200)
        print('D2 test:', await pg.inner_text('#tms-body .case-note'))
        # включаем «любые сайты» в загрузчике — без перезагрузки страницы
        n = await sw.evaluate("saveSettings({anySite:true}).then(() => syncAnySite(true)).then(() => injectOpenTabs())")
        print('D3 injected tabs:', n)
        await pg.click('[data-tmb=test]'); await pg.wait_for_timeout(1500)
        print('D4 test:', await pg.inner_text('#tms-body .case-note'), '| banner:', (await pg.inner_text('#tms-body .banner'))[:80])
        # после перезагрузки мост подключается сам (зарегистрирован динамически)
        await pg.reload(); await pg.wait_for_timeout(1000)
        await pg.click('#btn-settings'); await pg.click('#settab-tms'); await pg.wait_for_timeout(1500)
        print('D5 after reload:', (await pg.inner_text('#tms-body .banner'))[:80])
        # настройки загрузчика: журнал обращений
        op=await ctx.new_page(); await op.goto(f'chrome-extension://{ext_id}/options.html'); await op.wait_for_timeout(600)
        print('D6 options any:', await op.is_checked('#any'), '| pings:', (await op.inner_text('#pings')).replace('\n',' | ')[:300])
        await op.screenshot(path=os.path.join(D,'v22_options.png'), full_page=True)
        # окружение, которое глушит входящие postMessage для страницы: ответы должны прийти событием документа
        pg2=await ctx.new_page(); pg2.on('pageerror', lambda e: errs.append('PAGE2 '+str(e)))
        await pg2.add_init_script(script="""(() => { const orig = EventTarget.prototype.addEventListener;
          EventTarget.prototype.addEventListener = function (type, fn, opts) {
            if (this === window && type === 'message') { const f = fn; fn = function (e) { if (e.data && e.data.source === 'qa-pro-sfera-uploader') return; return f.call(this, e); }; }
            return orig.call(this, type, fn, opts); }; })();""")
        await pg2.goto(BASE+'/qa-pro.html'); await pg2.wait_for_timeout(1000)
        await pg2.click('#btn-settings'); await pg2.click('#settab-tms'); await pg2.wait_for_timeout(300)
        await pg2.click('[data-tmb=test]'); await pg2.wait_for_timeout(1500)
        print('D7 filtered postMessage, test:', await pg2.inner_text('#tms-body .case-note'))
        print('ERRORS', errs)
        await ctx.close()
asyncio.run(main())
