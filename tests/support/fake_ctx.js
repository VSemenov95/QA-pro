// Загрузчик QA pro 1.8 «понарошку» для тестов источника контекста: отвечает странице на CTX_PING, CTX_CALL и CTX_GH
// так же, как bridge.js настоящего расширения, а файлы держит в памяти страницы:
//   window.__repo = { files: { 'rules/generation.md': '…' }, git: { repo: true, branch: 'main', remote: 'https://…' }, calls: [] }
//   window.__gh   = { files: {…}, branch: 'main', branches: {}, calls: [] }      — репозиторий GitHub
//   window.__ctxOffline = true                                                     — загрузчика нет (страница его не видит)
(() => {
  const h = (t) => { let x = 5381; const s = String(t); for (let i = 0; i < s.length; i++) x = ((x << 5) + x + s.charCodeAt(i)) >>> 0; return 'h' + x.toString(16) + '-' + s.length; };
  window.__ctxHash = h;
  window.__repo = window.__repo || { root: '/home/qa/ctx', files: {}, git: { repo: true, branch: 'main', remote: 'https://git.test/qa/ctx.git', ahead: 0, behind: 0, changed: [] }, calls: [], pulls: 0 };
  window.__gh = window.__gh || { repo: 'team/qa-context', branch: 'main', files: {}, branches: {}, calls: [] };
  const reply = (id, type, data) => window.postMessage({ source: 'qa-pro-sfera-uploader', id, type, ...data }, '*');
  const R = () => window.__repo;
  function call(tool, a) {
    const r = R();
    r.calls.push([tool, a.op || '', a.root || a.url || '']);
    if (tool === 'context_git' && a.op === 'clone') return { root: '/home/qa/.qa-pro-bridge/repos/qa-ctx', cloned: true };
    if (a.root && !String(a.root).startsWith('/home/qa/')) throw Object.assign(new Error('Папка не разрешена для QA pro: ' + a.root), { code: 'root_not_allowed' });
    if (tool === 'context_read' && a.op === 'list') {
      const sub = a.sub ? a.sub + '/' : '';
      return { root: a.root, name: 'ctx', files: Object.keys(r.files).filter((p) => p.startsWith(sub)).map((p) => ({ path: p, size: r.files[p].length, mtime: 1 })), git: r.git };
    }
    if (tool === 'context_read' && a.op === 'read') return { files: a.paths.map((p) => (p in r.files ? { path: p, text: r.files[p], hash: h(r.files[p]) } : { path: p, missing: true })) };
    if (tool === 'context_read' && a.op === 'status') return r.git;
    if (tool === 'context_write' && r.failWrite) { const m = r.failWrite; r.failWrite = null; throw Object.assign(new Error(m), { code: 'cancelled' }); }
    if (tool === 'context_write') {
      const conflicts = [];
      if (!a.force) for (const f of a.files) { const cur = f.path in r.files ? h(r.files[f.path]) : null; if (f.base !== undefined && (f.base || null) !== cur && cur !== h(f.text)) conflicts.push({ path: f.path, hash: cur, text: r.files[f.path] ?? null }); }
      if (conflicts.length) return { written: [], conflicts };
      for (const f of a.files) r.files[f.path] = f.text;
      return { written: a.files.map((f) => ({ path: f.path, hash: h(f.text) })), conflicts: [] };
    }
    if (tool === 'context_git' && a.op === 'pull') { r.pulls++; if (r.onPull) r.onPull(r); return { updated: true, head: 'abc123', status: r.git }; }
    if (tool === 'context_git' && a.op === 'commit') { r.committed = (r.committed || 0) + 1; if (r.git.branch === 'main') r.git = { ...r.git, branch: 'qa-pro/2026-10-22-1830' }; return { committed: true, branch: r.git.branch, head: 'c0ffee1', files: a.paths || [] }; }
    if (tool === 'context_git' && a.op === 'push') return { branch: r.git.branch, remote: r.git.remote, pr: 'https://git.test/qa/ctx/compare/' + r.git.branch, status: r.git };
    throw Object.assign(new Error('fake: ' + tool + ' ' + a.op), { code: 'bad_op' });
  }
  function ghCall(op, a) {
    const g = window.__gh;
    g.calls.push([op, a.branch || '']);
    const files = (b) => (b === g.branch || !b ? g.files : g.branches[b] || g.files);
    if (op === 'status') return { repo: a.repo, branch: a.branch || g.branch, defaultBranch: g.branch, canPush: true, web: 'https://github.com/' + a.repo };
    if (op === 'list') return { repo: a.repo, branch: a.branch, commit: 'c1', files: Object.keys(files(a.branch)).map((p) => ({ path: p, size: 1, hash: h(files(a.branch)[p]) })), web: 'https://github.com/' + a.repo };
    if (op === 'read') { const f = files(a.branch); return { files: a.paths.map((p) => (p in f ? { path: p, text: f[p], hash: h(f[p]) } : { path: p, missing: true })) }; }
    if (op === 'commit') {
      const cur = files(a.branch);
      const conflicts = a.files.filter((f) => f.base !== undefined && (f.base || null) !== (f.path in cur ? h(cur[f.path]) : null)).map((f) => ({ path: f.path }));
      if (conflicts.length) return { committed: false, conflicts };
      const inPlace = String(a.branch).startsWith('qa-pro/');
      const target = inPlace ? a.branch : 'qa-pro/2026-10-22-183000';
      const next = { ...cur };
      for (const f of a.files) next[f.path] = f.text;
      g.branches[target] = next;
      const base = inPlace ? a.base || g.branch : a.branch;
      return { committed: true, branch: target, base, commit: 'c2', hashes: Object.fromEntries(a.files.map((f) => [f.path, h(f.text)])), pr: `https://github.com/${a.repo}/compare/${base}...${target}?expand=1`, conflicts: [] };
    }
    throw new Error('fake gh ' + op);
  }
  window.addEventListener('message', (e) => {
    const d = e.data;
    if (e.source !== window || !d || d.source !== 'qa-pro' || !/^CTX_/.test(d.type || '') || window.__ctxOffline) return;
    setTimeout(() => {
      try {
        if (d.type === 'CTX_PING') return reply(d.id, 'CTX_RESULT', { data: { version: '1.8.0', bridge: true, gh: true } });
        const data = d.type === 'CTX_CALL' ? call(d.tool, d.args || {}) : ghCall(d.op, d.args || {});
        reply(d.id, 'CTX_RESULT', { data: JSON.parse(JSON.stringify(data)) });
      } catch (err) { reply(d.id, 'CTX_ERROR', { error: err.message, code: err.code || '' }); }
    }, 5);
  });
})();
