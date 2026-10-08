'use strict';
// Отдельный поток для Whisper: вычисления WebAssembly синхронны и иначе останавливали бы ядро моста
// (связь с загрузчиком, задания Сферы, вызовы приложения Claude) на всё время распознавания.
const { parentPort, workerData } = require('worker_threads');
const path = require('path');
const zlib = require('zlib');
const { pathToFileURL } = require('url');

const { rtDir, modelsDir, hfHost, threads, modelId } = workerData;
let pipe = null, tf = null;

async function load() {
  tf = await import(pathToFileURL(path.join(rtDir, 'node_modules', '@huggingface', 'transformers', 'dist', 'transformers.node.mjs')).href);
  const env = tf.env;
  env.allowLocalModels = true; env.localModelPath = modelsDir + path.sep; env.cacheDir = path.join(modelsDir, '.cache');
  env.allowRemoteModels = true;
  if (hfHost) env.remoteHost = hfHost.replace(/\/*$/, '/');
  env.backends.onnx.wasm.wasmPaths = pathToFileURL(path.join(rtDir, 'node_modules', 'onnxruntime-web', 'dist') + path.sep).href;
  env.backends.onnx.wasm.numThreads = threads;
  parentPort.postMessage({ t: 'step', step: 'model' });
  let last = 0;
  pipe = await tf.pipeline('automatic-speech-recognition', modelId, {
    dtype: 'q8', device: 'cpu',
    progress_callback: (p) => {
      if (p.status !== 'progress' || !p.file) return;
      const now = Date.now();
      if (now - last < 250 && p.loaded !== p.total) return;
      last = now;
      parentPort.postMessage({ t: 'progress', file: p.file, loaded: p.loaded || 0, total: p.total || 0 });
    },
  });
}

// Без языка transformers.js считает речь английской, поэтому язык определяем сами: один шаг декодера
// после <|startoftranscript|> — что вероятнее, русский или английский (на созвонах команды других языков не бывает,
// а малые модели легко путают русский с польским или украинским).
async function detectLanguage(pcm) {
  const model = pipe.model, gc = model.generation_config || {};
  const langs = Object.entries(gc.lang_to_id || {}).filter(([k]) => k === '<|ru|>' || k === '<|en|>');
  if (langs.length < 2) return 'russian';
  const feats = await pipe.processor(pcm.subarray(0, 30 * 16000));
  const start = new tf.Tensor('int64', BigInt64Array.from([BigInt(gc.decoder_start_token_id || 50258)]), [1, 1]);
  const out = await model({ input_features: feats.input_features, decoder_input_ids: start });
  const lg = out.logits, V = lg.dims[lg.dims.length - 1], base = (lg.dims[1] - 1) * V, data = lg.data;
  let best = langs[0];
  for (const x of langs) if (data[base + x[1]] > data[base + best[1]]) best = x;
  return best[0].replace(/[<|>]/g, '');
}
// Признак «зацикливания» (Whisper повторяет одну фразу): текст сжимается слишком хорошо.
const looped = (t) => t.length > 60 && t.length / zlib.deflateSync(Buffer.from(t)).length > 2.4;
parentPort.on('message', async (m) => {
  if (m.t === 'run') {
    try {
      const t0 = Date.now();
      const language = m.language === 'auto' ? await detectLanguage(m.pcm) : m.language;
      const opts = { language, task: 'transcribe', chunk_length_s: 30, stride_length_s: 5, max_new_tokens: 320 };
      let text = String((await pipe(m.pcm, opts))?.text || '').trim();
      if (looped(text)) { text = String((await pipe(m.pcm, { ...opts, no_repeat_ngram_size: 4 }))?.text || '').trim(); if (looped(text)) text = ''; }
      parentPort.postMessage({ t: 'result', id: m.id, text, language, ms: Date.now() - t0 });
    } catch (e) {
      parentPort.postMessage({ t: 'fail', id: m.id, error: String(e?.message || e).slice(0, 300) });
    }
  }
});

load().then(() => parentPort.postMessage({ t: 'ready' }), (e) => parentPort.postMessage({ t: 'error', error: String(e?.message || e).slice(0, 300) }));
