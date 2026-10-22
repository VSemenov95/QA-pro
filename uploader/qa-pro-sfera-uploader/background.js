// QA pro — загрузчик в Сферу ФТ. Фоновая часть.
// Вход — по cookie ACCESS_TOKEN той Сферы, в которую пользователь уже вошёл в этом браузере.
// Загрузка — POST /app/testing/api/v1/test-issues по одному кейсу (как в QA Toolkit), без метки AI_gen:
//   смоук → метка SMOKE, регресс → поле «Регрессионный» (ti_regressive).

const QA_PRO_URL = 'https://claude.ai/artifact/TrWQGTAs4Wqe5XjZBcQFCp';
const DEFAULTS = { baseUrl: 'https://sfera-t1.ru', lastSectionUrl: '', qaProOrigins: [], anySite: false, keepQaPro: false, qaProUrl: QA_PRO_URL, desktopBridge: true, bridgePort: 47321, ghToken: '', ghApi: 'https://api.github.com', ctxGrants: {} };
importScripts('context.js'); // источник контекста QA pro: папка или git через мост, GitHub через API
const trimBase = (u) => String(u || '').trim().replace(/\/+$/, '');
async function getSettings() {
  const { settings } = await chrome.storage.local.get('settings');
  return { ...DEFAULTS, ...(settings || {}) };
}
async function saveSettings(patch) {
  const s = { ...(await getSettings()), ...patch };
  await chrome.storage.local.set({ settings: s });
  return s;
}

async function getCookieToken(baseUrl) {
  try {
    const c = await chrome.cookies.get({ url: baseUrl, name: 'ACCESS_TOKEN' });
    return c?.value || null;
  } catch { return null; }
}
const NO_TOKEN = 'Не найден вход в Сферу ФТ (cookie ACCESS_TOKEN). Откройте Сферу в этом браузере, войдите и повторите.';
async function sfera() {
  const s = await getSettings(), base = trimBase(s.baseUrl), token = await getCookieToken(base);
  return { base, token, settings: s };
}

// ---------- справочники статусов и приоритетов (как в QA Toolkit) ----------
const isInnolocal = (b) => /inno\.local|innolocal/i.test(b || '');
const INNOLOCAL_STATUS_ID_FALLBACK = 'a7260a64-d074-11f0-a7ab-02430b8e591b';
function pickDefaultAttrValueId(values) {
  const def = (values || []).find((v) => v.code === 'created') || (values || []).find((v) => v.isDefault) || (values || [])[0];
  return def?.id || '';
}
async function fetchAttributesCatalog(base, token, projectCode, categories) {
  try {
    const res = await fetch(`${base}/app/testing/api/v1/attributes?page=0&size=50&sort=entityInfo.modifiedAt%2Cdesc&categories=${encodeURIComponent(categories)}&projectCodes=${encodeURIComponent(projectCode)}`, { headers: { Authorization: `Bearer ${token}` } });
    if (res.ok) return (await res.json()).content || [];
  } catch { /* справочник недоступен — останутся значения по умолчанию */ }
  return [];
}
async function fetchDefaultTestCaseAttrs(base, token, projectCode) {
  const result = { statusId: '', tiStatusId: '', tiPriorityId: '' };
  const statusAttr = (await fetchAttributesCatalog(base, token, projectCode, 'TEST_CASE_STATUS')).find((a) => a.objectType === 'TEST_CASE');
  if (statusAttr) result.statusId = pickDefaultAttrValueId(statusAttr.values);
  const system = await fetchAttributesCatalog(base, token, projectCode, 'SYSTEM');
  const tiStatus = system.find((a) => a.code === 'ti_status' && a.objectType === 'TEST_CASE');
  const tiPrio = system.find((a) => a.code === 'ti_priority' && a.objectType === 'TEST_CASE');
  if (tiStatus) result.tiStatusId = pickDefaultAttrValueId(tiStatus.values);
  if (tiPrio) result.tiPriorityId = pickDefaultAttrValueId(tiPrio.values);
  return result;
}
function patchTcForInnolocal(item, statusId) {
  const { status, ...rest } = item;
  return {
    ...rest,
    ti_priority: 'c291b09a-ea39-11ef-b981-02e2c45bc74d',
    ti_status: 'c2916be4-ea39-11ef-b981-02e2c45bc74d',
    statusId: statusId || INNOLOCAL_STATUS_ID_FALLBACK,
    automationStatus: 'A2_NOT_AUTOMATED',
    attachments: [],
    Tekhnologiya_a7: '40049116-aed7-4819-86a1-1391ec4cff58',
    Etap_Testirovaniya_67: ['f92bb26d-c64a-41c4-9e15-2ba54828fbd4'],
    Napravleniye_ef: '2f872761-e2f6-4d79-8399-4e34b9f0afc3',
  };
}

