// QA pro — загрузчик. Источник контекста для QA pro в браузере (подключается в background.js через importScripts).
//  • Папка или git-клон на компьютере: страница → загрузчик → ядро моста qa-pro-bridge (ws://127.0.0.1:<порт>/ext).
//  • GitHub без моста: загрузчик сам ходит в API GitHub с токеном из настроек; страница токена не видит.
// Каждая страница (адрес фрейма QA pro) получает доступ к папке или репозиторию только после «Разрешить»
// в окне загрузчика. Разрешения видны и отзываются в настройках загрузчика.
/* global getSettings, saveSettings, bridgeConnect, bridgeSocket */
'use strict';

const CTX_TEXT_RX = /\.(md|markdown|txt|json|ya?ml)$/i;
const ctxOriginOf = (sender) => { try { return sender.origin && sender.origin !== 'null' ? sender.origin : new URL(sender.url).origin; } catch { return ''; } };
const ctxErr = (message, code) => Object.assign(new Error(message), { code });

/* ---------- разрешения: { [адрес страницы]: { roots: [папки], repos: [адреса git], gh: [owner/repo] } } ---------- */
async function ctxGrants() { return (await getSettings()).ctxGrants || {}; }
async function ctxGranted(origin, kind, target) { const g = (await ctxGrants())[origin]; return !!g && (g[kind] || []).includes(target); }
async function ctxGrant(origin, kind, target) {
  const all = await ctxGrants();
  const g = { roots: [], repos: [], gh: [], ...(all[origin] || {}) };
  if (!g[kind].includes(target)) g[kind] = [...g[kind], target];
  g.at = Date.now();
  await saveSettings({ ctxGrants: { ...all, [origin]: g } });
}
async function ctxRevoke(origin, kind, target) {
  const all = await ctxGrants();
  const g = all[origin];
  if (!g) return;
  const next = { ...g, [kind]: (g[kind] || []).filter((x) => x !== target) };
  const left = ['roots', 'repos', 'gh'].some((k) => (next[k] || []).length);
  const copy = { ...all };
  if (left) copy[origin] = next; else delete copy[origin];
  await saveSettings({ ctxGrants: copy });
  if (kind === 'roots' && !Object.values(copy).some((x) => (x.roots || []).includes(target))) ctxCore('ctx_forget', { root: target }).catch(() => {});
}

// окно «Разрешить доступ»: ответ приходит сообщением CTX_DECIDE
const ctxAsks = new Map();
async function ctxAsk(origin, kind, target) {
  const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  await chrome.storage.session.set({ ['ctxask:' + id]: { origin, kind, target } });
  const decision = new Promise((resolve) => {
    const t = setTimeout(() => { ctxAsks.delete(id); resolve(false); }, 170000);
    ctxAsks.set(id, { resolve: (v) => { clearTimeout(t); resolve(v); } });
  });
  let windowId = null;
  try { windowId = (await chrome.windows.create({ url: chrome.runtime.getURL('ctx-allow.html?id=' + id), type: 'popup', width: 560, height: 520 }))?.id; } catch { /* без окна */ }
  if (!windowId) ctxDecide(id, false);
  else if (ctxAsks.has(id)) ctxAsks.get(id).windowId = windowId;
  const ok = await decision;
  await chrome.storage.session.remove('ctxask:' + id);
  if (windowId) chrome.windows.remove(windowId).catch(() => {});
  return ok;
}
function ctxDecide(id, allow) { const a = ctxAsks.get(id); if (!a) return false; ctxAsks.delete(id); a.resolve(!!allow); return true; }
// окно закрыли крестиком — это «Отклонить»
chrome.windows.onRemoved.addListener((windowId) => { for (const [id, a] of [...ctxAsks]) if (a.windowId === windowId) ctxDecide(id, false); });

