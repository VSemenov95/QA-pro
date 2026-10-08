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
    m=json.load(open(os.path.join(ext,'manifest.json'),encoding='utf-8')); m['host_permissions'].append('http://127.0.0.1/*')
    json.dump(m,open(os.path.join(ext,'manifest.json'),'w',encoding='utf-8'),ensure_ascii=False)
    async with async_playwright() as p:
        errs=[]
        ctx=await p.chromium.launch_persistent_context(tempfile.mkdtemp(), channel='chromium', headless=True, viewport={'width':1360,'height':900},
            args=[f'--disable-extensions-except={ext}', f'--load-extension={ext}'])
        sw = ctx.service_workers[0] if ctx.service_workers else await ctx.wait_for_event('serviceworker')
        ext_id = sw.url.split('/')[2]
        await sw.evaluate(f"chrome.storage.local.set({{settings:{{baseUrl:'{BASE}'}}}})")
        await ctx.add_cookies([{'name':'ACCESS_TOKEN','value':'tok-123','url':BASE}])
        await ctx.add_init_script(path=os.path.join(D,'mockgen.js')); await ctx.add_init_script(path=os.path.join(D,'mock_ext.js'))
        await ctx.add_init_script(script="""if (!localStorage.getItem('seed1')) { localStorage.setItem('seed1','1'); localStorage.setItem('qapro.conns', JSON.stringify([{id:'p-innocode',preset:'innocode',kind:'openai',name:'Иннокод',baseUrl:'https://chat.aicenter.inno.tech/v1',apiKey:'k',model:'qwen',tools:false}])); localStorage.setItem('tca.settings', JSON.stringify({genAI:'conn:p-innocode'})); }""")
        pg=await ctx.new_page(); pg.on('pageerror', lambda e: errs.append('PAGE '+str(e)))
        sf=await ctx.new_page(); await sf.goto(BASE+'/project/PPAN?section=124')
        await pg.bring_to_front()
        await pg.goto(BASE+'/qa-pro.html'); await pg.wait_for_timeout(1000)
        await pg.click('#btn-run'); await pg.wait_for_selector('#btn-run:not([hidden])', timeout=40000); await pg.wait_for_timeout(500)
        await pg.click('#tab-cases'); await pg.wait_for_timeout(1500)
        print('U1 bar:', (await pg.inner_text('#tms-bar')).replace('\n',' | ')[:200])
        CASES = "() => [...document.querySelectorAll('#case-list article')].map(a => a.querySelector('.case-id').textContent + ' ' + [...a.querySelectorAll('.case-sub .chip')].map(c => c.textContent).filter(t => /смоук|регресс|в тмс/i.test(t)).join(','))"
        print('U1 suites:', await pg.evaluate(CASES))
        async with ctx.expect_page() as pi:
            await pg.click('[data-act=tms-upload]')
        up = await pi.value; await up.wait_for_load_state(); await up.wait_for_timeout(600)
        print('U2 window:', up.url.split('/')[-1][:30], '| source:', await up.inner_text('#source'), '| login:', await up.inner_text('#login'))
        print('U2 qa log:', await pg.inner_text('#tms-bar .log'))
        print('U2 rows:', await up.eval_on_selector_all('#rows tr', 'rs => rs.map(r => r.children[1].innerText.split("\\n")[0] + " | " + r.children[3].innerText.replace(/\\s+/g," "))'))
        await up.click('#from-tab'); await up.wait_for_timeout(600)
        print('U3 from tab:', await up.input_value('#sect-url'), '| proj', await up.input_value('#proj'), '| sect', await up.eval_on_selector('#sect', 'e => e.value + " " + e.selectedOptions[0]?.textContent'))
        print('U3 go:', await up.inner_text('#go'), '|', await up.inner_text('#go-note'))
        await up.click('#go'); await up.wait_for_timeout(1500)
        print('U4 summary:', await up.inner_text('#summary'))
        await pg.wait_for_timeout(500)
        print('U5 qa log:', await pg.inner_text('#tms-bar .log'))
        print('U5 marks:', await pg.evaluate(CASES))
        print('U6 posts:', len(POSTS), '| auth:', set(AUTH))
        for b in POSTS:
            print('   ', b['name'][:40], '| labels', b['labels'], '| regr', b['ti_regressive'], '| sect', b['sectionId'], b['projectCode'], '| status', b['statusId'], b['ti_status'], b['ti_priority'], '| prio', b['priority'], '| steps', len(b['steps']), b['steps'][0]['action'][:30] if b['steps'] else '')
        print('U6 no AI_gen:', all('AI_gen' not in b['labels'] for b in POSTS))
        await up.screenshot(path=os.path.join(D,'v21_uploader.png'), full_page=True)
        await up.close()
        # cancel flow: send again (re-upload) and close window
        (await pg.locator('#tms-reup').count()) and await pg.check('#tms-reup'); await pg.wait_for_timeout(100)
        async with ctx.expect_page() as pi:
            await pg.click('[data-act=tms-upload]')
        up2 = await pi.value; await up2.wait_for_load_state(); await up2.wait_for_timeout(400)
        await up2.close(); await pg.wait_for_timeout(800)
        print('U7 after close:', await pg.inner_text('#tms-bar .log'))
        # manual mode: json export + open in extension page
        (await pg.locator('#tms-reup').count()) and await pg.check('#tms-reup'); await pg.wait_for_timeout(100)
        async with pg.expect_download() as di:
            await pg.click('[data-act=sfera-json]')
        dl = await di.value
        path=os.path.join(tempfile.mkdtemp(),'qa-pro-sfera.json'); await dl.save_as(path)
        j=json.load(open(path,encoding='utf-8')); print('U8 export:', dl.suggested_filename, j['format'], len(j['cases']), list(j['cases'][0].keys()))
        man=await ctx.new_page(); await man.goto(f'chrome-extension://{ext_id}/upload.html'); await man.wait_for_timeout(500)
        await man.set_input_files('#file', path); await man.wait_for_timeout(300)
        print('U8 manual:', await man.inner_text('#source'), '| rows', await man.locator('#rows tr').count(), '| sect remembered:', await man.input_value('#sect-url'))
        await man.screenshot(path=os.path.join(D,'v21_manual.png'), full_page=True)
        # settings tab view
        await pg.click('#btn-settings'); await pg.click('#settab-tms'); await pg.wait_for_timeout(600)
        print('U9 settings:', (await pg.inner_text('#tms-body .banner')).replace('\n',' '))
        await pg.click('[data-tmb=test]'); await pg.wait_for_timeout(800); print('U9 test:', await pg.inner_text('#tms-body .case-note'))
        await pg.screenshot(path=os.path.join(D,'v21_tms_settings.png'))
        async with pg.expect_download() as di:
            await pg.click('#tms-body [data-act=sfera-zip]')
        dz = await di.value; zp=os.path.join(tempfile.mkdtemp(), dz.suggested_filename); await dz.save_as(zp)
        import zipfile, subprocess
        zt = subprocess.run(['unzip','-t',zp],capture_output=True,text=True).stdout.strip().split('\n')[-1]
        zf = zipfile.ZipFile(zp); same = all(zf.read('qa-pro-sfera-uploader/'+f) == open(os.path.join(EXT_SRC,f),'rb').read() for f in os.listdir(EXT_SRC))
        print('U10 zip:', dz.suggested_filename, '|', zt, '| files', len(zf.namelist()), '| identical:', same)
        print('ERRORS', errs)
        await ctx.close()
asyncio.run(main())
