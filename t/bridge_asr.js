// Мост 1.2: распознавание речи — распознаватель из npm (с проверкой хэша), модель из папки, звук μ-law.
const { spawn, execFileSync } = require('child_process'), path = require('path'), fs = require('fs'), os = require('os'), http = require('http');
const PORT = 48100 + Math.floor(Math.random() * 80), DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'qpa-'));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// модель: копия Xenova/whisper-base (зеркало из npm) в папку моделей моста
const src = '/tmp/tfjs/node_modules/sts-whisper-base/models/Xenova/whisper-base';
fs.cpSync(src, path.join(DIR, 'models', 'Xenova', 'whisper-base'), { recursive: true });
const p = spawn(process.execPath, [path.join(__dirname, '../bridge/qa-pro-bridge/server/index.js')], { env: { ...process.env, QA_PRO_BRIDGE_PORT: String(PORT), QA_PRO_BRIDGE_DIR: DIR } });
let out = ''; const pend = new Map(); let nid = 1;
p.stdout.on('data', (d) => { out += d; let i; while ((i = out.indexOf('\n')) >= 0) { const l = out.slice(0, i); out = out.slice(i + 1); const m = JSON.parse(l); pend.get(m.id)?.(m); pend.delete(m.id); } });
p.stderr.on('data', (d) => process.stdout.write('   wrap: ' + d));
const rpc = (method, params) => new Promise((r) => { const id = nid++; pend.set(id, r); p.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n'); });
const tool = async (name, args) => { const r = (await rpc('tools/call', { name, arguments: args })).result; return r.isError ? { error: r.content[0].text } : r.structuredContent; };
function mulawB64(file) { // wav → 16 кГц моно s16 (ffmpeg) → μ-law
  const raw = execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-i', file, '-ar', '16000', '-ac', '1', '-f', 's16le', '-'], { maxBuffer: 64 << 20 });
  const out = Buffer.alloc(raw.length / 2);
  for (let i = 0; i < out.length; i++) {
    let s = raw.readInt16LE(i * 2); const sign = s < 0 ? 0x80 : 0; if (s < 0) s = -s; s = Math.min(s, 32635) + 0x84;
    let e = 7; for (let m = 0x4000; (s & m) === 0 && e > 0; m >>= 1) e--;
    out[i] = ~(sign | (e << 4) | ((s >> (e + 3)) & 0x0f)) & 0xff;
  }
  return out.toString('base64');
}
(async () => {
  await rpc('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 't', version: '1' } });
  const tl = await rpc('tools/list', {});
  console.log('A1 tools:', tl.result.tools.map((t) => t.name + (t.annotations.readOnlyHint ? '(ro)' : '')).join(', '));
  console.log('A2 before:', JSON.stringify((await tool('asr_transcribe', { audio: 'AAAA' }))));
  let st = await tool('asr_prepare', { model: 'base' }); const t0 = Date.now(); let last = '';
  while (st.state === 'loading' && Date.now() - t0 < 240000) { await sleep(1000); st = await tool('asr_status', {}); const k = st.step + ' ' + (st.file || '') + ' ' + st.pct; if (st.step !== last) { console.log('   step:', k); last = st.step; } }
  console.log('A3 prepared in', Math.round((Date.now() - t0) / 1000), 's:', st.state, st.title, st.error || '', '| threads', st.threads);
  const rt = path.join(DIR, 'runtime'); const du = execFileSync('du', ['-sh', rt]).toString().trim();
  console.log('A4 runtime on disk:', du);
  // ядро не должно «замирать» во время распознавания: /health отвечает быстро
  let maxLag = 0, probing = true;
  (async () => { while (probing) { const a = Date.now(); await new Promise((r) => { const q = http.get({ host: '127.0.0.1', port: PORT, path: '/health', timeout: 30000 }, (res) => { res.resume(); res.on('end', r); }); q.on('error', r); }); maxLag = Math.max(maxLag, Date.now() - a); await sleep(100); } })();
  for (const [f, lang] of [['asr/jfk.wav', 'english'], ['asr/speech.wav', 'russian']]) {
    const t1 = Date.now(); const r = await tool('asr_transcribe', { audio: mulawB64(path.join(__dirname, '..', f)), language: lang });
    console.log('A5', f, Date.now() - t1, 'ms:', JSON.stringify(r.text || r.error));
  }
  probing = false; console.log('A5b max /health latency during ASR:', maxLag, 'ms');
  console.log('A6 ping asr:', JSON.stringify((await tool('ping', {})).asr.transcribed));
  // повторный запуск: распознаватель уже на диске, не скачивается
  const tok = fs.readFileSync(path.join(DIR, 'token'), 'utf8');
  await new Promise((r) => { const q = http.request({ host: '127.0.0.1', port: PORT, method: 'POST', path: '/shutdown', headers: { 'x-qa-pro-bridge-token': tok } }, (res) => { res.resume(); res.on('end', r); }); q.end(); });
  p.kill(); process.exit(0);
})().catch((e) => { console.error('FAIL', e); p.kill(); process.exit(1); });
