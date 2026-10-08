# «Материалы» → расшифровка видео: настоящий мост 1.2 (Whisper base) в двух путях —
# A) приложение Claude (host:…), B) Chrome с загрузчиком 1.5 (RPC через WebSocket). Видео не сохраняется, расшифровка — документ продукта.
import asyncio, os, json, threading, shutil, tempfile, time, itertools, re, urllib.request
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from playwright.async_api import async_playwright
D=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(D)
EXT_SRC=os.path.join(ROOT,'uploader','qa-pro-sfera-uploader')
STANDALONE=open(os.path.join(ROOT,'qa-pro.html'),'rb').read()
AI=[]
def ai_answer(text, imgs):
    if imgs:
        n=re.findall(r'кадр (\d+) — \[([\d:]+)\]', text)
        return {'frames':[{'n':int(a),'skip':False,'screen':'Экран '+b,'details':'Описание кадра '+a} for a,b in n]}
    if 'Ты — аналитик QA-команды. Это' in text: return {'summary':'Демо восстановления пароля.','points':['Вход','Восстановление'],'requirements':['Блокировка на 30 минут после трёх попыток'],'decisions':['Ссылка живёт 30 минут'],'questions':[]}
    if 'Раздели фрагмент документа' in text: return {'blocks':[{'blockId':None,'title':'Восстановление пароля','summary':'x','sections':['видео'],'content':'### Описание\n- Из расшифровки видео'}]}
    if 'Проверка связи' in text: return {'ok':True,'model':'mock'}
    if 'Собери единую сводку раздела' in text: return {'summary':'Сводка раздела','synth':'### Описание\n- Сведения из видео (Видео — demo_call_frag)','conflicts':[],'links':[]}
    if 'Ты ведёшь «паспорт продукта»' in text: return {'passport':'## Назначение и границы\n- Восстановление пароля (Видео — demo_call_frag)'}
    if 'Ты помогаешь найти ответ в базе знаний' in text: return {'sections':[],'terms':[]}
    return {}
