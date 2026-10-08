// Окно загрузки: показывает кейсы, даёт выбрать раздел Сферы ФТ и загружает после подтверждения.
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const send = (msg) => new Promise((resolve) => {
  chrome.runtime.sendMessage(msg, (r) => resolve(r || { ok: false, error: chrome.runtime.lastError?.message || 'Расширение не ответило.' }));
});
const PRIO_RU = { P1_LOW: 'Низкий', P2_MEDIUM: 'Средний', P3_HIGH: 'Высокий', P4_CRITICAL: 'Критический' };
const jobId = new URLSearchParams(location.search).get('job');
const st = { cases: [], picked: new Set(), results: new Map(), busy: false, meta: { projectCode: '', sectionId: '' }, sections: [], loggedIn: false };

const suitesOf = (tc) => {
  const s = (Array.isArray(tc.suites) ? tc.suites : []).map((x) => String(x).toLowerCase());
  return { smoke: s.some((x) => /smoke|смоук/.test(x)), regress: tc.ti_regressive === true || s.some((x) => /regress|регресс/.test(x)) };
};
function parseSectionUrl(u) {
  try {
    const url = new URL(String(u).trim());
    const parts = url.pathname.split('/').filter(Boolean);
    const i = parts.indexOf('project');
    if (i < 0 || !parts[i + 1]) return null;
    return { projectCode: decodeURIComponent(parts[i + 1]), sectionId: url.searchParams.get('section') || '' };
  } catch { return null; }
}

function renderRows() {
  const tb = $('#rows');
  $('#count').textContent = st.cases.length ? `· ${st.cases.length}` : '';
  if (!st.cases.length) { tb.innerHTML = '<tr><td colspan="5" class="hint">Тест-кейсов пока нет.</td></tr>'; renderGo(); return; }
  tb.innerHTML = st.cases.map((c, i) => {
    const s = suitesOf(c), r = st.results.get(i);
    const tags = `${s.smoke ? '<span class="tag smoke">SMOKE</span> ' : ''}${s.regress ? '<span class="tag reg">РЕГРЕССИОННЫЙ</span>' : ''}`;
    const res = !r ? '' : r.ok ? `<span class="res-ok">✓ ${esc(r.code || 'создан')}</span>` : `<span class="res-bad" title="${esc(r.error || '')}">✗ ${r.status ? 'HTTP ' + r.status : 'ошибка'}</span>`;
    return `<tr><td class="c"><input type="checkbox" data-i="${i}" ${st.picked.has(i) ? 'checked' : ''} ${st.busy ? 'disabled' : ''} aria-label="Загрузить «${esc(c.name)}»"></td>
      <td>${esc(c.name || 'Без названия')}<div class="hint">${c.qaId ? esc(c.qaId) + ' · ' : ''}шагов: ${(c.steps || []).length}</div></td>
      <td>${esc(PRIO_RU[c.priority] || c.priority || 'Средний')}</td><td>${tags || '<span class="hint">—</span>'}</td><td>${res}</td></tr>`;
  }).join('');
  $('#all').checked = st.picked.size === st.cases.length;
  renderGo();
}
function renderGo() {
  const n = st.picked.size, m = st.meta, go = $('#go'), note = $('#go-note');
  const why = !st.loggedIn ? 'Войдите в Сферу ФТ в этом браузере.' : !st.cases.length ? 'Нет тест-кейсов.' : !n ? 'Отметьте тест-кейсы.' : !m.projectCode || !m.sectionId ? 'Укажите проект и раздел.' : '';
  go.disabled = st.busy || !!why;
  go.textContent = st.busy ? 'Загружаю…' : `Загрузить ${n || ''}`.trim();
  note.textContent = st.busy ? '' : why || `в проект ${m.projectCode}, раздел ${sectionName(m.sectionId)}`;
}
const sectionName = (id) => st.sections.find((s) => String(s.id) === String(id))?.name || '#' + id;

