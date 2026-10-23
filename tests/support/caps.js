// Возможности артефакта для тестов: база (через Python), модель (через Python), пользователь, скачивание файлов.
(() => {
  const op = (...a) => window.__dbop(...a);
  const deepFreeze = (o) => { if (o && typeof o === 'object' && !Object.isFrozen(o)) { Object.freeze(o); for (const v of Object.values(o)) deepFreeze(v); } return o; };   // как в настоящей базе: документ из снимка заморожен
  const snapOf = (path, d) => ({ id: path.split('/').pop(), exists: d != null, data: () => (d == null ? undefined : deepFreeze(d)), metadata: { fromCache: false, hasPendingWrites: false } });
  const poll = (fn, next) => {
    let last, alive = true;
    const tick = async () => { if (!alive) return; try { const v = await fn(); const k = JSON.stringify(v.key); if (k !== last) { last = k; next(v.snap); } } catch (e) { /* ignore */ } if (alive) setTimeout(tick, 200); };
    tick(); return () => { alive = false; };
  };
  const clone = (d) => JSON.parse(JSON.stringify(d));
  // window.__dbLimit — как в настоящей базе: запись больше 256 КиБ отклоняется (invalid_argument)
  const tooBig = (d) => { if (window.__dbLimit && new TextEncoder().encode(JSON.stringify(d)).length > 262144) throw { code: 'invalid_argument', message: 'document over 256 KiB' }; };
  // window.__dbFailGet — регулярное выражение пути: чтение такой записи падает (unavailable)
  const failGet = (path) => { if (window.__dbFailGet && new RegExp(window.__dbFailGet).test(path)) throw { code: 'unavailable', message: 'test failure' }; };
  const docRef = (path) => ({
    id: path.split('/').pop(), path,
    get: async () => { failGet(path); return snapOf(path, await op('get', path)); },
    set: async (d) => { tooBig(d); await op('set', path, clone(d)); },
    update: async (d) => { tooBig(d); const r = await op('update', path, clone(d)); if (r === 'missing') throw { code: 'invalid_argument', message: 'missing' }; },
    delete: async () => { await op('delete', path); },
    acquire: async (o) => op('acquire', path, o),
    onSnapshot: (next) => poll(async () => { const d = await op('get', path); return { key: d, snap: snapOf(path, d) }; }, next),
    collection: (sub) => colQuery(path + '/' + sub),
  });
  const colQuery = (path, filters = [], ord = null, lim = 1000) => {
    const run = async () => {
      const rows = await op('list', path, { filters, ord, lim });
      const docs = rows.map(([p, d]) => snapOf(p, d));
      return { key: rows, snap: { docs, size: docs.length, empty: !docs.length, docChanges: () => [], metadata: { fromCache: false, hasPendingWrites: false } } };
    };
    return {
      path, where: (f, o, v) => colQuery(path, [...filters, [f, o, v]], ord, lim),
      orderBy: (f, d) => colQuery(path, filters, [f, d || 'asc'], lim), limit: (n) => colQuery(path, filters, ord, n),
      get: async () => (await run()).snap, doc: (id) => docRef(path + '/' + (id || 'd' + Math.random().toString(36).slice(2))),
      add: async (d) => { const r = docRef(path + '/d' + Math.random().toString(36).slice(2)); await r.set(d); return r; },
      onSnapshot: (next) => poll(run, next),
    };
  };
  const db = { doc: docRef, collection: (p) => colQuery(p) };
  const sample = async () => ({ text: 'x', truncated: false });
  sample.limits = async () => ({ maxPromptBytes: 262144, tools: { maxCount: 8 }, ...(window.__sampleImages ? { images: { maxCount: 5, maxInputBytes: 5e6, mediaTypes: ['image/jpeg', 'image/png'] } } : {}) });
  // Модель живёт в Python (window.__model). Ответ: { json } или { __error: { code, message } };
  // { __tools: [{ name, input }] } — модель «вызывает» инструменты агента, результаты кладутся в window.__toolResults.
  sample.json = async (prompt, opts) => {
    const info = { modelTier: opts && opts.modelTier, tools: ((opts && opts.tools) || []).map((t) => t.name), images: opts && opts.images ? [...opts.images].length : 0, cache: opts && opts.cache };
    await new Promise((r) => setTimeout(r, window.__sampleDelay ?? 15));
    opts?.onText?.({ text: 'x'.repeat(500), delta: 'x' });
    const res = await window.__model(prompt, info);
    if (res && res.__error) throw res.__error;
    if (res && res.__tools) {
      window.__toolResults = window.__toolResults || [];
      for (const t of res.__tools) {
        const tool = ((opts && opts.tools) || []).find((x) => x.name === t.name);
        try { window.__toolResults.push({ name: t.name, result: tool ? await tool.execute(t.input || {}) : 'нет инструмента' }); } catch (e) { window.__toolResults.push({ name: t.name, error: String(e) }); }
      }
    }
    return res ? res.json : {};
  };
  const user = { id: async () => 'u_test', canEdit: async () => true, isOwner: async () => true };
  const downloads = { save: async ({ filename, data }) => {
    (window.__downloads = window.__downloads || []).push({ filename, len: data.length ?? data.size, text: typeof data === 'string' ? data : null });
    window.__dl = { filename, len: data.length ?? data.size }; window.__dlBlob = data instanceof Blob ? data : null; window.__dlData = typeof data === 'string' ? data : null;
    return { status: 'saved' };
  } };
  const caps = { sample, db, user, downloads };
  window.claude = { use: (n) => new Promise((r) => setTimeout(() => r(caps[n] || null), 20)) };
})();