class H(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def _send(self, b, ct, code=200):
        self.send_response(code); self.send_header('Content-Type',ct); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path.startswith('/qa-pro.html'): return self._send(STANDALONE,'text/html; charset=utf-8')
        if self.path.startswith('/files/'): return self._send(open(os.path.join(D,self.path[7:]),'rb').read(),'video/mp4')
        self._send(b'{}','application/json',404)
    def do_POST(self):
        n=int(self.headers.get('Content-Length','0')); body=json.loads(self.rfile.read(n) or b'{}')
        if self.path=='/v1/chat/completions':
            u=body['messages'][-1]['content']
            text=u if isinstance(u,str) else ' '.join(p.get('text','') for p in u if p.get('type')=='text')
            imgs=0 if isinstance(u,str) else sum(1 for p in u if p.get('type')=='image_url')
            AI.append({'imgs':imgs,'head':text[:60].replace('\n',' '),'text':text})
            out={'choices':[{'message':{'role':'assistant','content':json.dumps(ai_answer(text,imgs),ensure_ascii=False)}}],'usage':{'prompt_tokens':100,'completion_tokens':20}}
            return self._send(json.dumps(out,ensure_ascii=False).encode(),'application/json')
        self._send(b'{}','application/json',404)
srv=ThreadingHTTPServer(('127.0.0.1',0),H); PORT=srv.server_address[1]; BASE=f'http://127.0.0.1:{PORT}'
threading.Thread(target=srv.serve_forever,daemon=True).start()

html=open(os.path.join(ROOT,'tc-agent.html'),encoding='utf-8').read()
SKEL='<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1"><style>[hidden]{display:none!important}body{margin:0}</style></head><body>'+html+'</body></html>'
async def serve(r): await r.fulfill(body=SKEL, content_type='text/html; charset=utf-8')
BPORT = 47600 + os.getpid() % 300
BDIR = tempfile.mkdtemp()
# распознаватель и модель — заранее (в песочнице Hugging Face закрыт; скачивание из npm проверено в bridge_asr.js)
rt=[os.path.join('/tmp',d,'runtime') for d in os.listdir('/tmp') if d.startswith('qpa-') and os.path.isfile(os.path.join('/tmp',d,'runtime','tf-4.3.0_ort-1.31.0-dev_r2','.ready'))]
shutil.copytree(rt[0], os.path.join(BDIR,'runtime'))
shutil.copytree('/tmp/tfjs/node_modules/sts-whisper-base/models/Xenova/whisper-base', os.path.join(BDIR,'models','Xenova','whisper-base'))
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
class Bridge:
    async def start(self):
        self.p = await asyncio.create_subprocess_exec('node', os.path.join(ROOT,'bridge','qa-pro-bridge','server','index.js'), stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env={**os.environ, 'QA_PRO_BRIDGE_PORT': str(BPORT), 'QA_PRO_BRIDGE_DIR': BDIR}, limit=1<<24)
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
            print('   bridge:', line.decode().strip()[:200])
    async def rpc(self, method, params):
        i = next(self.ids); f = asyncio.get_event_loop().create_future(); self.fut[i] = f
        self.p.stdin.write((json.dumps({'jsonrpc':'2.0','id':i,'method':method,'params':params})+'\n').encode()); await self.p.stdin.drain()
        return await f
BR = Bridge(); BR_UP = False; MCP_LOG=[]
async def mcp_binding(source, tool, args):
    MCP_LOG.append(tool)
    if not BR_UP: return {'__err':'server_not_connected','message':'no host'}
    m = await BR.rpc('tools/call', {'name': tool, 'arguments': args})
    return m['result']
def shutdown_core():
    try:
        tok=open(os.path.join(BDIR,'token')).read().strip()
        urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{BPORT}/shutdown', data=b'{}', headers={'x-qa-pro-bridge-token': tok}, method='POST'), timeout=2).read()
    except Exception as e: print('   core shutdown:', e)

async def open_mat(pg):
    await pg.click('[data-mode=help]'); await pg.wait_for_timeout(500)
    await pg.click('#help-head [data-act=help-view][data-v=mat]'); await pg.wait_for_timeout(500)
async def follow(pg, label, n_before, timeout=420):
    """ждём, пока в списке появится новая расшифровка или задание упадёт; печатаем этапы"""
    seen=[]; t0=time.time()
    while time.time()-t0 < timeout:
        st = await pg.evaluate("(() => { const j = __qa.S.mat.jobs[0]; return { n: __qa.vidDocs().length, stage: j ? j.stage : '', note: j ? j.note : '', err: j ? j.error : '' }; })()")
        key = st['stage'] + ' ' + re.sub(r'\d+%|осталось.*|фрагмент \d+', '#', st['note'])
        if st['stage'] and (not seen or seen[-1] != key): seen.append(key)
        if st['n'] > n_before or st['stage'] == 'error': break
        await pg.wait_for_timeout(400)
    print(f'{label} stages:', ' → '.join(seen)[:900])
    print(f'{label} done in {round(time.time()-t0)} s:', await pg.evaluate("(() => { const j = __qa.S.mat.jobs[0]; return j ? 'ERROR ' + j.error : 'ok, расшифровок ' + __qa.vidDocs().length; })()"))

async def main():
    global BR_UP
    await BR.start()
    errs=[]
    async with async_playwright() as p:
        # ---------- A) приложение Claude: мост как host-сервер ----------
        b2=await p.chromium.launch()
        ca=await b2.new_context(viewport={'width':1360,'height':900}, user_agent='Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Claude/1.0.0 Chrome/138.0.0.0 Electron/37.2.0 Safari/537.36')
        await ca.expose_binding('__mcp', mcp_binding); await ca.expose_binding('__dbop', dbop)
        await ca.add_init_script(script='window.__qaTest = true; window.__sampleImages = true; window.__sampleDelay = 30;')
        for f in ('mockgen.js','mock_shared.js','mock_mcp.js'): await ca.add_init_script(path=os.path.join(D,f))
        await ca.route('http://desk.test/**', serve)
        pa=await ca.new_page(); pa.on('pageerror', lambda e: errs.append('A '+str(e)))
        await pa.goto('http://desk.test/'); await pa.wait_for_timeout(2500)
        await open_mat(pa); await pa.wait_for_timeout(1500)
        print('A1 no bridge:', (await pa.inner_text('#mat-asr')).replace('\n',' | ')[:400], '| buttons:', await pa.eval_on_selector_all('#mat-asr button', 'els => els.map(e => e.textContent)'))
        await pa.screenshot(path=os.path.join(D,'v27_mat_nobridge.png'))
        BR_UP=True
        await pa.click('[data-act=mat-check]'); await pa.wait_for_function("() => __qa.S.mat.route === 'host' && __qa.S.mat.asr", timeout=15000); await pa.wait_for_timeout(300)
        print('A2 bridge found:', (await pa.inner_text('#mat-asr')).replace('\n',' | ')[:300], '| route', await pa.evaluate('__qa.S.mat.route'), '| asr', await pa.evaluate('__qa.S.mat.asr.state'))
        await pa.select_option('#mat-model','base'); await pa.wait_for_timeout(200)
        print('A3 model saved:', await pa.evaluate("localStorage.getItem('qapro.asrModel')"), '|', (await pa.inner_text('#mat-asr .mat-asr-row')).replace('\n',' | ')[:200])
        await pa.set_input_files('#mat-file', os.path.join(D,'demo_call.mp4')); await pa.wait_for_timeout(1200)
        await pa.screenshot(path=os.path.join(D,'v27_mat_progress.png'))
        await follow(pa, 'A4', 0)
        doc = await pa.evaluate("(() => { const d = __qa.vidDocs()[0]; return d && { name: d.name, chars: d.chars, video: d.video, saved: d.savedParts, text: d.text, inRun: __qa.docsFor(null).includes(d) }; })()")
        print('A5 doc:', doc and {k: v for k, v in doc.items() if k != 'text'})
        print('A5 text:\n' + (doc['text'][:2600] if doc else '—'))
        print('A6 images sent to Claude:', await pa.evaluate('window.__imgCalls || []'))
        print('A6 mcp calls:', {t: MCP_LOG.count(t) for t in set(MCP_LOG)})
        meta=[d for k,v in STORE.items() if k.count('/')==1 and isinstance(v,dict) and v.get('kind')=='product' for d in v.get('docs',[]) if d.get('source')=='video']
        print('A7 product doc meta:', [{k: m.get(k) for k in ('name','source','parts','chars')} | {'video': {k: m['video'].get(k) for k in ('duration','speech','screens','model')}} for m in meta])
        await pa.wait_for_function("() => { const d = __qa.vidDocs()[0]; return d && __qa.S.kb.index.docs && __qa.S.kb.index.docs[d.id]; }", timeout=30000)
        await pa.wait_for_timeout(500)
        print('A8 kb:', await pa.evaluate("(() => { const d = __qa.vidDocs()[0]; return { inKb: !!__qa.S.kb.index.docs[d.id], blocks: __qa.S.kb.index.blocks.length }; })()"), '|', (await pa.inner_text('#mat-list')).replace('\n',' | ')[:300])
        await pa.screenshot(path=os.path.join(D,'v27_mat_list.png'), full_page=True)
        await pa.click('[data-act=mat-open]'); await pa.wait_for_timeout(400)
        print('A9 dialog:', (await pa.inner_text('#mat-ov')).replace('\n',' | ')[:300])
        await pa.screenshot(path=os.path.join(D,'v27_mat_doc.png'))
        await pa.keyboard.press('Escape'); await pa.wait_for_timeout(200)
        # генерация видит расшифровку
        await pa.click('[data-mode=generate]'); await pa.wait_for_timeout(500)
        print('A10 docs panel:', (await pa.inner_text('#doc-list')).replace('\n',' | ')[:300])
        await pa.click('#btn-run'); await pa.wait_for_selector('#btn-run:not([hidden])', timeout=60000); await pa.wait_for_timeout(500)
        print('A10 generation prompts with transcript:', await pa.evaluate("(window.__prompts || []).filter(p => p.includes('Видео — demo_call') && p.includes('Расшифровка речи')).map(p => p.slice(0, 40))"))
        # отмена во время распознавания
        await open_mat(pa)
        await pa.set_input_files('#mat-file', os.path.join(D,'demo_call.mp4'))
        await pa.wait_for_function("() => __qa.S.mat.jobs[0] && __qa.S.mat.jobs[0].stage === 'speech'", timeout=60000)
        await pa.click('#mat-jobs [data-act=mat-cancel]'); await pa.wait_for_function("() => !__qa.S.mat.jobs.length && !__qa.S.mat.busy", timeout=60000)
        print('A11 cancelled: jobs', await pa.evaluate('__qa.S.mat.jobs.length'), '| transcripts', await pa.evaluate('__qa.vidDocs().length'))
        # удаление расшифровки (двойное нажатие)
        await pa.click('#mat-list [data-act=mat-del]'); await pa.wait_for_timeout(200)
        armed = await pa.inner_text('#mat-list [data-act=mat-del]')
        await pa.click('#mat-list [data-act=mat-del]'); await pa.wait_for_timeout(800)
        meta=[d for k,v in STORE.items() if k.count('/')==1 and isinstance(v,dict) and v.get('kind')=='product' for d in v.get('docs',[]) if d.get('source')=='video']
        print('A12 deleted:', armed, '| transcripts', await pa.evaluate('__qa.vidDocs().length'), '| meta left', len(meta), '| parts left', len([k for k in STORE if '/docparts/' in k and k.split('/docparts/')[1].startswith(doc and '' or 'x')]))
        await b2.close()

        # ---------- B) Chrome: автономная версия + загрузчик 1.5 → мост по WebSocket ----------
        ext=tempfile.mkdtemp(); shutil.copytree(EXT_SRC, ext, dirs_exist_ok=True)
        m=json.load(open(os.path.join(ext,'manifest.json'),encoding='utf-8')); m['host_permissions'].append('http://127.0.0.1/*')
        json.dump(m,open(os.path.join(ext,'manifest.json'),'w',encoding='utf-8'),ensure_ascii=False)
        cb=await p.chromium.launch_persistent_context(tempfile.mkdtemp(), channel='chromium', headless=True, viewport={'width':1360,'height':900},
            args=[f'--disable-extensions-except={ext}', f'--load-extension={ext}'])
        sw = cb.service_workers[0] if cb.service_workers else await cb.wait_for_event('serviceworker')
        print('B0 uploader', await sw.evaluate('chrome.runtime.getManifest().version'))
        await sw.evaluate(f"saveSettings({{bridgePort:{BPORT}}}).then(() => {{ try {{ bws && bws.close(); }} catch (e) {{}} bws = null; return bridgeConnect(); }})")
        await cb.add_init_script(script=f"window.__qaTest = true; try {{ localStorage.setItem('qapro.conns', JSON.stringify([{{id:'c1',kind:'openai',name:'Мок',baseUrl:'{BASE}/v1',apiKey:'k',auth:'Bearer',model:'gpt-x',headers:'',tools:false}}])); }} catch (e) {{}}")
        pb=await cb.new_page(); pb.on('pageerror', lambda e: errs.append('B '+str(e)))
        await pb.goto(BASE+'/qa-pro.html'); await pb.wait_for_timeout(2500)
        print('B1 bridge state in uploader:', await sw.evaluate('bwsState'))
        await open_mat(pb)
        await pb.wait_for_function("() => __qa.S.mat.checked && !__qa.S.mat.checking", timeout=20000); await pb.wait_for_timeout(300)
        print('B2 route:', await pb.evaluate('__qa.S.mat.route'), '|', (await pb.inner_text('#mat-asr .mat-asr-row')).replace('\n',' | ')[:250])
        # разбор MP4 на странице
        info = await pb.evaluate("""(async () => { const out = {};
          for (const n of ['demo_call.mp4', 'demo_call_h264.mp4', 'demo_call_frag.mp4']) {
            const b = await (await fetch('/files/' + n)).blob(); const i = await __qa.mp4Info(new File([b], n));
            out[n] = { dur: Math.round(i.duration * 10) / 10, frag: i.frag, hasAudio: i.hasAudio, hasVideo: i.hasVideo, audio: i.audio && { codec: i.audio.codec, sr: i.audio.sr, ch: i.audio.ch, desc: i.audio.desc ? i.audio.desc.length : 0, samples: i.audio.count, chunks: i.audio.chunks.length, end: Math.round(i.audio.times[i.audio.count - 1] / i.audio.timescale * 10) / 10 } };
            if (i.audio) out[n].wc = (await AudioDecoder.isConfigSupported({ codec: i.audio.codec, sampleRate: i.audio.sr, numberOfChannels: i.audio.ch, description: i.audio.desc })).supported;
          }
          return out; })()""")
        for k,v in info.items(): print('B3', k, v)
        # извлечение звука WebCodecs: длительность и сегменты
        seg = await pb.evaluate("""(async () => { const b = await (await fetch('/files/demo_call.mp4')).blob(); const f = new File([b], 'x.mp4'); const i = await __qa.mp4Info(f);
          const s = __qa.vidSink(i.duration), t0 = performance.now(); await __qa.vidAudioWC(f, i.audio, s, {}); const a = s.done();
          const t1 = performance.now(); const s2 = __qa.vidSink(i.duration); await __qa.vidAudioDecode(f, s2, {}); const a2 = s2.done();
          return { sec: a.seconds.toFixed(2), ms: Math.round(t1 - t0), segs: __qa.vidSegments(a.energy).map(g => [+(g.s / 50).toFixed(1), +(g.e / 50).toFixed(1)]), fallbackSec: a2.seconds.toFixed(2), fallbackSegs: __qa.vidSegments(a2.energy).length }; })()""")
        print('B4 audio:', seg)
        await pb.select_option('#mat-model','base'); await pb.select_option('#mat-lang','auto'); await pb.wait_for_timeout(200)
        await pb.set_input_files('#mat-file', os.path.join(D,'demo_call_frag.mp4')); await pb.wait_for_timeout(500)
        await follow(pb, 'B5', 0)
        d = await pb.evaluate("(() => { const d = __qa.vidDocs()[0]; return d && { name: d.name, video: d.video, speech: (d.text.split('## Расшифровка речи')[1] || '').trim().slice(0, 600), screen: (d.text.split('## Что показано на экране')[1] || '').split('##')[0].trim().slice(0, 300) }; })()")
        print('B6 doc:', d and {k: d[k] for k in ('name','video')}); print('B6 speech:', d and d['speech']); print('B6 screen:', d and d['screen'])
        print('B7 AI calls:', [(a['imgs'], a['head'][:40]) for a in AI])
        await pb.screenshot(path=os.path.join(D,'v27_chrome_list.png'), full_page=True)
        # H.264 + AAC: в тестовом Chromium нет этих кодеков — понятная ошибка вместо зависания
        await pb.set_input_files('#mat-file', os.path.join(D,'demo_call_h264.mp4')); await pb.wait_for_timeout(500)
        await follow(pb, 'B8', 1, timeout=120)
        await pb.screenshot(path=os.path.join(D,'v27_chrome_err.png'))
        # не .mp4
        await pb.set_input_files('#mat-file', os.path.join(D,'notes.pdf')); await pb.wait_for_timeout(500)
        print('B9 toast:', await pb.eval_on_selector_all('#toasts > *', 'els => els.map(e => e.textContent.trim()).slice(-1)'))
        await cb.close()
        # ---------- C) приложение Claude, но в разрешениях страницы нет asr_* — понятное объяснение ----------
        b3=await p.chromium.launch()
        cc=await b3.new_context(viewport={'width':1360,'height':900}, user_agent='Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Claude/1.0.0 Chrome/138.0.0.0 Electron/37.2.0 Safari/537.36')
        await cc.expose_binding('__mcp', mcp_binding); await cc.expose_binding('__dbop', dbop)
        await cc.add_init_script(script="window.__qaTest = true; window.__mcpTools = ['ping','sfera_upload','sfera_job','sfera_cancel'];")
        for f in ('mockgen.js','mock_shared.js','mock_mcp.js'): await cc.add_init_script(path=os.path.join(D,f))
        await cc.route('http://desk.test/**', serve)
        pc=await cc.new_page(); pc.on('pageerror', lambda e: errs.append('C '+str(e)))
        await pc.goto('http://desk.test/'); await pc.wait_for_timeout(2500)
        await open_mat(pc); await pc.wait_for_function("() => __qa.S.mat.checked && !__qa.S.mat.checking", timeout=20000)
        print('C1 no asr permission:', await pc.evaluate('__qa.S.mat.route'), '|', (await pc.inner_text('#mat-asr .mat-asr-row')).replace('\n',' | ')[:400])
        await b3.close()
    shutdown_core(); BR.p.kill()
    print('ERRORS:', errs or 'none')
asyncio.run(main())
