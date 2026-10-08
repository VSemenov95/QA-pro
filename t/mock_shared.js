(() => {
  const op = (...a) => window.__dbop(...a);
  // как настоящая база артефакта: документ из снимка заморожен целиком
  const deepFreeze = (o) => { if (o && typeof o === 'object' && !Object.isFrozen(o)) { Object.freeze(o); for (const v of Object.values(o)) deepFreeze(v); } return o; };
  const snapOf = (path, d) => ({ id: path.split('/').pop(), exists: d != null, data: () => (d == null ? undefined : (window.__noFreeze ? d : deepFreeze(d))), metadata: { fromCache: false, hasPendingWrites: false } });
  const poll = (fn, next) => {
    let last, alive = true;
    const tick = async () => { if (!alive) return; try { const v = await fn(); const k = JSON.stringify(v.key); if (k !== last) { last = k; next(v.snap); } } catch (e) { /* ignore */ } if (alive) setTimeout(tick, 200); };
    tick(); return () => { alive = false; };
  };
  const clone = (d) => JSON.parse(JSON.stringify(d));
  const docRef = (path) => ({
    id: path.split('/').pop(), path,
    get: async () => snapOf(path, await op('get', path)),
    set: async (d) => { await op('set', path, clone(d)); },
    update: async (d) => { const r = await op('update', path, clone(d)); if (r === 'missing') throw { code: 'invalid_argument', message: 'missing' }; },
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
  const store = new Map();
  window.__store = store;
  const sample = async () => ({ text: 'x', truncated: false });
  sample.limits = async () => ({ maxPromptBytes: 262144, tools: { maxCount: 8 }, ...(window.__sampleImages ? { images: { maxCount: 5, maxInputBytes: 5e6, mediaTypes: ['image/jpeg', 'image/png'] } } : {}) });
  window.__calls = [];
  sample.json = async (prompt, opts) => {
    (window.__tiers = window.__tiers || []).push([prompt.slice(0, 50), opts && opts.modelTier]);
    if (opts && opts.images) (window.__imgCalls = window.__imgCalls || []).push([...opts.images].map((b) => b.type + ':' + b.size));
    if (opts && opts.tools) {
      (window.__toolNames = window.__toolNames || []).push(opts.tools.map((t) => t.name));
      const kt = opts.tools.find((t) => t.name === 'search_knowledge_base');
      if (kt && !window.__kbToolRes) { try { window.__kbToolRes = await kt.execute({ query: 'лимит запросов на сброс пароля' }); } catch (e) { window.__kbToolRes = String(e); } }
    }
    await new Promise(r => setTimeout(r, window.__sampleDelay || 120));
    opts?.onText?.({ text: 'x'.repeat(500), delta: 'x' });
    return window.__mockJSON(prompt);
  };
  const user = { id: async () => 'u_test', canEdit: async () => true, isOwner: async () => true };
  const downloads = { save: async ({ filename, data }) => { window.__dl = { filename, len: data.length ?? data.size }; window.__dlBlob = data instanceof Blob ? data : null; window.__dlData = typeof data === 'string' ? data : null; return { status: 'saved' }; } };
  const caps = { sample, db, user, downloads };
  window.claude = { use: (n) => new Promise(r => setTimeout(() => r(caps[n] || null), 50)) };
})();
