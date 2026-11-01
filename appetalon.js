/* ================= сравнение черновика с эталонными тест-кейсами ================= */
/* Пользователь отмечает кейсы черновика (или берёт все) и загружает эталонные кейсы команды — в тех же форматах, что
   и документы. Агент по каждому виду тестов (API, UI, E2E) сравнивает сгенерированные кейсы с эталоном и предлагает
   правила генерации. Каждое правило пользователь добавляет или отклоняет; добавленное дописывается в правила
   оформления шаблона этого вида (шестерёнка → Шаблоны → «Особенности оформления») и сохраняется так же, как правка
   шаблона: для команды, в источник контекста или — без прав — только у этого пользователя. */
const ETALON_CAP = 200000;         // знаков эталона в одном запросе: эталон идёт целиком, длиннее — кейсы эталона по теме сравниваемых
const ETALON_CASES_CAP = 150000;   // знаков кейсов агента в одном запросе: больше — сравнение частями
const ETALON_MAX_RULES = 8;   // правил оформления на вид тестов; состав проверок — в метриках, не в правилах
const ETALON_KINDS = { format: 'Оформление', content: 'Состав проверок' };
S.etalon = { uids: [], files: [], busy: false, error: '', log: [], ctl: null, view: 'upload' };

const etalonScope = (run = S.run) => {
  if (!run) return [];
  const sel = run.cases.filter((c) => S.caseSel.has(c.uid));
  return sel.length ? sel : run.cases.slice();
};
const etalonCases = (run = S.run) => { const ids = new Set(S.etalon.uids); return (run?.cases || []).filter((c) => ids.has(c.uid)); };
const etalonTypes = (cases) => TYPES.filter((t) => cases.some((c) => c.type === t));
const etalonReady = () => S.etalon.files.filter((f) => f.status === 'ready');
const etalonPending = (run = S.run) => (run?.etalon?.rules || []).filter((x) => x.status === 'new').length;
const tplRuleLines = (t) => String(S.cfg.tpl[t]?.rules || '').split('\n').map((l) => l.replace(/^\s*[-*•]\s*/, '').trim()).filter(Boolean);

function openEtalon(view) {
  const r = S.run;
  if (!r || !r.cases.length) return;
  const E = S.etalon;
  if (view === 'result' && r.etalon) E.view = 'result';
  else { E.view = 'upload'; E.uids = etalonScope(r).map((c) => c.uid); E.error = ''; E.log = []; }
  renderEtalon();
  openDialog('etalon-ov');
}
function etalonAddFiles(list) {
  for (const f of [...(list || [])]) {
    const ext = (f.name.split('.').pop() || '').toLowerCase();
    const x = { id: rid('e'), name: f.name, ext, status: 'parsing', text: '', chars: 0, error: '' };
    S.etalon.files.push(x);
    etalonParse(f, ext).then((res) => { x.text = String(res.text || '').trim(); x.chars = x.text.length; x.cases = res.cases || 0; x.status = x.chars ? 'ready' : 'error'; if (!x.chars) x.error = 'В файле не найден текст'; })
      .catch((e) => { x.status = 'error'; x.error = e.message || String(e); })
      .finally(renderEtalon);
  }
  renderEtalon();
}
/* эталон .xlsx и .json — это тест-кейсы: разбираем их тем же разбором, что файл кейсов при актуализации, и пишем каждый
   кейс отдельным блоком. Как документ таблица стала бы сплошным текстом без границ кейсов */