// ---------- кейс → тело запроса Сферы ----------
const PRIORITIES = new Set(['P1_LOW', 'P2_MEDIUM', 'P3_HIGH', 'P4_CRITICAL']);
const PRIO_WORDS = { low: 'P1_LOW', 'низкий': 'P1_LOW', medium: 'P2_MEDIUM', 'средний': 'P2_MEDIUM', high: 'P3_HIGH', 'высокий': 'P3_HIGH', critical: 'P4_CRITICAL', 'критический': 'P4_CRITICAL' };
const rowsOf = (v) => (Array.isArray(v) ? v : []).filter((x) => x && typeof x === 'object').map((x) => ({ action: String(x.action ?? ''), expectedResult: String(x.expectedResult ?? '') }));
function suitesOf(tc) {
  const s = (Array.isArray(tc.suites) ? tc.suites : []).map((x) => String(x).toLowerCase());
  return { smoke: s.some((x) => /smoke|смоук/.test(x)), regress: tc.ti_regressive === true || s.some((x) => /regress|регресс/.test(x)) };
}
function labelsOf(tc) {
  const { smoke } = suitesOf(tc);
  const own = (Array.isArray(tc.labels) ? tc.labels : []).map(String).filter((l) => l && l !== 'AI_gen');
  return [...new Set([...own, ...(smoke ? ['SMOKE'] : [])])];
}
function toSferaItem(tc, meta) {
  const p = String(tc.priority || '').trim();
  return {
    ti_regressive: suitesOf(tc).regress,
    name: String(tc.name || '').slice(0, 256),
    sectionId: Number(meta.sectionId) || 0,
    ti_priority: '0eaae9f6-6f0f-11f0-871f-005056053b34',
    ti_status: '0ea9d016-6f0f-11f0-871f-005056053b34',
    type: 'T1_TEST_CASE',
    priority: PRIORITIES.has(p) ? p : PRIO_WORDS[p.toLowerCase()] || 'P2_MEDIUM',
    labels: labelsOf(tc),
    description: String(tc.description || ''),
    preConditions: rowsOf(tc.preConditions),
    steps: rowsOf(tc.steps),
    postConditions: rowsOf(tc.postConditions),
    projectCode: meta.projectCode,
  };
}

async function uploadItems(items, meta, onProgress) {
  const { base, token } = await sfera();
  if (!token) throw new Error(NO_TOKEN);
  if (!meta?.projectCode || !meta?.sectionId) throw new Error('Не выбран проект или раздел Сферы ФТ.');
  const attrs = await fetchDefaultTestCaseAttrs(base, token, meta.projectCode);
  const apiUrl = `${base}/app/testing/api/v1/test-issues`;
  const results = [];
  for (let i = 0; i < items.length; i++) {
    const src = items[i];
    let body = toSferaItem(src, meta);
    body = isInnolocal(base) ? patchTcForInnolocal(body, attrs.statusId)
      : { ...body, statusId: attrs.statusId, attachments: [], ...(attrs.tiPriorityId ? { ti_priority: attrs.tiPriorityId } : {}), ...(attrs.tiStatusId ? { ti_status: attrs.tiStatusId } : {}) };
    let r;
    try {
      const res = await fetch(apiUrl, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify(body) });
      const text = await res.text();
      let data; try { data = JSON.parse(text); } catch { data = text; }
      r = res.ok ? { ok: true, code: String(data?.testIssueCode || data?.code || data?.id || '') }
        : { ok: false, status: res.status, error: (typeof data === 'string' ? data : JSON.stringify(data)).slice(0, 400) };
    } catch (e) { r = { ok: false, status: 0, error: 'Сетевая ошибка: ' + (e?.message || e) }; }
    results.push({ ref: src.ref ?? null, index: i, name: body.name, ...r });
    onProgress?.(results);
  }
  return results;
}