/* ---------- ядро моста: запрос и ответ по WebSocket ---------- */
const ctxPending = new Map();
function ctxOnCoreMessage(m) {
  if (m?.t !== 'ctx_result' || !m.id) return false;
  const p = ctxPending.get(m.id);
  if (!p) return true;
  ctxPending.delete(m.id); clearTimeout(p.t);
  if (m.ok) p.resolve(m.data); else p.reject(ctxErr(String(m.error || 'Мост вернул ошибку.'), m.code || ''));
  return true;
}
async function ctxSocket() {
  let w = bridgeSocket();
  if (w && w.readyState === WebSocket.OPEN) return w;
  await bridgeConnect();
  for (let i = 0; i < 30; i++) { w = bridgeSocket(); if (w && w.readyState === WebSocket.OPEN) return w; await new Promise((r) => setTimeout(r, 100)); }
  const s = await getSettings();
  throw ctxErr(s.desktopBridge === false
    ? 'В настройках загрузчика выключена связь с мостом — включите «Связь с приложением Claude через мост».'
    : `Мост qa-pro-bridge не запущен на этом компьютере (порт ${Number(s.bridgePort) || 47321}). Запустите его: node core.js --keep — или откройте приложение Claude с установленным мостом.`, 'no_bridge');
}
async function ctxCore(t, payload, timeout = 30000) {
  const w = await ctxSocket();
  const id = 'cx-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  return new Promise((resolve, reject) => {
    const tm = setTimeout(() => { ctxPending.delete(id); reject(ctxErr('Мост не ответил за ' + Math.round(timeout / 1000) + ' с.', 'timeout')); }, timeout);
    ctxPending.set(id, { resolve, reject, t: tm });
    try { w.send(JSON.stringify({ t, id, ...payload })); } catch (e) { clearTimeout(tm); ctxPending.delete(id); reject(ctxErr('Не удалось передать запрос мосту: ' + (e?.message || e), 'no_bridge')); }
  });
}

/* ---------- вызов от страницы: папка или git-клон через мост ---------- */
async function ctxCall(sender, tool, args0) {
  const origin = ctxOriginOf(sender);
  if (!origin) throw ctxErr('Не удалось определить адрес страницы QA pro.', 'no_origin');
  if (!/^context_(read|write|git)$/.test(String(tool))) throw ctxErr('Неизвестный инструмент: ' + tool, 'bad_tool');
  const args = args0 && typeof args0 === 'object' ? { ...args0 } : {};
  if (tool === 'context_read' && args.op === 'roots') return { roots: ((await ctxGrants())[origin]?.roots) || [] };
  if (tool === 'context_git' && args.op === 'clone') {
    const url = String(args.url || '').trim();
    if (!(await ctxGranted(origin, 'repos', url))) {
      if (!(await ctxAsk(origin, 'repos', url))) throw ctxErr('Доступ к репозиторию не разрешён в окне загрузчика.', 'denied');
      await ctxGrant(origin, 'repos', url);
    }
    const r = await ctxCore('ctx', { tool, args }, 30000);
    if (r?.root) await ctxGrant(origin, 'roots', r.root);
    return r;
  }
  const root = String(args.root || '').trim();
  if (!root) throw ctxErr('Не указана папка контекста.', 'bad_root');
  if (!(await ctxGranted(origin, 'roots', root))) {
    if (!(await ctxAsk(origin, 'roots', root))) throw ctxErr('Доступ к папке не разрешён в окне загрузчика.', 'denied');
    await ctxCore('ctx_allow', { root }, 10000); // ядро проверит, что папка есть, и добавит её в свой список
    await ctxGrant(origin, 'roots', root);
  }
  const call = () => ctxCore('ctx', { tool, args }, tool === 'context_git' ? 30000 : 25000);
  try { return await call(); }
  catch (e) {
    if (e.code !== 'root_not_allowed') throw e;
    // разрешение есть в загрузчике, но ядро его не знает (новый компьютерный профиль, ядро переустановлено) — напоминаем и повторяем
    await ctxCore('ctx_allow', { root }, 10000);
    return call();
  }
}