function etalonCaseText(c) {
  const val = (v) => (typeof v === 'string' ? v : JSON.stringify(v));
  const lines = [`### ${c.srcId ? c.srcId + '. ' : ''}${c.title}`];
  for (const [k, v] of Object.entries(c.raw || {})) {
    if (v == null || v === '' || v === c.title || v === c.srcId) continue;
    if (k === 'Следующие строки кейса' && Array.isArray(v)) for (const row of v) lines.push('- ' + Object.entries(row).map(([a, b]) => `${a}: ${val(b)}`).join('; '));
    else lines.push(`${k}: ${val(v)}`);
  }
  return lines.join('\n');
}
async function etalonParse(f, ext) {
  if (['xlsx', 'xls', 'json'].includes(ext)) {
    try {
      const buf = await f.arrayBuffer();
      const r = ext === 'json' ? parseTestsJSON(decodeText(buf)) : await parseTestsSheet(buf);
      if (r.cases.length) return { text: r.cases.map(etalonCaseText).join('\n\n'), cases: r.cases.length };
    } catch { /* не тест-кейсы — читаем как документ */ }
  }
  let res = await parseFile(f);
  if (res.ocr) res = await res.ocr();   // эталон сравнивается целиком: скриншоты дожидаемся
  return res;
}
/* длинный эталон: блоки (кейсы, абзацы), ближе всего к теме сравниваемых кейсов, в исходном порядке. Блок без пустых строк
   (таблица) делится по строкам, а строка заголовков таблицы повторяется в каждой его части */