async function getSections(projectCode) {
  const { base, token } = await sfera();
  if (!token) throw new Error(NO_TOKEN);
  const res = await fetch(`${base}/app/testing/api/v1/projects/${encodeURIComponent(projectCode)}/sections`, { headers: { Authorization: `Bearer ${token}` } });
  if (!res.ok) throw new Error(`Сфера ответила ${res.status} при получении разделов проекта ${projectCode}.`);
  const data = await res.json();
  return (Array.isArray(data) ? data : data.content || []).map((x) => ({ id: x.id, name: x.name, parentSectionId: x.parentSectionId ?? null }));
}

// ---------- задания от страниц QA pro ----------
// Задание хранится в storage.session: фоновая часть может перезапуститься, пока открыто окно загрузки.
const jobKey = (id) => 'job:' + id;
async function getJob(id) { return (await chrome.storage.session.get(jobKey(id)))[jobKey(id)] || null; }
async function setJob(id, job) { await chrome.storage.session.set({ [jobKey(id)]: job }); }
async function dropJob(id) { await chrome.storage.session.remove(jobKey(id)); }
async function notifyPage(job, payload) {
  if (job?.via === 'bridge') { bridgeSend(payload.cancelled ? { t: 'cancelled', id: job.remoteId } : { t: 'result', id: job.remoteId, results: payload.results || [], section: payload.section || null }); return; }
  if (!job?.tabId) return;
  try { await chrome.tabs.sendMessage(job.tabId, { type: 'SFERA_RESULT', requestId: job.requestId, ...payload }, { frameId: job.frameId || 0 }); } catch { /* вкладку закрыли */ }
}
async function openUploadWindow(jobId) {
  const w = await chrome.windows.create({ url: chrome.runtime.getURL('upload.html' + (jobId ? '?job=' + encodeURIComponent(jobId) : '')), type: 'popup', width: 820, height: 860 });
  return w?.id;
}
chrome.windows.onRemoved.addListener(async (windowId) => {
  const all = await chrome.storage.session.get(null);
  for (const [k, job] of Object.entries(all)) {
    if (!k.startsWith('job:') || job.windowId !== windowId) continue;
    if (!job.done) await notifyPage(job, { cancelled: true, results: [] });
    await chrome.storage.session.remove(k);
  }
});
chrome.action.onClicked.addListener(() => { openUploadWindow(null); });

// ---------- где работает мост ----------
// Статические адреса — content_scripts в manifest.json. Дополнительно: свои адреса QA pro (внутренний веб-сервер)
// и режим «на любых сайтах» — регистрируются здесь, после разрешения браузера.
const STATIC_MATCHES = chrome.runtime.getManifest().content_scripts[0].matches;
async function registerBridge(id, matches) {
  try { await chrome.scripting.unregisterContentScripts({ ids: [id] }); } catch { /* не было */ }
  if (!matches.length) return;
  const base = { id, matches, js: ['bridge.js'], allFrames: true, runAt: 'document_start', persistAcrossSessions: true };
  try { await chrome.scripting.registerContentScripts([{ ...base, matchOriginAsFallback: true }]); }
  catch { await chrome.scripting.registerContentScripts([base]); } // старый браузер без matchOriginAsFallback
}
const customMatches = (origins) => (origins || []).map((o) => trimBase(o) + '/*');
async function syncQaProScripts(origins) { await registerBridge('qa-pro-bridge-custom', customMatches(origins)); }
async function syncAnySite(on) { await registerBridge('qa-pro-bridge-any', on ? ['https://*/*'] : []); }

// Мост подключается к странице при её загрузке. Чтобы не просить обновлять уже открытый QA pro после установки
// или обновления расширения, подключаем его к открытым вкладкам сразу.
async function injectOpenTabs() {
  const s = await getSettings();
  const patterns = [...new Set([...STATIC_MATCHES, ...customMatches(s.qaProOrigins), ...(s.anySite ? ['https://*/*'] : [])])];
  let tabs = [];
  try { tabs = await chrome.tabs.query({ url: patterns }); } catch { return 0; }
  let n = 0;
  for (const t of tabs) {
    try { await chrome.scripting.executeScript({ target: { tabId: t.id, allFrames: true }, files: ['bridge.js'] }); n++; } catch { /* нет доступа к вкладке */ }
  }
  return n;
}
chrome.runtime.onInstalled.addListener(async () => {
  const s = await getSettings();
  try { await syncQaProScripts(s.qaProOrigins); await syncAnySite(s.anySite); } catch { /* разрешение отозвано */ }
  await injectOpenTabs();
  ensureQaProTab().catch(() => {});
});

