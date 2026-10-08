# Мост из изолированной рамки (как артефакт на claude.ai): sandbox="allow-scripts" без allow-same-origin
import asyncio, os, json, tempfile, shutil
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'run15.py')).read().split('async def main')[0])
FRAME = """<!doctype html><meta charset=utf-8><body><pre id=log></pre><script>
const log = (x) => { document.getElementById('log').textContent += JSON.stringify(x) + '\\n'; };
window.addEventListener('message', (e) => { if (e.data && e.data.source === 'qa-pro-sfera-uploader') log(e.data.type + ':' + (e.data.version || e.data.jobId || (e.data.results ? e.data.results.length : '') || e.data.error || '')); });
log('origin=' + origin);
setTimeout(() => window.postMessage({ source: 'qa-pro', id: 'p1', type: 'SFERA_PING' }, '*'), 300);
setTimeout(() => window.postMessage({ source: 'qa-pro', id: 'u1', type: 'SFERA_UPLOAD', title: 'из рамки', cases: [{ ref: 'r1', qaId: 'API-001', name: 'Кейс из рамки', suites: ['smoke'], steps: [{action:'<p>a</p>', expectedResult:'<p>b</p>'}] }] }, '*'), 900);
</script>"""
class H2(H):
    def do_GET(self):
        if self.path.startswith('/frame.html'):
            b=FRAME.encode(); self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write(b); return
        if self.path.startswith('/host.html'):
            b=f'<!doctype html><meta charset=utf-8><h3>Хост (как claude.ai)</h3><iframe id=f sandbox="allow-scripts allow-popups" src="http://127.0.0.1:{PORT2}/frame.html" width=800 height=300></iframe>'.encode()
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); self.wfile.write(b); return
        return super().do_GET()
srv2=ThreadingHTTPServer(('127.0.0.1',0),H2); PORT2=srv2.server_address[1]; BASE2=f'http://127.0.0.1:{PORT2}'
threading.Thread(target=srv2.serve_forever,daemon=True).start()
async def main():
    ext=tempfile.mkdtemp(); shutil.copytree(EXT_SRC, ext, dirs_exist_ok=True)
    m=json.load(open(os.path.join(ext,'manifest.json'),encoding='utf-8')); m['host_permissions'].append('http://127.0.0.1/*')
    json.dump(m,open(os.path.join(ext,'manifest.json'),'w',encoding='utf-8'),ensure_ascii=False)
    async with async_playwright() as p:
        ctx=await p.chromium.launch_persistent_context(tempfile.mkdtemp(), channel='chromium', headless=True, args=[f'--disable-extensions-except={ext}', f'--load-extension={ext}'])
        sw = ctx.service_workers[0] if ctx.service_workers else await ctx.wait_for_event('serviceworker')
        await sw.evaluate(f"chrome.storage.local.set({{settings:{{baseUrl:'{BASE2}', lastSectionUrl:'{BASE2}/project/PPAN?section=124'}}}})")
        await ctx.add_cookies([{'name':'ACCESS_TOKEN','value':'tok-123','url':BASE2}])
        pg=await ctx.new_page()
        async with ctx.expect_page(timeout=8000) as pi:
            await pg.goto(f'http://localhost:{PORT2}/host.html')
        up=await pi.value; await up.wait_for_load_state(); await up.wait_for_timeout(800)
        fr=pg.frame_locator('#f')
        print('F1 frame log:', (await fr.locator('#log').inner_text()).strip().split('\n'))
        await up.click('#go'); await up.wait_for_timeout(1200)
        print('F2 summary:', await up.inner_text('#summary'))
        await pg.wait_for_timeout(500)
        print('F3 frame log:', (await fr.locator('#log').inner_text()).strip().split('\n'))
        print('F4 posted labels:', [b['labels'] for b in POSTS])
        await ctx.close()
asyncio.run(main())
