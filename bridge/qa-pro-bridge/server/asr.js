'use strict';
// Распознавание речи на этом компьютере: Whisper через transformers.js на WebAssembly — без установки программ.
// Звук никуда не отправляется. При первом запуске ядро скачивает:
//  • распознаватель — пакеты npm с закреплёнными версиями и проверкой хэша (≈36 МБ, registry.npmjs.org или зеркало);
//  • модель Whisper — с Hugging Face или его зеркала (small ≈ 250 МБ, base ≈ 80 МБ).
// Модель можно положить вручную: ~/.qa-pro-bridge/models/Xenova/whisper-small/… (файлы как в репозитории модели).
const fs = require('fs');
const path = require('path');
const os = require('os');
const crypto = require('crypto');
const zlib = require('zlib');
const { Worker } = require('worker_threads');

const RT_NAME = 'tf-4.3.0_ort-1.31.0-dev_r2';
const RUNTIME = [
  { name: '@huggingface/transformers', version: '4.3.0', integrity: 'sha512-fL1A/WUZwouPrOlYxU5dzIwD2T5J781JiB2jDR8bFe5DwCj0Gfudq+NEXCMno49kQgajHA7xQkrRLJlqG1veEA==',
    into: '@huggingface/transformers', keep: (p) => ['package.json', 'LICENSE', 'dist/transformers.node.mjs'].includes(p) },
  { name: 'onnxruntime-common', version: '1.30.0', integrity: 'sha512-7fdVWjAID1dVhH/G8qK3APARunV4VkBFoCQAP7qp4Wkab0mrorvmc+sqiT+mKXOzDqdjN5j+/Z9nb4gzNPWcyA==',
    into: 'onnxruntime-common', keep: (p) => p === 'package.json' || p.startsWith('dist/') },
  { name: 'onnxruntime-web', version: '1.31.0-dev.20260914-8d85527a0', integrity: 'sha512-Iy7rtadoBgxS/LLvDr3QW38DB1PNXRnr0GJMcL0TAt7c9qjgVQl83UlGCVyeAnK2InpmW8Uc3PL8XIuqtDeF6g==',
    into: 'onnxruntime-web', keep: (p) => ['package.json', 'LICENSE', 'dist/ort.node.min.js', 'dist/ort.node.min.mjs', 'dist/ort-wasm-simd-threaded.mjs', 'dist/ort-wasm-simd-threaded.wasm'].includes(p) },
  { name: 'onnxruntime-common', version: '1.31.0-dev.20260911-2a43ec07e', integrity: 'sha512-gBuF6U32YErKIAt+yD7DeGBpjRxhJ1uJwako6ygjokSZULDU6Pd+KWComX8Tumk1hYVHRxjPj7mdMnD0ryAPOw==',
    into: 'onnxruntime-web/node_modules/onnxruntime-common', keep: (p) => p === 'package.json' || p.startsWith('dist/') },
];
// Нативный onnxruntime-node и sharp не нужны: подменяем их WebAssembly-сборкой и пустышкой.
const SHIMS = {
  'onnxruntime-node/package.json': JSON.stringify({ name: 'onnxruntime-node', version: '0.0.0-wasm', type: 'module', exports: { '.': { import: './index.js', require: './index.cjs' } } }),
  'onnxruntime-node/index.js': "export * from 'onnxruntime-web';\nimport * as o from 'onnxruntime-web';\nexport default o;\n",
  'onnxruntime-node/index.cjs': "module.exports = require('onnxruntime-web');\n",
  'sharp/package.json': JSON.stringify({ name: 'sharp', version: '0.0.0-stub', type: 'module', exports: { '.': { import: './index.js', require: './index.cjs' } } }),
  'sharp/index.js': "export default function sharp() { throw new Error('Обработка изображений в мосте не нужна'); }\n",
  'sharp/index.cjs': "module.exports = function sharp() { throw new Error('Обработка изображений в мосте не нужна'); };\n",
};
const MODELS = {
  small: { id: 'Xenova/whisper-small', title: 'Whisper small', size: '≈ 250 МБ' },
  base: { id: 'Xenova/whisper-base', title: 'Whisper base', size: '≈ 80 МБ' },
};
// G.711 μ-law → линейный звук: страница присылает 8 бит на отсчёт, вдвое меньше данных при том же качестве для речи.
const MULAW = new Float32Array(256);
for (let i = 0; i < 256; i++) {
  const u = ~i & 0xff, sign = u & 0x80, exp = (u >> 4) & 7, man = u & 0x0f;
  let s = ((man << 3) + 0x84) << exp; s -= 0x84;
  MULAW[i] = (sign ? -s : s) / 32768;
}

