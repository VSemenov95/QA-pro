/* ================= источник контекста: база QA pro, папка, git-репозиторий, GitHub ================= */
/* У продукта один активный источник контекста — личная настройка каждого пользователя (локальная папка у всех своя).
   Пока источник — репозиторий, правила для агента, правила ревью, шаблоны, формат экспорта, память агента, паспорт
   продукта и доп. контекст берутся из его файлов, а разделы базы знаний из репозитория добавляются к базе знаний
   продукта (при совпадении названия — версия из репозитория). Изменения в QA pro записываются обратно в файлы.

   Раскладка файлов (относительно подпапки контекста):
     CLAUDE.md                                — порядок работы (для Claude Code и людей)
     rules/generation.md, rules/review.md     — правила для агента и правила ревью
     templates/api.md, ui.md, e2e.md           — шаблоны: idPrefix, «## Правила», «## Образец» с JSON
     templates/export.md                       — формат экспорта
     knowledge/**.md                           — общая база знаний для всех продуктов
     products/<папка продукта>/passport.md     — знания о продукте (паспорт)
     products/<папка продукта>/context.md      — доп. контекст QA: «## Для всех», «## API», «## UI», «## E2E»
     products/<папка продукта>/lessons.md      — память агента: «- [генерация|ревью|оба] правило»
     products/<папка продукта>/kb/**.md        — разделы базы знаний продукта

   Каналы: папка и git — мост qa-pro-bridge (в приложении Claude — инструменты context_*, в браузере — через загрузчик),
   GitHub — загрузчик с токеном (без моста), «папка только для чтения» — выбор папки на странице. */
const CTX_KINDS = {
  qa: { title: 'База QA pro', desc: 'Как сейчас: правила, шаблоны, память и база знаний хранятся в приложении.' },
  local: { title: 'Папка на компьютере', desc: 'Папка или git-клон. Чтение и запись через мост qa-pro-bridge.' },
  git: { title: 'Git-репозиторий', desc: 'Адрес https или ssh. Мост клонирует его, обновляет и отправляет изменения в ветку.' },
  github: { title: 'GitHub без моста', desc: 'Через загрузчик в браузере по токену GitHub. Изменения — в ветку qa-pro/<дата>.' },
  folder: { title: 'Папка только для чтения', desc: 'Выбрать папку на этом компьютере. Без моста и расширений; изменения не записываются.' },
};
const CTX_BRIDGE = new Set(['local', 'git']);
const CTX_TEXT_RX = /\.(md|markdown|txt|json|ya?ml)$/i;
const CTX_TOOLS = ['context_read', 'context_write', 'context_git'];
const CTX_KB_SPLIT = 8000;      // файл базы знаний длиннее — делится на разделы по заголовкам «##»
const CTX_CACHE_PART = 150000;  // копия файлов в хранилище — частями до 150 тыс. знаков
const ctxBlank = () => ({ kind: 'qa', root: '', url: '', cloned: '', repo: '', branch: '', baseBranch: '', sub: '', slug: '' });
S.ctx = { pid: null, src: ctxBlank(), draft: null, on: false, busy: '', error: '', files: new Map(), git: null, channel: '', loadedAt: 0, fromCache: false, conflicts: [], pending: new Set(), backup: null, kb: [], kbAt: 0, note: '', confirm: null, lastPush: null, warn: [] };

/* ---------- пути ---------- */
const ctxSlug = (C = S.ctx) => C.src.slug || slugName(productById(C.pid)?.name || 'product');
const CP = {
  rules: 'rules/generation.md', review: 'rules/review.md', export: 'templates/export.md', claude: 'CLAUDE.md',
  tpl: (t) => `templates/${t}.md`,
  passport: (C) => `products/${ctxSlug(C)}/passport.md`,
  context: (C) => `products/${ctxSlug(C)}/context.md`,
  lessons: (C) => `products/${ctxSlug(C)}/lessons.md`,
  kbDir: (C) => `products/${ctxSlug(C)}/kb/`,
};
const ctxCfgPath = (k) => (k === 'rules' ? CP.rules : k === 'review' ? CP.review : k === 'export' ? CP.export : CP.tpl(k));
const ctxSub = (C = S.ctx) => String(C.src.sub || '').replace(/\\/g, '/').replace(/^\/+|\/+$/g, '');
const ctxFull = (p, C = S.ctx) => (ctxSub(C) ? ctxSub(C) + '/' + p : p);
const ctxRel = (full, C = S.ctx) => { const s = ctxSub(C); return !s ? full : full.startsWith(s + '/') ? full.slice(s.length + 1) : null; };
const ctxText = (p) => { const f = S.ctx.files.get(p); return f && f.text != null ? f.text : null; };
const ctxWanted = (rel, C = S.ctx) => [CP.rules, CP.review, CP.export, CP.claude, ...TYPES.map(CP.tpl), CP.passport(C), CP.context(C), CP.lessons(C)].includes(rel) || rel.startsWith(CP.kbDir(C)) || rel.startsWith('knowledge/');

/* ---------- состояние ---------- */
const ctxActive = (pid = S.productId) => S.ctx.on && S.ctx.pid === pid && S.ctx.src.kind !== 'qa';
const ctxOwnsCfg = () => S.ctx.on && !!S.ctx.backup;
const ctxWritable = () => CTX_BRIDGE.has(S.ctx.src.kind) || S.ctx.src.kind === 'github';
const ctxWhere = (src = S.ctx.src) => (src.kind === 'local' ? src.root : src.kind === 'git' ? src.url : src.kind === 'github' ? `${src.repo}${src.branch ? ' · ' + src.branch : ''}` : src.kind === 'folder' ? src.root || 'выбранная папка' : 'база QA pro') + (ctxSub({ src }) ? ` · ${ctxSub({ src })}` : '');
const ctxRootOf = (src = S.ctx.src) => (src.kind === 'git' ? src.cloned : src.root);

