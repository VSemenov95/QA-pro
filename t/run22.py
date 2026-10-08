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

DESK_UA='Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Claude/1.0.0 Chrome/138.0.0.0 Electron/37.2.0 Safari/537.36'
async def main():
    async with async_playwright() as p:
        errs=[]
        b=await p.chromium.launch()
        # фоновый исполнитель: обычная вкладка браузера
        cw=await b.new_context(viewport={'width':1360,'height':900})
        await cw.expose_binding('__dbop', dbop); await cw.add_init_script(path=os.path.join(D,'mockgen.js')); await cw.add_init_script(path=os.path.join(D,'mock_shared.js'))
        await cw.add_init_script(script="window.__qaTest = true; localStorage.setItem('qapro.worker','true');")
        await cw.route('http://app.test/**', serve)
        pw=await cw.new_page(); pw.on('pageerror', lambda e: errs.append('W '+str(e)))
        pw.on('console', lambda m: errs.append('W console '+m.text) if m.type=='error' and 'net::' not in m.text and 'Failed to load' not in m.text else None)
        await pw.goto('http://app.test/'); await pw.wait_for_timeout(4000)
        wk=[k for k in STORE if k.endswith('/worker')]
        print('W0 presence:', {k: {x: STORE[k][x] for x in ('kind','ai','aiReady','doing')} for k in wk})
        # приложение Claude: медленная модель, генерация, окно закрывают
        ca=await b.new_context(viewport={'width':1360,'height':900}, user_agent=DESK_UA)
        await ca.expose_binding('__dbop', dbop); await ca.add_init_script(path=os.path.join(D,'mockgen.js')); await ca.add_init_script(path=os.path.join(D,'mock_shared.js'))
        await ca.add_init_script(script="window.__sampleDelay = 3000;")
        await ca.route('http://desk.test/**', serve)
        pa=await ca.new_page(); pa.on('pageerror', lambda e: errs.append('A '+str(e)))
        await pa.goto('http://desk.test/'); await pa.wait_for_timeout(3000)
        await pa.click('#btn-settings'); await pa.click('#settab-bg'); await pa.wait_for_timeout(800)
        print('A1 bg tab:', (await pa.inner_text('#bg-body')).replace('\n',' | ')[:500])
        await pa.screenshot(path=os.path.join(D,'v25_bg_desktop.png'))
        await pa.keyboard.press('Escape')
        await pa.click('#btn-run'); await pa.wait_for_timeout(1500)
        print('A2 run note:', await pa.inner_text('#run-note'))
        await pa.wait_for_function("() => document.querySelector('#tab-cases .cnt') && +document.querySelector('#tab-cases .cnt').textContent >= 1", timeout=60000)
        await pa.wait_for_timeout(800)
        n_before = await pa.evaluate("+document.querySelector('#tab-cases .cnt').textContent")
        await pa.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide', {persisted:false}))"); await pa.wait_for_timeout(600)
        await pa.close()
        runs=[(k, v.get('status'), v.get('hb')) for k,v in STORE.items() if '/runs/' in k and k.count('/')==3]
        print('A3 closed with cases:', n_before, '| run meta:', runs)
        # исполнитель подхватывает
        try: await pw.wait_for_selector('#btn-stop:not([hidden])', timeout=60000)
        except Exception:
            print('ERRS so far:', errs[:6])
            print('STATE:', await pw.evaluate("({ running: __qa.S.running, kbBusy: __qa.S.kb.job.busy, kbPhase: __qa.S.kb.job.phase, kbLog: __qa.S.kb.job.log.slice(-3).map(l=>l.text), switching: __qa.S.switching, follow: !!__qa.S.follow, resume: !!__qa.S.resume, prodReady: __qa.S.prodReady, sessionReady: __qa.S.sessionReady, know: __qa.S.know.busy, run: __qa.S.run && __qa.S.run.status })"))
            print('PROBE:', await pw.evaluate("""(async () => { try { const ses = await __qa.readSession(); const ok = await __qa.openHistory(ses.runId, { silent: true, pid: ses.runPid, tab: 'agent' }); return { ses: ses.runId, ok, run: __qa.S.run && __qa.S.run.status }; } catch (e) { return 'THROW ' + e + ' ' + (e.stack || '').slice(0, 600); } })()"""))
            raise
        print('W1 worker resumed:', await pw.inner_text('#run-note'), '| doing:', [STORE[k].get('doing') for k in wk])
        await pw.wait_for_selector('#btn-run:not([hidden])', timeout=90000); await pw.wait_for_timeout(1500)
        n_after = await pw.evaluate("+document.querySelector('#tab-cases .cnt').textContent")
        runs=[(v.get('status'), v.get('counts')) for k,v in STORE.items() if '/runs/' in k and k.count('/')==3]
        print('W2 finished:', n_after, 'cases | run meta:', runs)
        # снова открываем приложение — результат на месте
        pa2=await ca.new_page(); pa2.on('pageerror', lambda e: errs.append('A2 '+str(e)))
        await pa2.goto('http://desk.test/'); await pa2.wait_for_timeout(3500)
        print('A4 reopened:', 'cases tab', await pa2.evaluate("document.querySelector('#tab-cases .cnt')?.textContent"), '| tabs:', (await pa2.inner_text('#tabs')).replace('\n',' ')[:120])
        # разбор документа в базу знаний: добавили в приложении и закрыли
        open(os.path.join(D,'extra.txt'),'w').write('ТЗ: дополнительный документ про лимиты. Не более 3 запросов за 15 минут.')
        await pa2.set_input_files('#file-input', os.path.join(D,'extra.txt')); await pa2.wait_for_timeout(1500)
        await pa2.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide', {persisted:false}))"); await pa2.close()
        for k in [k for k in LEASES if k.endswith('/meta/kbjob')]: LEASES.pop(k)   # аренда окна истекла (в жизни — через 2 минуты)
        kbmark = lambda: [ (k, sorted((v.get('docs') or {}).keys())) for k,v in STORE.items() if k.endswith('/kb/index') or k.endswith('/meta/kb') ]
        print('K0 kb index before:', kbmark())
        for i in range(30):
            await pw.wait_for_timeout(1000)
            if any('extra' in json.dumps(v, ensure_ascii=False) for k,v in STORE.items() if '/kb' in k): break
        blocks=[v.get('title') for k,v in STORE.items() if v and v.get('kind')=='kbblock']
        print('K1 worker kb:', i+1, 's | blocks:', blocks, '| index:', kbmark())
        await pw.click('#btn-settings'); await pw.click('#settab-bg'); await pw.wait_for_timeout(600)
        print('W3 bg tab in worker:', (await pw.inner_text('#bg-body')).replace('\n',' | ')[:300])
        await pw.screenshot(path=os.path.join(D,'v25_bg_worker.png'))
        print('ERRORS', errs)
        await b.close()
asyncio.run(main())