function untar(buf) {
  const out = new Map();
  let off = 0, longName = null;
  while (off + 512 <= buf.length) {
    const h = buf.subarray(off, off + 512);
    if (h.every((b) => b === 0)) break;
    const str = (a, b) => h.subarray(a, b).toString('utf8').replace(/\0.*$/s, '');
    let name = str(0, 100);
    const size = parseInt(str(124, 136).trim() || '0', 8);
    const type = String.fromCharCode(h[156] || 48);
    const prefix = str(345, 500);
    if (prefix) name = prefix + '/' + name;
    const body = buf.subarray(off + 512, off + 512 + size);
    if (type === 'x') { const m = /\d+ path=([^\n]+)\n/.exec(body.toString('utf8')); longName = m ? m[1] : null; }
    else if (type === 'L') longName = body.toString('utf8').replace(/\0.*$/s, '');
    else { if (type === '0' || type === '\0') out.set((longName || name).replace(/^package\//, ''), Buffer.from(body)); longName = null; }
    off += 512 + Math.ceil(size / 512) * 512;
  }
  return out;
}

module.exports = function createAsr({ dir, log }) {
  const registry = ((process.env.QA_PRO_BRIDGE_NPM || '').trim() || 'https://registry.npmjs.org').replace(/\/+$/, '');
  const hfHost = (process.env.QA_PRO_BRIDGE_HF || '').trim();
  const rtDir = path.join(dir, 'runtime', RT_NAME);
  const modelsDir = path.join(dir, 'models');
  const threads = Math.max(1, Math.min(8, (os.cpus()?.length || 2) - 1));
  const A = { state: 'idle', model: '', step: '', file: '', loaded: 0, total: 0, error: '', loading: null, busy: Promise.resolve(), done: 0, seconds: 0, files: {} };

  const status = () => ({
    state: A.state, model: A.model, title: MODELS[A.model]?.title || '', size: MODELS[A.model]?.size || '', step: A.step, file: A.file,
    loaded: A.loaded, total: A.total, pct: A.total ? Math.round((A.loaded / A.total) * 100) : 0, error: A.error, threads,
    transcribed: { chunks: A.done, seconds: Math.round(A.seconds) }, models: Object.fromEntries(Object.entries(MODELS).map(([k, m]) => [k, { title: m.title, size: m.size }])),
  });

  async function download(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${new URL(url).host} ответил ${r.status}`);
    const total = Number(r.headers.get('content-length')) || 0;
    const parts = []; let got = 0;
    for await (const c of r.body) { parts.push(Buffer.from(c)); got += c.length; A.loaded = got; A.total = total; }
    return Buffer.concat(parts);
  }
  let rtLoading = null;
  const ensureRuntime = () => (rtLoading ||= fetchRuntime().finally(() => { rtLoading = null; }));
  async function fetchRuntime() {
    if (fs.existsSync(path.join(rtDir, '.ready'))) return;
    const nm = path.join(rtDir, 'node_modules');
    for (const pkg of RUNTIME) {
      const base = pkg.name.split('/').pop();
      A.step = 'runtime'; A.file = `${pkg.name}@${pkg.version}`; A.loaded = 0; A.total = 0;
      let tgz;
      try { tgz = await download(`${registry}/${pkg.name}/-/${base}-${pkg.version}.tgz`); }
      catch (e) { throw new Error(`Не удалось скачать распознаватель из ${new URL(registry).host}: ${e.message}. Проверьте доступ к реестру npm или укажите зеркало в настройках моста.`); }
      const sum = 'sha512-' + crypto.createHash('sha512').update(tgz).digest('base64');
      if (sum !== pkg.integrity) throw new Error(`Пакет ${pkg.name} не прошёл проверку подлинности — скачивание прервано.`);
      for (const [p, data] of untar(zlib.gunzipSync(tgz))) {
        if (!pkg.keep(p)) continue;
        const to = path.join(nm, pkg.into, p);
        fs.mkdirSync(path.dirname(to), { recursive: true });
        fs.writeFileSync(to, data);
      }
    }
    for (const [p, text] of Object.entries(SHIMS)) { const to = path.join(nm, p); fs.mkdirSync(path.dirname(to), { recursive: true }); fs.writeFileSync(to, text); }
    fs.writeFileSync(path.join(rtDir, '.ready'), new Date().toISOString());
  }

  // Сам Whisper работает в отдельном потоке (asr-worker.js): ядро моста остаётся отзывчивым во время распознавания.
  let worker = null, wid = 0;
  const waits = new Map();
  function stopWorker(reason) {
    const w = worker; worker = null;
    for (const [, cb] of waits) cb.reject(Object.assign(new Error(reason || 'Распознаватель остановлен.'), { code: 'not_ready' }));
    waits.clear();
    if (w) w.terminate().catch(() => {});
  }
  function prepare(model = 'small') {
    if (!MODELS[model]) model = 'small';
    if (A.state === 'ready' && A.model === model) return status();
    if (A.loading && A.model === model) return status();
    if (A.loading || worker) stopWorker('Выбрана другая модель.');
    A.state = 'loading'; A.model = model; A.error = ''; A.files = {};
    const my = (A.loading = (async () => {
      await ensureRuntime();
      if (A.loading !== my) return;
      A.step = 'init'; A.file = ''; A.loaded = 0; A.total = 0;
      const w = new Worker(path.join(__dirname, 'asr-worker.js'), { workerData: { rtDir, modelsDir, hfHost, threads, modelId: MODELS[model].id } });
      worker = w;
      await new Promise((resolve, reject) => {
        w.on('message', (m) => {
          if (worker !== w) return;
          if (m.t === 'step') A.step = m.step;
          else if (m.t === 'progress') {
            A.files[m.file] = { loaded: m.loaded, total: m.total }; A.file = m.file;
            A.loaded = Object.values(A.files).reduce((a, f) => a + f.loaded, 0);
            A.total = Object.values(A.files).reduce((a, f) => a + f.total, 0);
          } else if (m.t === 'ready') resolve();
          else if (m.t === 'error') reject(new Error(`Не удалось получить модель ${MODELS[model].title}: ${m.error}. Нужен доступ к huggingface.co (или зеркало в настройках моста), либо положите файлы модели в ${path.join(modelsDir, MODELS[model].id)}.`));
          else if ((m.t === 'result' || m.t === 'fail') && waits.has(m.id)) {
            const cb = waits.get(m.id); waits.delete(m.id);
            if (m.t === 'result') cb.resolve(m); else cb.reject(new Error('Распознавание не удалось: ' + m.error));
          }
        });
        w.on('error', (e) => { reject(e); if (worker === w) { A.state = 'error'; A.error = 'Распознаватель упал: ' + String(e?.message || e).slice(0, 200); stopWorker(A.error); } });
        w.on('exit', (code) => { reject(new Error('Поток распознавания завершился, код ' + code)); if (worker === w) { A.state = 'error'; A.error = A.error || 'Поток распознавания завершился (возможно, не хватило памяти).'; stopWorker(A.error); } });
      });
      if (A.loading !== my) return;
      A.state = 'ready'; A.step = 'ready'; A.file = '';
      log('распознаватель готов:', MODELS[model].title, 'потоков', threads);
    })().catch((e) => { if (A.loading !== my) return; A.state = 'error'; A.step = ''; A.error = String(e?.message || e); log('распознаватель:', A.error); stopWorker(A.error); })
      .finally(() => { if (A.loading === my) A.loading = null; }));
    return status();
  }

  function transcribe(args = {}) {
    if (A.state !== 'ready' || !worker) {
      const e = new Error(A.state === 'error' ? A.error : A.state === 'loading' ? 'Распознаватель ещё готовится.' : 'Распознаватель не запущен — сначала asr_prepare.');
      e.code = 'not_ready'; throw e;
    }
    const buf = Buffer.from(String(args.audio || ''), 'base64');
    if (!buf.length) throw new Error('Нет звука.');
    if (buf.length > 16000 * 60) throw new Error('Фрагмент длиннее минуты — разбейте его.');
    const pcm = new Float32Array(buf.length);
    for (let i = 0; i < buf.length; i++) pcm[i] = MULAW[buf[i]];
    const language = String(args.language || 'russian').slice(0, 30);
    const run = () => new Promise((resolve, reject) => {
      if (!worker) return reject(Object.assign(new Error(A.error || 'Распознаватель остановлен.'), { code: 'not_ready' }));
      const id = ++wid;
      waits.set(id, { resolve, reject });
      worker.postMessage({ t: 'run', id, pcm, language }, [pcm.buffer]);
    }).then((m) => { A.done++; A.seconds += buf.length / 16000; return { text: m.text, language: m.language || language, ms: m.ms, seconds: buf.length / 16000 }; });
    const p = A.busy.then(run, run);
    A.busy = p.catch(() => {});
    return p;
  }

  return { status, prepare, transcribe, MODELS };
};