function etalonFit(text, focus, cap = ETALON_CAP) {
  const t = String(text || '');
  if (t.length <= cap) return { text: t, cut: false };
  const units = [];
  for (const para of t.split(/\n\s*\n/)) {
    if (para.length <= 1500) { units.push(para); continue; }
    const lines = para.split('\n'), head = lines.find((l) => l.startsWith('|')) || '';
    let cur = '';
    for (const l of lines) {
      if (cur && cur.length + l.length > 1500) { units.push(cur); cur = head && l !== head ? head : ''; }
      cur += (cur ? '\n' : '') + l.slice(0, 1500);
    }
    if (cur) units.push(cur);
  }
  const parts = [];
  let cur = '';
  for (const u of units) {
    if (cur && cur.length + u.length > 1500) { parts.push(cur); cur = ''; }
    cur += (cur ? '\n\n' : '') + u;
  }
  if (cur) parts.push(cur);
  const q = new Set(helpTokens(focus));
  const scored = parts.map((p, k) => ({ p, k, s: [...new Set(helpTokens(p))].reduce((a, w) => a + (q.has(w) ? 1 : 0), 0) }));
  const keep = new Set();
  let size = 0;
  for (const x of scored.slice().sort((a, b) => b.s - a.s || a.k - b.k)) { if (size + x.p.length + 2 > cap) continue; keep.add(x.k); size += x.p.length + 2; }
  return { text: scored.filter((x) => keep.has(x.k)).map((x) => x.p).join('\n\n…\n\n'), cut: true };
}
function promptEtalon(type, cases, etalonText, part = null) {
  const own = tplRuleLines(type), team = rulesText(), ls = S.lessons.filter((l) => l.scope !== 'review').map((l) => l.text);
  const rules = [own.length ? `Особенности оформления ${TL[type]}:\n${own.map((x) => '- ' + x).join('\n')}` : '', team ? `Правила для агента (все виды):\n${team}` : '', ls.length ? `Правила из замечаний команды:\n${ls.map((x) => '- ' + x).join('\n')}` : ''].filter(Boolean).join('\n\n') || 'Не заданы.';
  const payload = [];
  let size = 0;
  for (const c of cases) { const s = JSON.stringify({ id: c.dispId, testCase: c.testCase }); if (size + s.length > ETALON_CASES_CAP && payload.length) break; payload.push(s); size += s.length; }
  const focus = cases.map((c) => pickTitleText(c.testCase)).join(' ');
  const fit = etalonFit(etalonText, focus);
  return renderPrompt('promptEtalon', {
    type: TL[type], rules, shown: part ? ` (часть ${part.k} из ${part.n}: ${cases[0].dispId}–${cases[cases.length - 1].dispId})` : payload.length < cases.length ? ` (первые ${payload.length} из ${cases.length})` : '',
    cases: '[' + payload.join(',\n') + ']', etalonNote: fit.cut ? ' — фрагменты по теме этих кейсов (эталон длиннее лимита запроса)' : '', etalon: fit.text,
  });
}
function etalonNormRules(type, res, have) {
  const exist = new Set([...tplRuleLines(type), ...have].map(normKey));
  const out = [], per = { format: 0, content: 0 };
  for (const x of arrOf(res?.rules).slice(0, ETALON_MAX_RULES * 4)) {
    const text = String(x?.text || x?.rule || '').replace(/\s+/g, ' ').trim().slice(0, 300);
    const kind = String(x?.kind || '').toLowerCase() === 'content' ? 'content' : 'format';
    if (kind === 'content') continue;   // правила только об оформлении: состав проверок зависит от функции, а не от команды
    if (!text || exist.has(normKey(text)) || per[kind] >= ETALON_MAX_RULES) continue;
    exist.add(normKey(text)); per[kind]++;
    out.push({ id: rid('er'), type, kind, text, why: String(x?.why || '').trim().slice(0, 400), generated: arrStr(x?.generated).slice(0, 8), etalon: String(x?.etalon || '').trim().slice(0, 160), status: 'new' });
  }
  return out;
}
/* метрика по эталону: полнота — доля проверок эталона, которые есть у агента; лишние — кейсы агента без пары и малоценные */
function etalonMetrics(res, list) {
  const m = res?.metrics || {};
  const total = Math.max(0, Math.round(Number(m.etalonChecks) || 0));
  const matched = Math.min(total, Math.max(0, Math.round(Number(m.matched) || 0)));
  const ids = new Set(list.map((c) => c.dispId));
  return { total, matched, missed: arrStr(m.missed).slice(0, 10).map((x) => x.slice(0, 200)), extra: arrStr(m.extra).filter((id) => ids.has(id)).slice(0, 30) };
}
/* кейсы агента — частями по ETALON_CASES_CAP: модель видит все кейсы, а не первые, что поместились */
function etalonParts(list) {
  const parts = [];
  let cur = [], size = 0;
  for (const c of list) {
    const s = JSON.stringify({ id: c.dispId, testCase: c.testCase }).length;
    if (cur.length && size + s > ETALON_CASES_CAP) { parts.push(cur); cur = []; size = 0; }
    cur.push(c); size += s;
  }
  if (cur.length) parts.push(cur);
  return parts;
}
// метрики частей: проверки эталона во всех частях одни и те же — берём наибольшую оценку, совпавшие складываем (не больше всех)
function etalonMerge(ms) {
  if (ms.length === 1) return ms[0];
  const total = Math.max(0, ...ms.map((m) => m.total));
  return { total, matched: Math.min(total, ms.reduce((a, m) => a + m.matched, 0)), missed: [...new Set(ms.flatMap((m) => m.missed))].slice(0, 10), extra: ms.flatMap((m) => m.extra).slice(0, 30), approx: true };
}
function etalonTotals(R) {
  const ms = Object.values(R?.byType || {}).filter((x) => x.metrics);
  if (!ms.length) return null;
  const total = ms.reduce((a, x) => a + x.metrics.total, 0), matched = ms.reduce((a, x) => a + x.metrics.matched, 0);
  const n = ms.reduce((a, x) => a + x.n, 0), extra = ms.reduce((a, x) => a + x.metrics.extra.length, 0);
  return { total, matched, n, extra, recall: total ? Math.round((100 * matched) / total) : null };
}
// последняя метрика по эталону в продукте — в этом браузере: следующее сравнение покажет, стало ли лучше
const etalonKey = (r) => `qapro.etalonLast.${r?.productId || 'none'}`;
const etalonLine = (m, n) => `${m.total ? `Полнота: ${m.matched} из ${m.total} ${plural(m.total, 'проверки', 'проверок', 'проверок')} эталона (${Math.round((100 * m.matched) / m.total)}%)` : 'Эталон не по теме этих кейсов'} · лишних кейсов: ${m.extra.length} из ${n}`;
async function runEtalon() {
  const E = S.etalon, r = S.run;
  if (E.busy || !r) return;
  const cases = etalonCases(r);
  const files = etalonReady();
  if (!cases.length) { E.error = 'Не выбраны кейсы для сравнения.'; return renderEtalon(); }
  if (!files.length) { E.error = 'Загрузите файл с эталонными тест-кейсами.'; return renderEtalon(); }
  if (!aiReady(S.settings.genAI)) { E.error = aiProblem(S.settings.genAI); return renderEtalon(); }
  const text = files.map((f) => `### Файл «${f.name}»\n${f.text}`).join('\n\n');
  E.busy = true; E.error = ''; E.log = []; E.ctl = new AbortController();
  const types = etalonTypes(cases);
  const result = { at: Date.now(), files: files.map((f) => f.name), count: cases.length, byType: {}, rules: [], prev: etalonTotals(r.etalon) || lsGet(etalonKey(r), null) };
  renderEtalon();
  try {
    for (const t of types) {
      const list = cases.filter((c) => c.type === t), parts = etalonParts(list);
      const line = { text: `${TL[t]}: сравниваю ${list.length} ${plural(list.length, 'кейс', 'кейса', 'кейсов')} с эталоном${parts.length > 1 ? ` — частями: ${parts.length}` : ''}…` };
      E.log.push(line); renderEtalon();
      const got = [];
      for (const [k, part] of parts.entries()) {
        if (parts.length > 1) { line.text = `${TL[t]}: сравниваю часть ${k + 1} из ${parts.length}…`; renderEtalon(); }
        const res = await ask(promptEtalon(t, part, text, parts.length > 1 ? { k: k + 1, n: parts.length } : null), { step: 'etalon', ai: S.settings.genAI, cache: false, signal: E.ctl.signal });
        result.rules.push(...etalonNormRules(t, res, result.rules.map((x) => x.text)));
        got.push({ summary: String(res?.summary || '').trim(), metrics: etalonMetrics(res, part) });
      }
      const n = result.rules.filter((x) => x.type === t).length;
      result.byType[t] = { n: list.length, parts: parts.length, summary: got.map((x) => x.summary).filter(Boolean).join(' ').slice(0, 600), metrics: etalonMerge(got.map((x) => x.metrics)) };
      line.text = `${TL[t]}: ${n ? `предложено правил — ${n}` : 'новых правил нет'}`;
      renderEtalon();
    }
    r.etalon = result;
    if (etalonTotals(result)?.recall != null) lsSet(etalonKey(r), etalonTotals(result));   // для сравнения со следующим запуском
    queueSave(r);
    E.view = 'result';
    toast(result.rules.length ? `Сравнение с эталоном: предложено правил — ${result.rules.length}` : 'Сравнение с эталоном: новых правил нет');
  } catch (e) {
    E.error = e?.code === 'aborted' || e?.name === 'AbortError' ? 'Сравнение остановлено.' : 'Не удалось сравнить: ' + errText(e);
  } finally { E.busy = false; E.ctl = null; renderEtalon(); if (S.tab === 'draft') renderTab(); }
}
// «Добавить»: правило дописывается в правила оформления шаблона своего вида и сохраняется, как правка шаблона
async function etalonDecide(id, add) {
  const r = S.run, x = r?.etalon?.rules.find((y) => y.id === id);
  if (!x || x.status !== 'new') return;
  if (!add) { x.status = 'rejected'; queueSave(r); renderEtalon(); if (S.tab === 'draft') renderTab(); return; }
  const t = x.type, tp = S.cfg.tpl[t];
  if (!tplRuleLines(t).some((l) => normKey(l) === normKey(x.text))) {
    S.cfg.tpl[t] = { ...tp, rules: (String(tp.rules || '').trim() ? String(tp.rules).trim() + '\n' : '') + '- ' + x.text };
  }
  S.cfgDirty[t] = true;
  x.status = 'added'; x.addedAt = Date.now();
  queueSave(r);
  if (ctxOwnsCfg()) await ctxSaveCfg(t);
  else if (S.caps.db && S.caps.canEdit) await saveCfg(t);
  else { saveDrafts(); renderCfgTabs(); toast(`Правило добавлено в шаблон ${TL[t]} только у вас: сохранить для команды может владелец или редактор приложения.`); }
  renderEtalon(); if (S.tab === 'draft') renderTab();
}
function etalonSaveNote() {
  if (ctxOwnsCfg()) return `Добавленное правило записывается в шаблон своего вида в источнике контекста: ${esc(ctxFull('templates/<вид>.md'))}.`;
  if (S.caps.db && S.caps.canEdit) return 'Добавленное правило дописывается в «Особенности оформления» шаблона своего вида и сохраняется для команды.';
  return 'Добавленное правило дописывается в «Особенности оформления» шаблона своего вида только у вас: сохранить для команды может владелец или редактор приложения.';
}
const ETALON_FMT = '.docx,.pdf,.txt,.md,.markdown,.xlsx,.xls,.csv,.json,.yaml,.yml';
function etalonUploadHTML() {
  const E = S.etalon, cases = etalonCases();
  const types = etalonTypes(cases).map((t) => `${TL[t]} ${cases.filter((c) => c.type === t).length}`).join(' · ');
  const all = S.run && cases.length === S.run.cases.length;
  const st = { parsing: 'разбор…', ready: '', error: 'ошибка' };
  const files = E.files.length ? `<ul class="et-files">${E.files.map((f) => `<li class="${f.status}"><span class="et-fname">${esc(f.name)}</span><span class="muted small">${f.status === 'ready' ? (f.cases ? `${f.cases} ${plural(f.cases, 'кейс', 'кейса', 'кейсов')} · ` : '') + fmtKChars(f.chars) : st[f.status]}${f.error ? ' — ' + esc(f.error) : ''}</span><button class="icon-btn" type="button" data-eact="drop" data-id="${f.id}" aria-label="Убрать файл ${esc(f.name)}" ${E.busy ? 'disabled' : ''}>${ICON.x}</button></li>`).join('')}</ul>` : '';
  const ready = etalonReady().length > 0 && !E.files.some((f) => f.status === 'parsing');
  return `<p class="hint">Сравниваю ${all ? 'все' : 'выбранные'} ${cases.length} ${plural(cases.length, 'кейс', 'кейса', 'кейсов')} черновика (${esc(types)}) с эталонными тест-кейсами команды. По каждому виду тестов агент предложит правила генерации — добавьте нужные или отклоните.</p>
    <label class="drop et-drop" id="etalon-drop" for="etalon-file" tabindex="0" role="button" aria-label="Загрузить эталонные тест-кейсы">
      <input type="file" id="etalon-file" multiple accept="${ETALON_FMT}" hidden>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M12 17v-6"/><path d="m9 13 3-3 3 3"/></svg>
      <span class="drop-t">Эталонные кейсы — перетащите или <u>выберите</u></span>
      <span class="drop-f">DOCX · PDF · TXT · MD · XLSX · CSV · JSON / YAML</span>
    </label>
    ${files}
    ${E.error ? `<p class="case-note err">${esc(E.error)}</p>` : ''}
    ${E.busy ? `<div class="et-log">${E.log.map((l) => `<div class="small">${esc(l.text)}</div>`).join('')}</div>` : ''}
    <div class="row">${E.busy ? '<button class="btn" type="button" data-eact="stop">Остановить</button>' : `<button class="btn accent" type="button" data-eact="run" ${ready ? '' : 'disabled'}>Сравнить с эталоном</button>`}${S.run?.etalon && !E.busy ? `<button class="link" type="button" data-eact="result">Прошлый результат</button>` : ''}</div>`;
}
function etalonResultHTML() {
  const r = S.run, R = r?.etalon;
  if (!R) return '<p class="hint">Сравнения ещё не было.</p>';
  const groups = TYPES.filter((t) => R.byType[t]).map((t) => {
    const rules = R.rules.filter((x) => x.type === t);
    const item = (x) => `<li class="et-rule ${x.status}" id="et-${x.id}">
        <div class="et-rule-t">${esc(x.text)}</div>
        ${x.why || x.generated.length || x.etalon ? `<div class="muted small">${esc(x.why)}${x.generated.length ? ` · кейсы: ${esc(x.generated.join(', '))}` : ''}${x.etalon ? ` · эталон: ${esc(x.etalon)}` : ''}</div>` : ''}
        <div class="et-acts">${x.status === 'new' ? `<button class="btn sm accent" type="button" data-eact="add" data-id="${x.id}">Добавить</button><button class="btn sm" type="button" data-eact="reject" data-id="${x.id}">Отклонить</button>`
          : x.status === 'added' ? `<span class="chip ok">добавлено в правила ${TL[t]}</span>` : '<span class="chip">отклонено</span>'}</div></li>`;
    // правила прежних сравнений без рода — оформление
    const items = Object.entries(ETALON_KINDS).map(([k, title]) => { const xs = rules.filter((x) => (x.kind || 'format') === k); return xs.length ? `<h5 class="et-kind">${title} · ${xs.length}</h5><ul class="et-rules">${xs.map(item).join('')}</ul>` : ''; }).join('');
    const m = R.byType[t].metrics;
    const metric = m ? `<p class="small"><b>${esc(etalonLine(m, R.byType[t].n))}</b>${m.approx ? ` <span class="muted">· сравнение частями (${R.byType[t].parts}), полнота приблизительная</span>` : ''}${m.extra.length ? ` <span class="muted">(${esc(m.extra.join(', '))})</span>` : ''}</p>${m.missed.length ? `<details class="small"><summary>Нет у агента: ${m.missed.length}</summary><ul>${m.missed.map((x) => `<li>${esc(x)}</li>`).join('')}</ul></details>` : ''}` : '';
    return `<section class="et-group"><h4>${TL[t]} · ${R.byType[t].n} ${plural(R.byType[t].n, 'кейс', 'кейса', 'кейсов')}</h4>
      ${metric}
      ${R.byType[t].summary ? `<p class="hint">${esc(R.byType[t].summary)}</p>` : ''}
      ${items || '<p class="hint">Новых правил нет.</p>'}</section>`;
  }).join('');
  const tot = etalonTotals(R), prev = R.prev;
  const delta = tot?.recall != null && prev?.recall != null ? ` (в прошлый раз ${prev.recall}%)` : '';
  const head = tot && tot.recall != null ? `<p class="et-metric"><b>Полнота по эталону: ${tot.recall}%</b>${esc(delta)} · найдено ${tot.matched} из ${tot.total} ${plural(tot.total, 'проверки', 'проверок', 'проверок')} эталона · лишних кейсов: ${tot.extra} из ${tot.n}</p>` : '';
  return `<p class="hint">Сравнение ${fmtDate(R.at)} · ${R.count} ${plural(R.count, 'кейс', 'кейса', 'кейсов')} · эталон: ${esc(R.files.join(', '))}. ${etalonSaveNote()}</p>
    ${head}
    ${groups}
    <div class="row"><button class="btn" type="button" data-eact="again">Новое сравнение</button></div>`;
}
function renderEtalon() {
  const b = $('#etalon-body');
  if (!b) return;
  b.innerHTML = S.etalon.view === 'result' && S.run?.etalon ? etalonResultHTML() : etalonUploadHTML();
}
function bindEtalon() {
  const b = $('#etalon-body');
  if (!b || b.dataset.bound) return;
  b.dataset.bound = '1';
  b.addEventListener('change', (e) => { if (e.target.id === 'etalon-file') { etalonAddFiles(e.target.files); e.target.value = ''; } });
  b.addEventListener('dragover', (e) => { if (e.target.closest('#etalon-drop')) { e.preventDefault(); e.target.closest('#etalon-drop').classList.add('over'); } });
  b.addEventListener('dragleave', (e) => { e.target.closest?.('#etalon-drop')?.classList.remove('over'); });
  b.addEventListener('drop', (e) => { const d = e.target.closest('#etalon-drop'); if (!d) return; e.preventDefault(); d.classList.remove('over'); etalonAddFiles(e.dataTransfer?.files); });
  b.addEventListener('click', (e) => {
    const el = e.target.closest('[data-eact]');
    if (!el || el.disabled) return;
    const a = el.dataset.eact, E = S.etalon;
    if (a === 'run') runEtalon();
    else if (a === 'stop') E.ctl?.abort();
    else if (a === 'drop') { E.files = E.files.filter((f) => f.id !== el.dataset.id); renderEtalon(); }
    else if (a === 'add' || a === 'reject') etalonDecide(el.dataset.id, a === 'add');
    else if (a === 'again') { E.view = 'upload'; E.uids = etalonScope().map((c) => c.uid); E.error = ''; E.log = []; renderEtalon(); }
    else if (a === 'result') { E.view = 'result'; renderEtalon(); }
  });
}