/* ---------- GitHub без моста ---------- */
const ghApiBase = (s) => String(s.ghApi || 'https://api.github.com').trim().replace(/\/+$/, '');
const ghWeb = (api) => (/^https:\/\/api\.github\.com$/i.test(api) ? 'https://github.com' : api.replace(/\/api\/v3$/i, ''));
const ghRepoOk = (r) => /^[\w.-]+\/[\w.-]+$/.test(r);
const encBranch = (b) => String(b).split('/').map(encodeURIComponent).join('/');
async function gh(path, { method = 'GET', body } = {}) {
  const s = await getSettings();
  const token = String(s.ghToken || '').trim();
  if (!token) throw ctxErr('Укажите токен GitHub в настройках загрузчика (раздел «Контекст QA pro»).', 'gh_no_token');
  const api = ghApiBase(s);
  let res;
  try {
    res = await fetch(api + path, { method, headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', ...(body ? { 'Content-Type': 'application/json' } : {}) }, body: body ? JSON.stringify(body) : undefined, cache: 'no-store' });
  } catch (e) { throw ctxErr('GitHub недоступен: ' + (e?.message || e), 'gh_network'); }
  const text = await res.text();
  let data; try { data = text ? JSON.parse(text) : null; } catch { data = text; }
  if (!res.ok) {
    const msg = (data && data.message) || String(text).slice(0, 200);
    throw ctxErr(res.status === 401 ? 'GitHub не принял токен — проверьте его в настройках загрузчика.' : res.status === 404 ? 'Репозиторий или ветка не найдены (или у токена нет к ним доступа).' : `GitHub ответил ${res.status}: ${msg}`, 'gh_' + res.status);
  }
  return data;
}
const b64utf8 = (b64) => new TextDecoder().decode(Uint8Array.from(atob(String(b64 || '').replace(/\s+/g, '')), (c) => c.charCodeAt(0)));
async function ghTree(repo, ref) {
  const head = await gh(`/repos/${repo}/commits/${String(ref).split('/').map(encodeURIComponent).join('/')}`);
  const tree = await gh(`/repos/${repo}/git/trees/${head.commit.tree.sha}?recursive=1`);
  return { commit: head.sha, tree: head.commit.tree.sha, items: (tree.tree || []).filter((x) => x.type === 'blob'), truncated: !!tree.truncated };
}
async function ghCall(sender, op, args0) {
  const origin = ctxOriginOf(sender);
  if (!origin) throw ctxErr('Не удалось определить адрес страницы QA pro.', 'no_origin');
  const args = args0 && typeof args0 === 'object' ? args0 : {};
  const repo = String(args.repo || '').trim();
  if (!ghRepoOk(repo)) throw ctxErr('Укажите репозиторий в виде владелец/название, например team/qa-context.', 'bad_repo');
  if (!(await ctxGranted(origin, 'gh', repo))) {
    if (!(await ctxAsk(origin, 'gh', repo))) throw ctxErr('Доступ к репозиторию не разрешён в окне загрузчика.', 'denied');
    await ctxGrant(origin, 'gh', repo);
  }
  const info = await gh(`/repos/${repo}`);
  const branch = String(args.branch || '').trim() || info.default_branch;
  const sub = String(args.sub || '').replace(/^\/+|\/+$/g, '');
  const api = ghApiBase(await getSettings());
  if (op === 'status') return { repo, branch, defaultBranch: info.default_branch, canPush: !!info.permissions?.push, web: `${ghWeb(api)}/${repo}` };
  if (op === 'list') {
    const t = await ghTree(repo, branch);
    const files = t.items.filter((x) => CTX_TEXT_RX.test(x.path) && (!sub || x.path.startsWith(sub + '/')) && !x.path.split('/').some((p) => p.startsWith('.')))
      .slice(0, 3000).map((x) => ({ path: x.path, size: x.size || 0, hash: x.sha }));
    return { repo, branch, commit: t.commit, files, truncated: t.truncated, web: `${ghWeb(api)}/${repo}` };
  }
  if (op === 'read') {
    const t = await ghTree(repo, branch);
    const byPath = new Map(t.items.map((x) => [x.path, x]));
    const paths = (Array.isArray(args.paths) ? args.paths : []).slice(0, 300).map(String);
    const out = [];
    let i = 0;
    await Promise.all(Array.from({ length: 6 }, async () => {
      while (i < paths.length) {
        const p = paths[i++];
        const x = byPath.get(p);
        if (!x) { out.push({ path: p, missing: true }); continue; }
        if ((x.size || 0) > 2 * 1024 * 1024) { out.push({ path: p, error: 'файл больше 2 МБ' }); continue; }
        try { const b = await gh(`/repos/${repo}/git/blobs/${x.sha}`); out.push({ path: p, text: b64utf8(b.content), hash: x.sha }); }
        catch (e) { out.push({ path: p, error: e.message }); }
      }
    }));
    return { files: out };
  }
  if (op === 'commit') {
    const files = (Array.isArray(args.files) ? args.files : []).slice(0, 300);
    if (!files.length) throw ctxErr('Нет файлов для отправки.', 'empty');
    for (const f of files) if (!CTX_TEXT_RX.test(String(f?.path || '')) || String(f.path).split('/').some((p) => p === '..' || p.startsWith('.') || !p)) throw ctxErr('Нельзя записать файл: ' + f?.path, 'bad_path');
    const t = await ghTree(repo, branch);
    const cur = new Map(t.items.map((x) => [x.path, x.sha]));
    const conflicts = args.force ? [] : files.filter((f) => f.base !== undefined && (f.base || null) !== (cur.get(f.path) || null)).map((f) => ({ path: f.path, hash: cur.get(f.path) || null }));
    if (conflicts.length) return { committed: false, conflicts };
    const tree = await gh(`/repos/${repo}/git/trees`, { method: 'POST', body: { base_tree: t.tree, tree: files.map((f) => (f.delete ? { path: f.path, mode: '100644', type: 'blob', sha: null } : { path: f.path, mode: '100644', type: 'blob', content: String(f.text ?? '') })) } });
    const commit = await gh(`/repos/${repo}/git/commits`, { method: 'POST', body: { message: String(args.message || 'QA pro: контекст').slice(0, 300), tree: tree.sha, parents: [t.commit] } });
    // своя ветка qa-pro/… дополняется; с основной ветки — новая ветка qa-pro/<дата>
    const inPlace = branch.startsWith('qa-pro/');
    const d = new Date(), z = (n) => String(n).padStart(2, '0');
    const target = inPlace ? branch : `qa-pro/${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}-${z(d.getHours())}${z(d.getMinutes())}${z(d.getSeconds())}`;
    if (inPlace) await gh(`/repos/${repo}/git/refs/heads/${target.split('/').map(encodeURIComponent).join('/')}`, { method: 'PATCH', body: { sha: commit.sha, force: false } });
    else await gh(`/repos/${repo}/git/refs`, { method: 'POST', body: { ref: 'refs/heads/' + target, sha: commit.sha } });
    const base = inPlace ? String(args.base || info.default_branch) : branch;
    const after = await gh(`/repos/${repo}/git/trees/${tree.sha}?recursive=1`).catch(() => null);
    const hashes = Object.fromEntries(files.map((f) => [f.path, (after?.tree || []).find((x) => x.path === f.path)?.sha || null]));
    return { committed: true, branch: target, base, commit: commit.sha, hashes, pr: `${ghWeb(api)}/${repo}/compare/${encBranch(base)}...${encBranch(target)}?expand=1`, conflicts: [] };
  }
  throw ctxErr('Неизвестная операция GitHub: ' + op, 'bad_op');
}

/* ---------- сообщения: от страниц (через bridge.js), от окна разрешения и настроек ---------- */
async function ctxMessage(msg, sender) {
  switch (msg?.type) {
    case 'CTX_CALL': return { ok: true, data: await ctxCall(sender, msg.tool, msg.args) };
    case 'CTX_GH': return { ok: true, data: await ghCall(sender, msg.op, msg.args) };
    case 'CTX_PING': {
      const s = await getSettings();
      const w = bridgeSocket();
      return { ok: true, version: chrome.runtime.getManifest().version, bridge: !!(w && w.readyState === WebSocket.OPEN), gh: !!String(s.ghToken || '').trim() };
    }
    case 'CTX_ASK_INFO': { const k = 'ctxask:' + msg.id; return { ok: true, ask: (await chrome.storage.session.get(k))[k] || null }; }
    case 'CTX_DECIDE': return { ok: ctxDecide(msg.id, msg.allow) };
    case 'CTX_GRANTS': return { ok: true, grants: await ctxGrants() };
    case 'CTX_REVOKE': await ctxRevoke(msg.origin, msg.kind, msg.target); return { ok: true, grants: await ctxGrants() };
    default: return null;
  }
}
