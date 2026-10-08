(() => {
  const store = new Map(); const subs = [];
  const notify = () => subs.forEach(s => s());
  const docRef = (path) => ({
    id: path.split('/').pop(), path,
    get: async () => ({ id: path.split('/').pop(), exists: store.has(path), data: () => store.get(path) }),
    set: async (d) => { store.set(path, JSON.parse(JSON.stringify(d))); notify(); },
    update: async (d) => { store.set(path, { ...store.get(path), ...d }); notify(); },
    delete: async () => { store.delete(path); notify(); },
    onSnapshot: () => () => {},
  });
  const colQuery = (path, filters = [], ord = null, lim = 1000) => {
    const run = () => {
      let docs = [...store.entries()].filter(([p]) => p.startsWith(path + '/') && p.slice(path.length + 1).split('/').length === 1)
        .map(([p, d]) => ({ id: p.split('/').pop(), exists: true, data: () => d }));
      for (const [f, , v] of filters) docs = docs.filter(x => x.data()[f] === v);
      if (ord) docs.sort((a, b) => (a.data()[ord[0]] - b.data()[ord[0]]) * (ord[1] === 'desc' ? -1 : 1));
      docs = docs.slice(0, lim);
      return { docs, size: docs.length, empty: !docs.length, docChanges: () => [], metadata: {} };
    };
    return {
      path, where: (f, op, v) => colQuery(path, [...filters, [f, op, v]], ord, lim),
      orderBy: (f, d) => colQuery(path, filters, [f, d], lim), limit: (n) => colQuery(path, filters, ord, n),
      get: async () => run(), doc: (id) => docRef(path + '/' + id),
      onSnapshot: (next) => { const s = () => next(run()); subs.push(s); setTimeout(s, 10); return () => {}; },
    };
  };
  const db = { doc: docRef, collection: (p) => colQuery(p) };
  window.__store = store;
  const sample = async () => ({ text: 'x', truncated: false });
  sample.limits = async () => ({ maxPromptBytes: 262144, tools: { maxCount: 8 } });
  window.__calls = [];
  sample.json = async (prompt, opts) => {
    (window.__tiers = window.__tiers || []).push([prompt.slice(0, 50), opts && opts.modelTier]);
    await new Promise(r => setTimeout(r, 120));
    opts?.onText?.({ text: 'x'.repeat(500), delta: 'x' });
    return window.__mockJSON(prompt);
  };
  const user = { id: async () => 'u_test', canEdit: async () => true, isOwner: async () => true };
  const downloads = { save: async ({ filename, data }) => { window.__dl = { filename, len: data.length ?? data.size }; window.__dlBlob = data instanceof Blob ? data : null; window.__dlData = typeof data === 'string' ? data : null; return { status: 'saved' }; } };
  const caps = { sample, db, user, downloads };
  window.claude = { use: (n) => new Promise(r => setTimeout(() => r(caps[n] || null), 50)) };
})();