function sectionOptions() {
  const byParent = new Map();
  for (const s of st.sections) { const k = s.parentSectionId ?? 'root'; if (!byParent.has(k)) byParent.set(k, []); byParent.get(k).push(s); }
  const ids = new Set(st.sections.map((s) => s.id));
  const roots = st.sections.filter((s) => s.parentSectionId == null || !ids.has(s.parentSectionId));
  const out = [];
  const walk = (list, depth) => { for (const s of list) { out.push(`<option value="${esc(s.id)}">${'  '.repeat(depth)}${depth ? '└ ' : ''}${esc(s.name)}</option>`); walk(byParent.get(s.id) || [], depth + 1); } };
  walk(roots, 0);
  return out.join('');
}
async function loadSections() {
  const sel = $('#sect'), code = st.meta.projectCode;
  if (!code) { sel.innerHTML = '<option value="">— укажите ссылку или проект —</option>'; renderGo(); return; }
  sel.innerHTML = '<option value="">Загружаю разделы…</option>';
  const r = await send({ type: 'GET_SECTIONS', projectCode: code });
  st.sections = r.ok ? r.sections : [];
  if (!r.ok) sel.innerHTML = `<option value="${esc(st.meta.sectionId)}">${st.meta.sectionId ? 'Раздел #' + esc(st.meta.sectionId) : '— разделы не загрузились —'}</option>`;
  else sel.innerHTML = '<option value="">— выберите раздел —</option>' + sectionOptions();
  sel.value = String(st.meta.sectionId || '');
  if (!r.ok) $('#tabs-note').textContent = r.error;
  renderGo();
}
function applyUrl(u, load = true) {
  const p = parseSectionUrl(u);
  if (!p) return false;
  const projChanged = p.projectCode !== st.meta.projectCode;
  st.meta = { projectCode: p.projectCode, sectionId: p.sectionId };
  $('#proj').value = p.projectCode;
  if (load && projChanged) loadSections(); else { $('#sect').value = String(p.sectionId || ''); renderGo(); }
  return true;
}
function sectionUrl() {
  const raw = $('#sect-url').value.trim();
  try { const u = new URL(raw); if (st.meta.sectionId) u.searchParams.set('section', st.meta.sectionId); return u.toString(); } catch { return ''; }
}

function setCases(list, sourceText) {
  st.cases = list.filter((c) => c && typeof c === 'object' && String(c.name || '').trim());
  st.picked = new Set(st.cases.map((_, i) => i));
  st.results.clear();
  $('#source').textContent = sourceText;
  renderRows();
}
function parseInput(text) {
  const j = JSON.parse(text);
  const list = Array.isArray(j) ? j : Array.isArray(j?.cases) ? j.cases : null;
  if (!list) throw new Error('Ожидается массив тест-кейсов или объект с полем cases.');
  return list;
}

async function upload(onlyFailed) {
  const idx = onlyFailed ? [...st.results.entries()].filter(([, r]) => !r.ok).map(([i]) => i) : [...st.picked].sort((a, b) => a - b);
  if (!idx.length) return;
  st.busy = true; renderRows();
  $('#summary').hidden = true;
  const items = idx.map((i) => st.cases[i]);
  const onProgress = (m) => { if (m?.type === 'PROGRESS' && (m.jobId || null) === (jobId || null)) { m.results.forEach((r, k) => st.results.set(idx[k], r)); renderRows(); } };
  chrome.runtime.onMessage.addListener(onProgress);
  const r = await send({ type: 'UPLOAD', jobId, items, meta: st.meta, sectionUrl: sectionUrl() });
  chrome.runtime.onMessage.removeListener(onProgress);
  st.busy = false;
  if (r.ok) r.results.forEach((x, k) => st.results.set(idx[k], x));
  renderRows();
  const ok = r.ok ? r.results.filter((x) => x.ok).length : 0, bad = r.ok ? r.results.length - ok : 0;
  const sm = $('#summary');
  sm.hidden = false;
  sm.className = 'banner ' + (!r.ok ? 'bad' : bad ? 'warn' : 'ok');
  sm.innerHTML = !r.ok ? esc(r.error)
    : `Создано в Сфере ФТ: <b>${ok}</b> из ${r.results.length}.${bad ? ` С ошибкой: ${bad} — наведите на ✗, чтобы увидеть причину. <button class="link" type="button" id="retry">Повторить для ошибок</button>` : ''}${jobId ? ' Результат отправлен в QA pro.' : ''} <button class="link" type="button" id="close">Закрыть окно</button>`;
}

