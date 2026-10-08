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
    async with async_playwright() as p:
        errs=[]
        cb=await p.chromium.launch_persistent_context(tempfile.mkdtemp(), channel='chromium', headless=True, viewport={'width':1360,'height':900},
            args=[f'--disable-extensions-except={ext}', f'--load-extension={ext}'])
        sw = cb.service_workers[0] if cb.service_workers else await cb.wait_for_event('serviceworker')
        ext_id = sw.url.split('/')[2]
        await cb.expose_binding('__dbop', dbop); await cb.add_init_script(path=os.path.join(D,'mockgen.js')); await cb.add_init_script(path=os.path.join(D,'mock_shared.js'))
        await cb.route('https://claude.ai/artifact/**', serve)
        op=await cb.new_page(); await op.goto(f'chrome-extension://{ext_id}/options.html'); await op.wait_for_timeout(500)
        print('K0 url field:', await op.input_value('#qa-url'), '| keep:', await op.is_checked('#keep'))
        await op.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)"); await op.check('#keep'); await op.wait_for_timeout(4000)
        print('K1 note:', await op.inner_text('#keep-note'))
        tabs = await sw.evaluate("chrome.tabs.query({}).then(ts => ts.map(t => ({url: t.url || t.pendingUrl, pinned: t.pinned, active: t.active, autoDiscardable: t.autoDiscardable})))")
        print('K2 tabs:', [t for t in tabs if 'claude.ai' in (t.get('url') or t.get('pendingUrl') or '')], len(tabs))
        await sw.evaluate("ensureQaProTab()"); await op.wait_for_timeout(500)
        tabs = await sw.evaluate("chrome.tabs.query({}).then(ts => ts.filter(t => (t.url || t.pendingUrl || '').includes('claude.ai')).length)")
        print('K3 no duplicate:', tabs)
        await op.wait_for_timeout(3000)
        qp=[pg for pg in cb.pages if 'claude.ai' in pg.url]
        if qp:
            print('K4 page:', qp[0].url, '| title:', await qp[0].title(), '| has __dbop:', await qp[0].evaluate("typeof window.__dbop"), '| bridge:', await qp[0].evaluate("new Promise(r => { const id='t1'; window.addEventListener('message', e => { if (e.data?.id===id && e.data.type==='SFERA_PONG') r('pong') }); window.postMessage({source:'qa-pro', id, type:'SFERA_PING'}, '*'); setTimeout(() => r('none'), 3000); })"))
        await op.screenshot(path=os.path.join(D,'v23_options.png'), full_page=True)
        await cb.close()
asyncio.run(main())
