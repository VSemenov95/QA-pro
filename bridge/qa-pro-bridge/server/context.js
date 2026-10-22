// QA pro — источник контекста на компьютере: папка или git-репозиторий с правилами, шаблонами,
// памятью агента и базой знаний. Страница читает и пишет только текстовые файлы и только внутри
// разрешённых папок:
//   • папка из настроек моста в приложении Claude (QA_PRO_CONTEXT_DIR);
//   • папки, разрешённые в загрузчике Chrome или командой `node core.js --allow <папка>` (~/.qa-pro-bridge/context.json);
//   • клоны удалённых репозиториев, которые мост сделал сам (~/.qa-pro-bridge/repos).
// git запускается без оболочки, без запроса пароля в терминале, только с адресами https и ssh.
'use strict';
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const TEXT_RX = /\.(md|markdown|txt|json|ya?ml)$/i;
const SKIP_DIRS = new Set(['.git', 'node_modules', '.idea', '.vscode', 'target', 'build', 'out', 'dist', '.gradle']);
const MAX_FILE = 2 * 1024 * 1024;     // один файл — до 2 МБ
const MAX_READ = 3 * 1024 * 1024;     // за один вызов — до 3 МБ текста (лимит ответа приложения Claude)
const MAX_FILES = 3000;
const GIT_TIMEOUT = 25000;            // меньше лимита ответа приложения Claude

const sha = (s) => crypto.createHash('sha1').update(String(s), 'utf8').digest('hex');
const err = (message, code) => Object.assign(new Error(message), { code });
const real = (p) => { try { return fs.realpathSync(p); } catch { return null; } };
const isDir = (p) => { try { return fs.statSync(p).isDirectory(); } catch { return false; } };
const within = (root, p) => { const r = path.relative(root, p); return r === '' || (!!r && !r.startsWith('..') && !path.isAbsolute(r)); };