async function init() {
  const s = await send({ type: 'STATUS' });
  st.loggedIn = !!s.loggedIn;
  const pill = $('#login');
  pill.className = 'pill ' + (s.loggedIn ? 'ok' : 'bad');
  pill.innerHTML = `<i></i>${s.loggedIn ? 'Вход в Сферу найден' : 'Нет входа в Сферу'}`;
  if (!s.loggedIn) { const w = $('#login-warn'); w.hidden = false; w.innerHTML = `Откройте <b>${esc(s.baseUrl || 'Сферу ФТ')}</b> в этом браузере и войдите — загрузчик работает от вашего имени. Адрес Сферы меняется в <button class="link" type="button" id="opts">настройках расширения</button>.`; }
  if (jobId) {
    const r = await send({ type: 'GET_JOB', jobId });
    if (!r.job) setCases([], 'Задание устарело — отправьте кейсы из QA pro ещё раз.');
    else setCases(r.job.cases, `Из QA pro${r.job.title ? ' · ' + r.job.title : ''}`);
  } else {
    $('#manual').hidden = false;
    setCases([], 'Откройте файл, выгруженный из QA pro');
  }
  if (s.lastSectionUrl) { $('#sect-url').value = s.lastSectionUrl; applyUrl(s.lastSectionUrl); }
  else renderGo();
}

document.addEventListener('change', async (e) => {
  const t = e.target;
  if (t.dataset.i) { const i = Number(t.dataset.i); t.checked ? st.picked.add(i) : st.picked.delete(i); renderRows(); }
  else if (t.id === 'all') { st.picked = t.checked ? new Set(st.cases.map((_, i) => i)) : new Set(); renderRows(); }
  else if (t.id === 'sect') { st.meta.sectionId = t.value; renderGo(); }
  else if (t.id === 'proj') { st.meta = { projectCode: t.value.trim(), sectionId: '' }; loadSections(); }
  else if (t.id === 'sect-url') { if (!applyUrl(t.value)) $('#tabs-note').textContent = 'В ссылке не нашёл /project/<код>?section=<id>.'; else $('#tabs-note').textContent = ''; }
  else if (t.id === 'file' && t.files?.[0]) {
    const f = t.files[0];
    try { setCases(parseInput(await f.text()), `Из файла ${f.name}`); $('#file-name').textContent = f.name; }
    catch (err) { $('#file-name').textContent = 'Не удалось прочитать: ' + err.message; }
    t.value = '';
  }
});
document.addEventListener('click', async (e) => {
  const b = e.target.closest('button');
  if (!b) return;
  if (b.id === 'go') upload(false);
  else if (b.id === 'retry') upload(true);
  else if (b.id === 'close') window.close();
  else if (b.id === 'opts') chrome.runtime.openOptionsPage();
  else if (b.id === 'paste-apply') {
    try { setCases(parseInput($('#paste').value), 'Из вставленного JSON'); } catch (err) { $('#file-name').textContent = 'Не удалось разобрать: ' + err.message; }
  } else if (b.id === 'from-tab') {
    const r = await send({ type: 'FIND_SFERA_TABS' });
    const tabs = r.ok ? r.tabs : [];
    const note = $('#tabs-note');
    if (!tabs.length) { note.textContent = 'Не нашёл открытой вкладки Сферы ФТ с разделом проекта.'; return; }
    if (tabs.length === 1) { $('#sect-url').value = tabs[0].url; applyUrl(tabs[0].url); note.textContent = tabs[0].title || ''; return; }
    note.innerHTML = 'Открыто несколько: ' + tabs.map((t, i) => `<button class="link" type="button" data-tab-url="${i}">${esc(t.title || t.url)}</button>`).join(' · ');
    note.onclick = (ev) => { const x = ev.target.closest('[data-tab-url]'); if (!x) return; const t = tabs[Number(x.dataset.tabUrl)]; $('#sect-url').value = t.url; applyUrl(t.url); note.textContent = t.title || ''; };
  }
});
init();
