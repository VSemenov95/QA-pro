# Сквозная проверка загрузчика: QA pro (автономная, http) → мост → окно расширения → мок API Сферы
import asyncio, os, json, threading, shutil, tempfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
EXT_SRC=os.path.join(ROOT,'uploader','qa-pro-sfera-uploader')
STANDALONE=open(os.path.join(ROOT,'qa-pro.html'),'rb').read()
import time
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


html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
SKEL='<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>[hidden]{display:none!important}body{margin:0}</style></head><body>'+html+'</body></html>'
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
async def serve(r): await r.fulfill(body=SKEL, content_type='text/html; charset=utf-8')
jobs=lambda: sorted(k for k in STORE if '/sfjob-' in k)
async def main():
    ext=tempfile.mkdtemp(); shutil.copytree(EXT_SRC, ext, dirs_exist_ok=True)
    m=json.load(open(os.path.join(ext,'manifest.json'),encoding='utf-8'))
    m['host_permissions'] += ['http://127.0.0.1/*','http://app.test/*']; m['content_scripts'][0]['matches'].append('http://app.test/*')
    json.dump(m,open(os.path.join(ext,'manifest.json'),'w',encoding='utf-8'),ensure_ascii=False)
    async with async_playwright() as p:
        errs=[]
        # «Chrome» с загрузчиком: QA pro во вкладке + Сфера
        cb=await p.chromium.launch_persistent_context(tempfile.mkdtemp(), channel='chromium', headless=True, viewport={'width':1360,'height':900},
            args=[f'--disable-extensions-except={ext}', f'--load-extension={ext}'])
        sw = cb.service_workers[0] if cb.service_workers else await cb.wait_for_event('serviceworker')
        await sw.evaluate(f"chrome.storage.local.set({{settings:{{baseUrl:'{BASE}'}}}})")
        await cb.add_cookies([{'name':'ACCESS_TOKEN','value':'tok-123','url':BASE}])
        await cb.expose_binding('__dbop', dbop); await cb.add_init_script(path=os.path.join(D,'mockgen.js')); await cb.add_init_script(path=os.path.join(D,'mock_shared.js'))
        await cb.route('http://app.test/**', serve)
        sf=await cb.new_page(); await sf.goto(BASE+'/project/PPAN?section=124')
        pb=await cb.new_page(); pb.on('pageerror', lambda e: errs.append('B '+str(e)))
        await pb.goto('http://app.test/'); await pb.wait_for_timeout(3000)
        print('R0 presence:', {k:v for k,v in STORE.items() if k.endswith('/sfera-relay')})
        # «Приложение Claude»: отдельный браузер без расширений, UA Electron
        b2=await p.chromium.launch()
        ca=await b2.new_context(viewport={'width':1360,'height':900}, user_agent='Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Claude/1.0.0 Chrome/138.0.0.0 Electron/37.2.0 Safari/537.36')
        await ca.expose_binding('__dbop', dbop); await ca.add_init_script(path=os.path.join(D,'mockgen.js')); await ca.add_init_script(path=os.path.join(D,'mock_shared.js'))
        await ca.route('http://desk.test/**', serve)
        pa=await ca.new_page(); pa.on('pageerror', lambda e: errs.append('A '+str(e)))
        await pa.goto('http://desk.test/'); await pa.wait_for_timeout(2500)
        await pa.click('#btn-run'); await pa.wait_for_selector('#btn-run:not([hidden])', timeout=40000); await pa.wait_for_timeout(800)
        await pa.click('#tab-cases'); await pa.wait_for_timeout(2500)
        print('A1 bar:', (await pa.inner_text('#tms-bar')).replace('\n',' | ')[:220])
        await pa.click('#btn-settings'); await pa.click('#settab-tms'); await pa.wait_for_timeout(1500)
        print('A2 banner:', (await pa.inner_text('#tms-body .banner')).replace('\n',' | ')[:600])
        await pa.screenshot(path=os.path.join(D,'v23_desktop_tms.png'))
        await pa.click('[data-tmb=test]'); await pa.wait_for_timeout(2500)
        print('A3 test:', await pa.inner_text('#tms-body .case-note'))
        await pa.click('#set-close') if await pa.locator('#set-close').count() else await pa.keyboard.press('Escape')
        await pa.wait_for_timeout(300)
        # загрузка: задание → вкладка Chrome → окно загрузчика
        async with cb.expect_page(timeout=20000) as pi:
            await pa.click('[data-act=tms-upload]')
        up = await pi.value; await up.wait_for_load_state(); await up.wait_for_timeout(800)
        print('A4 desk log:', await pa.inner_text('#tms-bar .log'))
        print('A4 window source:', await up.inner_text('#source'), '| rows', await up.locator('#rows tr').count())
        print('A4 job:', [(k.split('/')[-1], STORE[k].get('status')) for k in jobs() if k.count('/')==3])
        await up.click('#from-tab'); await up.wait_for_timeout(600); await up.click('#go'); await up.wait_for_timeout(2500)
        print('A5 summary:', await up.inner_text('#summary'))
        await pa.wait_for_timeout(1500)
        print('A6 desk log:', await pa.inner_text('#tms-bar .log'))
        CASES = "() => [...document.querySelectorAll('#case-list article')].map(a => a.querySelector('.case-id').textContent + ' ' + [...a.querySelectorAll('.case-sub .chip')].map(c => c.textContent).filter(t => /в тмс/i.test(t)).join(','))"
        print('A6 desk marks:', await pa.evaluate(CASES))
        print('A6 posts:', len(POSTS), [b['labels'] for b in POSTS], '| regr', [b['ti_regressive'] for b in POSTS])
        print('A6 jobs left:', jobs())
        print('A6 chrome tab log:', await pb.evaluate("document.querySelector('#tms-bar .log')?.innerText || '(нет)'"))
        await up.close()
        # отмена в окне загрузчика
        (await pa.locator('#tms-reup').count()) and await pa.check('#tms-reup'); await pa.wait_for_timeout(100)
        async with cb.expect_page(timeout=20000) as pi:
            await pa.click('[data-act=tms-upload]')
        up2 = await pi.value; await up2.wait_for_load_state(); await up2.wait_for_timeout(500); await up2.close(); await pa.wait_for_timeout(2000)
        print('A7 after close:', await pa.inner_text('#tms-bar .log'), '| jobs', jobs())
        # Chrome не открыт: задание ждёт, после перезагрузки приложения подхватывается
        await pb.close(); STORE.pop([k for k in STORE if k.endswith('/sfera-relay')][0], None)
        (await pa.locator('#tms-reup').count()) and await pa.check('#tms-reup'); await pa.wait_for_timeout(100)
        await pa.click('[data-act=tms-upload]'); await pa.wait_for_timeout(1500)
        print('A8 waiting:', (await pa.inner_text('#tms-bar')).replace('\n',' | ')[:400])
        await pa.screenshot(path=os.path.join(D,'v23_desktop_wait.png'))
        await pa.reload(); await pa.wait_for_timeout(2500)
        await pa.click('#tab-cases'); await pa.wait_for_timeout(1500)
        print('A9 after reload:', await pa.evaluate("document.querySelector('#tms-bar .log')?.innerText || '(нет лога)'"), '| jobs', [(k.split('/')[-1], STORE[k].get('status')) for k in jobs() if k.count('/')==3])
        n0=len(POSTS)
        pb2=await cb.new_page(); pb2.on('pageerror', lambda e: errs.append('B2 '+str(e)))
        async with cb.expect_page(timeout=25000) as pi:
            await pb2.goto('http://app.test/')
        up3 = await pi.value; await up3.wait_for_load_state(); await up3.wait_for_timeout(800)
        await up3.click('#from-tab'); await up3.wait_for_timeout(600); await up3.click('#go'); await up3.wait_for_timeout(2500)
        await pa.wait_for_timeout(1500)
        print('A10 after Chrome opened:', await pa.inner_text('#tms-bar .log'), '| new posts', len(POSTS)-n0, '| jobs', jobs())
        # отмена ожидания отправителем
        await pb2.close(); STORE.pop([k for k in STORE if k.endswith('/sfera-relay')][0], None)
        (await pa.locator('#tms-reup').count()) and await pa.check('#tms-reup'); await pa.click('[data-act=tms-upload]'); await pa.wait_for_timeout(1200)
        await pa.click('[data-act=tms-stop]'); await pa.wait_for_timeout(1200)
        print('A11 cancel:', await pa.inner_text('#tms-bar .log'), '| jobs', jobs())
        print('ERRORS', errs)
        await b2.close(); await cb.close()
asyncio.run(main())