/* ---------- разбор и сборка файлов ---------- */
const CTX_HEADS = { rules: 'Правила для агента', review: 'Правила ревью', export: 'Формат экспорта' };
function ctxParsePlain(text) { return String(text).replace(/^\uFEFF/, '').replace(/^#\s+(Правила для агента|Правила генерации|Правила ревью|Формат экспорта)\s*\n+/i, '').trim(); }
const ctxMakePlain = (k, v) => `# ${CTX_HEADS[k]}\n\n${String(v || '').trim()}\n`;
function ctxParseTpl(text, t) {
  const s = String(text).replace(/\r\n/g, '\n');
  const idp = (s.match(/^idPrefix:\s*(.*)$/m) || [])[1];
  const rules = s.includes('## Правила') ? s.split(/^## Правила\s*$/m)[1].split(/^## /m)[0].trim() : '';
  const ex = (s.match(/```json\s*\n([\s\S]*?)\n```/) || [])[1];
  if (ex == null) return null;
  return { idPrefix: idp != null ? idp.trim() : DEFAULT_TPL[t].idPrefix, rules, example: ex };
}
const ctxMakeTpl = (t, tp) => `# Шаблон ${TL[t]}\n\nidPrefix: ${tp.idPrefix || ''}\n\n## Правила\n\n${String(tp.rules || '').trim()}\n\n## Образец\n\n${'```'}json\n${String(tp.example || '').trim()}\n${'```'}\n`;
const LESSON_TAG = { generation: 'генерация', review: 'ревью', both: 'оба' };
function ctxParseLessons(text) {
  const out = [];
  for (const line of String(text).split('\n')) {
    const m = line.match(/^\s*[-*]\s+(?:\[(генерация|ревью|оба|generation|review|both)\]\s*)?(.+)$/i);
    if (!m || !m[2].trim()) continue;
    const tag = String(m[1] || '').toLowerCase();
    const scope = /ревью|review/.test(tag) ? 'review' : /оба|both/.test(tag) ? 'both' : 'generation';
    out.push({ id: 'ctxl-' + hash(m[2].trim()), text: m[2].trim().slice(0, 400), scope, source: 'repo', createdAt: out.length, ctx: true });
  }
  return out;
}
const ctxMakeLessons = (ls) => `# Память агента\n\nПравила из замечаний команды. Агент соблюдает их при генерации и ревью. Строка: «- [генерация|ревью|оба] правило».\n\n${ls.map((l) => `- [${LESSON_TAG[l.scope] || 'генерация'}] ${String(l.text).replace(/\s+/g, ' ').trim()}`).join('\n')}\n`;
const CTX_QA_HEAD = { all: 'Для всех', api: 'API', ui: 'UI', e2e: 'E2E' };
function ctxParseQaCtx(text) {
  const c = { all: '', api: '', ui: '', e2e: '' };
  let k = 'all';
  const buf = { all: [], api: [], ui: [], e2e: [] };
  for (const line of String(text).replace(/\r\n/g, '\n').split('\n')) {
    const h = line.match(/^##\s+(.+?)\s*$/);
    if (h) { const key = Object.keys(CTX_QA_HEAD).find((x) => normKey(CTX_QA_HEAD[x]) === normKey(h[1])); if (key) { k = key; continue; } }
    if (/^#\s/.test(line) && !buf[k].length && k === 'all') continue; // заголовок файла
    buf[k].push(line);
  }
  for (const x of Object.keys(c)) c[x] = buf[x].join('\n').trim();
  return c;
}
const ctxMakeQaCtx = (c) => `# Доп. контекст QA\n\n${Object.keys(CTX_QA_HEAD).filter((k) => String(c?.[k] || '').trim()).map((k) => `## ${CTX_QA_HEAD[k]}\n\n${String(c[k]).trim()}\n`).join('\n')}`;
function ctxClaudeMd(slug) {
  return `# Контекст QA pro

Этот репозиторий — источник контекста для QA pro и для Claude: правила, шаблоны, память агента и база знаний.
QA pro читает его через мост qa-pro-bridge, загрузчик в браузере или API GitHub и записывает изменения обратно.

## Порядок работы
1. Перед составлением тест-кейсов прочитай \`rules/generation.md\`, шаблон нужного вида из \`templates/\` и память агента \`products/<продукт>/lessons.md\`.
2. Термины, роли, экраны и связи бери из \`products/<продукт>/passport.md\` и разделов \`products/<продукт>/kb/\` и \`knowledge/\`.
3. Кейсы оформляй строго по образцу JSON из шаблона, без полей, которых в нём нет.
4. Перед выдачей проверь кейсы по \`rules/review.md\`.

## Файлы
- \`rules/generation.md\`, \`rules/review.md\` — правила для агента и правила ревью.
- \`templates/api.md\`, \`templates/ui.md\`, \`templates/e2e.md\` — шаблоны: префикс ID, правила оформления, образец JSON.
- \`templates/export.md\` — формат экспорта.
- \`knowledge/\` — общая база знаний.
- \`products/${slug}/\` — продукт: \`passport.md\`, \`context.md\`, \`lessons.md\`, \`kb/\`.

Изменения правил и шаблонов — через ветку и запрос на слияние: QA pro отправляет их в ветку \`qa-pro/<дата>\`.
`;
}
// база знаний: файл — раздел; длинный файл — разделы по заголовкам «##»
function ctxKbSections(files) {
  const out = [];
  for (const [rel, f] of files) {
    const text = String(f.text || '').replace(/\r\n/g, '\n').trim();
    if (!text) continue;
    const name = rel.split('/').pop().replace(/\.[^.]+$/, '').replace(/[-_]+/g, ' ');
    const h1 = (text.match(/^#\s+(.+)$/m) || [])[1];
    const title = (h1 || name).trim().slice(0, 140);
    const shared = rel.startsWith('knowledge/');
    const add = (t, body, i) => {
      const d = { synth: body, summary: '', parts: [], conflicts: [], links: [], ctx: true, path: rel };
      out.push({ b: { id: 'ctx:' + rel + (i ? '#' + i : ''), title: t, summary: shared ? 'общая база знаний' : '', ctx: true, path: rel }, d });
    };
    if (text.length <= CTX_KB_SPLIT || !/^##\s/m.test(text)) { add(title, text, 0); continue; }
    const parts = text.split(/^(?=##\s)/m);
    const lead = parts[0].replace(/^#\s+.+\n?/, '').trim();
    let i = 0;
    for (const p of parts.slice(1)) {
      const h = (p.match(/^##\s+(.+)$/m) || [])[1] || 'раздел';
      add(`${title} › ${h.trim()}`.slice(0, 160), (i === 0 && lead ? lead + '\n\n' : '') + p.trim(), ++i);
    }
    if (!parts.slice(1).length) add(title, text, 0);
  }
  return out;
}

/* ---------- канал: мост (приложение Claude или загрузчик) и загрузчик (GitHub) ---------- */
const ctxErr = (message, code) => Object.assign(new Error(message), { code });
let ctxExt = null; // { ok, version, bridge, gh, at }
async function ctxPingExt(force = false) {
  if (!force && ctxExt && Date.now() - ctxExt.at < 20000) return ctxExt;
  const r = await bridgeCall({ type: 'CTX_PING' }, { timeout: 4000, until: ['CTX_RESULT', 'CTX_ERROR'] });
  ctxExt = r?.type === 'CTX_RESULT' ? { ok: true, ...(r.data || {}), at: Date.now() } : { ok: false, at: Date.now(), error: r?.error || '' };
  return ctxExt;
}
const ctxNoExt = () => (inDesktopApp
  ? 'В приложении Claude нет расширений браузера, а мост qa-pro-bridge не отвечает. Установите мост версии 1.5 (шестерёнка → ТМС → «Скачать мост») и укажите в его настройках папку контекста.'
  : 'Загрузчик QA pro версии 1.8 не видит эту страницу. Установите или обновите загрузчик (шестерёнка → ТМС → «Скачать загрузчик»), обновите страницу (Ctrl+F5) и повторите.');
async function ctxViaHost(tool, args) {
  try { return { ok: true, data: await hostCall(tool, args) }; }
  catch (e) {
    if (['not_in_manifest', 'server_not_connected', 'server_not_found'].includes(e?.code) && !inDesktopApp) return { ok: false, skip: true }; // в браузере — через загрузчик
    if (e?.code === 'not_in_manifest') throw ctxErr('Этой странице QA pro не разрешены инструменты моста context_*: страницу нужно опубликовать заново из локальной сессии с этими инструментами (см. инструкцию «Источник контекста»). Пока можно открыть QA pro в браузере с загрузчиком.', 'not_in_manifest');
    if (e?.code === 'tool_error') { const m = String(e.message || ''); throw ctxErr(m || 'Ошибка моста', /не разрешена/.test(m) ? 'root_not_allowed' : 'tool_error'); }
    throw ctxErr(hostErr(e), e?.code || 'host');
  }
}
// tool — context_read | context_write | context_git; долгие (с окном разрешения в загрузчике) ждём до 3 минут
async function ctxCall(tool, args) {
  if (hostOn()) {
    const r = await ctxViaHost(tool, args);
    if (r.ok) { S.ctx.channel = 'app'; return r.data; }
  }
  if (inDesktopApp) throw ctxErr(ctxNoExt(), 'no_channel');
  const p = await ctxPingExt();
  if (!p.ok) throw ctxErr(ctxNoExt(), 'no_ext');
  const r = await bridgeCall({ type: 'CTX_CALL', tool, args }, { timeout: 185000, until: ['CTX_RESULT', 'CTX_ERROR'] });
  if (!r) throw ctxErr('Загрузчик не ответил за 3 минуты. Если открылось окно «Доступ к контексту» — ответьте в нём и повторите.', 'timeout');
  if (r.type === 'CTX_ERROR') throw ctxErr(r.error || 'Ошибка загрузчика', r.code || '');
  S.ctx.channel = 'ext';
  return r.data;
}
async function ctxGh(op, args) {
  if (inDesktopApp) throw ctxErr('GitHub без моста работает в браузере с загрузчиком. В приложении Claude выберите «Git-репозиторий» — его клонирует мост.', 'no_channel');
  const p = await ctxPingExt();
  if (!p.ok) throw ctxErr(ctxNoExt(), 'no_ext');
  const r = await bridgeCall({ type: 'CTX_GH', op, args }, { timeout: 185000, until: ['CTX_RESULT', 'CTX_ERROR'] });
  if (!r) throw ctxErr('Загрузчик не ответил за 3 минуты.', 'timeout');
  if (r.type === 'CTX_ERROR') throw ctxErr(r.error || 'Ошибка загрузчика', r.code || '');
  S.ctx.channel = 'ext';
  return r.data;
}

/* ---------- настройка источника и копия файлов (личные, по продукту) ---------- */
const ctxDocPath = (pid, sfx = '') => `data/users/${S.caps.uid}/ctx_${pid}${sfx}`;
const ctxDbOk = () => !!(S.caps.db && S.caps.uid);
async function ctxLoadSrc(pid) {
  let v = null;
  if (ctxDbOk()) { try { v = (await S.caps.db.doc(ctxDocPath(pid)).get()).data() || null; } catch { /* нет записи */ } }
  if (!v) v = lsGet('qapro.ctx.' + pid, null);
  return v && typeof v === 'object' ? v : null;
}
async function ctxSaveSrc() {
  const C = S.ctx, pid = C.pid;
  if (!pid) return;
  const v = { src: { ...C.src }, pending: [...C.pending].map((p) => [p, ctxText(p)]).filter((x) => x[1] != null && !CTX_BRIDGE.has(C.src.kind)), lastPush: C.lastPush || null, updatedAt: Date.now() };
  lsSet('qapro.ctx.' + pid, { src: v.src, lastPush: v.lastPush });
  if (ctxDbOk()) { try { await S.caps.db.doc(ctxDocPath(pid)).set(v); } catch { /* только в этом браузере */ } }
}
async function ctxCacheWrite() {
  const C = S.ctx;
  if (!ctxDbOk() || !C.pid) return;
  const body = JSON.stringify([...C.files].map(([p, f]) => [p, f.text, f.hash || null]));
  const n = Math.ceil(body.length / CTX_CACHE_PART) || 1;
  try {
    for (let i = 0; i < n; i++) await S.caps.db.doc(ctxDocPath(C.pid, '_c' + i)).set({ s: body.slice(i * CTX_CACHE_PART, (i + 1) * CTX_CACHE_PART) });
    await S.caps.db.doc(ctxDocPath(C.pid, '_cache')).set({ n, at: C.loadedAt, where: ctxWhere(), git: C.git || null });
  } catch { /* копия не сохранилась — при следующем открытии файлы прочитаются заново */ }
}
async function ctxCacheRead(pid) {
  if (!ctxDbOk()) return null;
  try {
    const m = (await S.caps.db.doc(ctxDocPath(pid, '_cache')).get()).data();
    if (!m?.n) return null;
    let body = '';
    for (let i = 0; i < m.n; i++) body += ((await S.caps.db.doc(ctxDocPath(pid, '_c' + i)).get()).data() || {}).s || '';
    const arr = JSON.parse(body);
    return { at: m.at || 0, git: m.git || null, files: new Map(arr.map(([p, text, h]) => [p, { text, hash: h }])) };
  } catch { return null; }
}

/* ---------- чтение источника ---------- */
async function ctxReadSource() {
  const C = S.ctx, src = C.src;
  const files = new Map();
  if (src.kind === 'folder') throw ctxErr('Папку только для чтения нужно выбрать заново: «Выбрать папку».', 'pick');
  if (src.kind === 'github') {
    const st = await ctxGh('status', { repo: src.repo, branch: src.branch });
    if (!src.baseBranch) src.baseBranch = st.defaultBranch;
    if (!src.branch) src.branch = st.defaultBranch;
    const l = await ctxGh('list', { repo: src.repo, branch: src.branch, sub: ctxSub() });
    const want = l.files.map((f) => ({ ...f, rel: ctxRel(f.path) })).filter((f) => f.rel && ctxWanted(f.rel));
    for (let i = 0; i < want.length; i += 60) {
      const r = await ctxGh('read', { repo: src.repo, branch: src.branch, paths: want.slice(i, i + 60).map((f) => f.path) });
      for (const f of r.files || []) if (f.text != null) files.set(ctxRel(f.path), { text: f.text, hash: f.hash });
    }
    C.git = { repo: true, branch: src.branch, base: src.baseBranch, web: l.web, canPush: st.canPush };
    return files;
  }
  if (src.kind === 'git' && !src.cloned) {
    const r = await ctxCall('context_git', { op: 'clone', url: src.url, ...(src.branch ? { branch: src.branch } : {}) });
    src.cloned = r.root;
  }
  const root = ctxRootOf(src);
  const l = await ctxCall('context_read', { op: 'list', root, ...(ctxSub() ? { sub: ctxSub() } : {}) });
  const want = (l.files || []).map((f) => ({ ...f, rel: ctxRel(f.path) })).filter((f) => f.rel && ctxWanted(f.rel));
  let queue = want.map((f) => f.path);
  for (let guard = 0; queue.length && guard < 50; guard++) {
    const r = await ctxCall('context_read', { op: 'read', root, paths: queue.slice(0, 200) });
    const later = [];
    for (const f of r.files || []) {
      if (f.later) later.push(f.path);
      else if (f.text != null) files.set(ctxRel(f.path), { text: f.text, hash: f.hash });
    }
    queue = [...later, ...queue.slice(200)];
  }
  C.git = l.git || null;
  return files;
}
function ctxApplyFiles(files, { at = Date.now(), fromCache = false } = {}) {
  const C = S.ctx;
  // несохранённые изменения (GitHub, папка только для чтения) остаются поверх прочитанного
  for (const p of C.pending) { const cur = C.files.get(p); if (cur && files.get(p)?.text !== cur.text) files.set(p, { ...cur, hash: files.get(p)?.hash ?? cur.hash, dirty: true }); }
  C.files = files; C.loadedAt = at; C.fromCache = fromCache;
  ctxApply();
}

/* ---------- применение к QA pro и откат ---------- */
function ctxApply() {
  const C = S.ctx;
  if (!C.on) return;
  if (!C.backup) C.backup = { cfg: JSON.parse(JSON.stringify(S.cfg)), dirty: { ...S.cfgDirty }, lessons: S.lessons.slice() };
  C.warn = [];
  for (const k of CFG_KEYS) {
    const t = ctxText(ctxCfgPath(k));
    let v = null;
    if (t != null) {
      if (TYPES.includes(k)) { v = ctxParseTpl(t, k); if (!v) C.warn.push(`${ctxFull(ctxCfgPath(k))}: нет образца в блоке \`\`\`json — используется шаблон команды`); }
      else v = ctxParsePlain(t);
    }
    const team = C.backup.cfg;
    setCfgValue(k, v != null ? v : TYPES.includes(k) ? { ...team.tpl[k] } : k === 'rules' ? team.rules : k === 'review' ? team.reviewRules : team.exportFormat);
    S.cfgDirty[k] = false;
  }
  const lt = ctxText(CP.lessons(C));
  S.lessons = lt != null ? ctxParseLessons(lt) : C.backup.lessons.slice();
  const qt = ctxText(CP.context(C));
  if (qt != null && !S.ctxDirty) { S.qaCtx = ctxParseQaCtx(qt); renderQaCtx(true); }
  C.kb = ctxKbSections([...C.files].filter(([p]) => p.startsWith(CP.kbDir(C)) || p.startsWith('knowledge/')));
  C.kbAt = Date.now();
  ctxRehydrate();
  renderCfg(); renderAll();
}
function ctxRehydrate() {
  const p = productById(S.ctx.pid);
  if (p) upsertLocalProduct(p.id, p);
}
function ctxOff() {
  const C = S.ctx, b = C.backup;
  if (b) {
    S.cfg = b.cfg; S.cfgDirty = b.dirty; S.lessons = b.lessons;
    saveDrafts();
  }
  const pid = C.pid;
  C.on = false; C.backup = null; C.kb = []; C.files = new Map(); C.conflicts = []; C.pending = new Set(); C.git = null; C.warn = [];
  const prod = productById(pid);
  if (prod && pid === S.productId) { S.qaCtx = { all: '', api: '', ui: '', e2e: '', ...(prod.qaCtx || {}) }; S.ctxDirty = false; renderQaCtx(true); }
  if (pid && S.caps.db) readProduct(pid).then((p) => { if (p) upsertLocalProduct(pid, p); renderAll(); }).catch(() => {});
  renderCfg(); renderAll();
}
// паспорт: версия из репозитория вместо записи в хранилище (вызывается из hydrateProd)
function ctxPassportFor(pid) {
  if (!ctxActive(pid)) return null;
  return ctxText(CP.passport(S.ctx));
}
// база знаний: разделы из репозитория + разделы продукта с другими названиями
function ctxKbFor(pid) { return ctxActive(pid) ? S.ctx.kb : []; }

/* ---------- запись ---------- */
let ctxFlushT = null;
function ctxPut(rel, text) {
  const C = S.ctx;
  const cur = C.files.get(rel);
  if (cur && cur.text === text) return;
  C.files.set(rel, { text, hash: cur?.hash ?? null, dirty: true });
  C.pending.add(rel);
  if (CTX_BRIDGE.has(C.src.kind)) { clearTimeout(ctxFlushT); ctxFlushT = setTimeout(() => ctxFlush().catch(() => {}), 300); }
  else ctxSaveSrc();
  renderCtxPane();
}
async function ctxFlush({ force = false, only = null } = {}) {
  const C = S.ctx;
  if (!CTX_BRIDGE.has(C.src.kind) || !C.pending.size) return { written: 0 };
  const paths = [...C.pending].filter((p) => !only || only.includes(p));
  if (!paths.length) return { written: 0 };
  const files = paths.map((p) => ({ path: ctxFull(p), text: ctxText(p) ?? '', base: C.files.get(p)?.hash ?? null }));
  try {
    const r = await ctxCall('context_write', { root: ctxRootOf(), files, ...(force ? { force: true } : {}) });
    for (const w of r.written || []) { const rel = ctxRel(w.path); const f = C.files.get(rel); if (f) { f.hash = w.hash; f.dirty = false; } C.pending.delete(rel); }
    const conf = (r.conflicts || []).map((c) => ({ path: ctxRel(c.path), theirs: c.text, hash: c.hash }));
    C.conflicts = [...C.conflicts.filter((c) => !conf.some((x) => x.path === c.path) && C.pending.has(c.path)), ...conf];
    if (conf.length) toast(`Не записано: ${conf.length} ${plural(conf.length, 'файл изменён', 'файла изменены', 'файлов изменены')} в источнике после чтения — выберите версию в настройках «Контекст».`, 'err');
    C.error = '';
    ctxCacheWrite();
    renderCtxPane();
    ctxCall('context_read', { op: 'status', root: ctxRootOf() }).then((g) => { C.git = g; renderCtxPane(); }).catch(() => {});
    return { written: (r.written || []).length, conflicts: conf.length };
  } catch (e) { C.error = 'Не удалось записать в источник: ' + e.message; renderCtxPane(); toast(C.error, 'err'); throw e; }
}
async function ctxResolve(rel, mine) {
  const C = S.ctx, c = C.conflicts.find((x) => x.path === rel);
  if (!c) return;
  if (mine) { await ctxFlush({ force: true, only: [rel] }); C.conflicts = C.conflicts.filter((x) => x.path !== rel); }
  else {
    C.conflicts = C.conflicts.filter((x) => x.path !== rel); C.pending.delete(rel);
    if (c.theirs == null) C.files.delete(rel); else C.files.set(rel, { text: c.theirs, hash: c.hash });
    ctxApply();
  }
  ctxSaveSrc(); renderCtxPane();
}

/* ---------- хуки: что меняется в QA pro, то пишется в источник ---------- */
async function ctxSaveCfg(k) {
  if (TYPES.includes(k) && !tplInfo(k).ok) return toast('Исправьте JSON примера перед сохранением.', 'err');
  if (S.ctx.src.kind === 'folder') return toast('Папка подключена только для чтения: изменение действует до перезагрузки страницы. Чтобы записывать, подключите папку через мост.', 'err');
  const v = cfgValue(k);
  ctxPut(ctxCfgPath(k), TYPES.includes(k) ? ctxMakeTpl(k, v) : ctxMakePlain(k, v));
  S.cfgDirty[k] = false;
  renderCfgTabs(); renderCfgFoot();
  toast(`${cfgName(k)}: ${S.ctx.src.kind === 'github' ? 'сохранено — отправьте изменения в GitHub в настройках «Контекст»' : 'записано в ' + ctxFull(ctxCfgPath(k))}`);
}
function ctxRevertCfg(k) {
  const t = ctxText(ctxCfgPath(k)), b = S.ctx.backup.cfg;
  const v = t != null ? (TYPES.includes(k) ? ctxParseTpl(t, k) : ctxParsePlain(t)) : null;
  setCfgValue(k, v != null ? v : TYPES.includes(k) ? { ...b.tpl[k] } : k === 'rules' ? b.rules : k === 'review' ? b.reviewRules : b.exportFormat);
  S.cfgDirty[k] = false; renderCfg();
  if (S.tab === 'export') renderTab();
}
function ctxCfgFoot(k) {
  const dirty = S.cfgDirty[k], file = ctxFull(ctxCfgPath(k)), has = ctxText(ctxCfgPath(k)) != null;
  const ro = S.ctx.src.kind === 'folder';
  const state = dirty ? '<b>Изменено в этом окне</b>' : has ? `<b>Из источника</b><span>· ${esc(file)}</span>` : `<b>В источнике нет файла</b><span>· действует версия команды; при сохранении появится ${esc(file)}</span>`;
  return `<div class="cfg-state${dirty ? ' dirty' : ''}">${esc(cfgName(k))}: ${state}</div>
    ${dirty ? `<div class="row">${ro ? '' : `<button class="btn accent" type="button" data-cfg="save" data-k="${k}">Сохранить в источник</button>`}<button class="btn" type="button" data-cfg="revert" data-k="${k}">${has ? 'Вернуть версию из источника' : 'Отменить изменения'}</button></div>
    ${ro ? '<p class="hint">Папка подключена только для чтения — изменения действуют до перезагрузки страницы.</p>' : ''}` : ''}`;
}
function ctxSaveLessons() { if (S.ctx.src.kind !== 'folder') ctxPut(CP.lessons(S.ctx), ctxMakeLessons(S.lessons)); }
function ctxAddLesson(l) {
  const id = 'ctxl-' + hash(l.text);
  if (S.lessons.some((x) => normKey(x.text) === normKey(l.text))) return false;
  S.lessons.push({ id, ...l, ctx: true });
  ctxSaveLessons();
  renderCfg();
  return true;
}
function ctxDeleteLesson(id) { S.lessons = S.lessons.filter((x) => x.id !== id); ctxSaveLessons(); renderCfg(); }
function ctxSaveQaCtx() { if (S.ctx.src.kind !== 'folder') ctxPut(CP.context(S.ctx), ctxMakeQaCtx(S.qaCtx)); S.ctxDirty = false; }
function ctxAfterPassport(pid, text) { if (ctxActive(pid) && S.ctx.src.kind !== 'folder') { ctxPut(CP.passport(S.ctx), String(text || '').trim() + '\n'); ctxRehydrate(); } }
function ctxTeamCfg(k, value) { // подписка на настройки команды, пока действует источник: только в резервную копию
  const b = S.ctx.backup;
  if (!b || b.dirty[k]) return;
  if (TYPES.includes(k)) b.cfg.tpl[k] = typeof value === 'object' ? { ...value } : value;
  else if (k === 'rules') b.cfg.rules = value; else if (k === 'review') b.cfg.reviewRules = value; else b.cfg.exportFormat = value;
}

/* ---------- переключение продукта, подключение, обновление ---------- */
let ctxTok = 0;
async function ctxSwitch(pid) {
  const tok = ++ctxTok;
  if (S.ctx.on && S.ctx.pid !== pid) ctxOff();
  const saved = await ctxLoadSrc(pid);
  if (tok !== ctxTok || S.productId !== pid) return;
  const C = S.ctx;
  C.pid = pid; C.src = { ...ctxBlank(), ...(saved?.src || {}) }; C.lastPush = saved?.lastPush || null; C.draft = null; C.error = ''; C.confirm = null;
  C.pending = new Set(); C.conflicts = [];
  if (C.src.kind === 'qa') { renderCtxPane(); return; }
  C.on = true;
  const cache = await ctxCacheRead(pid);
  if (tok !== ctxTok) return;
  const pend = new Map((saved?.pending || []).filter((x) => Array.isArray(x) && typeof x[1] === 'string'));
  if (cache) {
    for (const [p, t] of pend) { const f = cache.files.get(p); cache.files.set(p, { text: t, hash: f?.hash ?? null, dirty: true }); C.pending.add(p); }
    C.git = cache.git; ctxApplyFiles(cache.files, { at: cache.at, fromCache: true });
  }
  if (C.src.kind === 'folder') { if (!cache) { C.error = 'Копия папки не найдена — выберите папку заново.'; C.on = false; } renderCtxPane(); return; }
  ctxRefresh({ quiet: !!cache, tok }).catch(() => {});
}
async function ctxRefresh({ quiet = false, tok = null, pull = false } = {}) {
  const C = S.ctx;
  if (C.busy) return;
  C.busy = pull ? 'pull' : 'read'; C.error = ''; renderCtxPane();
  try {
    if (pull && CTX_BRIDGE.has(C.src.kind)) {
      if (C.pending.size) await ctxFlush();
      const r = await ctxCall('context_git', { op: 'pull', root: ctxRootOf() });
      C.note = r.updated ? `Получены изменения: ${r.head}` : 'Изменений на удалённом нет';
    }
    const files = await ctxReadSource();
    if (tok != null && tok !== ctxTok) return;
    C.on = true;
    ctxApplyFiles(files);
    await ctxCacheWrite();
    await ctxSaveSrc();
    if (!quiet) toast(`Контекст прочитан: ${files.size} ${plural(files.size, 'файл', 'файла', 'файлов')} · ${ctxWhere()}`);
  } catch (e) {
    C.error = (C.fromCache && C.files.size ? `Источник недоступен — работаю с копией от ${fmtDate(C.loadedAt)}. ` : '') + e.message;
    if (!quiet) toast(e.message, 'err');
  } finally { C.busy = ''; renderCtxPane(); }
}
async function ctxConnect() {
  const C = S.ctx, d = C.draft;
  if (!d || !S.productId) return;
  const src = { ...ctxBlank(), ...d, slug: String(d.slug || '').trim(), sub: String(d.sub || '').trim() };
  if (src.slug && !/^[\p{L}\p{N}][\p{L}\p{N}._-]*$/u.test(src.slug)) return ctxFail('Папка продукта — одно слово: буквы, цифры, точка, дефис или подчёркивание.');
  if (src.kind === 'local' && !/^([a-zA-Z]:[\\/]|\/|~)/.test(src.root.trim())) return ctxFail('Укажите полный путь к папке, например C:\\work\\qa-context или /Users/me/qa-context.');
  if (src.kind === 'git' && !/^(https:\/\/|ssh:\/\/|[\w.-]+@[\w.-]+:)/.test(src.url.trim())) return ctxFail('Адрес репозитория — https://… или git@host:группа/репозиторий.git.');
  if (src.kind === 'github' && !/^[\w.-]+\/[\w.-]+$/.test(src.repo.trim())) return ctxFail('Репозиторий GitHub — в виде владелец/название, например team/qa-context.');
  if (src.kind === 'folder') return ctxFail('Для папки только для чтения нажмите «Выбрать папку».');
  const prev = { ...C.src };
  if (C.on) ctxOff();
  C.pid = S.productId; C.src = { ...src, root: src.root.trim(), url: src.url.trim(), repo: src.repo.trim(), cloned: src.kind === 'git' && src.url.trim() === d.prevUrl ? d.cloned || '' : '' };
  C.draft = null; C.pending = new Set(); C.conflicts = []; C.lastPush = null; C.note = '';
  if (C.src.kind === 'qa') { await ctxSaveSrc(); renderCtxPane(); toast('Источник контекста — база QA pro.'); return; }
  C.on = true;
  await ctxRefresh();
  if (C.error && !C.files.size) {
    // не подключилось: форма остаётся с ошибкой, прежний источник не меняется (вернётся по «Отмена»)
    const msg = C.error;
    ctxOff();
    C.draft = { ...d, ...src, cloned: C.src.cloned, prevUrl: C.src.url };
    C.src = prev; C.error = msg;
    renderCtxPane();
  }
}
function ctxFail(msg) { S.ctx.error = msg; renderCtxPane(); return false; }
async function ctxDisconnect() {
  const C = S.ctx;
  if (C.pending.size && C.src.kind === 'github') { C.confirm = { kind: 'off' }; renderCtxPane(); return; }
  if (C.on) ctxOff();
  C.src = { ...ctxBlank() }; C.lastPush = null;
  await ctxSaveSrc();
  if (ctxDbOk()) { try { await S.caps.db.doc(ctxDocPath(C.pid, '_cache')).delete(); } catch { /* нечего удалять */ } }
  renderCtxPane();
  toast('Источник контекста — база QA pro.');
}
// папка только для чтения: файлы выбранной папки → копия в хранилище
async function ctxPickFolder(fileList) {
  const C = S.ctx;
  const all = [...(fileList || [])].filter((f) => CTX_TEXT_RX.test(f.name) && !String(f.webkitRelativePath || f.name).split('/').some((p) => p.startsWith('.') || p === 'node_modules'));
  if (!all.length) return ctxFail('В выбранной папке нет файлов .md, .txt, .json или .yaml.');
  const top = String(all[0].webkitRelativePath || '').split('/')[0] || '';
  const files = new Map();
  for (const f of all.slice(0, 3000)) {
    const full = String(f.webkitRelativePath || f.name).split('/').slice(top ? 1 : 0).join('/');
    const rel = ctxRel(full, { src: { ...C.src, sub: C.draft?.sub ?? C.src.sub } });
    if (!rel || !ctxWanted(rel, { pid: S.productId, src: { ...ctxBlank(), ...(C.draft || C.src) } })) continue;
    if (f.size > 2 * 1024 * 1024) continue;
    files.set(rel, { text: await f.text(), hash: null });
  }
  if (C.on) ctxOff();
  C.pid = S.productId; C.src = { ...ctxBlank(), ...(C.draft || {}), kind: 'folder', root: top }; C.draft = null; C.pending = new Set(); C.conflicts = []; C.error = '';
  C.on = true;
  ctxApplyFiles(files);
  await ctxCacheWrite(); await ctxSaveSrc();
  toast(`Папка «${top || 'выбранная'}» подключена только для чтения: ${files.size} ${plural(files.size, 'файл', 'файла', 'файлов')}.`);
  renderCtxPane();
}

/* ---------- выгрузка базы QA pro в источник ---------- */
async function ctxExportPlan() {
  const C = S.ctx, b = C.backup || { cfg: S.cfg, lessons: S.lessons };
  const out = new Map();
  const team = b.cfg;
  if (team.rules?.trim()) out.set(CP.rules, ctxMakePlain('rules', team.rules));
  if (team.reviewRules?.trim()) out.set(CP.review, ctxMakePlain('review', team.reviewRules));
  if (team.exportFormat?.trim()) out.set(CP.export, ctxMakePlain('export', team.exportFormat));
  for (const t of TYPES) out.set(CP.tpl(t), ctxMakeTpl(t, team.tpl[t]));
  const lessons = (b.lessons || []).filter((l) => !l.ctx);
  if (lessons.length) out.set(CP.lessons(C), ctxMakeLessons(lessons));
  const pid = C.pid;
  let prod = null;
  if (S.caps.db) { try { prod = await readProduct(pid); } catch { /* без продукта */ } }
  const passport = String((S.caps.db ? passCache[pid]?.text : '') || (ctxActive(pid) ? '' : prod?.passport?.text) || '').trim();
  if (passport) out.set(CP.passport(C), passport + '\n');
  const qc = { all: '', api: '', ui: '', e2e: '', ...(prod?.qaCtx || {}) };
  if (ctxHas(qc)) out.set(CP.context(C), ctxMakeQaCtx(qc));
  await kbLoadAll(pid).catch(() => 0);
  const used = new Set();
  for (const x of kbSections(pid).filter((y) => !y.b.ctx)) {
    let name = slugName(x.b.title).slice(0, 60) || 'razdel';
    while (used.has(name)) name += '-2';
    used.add(name);
    const body = kbSectionText(x.d).trim();
    if (body) out.set(CP.kbDir(C) + name + '.md', `# ${x.b.title}\n\n${x.d.summary || x.b.summary ? `> ${String(x.d.summary || x.b.summary).trim()}\n\n` : ''}${body}\n`);
  }
  if (ctxText(CP.claude) == null) out.set(CP.claude, ctxClaudeMd(ctxSlug(C)));
  return out;
}
async function ctxExportAsk() {
  const C = S.ctx;
  C.busy = 'plan'; renderCtxPane();
  try {
    const plan = await ctxExportPlan();
    const over = [...plan.keys()].filter((p) => ctxText(p) != null && ctxText(p) !== plan.get(p));
    C.confirm = { kind: 'export', plan, over };
  } catch (e) { C.error = e.message; }
  finally { C.busy = ''; renderCtxPane(); }
}
async function ctxExportRun() {
  const C = S.ctx, cf = C.confirm;
  if (!cf?.plan) return;
  C.confirm = null;
  for (const [p, t] of cf.plan) ctxPut(p, t);
  if (CTX_BRIDGE.has(C.src.kind)) { C.busy = 'write'; renderCtxPane(); try { await ctxFlush(); } catch { /* ошибка уже показана */ } finally { C.busy = ''; } }
  ctxApply();
  toast(`Выгружено в источник: ${cf.plan.size} ${plural(cf.plan.size, 'файл', 'файла', 'файлов')}${C.src.kind === 'github' ? ' — осталось отправить в GitHub' : ''}.`);
  renderCtxPane();
}

/* ---------- git и GitHub: зафиксировать и отправить ---------- */
async function ctxSend() {
  const C = S.ctx;
  if (C.busy) return;
  C.busy = 'send'; C.error = ''; renderCtxPane();
  const msg = `QA pro: контекст продукта «${productById(C.pid)?.name || ''}»`;
  try {
    if (C.src.kind === 'github') {
      const paths = [...C.pending];
      if (!paths.length) { toast('Нет изменений для отправки.'); return; }
      const files = paths.map((p) => ({ path: ctxFull(p), text: ctxText(p) ?? '', base: C.files.get(p)?.hash ?? null }));
      const r = await ctxGh('commit', { repo: C.src.repo, branch: C.src.branch, base: C.src.baseBranch, files, message: msg });
      if (!r.committed) {
        C.conflicts = (r.conflicts || []).map((c) => ({ path: ctxRel(c.path), theirs: null, hash: c.hash, gh: true }));
        throw ctxErr(`В GitHub изменились ${C.conflicts.length} ${plural(C.conflicts.length, 'файл', 'файла', 'файлов')} после чтения. Нажмите «Обновить из источника» — ваши изменения останутся поверх — и отправьте снова.`, 'conflict');
      }
      for (const p of paths) { const f = C.files.get(p); if (f) { f.hash = r.hashes?.[ctxFull(p)] ?? f.hash; f.dirty = false; } C.pending.delete(p); }
      if (!C.src.baseBranch) C.src.baseBranch = r.base;
      C.src.branch = r.branch; // дальше работаем в своей ветке, пока запрос на слияние не принят
      C.lastPush = { branch: r.branch, pr: r.pr, at: Date.now() };
      await ctxSaveSrc(); await ctxCacheWrite();
      toast(`Отправлено в ветку ${r.branch}. Откройте запрос на слияние по ссылке в настройках «Контекст».`);
      return;
    }
    if (C.pending.size) await ctxFlush();
    if (C.conflicts.length) throw ctxErr('Сначала разберите файлы, которые изменились в источнике.', 'conflict');
    const paths = [...C.files.keys()].map((p) => ctxFull(p));
    const c = await ctxCall('context_git', { op: 'commit', root: ctxRootOf(), message: msg, paths: ctxSub() ? [ctxSub()] : paths.length ? paths : undefined });
    const p = await ctxCall('context_git', { op: 'push', root: ctxRootOf() });
    C.lastPush = { branch: p.branch, pr: p.pr, at: Date.now(), committed: c.committed };
    C.git = p.status || C.git;
    await ctxSaveSrc();
    toast(c.committed ? `Изменения в ветке ${p.branch} отправлены.` : `Новых изменений нет — ветка ${p.branch} отправлена.`);
  } catch (e) { C.error = e.message; toast(e.message, 'err'); }
  finally { C.busy = ''; renderCtxPane(); }
}
async function ctxBackToBase() {
  const C = S.ctx;
  if (C.src.kind === 'github') { C.src.branch = C.src.baseBranch || ''; C.lastPush = null; await ctxSaveSrc(); return ctxRefresh(); }
}
async function ctxDownloadPending() {
  for (const p of S.ctx.pending) { const t = ctxText(p); if (t != null) await downloadFile(p.replace(/\//g, '__'), t); }
}

/* ---------- вкладка настроек «Контекст» ---------- */
const ctxAgo = (t) => (t ? new Date(t).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '—');
function ctxFoundHTML() {
  const C = S.ctx, has = (p) => ctxText(p) != null;
  const tplN = TYPES.filter((t) => has(CP.tpl(t))).length;
  const kbN = C.kb.length, ln = has(CP.lessons(C)) ? ctxParseLessons(ctxText(CP.lessons(C))).length : 0;
  const row = (ok, name, extra = '') => `<li class="${ok ? 'ok' : 'no'}"><span aria-hidden="true">${ok ? '✓' : '—'}</span> ${name}${extra ? ` <span class="muted">· ${extra}</span>` : ''}</li>`;
  return `<ul class="ctx-found">
    ${row(has(CP.rules), 'Правила для агента', esc(ctxFull(CP.rules)))}
    ${row(has(CP.review), 'Правила ревью', esc(ctxFull(CP.review)))}
    ${row(tplN > 0, `Шаблоны: ${tplN} из 3`, TYPES.filter((t) => has(CP.tpl(t))).map((t) => TL[t]).join(', ') || 'templates/api.md, ui.md, e2e.md')}
    ${row(has(CP.export), 'Формат экспорта')}
    ${row(has(CP.lessons(C)), 'Память агента', has(CP.lessons(C)) ? `${ln} ${plural(ln, 'правило', 'правила', 'правил')}` : esc(ctxFull(CP.lessons(C))))}
    ${row(has(CP.passport(C)), 'Знания о продукте (паспорт)', esc(ctxFull(CP.passport(C))))}
    ${row(has(CP.context(C)), 'Доп. контекст QA', esc(ctxFull(CP.context(C))))}
    ${row(kbN > 0, `База знаний: ${kbN} ${plural(kbN, 'раздел', 'раздела', 'разделов')}`, esc(ctxFull(CP.kbDir(C))) + ' и ' + esc(ctxFull('knowledge/')))}
  </ul>
  <p class="hint">Чего нет в источнике, берётся из базы QA pro. Разделы базы знаний из репозитория добавляются к базе знаний продукта; при совпадении названия используется версия из репозитория.</p>`;
}
function ctxGitHTML() {
  const C = S.ctx, g = C.git, k = C.src.kind;
  if (k === 'folder') return '';
  if (k === 'github') {
    const lp = C.lastPush;
    return `<div class="ctx-git"><div><b>GitHub</b> · ветка <span class="mono">${esc(C.src.branch || '—')}</span>${C.src.baseBranch && C.src.branch !== C.src.baseBranch ? ` (основная — <span class="mono">${esc(C.src.baseBranch)}</span>)` : ''} · неотправленных изменений: ${C.pending.size}</div>
      ${lp?.pr ? `<div>Отправлено в <span class="mono">${esc(lp.branch)}</span> ${ctxAgo(lp.at)} · <a href="${esc(lp.pr)}" target="_blank" rel="noopener">открыть запрос на слияние</a>${C.src.branch !== C.src.baseBranch ? ' · <button class="link" type="button" data-ctx-act="base">после слияния — вернуться на основную ветку</button>' : ''}</div>` : ''}</div>`;
  }
  if (!g) return '';
  if (!g.repo) return '<div class="ctx-git">Папка без git: изменения сразу записываются в файлы, история не ведётся.</div>';
  const lp = C.lastPush;
  return `<div class="ctx-git"><div><b>git</b> · ветка <span class="mono">${esc(g.branch || '—')}</span>${g.behind ? ` · отстаёт на ${g.behind}` : ''}${g.ahead ? ` · впереди на ${g.ahead}` : ''} · изменённых файлов: ${(g.changed || []).length}${g.remote ? ` · <span class="mono">${esc(g.remote)}</span>` : ''}</div>
    ${lp ? `<div>Отправлено в <span class="mono">${esc(lp.branch)}</span> ${ctxAgo(lp.at)}${lp.pr ? ` · <a href="${esc(lp.pr)}" target="_blank" rel="noopener">открыть запрос на слияние</a>` : ''}</div>` : ''}</div>`;
}
function ctxDraftHTML() {
  const C = S.ctx, d = C.draft;
  const inp = (key, lbl, ph, hint = '') => `<div class="field"><label class="lbl" for="ctx-${key}">${lbl}</label><input id="ctx-${key}" data-ctxf="${key}" type="text" class="mono" spellcheck="false" value="${esc(d[key] || '')}" placeholder="${esc(ph)}">${hint ? `<p class="hint">${hint}</p>` : ''}</div>`;
  const kinds = `<div class="ctx-kinds" role="radiogroup" aria-label="Источник контекста">${Object.entries(CTX_KINDS).map(([k, x]) => `<label class="type-opt" data-t="ctx"><input type="radio" name="ctx-kind" data-ctxk="${k}" ${d.kind === k ? 'checked' : ''}><b>${x.title}</b><span>${x.desc}</span></label>`).join('')}</div>`;
  let fields = '';
  if (d.kind === 'local') fields = inp('root', 'Папка на компьютере', 'C:\\work\\qa-context или /Users/me/qa-context', 'Полный путь. В приложении Claude папку нужно указать и в настройках моста; в браузере загрузчик спросит разрешение.');
  if (d.kind === 'git') fields = `<div class="grid2">${inp('url', 'Адрес репозитория', 'https://git.company.ru/qa/context.git')}${inp('branch', 'Ветка — необязательно', 'main')}</div><p class="hint">Мост клонирует репозиторий в ~/.qa-pro-bridge/repos. Вход — ваш обычный для git: ключ SSH или сохранённый пароль.</p>`;
  if (d.kind === 'github') fields = `<div class="grid2">${inp('repo', 'Репозиторий GitHub', 'team/qa-context')}${inp('branch', 'Ветка — необязательно', 'main')}</div><p class="hint">Токен GitHub указывается в настройках загрузчика — страница его не видит.</p>`;
  const common = d.kind === 'qa' ? '' : `<div class="grid2">${inp('sub', 'Подпапка контекста — необязательно', 'qa-context')}${inp('slug', 'Папка продукта', slugName(curProduct()?.name || 'product'), 'products/&lt;папка&gt; — паспорт, доп. контекст, память и база знаний продукта.')}</div>`;
  const pick = d.kind === 'folder' ? `<div class="row"><label class="btn accent" style="cursor:pointer">Выбрать папку<input type="file" id="ctx-pick" webkitdirectory directory multiple hidden></label><span class="hint">Файлы читаются в браузере. Чтобы подтянуть изменения, выберите папку ещё раз.</span></div>`
    : `<div class="row"><button class="btn accent" type="button" data-ctx-act="connect">${d.kind === 'qa' ? 'Сохранить' : 'Подключить'}</button>${S.ctx.src.kind !== 'qa' || C.on ? '<button class="btn" type="button" data-ctx-act="cancel">Отмена</button>' : ''}</div>`;
  return `${kinds}${fields}${common}${pick}`;
}
function ctxPaneHTML() {
  const C = S.ctx;
  if (!S.productId) return '<p class="hint">Выберите продукт: источник контекста задаётся для каждого продукта.</p>';
  const p = curProduct();
  if (C.pid !== S.productId) return '<p class="hint">Загружаю настройку источника…</p>';
  const head = `<p class="hint">Откуда QA pro берёт правила, шаблоны, память агента, знания о продукте и базу знаний для продукта «${esc(p?.name || '')}». Настройка личная: коллеги выбирают источник сами.</p>`;
  const err = C.error ? `<div class="banner err"><div>${esc(C.error)}</div></div>` : '';
  const warn = C.warn.length ? `<div class="banner warn"><div>${C.warn.map(esc).join('<br>')}</div></div>` : '';
  if (C.draft) return `${head}${err}${ctxDraftHTML()}`;
  if (C.src.kind === 'qa' || !C.on) return `${head}${err}<div class="exp-card"><div class="exp-row"><b>${CTX_KINDS.qa.title}</b><span class="muted small">${CTX_KINDS.qa.desc}</span></div><div class="row"><button class="btn accent" type="button" data-ctx-act="edit">Подключить репозиторий или папку</button></div></div>`;
  const busy = C.busy ? `<span class="hint">${{ read: 'Читаю источник…', pull: 'Получаю изменения…', write: 'Записываю…', send: 'Отправляю…', plan: 'Собираю файлы…' }[C.busy] || 'Работаю…'}</span>` : '';
  const channel = C.src.kind === 'folder' ? 'выбор папки на странице' : C.src.kind === 'github' ? 'загрузчик в браузере → GitHub' : C.channel === 'app' ? 'мост в приложении Claude' : C.channel === 'ext' ? 'загрузчик в браузере → мост' : '—';
  const conflicts = C.conflicts.length ? `<div class="banner warn"><div><b>Файлы изменились в источнике после чтения</b> — QA pro их не перезаписал. Выберите версию:
      <ul class="ctx-conf">${C.conflicts.map((c) => `<li><span class="mono">${esc(ctxFull(c.path))}</span>${c.gh ? '' : ` <button class="link" type="button" data-ctx-act="mine" data-p="${esc(c.path)}">оставить мою</button> <button class="link" type="button" data-ctx-act="theirs" data-p="${esc(c.path)}">взять из источника</button>`}</li>`).join('')}</ul></div></div>` : '';
  const cf = C.confirm;
  const confirm = cf?.kind === 'export' ? `<div class="banner warn"><div><b>Выгрузить в источник ${cf.plan.size} ${plural(cf.plan.size, 'файл', 'файла', 'файлов')}?</b> Правила, шаблоны и память команды, паспорт, доп. контекст и разделы базы знаний продукта из QA pro${cf.over.length ? `. Будут перезаписаны: ${cf.over.slice(0, 8).map((x) => `<span class="mono">${esc(ctxFull(x))}</span>`).join(', ')}${cf.over.length > 8 ? ` и ещё ${cf.over.length - 8}` : ''}` : ''}.
      <div class="row" style="margin-top:8px"><button class="btn accent" type="button" data-ctx-act="export-run">Выгрузить</button><button class="btn" type="button" data-ctx-act="confirm-no">Отмена</button></div></div></div>`
    : cf?.kind === 'off' ? `<div class="banner warn"><div><b>Есть неотправленные изменения: ${C.pending.size}.</b> После отключения они пропадут.<div class="row" style="margin-top:8px"><button class="btn" type="button" data-ctx-act="off-force">Отключить без отправки</button><button class="btn" type="button" data-ctx-act="confirm-no">Отмена</button></div></div></div>` : '';
  const pend = C.pending.size && !CTX_BRIDGE.has(C.src.kind) ? `<div class="hint">Изменения, ещё не ${C.src.kind === 'github' ? 'отправленные в GitHub' : 'записанные (папка только для чтения)'}: ${[...C.pending].map((x) => `<span class="mono">${esc(ctxFull(x))}</span>`).join(', ')}${C.src.kind === 'folder' ? ' · <button class="link" type="button" data-ctx-act="download">скачать файлы</button>' : ''}</div>` : '';
  const canSend = C.src.kind === 'github' ? C.pending.size > 0 : CTX_BRIDGE.has(C.src.kind) && !!C.git?.repo && !!C.git?.remote;
  const acts = `<div class="row">
      ${C.src.kind === 'folder' ? `<label class="btn" style="cursor:pointer">Выбрать папку заново<input type="file" id="ctx-pick" webkitdirectory directory multiple hidden></label>` : `<button class="btn" type="button" data-ctx-act="refresh" ${C.busy ? 'disabled' : ''}>${C.src.kind === 'git' || (C.src.kind === 'local' && C.git?.repo && C.git?.remote) ? 'Обновить (git pull)' : 'Обновить из источника'}</button>`}
      ${ctxWritable() ? `<button class="btn" type="button" data-ctx-act="export" ${C.busy ? 'disabled' : ''}>Выгрузить контекст QA pro в источник</button>` : ''}
      ${canSend ? `<button class="btn accent" type="button" data-ctx-act="send" ${C.busy ? 'disabled' : ''}>${C.src.kind === 'github' ? 'Отправить в GitHub' : 'Зафиксировать и отправить'}</button>` : ''}
      <button class="link" type="button" data-ctx-act="edit">Изменить</button><button class="link" type="button" data-ctx-act="off">Отключить</button>${busy}</div>`;
  return `${head}${err}${warn}${conflicts}${confirm}
    <div class="exp-card">
      <div class="exp-row"><b>${CTX_KINDS[C.src.kind].title}</b><span class="muted small mono" style="word-break:break-all">${esc(ctxWhere())}</span></div>
      <div class="hint">Канал: ${channel} · прочитано ${ctxAgo(C.loadedAt)}${C.fromCache ? ' (копия)' : ''} · ${C.files.size} ${plural(C.files.size, 'файл', 'файла', 'файлов')} · папка продукта <span class="mono">products/${esc(ctxSlug())}</span>${C.note ? ` · ${esc(C.note)}` : ''}</div>
      ${ctxGitHTML()}
      ${ctxFoundHTML()}
      ${pend}
      ${acts}
    </div>`;
}
function renderCtxPane() {
  const el = $('#ctx-body');
  renderCfgTabs();
  if (!el || $('#set-ctx')?.hidden) return;
  if (S.ctx.draft && isTyping(el)) return; // не мешаем заполнять форму
  el.innerHTML = ctxPaneHTML();
}
function ctxEdit() {
  const C = S.ctx;
  C.draft = { ...ctxBlank(), ...C.src, kind: C.src.kind === 'qa' ? 'local' : C.src.kind, prevUrl: C.src.url, cloned: C.src.cloned };
  C.error = ''; C.confirm = null;
  renderCtxPane();
}
function bindCtxPane() {
  const el = $('#ctx-body');
  if (!el || el.dataset.bound) return;
  el.dataset.bound = '1';
  el.addEventListener('change', (e) => {
    const t = e.target;
    if (t.dataset.ctxk) { S.ctx.draft = { ...S.ctx.draft, kind: t.dataset.ctxk }; S.ctx.error = ''; el.innerHTML = ctxPaneHTML(); }
    else if (t.id === 'ctx-pick') ctxPickFolder(t.files).catch((x) => ctxFail(x.message));
  });
  el.addEventListener('input', (e) => { const k = e.target.dataset.ctxf; if (k && S.ctx.draft) S.ctx.draft[k] = e.target.value; });
  el.addEventListener('click', (e) => {
    const b = e.target.closest('[data-ctx-act]');
    if (!b) return;
    const a = b.dataset.ctxAct, C = S.ctx;
    if (a === 'edit') ctxEdit();
    else if (a === 'cancel') { C.draft = null; C.error = ''; if (!C.on && C.src.kind !== 'qa') ctxSwitch(S.productId); else renderCtxPane(); }
    else if (a === 'connect') ctxConnect();
    else if (a === 'refresh') ctxRefresh({ pull: C.src.kind === 'git' || (C.src.kind === 'local' && !!C.git?.repo && !!C.git?.remote) });
    else if (a === 'export') ctxExportAsk();
    else if (a === 'export-run') ctxExportRun();
    else if (a === 'confirm-no') { C.confirm = null; renderCtxPane(); }
    else if (a === 'send') ctxSend();
    else if (a === 'off') ctxDisconnect();
    else if (a === 'off-force') { C.pending = new Set(); C.confirm = null; ctxDisconnect(); }
    else if (a === 'mine' || a === 'theirs') ctxResolve(b.dataset.p, a === 'mine');
    else if (a === 'base') ctxBackToBase();
    else if (a === 'download') ctxDownloadPending();
  });
}
