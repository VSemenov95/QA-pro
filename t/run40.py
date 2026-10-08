# Голосовые команды: разбор фраз, запись с микрофона (фейковое устройство Chrome) и ответ моста (фейковый загрузчик в странице), выполнение.
import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run27 import dbop, serve, D
from playwright.async_api import async_playwright
CASES = [('открой требования', 'tab', 'reqs'), ('Открой вопросы', 'tab', 'questions'), ('покажи тест-кейсы', 'tab', 'cases'),
         ('перейди в черновик', 'tab', 'draft'), ('черновик', 'tab', 'draft'), ('запусти генерацию', 'run', None),
         ('запусти ревью', 'review', None), ('сгенерируй', 'run', None), ('остановить', 'stop', None), ('помощь', 'help', None),
         ('да', 'confirm', None), ('абракадабра', None, None), ('', None, None)]
# фейковый загрузчик: отвечает на пинг и на вызовы моста (распознавание возвращает window.__voiceText)
FAKE_EXT = """
window.__voiceText = ''; window.__asrCalls = 0; window.__asrBytes = 0; window.__asrTools = [];
window.addEventListener('message', (e) => {
  const d = e.data; if (!d || d.source !== 'qa-pro' || e.source !== window) return;
  const reply = (o) => window.postMessage(Object.assign({ source: 'qa-pro-sfera-uploader', id: d.id }, o), '*');
  if (d.type === 'SFERA_PING') { reply({ type: 'SFERA_HELLO' }); setTimeout(() => reply({ type: 'SFERA_PONG', version: '1.5.0', baseUrl: '', bridge: true, bridgeVersion: '1.2.0' }), 50); }
  else if (d.type === 'SFERA_RPC') {
    const t = d.tool, a = d.args || {}; let result = {};
    window.__asrTools.push(t);
    if (t === 'asr_status') result = { state: 'ready', model: 'small' };
    else if (t === 'asr_prepare') result = { state: 'ready', model: a.model };
    else if (t === 'asr_transcribe') { window.__asrCalls++; window.__asrBytes = (a.audio || '').length; result = { text: window.__voiceText }; }
    reply({ type: 'SFERA_RPC_RESULT', ok: true, result });
  }
});
"""
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'])
        errs = []
        ctx = await b.new_context(viewport={'width': 1360, 'height': 900}, permissions=['microphone'])
        await ctx.expose_binding('__dbop', dbop)
        await ctx.add_init_script(script="window.__qaTest = true;")
        for f in ('mockgen.js', 'mock_shared.js'): await ctx.add_init_script(path=os.path.join(D, f))
        await ctx.add_init_script(script=FAKE_EXT)
        await ctx.route('http://localhost/**', serve)
        pg = await ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        await pg.goto('http://localhost/'); await pg.wait_for_timeout(1500)
        bad = 0
        for text, want, arg in CASES:
            got = await pg.evaluate("(t) => __qa.voiceParse(t)", text)
            ok = (got is None and want is None) or (got and got['action'] == want and (arg is None or got.get('tab') == arg))
            bad += 0 if ok else 1
            print('P', repr(text), '->', got, 'OK' if ok else 'FAIL')
        async def say(text):
            await pg.evaluate("(t) => { window.__voiceText = t; }", text)
            await pg.click('#btn-voice'); await pg.wait_for_timeout(1500); await pg.click('#btn-voice')
            await pg.wait_for_timeout(1200)
        await pg.click('#btn-voice'); await pg.wait_for_timeout(1000)
        print('R1 recording:', await pg.evaluate("document.querySelector('#btn-voice').getAttribute('aria-pressed')"), '| status:', await pg.inner_text('#voice-status'))
        await pg.evaluate("(t) => { window.__voiceText = t; }", 'открой требования')
        await pg.click('#btn-voice')
        await pg.wait_for_function("() => window.__asrCalls > 0", timeout=20000)
        await pg.wait_for_timeout(600)
        print('R2 asr calls:', await pg.evaluate('window.__asrCalls'), '| audio b64 length:', await pg.evaluate('window.__asrBytes'), '| tools:', await pg.evaluate('window.__asrTools'))
        print('R2 active tab:', await pg.evaluate("document.querySelector('[role=tab][aria-selected=true]')?.id"), '| status:', await pg.inner_text('#voice-status'))
        await say('запусти генерацию')
        print('R3 run pending:', await pg.inner_text('#voice-status'), '| running:', await pg.evaluate('__qa.S.running'))
        await say('да')
        print('R4 after yes:', await pg.inner_text('#voice-status'))
        await say('абракадабра')
        print('R5 unknown:', await pg.inner_text('#voice-status'))
        print('bad parses:', bad, '| ERRORS:', errs or 'none')
        await b.close()
asyncio.run(main())