// QA pro в приложении Claude для компьютера не видит расширений: задания оттуда принимает QA pro во вкладке Chrome.
// По желанию держим такую вкладку открытой: закреплённой, в фоне, без выгрузки из памяти.
async function ensureQaProTab() {
  const s = await getSettings();
  if (!s.keepQaPro || !s.qaProUrl) return null;
  let url; try { url = new URL(s.qaProUrl); } catch { return null; }
  if (url.protocol !== 'https:') return null;
  let tabs = [];
  try { tabs = await chrome.tabs.query({ url: url.origin + url.pathname + '*' }); } catch { /* нет доступа */ }
  let tab = tabs[0];
  if (!tab) tab = await chrome.tabs.create({ url: url.href, pinned: true, active: false });
  try { await chrome.tabs.update(tab.id, { autoDiscardable: false }); } catch { /* старый браузер */ }
  return tab;
}
// При запуске Chrome даём браузеру восстановить прошлые вкладки, чтобы не открыть вторую.
chrome.runtime.onStartup.addListener(() => { setTimeout(() => ensureQaProTab().catch(() => {}), 8000); });

// ---------- связь с приложением Claude через локальный мост qa-pro-bridge ----------
// QA pro в приложении Claude не видит расширений. Мост (MCP-сервер приложения) слушает 127.0.0.1 и передаёт
// задания сюда по WebSocket. Соединение держим постоянно: сердцебиение моста не даёт фоновой части уснуть,
// а таймер раз в 30 секунд переподключается, если мост или браузер перезапускались.
let bws = null, bwsState = { connected: false, at: 0, version: '', error: '' }, bwsProbing = false, bwsVersion = '';
const bridgeSocket = () => bws; // для context.js
async function bridgeConnect() {
  const s = await getSettings();
  if (!s.desktopBridge) { try { bws?.close(); } catch { /* уже закрыт */ } bws = null; return; }
  if (bwsProbing || (bws && (bws.readyState === WebSocket.CONNECTING || bws.readyState === WebSocket.OPEN))) return;
  const port = Number(s.bridgePort) || 47321;
  // Сначала тихая проверка: если моста нет, не открываем WebSocket (иначе браузер пишет ошибку раз в 30 секунд).
  bwsProbing = true;
  try {
    const r = await fetch(`http://127.0.0.1:${port}/health`, { cache: 'no-store' });
    const j = await r.json();
    if (j?.name !== 'qa-pro-bridge') throw new Error('not bridge');
    bwsVersion = String(j.version || '');
  } catch { bwsState = { connected: false, at: Date.now(), version: '', error: 'Мост не найден' }; return; }
  finally { bwsProbing = false; }
  if (bws && (bws.readyState === WebSocket.CONNECTING || bws.readyState === WebSocket.OPEN)) return;
  let w;
  try { w = new WebSocket(`ws://127.0.0.1:${port}/ext`); } catch (e) { bwsState = { connected: false, at: Date.now(), error: String(e?.message || e) }; return; }
  bws = w;
  w.onopen = async () => {
    const st = await getSettings();
    w.send(JSON.stringify({ t: 'hello', version: chrome.runtime.getManifest().version, baseUrl: trimBase(st.baseUrl) }));
    bwsState = { connected: true, at: Date.now(), version: bwsVersion, error: '' };
    for (const m of await outboxGet()) w.send(JSON.stringify(m)); // всё, что мост ещё не подтвердил
  };
  w.onmessage = (e) => { let m; try { m = JSON.parse(e.data); } catch { return; } onBridgeMessage(m).catch(() => {}); };
  w.onclose = () => {
    if (bws === w) bws = null;
    if (bwsState.connected) bwsState = { connected: false, at: Date.now(), version: '', error: '' };
  };
  w.onerror = () => { bwsState = { ...bwsState, connected: false, at: Date.now(), error: 'Мост не отвечает' }; };
}
// Сообщения о заданиях (открыто окно, результат, отмена) хранятся, пока мост их не подтвердит:
// результат не потеряется, даже если приложение Claude и мост были закрыты во время загрузки.
const outboxGet = async () => (await chrome.storage.local.get('bridgeOutbox')).bridgeOutbox || [];
let outboxChain = Promise.resolve();
const outboxEdit = (fn) => (outboxChain = outboxChain.then(async () => { await chrome.storage.local.set({ bridgeOutbox: fn(await outboxGet()).slice(-200) }); }).catch(() => {}));
function bridgeSend(m) {
  const open = bws && bws.readyState === WebSocket.OPEN;
  if (m.t !== 'hb') outboxEdit((list) => [...list.filter((x) => !(x.id === m.id && x.t === m.t)), m]);
  if (open) bws.send(JSON.stringify(m)); else if (m.t !== 'hb') bridgeConnect();
}
// Пульс для вкладок QA pro: фоновая вкладка в Chrome засыпает (таймеры раз в минуту), а сообщения от расширения
// будят её — так фоновый исполнитель QA pro вовремя отмечается и подхватывает работу.
let lastTick = 0;
async function tickQaPro() {
  if (Date.now() - lastTick < 15000) return;
  lastTick = Date.now();
  const s = await getSettings();
  const patterns = [...new Set([...STATIC_MATCHES, ...customMatches(s.qaProOrigins), ...(s.anySite ? ['https://*/*'] : [])])].filter((p) => !p.startsWith('file:'));
  let tabs = [];
  try { tabs = await chrome.tabs.query({ url: patterns }); } catch { return; }
  for (const t of tabs) chrome.tabs.sendMessage(t.id, { type: 'QA_TICK' }).catch(() => {});
}
async function onBridgeMessage(m) {
  if (ctxOnCoreMessage(m)) return; // ответ ядра на вызов источника контекста
  if (m.t === 'hb') { bridgeSend({ t: 'hb' }); tickQaPro(); return; }
  if (m.t === 'ack' && m.id) { outboxEdit((list) => list.filter((x) => !(x.id === m.id && x.t === m.kind))); return; }
  if (m.t === 'job' && m.id && Array.isArray(m.cases)) {
    const key = 'bridge:' + m.id;
    if ((await chrome.storage.session.get(key))[key]) return; // уже открывали
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
    await chrome.storage.session.set({ [key]: id });
    await setJob(id, { via: 'bridge', remoteId: m.id, from: 'Приложение Claude', title: String(m.title || 'QA pro').slice(0, 200), cases: m.cases.slice(0, 2000), done: false });
    const windowId = await openUploadWindow(id);
    const job = await getJob(id);
    if (job) await setJob(id, { ...job, windowId });
    bridgeSend({ t: 'opened', id: m.id });
    return;
  }
  if (m.t === 'cancel' && m.id) {
    const key = 'bridge:' + m.id, local = (await chrome.storage.session.get(key))[key];
    const job = local ? await getJob(local) : null;
    if (job && !job.done) { await setJob(local, { ...job, done: true }); if (job.windowId) chrome.windows.remove(job.windowId).catch(() => {}); }
  }
}
chrome.alarms.create('qa-pro-bridge', { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener((a) => { if (a.name === 'qa-pro-bridge') { bridgeConnect(); tickQaPro(); } });
chrome.runtime.onStartup.addListener(() => { bridgeConnect(); });
bridgeConnect();

// Журнал обращений страниц QA pro — для диагностики в настройках загрузчика.
async function notePing(sender) {
  const { pings = [] } = await chrome.storage.session.get('pings');
  pings.unshift({ at: Date.now(), frame: String(sender.url || '').slice(0, 300), origin: sender.origin || '', tab: String(sender.tab?.url || '').slice(0, 300) });
  await chrome.storage.session.set({ pings: pings.slice(0, 8) });
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    try {
      if (String(msg?.type || '').startsWith('CTX_')) {
        // настройки и окно разрешения — страницы самого расширения; CTX_GRANTS и CTX_REVOKE страницам QA pro недоступны
        const own = !sender.tab || String(sender.url || '').startsWith(chrome.runtime.getURL(''));
        if (['CTX_DECIDE', 'CTX_ASK_INFO', 'CTX_GRANTS', 'CTX_REVOKE'].includes(msg.type) && !own) return sendResponse({ ok: false, error: 'Недоступно для страницы.' });
        const r = await ctxMessage(msg, sender);
        return sendResponse(r || { ok: false, error: 'Неизвестная команда' });
      }
      switch (msg?.type) {
        case 'PING': {
          notePing(sender).catch(() => {});
          const s = await getSettings();
          return sendResponse({ ok: true, version: chrome.runtime.getManifest().version, baseUrl: trimBase(s.baseUrl), bridge: !!bwsState.connected, bridgeVersion: bwsState.connected ? bwsState.version || '' : '', context: true });
        }
        case 'UPLOAD_REQUEST': {
          const cases = Array.isArray(msg.cases) ? msg.cases.slice(0, 2000) : [];
          if (!cases.length) return sendResponse({ ok: false, error: 'Нет тест-кейсов для загрузки.' });
          const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
          await setJob(id, { requestId: msg.requestId, tabId: sender.tab?.id, frameId: sender.frameId, from: sender.origin || sender.url || '', title: String(msg.title || '').slice(0, 200), cases, done: false });
          const windowId = await openUploadWindow(id);
          const job = await getJob(id);
          if (job) await setJob(id, { ...job, windowId });
          return sendResponse({ ok: true, jobId: id });
        }
        case 'GET_JOB': return sendResponse({ ok: true, job: msg.jobId ? await getJob(msg.jobId) : null });
        case 'STATUS': {
          const { base, token, settings } = await sfera();
          return sendResponse({ ok: true, baseUrl: base, loggedIn: !!token, lastSectionUrl: settings.lastSectionUrl });
        }
        case 'FIND_SFERA_TABS': {
          const { base } = await sfera();
          const tabs = await chrome.tabs.query({ url: base + '/*' });
          return sendResponse({ ok: true, tabs: tabs.filter((t) => /\/project\//.test(t.url || '')).map((t) => ({ url: t.url, title: t.title })) });
        }
        case 'GET_SECTIONS': return sendResponse({ ok: true, sections: await getSections(msg.projectCode) });
        case 'UPLOAD': {
          const job = msg.jobId ? await getJob(msg.jobId) : null;
          if (msg.sectionUrl) await saveSettings({ lastSectionUrl: msg.sectionUrl });
          const results = await uploadItems(msg.items || [], msg.meta, (partial) => {
            chrome.runtime.sendMessage({ type: 'PROGRESS', jobId: msg.jobId || null, results: partial }).catch(() => {});
          });
          if (job) { await notifyPage(job, { results, section: msg.meta }); await setJob(msg.jobId, { ...job, done: true }); }
          return sendResponse({ ok: true, results });
        }
        case 'SAVE_SETTINGS': {
          const s = await saveSettings(msg.patch || {});
          if ('qaProOrigins' in (msg.patch || {})) await syncQaProScripts(s.qaProOrigins);
          if ('anySite' in (msg.patch || {})) await syncAnySite(s.anySite);
          const injected = ('qaProOrigins' in (msg.patch || {}) || 'anySite' in (msg.patch || {})) ? await injectOpenTabs() : 0;
          if ('desktopBridge' in (msg.patch || {}) || 'bridgePort' in (msg.patch || {})) { try { bws?.close(); } catch { /* уже закрыт */ } bws = null; bridgeConnect(); }
          let tab = null;
          if ('keepQaPro' in (msg.patch || {}) || 'qaProUrl' in (msg.patch || {})) { try { tab = await ensureQaProTab(); } catch (e) { return sendResponse({ ok: false, error: e?.message || String(e) }); } }
          return sendResponse({ ok: true, settings: s, injected, tabOpened: !!tab });
        }
        case 'GET_SETTINGS': { const st = await getSettings(); return sendResponse({ ok: true, settings: { ...st, ghToken: st.ghToken ? '••••' : '' } }); }
        case 'GET_DIAG': {
          const { pings = [] } = await chrome.storage.session.get('pings');
          return sendResponse({ ok: true, version: chrome.runtime.getManifest().version, pings, settings: await getSettings(), bridge: bwsState });
        }
        case 'INJECT_NOW': return sendResponse({ ok: true, injected: await injectOpenTabs() });
        case 'BRIDGE_STATUS': { await bridgeConnect(); await new Promise((r) => setTimeout(r, 600)); return sendResponse({ ok: true, bridge: bwsState }); }
        default: return sendResponse({ ok: false, error: 'Неизвестная команда' });
      }
    } catch (e) {
      sendResponse({ ok: false, error: e?.message || String(e), code: e?.code || '' });
    }
  })();
  return true;
});
