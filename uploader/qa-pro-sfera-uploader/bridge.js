// Мост между страницей QA pro и расширением.
// Страница шлёт { source: 'qa-pro', id, type, ... } двумя каналами: window.postMessage и событием документа 'qa-pro:to-uploader'
// (detail — JSON-строка). Мост отвечает { source: 'qa-pro-sfera-uploader', id, type, ... } тоже двумя каналами
// ('qa-pro:from-uploader'), страница берёт первый ответ. Два канала — на случай, если окружение страницы фильтрует postMessage.
// Сам мост ничего не загружает: он открывает окно расширения, где пользователь выбирает раздел и подтверждает загрузку.
(() => {
  // Расширение могли обновить, пока страница открыта: старый экземпляр моста тогда «осиротевший» и должен молчать.
  const alive = () => { try { return !!chrome.runtime?.id; } catch { return false; } };
  const FLAG = '__qaProSferaBridge11';
  try { if (typeof window[FLAG] === 'function' && window[FLAG]()) return; } catch { /* чужое значение */ }
  window[FLAG] = alive;

  const PAGE = 'qa-pro', EXT = 'qa-pro-sfera-uploader', EVT_IN = 'qa-pro:to-uploader', EVT_OUT = 'qa-pro:from-uploader';
  const reply = (id, type, data) => {
    const msg = { source: EXT, id, type, ...data };
    try { window.postMessage(msg, '*'); } catch { /* окно закрывается */ }
    try { document.dispatchEvent(new CustomEvent(EVT_OUT, { detail: JSON.stringify(msg) })); } catch { /* нет документа */ }
  };
  const ask = (msg) => new Promise((resolve) => {
    try {
      chrome.runtime.sendMessage(msg, (r) => resolve(chrome.runtime.lastError ? { ok: false, error: 'Расширение перезапущено — обновите страницу.' } : r));
    } catch { resolve({ ok: false, error: 'Расширение перезапущено — обновите страницу.' }); }
  });

  const seen = new Set();
  async function handle(d) {
    if (!alive() || !d || d.source !== PAGE || typeof d.id !== 'string' || typeof d.type !== 'string') return;
    const key = d.type + ':' + d.id;
    if (seen.has(key)) return; // одно и то же сообщение пришло обоими каналами
    seen.add(key);
    if (seen.size > 200) seen.delete(seen.values().next().value);
    if (d.type === 'SFERA_PING') {
      reply(d.id, 'SFERA_HELLO', {}); // мост на странице есть — дальше отвечает фоновая часть
      const r = await ask({ type: 'PING' });
      if (r?.ok) reply(d.id, 'SFERA_PONG', { version: r.version, baseUrl: r.baseUrl, bridge: !!r.bridge, bridgeVersion: r.bridgeVersion || '' });
      else reply(d.id, 'SFERA_ERROR', { error: r?.error || 'Расширение не ответило.' });
    } else if (d.type === 'SFERA_UPLOAD') {
      const r = await ask({ type: 'UPLOAD_REQUEST', requestId: d.id, cases: d.cases, title: d.title });
      if (!r?.ok) reply(d.id, 'SFERA_ERROR', { error: r?.error || 'Расширение не ответило.' });
      else reply(d.id, 'SFERA_OPENED', { jobId: r.jobId });
    } else if (d.type === 'CTX_PING' || d.type === 'CTX_CALL' || d.type === 'CTX_GH') {
      // источник контекста QA pro: папка или git через мост, GitHub через API. Доступ — после «Разрешить» в окне загрузчика.
      const r = await ask(d.type === 'CTX_PING' ? { type: 'CTX_PING' } : d.type === 'CTX_CALL' ? { type: 'CTX_CALL', tool: d.tool, args: d.args } : { type: 'CTX_GH', op: d.op, args: d.args });
      if (r?.ok) reply(d.id, 'CTX_RESULT', d.type === 'CTX_PING' ? { data: { version: r.version, bridge: !!r.bridge, gh: !!r.gh } } : { data: r.data });
      else reply(d.id, 'CTX_ERROR', { error: r?.error || 'Расширение не ответило.', code: r?.code || '' });
    }
  }

  window.addEventListener('message', (e) => { if (e.source === window) handle(e.data); });
  document.addEventListener(EVT_IN, (e) => {
    if (typeof e.detail !== 'string') return;
    let d; try { d = JSON.parse(e.detail); } catch { return; }
    handle(d);
  });

  chrome.runtime.onMessage.addListener((m) => {
    if (!alive()) return;
    if (m?.type === 'QA_TICK') { reply('tick-' + Date.now() + Math.random().toString(36).slice(2, 6), 'SFERA_TICK', {}); return; }
    if (m?.type === 'SFERA_RESULT' && m.requestId) reply(m.requestId, 'SFERA_RESULT', { results: m.results || [], cancelled: !!m.cancelled, section: m.section || null });
  });
})();
