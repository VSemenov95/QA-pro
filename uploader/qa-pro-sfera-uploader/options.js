const $ = (s) => document.querySelector(s);
const send = (msg) => new Promise((resolve) => chrome.runtime.sendMessage(msg, (r) => resolve(r || { ok: false, error: chrome.runtime.lastError?.message })));
const originOf = (u) => { try { const x = new URL(String(u).trim()); return /^https?:$/.test(x.protocol) ? x.origin : ''; } catch { return ''; } };

send({ type: 'GET_SETTINGS' }).then((r) => {
  const s = r.settings || {};
  $('#base').value = s.baseUrl || 'https://sfera-t1.ru';
  $('#origins').value = (s.qaProOrigins || []).join('\n');
});

$('#save').addEventListener('click', async () => {
  const note = $('#note');
  const base = originOf($('#base').value);
  if (!base) { note.textContent = 'Укажите адрес Сферы вида https://sfera.company.ru'; return; }
  const origins = [...new Set($('#origins').value.split('\n').map(originOf).filter(Boolean))];
  const need = [base, ...origins].filter((o) => o !== 'https://sfera-t1.ru').map((o) => o + '/*');
  if (need.length) {
    const granted = await chrome.permissions.request({ origins: need }).catch(() => false);
    if (!granted) { note.textContent = 'Без разрешения браузера загрузчик не сможет работать с этими адресами.'; return; }
  }
  const r = await send({ type: 'SAVE_SETTINGS', patch: { baseUrl: base, qaProOrigins: origins } });
  note.textContent = r.ok ? 'Сохранено.' : 'Не сохранилось: ' + (r.error || '');
});

// ---------- диагностика ----------
const esc = (t) => String(t ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
async function renderDiag() {
  const r = await send({ type: 'GET_DIAG' });
  if (!r.ok) { $('#pings').textContent = 'Не удалось получить данные: ' + (r.error || ''); return; }
  $('#any').checked = !!r.settings.anySite;
  $('#pings').innerHTML = r.pings.length
    ? '<ol class="pings">' + r.pings.map((p) => `<li>${new Date(p.at).toLocaleTimeString()} · ${esc(p.frame || p.origin || '?')}${p.tab && p.tab !== p.frame ? ' · вкладка ' + esc(p.tab) : ''}</li>`).join('') + '</ol>'
    : 'С момента запуска браузера QA pro к загрузчику не обращался. Нажмите в QA pro «Проверить подключение» (шестерёнка → ТМС) и обновите эту страницу: если список останется пустым — загрузчик не видит страницу QA pro.';
}
renderDiag();
$('#any').addEventListener('change', async (e) => {
  const on = e.target.checked, note = $('#inject-note');
  if (on) {
    const granted = await chrome.permissions.request({ origins: ['https://*/*'] }).catch(() => false);
    if (!granted) { e.target.checked = false; note.textContent = 'Браузер не дал разрешение — режим не включён.'; return; }
  }
  const r = await send({ type: 'SAVE_SETTINGS', patch: { anySite: on } });
  note.textContent = r.ok ? (on ? `Включено. Подключено к открытым вкладкам: ${r.injected}.` : 'Выключено.') : 'Не сохранилось: ' + (r.error || '');
});
$('#inject').addEventListener('click', async () => {
  const r = await send({ type: 'INJECT_NOW' });
  $('#inject-note').textContent = r.ok ? `Подключено к вкладкам: ${r.injected}. Теперь нажмите в QA pro «Проверить подключение».` : 'Не получилось: ' + (r.error || '');
});

// ---------- вкладка QA pro для заданий из приложения Claude ----------
send({ type: 'GET_SETTINGS' }).then((r) => {
  const s = r.settings || {};
  $('#keep').checked = !!s.keepQaPro;
  $('#qa-url').value = s.qaProUrl || '';
});
async function saveKeep() {
  const note = $('#keep-note'), url = $('#qa-url').value.trim();
  let u = null; try { u = new URL(url); } catch { /* ниже */ }
  if ($('#keep').checked && (!u || u.protocol !== 'https:')) { note.textContent = 'Укажите ссылку на QA pro вида https://claude.ai/artifact/…'; return; }
  if (u && u.origin !== 'https://claude.ai') {
    const granted = await chrome.permissions.request({ origins: [u.origin + '/*'] }).catch(() => false);
    if (!granted) { note.textContent = 'Без разрешения браузера загрузчик не найдёт эту вкладку.'; return; }
  }
  const r = await send({ type: 'SAVE_SETTINGS', patch: { keepQaPro: $('#keep').checked, qaProUrl: url } });
  note.textContent = !r.ok ? 'Не получилось: ' + (r.error || '') : $('#keep').checked ? 'Включено: вкладка QA pro открыта и закреплена.' : 'Выключено.';
}
$('#keep').addEventListener('change', saveKeep);
$('#qa-url').addEventListener('change', saveKeep);

// ---------- локальный мост приложения Claude ----------
function renderBridge(b, s) {
  const el = $('#bridge-state');
  if (!s?.desktopBridge) { el.className = 'banner'; el.textContent = 'Связь с приложением Claude выключена.'; return; }
  if (b?.connected) { el.className = 'banner ok'; el.textContent = 'Мост подключён: задания из QA pro в приложении Claude откроют окно загрузчика здесь.'; return; }
  el.className = 'banner warn';
  el.textContent = 'Мост не найден. Установите его в приложении Claude (QA pro → шестерёнка → ТМС → «Скачать мост») и держите приложение запущенным. Загрузчик подключается сам раз в 30 секунд.';
}
async function loadBridge(check) {
  const st = await send({ type: 'GET_SETTINGS' });
  const s = st.settings || {};
  $('#bridge-on').checked = s.desktopBridge !== false;
  $('#bridge-port').value = s.bridgePort || 47321;
  const r = await send({ type: check ? 'BRIDGE_STATUS' : 'GET_DIAG' });
  renderBridge(r.bridge, s);
}
loadBridge(true);
async function saveBridge() {
  const port = Number($('#bridge-port').value);
  if (!(port >= 1024 && port <= 65535)) { $('#keep-note').textContent = 'Порт — число от 1024 до 65535.'; return; }
  await send({ type: 'SAVE_SETTINGS', patch: { desktopBridge: $('#bridge-on').checked, bridgePort: port } });
  $('#keep-note').textContent = 'Сохранено.';
  setTimeout(() => loadBridge(true), 400);
}
$('#bridge-on').addEventListener('change', saveBridge);
$('#bridge-port').addEventListener('change', saveBridge);
$('#bridge-check').addEventListener('click', () => { $('#bridge-state').textContent = 'Проверяю мост…'; loadBridge(true); });
