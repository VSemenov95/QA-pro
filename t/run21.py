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


import subprocess, itertools
html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
SKEL='<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>[hidden]{display:none!important}body{margin:0}</style></head><body>'+html+'</body></html>'
async def serve(r): await r.fulfill(body=SKEL, content_type='text/html; charset=utf-8')
BPORT = 47600 + os.getpid() % 300
BDIR = tempfile.mkdtemp()
import time
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
async def core_shutdown():
    import urllib.request
    try:
        tok=open(os.path.join(BDIR,'token')).read().strip()
        urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{BPORT}/shutdown', data=b'{}', headers={'x-qa-pro-bridge-token': tok}, method='POST'), timeout=2).read()
    except Exception as e: print('   core shutdown:', e)
class Bridge:
    async def start(self):
        self.p = await asyncio.create_subprocess_exec('node', os.path.join(ROOT,'bridge','qa-pro-bridge','server','index.js'), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env={**os.environ, 'QA_PRO_BRIDGE_PORT': str(BPORT), 'QA_PRO_BRIDGE_DIR': BDIR})
        self.ids = itertools.count(1); self.fut = {}
        asyncio.create_task(self.reader()); asyncio.create_task(self.errs())
        await self.rpc('initialize', {'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'test','version':'1'}})
    async def reader(self):
        while True:
            line = await self.p.stdout.readline()
            if not line: return
            m = json.loads(line); f = self.fut.pop(m.get('id'), None)
            if f: f.set_result(m)
    async def errs(self):
        while True:
            line = await self.p.stderr.readline()
            if not line: return
            print('   bridge:', line.decode().strip())
    async def rpc(self, method, params):
        i = next(self.ids); f = asyncio.get_event_loop().create_future(); self.fut[i] = f
        self.p.stdin.write((json.dumps({'jsonrpc':'2.0','id':i,'method':method,'params':params})+'\n').encode()); await self.p.stdin.drain()
        return await f
BR = Bridge()
async def mcp_binding(source, tool, args):
    if not BR_UP: return {'__err':'server_not_connected','message':'no host'}
    m = await BR.rpc('tools/call', {'name': tool, 'arguments': args})
    return m['result']
BR_UP = True
async def main():
    await BR.start()
    ext=tempfile.mkdtemp(); shutil.copytree(EXT_SRC, ext, dirs_exist_ok=True)
    m=json.load(open(os.path.join(ext,'manifest.json'),encoding='utf-8')); m['host_permissions'].append('http://127.0.0.1/*')
    json.dump(m,open(os.path.join(ext,'manifest.json'),'w',encoding='utf-8'),ensure_ascii=False)
    async with async_playwright() as p:
        errs=[]
        cb=await p.chromium.launch_persistent_context(tempfile.mkdtemp(), channel='chromium', headless=True, viewport={'width':1360,'height':900},
            args=[f'--disable-extensions-except={ext}', f'--load-extension={ext}'])
        sw = cb.service_workers[0] if cb.service_workers else await cb.wait_for_event('serviceworker')
        ext_id = sw.url.split('/')[2]
        await cb.add_cookies([{'name':'ACCESS_TOKEN','value':'tok-123','url':BASE}])
        sf=await cb.new_page(); await sf.goto(BASE+'/project/PPAN?section=124')
        await sw.evaluate(f"saveSettings({{baseUrl:'{BASE}', bridgePort:{BPORT}}}).then(() => {{ try {{ bws && bws.close(); }} catch (e) {{}} bws = null; return bridgeConnect(); }})")
        await sf.wait_for_timeout(800)
        print('H0 ext bridge state:', await sw.evaluate("bwsState"))
        # «приложение Claude»
        b2=await p.chromium.launch()
        ca=await b2.new_context(viewport={'width':1360,'height':900}, user_agent='Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Claude/1.0.0 Chrome/138.0.0.0 Electron/37.2.0 Safari/537.36')
        await ca.expose_binding('__mcp', mcp_binding); await ca.expose_binding('__dbop', dbop)
        if os.environ.get('MCP_NAME'): await ca.add_init_script(script=f"window.__mcpServerName = {json.dumps(os.environ['MCP_NAME'])};")
        for f in ('mockgen.js','mock_shared.js','mock_mcp.js'): await ca.add_init_script(path=os.path.join(D,f))
        await ca.route('http://desk.test/**', serve)
        pa=await ca.new_page(); pa.on('pageerror', lambda e: errs.append('A '+str(e)))
        await pa.goto('http://desk.test/'); await pa.wait_for_timeout(2500)
        await pa.click('#btn-run'); await pa.wait_for_selector('#btn-run:not([hidden])', timeout=40000); await pa.wait_for_timeout(800)
        await pa.click('#tab-cases'); await pa.wait_for_timeout(2000)
        await pa.click('#btn-settings'); await pa.click('#settab-tms'); await pa.wait_for_timeout(1500)
        print('H1 banner:', (await pa.inner_text('#tms-body .banner')).replace('\n',' | ')[:900])
        await pa.screenshot(path=os.path.join(D,'v24_desktop_bridge.png'))
        await pa.click('[data-tmb=test]'); await pa.wait_for_timeout(1500)
        print('H2 test:', await pa.inner_text('#tms-body .case-note'))
        async with pa.expect_event('console', timeout=3000) if False else _null():
            pass
        await pa.click('#tms-body [data-act=bridge-mcpb]'); await pa.wait_for_timeout(400)
        b64 = await pa.evaluate("window.__dlBlob.arrayBuffer().then(a => { let s=''; new Uint8Array(a).forEach(x => s += String.fromCharCode(x)); return btoa(s); })")
        import base64; mp=os.path.join(tempfile.mkdtemp(),'qa-pro-bridge.mcpb'); open(mp,'wb').write(base64.b64decode(b64))
        info = subprocess.run([os.path.join(ROOT,'tools','node_modules','.bin','mcpb'),'info',mp],capture_output=True,text=True).stdout
        print('H3 page mcpb:', await pa.evaluate('window.__dl'), '|', ' '.join(l.strip() for l in info.splitlines() if l.startswith(('File','Size','name','version')))[:200])
        ud=tempfile.mkdtemp(); un=subprocess.run([os.path.join(ROOT,'tools','node_modules','.bin','mcpb'),'unpack',mp,ud],capture_output=True,text=True)
        print('H3 unpack:', un.returncode, sorted(os.listdir(ud)), sorted(os.listdir(os.path.join(ud,'server'))), all(open(os.path.join(ud,'server',f),encoding='utf-8').read()==open(os.path.join(ROOT,'bridge','qa-pro-bridge','server',f),encoding='utf-8').read() for f in ('index.js','core.js')))
        # распакованный с страницы мост запускается и отвечает
        tdir=tempfile.mkdtemp(); tport=BPORT+1
        pr=subprocess.Popen(['node', os.path.join(ud,'server','index.js')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env={**os.environ,'QA_PRO_BRIDGE_PORT':str(tport),'QA_PRO_BRIDGE_DIR':tdir})
        pr.stdin.write(json.dumps({'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'t','version':'1'}}})+'\n'); pr.stdin.flush(); pr.stdout.readline()
        pr.stdin.write(json.dumps({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'ping','arguments':{}}})+'\n'); pr.stdin.flush()
        pp=json.loads(pr.stdout.readline())['result']['structuredContent']; pr.kill()
        print('H3 page-built bridge runs:', pp['version'], pp['core'], pp['listening'])
        import urllib.request
        try: urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{tport}/shutdown', data=b'{}', headers={'x-qa-pro-bridge-token': open(os.path.join(tdir,'token')).read().strip()}, method='POST'), timeout=2).read()
        except Exception as e: print('   tcore:', e)
        await pa.keyboard.press('Escape'); await pa.wait_for_timeout(300)
        # 1) загрузка через мост
        async with cb.expect_page(timeout=20000) as pi:
            await pa.click('[data-act=tms-upload]')
        up = await pi.value; await up.wait_for_load_state(); await up.wait_for_timeout(700)
        print('H4 window:', await up.inner_text('#source'), '| rows', await up.locator('#rows tr').count(), '| desk log:', await pa.inner_text('#tms-bar .log'))
        await up.click('#from-tab'); await up.wait_for_timeout(600); await up.click('#go'); await up.wait_for_timeout(2500)
        print('H5 summary:', await up.inner_text('#summary'))
        await pa.wait_for_timeout(1200)
        CASES = "() => [...document.querySelectorAll('#case-list article')].map(a => a.querySelector('.case-id').textContent + ' ' + [...a.querySelectorAll('.case-sub .chip')].map(c => c.textContent).filter(t => /в тмс/i.test(t)).join(','))"
        print('H6 desk log:', await pa.inner_text('#tms-bar .log'), '| marks:', await pa.evaluate(CASES))
        print('H6 posts:', len(POSTS), [b['labels'] for b in POSTS], [b['ti_regressive'] for b in POSTS], '| calls:', await pa.evaluate('window.__mcpCalls.join(",")'))
        await up.close()
        # 2) окно закрыто без загрузки
        (await pa.locator('#tms-reup').count()) and await pa.check('#tms-reup')
        async with cb.expect_page(timeout=20000) as pi:
            await pa.click('[data-act=tms-upload]')
        up2 = await pi.value; await up2.wait_for_timeout(500); await up2.close(); await pa.wait_for_timeout(1500)
        print('H7 closed window:', await pa.inner_text('#tms-bar .log'))
        # 3) отмена из приложения закрывает окно загрузчика
        (await pa.locator('#tms-reup').count()) and await pa.check('#tms-reup')
        async with cb.expect_page(timeout=20000) as pi:
            await pa.click('[data-act=tms-upload]')
        up3 = await pi.value; await up3.wait_for_timeout(500)
        await pa.click('[data-act=tms-stop]'); await pa.wait_for_timeout(1500)
        print('H8 app cancel:', await pa.inner_text('#tms-bar .log'), '| window closed:', up3.is_closed())
        # 4) загрузчик не подключён: задание ждёт и уходит, когда он подключается
        await sw.evaluate("saveSettings({desktopBridge:false}).then(() => bridgeConnect())"); await pa.wait_for_timeout(500)
        n0=len(POSTS)
        (await pa.locator('#tms-reup').count()) and await pa.check('#tms-reup'); await pa.click('[data-act=tms-upload]'); await pa.wait_for_timeout(1500)
        print('H9 queued:', await pa.inner_text('#tms-bar .log'))
        async with cb.expect_page(timeout=20000) as pi:
            await sw.evaluate("saveSettings({desktopBridge:true}).then(() => bridgeConnect())")
        up4 = await pi.value; await up4.wait_for_load_state(); await up4.wait_for_timeout(600)
        print('H10 delivered on connect:', await pa.inner_text('#tms-bar .log'))
        await up4.click('#from-tab'); await up4.wait_for_timeout(500); await up4.click('#go'); await up4.wait_for_timeout(2500); await pa.wait_for_timeout(1200)
        print('H11 done:', await pa.inner_text('#tms-bar .log'), '| new posts', len(POSTS)-n0)
        # 5) настройки загрузчика
        op=await cb.new_page(); await op.goto(f'chrome-extension://{ext_id}/options.html'); await op.wait_for_timeout(1200)
        print('H12 options bridge:', await op.inner_text('#bridge-state'))
        await op.screenshot(path=os.path.join(D,'v24_options.png'), full_page=True)
        # 6) отправили и закрыли приложение: ядро моста живёт, загрузка доделывается, отметки — при следующем открытии
        print('H13a ping core:', (await BR.rpc('tools/call', {'name':'ping','arguments':{}}))['result']['structuredContent'].get('core'))
        (await pa.locator('#tms-reup').count()) and await pa.check('#tms-reup')
        async with cb.expect_page(timeout=20000) as pi:
            await pa.click('[data-act=tms-upload]')
        up5 = await pi.value; await up5.wait_for_load_state(); await up5.wait_for_timeout(600)
        await pa.close(); BR.p.kill(); await asyncio.sleep(1.0)
        print('H13b app closed: ext still connected:', (await sw.evaluate("bwsState"))['connected'])
        n1=len(POSTS)
        await up5.click('#from-tab'); await up5.wait_for_timeout(500); await up5.click('#go'); await up5.wait_for_timeout(2500)
        print('H13c uploaded while app closed:', len(POSTS)-n1, '| outbox left:', await sw.evaluate("chrome.storage.local.get('bridgeOutbox').then(r => (r.bridgeOutbox||[]).length)"))
        BR.__init__(); await BR.start()
        pa = await ca.new_page(); pa.on('pageerror', lambda e: errs.append('A3 '+str(e)))
        await pa.goto('http://desk.test/'); await pa.wait_for_timeout(3000)
        await pa.click('#tab-cases'); await pa.wait_for_timeout(3000)
        print('H13d reopened app log:', await pa.evaluate("document.querySelector('#tms-bar .log')?.innerText || '(нет)'"))
        # 7) мост не установлен
        global BR_UP; BR_UP=False
        await pa.click('#btn-settings'); await pa.click('#settab-tms'); await pa.click('[data-tmb=test]'); await pa.wait_for_timeout(2500)
        print('H13 no bridge test:', await pa.inner_text('#tms-body .case-note'))
        print('ERRORS', errs)
        await b2.close(); await cb.close()
    BR.p.kill(); await core_shutdown()
import contextlib
@contextlib.asynccontextmanager
async def _null():
    yield
asyncio.run(main())