function create({ dir, log = () => {} }) {
  const cfgFile = path.join(dir, 'context.json');
  const reposDir = path.join(dir, 'repos');

  /* ---------- разрешённые папки ---------- */
  function readCfg() { try { const c = JSON.parse(fs.readFileSync(cfgFile, 'utf8')); return { roots: Array.isArray(c.roots) ? c.roots.filter((x) => typeof x === 'string') : [] }; } catch { return { roots: [] }; } }
  function writeCfg(c) { const tmp = cfgFile + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(c, null, 2), { mode: 0o600 }); fs.renameSync(tmp, cfgFile); }
  function envRoots() {
    const v = String(process.env.QA_PRO_CONTEXT_DIR || '');
    if (!v || v.includes('${')) return []; // приложение Claude не подставило значение — папка в настройках не задана
    return v.split(path.delimiter).map((x) => x.trim()).filter(Boolean);
  }
  function allowedRoots() {
    const out = [];
    for (const r of [...envRoots(), ...readCfg().roots]) { const p = real(r); if (p && isDir(p) && !out.includes(p)) out.push(p); }
    const repos = real(reposDir);
    if (repos && !out.includes(repos)) out.push(repos);
    return out;
  }
  function allow(root) {
    const p = String(root || '').trim();
    if (!p || !path.isAbsolute(p)) throw err('Нужен полный путь к папке, например C:\\work\\qa-context или /Users/me/qa-context.', 'bad_root');
    const r = real(p);
    if (!r || !isDir(r)) throw err('Папка не найдена: ' + p, 'no_root');
    const c = readCfg();
    if (!c.roots.map(real).includes(r)) { c.roots.push(r); writeCfg(c); log('разрешена папка контекста', r); }
    return { root: r, roots: allowedRoots() };
  }
  function forget(root) {
    const r = real(String(root || '')) || String(root || '');
    const c = readCfg();
    c.roots = c.roots.filter((x) => (real(x) || x) !== r);
    writeCfg(c);
    return { roots: allowedRoots() };
  }
  function rootOf(args) {
    const p = String(args?.root || '').trim();
    if (!p || !path.isAbsolute(p)) throw err('Укажите полный путь к папке контекста, например C:\\work\\qa-context или /Users/me/qa-context.', 'bad_root');
    const r = real(p);
    if (!r || !isDir(r)) throw err('Папка не найдена: ' + p, 'no_root');
    if (!allowedRoots().some((a) => within(a, r))) throw err('Папка не разрешена для QA pro: ' + r + '. Разрешите её в загрузчике Chrome, в настройках моста в приложении Claude или командой node core.js --allow "<папка>".', 'root_not_allowed');
    return r;
  }
  // путь файла внутри папки: без «..», абсолютных путей и ссылок наружу
  function inside(root, rel) {
    const s = String(rel || '').replace(/\\/g, '/');
    if (!s || s.startsWith('/') || /^[a-zA-Z]:/.test(s) || s.split('/').some((x) => x === '..' || x === '.git')) throw err('Путь вне папки контекста: ' + rel, 'bad_path');
    const p = path.resolve(root, s);
    if (!within(root, p) || p === root) throw err('Путь вне папки контекста: ' + rel, 'bad_path');
    let probe = p;
    while (!fs.existsSync(probe)) probe = path.dirname(probe);
    const rp = real(probe);
    if (!rp || !within(root, rp)) throw err('Путь ведёт за пределы папки контекста: ' + rel, 'bad_path');
    return p;
  }

  /* ---------- файлы ---------- */
  function list(root, sub) {
    const base = sub ? inside(root, sub) : root;
    const files = [];
    const walk = (d) => {
      let items = [];
      try { items = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
      for (const it of items) {
        if (files.length >= MAX_FILES) return;
        if (it.isSymbolicLink()) continue;
        const full = path.join(d, it.name);
        if (it.isDirectory()) { if (!SKIP_DIRS.has(it.name) && !it.name.startsWith('.')) walk(full); continue; }
        if (!TEXT_RX.test(it.name)) continue;
        let st; try { st = fs.statSync(full); } catch { continue; }
        files.push({ path: path.relative(root, full).split(path.sep).join('/'), size: st.size, mtime: Math.round(st.mtimeMs) });
      }
    };
    if (isDir(base)) walk(base);
    files.sort((a, b) => (a.path < b.path ? -1 : 1));
    return { root, name: path.basename(root), files, truncated: files.length >= MAX_FILES };
  }
  function read(root, paths) {
    let total = 0;
    const files = [];
    for (const rel of (Array.isArray(paths) ? paths : []).slice(0, 500)) {
      let p;
      try { p = inside(root, rel); } catch (e) { files.push({ path: String(rel), error: e.message }); continue; }
      if (!TEXT_RX.test(p)) { files.push({ path: rel, error: 'не текстовый файл' }); continue; }
      let st; try { st = fs.statSync(p); } catch { files.push({ path: rel, missing: true }); continue; }
      if (st.size > MAX_FILE) { files.push({ path: rel, error: 'файл больше 2 МБ' }); continue; }
      if (total + st.size > MAX_READ) { files.push({ path: rel, later: true }); continue; } // дочитать следующим вызовом
      const text = fs.readFileSync(p, 'utf8');
      total += st.size;
      files.push({ path: rel, text, hash: sha(text), mtime: Math.round(st.mtimeMs) });
    }
    return { files };
  }
  // запись: сначала проверка всех файлов (base — отпечаток версии, которую видела страница), потом запись
  function write(root, list0, { force = false } = {}) {
    const items = (Array.isArray(list0) ? list0 : []).slice(0, 300);
    if (!items.length) throw err('Нет файлов для записи.', 'empty');
    const plan = [], conflicts = [];
    for (const f of items) {
      const rel = String(f?.path || '');
      const p = inside(root, rel);
      if (!TEXT_RX.test(rel)) throw err('Записывать можно только .md, .txt, .json и .yaml: ' + rel, 'bad_ext');
      const text = f?.delete ? null : String(f?.text ?? '');
      if (text != null && Buffer.byteLength(text, 'utf8') > MAX_FILE) throw err('Файл больше 2 МБ: ' + rel, 'too_big');
      let cur = null;
      try { cur = fs.readFileSync(p, 'utf8'); } catch { /* нового файла ещё нет */ }
      const curHash = cur == null ? null : sha(cur);
      const base = f?.base === undefined ? undefined : f.base || null;
      if (!force && base !== undefined && base !== curHash && curHash !== (text == null ? null : sha(text))) conflicts.push({ path: rel, hash: curHash, text: cur });
      else plan.push({ rel, p, text, same: cur === text });
    }
    if (conflicts.length) return { written: [], conflicts };
    const written = [];
    for (const x of plan) {
      if (x.text == null) { try { fs.unlinkSync(x.p); written.push({ path: x.rel, deleted: true, hash: null }); } catch { /* уже нет */ } continue; }
      if (!x.same) {
        fs.mkdirSync(path.dirname(x.p), { recursive: true });
        const tmp = x.p + '.qa-pro-tmp';
        fs.writeFileSync(tmp, x.text, 'utf8'); fs.renameSync(tmp, x.p);
      }
      written.push({ path: x.rel, hash: sha(x.text) });
    }
    return { written, conflicts: [] };
  }

  /* ---------- git ---------- */
  const fileUrlsOk = () => process.env.QA_PRO_BRIDGE_ALLOW_FILE_URLS === '1'; // только для автотестов моста
  function git(cwd, args, { timeout = GIT_TIMEOUT } = {}) {
    return new Promise((resolve, reject) => {
      let out = '', errOut = '', done = false;
      let p;
      try {
        p = spawn('git', ['-c', 'core.quotepath=off', '-c', 'protocol.file.allow=' + (fileUrlsOk() ? 'always' : 'never'), ...args], {
          cwd, windowsHide: true,
          env: { ...process.env, GIT_TERMINAL_PROMPT: '0', GCM_INTERACTIVE: 'never', GIT_ASKPASS: process.env.GIT_ASKPASS || '', LC_ALL: 'C' },
        });
      } catch (e) { return reject(err('git не запустился: ' + e.message, 'no_git')); }
      const t = setTimeout(() => { if (!done) { done = true; try { p.kill(); } catch { /* уже завершён */ } reject(err('git не уложился в ' + Math.round(timeout / 1000) + ' с: ' + args[0], 'git_timeout')); } }, timeout);
      p.stdout.on('data', (d) => { out += d; if (out.length > 2e6) out = out.slice(-2e6); });
      p.stderr.on('data', (d) => { errOut += d; if (errOut.length > 2e5) errOut = errOut.slice(-2e5); });
      p.on('error', (e) => { if (done) return; done = true; clearTimeout(t); reject(err(e.code === 'ENOENT' ? 'git не установлен или не найден в PATH.' : 'git: ' + e.message, 'no_git')); });
      p.on('close', (code) => {
        if (done) return; done = true; clearTimeout(t);
        if (code === 0) resolve(out);
        else reject(err(('git ' + args[0] + ': ' + (errOut || out).trim().split('\n').slice(-4).join(' ')).slice(0, 600), 'git_failed'));
      });
    });
  }
  const cleanUrl = (u) => String(u || '').trim().replace(/\/\/[^/@\s]*@/, '//'); // без логина и токена в адресе
  function webUrl(remote) {
    const u = cleanUrl(remote).replace(/\.git$/, '');
    const m = u.match(/^git@([^:]+):(.+)$/) || u.match(/^ssh:\/\/(?:[^@/]+@)?([^/:]+)(?::\d+)?\/(.+)$/);
    if (m) return `https://${m[1]}/${m[2]}`;
    return /^https?:\/\//.test(u) ? u : '';
  }
  function prUrl(remote, branch) {
    const w = webUrl(remote);
    if (!w) return '';
    if (/github/i.test(w)) return `${w}/compare/${String(branch).split("/").map(encodeURIComponent).join("/")}?expand=1`;
    if (/gitlab/i.test(w)) return `${w}/-/merge_requests/new?merge_request%5Bsource_branch%5D=${encodeURIComponent(branch)}`;
    return w;
  }
  async function isRepo(root) { try { return (await git(root, ['rev-parse', '--is-inside-work-tree'], { timeout: 8000 })).trim() === 'true'; } catch { return false; } }
  async function status(root, { fetch = false } = {}) {
    if (!(await isRepo(root))) return { repo: false };
    let remote = '';
    try { remote = (await git(root, ['remote', 'get-url', 'origin'], { timeout: 8000 })).trim(); } catch { /* без удалённого */ }
    let fetchError = '';
    if (fetch && remote) { try { await git(root, ['fetch', '--quiet', 'origin']); } catch (e) { fetchError = e.message; } }
    const out = await git(root, ['status', '--porcelain=v1', '-b', '--untracked-files=all']);
    const lines = out.split('\n').filter(Boolean);
    const head = lines[0] || '';
    const m = head.match(/^## (?:No commits yet on )?([^\s.]+)(?:\.\.\.(\S+))?(?: \[(.*)\])?/) || [];
    const ab = m[3] || '';
    return {
      repo: true, branch: m[1] || '', upstream: m[2] || '', remote: cleanUrl(remote), web: webUrl(remote),
      ahead: Number((ab.match(/ahead (\d+)/) || [])[1] || 0), behind: Number((ab.match(/behind (\d+)/) || [])[1] || 0),
      changed: lines.slice(1).map((l) => ({ code: l.slice(0, 2).trim(), path: l.slice(3).replace(/^"|"$/g, '').split(' -> ').pop() })).slice(0, 500),
      fetchError,
    };
  }
  function checkUrl(url) {
    const u = String(url || '').trim();
    if (u.startsWith('-') || /\s/.test(u)) throw err('Некорректный адрес репозитория.', 'bad_url');
    if (/^https:\/\/[^\s]+$/i.test(u) || /^ssh:\/\/[^\s]+$/i.test(u) || /^[\w.-]+@[\w.-]+:[\w./~-]+$/.test(u)) return u;
    if (fileUrlsOk() && /^file:\/\//.test(u)) return u;
    throw err('Поддерживаются адреса https://… и ssh (git@host:группа/репозиторий.git).', 'bad_url');
  }
  const repoName = (url) => (cleanUrl(url).replace(/\.git$/, '').split(/[/:]/).filter(Boolean).slice(-2).join('-').replace(/[^\w.-]+/g, '-').replace(/^[.-]+/, '') || 'repo').slice(0, 80);
  async function clone(url0, { branch } = {}) {
    const url = checkUrl(url0);
    fs.mkdirSync(reposDir, { recursive: true, mode: 0o700 });
    const dirName = repoName(url);
    const target = path.join(reposDir, dirName);
    if (isDir(path.join(target, '.git'))) {
      let cur = '';
      try { cur = (await git(target, ['remote', 'get-url', 'origin'], { timeout: 8000 })).trim(); } catch { /* без удалённого */ }
      if (cleanUrl(cur) !== cleanUrl(url)) throw err(`Папка ${target} уже занята клоном другого репозитория (${cleanUrl(cur)}). Удалите её или подключите тот репозиторий.`, 'clone_busy');
      return { root: real(target), cloned: false };
    }
    if (fs.existsSync(target)) throw err('Папка уже существует и это не git-репозиторий: ' + target, 'clone_busy');
    const args = ['clone', '--depth', '50', '--no-tags'];
    if (branch) { if (!/^[\w./-]{1,100}$/.test(branch) || branch.startsWith('-')) throw err('Некорректное имя ветки.', 'bad_branch'); args.push('--branch', branch); }
    try { await git(reposDir, [...args, '--', url, dirName], { timeout: GIT_TIMEOUT }); }
    catch (e) { try { fs.rmSync(target, { recursive: true, force: true }); } catch { /* нечего удалять */ } throw e; }
    log('склонирован репозиторий контекста', cleanUrl(url));
    return { root: real(target), cloned: true };
  }
  async function pull(root) {
    if (!(await isRepo(root))) throw err('Папка не является git-репозиторием — обновлять нечего.', 'not_repo');
    const before = (await git(root, ['rev-parse', 'HEAD'], { timeout: 8000 }).catch(() => '')).trim();
    await git(root, ['pull', '--ff-only', '--quiet']);
    const after = (await git(root, ['rev-parse', 'HEAD'], { timeout: 8000 }).catch(() => '')).trim();
    return { updated: before !== after, head: after.slice(0, 12), status: await status(root) };
  }
  const stamp = () => { const d = new Date(), z = (n) => String(n).padStart(2, '0'); return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}-${z(d.getHours())}${z(d.getMinutes())}`; };
  async function commit(root, { message, paths, branch } = {}) {
    if (!(await isRepo(root))) throw err('Папка не является git-репозиторием: изменения уже сохранены в файлах, фиксировать нечего.', 'not_repo');
    const st = await status(root);
    let def = '';
    try { def = (await git(root, ['symbolic-ref', '--short', 'refs/remotes/origin/HEAD'], { timeout: 8000 })).trim().replace(/^origin\//, ''); } catch { /* без удалённого */ }
    let target = st.branch;
    if (branch) {
      if (!/^[\w./-]{1,100}$/.test(branch) || branch.startsWith('-')) throw err('Некорректное имя ветки.', 'bad_branch');
      target = branch;
    } else if (!st.branch || ['main', 'master', 'develop', 'HEAD', def].includes(st.branch)) target = 'qa-pro/' + stamp();
    if (target !== st.branch) await git(root, ['switch', '-c', target]);
    const scope = (Array.isArray(paths) && paths.length ? paths : ['.']).slice(0, 300).map((x) => { if (x !== '.') inside(root, x); return x; });
    await git(root, ['add', '-A', '--', ...scope]);
    const staged = (await git(root, ['diff', '--cached', '--name-only'])).split('\n').filter(Boolean);
    if (!staged.length) return { committed: false, branch: target, files: [] };
    let who = [];
    try { await git(root, ['config', 'user.email'], { timeout: 5000 }); } catch { who = ['-c', 'user.name=QA pro', '-c', 'user.email=qa-pro@localhost']; }
    await git(root, [...who, 'commit', '--quiet', '-m', String(message || 'QA pro: контекст').slice(0, 300)]);
    const head = (await git(root, ['rev-parse', '--short', 'HEAD'], { timeout: 8000 })).trim();
    return { committed: true, branch: target, head, files: staged };
  }
  async function push(root) {
    const st = await status(root);
    if (!st.repo) throw err('Папка не является git-репозиторием.', 'not_repo');
    if (!st.remote) throw err('У репозитория нет удалённого origin — отправлять некуда.', 'no_remote');
    if (['main', 'master'].includes(st.branch)) throw err('QA pro не отправляет изменения прямо в ' + st.branch + ': сначала зафиксируйте их — появится ветка qa-pro/<дата>.', 'protected_branch');
    await git(root, ['push', '--quiet', '-u', 'origin', 'HEAD']);
    return { branch: st.branch, remote: st.remote, pr: prUrl(st.remote, st.branch), status: await status(root) };
  }

  /* ---------- инструменты ---------- */
  async function tool(name, args = {}) {
    if (name === 'context_read') {
      const op = String(args.op || 'list');
      if (op === 'roots') return { roots: allowedRoots(), repos: real(reposDir) || reposDir };
      const root = rootOf(args);
      if (op === 'list') return { ...list(root, args.sub ? String(args.sub) : ''), git: await status(root).catch(() => ({ repo: false })) };
      if (op === 'read') return read(root, args.paths);
      if (op === 'status') return status(root, { fetch: !!args.fetch });
      throw err('Неизвестная операция чтения: ' + op, 'bad_op');
    }
    if (name === 'context_write') return write(rootOf(args), args.files, { force: !!args.force });
    if (name === 'context_git') {
      const op = String(args.op || '');
      if (op === 'clone') return clone(args.url, { branch: args.branch ? String(args.branch) : '' });
      const root = rootOf(args);
      if (op === 'pull') return pull(root);
      if (op === 'commit') return commit(root, { message: args.message, paths: args.paths, branch: args.branch ? String(args.branch) : '' });
      if (op === 'push') return push(root);
      if (op === 'status') return status(root, { fetch: !!args.fetch });
      throw err('Неизвестная операция git: ' + op, 'bad_op');
    }
    throw err('Неизвестный инструмент: ' + name, 'bad_tool');
  }
  return { tool, allow, forget, allowedRoots, rootOf, inside, list, read, write, status, clone, pull, commit, push, webUrl, prUrl, sha };
}

module.exports = { create, TEXT_RX, sha };
