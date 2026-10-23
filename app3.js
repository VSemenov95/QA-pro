/* ================= rendering helpers ================= */
const LABELS = {
  preconditions: 'Предусловия', steps: 'Шаги', expectedResult: 'Ожидаемый результат', expected: 'Ожидаемый результат',
  testData: 'Тестовые данные', priority: 'Приоритет', tags: 'Теги', request: 'Запрос', response: 'Ответ',
  postconditions: 'Постусловия', scenario: 'Сценарий', notes: 'Примечания', description: 'Описание', action: 'Действие',
  step: '№', system: 'Система', severity: 'Серьёзность', type: 'Тип', component: 'Компонент', module: 'Модуль',
  feature: 'Функция', automation: 'Автоматизация', status: 'Статус', owner: 'Владелец', links: 'Ссылки',
  requirements: 'Требования', endpoint: 'Эндпоинт', method: 'Метод', headers: 'Заголовки', body: 'Тело',
  data: 'Данные', result: 'Результат', environment: 'Окружение', title: 'Название', name: 'Название',
};
const label = (k) => LABELS[k] || k;
const TITLE_KEYS = ['title', 'name', 'summary', 'название', 'Название', 'caseName', 'testName', 'Title', 'Name'];
function pickTitle(tc) {
  for (const k of TITLE_KEYS) if (typeof tc?.[k] === 'string' && tc[k].trim()) return { key: k, text: tc[k] };
  const v = Object.entries(tc || {}).find(([k, x]) => typeof x === 'string' && x.length > 8 && !ID_KEYS.includes(k));
  return v ? { key: v[0], text: v[1] } : { key: null, text: 'Без названия' };
}
function pickTitleText(tc) { return pickTitle(tc).text; }
const prioOf = (tc) => tc?.priority ?? tc?.Priority ?? tc?.['приоритет'] ?? tc?.['Приоритет'] ?? null;
const prioClass = (p) => ({ P4_CRITICAL: 'p-critical', P3_HIGH: 'p-high', P2_MEDIUM: 'p-medium', P1_LOW: 'p-low' })[normPrio(p)];
/* Показ текста кейса: сообщения Kafka, SQL, тела запроса и ответа API — блоком кода, без кавычек. Меняется только вид на экране. */
function richText(s) {
  if (!/[{\[`]|SELECT|INSERT|UPDATE|DELETE|MERGE/i.test(s)) return esc(s).replace(/\n/g, '<br>');
  return codeParts(s, true).map((p) => (p.code ? `<pre class="inl-code">${esc(p.text)}</pre>` : esc(p.text.replace(/^\n+|\n+$/g, '')).replace(/\n/g, '<br>'))).filter(Boolean).join('');
}
function rv(v, depth = 0) {
  if (v === null || v === undefined || v === '') return '<span class="muted">—</span>';
  if (typeof v === 'boolean') return v ? 'да' : 'нет';
  if (typeof v === 'number') return `<span class="num">${v}</span>`;
  if (typeof v === 'string') return richText(v);
  if (Array.isArray(v)) {
    if (!v.length) return '<span class="muted">—</span>';
    const objs = v.every((x) => x && typeof x === 'object' && !Array.isArray(x));
    if (objs) {
      const keys = [...new Set(v.flatMap((x) => Object.keys(x)))];
      const flat = v.every((x) => Object.values(x).every((y) => y === null || typeof y !== 'object'));
      if (flat && keys.length <= 6) {
        return `<div class="tbl-wrap"><table class="steps-t"><thead><tr>${keys.map((k) => `<th>${esc(label(k))}</th>`).join('')}</tr></thead><tbody>${v.map((x) => `<tr>${keys.map((k) => `<td>${rv(x[k], depth + 1)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
      }
      return `<ol>${v.map((x) => `<li>${kvHTML(x, depth + 1)}</li>`).join('')}</ol>`;
    }
    if (v.every((x) => x === null || typeof x !== 'object')) return `<ul>${v.map((x) => `<li>${rv(x, depth + 1)}</li>`).join('')}</ul>`;
    return `<pre class="inl-code">${esc(JSON.stringify(v, null, 2))}</pre>`;
  }
  if (depth >= 1) return `<pre class="inl-code">${esc(JSON.stringify(v, null, 2))}</pre>`;
  return kvHTML(v, depth + 1);
}
function kvHTML(o, depth, skip = []) {
  return `<dl class="kv">${Object.entries(o).filter(([k]) => !skip.includes(k)).map(([k, x]) => `<dt>${esc(label(k))}</dt><dd>${rv(x, depth)}</dd>`).join('')}</dl>`;
}
function hlJSON(json) {
  const re = /("(?:\\.|[^"\\])*")(\s*:)?|(-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b)|\b(true|false|null)\b/g;
  let out = '', last = 0, m;
  while ((m = re.exec(json))) {
    out += esc(json.slice(last, m.index));
    if (m[1]) out += m[2] ? `<span class="k">${esc(m[1])}</span>${m[2]}` : `<span class="s">${esc(m[1])}</span>`;
    else out += `<span class="n">${esc(m[0])}</span>`;
    last = re.lastIndex;
  }
  return out + esc(json.slice(last));
}
const emptyHTML = (title, text = '', extra = '') => `<div class="empty"><b>${esc(title)}</b>${text ? `<span>${esc(text)}</span>` : ''}${extra}</div>`;
const fmtTok = (n) => (n >= 1000 ? `${(n / 1000).toLocaleString('ru-RU', { maximumFractionDigits: n >= 100000 ? 0 : 1 })} тыс.` : String(Math.round(n)));
const stat = (k, v, sub = '', id = '') => `<div class="stat"><span>${esc(k)}</span><b class="num"${id ? ` id="${id}"` : ''}>${esc(v)}</b>${sub ? `<small>${esc(sub)}</small>` : '<small>&nbsp;</small>'}</div>`;
const suiteChips = (suites) => (suites || []).map((s) => `<span class="chip ${s === 'smoke' ? 'smoke' : 'reg'}">${SUITE_RU[s]}</span>`).join('');
const suiteToggles = (suites, act, attrs) => SUITES.map((s) => `<button type="button" class="suite-btn ${s === 'smoke' ? 'smoke' : 'reg'}" aria-pressed="${(suites || []).includes(s)}" data-act="${act}" data-s="${s}" ${attrs} title="${(suites || []).includes(s) ? 'Убрать из набора' : 'Добавить в набор'} «${SUITE_RU[s]}»">${SUITE_RU[s]}</button>`).join('');
function caseUI(uid) {
  if (!S.caseUI.has(uid)) S.caseUI.set(uid, { open: false, mode: 'view', draft: '', comment: '', busy: false, error: '', note: '', prev: null, ctl: null });
  return S.caseUI.get(uid);
}
const anyEditing = () => [...S.caseUI.values()].some((u) => u.mode !== 'view' || u.busy);
const ICON = {
  play: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l10.5-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5z"/></svg>',
  x: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M4 4l8 8M12 4l-8 8"/></svg>',
  eye: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M1.5 8S4 3.5 8 3.5 14.5 8 14.5 8 12 12.5 8 12.5 1.5 8 1.5 8z"/><circle cx="8" cy="8" r="2"/></svg>',
  gear: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/></svg>',
  chat: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"><path d="M2.5 3.5h11v7h-6l-3 2.5v-2.5h-2z"/></svg>',
  pen: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"><path d="M10.5 2.5l3 3L6 13H3v-3z"/></svg>',
  chev: '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6l4 4 4-4"/></svg>',
  sun: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true"><circle cx="8" cy="8" r="3"/><path d="M8 1.5V3M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1"/></svg>',
  moon: '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M13.5 9.6A5.6 5.6 0 0 1 6.4 2.5a5.6 5.6 0 1 0 7.1 7.1z"/></svg>',
};
/* тема: светлая, тёмная или как в системе; выбор запоминается в этом браузере */
const THEME_KEY = 'qapro.theme';
const mqDark = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
const effTheme = () => { const t = document.documentElement.dataset.theme; return t === 'dark' || t === 'light' ? t : (mqDark?.matches ? 'dark' : 'light'); };
function renderThemeBtn() {
  const b = $('#btn-theme');
  if (!b) return;
  const dark = effTheme() === 'dark', label = dark ? 'Светлая тема' : 'Тёмная тема';
  b.innerHTML = dark ? ICON.sun : ICON.moon;
  b.setAttribute('aria-label', label); b.title = label;
}
function initTheme() {
  const t = lsGet(THEME_KEY, '');
  if (t === 'dark' || t === 'light') document.documentElement.dataset.theme = t;
  renderThemeBtn();
  mqDark?.addEventListener?.('change', renderThemeBtn);
  if (window.MutationObserver) new MutationObserver(renderThemeBtn).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  $('#btn-theme')?.addEventListener('click', () => {
    const next = effTheme() === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    lsSet(THEME_KEY, next);
  });
}
const isTyping = (root) => { const a = document.activeElement; return !!(a && root?.contains(a) && /TEXTAREA|INPUT|SELECT/.test(a.tagName)); };

/* ================= top + rail ================= */
function renderStatus() {
  const el = $('#st-claude');
  if (!S.caps.ready && !S.caps.sample) { el.className = 'pill wait'; el.innerHTML = '<i></i>Claude: проверка…'; }
  else if (S.caps.sample) { el.className = 'pill ok'; el.innerHTML = `<i></i>Claude подключён${S.caps.tools ? ' · агентный режим' : ''}`; }
  else { el.className = 'pill bad'; el.innerHTML = '<i></i>Claude недоступен'; }
  const st = $('#st-store');
  if (!inClaude) {
    el.className = 'pill'; el.innerHTML = `<i></i>Автономная версия · ${esc(aiLabel(S.settings.genAI))}`;
    st.hidden = false; st.className = 'pill ok'; st.innerHTML = '<i></i>Продукты и данные — в этом браузере';
    return;
  }
  if (S.caps.ready) {
    st.hidden = false;
    const ok = S.caps.db && S.caps.uid;
    st.className = 'pill ' + (ok ? 'ok' : 'bad');
    st.innerHTML = ok ? '<i></i>Продукты общие для команды' : '<i></i>Хранилище недоступно';
  }
}
let prodSelSig = '';
function renderProdSelect() {
  const box = $('#prod-switch'), sel = $('#prod-select');
  if (!box) return;
  const on = !!(S.caps.db && S.caps.uid && S.products.length && S.productId);
  if (on) {
    const p = curProduct(), name = String(p?.name || 'Продукт').trim();
    const words = name.split(/[\s\-—_.]+/).filter((w) => /[\p{L}\p{N}]/u.test(w));
    const ini = (words.length > 1 ? words[0][0] + words[1][0] : (words[0] || 'П').slice(0, 2)).toUpperCase();
    const nd = S.docs.length, nc = S.prodIndex?.pid === S.productId ? S.prodIndex.cases.length : 0;
    const av = $('#ps-av'), sub = $('#ps-sub');
    if (av && av.textContent !== ini) av.textContent = ini;
    const subT = `${nd} ${plural(nd, 'документ', 'документа', 'документов')} · ${nc} ${plural(nc, 'тест-кейс', 'тест-кейса', 'тест-кейсов')}`;
    if (sub && sub.textContent !== subT) sub.textContent = subT;
  }
  const sig = JSON.stringify([on, S.productId, S.running, !!S.follow, S.products.map((p) => [p.id, p.name])]);
  if (sig === prodSelSig) return;
  prodSelSig = sig;
  box.hidden = !on;
  if (!on) return;
  sel.innerHTML = S.products.map((p) => `<option value="${esc(p.id)}" ${p.id === S.productId ? 'selected' : ''}>${esc(p.name || 'Без названия')}</option>`).join('') + '<option value="__new">+ Новый продукт…</option>';
  sel.value = S.productId;
  sel.disabled = S.running || !!S.follow;
  sel.title = S.running ? 'Переключиться можно после окончания генерации' : 'Продукт: документы, контекст, запуски и знания агента';
}
/* ---------- документы: список сворачивается (отдельно в каждом режиме), в базе знаний — статус разбора ---------- */
const docsFolded = () => !!S.docsFold?.[S.settings.mode];
function toggleDocsFold(open) {
  const fold = open === undefined ? !docsFolded() : !open;
  S.docsFold = { ...(S.docsFold || {}), [S.settings.mode]: fold };
  lsSet('qapro.docsFold', S.docsFold);
  renderDocs();
  if (!fold) $('#docs-fold')?.focus();
}
const docTitle = (d) => String(d.name || '').replace(/\.(md|markdown|txt|docx|pdf|xlsx|xls|csv)$/i, '');
// где документ в базе знаний: разобран (и с тех пор не менялся), разбирается сейчас или ждёт разбора
function docKbState(d) {
  if (d.status !== 'ready' || !S.productId || d.pid !== S.productId || !S.kb.loaded) return '';
  if (S.kb.index.docs?.[d.id]?.hash === docHash(d)) return 'ok';
  if ((S.kb.job.busy && S.kb.job.doc === d.name) || S.kb.queue.some((x) => x.id === d.id)) return 'busy';
  return 'pend';
}
const KB_ST = { ok: ['ok', 'в базе знаний'], busy: ['', 'разбирается…'], pend: ['warn', 'не разобран'] };
// база знаний для генерации: сколько разделов и из скольких документов — одной фразой
function kbRunInfo() {
  if (!S.productId) return 'Без продукта база знаний не ведётся — генерация идёт только по загруженным документам.';
  if (!S.kb.loaded) return 'Загружаю базу знаний продукта…';
  const n = S.kb.index.blocks.length, nd = Object.keys(S.kb.index.docs || {}).length;
  if (!n) return 'База знаний продукта пока пуста: загруженные документы сохранятся в продукте и разберутся в ней.';
  return `Остальное о продукте агент берёт из базы знаний: ${n} ${plural(n, 'раздел', 'раздела', 'разделов')} из ${nd} ${plural(nd, 'документа', 'документов', 'документов')}. Загруженные документы сохраняются в продукте и пополняют её.`;
}
function docsSumHTML(help, list, ready) {
  const empty = help ? (S.productId ? 'В продукте пока нет документов' : 'Документов пока нет') : 'Документы для запуска не загружены';
  if (!list.length) return `<button class="fold-sum" type="button" data-docs-act="open"><span class="fold-sum-n">${empty}</span>${!help && S.productId && S.kb.index.blocks.length ? `<span class="fold-sum-s"><span>база знаний: ${S.kb.index.blocks.length} ${plural(S.kb.index.blocks.length, 'раздел', 'раздела', 'разделов')}</span></span>` : ''}</button>
    <button class="icon-btn" type="button" data-docs-act="add" aria-label="Добавить документы" title="Добавить документы"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M8 3v10M3 8h10"/></svg></button>`;
  const names = list.map(docTitle), shown = names.slice(0, 3).join(', ') + (names.length > 3 ? ` и ещё ${names.length - 3}` : '');
  const busy = list.filter((d) => d.status === 'parsing' || d.status === 'loading').length, bad = list.filter((d) => d.status === 'error').length;
  const parts = [];
  if (help) {
    const st = ready.map(docKbState), ok = st.filter((x) => x === 'ok').length, pend = st.filter((x) => x === 'pend').length;
    if (S.productId && S.kb.loaded) parts.push(`<span class="${ok === ready.length && ready.length ? 'ok' : ''}">в базе знаний ${ok} из ${ready.length}</span>`);
    if (pend) parts.push(`<span class="warn">не разобрано ${pend}</span>`);
  } else if (S.productId && S.kb.index.blocks.length) parts.push(`<span>+ база знаний: ${S.kb.index.blocks.length} ${plural(S.kb.index.blocks.length, 'раздел', 'раздела', 'разделов')}</span>`);
  if (S.kb.job.busy) { const kp = kbProgress(); parts.push(`<span>${esc(kp ? kp.title : 'идёт разбор…')}</span>`); }
  if (busy) parts.push(`<span>загружается ${busy}</span>`);
  if (bad) parts.push(`<span class="err">с ошибкой ${bad}</span>`);
  return `<button class="fold-sum" type="button" data-docs-act="open" title="Развернуть список документов"><span class="fold-sum-n">${esc(shown)}</span><span class="fold-sum-s">${parts.join('')}</span></button>
    <button class="icon-btn" type="button" data-docs-act="add" aria-label="Добавить документы" title="Добавить документы"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M8 3v10M3 8h10"/></svg></button>`;
}
/* панель документов. В «Базе знаний» — все документы продукта. В генерации и актуализации — только документы запуска
   (загруженные для него): выбирать из всех документов не нужно, остальное агент берёт из базы знаний. */
function renderDocs() {
  const help = S.settings.mode === 'help', upd = S.settings.mode === 'update';
  const prod = !!S.productId;
  const list = help ? S.docs : runDocList(), ready = list.filter((d) => d.status === 'ready'), total = ready.reduce((a, d) => a + d.chars, 0);
  $('#h-docs-t').textContent = help ? (prod ? 'Документы продукта' : 'Документы') : 'Документы запуска';
  const nDocs = list.length;
  $('#docs-total').textContent = !nDocs ? '' : `${nDocs} ${plural(nDocs, 'документ', 'документа', 'документов')} · ${fmtKChars(total)}`;
  const folded = docsFolded();
  $('#docs-fold').setAttribute('aria-expanded', String(!folded));
  $('#docs-fold').title = folded ? 'Развернуть список документов' : 'Свернуть список документов';
  $('#docs-body').hidden = folded;
  $('#docs-sum').hidden = !folded;
  $('#docs-sum').innerHTML = folded ? docsSumHTML(help, list, ready) : '';
  kbEnsureConflicts();
  $('#doc-list').innerHTML = folded ? '' : list.map((d) => {
    const kb = KB_ST[docKbState(d)];
    const conf = docConflicts(d).reduce((a, x) => a + x.items.length, 0);
    const keep = !help && prod && d.pid && d.status === 'ready'; // из запуска убирается, в продукте остаётся
    return `
    <li class="doc">
      <span class="ext">${esc(d.ext || '?')}</span>
      <div style="min-width:0">
        <div class="doc-name" title="${esc(d.name)}">${esc(d.name)}</div>
        <div class="doc-meta">${d.status === 'parsing' ? '<span>разбор…</span>' : d.status === 'loading' ? '<span>загрузка…</span>' : d.status === 'error' ? `<span class="err">${esc(d.error)}</span>` : `<span class="num">${fmtKChars(d.chars)}</span>`}${d.sample ? '<span class="tag-sample">пример</span>' : ''}${d.source === 'video' ? '<span class="tag-sample">из видео</span>' : ''}${d.warn ? `<span class="warn">${esc(d.warn)}</span>` : ''}${kb ? `<span class="kb-st ${kb[0]}">${kb[1]}</span>` : ''}${conf ? `<span class="warn">расхождений ${conf}</span><button class="link doc-conf" type="button" data-doc-act="conf" data-id="${d.id}" title="Где этот документ расходится с другими документами продукта">Показать</button>` : ''}${d.addedAt && prod && help ? `<span>${new Date(d.addedAt).toLocaleDateString('ru-RU')}</span>` : ''}</div>
      </div>
      <div class="doc-acts">
        ${d.status === 'ready' ? `<button class="icon-btn" type="button" data-doc-act="preview" data-id="${d.id}" aria-label="Показать извлечённый текст" title="Показать извлечённый текст">${ICON.eye}</button>` : ''}
        <button class="icon-btn" type="button" data-doc-act="${keep ? 'unrun' : 'remove'}" data-id="${d.id}" aria-label="${keep ? 'Убрать из запуска' : prod && help ? 'Удалить документ из продукта' : 'Убрать документ'}" title="${keep ? 'Убрать из запуска — документ останется в продукте и базе знаний' : prod && help ? 'Удалить из продукта' : 'Убрать'}">${ICON.x}</button>
      </div>
      ${d.preview ? `<pre class="doc-preview">${esc(d.text.slice(0, 5000))}${d.text.length > 5000 ? '\n…' : ''}</pre>` : ''}
    </li>`;
  }).join('');
  $('#btn-sample').hidden = S.docs.length > 0; // пример ТЗ — только для пустого продукта: когда документы есть, кнопка не нужна
  const kp = kbProgress();
  const kbN = S.kb.job.busy ? ` ${kp ? `${kp.title}${kp.line ? ' · ' + kp.line : ''}.` : `Разбираю «${S.kb.job.doc || 'документ'}» по разделам базы знаний…`}` : S.kb.note ? ' ' + S.kb.note : '';
  const what = upd ? 'Актуализация' : 'Генерация';
  const text = help
    ? (!S.docs.length ? (prod ? 'В продукте пока нет документов. Загрузите ТЗ, описания и инструкции — агент разберёт их по разделам базы знаний.' : '') : prod ? 'Из документов продукта агент собирает разделы базы знаний и сводки по ним — их учитывает генерация. Видео .mp4 разбираются в «Материалах».' : '')
    : (!list.length ? `Загрузите ТЗ и другие документы для этого запуска — ${what.toLowerCase()} пойдёт по ним.` : `${what} идёт по этим документам.`) + (prod ? ' ' + kbRunInfo() : '');
  const kbLink = !help && prod && S.kb.loaded ? ' <button class="link" type="button" data-docs-act="kb">Открыть базу знаний</button>' : '';
  $('#docs-note').innerHTML = esc(text + kbN) + kbLink;
}
/* ---------- расхождения документа с другими документами продукта ---------- */
// Расхождения хранятся в сводках разделов. Документ участвует, если его имя есть в строке расхождения;
// если модель не назвала документы, строка относится ко всем документам раздела.
const nameKey = (s) => normKey(s).replace(/ /g, '');
function docConflicts(d) {
  if (!d?.pid || !S.kb.loaded || S.kb.pid !== d.pid) return [];
  const mine = nameKey(docTitle(d));
  const out = [];
  for (const b of S.kb.index.blocks) {
    if (!b.conf || !arrOf(b.docIds).includes(d.id)) continue;
    const list = arrOf(b.cf).length ? b.cf : arrOf(S.kb.cache[b.id]?.conflicts);
    const names = arrOf(b.docIds).map((id) => S.docs.find((x) => x.id === id)).filter(Boolean).map((x) => nameKey(docTitle(x))).filter((n) => n.length > 2);
    const items = list.filter((c) => { const k = nameKey(c); return (mine.length > 2 && k.includes(mine)) || !names.some((n) => k.includes(n)); });
    if (items.length) out.push({ id: b.id, title: b.title, items });
  }
  return out;
}
// старые разделы хранят расхождения только в самом разделе — подгружаем их один раз
let kbCfLoading = false;
function kbEnsureConflicts() {
  if (kbCfLoading || !S.kb.loaded || !S.caps.db) return;
  const need = S.kb.index.blocks.filter((b) => b.conf && !arrOf(b.cf).length && !S.kb.cache[b.id]);
  if (!need.length) return;
  kbCfLoading = true;
  (async () => { for (const b of need) { try { await kbBlock(b.id); } catch { /* без расхождений этого раздела */ } } })()
    .finally(() => { kbCfLoading = false; renderDocs(); });
}
function openDocConflicts(d) {
  const secs = docConflicts(d), n = secs.reduce((a, x) => a + x.items.length, 0);
  const hl = (c) => { const t = docTitle(d); const i = c.toLowerCase().indexOf(t.toLowerCase()); return i < 0 ? mdInline(c) : `${mdInline(c.slice(0, i))}<mark>${esc(c.slice(i, i + t.length))}</mark>${mdInline(c.slice(i + t.length))}`; };
  $('#mat-title').textContent = `Расхождения: ${docTitle(d)}`;
  $('#mat-body').innerHTML = !n ? emptyHTML('Расхождений нет', 'Сводки разделов не нашли противоречий этого документа с другими.')
    : `<div class="conf-dlg"><p class="hint">Документ «${esc(d.name)}» расходится с другими документами продукта: ${n} ${plural(n, 'место', 'места', 'мест')} в ${secs.length} ${plural(secs.length, 'разделе', 'разделах', 'разделах')}. Уточните у аналитика — пока ответа нет, генерация следует требованиям запуска и не выдаёт спорное за факт, а анализ задаёт по этим местам вопросы.</p>
      ${secs.map((x) => `<section class="conf-sec"><div class="conf-h"><b>Раздел «${esc(x.title)}»</b><button class="link" type="button" data-conf-open="${esc(x.id)}">Открыть раздел</button></div><ul>${x.items.map((c) => `<li>${hl(c)}</li>`).join('')}</ul></section>`).join('')}</div>`;
  openDialog('mat-ov');
}
// из окна расхождений — в раздел базы знаний
function openKbSection(id) {
  closeDialog('mat-ov');
  if (S.settings.mode !== 'help') { S.settings.mode = 'help'; saveSettings(); renderMode(); }
  S.helpView = 'blocks'; lsSet('qapro.kbView', 'blocks');
  S.kb.open = id; S.kb.edit = null;
  renderHelp(true);
  $('#help-view')?.scrollIntoView({ block: 'start', behavior: 'smooth' });
}
/* ---------- режим: генерация или актуализация ---------- */
const MODES = [['generate', 'Генерация', 'Чек-листы и тест-кейсы по ТЗ'], ['update', 'Актуализация', 'Актуализация существующих кейсов под ТЗ'], ['help', 'База знаний', 'Вопросы и ответы строго по базе знаний продукта'], ['trace', 'Трассировка', 'Разбор дефекта по слоям: описание и стек трейс']];
function renderMode() {
  const m = S.settings.mode;
  $('#mode-seg').innerHTML = MODES.map(([id, n, t]) => `<button type="button" role="radio" aria-checked="${m === id}" data-mode="${id}" title="${t}">${n}</button>`).join('');
  $('#upd-panel').hidden = m !== 'update';
  const newRun = $('#btn-newses'), noRun = m === 'help' || m === 'trace';
  if (newRun) { newRun.disabled = noRun; newRun.title = noRun ? 'Новый запуск — в режимах «Генерация» и «Актуализация»' : 'Закрыть текущий результат и начать новый запуск. Результат останется в «Истории», документы и знания продукта — на месте'; }
  document.querySelector('.app')?.classList.toggle('no-rail', m === 'trace');
  for (const el of document.querySelectorAll('[data-modes]')) el.hidden = !el.dataset.modes.split(',').includes(m);
  let k = 0;
  for (const el of document.querySelectorAll('.rail > .panel')) if (!el.hidden) { const n = el.querySelector('.step-n'); if (n) n.textContent = String(++k).padStart(2, '0'); }
  renderUpd(); renderParams(); renderRunControls(); renderTabs(); renderTab(); renderDocs();
}
function renderUpd() {
  const f = S.upd.file, box = $('#upd-info');
  if (!box) return;
  $('#upd-drop').hidden = !!f && f.status !== 'error';
  if (!f) { box.innerHTML = ''; return; }
  const byType = (t) => f.cases.filter((c) => c.typeHint === t).length;
  const hints = TYPES.filter((t) => byType(t)).map((t) => `${TL[t]} ${byType(t)}`).join(' · ');
  box.innerHTML = `<ul class="doc-list"><li class="doc">
      <span class="ext">${esc(f.ext || '?')}</span>
      <div style="min-width:0"><div class="doc-name" title="${esc(f.name)}">${esc(f.name)}</div>
        <div class="doc-meta">${f.status === 'parsing' ? '<span>разбор…</span>' : f.status === 'error' ? `<span class="err">${esc(f.error)}</span>` : `<span class="num">${f.cases.length} ${plural(f.cases.length, 'кейс', 'кейса', 'кейсов')}</span>${hints ? `<span>${esc(hints)}</span>` : ''}${f.note ? `<span>${esc(f.note)}</span>` : ''}`}</div></div>
      <div class="doc-acts">${f.status === 'ready' ? `<button class="icon-btn" type="button" data-upd-act="preview" aria-label="Показать найденные кейсы" title="Показать найденные кейсы">${ICON.eye}</button>` : ''}<button class="icon-btn" type="button" data-upd-act="remove" aria-label="Убрать файл" title="Убрать файл">${ICON.x}</button></div>
      ${f.preview && f.status === 'ready' ? `<ol class="upd-preview">${f.cases.slice(0, 40).map((c) => `<li><span class="mono">${esc(c.srcId || '#' + c.index)}</span> ${esc(c.title)}</li>`).join('')}${f.cases.length > 40 ? `<li class="muted">и ещё ${f.cases.length - 40}</li>` : ''}</ol>` : ''}
    </li></ul>
    ${f.status === 'ready' ? '<button class="link" type="button" data-upd-act="replace">Заменить файл</button>' : ''}`;
}

/* ---------- доп. контекст от QA ---------- */
const CTX_TABS = [['all', 'Для всех'], ['api', 'API'], ['ui', 'UI'], ['e2e', 'E2E']];
const CTX_PH = {
  all: 'Например: тестовое окружение — stage; вход под ролью «Оператор», учётная запись qa_operator',
  api: 'Например: базовый URL https://stage.example.ru/api; авторизация — Bearer-токен из POST /auth/token',
  ui: 'Например: проверки выполняются на экране «Профиль клиента». Перейти: Главная → Клиенты → карточка клиента → вкладка «Профиль»',
  e2e: 'Например: сценарии начинаются со входа в ЛК под пользователем qa_user; письма приходят в тестовый ящик test@example.ru',
};
function renderQaCtx(force) {
  const ta = $('#qa-ctx');
  if (!ta) return;
  const k = S.qaCtxType;
  $('#qa-ctx-tabs').innerHTML = CTX_TABS.map(([id, n]) => `<button class="fchip" type="button" data-ctx="${id}" aria-pressed="${k === id}">${n}${S.qaCtx[id]?.trim() ? '<span class="dot-d" title="Заполнено">•</span>' : ''}</button>`).join('');
  if (force || document.activeElement !== ta || ta.dataset.k !== k) ta.value = S.qaCtx[k] || '';
  ta.dataset.k = k;
  ta.placeholder = CTX_PH[k];
  const filled = CTX_TABS.filter(([id]) => S.qaCtx[id]?.trim()).map(([id, n]) => (id === 'all' ? 'для всех' : n));
  $('#qa-ctx-note').textContent = filled.length
    ? `Учитывается при генерации: ${filled.join(', ')}. Контекст «для всех» получают все виды тестов, остальное — только свой вид.`
    : 'Пусто — агент опирается только на загруженные документы.';
}
function renderParams() {
  const o = S.settings.outputs, upd = S.settings.mode === 'update';
  $('#outs').innerHTML = [['cases', 'Тест-кейсы', upd ? 'Актуализация — всегда' : 'Шаги по шаблонам'], ['checklist', 'Чек-лист', upd ? 'Заново по текущему ТЗ' : 'Короткие пункты проверок']].map(([k, n, d]) => `
    <label class="type-opt" data-t="out"><input type="checkbox" id="out-${k}" data-out="${k}" ${o[k] || (upd && k === 'cases') ? 'checked' : ''} ${upd && k === 'cases' ? 'disabled' : ''}><b>${n}</b><span>${d}</span></label>`).join('');
  $('#types-hint').textContent = upd ? 'Для этих видов агент допишет новые кейсы. Кейсы из файла актуализируются все.' : '';
  $('#types-hint').hidden = !upd;
  $('#types').innerHTML = TYPES.map((t) => `
    <label class="type-opt" data-t="${t}"><input type="checkbox" id="type-${t}" data-type="${t}" ${S.settings.types[t] ? 'checked' : ''}><b>${TL[t]}</b><span>${TYPE_DESC[t]}</span></label>`).join('');
  $('#depth').innerHTML = DEPTHS.map((d) => `<button type="button" role="radio" aria-checked="${S.settings.depth === d.id}" data-depth="${d.id}">${d.label}</button>`).join('');
  $('#depth-hint').textContent = (DEPTHS.find((d) => d.id === S.settings.depth) || DEPTHS[1]).hint;
  renderProviders();
  renderStages();
  renderAIHint();
  $('#agent-tools').checked = S.settings.agentTools;
  $('#skip-existing').checked = S.settings.skipExisting;
  $('#strict-rules').checked = !!S.settings.strictRules;
  $('#economy').checked = S.settings.economy;
  $('#reuse-analysis').checked = S.settings.reuseAnalysis;
  const claudeAI = parseAI(S.settings.genAI)?.kind === 'claude';
  $('#eco-hint').textContent = S.settings.mode === 'help'
    ? (S.settings.economy ? `Включён: ${claudeAI ? 'быстрая модель, ' : ''}меньше фрагментов базы знаний в каждом ответе.` : 'Модель получает только фрагменты базы знаний по теме вопроса.')
    : S.settings.economy
      ? `Включён: ${claudeAI ? 'быстрая модель для сверки кейсов и знаний о продукте, ' : ''}меньше знаний и фрагментов ТЗ в каждом запросе, без поиска по документам.`
      : 'Всегда: в запрос идут только нужные разделы знаний и фрагменты ТЗ, знания обновляются правками, повторное ревью — только по изменённым кейсам.';
}
function runLabel() {
  const o = S.settings.outputs;
  if (S.settings.mode === 'update') return o.checklist ? 'Актуализировать кейсы и чек-лист' : 'Актуализировать тест-кейсы';
  return o.cases && o.checklist ? 'Сгенерировать чек-лист и тест-кейсы' : o.checklist ? 'Сгенерировать чек-лист' : 'Сгенерировать тест-кейсы';
}
/* «Сократить количество тестов»: спрашиваем, сколько оставить, и сокращаем черновик */
function openReduce() {
  const n = S.run ? activeCases(S.run).length : 0, inp = $('#reduce-n'), hint = $('#reduce-hint'); // устаревшие кейсы не считаются: их не сократить
  if (!isDraft(S.run) || n < 2) return;
  $('#reduce-form').hidden = false;
  inp.max = String(n - 1); inp.value = String(Math.max(1, Math.floor(n / 2)));
  hint.className = 'hint'; hint.textContent = `В черновике ${n} ${plural(n, 'кейс', 'кейса', 'кейсов')}. Оставить можно от 1 до ${n - 1}; покрытие требований сохранится.`;
  inp.focus(); inp.select();
}
let reduceWarned = false;
function resetReduceWarn() { reduceWarned = false; reducePending = null; const go = $('#reduce-go'); if (go) go.textContent = 'Сократить'; }
function closeReduce() { resetReduceWarn(); $('#reduce-form').hidden = true; }
async function reduceGo() {
  const inp = $('#reduce-n'), hint = $('#reduce-hint'), go = $('#reduce-go');
  const n = S.run ? activeCases(S.run).length : 0, v = Number(inp.value);
  if (!Number.isInteger(v) || v < 1 || v >= n) { resetReduceWarn(); hint.className = 'hint err'; hint.textContent = `Введите целое число от 1 до ${n - 1}.`; return; }
  const confirmed = reduceWarned;
  go.disabled = true; hint.className = 'hint'; hint.textContent = confirmed ? 'Сокращаю…' : 'Выбираю самые важные кейсы…';
  const res = await reduceDraft(v, { confirmed });
  go.disabled = false;
  if (res.warn) { reduceWarned = true; go.textContent = 'Сократить всё равно'; hint.className = 'hint warn-hint'; hint.textContent = res.message; renderRunControls(); return; }
  resetReduceWarn();
  if (res.error) { hint.className = 'hint err'; hint.textContent = res.error; renderRunControls(); return; }
  closeReduce();
  toast(`Осталось ${res.kept} ${plural(res.kept, 'тест', 'теста', 'тестов')}, убрано ${res.removed}${confirmed ? '' : '. Покрытие требований сохранено'}.`);
  renderRunControls();
}
function renderRunControls() {
  const run = $('#btn-run'), stop = $('#btn-stop'), note = $('#run-note'), rev = $('#btn-review');
  run.hidden = S.running; stop.hidden = !S.running;
  const hasRes = !!S.run && (S.run.cases.length > 0 || checklistItems(S.run).length > 0);
  rev.hidden = S.running || !hasRes; rev.disabled = !aiReady(aiValue('review'));
  rev.title = aiProblem(aiValue('review')) || 'Субагент проверит чек-лист и кейсы по документации и правилам ревью';
  run.textContent = runLabel();
  const regen = $('#btn-regen');
  if (regen) {
    const dr = isDraft(S.run) && S.run.cases.length > 0;
    regen.hidden = S.running || !dr;
    regen.disabled = draftLocked(S.run) || !docsFor(S.run).length || !aiReady(S.run?.settings?.genAI || S.settings.genAI);
  }
  const red = $('#btn-reduce'), form = $('#reduce-form');
  if (red) {
    const dr = isDraft(S.run) && activeCases(S.run).length > 1;
    red.hidden = S.running || !dr;
    red.disabled = draftLocked(S.run) || reducing || !aiReady(S.run?.settings?.genAI || S.settings.genAI);
    if (form && (S.running || !dr)) form.hidden = true;
  }
  if (reducing) run.disabled = true;
  // поле «API» активно только когда в запуске есть спецификация OpenAPI / Swagger
  const apiOn = docsFor(null).some((d) => d.openapi);
  const af = $('#api-filter'); if (af) af.disabled = !apiOn;
  const ab = $('#api-block'); if (ab) ab.classList.toggle('is-off', !apiOn);
  const docs = docsFor(null), types = selectedTypes(), o = S.settings.outputs, upd = S.settings.mode === 'update';
  run.disabled = !docs.length || !types.length || (!upd && !o.cases && !o.checklist) || runDocList().some((d) => d.status === 'parsing' || d.status === 'loading') || (upd && S.upd.file?.status !== 'ready');
  renderProdSelect();
  note.className = 'run-note';
  if (S.follow) { run.disabled = true; rev.hidden = true; note.textContent = 'Генерация идёт в другой вкладке — дождитесь окончания или остановите её там.'; return; }
  if (S.resume) { note.textContent = `Продолжу прерванную генерацию через ${S.resume.left} с — отменить можно на вкладке «Агент».`; }
  if (S.running) { note.textContent = `Агент работает · ${fmtClock(elapsedOf(S.run))}. ${S.workerPeer?.online && !S.workerPeer.self && !workerOn() ? 'Окно можно закрыть — генерацию доделает фоновый исполнитель.' : 'Можно переключать вкладки.'}`; return; }
  if (S.caps.ready && !aiReady(S.settings.genAI)) { note.className = 'run-note err'; note.textContent = aiProblem(S.settings.genAI); return; }
  if (upd && S.upd.file?.status !== 'ready') { note.textContent = S.upd.file?.status === 'parsing' ? 'Разбираю файл с тест-кейсами…' : 'Загрузите файл с тест-кейсами: .xlsx или .json.'; return; }
  if (!docs.length) { note.textContent = runDocList().some((d) => d.status === 'parsing' || d.status === 'loading') ? 'Читаю документы…' : S.productId ? 'Загрузите ТЗ для этого запуска — остальное о продукте агент возьмёт из базы знаний.' : 'Добавьте документы, чтобы начать.'; return; }
  if (!upd && !o.cases && !o.checklist) { note.textContent = 'Выберите, что сгенерировать.'; return; }
  if (!types.length) { note.textContent = 'Выберите хотя бы один вид тестов.'; return; }
  const total = docs.reduce((a, d) => a + d.chars, 0);
  const nSrc = upd ? S.upd.file.cases.length : 0;
  const calls = buildChunks(docs).length + (o.checklist ? 1 : 0) + (upd ? Math.ceil(nSrc / 10) + Math.ceil(nSrc / 5) + 1 : o.cases ? 2 : 0);
  const k = knowOf(null);
  const kn = k ? ` Агент учтёт ${[k.passport ? 'знания о продукте' : '', k.cases.length ? `${k.cases.length} ${plural(k.cases.length, 'готовый кейс', 'готовых кейса', 'готовых кейсов')} продукта` : ''].filter(Boolean).join(' и ')}.` : '';
  note.textContent = `${upd ? `${S.upd.file.cases.length} ${plural(S.upd.file.cases.length, 'кейс', 'кейса', 'кейсов')} на актуализацию · ` : ''}${docs.length} ${plural(docs.length, 'документ', 'документа', 'документов')} · ${fmtKChars(total)} · ${types.map((t) => TL[t]).join(', ')}.${k && (k.passport || k.cases.length) ? kn : ''} ${parseAI(S.settings.genAI)?.kind === 'claude' ? `Запросы к модели (от ${calls}) расходуют лимит вашего аккаунта Claude.` : `Запросы к модели (от ${calls}) уходят в «${aiLabel(S.settings.genAI)}».`}`;
}

/* ---------- правила для агента (левая колонка) и настройки под шестерёнкой ---------- */
const SET_TABS = [['model', 'Модель'], ['ctx', 'Контекст'], ['tpl', 'Шаблоны'], ['export', 'Формат экспорта'], ['review', 'Правила ревью'], ['tms', 'ТМС'], ['bg', 'Фон']];
const tmsDirty = () => !!S.tmsDraft && JSON.stringify(S.tmsDraft) !== JSON.stringify(S.tms);
const cfgKeyOfTab = () => (S.cfgTab === 'tpl' ? S.cfgType : S.cfgTab);
const cfgName = (k) => (k === 'rules' ? 'Правила для агента' : k === 'export' ? 'Формат экспорта' : k === 'review' ? 'Правила ревью' : 'Шаблон ' + TL[k]);
const cfgTabDirty = (id) => (id === 'tpl' ? TYPES.some((t) => S.cfgDirty[t]) : id === 'model' ? false : id === 'tms' ? tmsDirty() : id === 'ctx' ? S.ctx.conflicts.length > 0 || (S.ctx.src.kind !== 'folder' && S.ctx.pending.size > 0) : !!S.cfgDirty[id]);
const DOT = '<span class="dot-d" title="Есть несохранённые изменения">•</span>';
function renderCfgTabs() {
  const nav = $('#set-tabs');
  if (nav) nav.innerHTML = SET_TABS.map(([id, name]) => `<button type="button" role="tab" id="settab-${id}" aria-selected="${S.setTab === id}" data-settab="${id}">${name}${cfgTabDirty(id) ? DOT : ''}</button>`).join('');
  $('#btn-settings')?.classList.toggle('dirty', ['ctx', 'tpl', 'export', 'review', 'tms'].some(cfgTabDirty));
  const rd = $('#h-rules-dot');
  if (rd) rd.hidden = !S.cfgDirty.rules;
}
function openSettings(tab) {
  if (tab) S.setTab = tab;
  renderCfg();
  openDialog('set-ov');
}
function renderRules() {
  const ta = $('#cfg-rules');
  if (ta && document.activeElement !== ta && ta.value !== S.cfg.rules) ta.value = S.cfg.rules;
  const f = $('#rules-foot');
  if (f) f.innerHTML = cfgFootHTML('rules');
}
function renderCfg() {
  renderCfgTabs();
  renderRules();
  const model = S.setTab === 'model', tms = S.setTab === 'tms', bg = S.setTab === 'bg', cx = S.setTab === 'ctx';
  $('#set-model').hidden = !model;
  $('#set-tms').hidden = !tms;
  $('#set-bg').hidden = !bg;
  $('#set-ctx').hidden = !cx;
  $('#set-cfg').hidden = model || tms || bg || cx;
  if (model) { renderProviders(true); return; }
  if (cx) { bindCtxPane(); renderCtxPane(); return; }
  if (bg) { renderBgPane(true); return; }
  if (tms) { if (!S.tmsDraft) S.tmsDraft = { ...S.tms }; renderTmsDialog(); return; }
  S.cfgTab = S.setTab;
  const body = $('#cfg-body');
  if (S.cfgTab === 'tpl') {
    const t = S.cfgType, tp = S.cfg.tpl[t];
    body.innerHTML = `<div class="cfg-types">${TYPES.map((x) => `<button class="fchip" type="button" data-cfgtype="${x}" aria-pressed="${t === x}">${TL[x]}${S.cfgDirty[x] ? ' •' : ''}</button>`).join('')}</div>
      <div class="field"><div class="lbl-row"><label class="lbl" for="cfg-example">Пример кейса ${TL[t]} (JSON)</label><button class="link" type="button" data-cfg="expand">Развернуть</button></div>
        <textarea class="code" id="cfg-example" rows="12" spellcheck="false">${esc(tp.example)}</textarea><span class="valid" id="cfg-valid"></span></div>
      <div class="field"><label class="lbl" for="cfg-tplrules">Особенности оформления ${TL[t]}</label>
        <textarea id="cfg-tplrules" rows="4" placeholder="Например: шаги в повелительном наклонении, ожидаемый результат у каждого шага">${esc(tp.rules)}</textarea></div>
      <div class="prefix-row"><label class="lbl" for="cfg-prefix">Префикс ID</label><input type="text" id="cfg-prefix" class="mono" value="${esc(tp.idPrefix)}" spellcheck="false"></div>
      <p class="hint">Агент повторяет поля, вложенность и стиль примера. Можно указать массив из нескольких примеров — первый задаёт структуру. Поле id система заполняет сама: префикс и номер.</p>
      <div class="cfg-mini"><button class="link" type="button" data-cfg="load">Загрузить из .json</button><button class="link" type="button" data-cfg="default">Стандартный пример</button></div>
      <input type="file" id="cfg-file" accept=".json,application/json" hidden>`;
  } else if (S.cfgTab === 'review') {
    body.innerHTML = `<div class="field"><div class="lbl-row"><label class="lbl" for="cfg-review">Правила для ревьюера</label><button class="link" type="button" data-cfg="expand">Развернуть</button></div>
      <textarea id="cfg-review" rows="7" placeholder="Например: каждый кейс проверяет одно требование; ожидаемый результат — с конкретными значениями; негативные кейсы — с кодом ошибки из ТЗ">${esc(S.cfg.reviewRules)}</textarea>
      <div class="cfg-mini"><button class="link" type="button" data-cfg="load-md">Приложить файл .md</button></div>
      <input type="file" id="cfg-md" accept=".md,.markdown,.txt,text/markdown,text/plain" hidden>
      <p class="hint">Ревьюер проверяет по этим правилам и по стандартным критериям: соответствие документации, полнота, тестовые данные, шаблон, дубли, наборы.</p></div>
      <div class="field"><span class="lbl">Память агента · ${S.lessons.length}</span>
        <p class="hint">Правила из ваших замечаний: комментарии к доработке кейсов и пунктов, причины отклонения замечаний ревьюера. Агент учитывает их при генерации и ревью, они общие для команды.</p>
        <ul class="lessons">${S.lessons.length ? S.lessons.map((l) => `<li><div style="min-width:0"><span>${esc(l.text)}</span><div><span class="chip">${LESSON_SCOPE_RU[l.scope] || l.scope}</span></div></div><button class="icon-btn" type="button" data-cfg="lesson-del" data-id="${esc(l.id)}" aria-label="Удалить правило" title="Удалить правило">${ICON.x}</button></li>`).join('') : '<li class="muted small">Пока пусто — правила появятся после ваших замечаний.</li>'}</ul>
        <div class="lesson-add"><input id="lesson-new" type="text" placeholder="Добавить правило вручную" aria-label="Новое правило"><select id="lesson-scope" aria-label="Для чего правило"><option value="generation">генерация</option><option value="review">ревью</option><option value="both">оба</option></select><button class="btn" type="button" data-cfg="lesson-add">Добавить</button></div></div>`;
  } else {
    body.innerHTML = `<div class="field"><div class="lbl-row"><label class="lbl" for="cfg-export">Формат и правила заполнения</label><button class="link" type="button" data-cfg="expand">Развернуть</button></div>
      <textarea id="cfg-export" rows="8" placeholder="Например: CSV для импорта в Test IT, разделитель «;». Колонки: Название, Предусловия, Шаг, Ожидаемый результат, Приоритет, Теги. Каждый шаг — отдельная строка, название и предусловия — только в первой строке кейса. В теги добавить smoke или regression.">${esc(S.cfg.exportFormat)}</textarea>
      <p class="hint">Опишите словами или вставьте пример файла — JSON, CSV, Excel, XML или Markdown. Файл по описанию собирает агент. Пусто — стандартный JSON со всеми кейсами, наборами и трассировкой.</p></div>`;
  }
  renderCfgFoot();
  updateCfgValidity();
}
function cfgFootHTML(k) {
  if (ctxOwnsCfg()) return ctxCfgFoot(k); // источник контекста — репозиторий
  const team = S.cfgTeam[k], dirty = S.cfgDirty[k];
  const canSave = !!(S.caps.db && S.caps.canEdit);
  const state = dirty ? '<b>Изменено в этом окне</b>' : team ? `<b>Версия команды</b><span>· обновлена ${fmtDate(team.updatedAt)}</span>` : `<b>${k === 'rules' || k === 'export' || k === 'review' ? 'Не задано' : 'Стандартный шаблон'}</b>`;
  return `<div class="cfg-state${dirty ? ' dirty' : ''}">${esc(cfgName(k))}: ${state}</div>
    ${dirty ? `<div class="row">${canSave ? `<button class="btn accent" type="button" data-cfg="save" data-k="${k}">Сохранить для команды</button>` : ''}<button class="btn" type="button" data-cfg="revert" data-k="${k}">${team ? 'Вернуть версию команды' : 'Отменить изменения'}</button></div>
    ${canSave ? '' : `<p class="hint">${S.caps.db ? 'Изменения действуют только у вас. Сохранить для всей команды может владелец или редактор приложения.' : 'Изменения действуют только в этом браузере.'}</p>`}` : ''}`;
}
function renderCfgFoot() {
  const f = $('#cfg-foot');
  if (f && S.setTab !== 'model') f.innerHTML = cfgFootHTML(cfgKeyOfTab());
  const rf = $('#rules-foot');
  if (rf) rf.innerHTML = cfgFootHTML('rules');
}
function updateCfgValidity() {
  const v = $('#cfg-valid');
  if (!v) return;
  const info = tplInfo(S.cfgType);
  v.className = 'valid ' + (info.ok ? 'ok' : 'bad');
  v.textContent = info.ok ? `JSON корректен · ${info.fields.length} ${plural(info.fields.length, 'поле', 'поля', 'полей')}${info.examples.length > 1 ? ` · ${info.examples.length} примера` : ''}${info.idField ? '' : ' · поле id не найдено'}` : info.error;
}
function markCfgDirty(k) {
  S.cfgDirty[k] = true;
  clearTimeout(markCfgDirty.t); markCfgDirty.t = setTimeout(saveDrafts, 400);
  renderCfgTabs(); renderCfgFoot();
  if (k === S.cfgType) updateCfgValidity();
  if (k === 'export' && S.tab === 'export') renderTab();
}
async function saveCfg(k) {
  if (ctxOwnsCfg()) return ctxSaveCfg(k);
  const db = S.caps.db;
  if (!db) return;
  const now = Date.now(), by = S.caps.uid || '';
  try {
    if (k === 'rules') await db.doc('config/rules').set({ text: S.cfg.rules, updatedAt: now, updatedBy: by });
    else if (k === 'review') await db.doc('config/review').set({ text: S.cfg.reviewRules, updatedAt: now, updatedBy: by });
    else if (k === 'export') await db.doc('config/export').set({ format: S.cfg.exportFormat, updatedAt: now, updatedBy: by });
    else {
      if (!tplInfo(k).ok) return toast('Исправьте JSON примера перед сохранением.', 'err');
      const tp = S.cfg.tpl[k];
      await db.doc('config/tpl_' + k).set({ idPrefix: tp.idPrefix, rules: tp.rules, example: tp.example, updatedAt: now, updatedBy: by });
    }
    const val = cfgValue(k);
    S.cfgTeam[k] = { updatedAt: now, value: typeof val === 'object' ? { ...val } : val };
    S.cfgDirty[k] = false; saveDrafts();
    renderCfgTabs(); renderCfgFoot();
    toast(`${cfgName(k)}: сохранено для команды`);
  } catch (e) {
    toast(e?.code === 'invalid_argument' ? 'Недостаточно прав, чтобы сохранить для команды.' : 'Не удалось сохранить. Попробуйте ещё раз.', 'err');
  }
}
function revertCfg(k) {
  if (ctxOwnsCfg()) return ctxRevertCfg(k);
  const team = S.cfgTeam[k];
  setCfgValue(k, team ? (typeof team.value === 'object' ? { ...team.value } : team.value) : cfgDefault(k));
  S.cfgDirty[k] = false; saveDrafts(); renderCfg();
  if (S.tab === 'export') renderTab();
}
function subscribeCfg() {
  S.caps.db.collection('config').onSnapshot((snap) => {
    const present = new Set();
    for (const d of snap.docs) {
      const data = d.data() || {};
      let k = null, value;
      if (d.id === 'rules') { k = 'rules'; value = String(data.text ?? ''); }
      else if (d.id === 'review') { k = 'review'; value = String(data.text ?? ''); }
      else if (d.id === 'export') {
        k = 'export';
        value = data.format != null ? String(data.format) : data.structure != null ? 'JSON со структурой:\n' + (typeof data.structure === 'string' ? data.structure : JSON.stringify(data.structure, null, 2)) : '';
      } else if (d.id.startsWith('tpl_') && TYPES.includes(d.id.slice(4))) {
        k = d.id.slice(4);
        value = { idPrefix: typeof data.idPrefix === 'string' ? data.idPrefix : DEFAULT_TPL[k].idPrefix, rules: String(data.rules ?? ''), example: typeof data.example === 'string' ? data.example : JSON.stringify(data.example ?? {}, null, 2) };
      }
      if (!k) continue;
      present.add(k);
      S.cfgTeam[k] = { updatedAt: data.updatedAt || Date.now(), value };
      if (ctxOwnsCfg()) { ctxTeamCfg(k, value); continue; } // действует источник контекста — версия команды в резерв
      if (!S.cfgDirty[k]) setCfgValue(k, typeof value === 'object' ? { ...value } : value);
      else if (JSON.stringify(cfgValue(k)) === JSON.stringify(value)) S.cfgDirty[k] = false;
    }
    for (const k of CFG_KEYS) if (!present.has(k) && S.cfgTeam[k]) { S.cfgTeam[k] = null; if (ctxOwnsCfg()) ctxTeamCfg(k, cfgDefault(k)); else if (!S.cfgDirty[k]) setCfgValue(k, cfgDefault(k)); }
    saveDrafts();
    if (isTyping($('#cfg-body'))) { renderCfgTabs(); renderCfgFoot(); } else renderCfg();
    if (S.tab === 'export') renderTab();
  }, () => { /* хранилище недоступно — работаем с локальными указаниями */ });
}

/* ---------- overlay editor (live-bound to the rail field) ---------- */
let ovKey = null;
function openEditor(which) {
  const rules = which === 'rules';
  const k = rules ? 'rules' : cfgKeyOfTab();
  const tpl = !rules && S.cfgTab === 'tpl';
  const src = rules ? '#cfg-rules' : { export: '#cfg-export', review: '#cfg-review' }[S.cfgTab] || '#cfg-example';
  ovKey = { k, src, tpl };
  $('#ov-title').textContent = tpl ? `Пример кейса ${TL[k]} (JSON)` : cfgName(k);
  const ta = $('#ov-text');
  ta.value = $(src).value;
  ta.className = tpl ? 'code' : '';
  $('#overlay').hidden = false;
  updateOvValid();
  ta.focus();
}
function updateOvValid() {
  const v = $('#ov-valid');
  if (!ovKey?.tpl) { v.textContent = ''; return; }
  const info = tplInfo(S.cfgType);
  v.className = 'valid ' + (info.ok ? 'ok' : 'bad');
  v.textContent = info.ok ? 'JSON корректен' : info.error;
}
function closeEditor() {
  if (!ovKey) return;
  const src = $(ovKey.src);
  $('#overlay').hidden = true; ovKey = null;
  src?.focus();
}

/* ================= tabs ================= */
const TABS = [['agent', 'Агент'], ['reqs', 'Требования'], ['questions', 'Вопросы'], ['draft', 'Черновик'], ['cases', 'Тест-кейсы'], ['checklist', 'Чек-лист'], ['review', 'Ревью'], ['export', 'Экспорт'], ['history', 'История']];
const validTab = () => { if (!TABS.some(([id]) => id === S.tab)) S.tab = 'agent'; };
function renderTabs() {
  validTab();
  $('#tabs').hidden = S.settings.mode === 'help' || S.settings.mode === 'trace';
  const r = S.run;
  const cnt = { reqs: r?.requirements.length, questions: r?.questions.length, cases: r ? r.cases.length : S.pc.loaded ? prodItems().length : S.prodIndex.cases.length, checklist: r ? checklistItems(r).length : 0, review: r?.findings ? r.findings.filter((f) => f.status === 'open').length : 0, draft: isDraft(r) ? r.cases.length : 0 };
  $('#tabs').innerHTML = TABS.map(([id, name]) => `<button class="tab" type="button" role="tab" id="tab-${id}" aria-selected="${S.tab === id}" data-tab="${id}">${name}${cnt[id] ? `<span class="cnt">${cnt[id]}</span>` : ''}</button>`).join('');
}
function renderTab() {
  const body = $('#tab-body');
  if (S.settings.mode === 'help') return renderHelp();
  if (S.settings.mode === 'trace') { body.innerHTML = traceTab(); return; }
  validTab();
  const fn = { agent: agentTab, reqs: reqsTab, questions: questionsTab, draft: draftTab, cases: casesTab, checklist: checklistTab, review: reviewTab, export: exportTab, history: historyTab }[S.tab];
  body.innerHTML = fn();
  if (S.tab === 'cases') { if (prodScope()) renderProdCases(); else { renderCaseList(); renderTmsBar(); } }
  S.pendingCasesRender = false;
}
function renderAll() { renderStatus(); renderProduct(); renderDocs(); renderRunControls(); renderTabs(); renderTab(); }
let rafPending = false;
function scheduleRender() {
  if (rafPending) return;
  rafPending = true;
  requestAnimationFrame(() => {
    rafPending = false;
    renderTabs(); renderRunControls();
    const typing = isTyping($('#tab-body'));
    if (S.tab === 'agent' || S.tab === 'reqs') renderTab();
    else if ((S.tab === 'questions' || S.tab === 'checklist' || S.tab === 'review' || S.tab === 'draft') && !typing && !S.clEdit && S.clGroupEdit == null) renderTab();
    else if (S.tab === 'cases' && S.pendingCasesRender) {
      if (!anyEditing() && !typing) renderTab();
      else if (document.activeElement?.id === 'case-q') { renderCaseList(); renderTmsBar(); S.pendingCasesRender = false; }
    }
  });
}
const elapsedOf = (r) => (r.finishedAt || Date.now()) - (r.taskStart || r.createdAt);
let ticker = null;
function startTicker() { stopTicker(); ticker = setInterval(() => { const el = $('#el-time'); if (el && S.run) el.textContent = fmtClock(elapsedOf(S.run)); renderRunControls(); }, 1000); }
function stopTicker() { clearInterval(ticker); ticker = null; }

/* ---------- agent tab ---------- */
function capsBanner() {
  if (!S.caps.ready || aiReady(S.settings.genAI)) return '';
  const t = parseAI(S.settings.genAI);
  return `<div class="banner warn" style="margin-bottom:16px"><div><b>Генерация сейчас недоступна.</b> ${esc(aiProblem(S.settings.genAI))}
    <span style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px"><button class="btn" type="button" data-act="open-conns">Настроить подключение</button>${inClaude && t?.kind === 'conn' ? '<button class="btn" type="button" data-act="standalone">Скачать автономную версию</button>' : ''}</span></div></div>`;
}
function agentTab() {
  const r = S.run;
  if (!r) {
    if (S.follow) return '<div class="banner info"><div><b>Генерация идёт в другой вкладке или на другом устройстве.</b> Прогресс появится здесь через несколько секунд.</div></div>';
    const m = S.settings.mode, upd = m === 'update';
    return capsBanner() + `<div class="intro">
      ${upd ? `<h3>Актуализация тест-кейсов под текущую версию ТЗ</h3>
      <p>Загрузите файл с существующими кейсами (.xlsx или .json — выгрузка из ТМС или экспорт QA pro) и актуальную документацию. Агент сверит каждый кейс с требованиями, исправит расходящиеся, допишет кейсы для непокрытых требований и пометит устаревшие. Каждый кейс получит статус и причину. Все кейсы переписываются по шаблонам API, UI и E2E, экспорт — по «Формату экспорта».</p>`
      : `<h3>Из ТЗ — в чек-лист и тест-кейсы по шаблонам команды</h3>
      <p>Загрузите требования, спецификации API или пользовательские истории. Агент выделит проверяемые требования и вопросы к документации, составит чек-лист и напишет тест-кейсы по шаблонам API, UI и E2E с отметками «Смоук» и «Регресс». Экспорт — в формате, который вы опишете словами.</p>`}
      <ol class="timeline">${stepsOf(m).filter((s) => !s.optional || (s.auto && S.productId)).map((s, i) => `<li class="st pending"><span class="dot">${i + 1}</span><div><div class="st-h"><h4>${stepTitle(s, m)}</h4></div><p class="st-d">${stepDesc(s, m)}</p></div></li>`).join('')}</ol>
      ${upd && S.upd.file?.status !== 'ready' ? '<div class="banner info"><div>Слева, в блоке «Тест-кейсы для актуализации», загрузите файл с кейсами — без него актуализацию не запустить.</div></div>' : S.docs.some((d) => d.sample) ? `<div class="banner info"><div>Слева загружен пример ТЗ на восстановление пароля. Нажмите «${upd ? 'Актуализировать' : 'Сгенерировать'}», чтобы посмотреть результат, или замените пример своими документами.</div></div>` : ''}
      ${kbIntroHTML()}
    </div>`;
  }
  const o = outputsOf(r), cl = checklistItems(r);
  const pct = coveragePct(r);
  const scope = r.requirements.filter((x) => x.inScope).length;
  const sm = r.cases.filter((c) => c.suites?.includes('smoke')).length, rg = r.cases.filter((c) => c.suites?.includes('regression')).length;
  const un = (k) => r.cases.filter((c) => c.status === k).length;
  let html = capsBanner() + `<div class="stats">
    ${stat('Требований', r.requirements.length, scope !== r.requirements.length ? `в работе ${scope}` : r.questions.length ? `вопросов к ТЗ: ${r.questions.length}` : '')}
    ${r.mode === 'update' ? stat('Кейсов в файле', r.srcCases.length, r.cases.length ? `без изменений ${un('same')} · изменено ${un('changed')}` : r.source?.name || '') + stat('Новых', un('new'), 'по непокрытым требованиям') + stat('Устарело', un('obsolete'), un('obsolete') ? 'помечены, не удалены' : '') : ''}
    ${o.checklist || cl.length ? stat('Чек-лист', cl.length, `смоук ${cl.filter((i) => i.suites.includes('smoke')).length} · регресс ${cl.filter((i) => i.suites.includes('regression')).length}`) : ''}
    ${r.mode !== 'update' && (o.cases || r.cases.length) ? stat('Тест-кейсов', r.cases.length, `смоук ${sm} · регресс ${rg}`) : ''}
    ${stat('Покрытие', pct == null ? '—' : pct + '%', o.cases ? 'требований с кейсами' : 'требований в чек-листе')}
    ${stat('Время', fmtClock(elapsedOf(r)), r.fromHistory ? fmtDate(r.createdAt) : aiLabel(r.settings.genAI || S.settings.genAI), r.finishedAt ? '' : 'el-time')}
    ${r.usage?.calls ? stat('Токены', '≈ ' + fmtTok(r.usage.in + r.usage.out), `${r.usage.calls} ${plural(r.usage.calls, 'запрос', 'запроса', 'запросов')} · ответы ${fmtTok(r.usage.out)}${r.usage.cached ? ` · из кэша ${fmtTok(r.usage.cached)}` : ''}`) : ''}
  </div>`;
  const btns = [r.cases.length ? '<button class="btn accent" type="button" data-act="go-tab" data-tab="cases">Открыть тест-кейсы</button>' : '', cl.length ? `<button class="btn${r.cases.length ? '' : ' accent'}" type="button" data-act="go-tab" data-tab="checklist">Открыть чек-лист</button>` : '', r.cases.length || cl.length ? '<button class="btn" type="button" data-act="go-tab" data-tab="review">Ревью</button>' : '', r.cases.length ? '<button class="btn" type="button" data-act="go-tab" data-tab="export">Экспорт</button>' : ''].join('');
  const openBtns = btns ? `<span style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">${btns}</span>` : '';
  const resumable = canResume(r);
  const pend = resumable && outputsOf(r).cases && stepComplete(r, 'plan') ? pendingParts(r, 'P-') + pendingParts(r, 'G-') : 0;
  const retry = resumable ? `<span style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px"><button class="btn accent" type="button" data-act="resume-run">Продолжить с места остановки${pend ? ` · ${pend} ${plural(pend, 'запрос', 'запроса', 'запросов')}` : ''}</button></span>` : '';
  const summary = `требований ${r.requirements.length}, тест-кейсов ${r.cases.length}, пунктов чек-листа ${cl.length}`;
  if (S.follow) html += '<div class="banner info" style="margin-bottom:16px"><div><b>Генерация идёт в другой вкладке или на другом устройстве.</b> Здесь прогресс обновляется автоматически каждые несколько секунд. Если та вкладка закроется, генерацию можно будет продолжить здесь.</div></div>';
  else if (r.status === 'interrupted') html += `<div class="banner warn" style="margin-bottom:16px"><div><b>${r.mode === 'update' ? 'Актуализация' : 'Генерация'} прервалась, когда страница была закрыта.</b> Всё сделанное сохранено: ${summary}. Агент продолжит с того же места — повторятся только незавершённые запросы.
    ${S.resume ? `<p style="margin-top:6px">Продолжу автоматически через <b id="resume-left">${S.resume.left}</b> с.</p>` : ''}
    <span style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px"><button class="btn accent" type="button" data-act="resume-run">Продолжить сейчас</button>${S.resume ? '<button class="btn" type="button" data-act="resume-cancel">Не продолжать</button>' : ''}</span></div></div>`;
  else if (r.status === 'stopped' && r.interrupted) {
    const t = (s0 => (s0 ? stepTitle(s0, r.mode) : 'Задача'))(STEPS.find((x) => x.id === r.interrupted));
    const act = r.interrupted === 'review' ? '<button class="btn accent" type="button" data-act="start-review">Запустить ревью заново</button>' : r.interrupted === 'knowledge' ? '<button class="btn accent" type="button" data-act="run-knowledge">Обновить знания о продукте</button>' : r.interrupted === 'answers' ? '<button class="btn accent" type="button" data-act="go-tab" data-tab="questions">К вопросам</button>' : '<button class="btn accent" type="button" data-act="go-tab" data-tab="review">К замечаниям</button>';
    html += `<div class="banner warn" style="margin-bottom:16px"><div><b>${esc(t)}: прервано, когда страница была закрыта.</b> Результаты до этого момента сохранены — запустите задачу заново.<span style="display:flex;gap:8px;flex-wrap:wrap;margin-top:8px">${act}</span></div></div>`;
  }
  if (S.follow || r.status === 'interrupted' || (r.status === 'stopped' && r.interrupted)) { /* баннер выше */ }
  else if (r.status === 'done') html += `<div class="banner info" style="margin-bottom:16px"><div><b>Готово.</b> ${r.fromHistory ? 'Запуск загружен из истории.' : 'Проверьте вопросы к документации, поправьте кейсы вручную или доработайте с ИИ, затем выгрузите.'}${openBtns}</div></div>`;
  else if (r.status === 'partial') html += `<div class="banner warn" style="margin-bottom:16px"><div><b>Готово с ошибками.</b> Часть запросов к модели не удалась — их можно повторить.${openBtns}${retry}</div></div>`;
  else if (r.status === 'stopped') html += `<div class="banner warn" style="margin-bottom:16px"><div><b>Остановлено.</b> Готовые результаты сохранены.${retry}${openBtns}</div></div>`;
  else if (r.status === 'error') html += `<div class="banner err" style="margin-bottom:16px"><div><b>Работа прервана.</b> ${esc(r.error || '')}${retry}${openBtns}</div></div>`;
  const steps = stepsOf(r.mode || 'generate').filter((s) => { const st = r.steps[s.id]; return r.fromHistory ? st.log.length > 0 : !(s.optional && st.status === 'pending'); });
  if (steps.length) {
    html += `<ol class="timeline">${steps.map((s, i) => {
      const st = r.steps[s.id];
      const dur = st.t0 && st.status !== 'skipped' ? fmtDur((st.t1 || Date.now()) - st.t0) : '';
      const sl = { pending: 'ожидает', running: 'выполняется', done: '', error: 'с ошибками', stopped: 'остановлено', skipped: st.note || 'пропущено' }[st.status];
      const dot = st.status === 'done' ? '✓' : st.status === 'error' ? '!' : st.status === 'running' ? '' : String(i + 1);
      return `<li class="st ${st.status}"><span class="dot">${dot}</span><div style="min-width:0"><div class="st-h"><h4>${stepTitle(s, r.mode)}</h4><span class="muted">${[sl, dur].filter(Boolean).join(' · ')}</span></div>${st.log.length ? `<ul class="log">${st.log.slice(-60).map((l) => `<li class="${l.kind}">${esc(l.text)}</li>`).join('')}</ul>` : st.status === 'pending' ? `<p class="st-d">${stepDesc(s, r.mode)}</p>` : ''}</div></li>`;
    }).join('')}</ol>`;
  }
  if (r.usage?.calls) {
    const by = Object.entries(r.usage.by || {}).sort((a, b) => (b[1].in + b[1].out) - (a[1].in + a[1].out));
    html += `<p class="hint usage-line">Расход по шагам (оценка): ${by.map(([k, u]) => `${STEP_RU[k] || k} ${fmtTok(u.in + u.out)}`).join(' · ')}${S.settings.economy ? ' · экономный режим' : ''}</p>`;
  }
  if (r.questions.length) {
    const pend = r.questions.filter((q) => qStatus(q) !== 'applied').length;
    html += `<div class="box q"><h4>Вопросы к документации · ${r.questions.length}</h4><ol>${r.questions.slice(0, 5).map((q) => `<li>${esc(q.text)}${qStatus(q) === 'applied' ? ' <span class="chip ok">учтён</span>' : ''}</li>`).join('')}</ol>${r.questions.length > 5 ? `<span class="small muted">и ещё ${r.questions.length - 5}</span>` : ''}
      <span><button class="btn" type="button" data-act="go-tab" data-tab="questions">${pend ? `Ответить на вопросы (${pend})` : 'Открыть вопросы'}</button></span></div>`;
  }
  return html;
}

/* ---------- requirements ---------- */
/* карточка требования: описание, критерии, покрытие тремя вариантами и правка */
function reqDetailHTML(r, q, cases) {
  const can = isDraft(r) && !draftLocked(r);
  const why = !isDraft(r) ? 'Кейсы этого запуска уже добавлены в проект: покрытие добавляет кейсы в черновик текущего запуска' : S.running ? 'Дождитесь окончания текущей работы' : 'Кейсы попадут в черновик — их можно проверить ревью';
  return `${q.description ? `<p>${esc(q.description)}</p>` : ''}
    ${q.criteria.length ? `<ul>${q.criteria.map((c) => `<li>${esc(c)}</li>`).join('')}</ul>` : ''}
    ${q.quote ? `<blockquote>${esc(q.quote)}</blockquote>` : ''}
    <div class="req-acts"><span class="lbl">Покрыть требование</span>
      <div class="case-acts">${Object.entries(COVER_VARIANTS).map(([k, v]) => `<button class="btn" type="button" data-act="cover-req" data-id="${q.id}" data-variant="${k}" ${can ? '' : 'disabled'} title="${esc(why)}">${esc(v.title)}</button>`).join('')}</div>
      <div class="case-acts"><button class="btn" type="button" data-act="req-edit" data-id="${q.id}" ${S.running ? 'disabled' : ''}>Редактировать требование</button></div>
    </div>
    ${cases.length ? `<div class="case-sub" style="margin-top:8px">${cases.map((c) => `<button class="btn" type="button" data-act="goto-case" data-uid="${c.uid}">${esc(c.dispId)}</button>`).join('')}</div>` : ''}`;
}
function reqEditHTML(q) {
  return `<div class="case-form req-form">
    <div class="field"><label class="lbl" for="req-ed-title">Название</label><input id="req-ed-title" type="text" value="${esc(q.title)}"></div>
    <div class="field"><label class="lbl" for="req-ed-desc">Описание</label><textarea id="req-ed-desc" rows="3">${esc(q.description || '')}</textarea></div>
    <div class="field"><label class="lbl" for="req-ed-crit">Критерии приёмки <span class="muted small">(каждый с новой строки)</span></label><textarea id="req-ed-crit" rows="5">${esc(q.criteria.join('\n'))}</textarea></div>
    <div class="cl-edit"><button class="btn accent" type="button" data-act="req-save" data-id="${q.id}">Сохранить</button><button class="btn" type="button" data-act="req-cancel">Отмена</button></div>
    <p class="hint">Уже созданные кейсы не меняются. Новое покрытие будет опираться на отредактированное требование.</p></div>`;
}
function reqsTab() {
  const r = S.run;
  if (!r || !r.requirements.length) return emptyHTML(S.running ? 'Агент анализирует документы…' : 'Требований пока нет', 'Они появятся после шага «Анализ требований».');
  const o = outputsOf(r), cl = checklistItems(r);
  const scope = r.requirements.filter((x) => x.inScope);
  const cov = scope.filter((x) => isCovered(r, x.id)).length;
  const rows = r.requirements.map((q) => {
    const cases = r.cases.filter((c) => c.requirementIds.includes(q.id));
    const items = cl.filter((i) => i.requirementIds.includes(q.id));
    const open = S.reqOpen.has(q.id);
    const chip = (n, what) => (n ? `<span class="chip ok" title="${what}">${n}</span>` : `<span class="chip no" title="${what}">${S.running ? '…' : 'нет'}</span>`);
    const ex = coveredByProduct(r, q.id);
    const covCell = !q.inScope ? '<span class="chip">вне выбора</span>' : `<span style="display:flex;gap:4px;flex-wrap:wrap">${ex && !cases.length ? `<span class="chip ok" title="Уже покрыто кейсами продукта: ${esc(ex.caseIds.join(', '))}">в продукте</span>` : o.cases || r.cases.length ? chip(cases.length, 'Тест-кейсы') : ''}${o.checklist || cl.length ? `<span class="small muted">ЧЛ</span>${chip(items.length, 'Пункты чек-листа')}` : ''}</span>`;
    return `<tr class="req-row" tabindex="0" data-act="toggle-req" data-id="${q.id}" aria-expanded="${open}">
      <td class="mono">${q.id}</td><td>${esc(q.title)}</td>
      <td><span style="display:flex;gap:4px;flex-wrap:wrap">${q.types.map((t) => `<span class="chip ${t}">${TL[t]}</span>`).join('') || '<span class="muted">—</span>'}</span></td>
      <td><span class="chip ${prioClass(q.priority)}">${prioRu(q.priority)}</span></td>
      <td class="small muted">${esc(q.doc)}${q.section ? ' · ' + esc(q.section) : ''}</td><td>${covCell}</td></tr>
      ${open ? `<tr class="req-detail"><td></td><td colspan="5">${S.reqEdit === q.id ? reqEditHTML(q) : reqDetailHTML(r, q, cases)}</td></tr>` : ''}`;
  }).join('');
  return `<div class="sec-h"><h3>${r.requirements.length} ${plural(r.requirements.length, 'требование', 'требования', 'требований')}</h3><span class="muted small">покрыто ${cov} из ${scope.length}</span></div>
    <div class="tbl-wrap"><table><thead><tr><th>ID</th><th>Требование</th><th>Вид</th><th>Приоритет</th><th>Источник</th><th>Покрытие</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}

/* ---------- questions ---------- */
function qChip(q) {
  const st = qStatus(q);
  return st === 'applied' ? '<span class="chip ok">учтён</span>' : st === 'pending' ? '<span class="chip p-medium">не учтён</span>' : '<span class="chip">нет ответа</span>';
}
function qTarget(r) {
  const c = outputsOf(r).cases || r.cases.length;
  return c ? (r.checklist ? 'тест-кейсах и чек-листе' : 'тест-кейсах') : 'чек-листе';
}
function qActionsHTML(r) {
  const n = r.questions.filter((q) => qStatus(q) === 'pending').length;
  if (S.running && r.steps.answers.status === 'running') return '<span class="hint">Агент учитывает ответы — ход работы ниже.</span><button class="btn" type="button" data-act="stop">Остановить</button>';
  const can = n && !S.running && aiReady(r.settings.genAI || S.settings.genAI) && (r.cases.length || r.checklist);
  return `<button class="btn accent" type="button" data-act="apply-answers" ${can ? '' : 'disabled'}>Учесть ответы в ${qTarget(r)}${n ? ` (${n})` : ''}</button>
    <span class="hint">Агент найдёт кейсы, которые затрагивают ответы, исправит их и допишет недостающие проверки. Ответы также учитываются при доработке кейсов и следующих генерациях в этом запуске.</span>`;
}
function questionsTab() {
  const r = S.run;
  if (!r || !r.requirements.length) return emptyHTML('Вопросов пока нет', 'Они появятся после шага «Анализ требований».');
  if (!r.questions.length) return emptyHTML('Вопросов к документации нет', 'Агент не нашёл неясностей и противоречий в документах.');
  const log = r.steps.answers.log;
  const open = r.questions.filter((q) => qStatus(q) === 'none').length;
  return `<div class="sec-h"><h3>Вопросы к документации · ${r.questions.length}</h3><span class="muted small">ответьте сами или вставьте ответ аналитика</span>
      <span class="sp q-export">${S.caps.downloads ? '<button class="btn" type="button" data-act="q-xlsx" title="Таблица для аналитика: ID, вопрос, ответ, статус. Аналитик заполняет колонку «Ответ» — загрузите файл обратно">Скачать .xlsx</button><button class="btn" type="button" data-act="q-md">Скачать .md</button>' : ''}<button class="btn" type="button" data-act="q-letter" title="${open ? `Письмо с ${open} ${plural(open, 'вопросом', 'вопросами', 'вопросами')} без ответа` : 'Все вопросы уже с ответами'}">Скопировать письмо</button><button class="btn" type="button" data-act="q-import" ${S.running ? 'disabled' : ''} title="Ответы из .xlsx, выгруженного отсюда: колонки «ID» и «Ответ»">Загрузить ответы</button><input type="file" id="q-file" accept=".xlsx,.xls,.csv" hidden></span></div>
    <div class="q-list">${r.questions.map((q) => `<div class="q-item ${qStatus(q)}" id="q-${q.id}">
      <div class="q-h"><span class="mono">${q.id}</span><p>${esc(q.text)}</p><span id="qst-${q.id}">${qChip(q)}</span></div>
      <textarea rows="2" data-q="${q.id}" placeholder="Ответ аналитика или решение команды" aria-label="Ответ на вопрос ${q.id}" ${S.running ? 'disabled' : ''}>${esc(q.answer)}</textarea>
    </div>`).join('')}</div>
    <div class="q-actions" id="q-actions">${qActionsHTML(r)}</div>
    ${log.length ? `<ul class="log" style="margin-top:12px">${log.slice(-40).map((l) => `<li class="${l.kind}">${esc(l.text)}</li>`).join('')}</ul>` : ''}`;
}

/* выгрузка вопросов аналитику и загрузка ответов из той же таблицы */
const Q_ST_RU = { none: 'Нет ответа', pending: 'Ответ не учтён', applied: 'Учтён' };
function qDocs(r) { return (r.docs || []).map((d) => d.name).join(', ') || 'документации'; }
function questionsExport(r) {
  return { kind: 'xlsx', sheet: 'Вопросы', filename: `questions_${new Date(r.createdAt).toISOString().slice(0, 10)}`, columns: ['ID', 'Вопрос', 'Ответ', 'Статус', 'Документы'],
    rows: r.questions.map((q) => [q.id, q.text, q.answer || '', Q_ST_RU[qStatus(q)], qDocs(r)]) };
}
function questionsMarkdown(r) {
  return [`# Вопросы к документации`, '', `Документы: ${qDocs(r)}`, `Продукт: ${curProduct()?.name || '—'}`, '',
    ...r.questions.map((q) => `## ${q.id}\n\n${q.text}\n\n**Ответ:** ${q.answer?.trim() || '_нет ответа_'}\n`)].join('\n');
}
function questionsLetter(r) {
  const list = r.questions.filter((q) => qStatus(q) === 'none');
  const qs = list.length ? list : r.questions;
  return ['Добрый день!', '', `При подготовке тест-кейсов по документации (${qDocs(r)}) возникли вопросы. Ответы нужны, чтобы зафиксировать ожидаемые результаты.`, '',
    ...qs.map((q, i) => `${i + 1}. [${q.id}] ${q.text}`), '', 'Ответить можно в этом письме или в приложенной таблице (колонка «Ответ»).', '', 'Спасибо!'].join('\n');
}
async function importAnswers(file) {
  const r = S.run;
  if (!r) return;
  let rows = [];
  try {
    await lib('xlsx');
    const wb = window.XLSX.read(await file.arrayBuffer(), { type: 'array' });
    rows = window.XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, defval: '' });
  } catch { return toast('Не удалось прочитать файл. Нужен .xlsx, выгруженный из вкладки «Вопросы».', 'err'); }
  const head = (rows[0] || []).map((x) => String(x).trim().toLowerCase());
  const iId = head.findIndex((h) => h === 'id' || h === '№' || h === 'ид'), iAns = head.findIndex((h) => /^ответ/.test(h)), iQ = head.findIndex((h) => /^вопрос/.test(h));
  if (iAns < 0 || (iId < 0 && iQ < 0)) return toast('В файле нет колонок «ID» и «Ответ».', 'err');
  let n = 0;
  for (const row of rows.slice(1)) {
    const ans = String(row[iAns] ?? '').trim();
    if (!ans) continue;
    const id = iId >= 0 ? String(row[iId] ?? '').trim() : '', text = iQ >= 0 ? String(row[iQ] ?? '').trim() : '';
    const q = r.questions.find((x) => (id && x.id === id) || (!id && text && x.text.trim() === text));
    if (q && (q.answer || '').trim() !== ans) { q.answer = ans; n++; }
  }
  if (!n) return toast('Новых ответов в файле нет.');
  queueSave(r, 0); renderTab(); renderTabs();
  toast(`Загружено ответов: ${n}. Нажмите «Учесть ответы», чтобы агент поправил затронутые кейсы.`);
}

/* ---------- cases ---------- */
function casesTab() {
  const r = S.run;
  if (S.run) ensureProdCases();
  if (prodScope()) return scopeSwitch() + prodCasesTab();
  const addBtns = (r) => `<span class="add-case"><span class="small muted">Добавить вручную:</span>${(r.settings.types || TYPES).map((t) => `<button class="btn sm" type="button" data-act="add-case" data-t="${t}">+ ${TL[t]}</button>`).join('')}</span>`;
  if (!r || !r.cases.length) {
    const off = r && !outputsOf(r).cases;
    return scopeSwitch() + emptyHTML(S.running && !off ? 'Кейсы появятся по мере генерации' : 'Тест-кейсов пока нет', off ? 'В этом запуске генерировался только чек-лист. Включите «Тест-кейсы» в параметрах и запустите снова — или добавьте кейсы вручную.' : S.running ? 'Следите за ходом работы на вкладке «Агент».' : 'Загрузите документы и запустите генерацию.', r && !S.running ? `<span style="margin-top:8px">${addBtns(r)}</span>` : '');
  }
  const n = (t) => r.cases.filter((c) => t === 'all' || c.type === t).length;
  const ns = (s) => r.cases.filter((c) => c.suites?.includes(s)).length;
  const chips = ['all', ...TYPES].filter((t) => t === 'all' || n(t)).map((t) => `<button class="fchip" type="button" data-act="ftype" data-t="${t}" aria-pressed="${S.filter.type === t}">${t === 'all' ? 'Все' : TL[t]}<span class="n">${n(t)}</span></button>`).join('');
  const schips = SUITES.map((s) => `<button class="fchip" type="button" data-act="fsuite" data-s="${s}" aria-pressed="${S.filter.suite === s}">${SUITE_RU[s]}<span class="n">${ns(s)}</span></button>`).join('');
  const nst = (k) => r.cases.filter((c) => c.status === k).length;
  const stchips = r.mode === 'update' ? `<span class="fsep" aria-hidden="true"></span>${Object.keys(UPD_ST).filter((k) => nst(k)).map((k) => `<button class="fchip" type="button" data-act="fstatus" data-s="${k}" aria-pressed="${S.filter.status === k}"><i class="st-dot st-${k}" aria-hidden="true"></i>${UPD_ST[k]}<span class="n">${nst(k)}</span></button>`).join('')}` : '';
  const draftNote = isDraft(r) ? `<div class="banner info" style="margin-bottom:10px"><div>Кейсы в черновике — ещё не в проекте. Проверка ревьюером, исправления и добавление в проект — во вкладке <button class="link" type="button" data-act="go-tab" data-tab="draft">«Черновик»</button>.</div></div>` : '';
  return scopeSwitch() + draftNote + `${r.mode === 'update' ? `<p class="hint" style="margin-bottom:10px">Актуализация «${esc(r.source?.name || 'файл')}»: ${r.srcCases.length} ${plural(r.srcCases.length, 'кейс', 'кейса', 'кейсов')} из файла переписаны по шаблонам команды. Откройте кейс, чтобы увидеть причину статуса, изменения и исходный вариант.</p>` : ''}<div class="toolbar">${chips}<span class="fsep" aria-hidden="true"></span>${schips}${stchips}<input type="text" id="case-q" placeholder="Поиск по кейсам" value="${esc(S.filter.q)}" aria-label="Поиск по кейсам">
    <span style="margin-left:auto;display:flex;gap:6px;flex-wrap:wrap">${canResume(r) ? '<button class="btn accent" type="button" data-act="resume-run">Продолжить генерацию</button>' : ''}<button class="btn" type="button" data-act="expand-all">Развернуть все</button><button class="btn" type="button" data-act="collapse-all">Свернуть</button></span></div>
    <div class="sel-bar" id="case-selbar"></div>
    <div class="cases" id="case-list"></div>
    <div class="cases-foot">${addBtns(r)}</div>
    <div class="tms-bar" id="tms-bar"></div>`;
}
/* ---------- разделы: тест-кейсы по документам ---------- */
// кейсы продукта показываются, когда запуск не открыт (например, сразу после загрузки продукта) или выбрана область «Весь продукт»
const prodScope = () => !!S.productId && !!S.caps.db && (S.run ? S.casesScope === 'product' && prodItems().length > 0 : !(S.pc.loaded && !prodItems().length));
function scopeSwitchHTML() {
  if (!S.run || !S.pc.loaded || !prodItems().length) return '';
  const on = prodScope() ? 'product' : 'run';
  const b = (id, name, n) => `<button class="fchip" type="button" data-act="cases-scope" data-s="${id}" aria-pressed="${on === id}">${name}<span class="n">${n}</span></button>`;
  return `<div class="toolbar scope-sw" role="group" aria-label="Какие кейсы показывать">${b('run', 'Этот запуск', S.run.cases.length)}${b('product', 'Весь продукт', prodItems().length)}</div>`;
}
const scopeSwitch = () => `<div id="scope-sw">${scopeSwitchHTML()}</div>`;
const renderScopeSwitch = () => { const el = $('#scope-sw'); if (el) el.innerHTML = scopeSwitchHTML(); };
function afterProdCases() {   // запуски продукта прочитаны: обновить число на вкладке, переключатель и список
  renderTabs();
  if (S.tab !== 'cases') return;
  if (!S.run && S.pc.loaded && !prodItems().length) return renderTab();   // кейсов нет — обычная пустая вкладка
  if (prodScope()) { if (isTyping($('#tab-body')) || S.secEdit) renderProdCases(); else renderTab(); } else renderScopeSwitch();   // вкладку целиком — чтобы обновились числа у фильтров
}
function sectionsHTML(items) {   // items: [{ doc, html }] — разделы по документу, внутри — карточки кейсов
  const groups = new Map();
  for (const it of items) { const k = secKey(it.doc); if (!groups.has(k)) groups.set(k, { key: k, doc: it.doc, rows: [] }); groups.get(k).rows.push(it.html); }
  const ord = (prodScope() ? S.docs : S.run?.docs || S.docs || []).map((d) => secKey(d.name));
  const list = [...groups.values()].sort((a, b) => (a.doc ? 0 : 1) - (b.doc ? 0 : 1) || (ord.indexOf(a.key) + 1 || 1e6) - (ord.indexOf(b.key) + 1 || 1e6));
  return list.map((g) => {
    const name = secName(g.doc), ed = S.secEdit?.key === g.key;
    const head = ed
      ? `<div class="sec-edit"><input type="text" id="sec-in" value="${esc(S.secEdit.value)}" maxlength="120" aria-label="Название раздела" autocomplete="off"><button class="btn sm accent" type="button" data-act="sec-save">Сохранить</button><button class="btn sm" type="button" data-act="sec-cancel">Отмена</button>${name !== secDefault(g.doc) ? '<button class="btn sm" type="button" data-act="sec-reset">Как документ</button>' : ''}</div>`
      : `<h3 class="sec-t">${esc(name)}</h3><span class="sec-n" title="Кейсов в разделе">${g.rows.length}</span>${g.doc && name !== secDefault(g.doc) ? `<span class="sec-d small muted" title="Документ">${esc(g.doc)}</span>` : ''}<button class="icon-btn sec-ed" type="button" data-act="sec-rename" data-key="${esc(g.key)}" data-doc="${esc(g.doc)}" title="Изменить название раздела" aria-label="Изменить название раздела «${esc(name)}»">${ICON.pen}</button>`;
    return `<section class="sec" aria-label="${esc(name)}"><header class="sec-h">${head}</header><div class="cases">${g.rows.join('')}</div></section>`;
  }).join('');
}
function prodCasesTab() {
  const all = prodItems(), n = (t) => all.filter((x) => t === 'all' || x.t === t).length;
  const chips = ['all', ...TYPES].filter((t) => t === 'all' || n(t)).map((t) => `<button class="fchip" type="button" data-act="pc-type" data-t="${t}" aria-pressed="${S.pc.type === t}">${t === 'all' ? 'Все' : TL[t]}<span class="n">${n(t)}</span></button>`).join('');
  return `<p class="hint" style="margin-bottom:10px">Тест-кейсы продукта «${esc(curProduct()?.name || '')}» из всех его запусков, включая черновики, — по документам, из которых они написаны. Название раздела можно изменить: нажмите на карандаш. Чтобы открыть кейс целиком, нажмите на него.</p>
    <div class="toolbar">${chips}<button class="btn sm danger" type="button" data-act="pc-del-all" ${S.running || !all.length ? 'disabled' : ''}>Удалить все кейсы (${all.length})</button><input type="text" id="pc-q" placeholder="Поиск по кейсам" value="${esc(S.pc.q)}" aria-label="Поиск по кейсам продукта"></div>
    <div class="sections" id="pcase-list"></div>`;
}
const prodCaseRow = (x) => `<article class="case"><div class="case-h pc-row" role="button" tabindex="0" data-act="pc-open" data-r="${esc(x.r)}" data-i="${esc(x.i)}" title="Открыть кейс">
  <span class="case-id t-${x.t}">${esc(x.i)}</span><div style="min-width:0"><div class="case-t${x.obs ? ' obs' : ''}">${esc(x.n)}</div>${x.draft || x.obs ? `<div class="case-sub">${x.draft ? '<span class="chip">Черновик</span>' : ''}${x.obs ? '<span class="chip">Устарел</span>' : ''}</div>` : ''}</div><span class="muted" style="transform:rotate(-90deg);display:grid">${ICON.chev}</span></div></article>`;
function renderProdCases() {
  const el = $('#pcase-list');
  if (!el) return;
  ensureProdCases();
  if (!S.pc.loaded) { el.innerHTML = '<p class="hint">Загружаю тест-кейсы продукта…</p>'; return; }
  const q = S.pc.q.trim().toLowerCase();
  const list = prodItems().filter((x) => (S.pc.type === 'all' || x.t === S.pc.type) && (!q || x.i.toLowerCase().includes(q) || x.n.toLowerCase().includes(q)));
  el.innerHTML = (S.pc.error ? `<p class="hint">${esc(S.pc.error)}</p>` : '') + (list.length ? sectionsHTML(list.map((x) => ({ doc: x.doc, html: prodCaseRow(x) }))) : emptyHTML('Ничего не найдено', 'Измените фильтр или запрос.'));
  if (S.secEdit) { const inp = $('#sec-in'); if (inp && document.activeElement !== inp) { inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); } }
}
function filteredCases() {
  const r = S.run, q = S.filter.q.trim().toLowerCase();
  const st = S.filter.status || 'all';
  return r.cases.filter((c) => (S.filter.type === 'all' || c.type === S.filter.type) && (S.filter.suite === 'all' || c.suites?.includes(S.filter.suite)) && (st === 'all' || c.status === st)
    && (!q || c.dispId.toLowerCase().includes(q) || JSON.stringify(c.testCase).toLowerCase().includes(q)));
}
function renderCaseList() {
  const el = $('#case-list');
  if (!el || !S.run) return;
  const list = filteredCases();
  el.innerHTML = list.length ? sectionsHTML(list.map((c) => ({ doc: docOfCase(S.run, c), html: caseHTML(c) }))) : emptyHTML('Ничего не найдено', 'Измените фильтр или запрос.');
  if (S.secEdit) { const inp = $('#sec-in'); if (inp && document.activeElement !== inp) { inp.focus(); inp.setSelectionRange(inp.value.length, inp.value.length); } }
  const bar = $('#case-selbar');
  if (bar) bar.innerHTML = selBarHTML(list, 'cases');
}
/* выбор кейсов флажками: удалить выбранные — во вкладках «Тест-кейсы» и «Черновик» */
const selLocked = () => !S.run || S.running || S.run.fromHistory === 'readonly' || S.run.fromHistory === 'follow';
function selPrune() { if (!S.run) { S.caseSel.clear(); return; } const ids = new Set(S.run.cases.map((c) => c.uid)); for (const u of [...S.caseSel]) if (!ids.has(u)) S.caseSel.delete(u); }
function selBarHTML(list, where) {
  selPrune();
  if (!list.length) return '';
  const n = list.filter((c) => S.caseSel.has(c.uid)).length, all = n === list.length, lock = selLocked();
  return `<label class="sel-all"><input type="checkbox" class="sel-all-cb" data-where="${where}" ${all ? 'checked' : ''} ${lock ? 'disabled' : ''} aria-label="Выбрать все кейсы в списке">${n ? `Выбрано ${n} из ${list.length}` : `Выбрать все (${list.length})`}</label>
    ${n ? `<button class="btn sm danger" type="button" data-act="sel-del" data-where="${where}" ${lock ? 'disabled' : ''}>Удалить выбранные (${n})</button><button class="link" type="button" data-act="sel-none">Снять выбор</button>` : ''}`;
}
const selCB = (c) => `<input type="checkbox" class="case-sel" data-uid="${c.uid}" ${S.caseSel.has(c.uid) ? 'checked' : ''} ${selLocked() ? 'disabled' : ''} aria-label="Выбрать кейс ${esc(c.dispId)}">`;
function deleteSelected(where) {
  const r = S.run;
  if (!r || selLocked()) return;
  const del = r.cases.filter((c) => S.caseSel.has(c.uid));
  if (!del.length) return;
  const ids = new Set(del.map((c) => c.dispId));
  r.cases = r.cases.filter((c) => !S.caseSel.has(c.uid));
  if (r.findings) r.findings = r.findings.filter((f) => !(f.kind === 'case' && ids.has(f.targetId)));
  for (const c of del) S.caseUI.delete(c.uid);
  S.caseSel.clear();
  queueSave(r); if (!isDraft(r)) productSync(r); // кейсы уходят и из индекса продукта
  renderTabs(); renderTab();
  const one = del.length === 1;
  toast(`${one ? `Кейс ${del[0].dispId} удалён` : `Удалено ${del.length} ${plural(del.length, 'кейс', 'кейса', 'кейсов')}`}${isDraft(r) ? ' из черновика' : r.productId ? ` — в продукте ${one ? 'его' : 'их'} больше нет` : ''}`);
}
function caseHTML(c) {
  const ui = caseUI(c.uid), tc = c.testCase || {};
  const t = pickTitle(tc), prio = prioOf(tc);
  const info = tplInfo(c.type);
  const skip = [t.key, info.ok ? info.idField : null].filter(Boolean);
  const missing = info.ok ? info.fields.filter((f) => !(f in tc)) : [];
  const fds = openFindingsFor(S.run, 'case', c.dispId).sort((a, b) => ['critical', 'major', 'minor'].indexOf(a.severity) - ['critical', 'major', 'minor'].indexOf(b.severity));
  let body = '';
  if (ui.open) {
    if (ui.mode === 'form') body = caseFormHTML(c, ui);
    else if (ui.mode === 'edit') {
      body = `<div class="case-edit"><label class="lbl" for="ed-${c.uid}">JSON тест-кейса</label>
        <textarea class="code" id="ed-${c.uid}" rows="18" data-uid="${c.uid}" data-field="draft" spellcheck="false">${esc(ui.draft)}</textarea>
        ${ui.error ? `<p class="case-note err">${esc(ui.error)}</p>` : ''}
        <div class="case-acts"><button class="btn accent" type="button" data-act="save-edit" data-uid="${c.uid}">Сохранить</button><button class="btn" type="button" data-act="cancel-mode" data-uid="${c.uid}">Отмена</button></div></div>`;
    } else if (ui.mode === 'refine') {
      body = `<div class="case-edit"><label class="lbl" for="rf-${c.uid}">Что исправить</label>
        <textarea id="rf-${c.uid}" rows="3" data-uid="${c.uid}" data-field="comment" placeholder="Например: добавь проверку логов, разбей шаг 3 на два, укажи код ошибки из п. 3.1" ${ui.busy ? 'disabled' : ''}>${esc(ui.comment)}</textarea>
        ${ui.error ? `<p class="case-note err">${esc(ui.error)}</p>` : ''}
        <div class="case-acts">${ui.busy ? `<span class="case-note muted">Модель дорабатывает кейс…</span><button class="btn" type="button" data-act="stop-refine" data-uid="${c.uid}">Остановить</button>`
          : `<button class="btn accent" type="button" data-act="do-refine" data-uid="${c.uid}">Доработать</button><button class="btn" type="button" data-act="cancel-mode" data-uid="${c.uid}">Отмена</button>`}</div></div>`;
    } else {
      body = updBlockHTML(c, ui) + `<div class="suites-row">Наборы: ${suiteToggles(c.suites, 'case-suite', `data-uid="${c.uid}"`)}</div>` + (fds.length ? `<div class="fd-inline">${fds.map((f) => `<p><span class="chip sev-${f.severity}">${SEV_RU[f.severity]}</span> ${esc(f.message)}</p>`).join('')}</div>` : '') + kvHTML(cleanCase(tc), 1, skip) + (ui.note ? `<p class="case-note muted">${esc(ui.note)}</p>` : '') +
        `<div class="case-acts">
          <button class="btn" type="button" data-act="form-case" data-uid="${c.uid}">Редактировать</button>
          <button class="btn" type="button" data-act="refine-case" data-uid="${c.uid}">Доработать с ИИ</button>
          <button class="btn" type="button" data-act="edit-case" data-uid="${c.uid}">Изменить JSON</button>
          <button class="btn" type="button" data-act="copy-case" data-uid="${c.uid}">Копировать JSON</button>
          ${ui.prev ? `<button class="btn" type="button" data-act="undo-case" data-uid="${c.uid}">Вернуть прежний вариант</button>` : ''}
          ${c.status && c.status !== 'new' ? `<button class="btn" type="button" data-act="case-obsolete" data-uid="${c.uid}">${c.status === 'obsolete' ? 'Вернуть в актуальные' : 'Пометить устаревшим'}</button>` : ''}
          <button class="btn danger" type="button" data-act="del-case" data-uid="${c.uid}">Удалить</button>
        </div>`;
    }
  }
  return `<article class="case" id="case-${c.uid}">
    <div class="case-h sel" role="button" tabindex="0" aria-expanded="${ui.open}" data-act="toggle-case" data-uid="${c.uid}">
      ${selCB(c)}<span class="case-id t-${c.type}">${esc(c.dispId)}</span>
      <div style="min-width:0"><div class="case-t${c.status === 'obsolete' ? ' obs' : ''}">${esc(t.text)}</div>
        <div class="case-sub">${c.status ? `<span class="chip ust-${c.status}" title="${esc(c.note || '')}">${UPD_ST[c.status]}</span>` : ''}${String(c.dispId || '').toUpperCase().startsWith(TL[c.type].toUpperCase()) ? '' : `<span class="chip ${c.type}">${TL[c.type]}</span>`}${suiteChips(c.suites)}${prio != null ? `<span class="chip ${prioClass(prio)}">${esc(prio)}</span>` : ''}${c.requirementIds.map((id) => `<span class="rq">${esc(id)}</span>`).join('')}${c.checklistId ? `<button class="chip cl-link" type="button" data-act="go-cl" data-id="${esc(c.checklistId)}" title="Кейс написан по пункту чек-листа">${esc(c.checklistId)}</button>` : ''}${missing.length ? `<span class="chip p-medium" title="Поля шаблона, которых нет в кейсе">нет полей: ${esc(missing.join(', '))}</span>` : ''}${fds.length ? `<span class="chip fd-chip sev-${fds[0].severity}" title="Открытые замечания ревьюера">замечаний: ${fds.length}</span>` : ''}${c.tms ? `<span class="chip ok" title="Загружен в ТМС">в ТМС${c.tms.id ? ' · ' + esc(c.tms.id) : ''}</span>` : ''}${c.manual ? '<span class="chip">вручную</span>' : ''}</div></div>
      <span class="muted" style="transform:rotate(${ui.open ? 180 : 0}deg);display:grid">${ICON.chev}</span>
    </div>
    ${ui.open ? `<div class="case-b">${body}</div>` : ''}
  </article>`;
}

function updBlockHTML(c, ui) {
  if (!c.status) return '';
  const src = c.srcIdx != null ? S.run.srcCases.find((x) => x.index === c.srcIdx) : null;
  return `<div class="upd-box ust-${c.status}"><div class="upd-h"><b>${UPD_ST[c.status]}</b>${c.sourceId ? `<span class="muted small">ID в файле: <span class="mono">${esc(c.sourceId)}</span></span>` : src ? `<span class="muted small">кейс №${src.index} в файле</span>` : ''}</div>
    ${c.note ? `<p>${esc(c.note)}</p>` : ''}
    ${c.changes?.length ? `<ul>${c.changes.map((x) => `<li>${esc(x)}</li>`).join('')}</ul>` : ''}
    ${src ? `<button class="link" type="button" data-act="toggle-src" data-uid="${c.uid}">${ui.showSrc ? 'Скрыть исходный кейс' : 'Показать исходный кейс из файла'}</button>${ui.showSrc ? `<pre class="inl-code">${esc(JSON.stringify(src.raw, null, 2))}</pre>` : ''}` : ''}</div>`;
}

/* ---------- checklist ---------- */
/* Выгрузка чек-листа — таблица: одна строка — одна проверка. Компонент: E2E — сквозные, FE — интерфейс, BE — API. */
const CL_COMPONENT = { e2e: 'E2E', ui: 'FE', api: 'BE' };
const CL_COLS = ['№', 'Название', 'Приоритет', 'Компонент', 'Ожидаемый результат'];
const checklistRows = (r) => checklistItems(r).filter((i) => i.check).map((i, k) => [String(k + 1), i.check, (PRIO_RU[normPrio(i.priority)] || 'Средний').toLowerCase(), CL_COMPONENT[i.type] || 'FE', i.expected || '']);
const clFileName = (r, ext) => `checklist_${new Date(r.createdAt).toISOString().slice(0, 10)}.${ext}`;
function checklistMarkdown(r) {
  const cell = (x) => String(x).replace(/\|/g, '\\|').replace(/\s*\n\s*/g, ' ');
  return ['# Чек-лист', '', `| ${CL_COLS.join(' | ')} |`, `|${CL_COLS.map((c, k) => (k === 0 ? '---:' : '---')).join('|')}|`, ...checklistRows(r).map((row) => `| ${row.map(cell).join(' | ')} |`), ''].join('\n');
}
const checklistJSON = (r) => ({ generatedAt: new Date(r.createdAt).toISOString(), sources: r.docs.map((d) => d.name), groups: r.checklist.groups.filter((g) => g.items.length).map((g) => ({ title: g.title, items: g.items.map((i) => ({ id: i.id, check: i.check, expected: i.expected || '', kind: i.kind || 'positive', type: i.type, component: CL_COMPONENT[i.type] || 'FE', priority: i.priority, suites: i.suites, requirementIds: i.requirementIds })) })) });
async function checklistXlsx(r) {
  try {
    await lib('xlsx');
    const X = window.XLSX, ws = X.utils.aoa_to_sheet([CL_COLS, ...checklistRows(r).map((row) => [Number(row[0]), ...row.slice(1)])]), wb = X.utils.book_new();
    ws['!cols'] = [{ wch: 5 }, { wch: 60 }, { wch: 12 }, { wch: 11 }, { wch: 70 }];
    X.utils.book_append_sheet(wb, ws, 'Чек-лист');
    return downloadFile(clFileName(r, 'xlsx'), new Blob([X.write(wb, { type: 'array', bookType: 'xlsx' })]));
  } catch { return toast('Не удалось сформировать Excel-файл.', 'err'); }
}
const CL_PRIO_FILL = { критический: '#fde2e1', высокий: '#feefd9', средний: '#fdf8d8', низкий: '#eef1f4' };
function checklistPdfDoc(r) {
  const rows = checklistRows(r), d = new Date(r.createdAt);
  const src = (r.docs || []).map((x) => x.name).filter(Boolean);
  const head = CL_COLS.map((t) => ({ text: t, style: 'th' }));
  return {
    pageSize: 'A4', pageOrientation: 'landscape', pageMargins: [28, 32, 28, 34],
    info: { title: 'Чек-лист', creator: 'QA pro' },
    defaultStyle: { font: 'Roboto', fontSize: 9, lineHeight: 1.15 },
    styles: { h: { fontSize: 15, bold: true, margin: [0, 0, 0, 2] }, sub: { fontSize: 8.5, color: '#5b6470', margin: [0, 0, 0, 10] }, th: { bold: true, color: '#ffffff', fillColor: '#2f3a48', margin: [2, 3, 2, 3] } },
    footer: (cur, all) => ({ text: `${cur} / ${all}`, alignment: 'right', fontSize: 8, color: '#8a929c', margin: [0, 8, 28, 0] }),
    content: [
      { text: 'Чек-лист', style: 'h' },
      { text: [`${d.toLocaleDateString('ru-RU')} · проверок: ${rows.length}`, src.length ? ` · документы: ${src.slice(0, 5).join(', ')}${src.length > 5 ? ` и ещё ${src.length - 5}` : ''}` : ''].join(''), style: 'sub' },
      { table: { headerRows: 1, dontBreakRows: true, widths: [22, '*', 62, 58, '*'],
        body: [head, ...rows.map((row) => [{ text: row[0], alignment: 'right' }, row[1], { text: row[2], fillColor: CL_PRIO_FILL[row[2]] }, { text: row[3], alignment: 'center' }, row[4] || { text: '—', color: '#8a929c' }])] },
        layout: { hLineWidth: () => 0.5, vLineWidth: () => 0.5, hLineColor: () => '#c9ced6', vLineColor: () => '#c9ced6', paddingLeft: () => 4, paddingRight: () => 4, paddingTop: () => 3, paddingBottom: () => 3 } },
    ],
  };
}
async function checklistPdfBlob(r) {
  await lib('pdfmake');
  await lib('pdfmakeFonts');
  const pm = window.pdfMake;
  if (!pm?.createPdf) throw new Error('pdfmake');
  return new Promise((resolve, reject) => { try { pm.createPdf(checklistPdfDoc(r)).getBlob((b) => resolve(b)); } catch (e) { reject(e); } });
}
async function checklistPdf(r) {
  try { return downloadFile(clFileName(r, 'pdf'), await checklistPdfBlob(r)); }
  catch { return toast('Не удалось сформировать PDF-файл. Проверьте подключение и попробуйте снова.', 'err'); }
}
function checklistTab() {
  const r = S.run;
  if (!r) return emptyHTML('Чек-листа пока нет', 'Включите «Чек-лист» в параметрах и запустите генерацию.');
  const items = checklistItems(r);
  if (!r.checklist || (!items.length && !r.checklist.groups.length)) {
    if (S.running && r.steps.checklist.status === 'running') return emptyHTML('Агент составляет чек-лист…', 'Ход работы — на вкладке «Агент».');
    const can = r.requirements.some((x) => x.inScope) && !S.running && aiReady(r.settings.genAI || S.settings.genAI);
    return emptyHTML('Чек-листа пока нет', r.requirements.length ? 'Его можно составить по уже выделенным требованиям или вести вручную.' : 'Он появится после анализа требований.',
      `<span class="case-acts" style="justify-content:center;margin-top:8px">${can ? '<button class="btn accent" type="button" data-act="gen-checklist">Составить чек-лист</button>' : ''}<button class="btn" type="button" data-act="cl-new-manual">Создать вручную</button></span>`);
  }
  const f = S.clFilter, filtered = f.type !== 'all' || f.suite !== 'all';
  const n = (t) => items.filter((i) => t === 'all' || i.type === t).length;
  const ns = (s) => items.filter((i) => i.suites.includes(s)).length;
  const chips = ['all', ...TYPES].filter((t) => t === 'all' || n(t)).map((t) => `<button class="fchip" type="button" data-act="cl-ftype" data-t="${t}" aria-pressed="${f.type === t}">${t === 'all' ? 'Все' : TL[t]}<span class="n">${n(t)}</span></button>`).join('');
  const schips = SUITES.map((s) => `<button class="fchip" type="button" data-act="cl-fsuite" data-s="${s}" aria-pressed="${f.suite === s}">${SUITE_RU[s]}<span class="n">${ns(s)}</span></button>`).join('');
  const show = (i) => (f.type === 'all' || i.type === f.type) && (f.suite === 'all' || i.suites.includes(f.suite));
  const groups = r.checklist.groups.map((g, gi) => ({ g, gi, items: g.items.filter(show) })).filter((x) => x.items.length || !filtered);
  const itemHTML = (i) => {
    const fds = openFindingsFor(r, 'checklist', i.id);
    const ref = S.clRefine?.id === i.id ? S.clRefine : null;
    const body = S.clEdit === i.id ? clEditHTML(r, i) : `<div class="cl-text">${i.check ? esc(i.check) : '<span class="muted">Пустой пункт</span>'}</div>
      ${i.expected ? `<div class="cl-exp"><span class="muted">Ожидаемый результат:</span> ${esc(i.expected)}</div>` : ''}
      <div class="cl-meta"><span class="chip ${i.type}">${TL[i.type]}</span><span class="chip ${prioClass(i.priority)}">${prioRu(i.priority)}</span>${i.kind === 'negative' ? '<span class="chip cl-neg">Негативная</span>' : ''}${suiteToggles(i.suites, 'cl-suite', `data-id="${i.id}"`)}${i.requirementIds.map((id) => `<span class="rq">${esc(id)}</span>`).join('')}${fds.length ? `<button class="chip fd-chip sev-${fds[0].severity}" type="button" data-act="go-tab" data-tab="review">замечаний: ${fds.length}</button>` : ''}</div>
      ${ref ? `<div class="case-edit" style="margin-top:8px"><label class="lbl" for="clr-input">Замечание к пункту</label><textarea id="clr-input" rows="2" placeholder="Например: укажи конкретное значение лимита; это проверка API, а не UI" ${ref.busy ? 'disabled' : ''}>${esc(ref.comment || '')}</textarea>
        ${ref.error ? `<p class="case-note err">${esc(ref.error)}</p>` : ''}
        <div class="case-acts">${ref.busy ? '<span class="case-note muted">Модель дорабатывает пункт…</span><button class="btn" type="button" data-act="cl-refine-stop">Остановить</button>' : `<button class="btn accent" type="button" data-act="cl-refine-go" data-id="${i.id}">Доработать с ИИ</button><button class="btn" type="button" data-act="cl-refine-cancel">Отмена</button>`}</div></div>` : ''}`;
    return `<li class="cl-item" id="cl-${i.id}"><span class="cl-box" aria-hidden="true"></span><span class="cl-id">${i.id}</span><div style="min-width:0">${body}</div>
      <div class="cl-acts">${S.clEdit === i.id ? '' : `<button class="icon-btn" type="button" data-act="cl-edit" data-id="${i.id}" aria-label="Изменить пункт ${i.id}" title="Изменить вручную">${ICON.pen}</button><button class="icon-btn" type="button" data-act="cl-refine" data-id="${i.id}" aria-label="Замечание к пункту ${i.id}" title="Замечание — доработать с ИИ">${ICON.chat}</button><button class="icon-btn" type="button" data-act="cl-del" data-id="${i.id}" aria-label="Удалить пункт ${i.id}" title="Удалить">${ICON.x}</button>`}</div></li>`;
  };
  return `<div class="toolbar">${chips}<span class="fsep" aria-hidden="true"></span>${schips}
    <span style="margin-left:auto;display:flex;gap:6px;flex-wrap:wrap"><button class="btn" type="button" data-act="cl-newgroup">+ Группа</button>${S.caps.downloads ? '<button class="btn" type="button" data-act="cl-dl-pdf">Скачать .pdf</button><button class="btn" type="button" data-act="cl-dl-xlsx">Скачать .xlsx</button><button class="btn" type="button" data-act="cl-dl-md">Скачать .md</button><button class="btn" type="button" data-act="cl-dl-json">Скачать .json</button>' : ''}<button class="btn" type="button" data-act="cl-copy">Копировать</button>${aiReady(r.settings.genAI || S.settings.genAI) && !S.running ? '<button class="btn" type="button" data-act="cl-regen">Составить заново</button>' : ''}</span></div>
    ${groups.length ? groups.map(({ g, gi, items: its }) => `<section class="cl-group"><h4>${S.clGroupEdit === gi ? `<span class="cl-edit" style="flex:1"><input type="text" id="clg-input" value="${esc(g.title)}" aria-label="Название группы"><button class="btn accent" type="button" data-act="cl-gsave" data-gi="${gi}">Сохранить</button><button class="btn" type="button" data-act="cl-gcancel">Отмена</button></span>`
      : `${esc(g.title)}<span>${its.length}</span><span class="cl-gacts"><button class="btn sm" type="button" data-act="cl-add" data-gi="${gi}">+ Пункт</button><button class="btn sm" type="button" data-act="cl-gedit" data-gi="${gi}">Переименовать</button><button class="btn sm danger" type="button" data-act="cl-gdel" data-gi="${gi}">Удалить</button></span>`}</h4>
      ${its.length ? `<ul class="cl-items">${its.map(itemHTML).join('')}</ul>` : '<p class="hint" style="padding:10px 12px">В группе нет пунктов.</p>'}</section>`).join('') : emptyHTML('Ничего не найдено', 'Измените фильтр.')}`;
}
function clEditHTML(r, it) {
  const gIdx = r.checklist.groups.findIndex((g) => g.items.includes(it));
  return `<div class="cl-form"><textarea id="cl-input" rows="2" aria-label="Название проверки ${it.id}" placeholder="Название проверки">${esc(it.check)}</textarea>
    <textarea id="cl-exp" rows="2" aria-label="Ожидаемый результат ${it.id}" placeholder="Ожидаемый результат">${esc(it.expected || '')}</textarea>
    <div class="cl-form-row"><select id="cl-type" aria-label="Вид">${TYPES.map((t) => `<option value="${t}" ${t === it.type ? 'selected' : ''}>${TL[t]}</option>`).join('')}</select>
      <select id="cl-kind" aria-label="Позитивная или негативная"><option value="positive" ${it.kind !== 'negative' ? 'selected' : ''}>Позитивная</option><option value="negative" ${it.kind === 'negative' ? 'selected' : ''}>Негативная</option></select>
      <select id="cl-prio" aria-label="Приоритет">${PRIOS.map((p) => `<option value="${p}" ${p === normPrio(it.priority) ? 'selected' : ''}>${PRIO_RU[p]}</option>`).join('')}</select>
      <select id="cl-group" aria-label="Группа">${r.checklist.groups.map((g, i) => `<option value="${i}" ${i === gIdx ? 'selected' : ''}>${esc(g.title)}</option>`).join('')}</select>
      <input id="cl-reqs" type="text" class="mono" placeholder="R-001, R-002" value="${esc(it.requirementIds.join(', '))}" aria-label="Требования"></div>
    <div class="cl-edit"><button class="btn accent" type="button" data-act="cl-save" data-id="${it.id}">Сохранить</button><button class="btn" type="button" data-act="cl-cancel" data-id="${it.id}">Отмена</button></div></div>`;
}
function removeChecklistItem(r, id) {
  for (const g of r.checklist.groups) g.items = g.items.filter((i) => i.id !== id);
}
function newChecklistItem(r, gi) {
  const g = r.checklist.groups[gi];
  if (!g) return;
  const it = { id: 'CL-' + pad(++r.counters.cl), check: '', expected: '', kind: 'positive', type: (r.settings.types || TYPES)[0] || 'ui', priority: 'P2_MEDIUM', suites: ['regression'], requirementIds: [], manual: true };
  g.items.push(it);
  S.clEdit = it.id; S.clNewId = it.id; S.clFilter = { type: 'all', suite: 'all' };
  renderTabs(); renderTab(); $('#cl-input')?.focus();
}

/* ---------- export ---------- */
function outputPreview(o) {
  if (o.kind === 'xlsx') {
    const rows = o.rows.slice(0, 40);
    return `<div class="tbl-wrap" style="max-height:65vh;overflow:auto"><table class="steps-t"><thead><tr>${o.columns.map((c) => `<th>${esc(c)}</th>`).join('')}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((x) => `<td>${esc(x).replace(/\n/g, '<br>')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${o.rows.length > 40 ? `<p class="hint" style="margin-top:6px">Показаны первые 40 строк из ${o.rows.length}.</p>` : ''}`;
  }
  const t = o.text.length > 300000 ? o.text.slice(0, 300000) + '\n…' : o.text;
  return `<pre class="json-pre" tabindex="0">${o.ext === 'json' ? hlJSON(t) : esc(t)}</pre>`;
}
/* вкладка «Трассировка ошибки»: описание дефекта, необязательный стек трейса и пошаговый разбор агентом */
function traceTab() {
  const T = S.trace, r = T.result;
  const ready = aiReady(S.settings.genAI);
  const note = ready ? `Агент построит трассировку по описанию дефекта, стеку трейса и знаниям о продукте (${aiLabel(S.settings.genAI)}).` : aiProblem(S.settings.genAI);
  const steps = r ? `<ol class="trace-steps">${r.steps.map((s) => `<li><div class="trace-h"><span class="trace-n">${s.n}</span><b>${esc(s.title)}</b>${s.layer ? `<span class="chip">${esc(s.layer)}</span>` : ''}</div>${s.details.length ? `<ul>${s.details.map((d) => `<li>${esc(d)}</li>`).join('')}</ul>` : ''}</li>`).join('')}</ol>` : '';
  const block = (title, rows) => (rows.some(Boolean) ? `<div class="exp-card"><div class="exp-row"><b>${title}</b></div>${rows.filter(Boolean).join('')}</div>` : '');
  const failure = r ? block('Место сбоя', [r.failure.error && `<p><b>Ошибка:</b> ${esc(r.failure.error)}</p>`, r.failure.location && `<p><b>Где:</b> ${esc(r.failure.location)}</p>`, r.failure.cause && `<p><b>Причина:</b> ${esc(r.failure.cause)}</p>`]) : '';
  const response = r ? block('Ответ сервера', [r.response.status && `<p><b>Статус:</b> ${esc(r.response.status)}</p>`, r.response.body && `<pre class="trace-pre">${esc(r.response.body)}</pre>`]) : '';
  const result = r ? block('Результат для пользователя', [r.result && `<p>${esc(r.result)}</p>`, r.summary && `<p class="muted">${esc(r.summary)}</p>`, r.questions.length && `<p><b>Уточнить:</b></p><ul>${r.questions.map((q) => `<li>${esc(q)}</li>`).join('')}</ul>`]) : '';
  return `<div class="exp-card"><div class="exp-row"><b>Трассировка ошибки</b><span class="muted small">${esc(aiLabel(S.settings.genAI))}</span></div>
    <p class="hint">${esc(note)}</p>
    <div class="field"><label class="lbl" for="trace-desc">Описание дефекта</label><textarea id="trace-desc" rows="4" placeholder="Что сделал пользователь, что ожидалось и что получилось">${esc(T.description)}</textarea></div>
    <div class="field"><label class="lbl" for="trace-stack">Стек трейс <span class="muted small">(необязательно)</span></label><textarea id="trace-stack" rows="8" class="mono" placeholder="Вставьте стек трейс из логов">${esc(T.stack)}</textarea></div>
    <div class="exp-row"><button class="btn accent" type="button" data-act="trace-run" ${T.busy || !T.description.trim() || !ready ? 'disabled' : ''}>${T.busy ? 'Агент трассирует…' : 'Выполнить трассировку'}</button></div>
    ${T.error ? `<div class="banner err"><div class="banner-body">${esc(T.error)}</div></div>` : ''}
  </div>${steps}${failure}${response}${result}`;
}
function exportTab() {
  const r = S.run;
  if (!r || !r.cases.length) return emptyHTML('Экспорт появится после генерации тест-кейсов', 'Формат файла задаётся слева: «Указания агенту» → «Формат экспорта».');
  const fmt = S.cfg.exportFormat.trim();
  if (!fmt) {
    const o = { kind: 'text', ext: 'json', filename: `test-cases_${new Date(r.createdAt).toISOString().slice(0, 10)}`, text: JSON.stringify(buildDefaultExport(r), null, 2) };
    S.defaultOut = o;
    return `<div class="exp-card"><div class="exp-row"><b>Стандартный JSON</b><span class="muted small">кейсы по видам, наборы «Смоук» и «Регресс», трассировка требований</span></div>
      <p class="hint">Чтобы выгрузить в формате вашей TMS, опишите его во вкладке «Формат экспорта» слева.</p>
      <div class="exp-row"><button class="btn" type="button" data-act="cfg-export">Описать формат</button></div></div>
      ${outputHead(o, 'default')}${outputPreview(o)}`;
  }
  const fmtH = hash(fmt);
  const exp = S.exp && S.exp.fmtH === fmtH ? S.exp : null;
  const stale = exp?.output && exp.key !== exportKey(r, fmt);
  const todo = r.cases.filter((c) => !exp?.spec || !S.expCache.has(itemKey(fmtH, exp.spec, c))).length;
  const local = !!exp?.spec && canMapLocally(exp.spec);
  const calls = (exp?.spec ? 0 : 1) + (local ? 0 : Math.ceil(todo / 8));
  const running = exp?.status === 'running';
  return `<div class="exp-card"><div class="exp-row"><b>Формат экспорта</b><button class="link" type="button" data-act="cfg-export" style="margin-left:auto">Изменить</button></div>
      <div class="exp-fmt">${esc(fmt)}</div>
      ${exp?.spec?.notes ? `<p class="hint">${esc(exp.spec.notes)}${local ? ' Файл собирается по шаблону полей, без модели.' : ''}</p>` : ''}
      <div class="exp-row">${running ? `<span class="small">${esc(exp.progress)}</span><button class="btn" type="button" data-act="stop-export">Остановить</button>`
        : todo || !exp?.output ? `<button class="btn accent" type="button" data-act="run-export" ${aiReady(S.settings.genAI) || local ? '' : 'disabled'}>${exp?.output ? 'Обновить файл' : 'Собрать файл'}</button><span class="hint">${!exp?.spec ? 'Агент один раз разберёт описание формата. Если поля кейсов можно подставить по шаблону, файл соберётся без других запросов к модели; если текст нужно переписывать — ещё примерно по запросу на 8 кейсов.' : local ? 'Формат собирается по шаблону — без запросов к модели.' : `Нужно ${calls} ${plural(calls, 'запрос', 'запроса', 'запросов')} к модели. Уже преобразованные кейсы повторно не обрабатываются.`}</span>`
          : `<button class="btn" type="button" data-act="rebuild-export" ${aiReady(S.settings.genAI) ? '' : 'disabled'}>Пересобрать с нуля</button><span class="hint">Файл актуален. «Пересобрать с нуля» заново определит формат и преобразует все кейсы — например, если результат не устроил.</span>`}</div></div>
    ${exp?.status === 'error' || (exp?.error && !running) ? `<div class="banner ${exp.status === 'error' ? 'err' : 'warn'}" style="margin-bottom:12px"><div>${esc(exp.error)}</div></div>` : ''}
    ${stale && !running ? '<div class="banner warn" style="margin-bottom:12px"><div>Кейсы изменились после сборки — пересоберите файл.</div></div>' : ''}
    ${exp?.output ? outputHead(exp.output, 'ai') + outputPreview(exp.output) : ''}`;
}
function outputHead(o, which) {
  const size = o.kind === 'xlsx' ? o.rows.length + ' ' + plural(o.rows.length, 'строка', 'строки', 'строк') : fmtN(Math.ceil(new Blob([o.text]).size / 1024)) + ' КБ';
  return `<div class="sec-h"><h3 class="mono">${esc(o.filename)}.${esc(o.ext)}</h3><span class="muted small num">${size}</span>
    <span class="sp">${S.caps.downloads ? `<button class="btn accent" type="button" data-act="dl-out" data-w="${which}">Скачать</button>` : ''}<button class="btn" type="button" data-act="copy-out" data-w="${which}">Копировать</button></span></div>`;
}
async function downloadFile(filename, data) {
  if (!S.caps.downloads) return toast('Скачивание недоступно в этом окне — используйте «Копировать».', 'err');
  try { await S.caps.downloads.save({ filename, data }); toast('Файл сохранён'); }
  catch (err) { if (err?.code !== 'declined') toast(err?.code === 'rate_limited' ? 'Окно сохранения уже открыто.' : 'Скачивание недоступно в этом окне — используйте «Копировать».', 'err'); }
}
async function downloadOutput(o) {
  if (o.kind === 'xlsx') {
    try {
      await lib('xlsx');
      const X = window.XLSX, ws = X.utils.aoa_to_sheet([o.columns, ...o.rows.map((r) => r.map(unfence))]), wb = X.utils.book_new();
      X.utils.book_append_sheet(wb, ws, o.sheet || 'Test cases');
      return downloadFile(`${o.filename}.xlsx`, new Blob([X.write(wb, { type: 'array', bookType: 'xlsx' })]));
    } catch { return toast('Не удалось сформировать Excel-файл.', 'err'); }
  }
  const data = o.ext === 'csv' ? String.fromCharCode(0xFEFF) + o.text : o.text;
  return downloadFile(o.ext === 'xml' ? `${o.filename}.xml.txt` : `${o.filename}.${o.ext}`, data);
}

/* ---------- history ---------- */
function histRow(h, legacy) {
  const u = h.counts?.upd;
  const counts = h.mode === 'update' && u ? [`изменено ${u.changed || 0}`, `новых ${u.new || 0}`, `устарело ${u.obsolete || 0}`, `без изменений ${u.same || 0}`, h.counts?.checklist ? `чек-лист ${h.counts.checklist}` : ''].filter(Boolean).join(' · ')
    : [...TYPES.filter((t) => h.counts?.[t]).map((t) => `${TL[t]} ${h.counts[t]}`), h.counts?.checklist ? `чек-лист ${h.counts.checklist}` : ''].filter(Boolean).join(' · ') || 'без результатов';
  const name = (h.mode === 'update' ? `Актуализация: ${h.source?.name || 'файл'} · ` : '') + ((h.docs || []).map((d) => d.name).join(', ') || 'Без названия');
  const pid = legacy ? '' : S.productId || '';
  const who = !legacy && S.productId && h.by && h.by !== S.caps.uid ? '<span>коллега</span>' : '';
  return `<div class="hrow"><div style="min-width:0"><h4>${esc(name)}</h4><div class="meta"><span class="num">${fmtDate(h.createdAt)}</span><span>${(h.docs || []).length} ${plural((h.docs || []).length, 'документ', 'документа', 'документов')}</span><span>${counts}</span>${h.coverage != null ? `<span>покрытие ${h.coverage}%</span>` : ''}${h.usage?.calls ? `<span>≈ ${fmtTok(h.usage.in + h.usage.out)} токенов</span>` : ''}${who}${S.run?.id === h.id ? '<span class="chip ok">открыт</span>' : ''}${h.status === 'running' && h.hb && Date.now() - h.hb < HB_STALE ? '<span class="chip p-medium">идёт генерация</span>' : ['running', 'interrupted', 'stopped'].includes(h.status) && S.run?.id !== h.id ? '<span class="chip p-medium">не завершён</span>' : ''}</div></div>
    <div class="acts"><button class="btn" type="button" data-act="open-hist" data-id="${esc(h.id)}" data-pid="${esc(pid)}">Открыть</button>${legacy && S.productId ? `<button class="btn" type="button" data-act="move-hist" data-id="${esc(h.id)}" title="Перенести запуск в текущий продукт: его кейсы и чек-лист станут частью знаний продукта">В продукт</button>` : ''}<button class="btn danger" type="button" data-act="del-hist" data-id="${esc(h.id)}" data-pid="${esc(pid)}">Удалить</button></div></div>`;
}
function historyTab() {
  if (!S.caps.ready) return emptyHTML('Подключаюсь к хранилищу…');
  if (!S.caps.db || !S.caps.uid) return emptyHTML('История недоступна в этом окне', 'Запуски сохраняются, когда приложение открыто на claude.ai под вашим аккаунтом.');
  if (S.historyState === 'idle') { setTimeout(loadHistory, 0); return emptyHTML('Загружаю историю…'); }
  if (S.historyState === 'loading') return emptyHTML('Загружаю историю…');
  if (S.historyState === 'error') return emptyHTML('Не удалось загрузить историю', '', '<button class="btn" type="button" data-act="reload-hist">Повторить</button>');
  const p = curProduct();
  let html = '';
  if (p) {
    html += `<div class="sec-h"><h3>Запуски продукта «${esc(p.name)}»</h3><span class="muted small">${inClaude ? 'видны всей команде' : 'хранятся в этом браузере'}</span></div>`;
    html += S.history.length ? `<div class="hist">${S.history.map((h) => histRow(h, false)).join('')}</div>` : emptyHTML('Запусков пока нет', 'Каждый запуск сохраняется сюда автоматически, а его кейсы и чек-лист пополняют знания продукта.');
    if (S.legacy.length) html += `<div class="sec-h" style="margin-top:22px"><h3>Личные запуски без продукта</h3><span class="muted small">сделаны до появления продуктов, видны только вам</span></div>
      <p class="hint" style="margin:-4px 0 10px">«В продукт» переносит запуск в текущий продукт: он станет виден команде, а агент перестанет повторять его кейсы.</p>
      <div class="hist">${S.legacy.map((h) => histRow(h, true)).join('')}</div>`;
    return html;
  }
  if (!S.history.length) return emptyHTML('Запусков пока нет', 'Каждый запуск сохраняется сюда автоматически. История видна только вам.');
  return `<div class="sec-h"><h3>Мои запуски</h3><span class="muted small">видны только вам</span></div><div class="hist">${S.history.map((h) => histRow(h, true)).join('')}</div>`;
}

/* ---------- справка по функциональности ---------- */
const HELP_ST = { answered: 'Ответ по базе знаний', partial: 'Частичный ответ', not_found: 'Нет в базе знаний', error: 'Ошибка', pending: 'Ищу в базе знаний…' };
const HELP_SUGGEST = ['Какие роли и права есть в продукте?', 'Какие ограничения и лимиты описаны?', 'Какие коды ошибок возвращает API?', 'Как попасть на основные экраны?', 'Что ещё не уточнено в требованиях?'];
function helpItemHTML(it) {
  if (it.status === 'pending') return `<div class="hq"><div class="hq-q"><p>${esc(it.q)}</p></div><div class="hq-a st-pending"><span class="hq-badge">${HELP_ST.pending}</span><button class="link" type="button" data-act="help-stop">Остановить</button></div></div>`;
  const meta = it.cached ? 'из истории: база знаний не менялась, без запроса к модели' : it.local ? 'без запроса к модели' : it.tok ? `≈ ${fmtTok(it.tok)} токенов` : '';
  const canOpen = (it.status === 'not_found' || it.status === 'partial') && S.productId && S.caps.db;
  return `<div class="hq" id="hq-${esc(it.id)}"><div class="hq-q"><span class="muted small">${fmtDate(it.at)}</span><p>${esc(it.q)}</p></div>
    <div class="hq-a st-${it.status}"><span class="hq-badge">${HELP_ST[it.status] || ''}</span>
      <div class="md">${mdHTML(it.answer)}</div>
      ${it.missing ? `<p class="hint">Не хватает в базе знаний: ${esc(it.missing)}</p>` : ''}
      ${it.nosrc ? '<p class="hint warn-hint">Модель не указала источник — ответ помечен как частичный, проверьте его.</p>' : ''}
      ${it.sources?.length ? `<div class="hq-src"><span class="muted small">Источники:</span>${it.sources.map((x) => (x.kbId ? `<button type="button" class="chip chip-link" data-act="kb-open" data-id="${esc(x.kbId)}" title="Открыть раздел">${esc(x.label)}</button>` : `<span class="chip" title="${esc(x.preview || '')}">${esc(x.label)}</span>`)).join('')}</div>` : ''}
      <div class="hq-foot">${canOpen ? (it.openAdded ? '<span class="chip ok">в открытых вопросах</span>' : `<button class="btn sm" type="button" data-act="help-open-add" data-id="${esc(it.id)}">В открытые вопросы</button>`) : ''}${meta ? `<span class="muted small">${esc(meta)}</span>` : ''}</div></div></div>`;
}
function renderHelp(force) {
  if (S.settings.mode !== 'help') return;
  const body = $('#tab-body'), H = S.help;
  if (!$('#help-view')) {
    body.innerHTML = `<div class="help" id="help-view"><div id="help-head"></div>
      <div id="kb-pane"><div class="kb-tools" id="kb-tools"><input type="search" id="kb-q" placeholder="Найти раздел" aria-label="Найти раздел базы знаний">
          <label class="switch small" title="Сразу после загрузки документа: разделы базы знаний, сводки затронутых разделов и «Что агент знает о продукте»"><input type="checkbox" id="kb-auto"><span class="sw"></span><span>Разбирать новые документы автоматически</span></label></div>
        <div id="kb-job"></div><div id="kb-body"></div></div>
      <div id="qa-pane"><div class="help-list" id="help-list" aria-live="polite"></div>
        <div class="help-form"><label class="sr" for="help-input">Вопрос к базе знаний</label>
          <textarea id="help-input" rows="2" placeholder="Например: как пользователь попадает на экран «Новый пароль»? Enter — отправить, Shift+Enter — новая строка"></textarea>
          <div class="help-acts"><span class="hint" id="help-note"></span><button class="btn accent" type="button" id="help-send" data-act="help-send">Спросить</button></div></div>
        <div id="help-open"></div></div>
      </div>`;
    $('#help-input').value = H.draft || '';
    $('#kb-q').value = S.kb.q || '';
  }
  const view = S.helpView === 'qa' ? 'qa' : 'blocks';
  const p = curProduct(), st = kbStats();
  const conf = S.kb.index.blocks.reduce((a, b) => a + (b.conf || 0), 0);
  const kb = [st.blocks ? `разделов ${st.blocks}` : '', conf ? `расхождений между документами ${conf}` : '', st.passport ? `знания о продукте ${fmtKChars(st.passport)}` : 'знаний о продукте пока нет', `документов ${st.docs}`, st.cases ? `тест-кейсов ${st.cases}` : '', st.checklist ? `пунктов чек-листа ${st.checklist}` : '', st.ctx ? 'доп. контекст QA' : ''].filter(Boolean).join(' · ');
  $('#help-head').innerHTML = `<div class="sec-h"><h3>База знаний</h3>${p ? `<span class="muted small">продукт «${esc(p.name)}»</span>` : ''}
      <div class="help-views" role="tablist" aria-label="Разделы базы знаний">${[['blocks', 'Разделы', st.blocks], ['qa', 'Вопросы', H.items.length], ].map(([id, n, c]) => `<button type="button" role="tab" aria-selected="${view === id}" data-act="help-view" data-v="${id}">${n}${c ? `<span class="cnt">${c}</span>` : ''}</button>`).join('')}</div>
      ${view === 'qa' && H.items.length ? '<span class="sp"><button class="link" type="button" data-act="help-clear">Очистить историю</button></span>' : ''}</div>
    <p class="hint">${view === 'qa' ? 'Агент отвечает только по базе знаний продукта и указывает источники. Чего в базе нет, он не придумывает — так и скажет. История вопросов видна только вам.' : 'При загрузке документа агент разбирает его по функциональным разделам и сводит сведения из всех документов раздела в одну сводку — с источниками и расхождениями между документами. Сводки учитываются в ответах и при генерации чек-листов и тест-кейсов. Разделы общие для команды.'}</p>
    <p class="kb-line"><b>В базе знаний:</b> ${esc(kb)}</p>`;
  $('#kb-pane').hidden = view !== 'blocks';
  $('#qa-pane').hidden = view !== 'qa';
  if (view === 'blocks') renderKbPane(force); else renderQaPane(force);
}
function renderQaPane(force) {
  const H = S.help;
  const list = $('#help-list');
  if (S.caps.db && S.productId && !H.loaded) list.innerHTML = emptyHTML('Загружаю историю вопросов…');
  else if (!H.items.length) list.innerHTML = `<div class="help-empty"><span class="muted small">Например:</span>${HELP_SUGGEST.map((q) => `<button class="fchip" type="button" data-act="help-suggest" data-q="${esc(q)}">${esc(q)}</button>`).join('')}</div>`;
  else list.innerHTML = H.items.map(helpItemHTML).join('');
  const v = S.settings.genAI;
  $('#help-send').disabled = H.busy || !aiReady(v);
  $('#help-input').disabled = H.busy;
  $('#help-note').textContent = !aiReady(v) ? aiProblem(v) : H.busy ? 'Агент ищет ответ в базе знаний…' : `Отвечает: ${aiLabel(v)}${S.settings.economy ? ' · экономный режим' : ''}. Повторный вопрос при неизменной базе знаний — без запроса к модели.`;
  $('#help-note').className = 'hint' + (!aiReady(v) ? ' warn-hint' : '');
  const oq = openQuestions();
  if (!force && isTyping($('#help-open'))) return;
  $('#help-open').innerHTML = oq.length ? `<div class="exp-card"><div class="exp-row"><b>Открытые вопросы продукта · ${oq.length}</b><span class="muted small">общие для команды</span></div>
    <p class="hint">Ответ попадёт в знания о продукте (раздел «Уточнения команды»), и агент начнёт учитывать его в ответах.</p>
    <ul class="open-q">${oq.map((o, i) => `<li><p>${esc(o.text)}</p>${H.ans[o.line] != null ? `<div class="oq-ans"><input type="text" data-help-ans="${i}" value="${esc(H.ans[o.line])}" placeholder="Ответ аналитика или решение команды" aria-label="Ответ на открытый вопрос"><button class="btn accent sm" type="button" data-act="help-ans-save" data-i="${i}">Сохранить</button><button class="btn sm" type="button" data-act="help-ans-cancel" data-i="${i}">Отмена</button></div>` : `<button class="link" type="button" data-act="help-ans-open" data-i="${i}">Ответить</button>`}</li>`).join('')}</ul></div>` : '';
}
/* ---------- разделы базы знаний ---------- */
function kbRelatedCases(blk) {
  const q = [...new Set(helpTokens(`${blk.title} ${blk.title} ${blk.summary || ''}`))];
  return S.prodIndex.cases.map((x) => ({ x, s: helpScore(q, x.n) })).filter((o) => o.s >= Math.min(2, q.length)).sort((a, b) => b.s - a.s).slice(0, 12).map((o) => o.x);
}
function renderKbPane(force) {
  $('#kb-auto').checked = S.settings.kbAuto;
  const J = S.kb.job, pend = S.kb.loaded ? kbPending() : [];
  const v = S.settings.genAI, staleL = S.kb.loaded ? kbStale() : [], staleN = staleL.length;
  $('#kb-tools').hidden = !!S.kb.open || !S.kb.index.blocks.length;
  $('#kb-job').innerHTML = J.busy
    ? `<div class="banner info kb-banner"><div>${kbProgressHTML(J)}${J.log.length ? `<ul class="log">${J.log.slice(-6).map((l) => `<li class="${l.kind}">${esc(l.text)}</li>`).join('')}</ul>` : ''}<span style="margin-top:6px;display:flex"><button class="btn sm" type="button" data-act="kb-stop">Остановить</button></span></div></div>`
    : J.error ? `<div class="banner err kb-banner"><div>${esc(J.error)}</div></div>`
      : S.kb.note && pend.length && !S.kb.open ? `<div class="banner info kb-banner"><div>${esc(S.kb.note)}</div></div>`
      : pend.length && !S.kb.open ? `<div class="banner warn kb-banner"><div><b>Не разобраны по разделам: ${pend.length} ${plural(pend.length, 'документ', 'документа', 'документов')}</b> — ${esc(pend.slice(0, 4).map((d) => d.name).join(', '))}${pend.length > 4 ? '…' : ''}.
          <span style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px"><button class="btn accent sm" type="button" data-act="kb-run" ${aiReady(v) ? '' : 'disabled'}>Разобрать</button><span class="small">${aiReady(v) ? `≈ ${pend.reduce((a, d) => a + buildChunks([d]).length, 0)} ${plural(pend.reduce((a, d) => a + buildChunks([d]).length, 0), 'запрос', 'запроса', 'запросов')} к модели на разбор и по одному на сводку каждого затронутого раздела` : esc(aiProblem(v))}</span></span></div></div>`
      : S.kb.synthReport && staleN && !S.kb.open ? kbReportHTML(S.kb.synthReport, staleN, v)
      : staleN && !S.kb.open ? `<div class="banner info kb-banner"><div><b>Сводки по всем документам: ${staleN} ${plural(staleN, 'раздел', 'раздела', 'разделов')} без свежей сводки</b> — ${esc(staleL.slice(0, 4).map((b) => b.title).join(', '))}${staleN > 4 ? '…' : ''}. Сводка сводит выдержки из всех документов раздела в один текст, показывает расхождения между документами и идёт в ответы и генерацию.
          <span style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px"><button class="btn accent sm" type="button" data-act="kb-synth" ${aiReady(v) ? '' : 'disabled'}>Собрать сводки</button><span class="small">${aiReady(v) ? `≈ ${staleN} ${plural(staleN, 'запрос', 'запроса', 'запросов')} к модели` : esc(aiProblem(v))}</span></span></div></div>` : '';
  const el = $('#kb-body');
  if (!S.caps.db || !S.productId) { el.innerHTML = emptyHTML('Разделы доступны внутри продукта', 'Откройте приложение на claude.ai под своим аккаунтом или в автономной версии.'); return; }
  if (!S.kb.loaded) { el.innerHTML = emptyHTML('Загружаю разделы…'); return; }
  if (S.kb.open) return renderKbArticle(el, force);
  const q = (S.kb.q || '').trim().toLowerCase();
  const all = S.kb.index.blocks.slice().sort(kbCmp);
  const list = all.filter((b) => !q || `${b.title} ${b.summary}`.toLowerCase().includes(q));
  if (!S.kb.index.blocks.length) {
    el.innerHTML = emptyHTML('Разделов пока нет', pend.length ? 'Нажмите «Разобрать» — агент разделит документы продукта на функциональные разделы.' : 'Загрузите документы продукта слева — агент разберёт их по функциональным разделам.');
    return;
  }
  // разделы — строками, по алфавиту; список сворачивается (поиск его разворачивает)
  const folded = S.kbFold;
  const head = `<div class="kb-list-h"><h4 class="fold-h"><button class="fold-btn" type="button" data-act="kb-fold" aria-expanded="${!folded}" aria-controls="kb-rows" title="${folded ? 'Развернуть' : 'Свернуть'} список разделов"><span class="fold-t">Разделы</span><span class="cnt">${q ? `${list.length} из ${all.length}` : all.length}</span><span class="muted small">по алфавиту</span>${FOLD_CHEV}</button></h4></div>`;
  if (folded) {
    const names = all.map((b) => b.title), shown = names.slice(0, 4).join(', ') + (names.length > 4 ? ` и ещё ${names.length - 4}` : '');
    el.innerHTML = head + `<div class="docs-sum kb-list-sum"><button class="fold-sum" type="button" data-act="kb-fold" title="Развернуть список разделов"><span class="fold-sum-n">${esc(shown)}</span></button></div>`;
    return;
  }
  const row = (b) => {
    const ids = arrOf(b.docIds), src = ids.map((id) => S.docs.find((d) => d.id === id)).filter(Boolean).map(docTitle);
    return `<li><button type="button" class="kb-row" data-act="kb-open" data-id="${esc(b.id)}" title="${esc(src.length ? 'Из документов: ' + src.join(', ') : b.title)}">
      <span class="kb-row-t">${hlText(b.title, q)}</span><span class="kb-row-s">${hlText(b.summary || '', q)}</span>
      <span class="kb-row-m">${ids.length} ${plural(ids.length, 'документ', 'документа', 'документов')} · ${fmtKChars(b.size || 0)}${b.conf ? ` · <span class="warn">расхождений ${b.conf}</span>` : !b.sh ? ' · без сводки' : ''}</span>${ROW_CHEV}</button></li>`;
  };
  el.innerHTML = head + (list.length ? `<ul class="kb-rows" id="kb-rows">${list.map(row).join('')}</ul>` : emptyHTML('Ничего не найдено', 'Измените запрос.'));
}
// По алфавиту, как в словаре: без учёта регистра и кавычек, «Ё» как «Е», числа по значению.
const kbSortKey = (t) => String(t || '').replace(/^[\s«"'„“(\[]+/, '');
const kbCmp = (a, b) => kbSortKey(a.title).localeCompare(kbSortKey(b.title), 'ru', { sensitivity: 'base', numeric: true });
const FOLD_CHEV = '<svg class="fold-chev" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 6l4 4 4-4"/></svg>';
const ROW_CHEV = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 4l4 4-4 4"/></svg>';
function hlText(text, q) {
  const t = String(text || '');
  if (!q) return esc(t);
  const lo = t.toLowerCase();
  let out = '', i = 0, k;
  while ((k = lo.indexOf(q, i)) >= 0) { out += esc(t.slice(i, k)) + '<mark>' + esc(t.slice(k, k + q.length)) + '</mark>'; i = k + q.length; }
  return out + esc(t.slice(i));
}
function renderKbArticle(el, force) {
  const id = S.kb.open;
  const meta = S.kb.index.blocks.find((b) => b.id === id);
  const blk = S.kb.cache[id];
  if (!meta && !blk) { S.kb.open = null; return renderKbPane(force); }
  if (!blk && S.kb.missing?.[id]) { el.innerHTML = emptyHTML('Раздел не найден в базе', 'Его записи нет — возможно, его удалили в другом окне. Обновите базу знаний или выберите другой раздел.'); return; }
  if (!blk) {
    el.innerHTML = emptyHTML('Загружаю раздел…');
    kbBlock(id).then(() => { if (S.kb.open === id) renderHelp(true); }).catch(() => { el.innerHTML = emptyHTML('Не удалось загрузить раздел'); });
    return;
  }
  if (!force && isTyping(el)) return;
  const all = arrOf(blk.parts).slice().sort((a, b) => (a.docName === b.docName ? a.chunk - b.chunk : (a.at || 0) - (b.at || 0)));
  const parts = all.filter((p) => p.md), cut = all.length - parts.length; // сведённые в сводку выдержки большого раздела не хранятся отдельно
  const docs = [...new Map(all.map((p) => [p.docId, p])).values()];
  const cases = kbRelatedCases(blk);
  const editing = S.kb.edit === id;
  const conflicts = arrOf(blk.conflicts), links = arrOf(blk.links).map((lid) => S.kb.index.blocks.find((b) => b.id === lid)).filter(Boolean);
  const stale = meta ? kbIsStale(meta) : !blk.synth, busy = S.kb.job.busy;
  const partsHTML = parts.map((pt) => `<section class="kb-part">${docs.length > 1 || parts.length > 1 ? `<div class="kb-part-h">Из «${esc(pt.docName)}»${pt.sections?.length ? ` · ${esc(pt.sections.join(', '))}` : ''}</div>` : pt.sections?.length ? `<div class="kb-part-h">Разделы документа: ${esc(pt.sections.join(', '))}</div>` : ''}<div class="md">${mdHTML(pt.md)}</div></section>`).join('');
  const synthHTML = blk.synth ? `<section class="kb-synth">
      <div class="kb-synth-h"><b>Сводка по всем документам</b><span class="muted small">${stale ? 'есть новые выдержки — сводка устарела' : `собрана ${fmtDate(blk.synthAt || blk.updatedAt || Date.now())}`}${blk.big ? ` · большой раздел: ${fmtKChars(blk.big)} сведено по подзаголовкам, без обрезки` : ''}</span><button class="link" type="button" data-act="kb-synth-one" data-id="${esc(id)}" ${busy ? 'disabled' : ''}>${stale ? 'Обновить сводку' : 'Пересобрать'}</button></div>
      ${conflicts.length ? `<div class="banner warn kb-conf"><div><b>Расхождения между документами · ${conflicts.length}</b><ul>${conflicts.map((c) => `<li>${mdInline(c)}</li>`).join('')}</ul><span class="small">Уточните у аналитика. Пока ответа нет, генерация следует требованиям запуска и не выдаёт спорное за факт, а анализ задаёт по этим местам вопросы.</span></div></div>` : ''}
      <div class="md">${mdHTML(kbSynthBody(blk.synth))}</div>
      ${links.length ? `<div class="hq-src"><span class="muted small">Связанные разделы:</span>${links.map((b) => `<button class="chip chip-link" type="button" data-act="kb-open" data-id="${esc(b.id)}">${esc(b.title)}</button>`).join('')}</div>` : ''}
    </section>
    <details class="kb-parts"${S.kb.partsOpen === id ? ' open' : ''}><summary>Выдержки из документов · ${parts.length}${cut ? ` · ещё ${cut} уже в сводке` : ''}</summary>${cut ? `<p class="muted small">${cut} ${plural(cut, 'выдержка уже сведена в сводку и не хранится', 'выдержки уже сведены в сводку и не хранятся', 'выдержек уже сведены в сводку и не хранятся')} отдельно, чтобы раздел уместился в базе${blk.lost ? `; ${blk.lost} — убраны до сводки, их сведения появятся при повторном разборе документов` : ''}.</p>` : ''}${partsHTML}</details>`
    : `<div class="banner info"><div><b>Сводка по всем документам ещё не собрана.</b> Она сведёт выдержки из ${docs.length} ${plural(docs.length, 'документа', 'документов', 'документов')} в один текст с источниками и покажет расхождения между документами; сводку учитывают ответы и генерация.
        <span style="display:flex;margin-top:8px"><button class="btn accent sm" type="button" data-act="kb-synth-one" data-id="${esc(id)}" ${busy || !aiReady(S.settings.genAI) ? 'disabled' : ''}>Собрать сводку</button></span></div></div>${partsHTML}`;
  el.innerHTML = `<article class="kb-art">
    <button class="link" type="button" data-act="kb-back">← Все разделы</button>
    <div class="kb-title-row">${editing ? `<input type="text" id="kb-title-input" value="${esc(blk.title)}" aria-label="Название раздела"><button class="btn accent sm" type="button" data-act="kb-rename-save" data-id="${esc(id)}">Сохранить</button><button class="btn sm" type="button" data-act="kb-rename-cancel">Отмена</button>`
      : `<h3>${esc(blk.title)}</h3><span class="sp"><button class="btn sm" type="button" data-act="kb-ask" data-id="${esc(id)}">Задать вопрос</button><button class="btn sm" type="button" data-act="kb-rename" data-id="${esc(id)}">Переименовать</button><button class="btn sm danger" type="button" data-act="kb-del" data-id="${esc(id)}">Удалить</button></span>`}</div>
    ${blk.summary ? `<p class="kb-lead">${esc(blk.summary)}</p>` : ''}
    <div class="hq-src"><span class="muted small">Источники:</span>${docs.map((p) => `<span class="chip" title="${esc(arrOf(parts.filter((x) => x.docId === p.docId).flatMap((x) => x.sections)).join(', '))}">${esc(p.docName)}</span>`).join('')}<span class="muted small">· обновлён ${fmtDate(blk.updatedAt || Date.now())}</span></div>
    ${synthHTML}
    ${cases.length ? `<div class="exp-card"><div class="exp-row"><b>Тест-кейсы продукта по разделу · ${cases.length}</b><span class="muted small">подобраны по названию раздела</span></div><ul class="kb-cases">${cases.map((x) => `<li><span class="mono">${esc(x.i)}</span> ${esc(x.n)}</li>`).join('')}</ul></div>` : ''}
  </article>`;
  if (editing) $('#kb-title-input')?.focus();
}
// заголовок работы базы знаний: что делается, сколько из скольких, полоса и оценка времени
function kbProgressHTML(J) {
  const p = kbProgress(J);
  if (!p) return `<b>${J.phase === 'synth' ? 'Собираю сводки разделов по всем документам…' : `Разбираю документы по разделам${J.doc ? ` — «${esc(J.doc)}»` : ''}…`}</b>`;
  return `<b>${esc(p.title)}</b>${p.line ? `<span class="small"> · ${esc(p.line)}</span>` : ''}<div class="mat-bar kb-bar" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${p.pct}"><i style="width:${Math.max(2, p.pct)}%"></i></div>`;
}
// итог последнего сбора сводок: сколько не получилось и почему — чтобы причина не терялась вместе с журналом
function kbReportHTML(R, staleN, v) {
  const why = Object.entries(R.reasons || {}).sort((a, b) => b[1] - a[1]).map(([t, n]) => `${esc(t)} — ${n}`).join('; ');
  return `<div class="banner warn kb-banner"><div><b>Сводки: собрано ${R.ok} из ${R.total}${R.fail ? `, не получилось ${R.fail}` : ''}${R.left > 0 ? `, не дошла очередь до ${R.left}` : ''}.</b>
    ${R.stop ? `<br>Сбор остановлен: ${esc(R.stop)}${/лимит/i.test(R.stop) ? ' Продолжу сам через 10 минут, если окно открыто.' : ''}` : ''}${why ? `<br><span class="small">Причины: ${why}</span>` : ''}
    <span style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:8px"><button class="btn accent sm" type="button" data-act="kb-synth" ${aiReady(v) ? '' : 'disabled'}>Собрать оставшиеся (${staleN})</button><button class="link" type="button" data-act="kb-report-hide">Скрыть</button></span></div></div>`;
}
// сводка без подраздела «Расхождения между документами» — они показаны отдельным блоком
const kbSynthBody = (t) => String(t || '').replace(/(^|\n)#{2,4}\s*Расхождени[^\n]*\n[\s\S]*?(?=\n#{2,4}\s|$)/i, '$1').trim();
function sendHelp() {
  const ta = $('#help-input');
  const q = (ta?.value || '').trim();
  if (!q) return;
  askHelp(q).then(() => { const last = $('#help-list .hq:last-child'); last?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); $('#help-input')?.focus(); });
  if (ta) ta.value = '';
  renderHelp();
  $('#help-list .hq:last-child')?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

/* ---------- продукт ---------- */
function mdInline(t) {
  return esc(t).replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/`([^`]+)`/g, '<code>$1</code>');
}
function mdHTML(text) {
  const out = []; let list = null, items = [];
  const flush = () => { if (list) { out.push(`<${list}>${items.map((x) => `<li>${x}</li>`).join('')}</${list}>`); list = null; items = []; } };
  for (const raw of String(text || '').split('\n')) {
    const line = raw.trimEnd();
    let m;
    if (!line.trim()) { flush(); continue; }
    if ((m = /^#{1,2}\s+(.*)$/.exec(line))) { flush(); out.push(`<h4>${mdInline(m[1])}</h4>`); continue; }
    if ((m = /^#{3,6}\s+(.*)$/.exec(line))) { flush(); out.push(`<h5>${mdInline(m[1])}</h5>`); continue; }
    if ((m = /^>\s?(.*)$/.exec(line))) { flush(); out.push(`<blockquote>${mdInline(m[1])}</blockquote>`); continue; }
    if ((m = /^\s*[-*•]\s+(.*)$/.exec(line))) { if (list !== 'ul') { flush(); list = 'ul'; } items.push(mdInline(m[1])); continue; }
    if ((m = /^\s*\d+[.)]\s+(.*)$/.exec(line))) { if (list !== 'ol') { flush(); list = 'ol'; } items.push(mdInline(m[1])); continue; }
    flush(); out.push(`<p>${mdInline(line)}</p>`);
  }
  flush();
  return out.join('');
}
// перед запуском: что из базы знаний агент учтёт в генерации
function kbIntroHTML() {
  if (!S.productId || S.kb.pid !== S.productId) return '';
  const n = S.kb.index.blocks.length;
  if (!n) return '';
  const conf = S.kb.index.blocks.reduce((a, b) => a + (b.conf || 0), 0), stale = kbStale().length;
  return `<div class="banner info"><div><b>База знаний продукта: ${n} ${plural(n, 'раздел', 'раздела', 'разделов')}${conf ? ` · расхождений между документами ${conf}` : ''}.</b> Сводки разделов по теме — из всех документов продукта, включая расшифровки видео, — агент учтёт на анализе, в чек-листе, плане, тест-кейсах и ревью${conf ? '; по расхождениям задаст вопросы' : ''}.${stale ? ` Без свежей сводки: ${stale} — по ним агент возьмёт выдержки из документов.` : ''}</div></div>`;
}
/* ---------- продукт: карточка в левой колонке над режимами ---------- */
const PP_CHEV = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M4 6l4 4 4-4"/></svg>';
function histRowMini(h) {
  const u = h.counts?.upd;
  const counts = h.mode === 'update' && u ? [`изменено ${u.changed || 0}`, `новых ${u.new || 0}`, `устарело ${u.obsolete || 0}`].join(' · ')
    : [...TYPES.filter((t) => h.counts?.[t]).map((t) => `${TL[t]} ${h.counts[t]}`), h.counts?.checklist ? `чек-лист ${h.counts.checklist}` : ''].filter(Boolean).join(' · ') || 'без результатов';
  const name = (h.mode === 'update' ? 'Актуализация: ' : '') + ((h.docs || []).map((d) => d.name).join(', ') || 'Без названия');
  const st = S.run?.id === h.id ? ' · открыт' : h.status === 'running' && h.hb && Date.now() - h.hb < HB_STALE ? ' · идёт генерация' : ['running', 'interrupted', 'stopped'].includes(h.status) ? ' · не завершён' : '';
  return `<button class="pp-run${S.run?.id === h.id ? ' cur' : ''}" type="button" data-act="open-hist" data-id="${esc(h.id)}" data-pid="${esc(S.productId || '')}" data-mode="${esc(h.mode || 'generate')}" title="Открыть запуск"><b>${esc(name)}</b><span class="num">${fmtDate(h.createdAt)} · ${esc(counts)}${st}</span></button>`;
}
function productPanelHTML() {
  if (!S.caps.db || !S.caps.uid) return `<div class="panel-h"><h2 id="h-prod">Продукт</h2></div><p class="hint">Продукты недоступны в этом окне. Откройте приложение на claude.ai под своим аккаунтом — продукты, документы и знания агента хранятся там.</p>`;
  if (!S.prodReady) return `<div class="panel-h"><h2 id="h-prod">Продукт</h2></div><p class="hint">Загружаю продукт…</p>`;
  const p = curProduct();
  if (!p) return `<div class="panel-h"><h2 id="h-prod">Продукт</h2></div><p class="hint">Продукт объединяет документы, доп. контекст, запуски и знания агента.</p><div class="pp-acts"><button class="btn accent" type="button" data-act="prod-new">Создать продукт</button><button class="btn" type="button" data-act="prod-import">Импорт продукта</button></div>`;
  const k = knowOf(null), K = S.know, idx = S.prodIndex;
  const by = (t) => idx.cases.filter((x) => x.t === t).length;
  const pass = k.passport.trim();
  const open = S.prodOpen;
  const docsN = S.docs.length;
  const head = `<div class="pp-h"><h2 id="h-prod" title="${esc(p.name)}">${esc(p.name)}</h2><button class="icon-btn pp-tog${open ? ' open' : ''}" type="button" data-act="pp-toggle" aria-expanded="${open}" aria-controls="prod-info" title="${open ? 'Свернуть' : 'Развернуть'} информацию о продукте">${PP_CHEV}</button></div>`;
  if (!open) {
    const sum = [`${docsN} ${plural(docsN, 'документ', 'документа', 'документов')}`, `${idx.cases.length} ${plural(idx.cases.length, 'кейс', 'кейса', 'кейсов')}`, `чек-лист ${idx.checklist.length}`, pass ? `знания ${fmtN(pass.length)} зн.` : 'знаний нет'];
    return head + `<button class="pp-sum" type="button" data-act="pp-toggle">${esc(sum.join(' · '))}</button>`;
  }
  const upd = p.passport?.updatedAt ? `обновлено ${fmtDate(p.passport.updatedAt)}${p.passport.runId ? ' после генерации' : ''}` : 'ещё не заполнено';
  const busy = K.busy || S.running;
  let html = head + `${p.description ? `<p class="muted pp-desc">${esc(p.description)}</p>` : ''}
    <div class="pp-acts"><button class="btn sm" type="button" data-act="prod-edit">Переименовать</button><button class="btn sm" type="button" data-act="prod-export" ${S.prodIO ? 'disabled' : ''} title="Скачать продукт одним JSON-файлом: знания, документы, контекст, запуски с кейсами">Экспорт</button><button class="btn sm" type="button" data-act="prod-import" ${S.prodIO || S.running ? 'disabled' : ''} title="Загрузить продукт из JSON-файла как новый продукт">Импорт</button><button class="btn sm danger" type="button" data-act="prod-del" ${S.running ? 'disabled' : ''}>Удалить продукт</button></div>
    ${S.prodIO ? `<div class="banner info"><div>${esc(S.prodIO.text)}</div></div>` : ''}
    <p class="hint">${inClaude ? 'Продукт общий для команды: документы, доп. контекст от QA, запуски, чек-листы, тест-кейсы и знания агента видят все, у кого есть доступ к приложению.' : 'В автономной версии продукты хранятся в этом браузере.'} Указания агенту (правила, шаблоны, формат экспорта) общие для всех продуктов.</p>
    <div class="stats pp-stats">
      ${stat('Документов', docsN, docsN ? fmtKChars(readyDocs().reduce((a, d) => a + d.chars, 0)) : 'загрузите ТЗ')}
      ${stat('Тест-кейсов', idx.cases.length, idx.cases.length ? TYPES.filter((t) => by(t)).map((t) => `${TL[t]} ${by(t)}`).join(' · ') : 'после генерации')}
      ${stat('Чек-лист', idx.checklist.length, idx.checklist.length ? 'пунктов в продукте' : '')}
      ${stat('Знания', pass ? fmtN(pass.length) : '—', pass ? `${plural(pass.length, 'знак', 'знака', 'знаков')} в паспорте` : 'паспорт пуст')}
    </div>`;
  const nd = newDocsForKnowledge().length;
  const learnBtn = K.busy ? '<button class="btn sm" type="button" data-act="know-stop">Остановить</button>'
    : nd ? `<button class="btn sm${pass ? '' : ' accent'}" type="button" data-act="know-learn" ${busy ? 'disabled' : ''} title="Агент прочитает документы, которые ещё не изучал, и дополнит паспорт">Изучить документы${nd < readyDocs().length ? ` · новых ${nd}` : ''}</button>`
      : readyDocs().length ? `<button class="btn sm" type="button" data-act="know-relearn" ${busy ? 'disabled' : ''} title="Все документы уже изучены. Агент прочитает их заново">Изучить заново</button>` : '';
  const passActs = learnBtn + (pass && !S.passEdit && !K.busy ? `<button class="btn sm" type="button" data-act="pass-edit" ${busy ? 'disabled' : ''}>Править</button>` : '') + (p.passportPrev?.text && !S.passEdit && !K.busy ? `<button class="btn sm" type="button" data-act="pass-prev" ${busy ? 'disabled' : ''} title="Вернуть версию от ${esc(fmtDate(p.passportPrev.updatedAt || Date.now()))}">Предыдущая версия</button>` : '');
  html += `<div class="pp-card"><div class="pp-card-h"><b>Что агент знает о продукте</b><span class="muted small">${esc(upd)}</span></div>
    ${passActs ? `<div class="pp-acts">${passActs}</div>` : ''}
    <p class="hint">Паспорт продукта пополняется автоматически после каждой генерации и учёта ответов на вопросы. Агент опирается на него в анализе, чек-листах, кейсах и ревью: те же названия экранов, роли и термины, связи между модулями. Готовые кейсы и пункты продукта агент не повторяет${S.settings.skipExisting ? '' : ' — сейчас это отключено в параметрах'}.</p>
    ${K.busy || K.log.length ? `<ul class="log">${K.log.slice(-8).map((l) => `<li class="${l.kind}">${esc(l.text)}</li>`).join('')}</ul>` : ''}${K.error ? `<p class="case-note err">${esc(K.error)}</p>` : ''}
    ${S.passEdit ? `<div class="case-edit"><label class="lbl" for="pass-text">Паспорт продукта (Markdown)</label><textarea id="pass-text" rows="14">${esc(S.passEdit.text)}</textarea><span class="hint">До ${fmtN(PASSPORT_MAX)} знаков. Правки сразу увидит вся команда и агент.</span>
        <div class="case-acts"><button class="btn accent" type="button" data-act="pass-save">Сохранить</button><button class="btn" type="button" data-act="pass-cancel">Отмена</button></div></div>`
      : pass ? `<div class="md pp-md">${mdHTML(pass)}</div>`
        : `<div class="empty pp-empty"><b>Пока пусто</b><span>Знания появятся после первой генерации. Или нажмите «Изучить документы» — агент прочитает документы продукта и составит паспорт сразу.</span><button class="btn" type="button" data-act="pass-new" ${busy ? 'disabled' : ''}>Написать вручную</button></div>`}
  </div>`;
  if (S.historyState === 'idle' && !S.running) setTimeout(() => { if (S.historyState === 'idle') loadHistory(); }, 0);
  const recent = S.history.slice(0, 3);
  html += `<div class="pp-card"><div class="pp-card-h"><b>Последние запуски</b>${S.history.length ? `<button class="link" type="button" data-act="go-tab" data-tab="history">Вся история${S.history.length > 3 ? ` · ${S.history.length}` : ''}</button>` : ''}</div>
    ${recent.length ? `<div class="pp-runs">${recent.map(histRowMini).join('')}</div>` : `<p class="hint">${S.historyState === 'ready' ? 'Запусков пока нет — выберите документы и нажмите «Сгенерировать».' : S.historyState === 'error' ? 'Не удалось загрузить запуски.' : 'Загружаю…'}</p>`}</div>`;
  return html;
}
function renderProduct(force) {
  renderProdSelect();
  const panel = $('#prod-panel'), box = $('#prod-info');
  if (!panel) return;
  panel.hidden = !S.caps.ready;
  if (!S.caps.ready) return;
  if (!force && isTyping(box)) return;
  box.innerHTML = productPanelHTML();
}

/* ================= подключение к ИИ: три варианта ================= */
const PROV_IC = { claude: 'C', openai: 'G', innocode: 'И' };
function reviewOptionsHTML(cur) {
  let h = `<option value="same" ${cur === 'same' ? 'selected' : ''}>Тот же, что для генерации</option>`;
  if (inClaude) h += `<optgroup label="Аккаунт Claude">${Object.entries(CLAUDE_TIERS).map(([k, n]) => `<option value="claude:${k}" ${cur === 'claude:' + k ? 'selected' : ''}>Claude · ${n}</option>`).join('')}</optgroup>`;
  else {
    const ready = PROV_IDS.map((p) => provConn(p)).filter((c) => c && c.apiKey);
    if (ready.length) h += `<optgroup label="По ключу API">${ready.map((c) => `<option value="conn:${c.id}" ${cur === 'conn:' + c.id ? 'selected' : ''}>${esc(PROVIDERS[provOfConn(c.id)].title)} · ${esc(c.model)}</option>`).join('')}</optgroup>`;
  }
  if (cur !== 'same' && !h.includes(`value="${esc(cur)}"`)) h += `<option value="${esc(cur)}" selected>${esc(aiLabel(cur))}</option>`;
  return h;
}
function provStatus(pid) {
  if (pid === 'claude' && inClaude) return S.caps.sample ? ['ok', 'Подключено'] : S.caps.ready ? ['warn', 'Недоступно'] : ['', 'Проверяю…'];
  if (inClaude) return ['', 'Автономная версия'];
  return provConn(pid)?.apiKey ? ['ok', 'Ключ указан'] : ['warn', 'Нужен ключ'];
}
function provBodyHTML(pid) {
  const P = PROVIDERS[pid];
  if (pid === 'claude' && inClaude) {
    const t = parseAI(S.settings.genAI), tier = t?.kind === 'claude' ? t.tier : 'default';
    return `<div class="field"><label class="lbl" for="pc-tier">Модель</label><select id="pc-tier">${Object.entries(CLAUDE_TIERS).map(([k, n]) => `<option value="${k}" ${tier === k ? 'selected' : ''}>Claude · ${n}</option>`).join('')}</select></div>
      <p class="hint">QA pro работает от имени вашего аккаунта Claude на claude.ai: запросы расходуют лимит аккаунта, ключи и пароли не нужны.</p>`;
  }
  const c = provConn(pid) || { apiKey: '', model: P.model, baseUrl: P.baseUrl };
  const t = S.provTest?.pid === pid ? S.provTest : null;
  return `<div class="grid2"><div class="field"><label class="lbl" for="pk-${pid}">Ключ API</label><input id="pk-${pid}" type="password" autocomplete="off" spellcheck="false" data-pk="${pid}" value="${esc(c.apiKey || '')}" placeholder="${esc(P.keyPh)}"></div>
      <div class="field"><label class="lbl" for="pm-${pid}">Модель</label><input id="pm-${pid}" type="text" class="mono" list="pml-${pid}" spellcheck="false" data-pm="${pid}" value="${esc(c.model || P.model)}"><datalist id="pml-${pid}">${P.models.map((m) => `<option value="${esc(m)}"></option>`).join('')}</datalist></div></div>
    ${pid === 'innocode' ? `<div class="field"><label class="lbl" for="pu-${pid}">Адрес API</label><input id="pu-${pid}" type="text" class="mono" spellcheck="false" data-pu="${pid}" value="${esc(c.baseUrl || P.baseUrl)}"></div>` : ''}
    <div class="row"><button class="btn" type="button" data-prov-test="${pid}" ${c.apiKey ? '' : 'disabled'}>Проверить подключение</button>${t ? `<span class="case-note ${t.ok === false ? 'err' : t.ok ? 'ok' : ''}" id="prov-test-note">${esc(t.text)}</span>` : ''}</div>
    <p class="hint">${esc(P.keyWhere)}${pid === 'claude' ? ' Вход через аккаунт Claude в сторонних приложениях Anthropic не разрешает, поэтому здесь нужен ключ API; через аккаунт работает версия QA pro на claude.ai.' : ''} Ключ хранится только в этом браузере.</p>`;
}
function updProvStatus() {
  for (const pid of PROV_IDS) {
    const el = $('#prov-st-' + pid);
    if (!el) continue;
    const [c, t] = provStatus(pid);
    el.className = 'prov-st ' + c; el.textContent = t;
  }
  const b = $('#prov-list [data-prov-test]');
  if (b) b.disabled = !provConn(b.dataset.provTest)?.apiKey;
}
function renderProviders(force) {
  const box = $('#prov-list');
  if (!box) return;
  const rv = $('#review-ai');
  if (rv && document.activeElement !== rv) rv.innerHTML = reviewOptionsHTML(S.settings.reviewAI);
  renderAIHint();
  if (!force && isTyping(box)) { updProvStatus(); return; }
  const cur = curProv();
  box.innerHTML = PROV_IDS.map((pid) => {
    const P = PROVIDERS[pid], on = cur === pid, dis = inClaude && pid !== 'claude';
    const [stc, stt] = provStatus(pid);
    const sub = pid === 'claude' ? (inClaude ? 'Вход через ваш аккаунт на claude.ai — ключ не нужен' : 'Ключ API из Claude Console') : pid === 'openai' ? 'Ключ API OpenAI' : 'Ключ API ИИ-центра inno.tech';
    return `<div class="prov${on ? ' on' : ''}${dis ? ' dis' : ''}" data-prov="${pid}">
      <label class="prov-h"><input type="radio" name="prov" value="${pid}" ${on ? 'checked' : ''} ${dis ? 'disabled' : ''}><span class="prov-ic p-${pid}" aria-hidden="true">${PROV_IC[pid]}</span><span class="prov-t"><b>${esc(P.title)}</b><small>${esc(sub)}</small></span><span class="prov-st ${stc}" id="prov-st-${pid}">${esc(stt)}</span></label>
      ${dis ? '<div class="prov-b"><p class="hint">Работает в автономной версии QA pro: страница на claude.ai не выходит в интернет. <button class="link inline" type="button" data-act="standalone">Скачать автономную версию</button></p></div>' : on ? `<div class="prov-b">${provBodyHTML(pid)}</div>` : ''}
    </div>`;
  }).join('');
  const lg = $('#prov-legacy'), legacy = !cur ? parseAI(S.settings.genAI) : null;
  if (lg) { lg.hidden = !legacy; lg.textContent = legacy ? `Сейчас выбрано прежнее подключение «${legacy.kind === 'conn' ? aiAbbrName(legacy.conn) : aiLabel(S.settings.genAI)}». Выберите один из вариантов выше.` : ''; }
}
function afterAIChange() { saveSettings(); renderStatus(); renderAIHint(); renderRunControls(); renderParams(); if (S.tab === 'review' || S.tab === 'agent') renderTab(); }
function selectProv(pid) {
  if (inClaude && pid !== 'claude') return;
  if (pid === 'claude' && inClaude) { const t = parseAI(S.settings.genAI); S.settings.genAI = 'claude:' + (t?.kind === 'claude' ? t.tier : 'default'); }
  else { const c = ensureProv(pid); saveConns(); S.settings.genAI = 'conn:' + c.id; }
  S.provTest = null;
  renderProviders(true); afterAIChange();
}
function onProvInput(e) {
  const t = e.target;
  if (t.name === 'prov' && t.checked) return selectProv(t.value);
  if (t.id === 'pc-tier') { S.settings.genAI = 'claude:' + t.value; return afterAIChange(); }
  const pid = t.dataset.pk || t.dataset.pm || t.dataset.pu;
  if (!pid || !PROVIDERS[pid]) return;
  const c = ensureProv(pid), v = t.value.trim();
  if (t.dataset.pk) c.apiKey = v; else if (t.dataset.pm) c.model = v || PROVIDERS[pid].model; else c.baseUrl = v || PROVIDERS[pid].baseUrl;
  saveConns();
  if (curProv() === pid) S.settings.genAI = 'conn:' + c.id;
  if (S.provTest?.pid === pid) { S.provTest = null; $('#prov-test-note')?.remove(); }
  saveSettings(); updProvStatus(); renderAIHint(); renderRunControls();
  const rv = $('#review-ai'); if (rv) rv.innerHTML = reviewOptionsHTML(S.settings.reviewAI);
}
async function onProvClick(e) {
  const b = e.target.closest('[data-prov-test],[data-act]');
  if (!b || b.disabled) return;
  if (b.dataset.act === 'standalone') return downloadStandalone();
  const pid = b.dataset.provTest, c = provConn(pid);
  if (!c) return;
  S.provTest = { pid, ok: null, text: 'Проверяю…' }; renderProviders(true);
  try { const r = await testConn(c); S.provTest = { pid, ok: true, text: 'Связь есть, модель отвечает: ' + JSON.stringify(r).slice(0, 120) }; }
  catch (err) { S.provTest = { pid, ok: false, text: errText(err) }; }
  if (!$('#set-model')?.hidden) renderProviders(true);
}
/* ---------- модель по этапам ---------- */
const STAGE_OPT = { same: 'Как основная модель', quick: 'Быстрая (Haiku)', default: 'Стандартная (Sonnet)', complex: 'Максимальная (Opus)' };
function stageSupported(stage) {   // уровень меняет модель у Claude (аккаунт или ключ); у ChatGPT и Иннокода модель одна
  const t = parseAI(stage === 'review' ? aiValue('review') : S.settings.genAI);
  return !!t && (t.kind === 'claude' || !!PROVIDERS[provOfConn(t.conn.id)]?.tiers);
}
function renderStages() {
  const box = $('#stage-models');
  if (!box) return;
  const st = S.settings.stages, sup = STAGES.map((x) => stageSupported(x.id)), any = sup.some(Boolean);
  const same = STAGES.every((x) => st[x.id] === x.rec), allMain = STAGES.every((x) => st[x.id] === 'same');
  box.innerHTML = `<div class="stage-list">${STAGES.map((x, i) => {
    const opts = STAGE_TIER_VALUES.map((v) => `<option value="${v}" ${st[x.id] === v ? 'selected' : ''}>${STAGE_OPT[v]}${v === x.rec ? ' — рекомендуем' : ''}</option>`).join('');
    return `<div class="stage-row"><div class="stage-h"><label class="lbl" for="stage-${x.id}">${esc(x.title)}</label><span class="small muted">${esc(x.desc)}</span></div>
      <select id="stage-${x.id}" data-stage="${x.id}" ${sup[i] ? '' : 'disabled'}>${opts}</select>
      <p class="hint stage-why"><b>Рекомендуем: ${esc(STAGE_OPT[x.rec].split(' (')[0].toLowerCase())}.</b> ${esc(x.why)}</p></div>`;
  }).join('')}</div>
    <div class="stage-acts"><button class="btn sm accent" type="button" data-stage-act="apply" ${any && !same ? '' : 'disabled'}>Применить рекомендации</button><button class="btn sm" type="button" data-stage-act="reset" ${any && !allMain ? '' : 'disabled'}>Все этапы — как основная</button></div>
    <p class="hint" id="stage-note">${any
    ? (same ? 'Выбрана рекомендуемая раскладка: сильная модель там, где важно качество, быстрая — там, где расход велик, а решения простые.' : allMain ? 'Сейчас все этапы идут на одной модели. Рекомендуемая раскладка: анализ и кейсы — стандартная, ревью и служебные шаги — быстрая; на нашем тестовом ТЗ это переносит на быструю модель около 55% входных токенов.' : 'Раскладка отличается от рекомендуемой — это нормально, если вы её проверили на своих документах.')
    : 'Для ChatGPT и Иннокода уровень модели по этапам не переключается: используется одна модель. Выбор работает для аккаунта Claude и для подключения по ключу Claude.'}
    Выбор по этапам сильнее экономного режима. Рекомендации — по замеру на одном ТЗ и ценам API на октябрь 2026; проверьте на своих документах.</p>`;
}
function renderAIHint() {
  const p1 = aiProblem(S.settings.genAI), rv2 = aiValue('review'), p2 = S.settings.reviewAI === 'same' ? '' : aiProblem(rv2);
  const el = $('#ai-hint');
  if (!el) return;
  el.textContent = p1 || p2 || '';
  el.hidden = !(p1 || p2);
}
/* загрузчик в Сферу ФТ: исходники расширения вшиты при сборке, архив собирается здесь (zip без сжатия) */
const UPLOADER_FILES = /*__UPLOADER__*/null;
const BRIDGE_FILES = /*__BRIDGE__*/null;
function crc32(bytes) {
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < bytes.length; i++) { let c = (crc ^ bytes[i]) & 0xFF; for (let k = 0; k < 8; k++) c = c & 1 ? (c >>> 1) ^ 0xEDB88320 : c >>> 1; crc = (crc >>> 8) ^ c; }
  return (crc ^ 0xFFFFFFFF) >>> 0;
}
function makeZip(files) {
  const enc = new TextEncoder(), parts = [], central = [];
  const d = new Date(), time = (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1), date = ((d.getFullYear() - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate();
  let offset = 0;
  for (const f of files) {
    const name = enc.encode(f.name), data = enc.encode(f.text), crc = crc32(data);
    const lh = new DataView(new ArrayBuffer(30));
    [[0, 0x04034b50, 4], [4, 20, 2], [6, 0x0800, 2], [8, 0, 2], [10, time, 2], [12, date, 2], [14, crc, 4], [18, data.length, 4], [22, data.length, 4], [26, name.length, 2], [28, 0, 2]].forEach(([o, v, n]) => (n === 4 ? lh.setUint32(o, v, true) : lh.setUint16(o, v, true)));
    parts.push(new Uint8Array(lh.buffer), name, data);
    const ch = new DataView(new ArrayBuffer(46));
    [[0, 0x02014b50, 4], [4, 20, 2], [6, 20, 2], [8, 0x0800, 2], [10, 0, 2], [12, time, 2], [14, date, 2], [16, crc, 4], [20, data.length, 4], [24, data.length, 4], [28, name.length, 2], [30, 0, 2], [32, 0, 2], [34, 0, 2], [36, 0, 2], [38, 0, 4], [42, offset, 4]].forEach(([o, v, n]) => (n === 4 ? ch.setUint32(o, v, true) : ch.setUint16(o, v, true)));
    central.push(new Uint8Array(ch.buffer), name);
    offset += 30 + name.length + data.length;
  }
  const size = central.reduce((a, b) => a + b.length, 0), end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true); end.setUint32(12, size, true); end.setUint32(16, offset, true);
  return new Blob([...parts, ...central, new Uint8Array(end.buffer)], { type: 'application/zip' });
}
function downloadBridge() {
  if (!BRIDGE_FILES) return toast('Мост не вшит в эту сборку QA pro.', 'err');
  downloadFile('qa-pro-bridge.mcpb', makeZip(Object.entries(BRIDGE_FILES).map(([name, text]) => ({ name, text }))));
}
function downloadUploaderZip() {
  if (!UPLOADER_FILES) return toast('Архив загрузчика не вшит в эту сборку QA pro.', 'err');
  downloadFile('qa-pro-sfera-uploader.zip', makeZip(Object.entries(UPLOADER_FILES).map(([name, text]) => ({ name: 'qa-pro-sfera-uploader/' + name, text }))));
}
function downloadStandalone() {
  fetch('qa-pro.html').then((r) => { if (!r.ok) throw new Error(); return r.text(); })
    .then((html) => downloadFile('qa-pro.html', html))
    .catch(() => toast('Не удалось получить автономную версию. Обновите страницу и попробуйте снова.', 'err'));
}
const STANDALONE_NOTE = (what) => `<div class="banner info"><div><b>${what} работают в автономной версии.</b> На claude.ai страница изолирована от интернета, поэтому внешние сервисы отсюда недоступны. Автономная версия QA pro — один HTML-файл: откройте его у себя или разместите на внутреннем веб-сервере. Настройки и ключи там вводятся заново — они не покидают браузер.<div style="margin-top:8px"><button class="btn accent" type="button" data-act="standalone">Скачать автономную версию</button></div></div></div>`;
function openDialog(id) { $('#' + id).hidden = false; $('#' + id + ' .ov-card')?.focus(); }
function closeDialog(id) { $('#' + id).hidden = true; }

/* ================= продукт: создание и переименование ================= */
function openProdDialog(mode) {
  const p = mode === 'edit' ? curProduct() : null;
  S.prodDlg = { mode, name: p?.name || '', description: p?.description || '', busy: false, error: '' };
  renderProdDialog(); openDialog('prod-ov');
  setTimeout(() => $('#prod-name')?.focus(), 0);
}
function renderProdDialog() {
  const d = S.prodDlg;
  if (!d) return;
  $('#prod-title').textContent = d.mode === 'edit' ? 'Продукт' : 'Новый продукт';
  $('#prod-body').innerHTML = `<div class="field"><label class="lbl" for="prod-name">Название</label><input id="prod-name" type="text" maxlength="80" value="${esc(d.name)}" placeholder="Например: Личный кабинет клиента" data-pf="name"></div>
    <div class="field"><label class="lbl" for="prod-desc">Коротко о продукте — необязательно</label><textarea id="prod-desc" rows="3" maxlength="500" data-pf="description" placeholder="Например: веб-кабинет и мобильное приложение для клиентов; модули — платежи, карты, профиль">${esc(d.description)}</textarea><p class="hint">Описание получает агент, когда составляет знания о продукте.</p></div>
    ${d.mode === 'new' ? `<p class="hint">У продукта свои документы, доп. контекст от QA, запуски и знания агента. Правила, шаблоны и формат экспорта — общие для всех продуктов.${inClaude ? ' Продукт увидит вся команда.' : ''}</p>` : ''}
    ${d.error ? `<p class="case-note err">${esc(d.error)}</p>` : ''}
    <div class="row"><button class="btn accent" type="button" data-pact="save" ${d.busy ? 'disabled' : ''}>${d.mode === 'edit' ? 'Сохранить' : 'Создать и открыть'}</button><button class="btn" type="button" data-close>Отмена</button></div>`;
}
async function saveProdDialog() {
  const d = S.prodDlg;
  if (!d || d.busy) return;
  const name = d.name.trim();
  if (!name) { d.error = 'Введите название продукта.'; return renderProdDialog(); }
  if (S.products.some((p) => p.id !== (d.mode === 'edit' ? S.productId : null) && normKey(p.name) === normKey(name))) { d.error = 'Продукт с таким названием уже есть.'; return renderProdDialog(); }
  d.busy = true; d.error = ''; renderProdDialog();
  try {
    if (d.mode === 'edit') {
      await updateProduct(S.productId, { name: name.slice(0, 80), description: d.description.trim().slice(0, 500) });
      renderProdSelect(); renderProduct(); toast('Продукт сохранён');
    } else {
      const id = await createProduct(name, d.description);
      closeDialog('prod-ov'); S.prodDlg = null;
      await switchProduct(id); toast(`Продукт «${name}» создан`);
      return;
    }
    closeDialog('prod-ov'); S.prodDlg = null;
  } catch { d.busy = false; d.error = 'Не удалось сохранить — нужны права на изменение данных приложения.'; renderProdDialog(); }
}

/* ================= ТМС: настройки и панель загрузки ================= */
function renderTmsDialog() {
  const c = S.tmsDraft, k = TMS_KINDS[c.kind];
  const inp = (key, lbl, ph = '', type = 'text', mono = true) => `<div class="field"><label class="lbl" for="tm-${key}">${lbl}</label><input id="tm-${key}" data-tm="${key}" type="${type}" ${type === 'password' ? 'autocomplete="off"' : ''} class="${mono ? 'mono' : ''}" value="${esc(c[key] ?? '')}" placeholder="${esc(ph)}"></div>`;
  let fields = '';
  if (c.kind === 'testit') fields = `${inp('baseUrl', 'Адрес Test IT', 'https://company.testit.software')}<div class="grid2">${inp('token', 'Токен (секретный ключ API)', '', 'password')}${inp('project', 'ID проекта', 'UUID')}</div>
    <div class="grid2">${inp('section', 'ID раздела — необязательно', 'UUID')}<div class="field"><label class="lbl" for="tm-state">Статус кейсов</label><select id="tm-state" data-tm="state">${['NotReady', 'NeedsWork', 'Ready'].map((x) => `<option value="${x}" ${c.state === x ? 'selected' : ''}>${{ NotReady: 'Не готов', NeedsWork: 'Требует доработки', Ready: 'Готов' }[x]}</option>`).join('')}</select></div></div>
    <div class="grid2">${inp('duration', 'Длительность по умолчанию, мин', '10', 'number')}<div></div></div>`;
  else if (c.kind === 'qase') fields = `${inp('baseUrl', 'Адрес API', 'https://api.qase.io/v1')}<div class="grid2">${inp('token', 'Токен API', '', 'password')}${inp('project', 'Код проекта', 'DEMO')}</div><div class="grid2">${inp('section', 'ID сьюта — необязательно', '12')}<div></div></div>`;
  else if (c.kind === 'testrail') fields = `${inp('baseUrl', 'Адрес TestRail', 'https://company.testrail.io')}<div class="grid2">${inp('user', 'Логин (email)', 'qa@company.ru', 'text', false)}${inp('token', 'API-ключ', '', 'password')}</div><div class="grid2">${inp('section', 'ID раздела (section_id)', '123')}<div></div></div>`;
  else if (c.kind === 'sfera') {
    if (!S.sferaExt) sferaPing().then(() => { if (!$('#set-tms')?.hidden) renderTmsDialog(); });
    const x = S.sferaExt;
    const why = x && !x.ok && x.stage !== 'ext' ? `<ol class="sfera-steps diag">
        <li>Обновите страницу QA pro (Ctrl+F5): расширение подключается к страницам, открытым после его установки. Версия 1.1 и новее подключается и к уже открытым.</li>
        <li>QA pro должен быть открыт в Chrome, Edge или Яндекс Браузере, где установлен загрузчик.</li>
        <li>В <span class="mono">chrome://extensions</span> → «Сведения» загрузчика → «Доступ к сайтам» не должно стоять «По нажатию».</li>
        <li>Если не помогло — в настройках загрузчика (правый клик по его значку → «Параметры») включите «Работать на любых сайтах» и обновите страницу.</li>
        ${inClaude ? '' : '<li>Если QA pro открыт с диска — включите для загрузчика «Разрешить доступ к URL файлов».</li>'}
      </ol>
      <p class="diag-where">Адрес окна QA pro: <span class="mono">${esc(x.where || '—')}</span></p>` : '';
    const relay = !!x && !x.ok && relayOn();
    if (relay && S.relayPeer === undefined) { S.relayPeer = null; relayPresence().then(() => { if (!$('#set-tms')?.hidden) renderTmsDialog(); renderTmsBar(); }); }
    const peer = S.relayPeer, ago = (t) => { const m = Math.round((Date.now() - t) / 60000); return m < 1 ? 'только что' : `${m} мин назад`; };
    const peerText = !peer ? 'проверяю…' : peer.online ? `<b>на связи</b> · загрузчик ${esc(peer.version)} · отклик ${ago(peer.at)}` : `<b>не открыт</b>${peer.at ? ` · последний отклик ${new Date(peer.at).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}` : ''}`;
    const relaySteps = `<ol class="sfera-steps diag">
        <li>Откройте QA pro в Chrome, где установлен загрузчик: <a href="${QA_PRO_URL}" target="_blank" rel="noopener">открыть</a> · <button class="link" type="button" data-act="relay-copy">скопировать ссылку</button>. Вкладку не закрывайте — удобно её закрепить.</li>
        <li>Чтобы вкладка открывалась сама, в настройках загрузчика (правый клик по его значку → «Параметры») включите «Держать QA pro открытым».</li>
        <li>Здесь нажимайте «Загрузить в Сферу ФТ» — окно загрузчика появится в Chrome.</li>
      </ol>
      <p class="diag-where">QA pro в Chrome: ${peerText}</p>`;
    const host = hostOn() && !!x && !x.ok;
    if (host && S.hostBridge === undefined) { S.hostBridge = null; hostPing().then(() => { if (!$('#set-tms')?.hidden) renderTmsDialog(); renderTmsBar(); }); }
    const hb = S.hostBridge;
    const hostText = hb === null || hb === undefined ? 'проверяю…' : hb.ok ? `<b>работает</b> · версия ${esc(hb.version)}` : `<b>не найден</b> — ${esc(hb.error || '')}`;
    const extText = !hb?.ok ? '—' : hb.extension?.connected ? `<b>подключён</b> · версия ${esc(hb.extension.version || '?')}` : '<b>не подключён</b> — откройте Chrome; нужна версия загрузчика 1.3 или новее';
    const hostHTML = `<b>Вы в приложении Claude: расширений браузера здесь нет.</b> Загрузчик в Chrome получает кейсы через мост qa-pro-bridge — расширение приложения Claude на этом компьютере. Окно загрузчика откроется в Chrome, отметки «в ТМС» вернутся сюда.
      <ol class="sfera-steps diag">
        <li>Скачайте мост: <button class="link" type="button" data-act="bridge-mcpb">qa-pro-bridge.mcpb</button> — и откройте файл: приложение Claude предложит его установить (или: настройки приложения → «Расширения» → установить из файла).</li>
        <li>Обновите загрузчик в Chrome до версии 1.3 — кнопка «Скачать загрузчик» ниже. Он сам подключится к мосту.</li>
        <li>Нажмите «Загрузить в Сферу ФТ» — приложение спросит разрешение на мост, окно загрузчика появится в Chrome.</li>
      </ol>
      <p class="diag-where">Мост: ${hostText}<br>Загрузчик в Chrome: ${extText}</p>
      <details class="diag-more"><summary>Без моста: через QA pro во вкладке Chrome</summary>${relaySteps}</details>`;
    const relayHTML = `<b>${inDesktopApp ? 'Вы в приложении Claude: расширений браузера здесь нет.' : 'В этом окне загрузчика нет.'}</b> Загрузка пойдёт через QA pro, открытый в Chrome с загрузчиком: задание отсюда откроет там окно загрузчика, а отметки «в ТМС» вернутся сюда.
      ${relaySteps}
      ${inDesktopApp ? '' : `<details class="diag-more"><summary>Загрузчик установлен в этом браузере, но не виден</summary>${why}</details>`}`;
    fields = `<div class="banner ${x && !x.ok && !relay && !host ? 'warn' : 'info'}"><div class="banner-body">${x?.ok ? `<b>Загрузчик найден</b> · версия ${esc(x.version)} · Сфера: ${esc(x.baseUrl || 'sfera-t1.ru')}${relayRx ? '<p class="diag-where">Эта вкладка принимает задания из приложения Claude и других окон QA pro — не закрывайте её.</p>' : ''}`
      : host ? hostHTML
        : relay ? relayHTML
        : x?.stage === 'ext' ? `<b>Загрузчик не отвечает.</b> ${esc(sferaNoExtText(x))}`
          : x ? '<b>Загрузчик не видит эту страницу.</b> Что проверить:' + why : 'Проверяю загрузчик…'}</div></div>`;
    fields += `
    <ol class="sfera-steps">
      <li>Скачайте загрузчик и распакуйте архив в папку.</li>
      <li>Откройте <span class="mono">chrome://extensions</span>, включите «Режим разработчика» и нажмите «Загрузить распакованное расширение» — выберите эту папку. Подойдёт Chrome, Edge или Яндекс Браузер.</li>
      <li>Войдите в Сферу ФТ в этом браузере: загрузчик работает от вашего имени, токен вводить не нужно.</li>
      <li>Обновите страницу QA pro и нажмите «Проверить подключение».</li>
    </ol>
    <div class="row"><button class="btn" type="button" data-act="sfera-zip">Скачать загрузчик (.zip)</button></div>
    <p class="hint">При загрузке откроется окно загрузчика: там выбирается проект и раздел Сферы (по ссылке или из открытой вкладки) и подтверждается загрузка. Смоук-кейсы получают метку SMOKE, регрессионные — отметку «Регрессионный».${inClaude ? ' Если QA pro открыт в приложении Claude для компьютера, задание уходит в QA pro во вкладке Chrome с загрузчиком. Запасной путь — «Скачать JSON для загрузчика» у тест-кейсов.' : ''}</p>`;
  }
  else fields = `${inp('url', 'Адрес (POST)', 'https://tms-gateway.company.ru/api/test-cases')}<div class="grid2">${inp('token', 'Токен (Bearer) — необязательно', '', 'password')}<div class="field"><label class="lbl" for="tm-mode">Отправка</label><select id="tm-mode" data-tm="mode"><option value="case" ${c.mode !== 'all' ? 'selected' : ''}>По одному кейсу</option><option value="all" ${c.mode === 'all' ? 'selected' : ''}>Все кейсы одним запросом</option></select></div></div>
    <div class="field"><label class="lbl" for="tm-headers">Заголовки, JSON</label><textarea id="tm-headers" data-tm="headers" class="code" rows="2" spellcheck="false" placeholder='{"X-Project": "…"}'>${esc(c.headers || '')}</textarea></div>`;
  $('#tms-body').innerHTML = (inClaude && c.kind !== 'sfera' ? STANDALONE_NOTE('Загрузка в ТМС и проверка подключения') : '') + `<div class="conn-form">
    <div class="field"><label class="lbl" for="tm-kind">Система управления тестированием</label><select id="tm-kind" data-tm="kind">${Object.entries(TMS_KINDS).map(([id, x]) => `<option value="${id}" ${c.kind === id ? 'selected' : ''}>${x.name}</option>`).join('')}</select><span class="hint">${esc(k.hint)}</span></div>
    ${fields}
    ${S.tmsTest ? `<p class="case-note ${S.tmsTest.ok === false ? 'err' : ''}">${esc(S.tmsTest.text)}</p>` : ''}
    <div class="row"><button class="btn accent" type="button" data-tmb="save">Сохранить</button><button class="btn" type="button" data-tmb="test" ${inClaude && c.kind !== 'sfera' ? 'disabled title="Проверка работает в автономной версии"' : ''}>Проверить подключение</button>${tmsDirty() ? '<span class="cfg-state dirty"><b>Есть несохранённые изменения</b></span>' : ''}</div></div>
    <p class="hint">${c.kind === 'sfera' ? 'Ключи и токены QA pro не хранит: вход в Сферу остаётся в браузере.' : 'Токен хранится только в этом браузере.'} ${c.kind === 'sfera' ? 'В Сферу уходят название, описание, предусловия, шаги с ожидаемыми результатами и приоритет; смоук — метка SMOKE, регресс — отметка «Регрессионный», без метки AI_gen.' : 'В ТМС уходят название, предусловия, шаги с ожидаемыми результатами, приоритет и теги, в том числе «smoke» и «regression».'} Уже загруженные кейсы помечаются и повторно не отправляются.</p>`;
}
/* ---------- настройки: фоновая работа ---------- */
function renderBgPane(refresh) {
  const el = $('#bg-body');
  if (!el) return;
  if (refresh) {
    workerPeer().then(() => { if (!$('#set-bg')?.hidden) renderBgPane(); });
    if (hostOn() && S.hostBridge === undefined) { S.hostBridge = null; hostPing().then(() => { if (!$('#set-bg')?.hidden) renderBgPane(); }); }
  }
  const me = workerOn(), peer = S.workerPeer;
  const ago = (t) => { const m = Math.round((Date.now() - t) / 60000); return m < 1 ? 'только что' : `${m} мин назад`; };
  const status = !inClaude ? '<b>Фоновая работа доступна в QA pro на claude.ai.</b> Автономная версия работает, только пока открыта.'
    : me ? `<b>Эта вкладка — фоновый исполнитель.</b> ${W.note ? `Сейчас: ${esc(W.note)}.` : 'Ждёт работу.'} Не закрывайте её.`
      : peer === undefined || peer === null ? 'Проверяю фоновый исполнитель…'
        : peer.online ? `<b>Фоновый исполнитель на связи</b> · отклик ${ago(peer.at)} · модель: ${esc(peer.ai || '?')}${peer.aiReady ? '' : ' (не настроена)'} · загрузчик: ${peer.uploader ? 'подключён' : 'нет'}${peer.doing ? ` · сейчас: ${esc(peer.doing)}` : ''}`
          : `<b>Фоновый исполнитель не на связи.</b>${peer.at ? ` Последний отклик — ${new Date(peer.at).toLocaleString('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}.` : ' Ещё не настроен.'}`;
  const hb = S.hostBridge;
  const bridgeLine = !hostOn() ? '' : `<p class="diag-where">Мост: ${!hb ? 'проверяю…' : hb.ok ? `<b>работает</b> · ${hb.core === 'background' ? 'отдельным фоновым процессом — переживает выход из приложения' : hb.core === 'app' ? 'внутри приложения — остановится вместе с ним' : 'версия ' + esc(hb.version)}` : `<b>не найден</b> — ${esc(hb.error || '')}`}${hb?.ok ? ` · загрузчик: ${hb.extension?.connected ? 'подключён' : 'не подключён'}` : ''}</p>`;
  const v = S.settings.genAI;
  el.innerHTML = `<div class="banner ${me || peer?.online ? 'info' : 'warn'}"><div class="banner-body">${status}</div></div>
    <p class="hint">Когда окно QA pro закрывают посреди работы, её доделывает фоновый исполнитель — QA pro, открытый во вкладке браузера (лучше Chrome с загрузчиком):</p>
    <ul class="sfera-steps">
      <li><b>Генерация кейсов</b> продолжается с места остановки. Откройте QA pro позже — результат в «Истории», а если генерация ещё идёт, вы увидите её ход.</li>
      <li><b>Разбор документов</b> в базу знаний доделывается для документов, добавленных в закрытом окне.</li>
      <li><b>Загрузка в Сферу ФТ</b>: можно отправить кейсы и закрыть QA pro — загрузчик дождётся вас в Chrome, а отметки «в ТМС» появятся при следующем открытии.</li>
    </ul>
    ${workerAllowed() ? `<label class="switch"><input type="checkbox" id="bg-worker" ${me ? 'checked' : ''}><span class="sw"></span><span>Этот браузер — фоновый исполнитель</span></label>
      <p class="hint">Модель здесь: <b>${esc(aiLabel(v))}</b>${aiReady(v) ? '' : ` — ${esc(aiProblem(v))}`}. ${parseAI(v)?.kind === 'claude' ? 'Запросы расходуют лимит вашего аккаунта Claude; если вкладка спросит доступ к Claude — разрешите. ' : ''}Чтобы вкладка всегда была открыта и браузер её не выгружал, в настройках загрузчика включите «Держать QA pro открытым».</p>`
      : inDesktopApp ? `<p class="hint">Окно приложения Claude при закрытии останавливается, поэтому фоновым исполнителем делают QA pro в Chrome: <a href="${QA_PRO_URL}" target="_blank" rel="noopener">откройте его там</a> (<button class="link" type="button" data-act="relay-copy">скопировать ссылку</button>) → шестерёнка → «Фон» → «Этот браузер — фоновый исполнитель».</p>` : ''}
    ${bridgeLine}`;
}
function onBgChange(e) {
  if (e.target.id !== 'bg-worker') return;
  lsSet(WORKER_KEY, e.target.checked);
  if (e.target.checked) { workerStart(); toast('Эта вкладка — фоновый исполнитель'); } else { workerStop(); toast('Фоновый исполнитель выключен'); }
  renderBgPane();
}
function openTms() { S.tmsDraft = { ...S.tms }; S.tmsTest = null; openSettings('tms'); }
async function onTmsClick(e) {
  const b = e.target.closest('[data-tmb],[data-act]');
  if (!b || b.disabled) return;
  if (b.dataset.act === 'standalone') return downloadStandalone();
  if (b.dataset.act === 'sfera-zip') return downloadUploaderZip();
  if (b.dataset.act === 'relay-copy') return copyText(QA_PRO_URL);
  if (b.dataset.act === 'bridge-mcpb') return downloadBridge();
  const a = b.dataset.tmb;
  if (a === 'save') { S.tms = { ...S.tmsDraft }; saveTms(); toast('Настройки ТМС сохранены'); renderTmsDialog(); renderCfgTabs(); renderTmsBar(); return; }
  if (a === 'test') {
    const p = S.tmsDraft.kind === 'sfera' ? '' : tmsProblem(S.tmsDraft); // загрузчик проверяем заново: его могли только что установить
    if (p) { S.tmsTest = { ok: false, text: p }; return renderTmsDialog(); }
    S.tmsTest = { ok: null, text: 'Проверяю…' }; renderTmsDialog();
    if (S.tmsDraft.kind === 'sfera') { S.relayPeer = undefined; S.hostBridge = undefined; }
    try { S.tmsTest = { ok: true, text: await tmsTestConn(S.tmsDraft) }; } catch (err) { S.tmsTest = { ok: false, text: errText(err) }; }
    renderTmsDialog();
  }
}
function onTmsInput(e) {
  const k = e.target.dataset.tm;
  if (!k || !S.tmsDraft) return;
  S.tmsDraft[k] = e.target.value;
  if (k === 'kind') { S.tmsTest = null; if (e.target.value === 'sfera') S.sferaExt = null; renderTmsDialog(); }
  renderCfgTabs();
}
// Сфера ФТ: в загрузчик уходят все кейсы запуска (кроме устаревших), включая уже загруженные — дубли допускаются осознанно.
// ТМС: как раньше — с учётом фильтров и без уже загруженных, если не включена повторная загрузка.
function tmsPending() {
  if (S.tms.kind === 'sfera') return activeCases(S.run);
  const list = filteredCases().filter((c) => c.status !== 'obsolete'); return S.tmsReup ? list : list.filter((c) => !c.tms);
}
function renderTmsBar() {
  const el = $('#tms-bar');
  if (!el || !S.run) return;
  const list = filteredCases(), pending = tmsPending();
  const done = list.filter((c) => c.tms).length, obs = list.filter((c) => c.status === 'obsolete').length;
  el.innerHTML = `<div class="tms-row">
      ${S.tmsBusy ? `<button class="btn" type="button" data-act="tms-stop">${S.relay ? 'Отменить задание' : 'Остановить загрузку'}</button>` : `<button class="btn accent" type="button" data-act="tms-upload" ${pending.length ? '' : 'disabled'}>Загрузить в ${S.tms.kind === 'sfera' ? 'Сферу ФТ' : 'ТМС'}${pending.length ? ` (${pending.length})` : ''}</button>`}
      <button class="icon-btn gear" type="button" data-act="tms-settings" aria-label="Настройки загрузки в ТМС" title="Настройки ТМС">${ICON.gear}</button>
      ${S.tms.kind === 'sfera' ? `<button class="btn" type="button" data-act="sfera-json" ${activeCases(S.run).length ? '' : 'disabled'} title="Все кейсы этого запуска (кроме устаревших), без учёта фильтров и уже загруженных. Для ручной загрузки: откройте файл в окне загрузчика">Скачать JSON для загрузчика (${activeCases(S.run).length})</button>` : ''}
      <span class="small muted">${esc(tmsSummary())}${done ? ` · уже загружено ${done}` : ''}</span>
      ${done && S.tms.kind !== 'sfera' ? `<label class="chk small"><input type="checkbox" id="tms-reup" ${S.tmsReup ? 'checked' : ''}> загрузить повторно</label>` : ''}
    </div>
    ${obs ? `<p class="hint">Устаревшие кейсы (${obs}) в ТМС не загружаются — уберите их там вручную или верните в актуальные.</p>` : ''}
    ${S.tmsLog.length ? `<ul class="log">${S.tmsLog.slice(-30).map((l) => `<li class="${l.kind}">${esc(l.text)}</li>`).join('')}</ul>` : ''}
    ${S.relay && ['sending', 'pending'].includes(S.relay.status) && !S.relayPeer?.online ? `<p class="hint relay-help"><a href="${QA_PRO_URL}" target="_blank" rel="noopener">Открыть QA pro в браузере</a> · <button class="link" type="button" data-act="relay-copy">скопировать ссылку</button> — откройте её в Chrome, где установлен загрузчик.</p>` : ''}
    ${inClaude && S.tms.kind !== 'sfera' ? '<p class="hint">Загрузка в ТМС работает в автономной версии: на claude.ai страница изолирована от интернета. <button class="link" type="button" data-act="standalone">Скачать автономную версию</button></p>' : ''}`;
  if (S.tms.kind === 'sfera' && S.sferaExt === undefined) { S.sferaExt = null; sferaPing().then(() => { if (S.tab === 'cases') renderTmsBar(); }); }
  if (S.tms.kind === 'sfera' && relayOn()) relayCheck();
  if (S.tms.kind === 'sfera' && hostOn()) hostResume();
}

/* ================= ручная правка тест-кейса: форма ================= */
const STEP_NUM_KEYS = ['step', '№', 'number', 'n', 'order', 'no', 'num', 'шаг'];
const isFlatObj = (o) => !!o && typeof o === 'object' && !Array.isArray(o) && Object.values(o).every((y) => y === null || typeof y !== 'object');
function blankFrom(v, key) {
  if (Array.isArray(v)) return v.length ? [blankFrom(v[0])] : [];
  if (v && typeof v === 'object') { const o = {}; for (const [k, x] of Object.entries(v)) o[k] = blankFrom(x, k); return o; }
  if (typeof v === 'number') return STEP_NUM_KEYS.includes(String(key).toLowerCase()) ? 1 : 0;
  if (typeof v === 'boolean') return false;
  return '';
}
function rowShape(type, key) {
  const info = tplInfo(type);
  const v = info.ok ? info.structure[key] : null;
  return Array.isArray(v) && isFlatObj(v[0]) ? v[0] : null;
}
function enterForm(c) {
  const ui = caseUI(c.uid);
  ui.mode = 'form'; ui.form = JSON.parse(JSON.stringify(cleanCase(c.testCase || {}))); ui.formJSON = {}; ui.formReqs = c.requirementIds.join(', '); ui.error = ''; ui.note = ''; ui.open = true;
}
function caseFormHTML(c, ui) {
  const f = ui.form, info = tplInfo(c.type), U = c.uid;
  const fid = (p) => `ff-${U}-${String(p).replace(/[^a-zA-Z0-9_-]/g, '_')}`;
  const lbl = (k, forId) => `<label class="lbl" for="${forId}">${esc(label(k))}${label(k) !== k ? ` <span class="ff-key">${esc(k)}</span>` : ''}</label>`;
  const rows = Object.keys(f).filter((k) => !(info.ok && k === info.idField)).map((k) => {
    const v = f[k], id = fid(k), a = `data-uid="${U}" data-fp="${esc(k)}"`;
    if (v === null || typeof v !== 'object') {
      if (typeof v === 'number') return `<div class="field">${lbl(k, id)}<input type="number" id="${id}" ${a} data-kind="num" value="${v}"></div>`;
      if (typeof v === 'boolean') return `<label class="switch"><input type="checkbox" id="${id}" ${a} data-kind="bool" ${v ? 'checked' : ''}><span class="sw"></span><span>${esc(label(k))}</span></label>`;
      const sv = v == null ? '' : String(v);
      const long = sv.length > 70 || sv.includes('\n') || /expect|result|descr|scenar|описан|сценар|ожид/i.test(k);
      return `<div class="field">${lbl(k, id)}${long ? `<textarea id="${id}" rows="3" ${a}>${esc(sv)}</textarea>` : `<input type="text" id="${id}" ${a} value="${esc(sv)}">`}</div>`;
    }
    if (Array.isArray(v) && v.every((x) => x === null || typeof x !== 'object')) {
      return `<div class="field">${lbl(k, id)}<textarea id="${id}" rows="${Math.max(2, v.length + 1)}" ${a} data-kind="lines">${esc(v.join('\n'))}</textarea><span class="hint">По одному на строку</span></div>`;
    }
    const shape = rowShape(c.type, k);
    if (Array.isArray(v) && (v.length ? v.every(isFlatObj) : !!shape)) {
      const cols = [...new Set([...v.flatMap((x) => Object.keys(x)), ...Object.keys(shape || {})])];
      return `<div class="field"><span class="lbl">${esc(label(k))}</span><div class="tbl-wrap"><table class="ff-table"><thead><tr>${cols.map((col) => `<th>${esc(label(col))}</th>`).join('')}<th><span class="sr">Действия</span></th></tr></thead><tbody>${v.map((row, i) => `<tr>${cols.map((col) => {
        const x = row[col], aa = `data-uid="${U}" data-fp="${esc(k)}|${i}|${esc(col)}" aria-label="${esc(label(col))}, строка ${i + 1}"`;
        return `<td>${typeof x === 'number' ? `<input type="number" ${aa} data-kind="num" value="${x}">` : `<textarea rows="2" ${aa}>${esc(x ?? '')}</textarea>`}</td>`;
      }).join('')}<td class="ff-acts"><button class="icon-btn" type="button" data-act="ff-row" data-op="up" data-uid="${U}" data-key="${esc(k)}" data-i="${i}" aria-label="Поднять строку ${i + 1}" ${i ? '' : 'disabled'}>↑</button><button class="icon-btn" type="button" data-act="ff-row" data-op="down" data-uid="${U}" data-key="${esc(k)}" data-i="${i}" aria-label="Опустить строку ${i + 1}" ${i < v.length - 1 ? '' : 'disabled'}>↓</button><button class="icon-btn" type="button" data-act="ff-row" data-op="del" data-uid="${U}" data-key="${esc(k)}" data-i="${i}" aria-label="Удалить строку ${i + 1}">${ICON.x}</button></td></tr>`).join('')}</tbody></table></div>
        <span><button class="btn" type="button" data-act="ff-row" data-op="add" data-uid="${U}" data-key="${esc(k)}">+ Добавить строку</button></span></div>`;
    }
    if (isFlatObj(v)) {
      return `<div class="field"><span class="lbl">${esc(label(k))}</span><div class="ff-sub">${Object.entries(v).map(([sk, sv]) => {
        const sid = fid(k + '_' + sk);
        return `<label class="small muted" for="${sid}">${esc(label(sk))}</label>${typeof sv === 'number' ? `<input type="number" id="${sid}" data-uid="${U}" data-fp="${esc(k)}|${esc(sk)}" data-kind="num" value="${sv}">` : `<input type="text" id="${sid}" data-uid="${U}" data-fp="${esc(k)}|${esc(sk)}" value="${esc(sv ?? '')}">`}`;
      }).join('')}</div></div>`;
    }
    return `<div class="field">${lbl(k, id)}<textarea class="code" id="${id}" rows="6" ${a} data-kind="json" spellcheck="false">${esc(ui.formJSON[k] ?? JSON.stringify(v, null, 2))}</textarea><span class="hint">JSON</span></div>`;
  }).join('');
  return `<div class="case-form">${rows}
    <div class="field"><label class="lbl" for="ff-${U}-reqs">Требования</label><input type="text" id="ff-${U}-reqs" class="mono" data-uid="${U}" data-meta="reqs" value="${esc(ui.formReqs)}" placeholder="R-001, R-002"></div>
    ${ui.error ? `<p class="case-note err">${esc(ui.error)}</p>` : ''}
    <div class="case-acts"><button class="btn accent" type="button" data-act="ff-save" data-uid="${U}">Сохранить</button><button class="btn" type="button" data-act="ff-cancel" data-uid="${U}">Отмена</button><button class="btn" type="button" data-act="ff-json" data-uid="${U}">Править как JSON</button></div></div>`;
}
function setPath(obj, parts, val) {
  let o = obj;
  for (let i = 0; i < parts.length - 1; i++) { const p = /^\d+$/.test(parts[i]) ? Number(parts[i]) : parts[i]; o = o[p]; if (o == null) return; }
  const last = parts[parts.length - 1];
  o[/^\d+$/.test(last) ? Number(last) : last] = val;
}
function renumber(arr) {
  if (!arr.length) return;
  const keys = Object.keys(arr[0]).filter((k) => STEP_NUM_KEYS.includes(k.toLowerCase()) && arr.every((r) => typeof r[k] === 'number' || r[k] === undefined));
  for (const k of keys) arr.forEach((r, i) => { r[k] = i + 1; });
}
function addManualCase(type) {
  const r = S.run, info = tplInfo(type);
  if (!r) return;
  if (!info.ok) { S.cfgType = type; openSettings('tpl'); return toast(`Шаблон ${TL[type]}: ${info.error}`, 'err'); }
  let tc = blankFrom(info.structure);
  const dispId = nextDispId(r, type);
  if (info.idField) tc[info.idField] = dispId;
  tc = orderLikeTemplate(tc, info);
  const c = { uid: rid('c'), type, planItem: 'manual', requirementIds: [], suites: ['regression'], testCase: tc, dispId, manual: true };
  if (r.mode === 'update') Object.assign(c, { status: 'new', note: 'Добавлен вручную', changes: [] });
  r.cases.push(c);
  S.filter = { type: 'all', suite: 'all', q: '' };
  enterForm(c); caseUI(c.uid).isNew = true;
  S.tab = 'cases'; renderTabs(); renderTab();
  document.getElementById('case-' + c.uid)?.scrollIntoView({ block: 'start', behavior: 'smooth' });
}

/* ================= вкладка «Ревью» ================= */
const runningStep = (r) => STEPS.find((s) => r.steps[s.id]?.status === 'running')?.id;
function findingHTML(r, f) {
  const ui = S.fdUI.get(f.id) || {};
  const tgt = findingTarget(r, f);
  const tname = f.kind === 'case' && tgt ? pickTitleText(tgt.testCase) : f.kind === 'checklist' && tgt ? tgt.check : f.kind === 'req' && tgt ? tgt.title : 'объект удалён';
  const st = f.status === 'fixed' ? '<span class="chip ok">исправлено</span>' : f.status === 'dismissed' ? '<span class="chip">отклонено</span>' : '';
  const busy = S.running;
  let acts = '';
  if (f.status === 'open') {
    acts = ui.dismissing
      ? `<div class="case-edit"><label class="lbl" for="fdr-${f.id}">Почему это не ошибка — необязательно</label><textarea id="fdr-${f.id}" rows="2" data-fd="${f.id}" placeholder="Причина станет правилом для ревьюера, чтобы он больше так не придирался">${esc(ui.reason || '')}</textarea>
        <div class="case-acts"><button class="btn accent" type="button" data-act="fd-dismiss-ok" data-id="${f.id}">Отклонить замечание</button><button class="btn" type="button" data-act="fd-dismiss-cancel" data-id="${f.id}">Отмена</button></div></div>`
      : `<div class="case-acts">${tgt ? `<button class="btn" type="button" data-act="fd-fix" data-id="${f.id}" ${busy ? 'disabled' : ''}>${f.kind === 'req' ? 'Дописать кейсы' : 'Исправить'}</button>` : ''}<button class="btn" type="button" data-act="fd-dismiss" data-id="${f.id}">Отклонить</button></div>`;
  } else acts = `<div class="case-acts"><button class="btn" type="button" data-act="fd-reopen" data-id="${f.id}">Вернуть в открытые</button></div>`;
  return `<div class="fd sev-${f.severity} st-${f.status}"><div class="fd-h"><span class="chip sev-${f.severity}">${SEV_RU[f.severity]}</span><span class="chip">${esc(f.category)}</span>
      <button class="link mono" type="button" data-act="fd-goto" data-id="${f.id}">${esc(f.targetId)}</button><span class="fd-t">${esc(tname)}</span>${st}</div>
    <p>${esc(f.message)}</p>${f.suggestion ? `<p class="fd-s">${esc(f.suggestion)}</p>` : ''}${f.reason ? `<p class="fd-s">Причина отклонения: ${esc(f.reason)}</p>` : ''}${acts}</div>`;
}
const logHTML = (log) => (log.length ? `<ul class="log" style="margin:10px 0">${log.slice(-40).map((l) => `<li class="${l.kind}">${esc(l.text)}</li>`).join('')}</ul>` : '');
/* итоги правил команды: сколько нарушений по каждому правилу, открыто и закрыто; видно, включён ли строгий режим */
function ruleCardHTML(F) {
  const rules = F.filter((f) => f.category === 'Правило');
  if (!rules.length && !S.settings.strictRules) return '';
  const byRule = {};
  for (const f of rules) { const k = byRule[f.rule] || (byRule[f.rule] = { open: 0, closed: 0 }); k[f.status === 'open' ? 'open' : 'closed']++; }
  const chips = Object.entries(byRule).map(([id, k]) => `<span class="chip">${esc(RULE_LABEL[id] || id)}: открыто ${k.open}, закрыто ${k.closed}</span>`).join('');
  return `<div class="exp-card"><div class="exp-row"><b>Правила команды</b><span class="muted small">${S.settings.strictRules ? 'строгий режим: нарушения исправляет модель' : 'строгий режим выключен: нарушения только в замечаниях'}</span></div>${rules.length ? `<div class="exp-row">${chips}</div>` : '<p class="hint">Нарушений правил не найдено.</p>'}</div>`;
}
function reviewTab() {
  const r = S.run;
  if (!r || (!r.cases.length && !checklistItems(r).length)) return emptyHTML('Ревью появится после генерации', 'Сначала сгенерируйте чек-лист или тест-кейсы.');
  const v = aiValue('review'), step = S.running ? runningStep(r) : null, busy = step === 'review' || step === 'fix';
  const head = `<div class="exp-card"><div class="exp-row"><b>Ревьюер</b><span class="muted small">${esc(aiLabel(v))} · правила ревью: ${S.cfg.reviewRules.trim() ? 'заданы командой' : 'стандартные'} · правил из замечаний: ${S.lessons.filter((l) => l.scope !== 'generation').length}</span><button class="link" type="button" data-act="cfg-review" style="margin-left:auto">Правила ревью</button></div>
      <p class="hint">Субагент сверяет чек-лист и кейсы с документами, требованиями, шаблонами и правилами ревью. Сам он ничего не меняет — исправления запускаете вы.</p>
      <div class="exp-row">${busy ? `<span class="small">${step === 'fix' ? 'Агент исправляет замечания…' : 'Ревьюер работает…'}</span><button class="btn" type="button" data-act="stop">Остановить</button>`
        : `<button class="btn accent" type="button" data-act="start-review" ${aiReady(v) && !S.running ? '' : 'disabled'}>${r.findings ? 'Повторить ревью' : 'Запустить ревью'}</button>${r.findings && aiReady(v) ? `<span class="hint">Повторно проверяются только изменённые кейсы и пункты.</span><button class="link" type="button" data-act="start-review-full" ${S.running ? 'disabled' : ''}>Проверить всё заново</button>` : ''}${aiReady(v) ? '' : `<span class="hint">${esc(aiProblem(v))}</span>`}`}</div>
      ${busy ? logHTML(r.steps[step].log) : ''}</div>`;
  if (!r.findings) return head;
  const F = r.findings, n = (fn) => F.filter(fn).length;
  const filters = [['open', 'Открытые', (f) => f.status === 'open'], ['critical', 'Критичные', (f) => f.status === 'open' && f.severity === 'critical'], ['major', 'Существенные', (f) => f.status === 'open' && f.severity === 'major'], ['minor', 'Мелкие', (f) => f.status === 'open' && f.severity === 'minor'], ['fixed', 'Исправленные', (f) => f.status === 'fixed'], ['dismissed', 'Отклонённые', (f) => f.status === 'dismissed'], ['all', 'Все', () => true]];
  const cur = filters.find((x) => x[0] === S.fdFilter) || filters[0];
  const open = F.filter((f) => f.status === 'open');
  const list = F.filter(cur[2]).sort((a, b) => ['critical', 'major', 'minor'].indexOf(a.severity) - ['critical', 'major', 'minor'].indexOf(b.severity));
  return head + ruleCardHTML(F) + `<div class="toolbar">${filters.map(([id, name, fn]) => `<button class="fchip" type="button" data-act="fd-filter" data-f="${id}" aria-pressed="${S.fdFilter === id}">${name}<span class="n">${n(fn)}</span></button>`).join('')}
      <span style="margin-left:auto"><button class="btn accent" type="button" data-act="fd-fixall" ${open.length && !S.running ? '' : 'disabled'}>Исправить все открытые${open.length ? ` (${open.length})` : ''}</button></span></div>
    ${list.length ? `<div class="fd-list">${list.map((f) => findingHTML(r, f)).join('')}</div>` : emptyHTML(F.length ? 'В этом фильтре пусто' : 'Замечаний нет', F.length ? '' : 'Ревьюер не нашёл проблем.')}`;
}
/* ---------- черновик: проверка сгенерированных кейсов перед добавлением в проект ---------- */
function draftTab() {
  const r = S.run;
  if (!r || !r.cases.length) {
    if (r && !isDraft(r) && r.addedAt) return emptyHTML('Кейсы добавлены в проект', `Добавлены ${fmtDate(r.addedAt)}.`);
    return emptyHTML(S.running ? 'Кейсы появятся здесь по мере генерации' : 'Черновик пуст', S.running ? '' : 'После генерации кейсы попадают сюда: проверьте их ревьюером, исправьте замечания и добавьте в проект.');
  }
  const draft = isDraft(r), lock = draftLocked(r), v = aiValue('review');
  selPrune();
  const selN = r.cases.filter((c) => S.caseSel.has(c.uid)).length;
  const step = S.running ? runningStep(r) : null, busy = step === 'review' || step === 'fix';
  const F = (r.findings || []).filter((f) => f.kind === 'case'), open = F.filter((f) => f.status === 'open');
  const sev = (k) => open.filter((f) => f.severity === k).length;
  const byType = TYPES.filter((t) => r.cases.some((c) => c.type === t)).map((t) => `${TL[t]} ${r.cases.filter((c) => c.type === t).length}`).join(' · ');
  const revState = !r.findings ? 'ревью ещё не запускалось'
    : open.length ? `открытых замечаний ${open.length}: ${[sev('critical') ? `критичных ${sev('critical')}` : '', sev('major') ? `существенных ${sev('major')}` : '', sev('minor') ? `мелких ${sev('minor')}` : ''].filter(Boolean).join(', ')}`
      : F.length ? 'все замечания исправлены или отклонены' : 'замечаний нет';
  const status = draft ? (r.productId ? 'Кейсы ещё не в продукте: их не видят проверки на повторы, номера не заняты.' : 'Кейсы этого запуска — без продукта.')
    : `Добавлены в проект ${fmtDate(r.addedAt || r.finishedAt || Date.now())}.`;
  const head = `<div class="exp-card draft-head">
      <div class="exp-row"><b>${draft ? 'Черновик тест-кейсов' : 'Тест-кейсы запуска'} · ${r.cases.length}</b><span class="muted small">${esc(byType)}</span></div>
      <p class="hint">${esc(status)} Ревью: ${esc(revState)}.</p>
      ${busy ? `<div class="exp-row"><span class="small">${step === 'fix' ? 'Агент исправляет замечания…' : 'Ревьюер проверяет кейсы…'}</span></div>${logHTML(r.steps[step].log)}` : ''}
      <div class="draft-acts">
        <button class="btn" type="button" data-act="draft-review" ${aiReady(v) && !lock ? '' : 'disabled'} title="${esc(aiProblem(v) || 'Субагент сверит кейсы с документами, требованиями, шаблоном и правилами ревью')}">${r.findings ? 'Повторить ревью' : 'Запустить ревью'}</button>
        <button class="btn" type="button" data-act="draft-fixall" ${open.length && !lock ? '' : 'disabled'}>Исправить все${open.length ? ` (${open.length})` : ''}</button>
        <button class="btn" type="button" data-act="etalon-open" ${S.running ? 'disabled' : ''} title="Сравнить ${selN ? 'выбранные' : 'все'} кейсы с эталонными и получить правила генерации">Сравнить с эталоном${selN ? ` (${selN})` : ''}</button>
        ${r.etalon ? `<button class="link" type="button" data-act="etalon-result">Правила из эталона${etalonPending(r) ? ` · ждут решения ${etalonPending(r)}` : ''}</button>` : ''}
        <span class="sp"></span>
        ${draft ? `<button class="btn danger" type="button" data-act="draft-clear" ${lock ? 'disabled' : ''}>Очистить</button>
        <button class="btn accent" type="button" data-act="draft-add" ${lock ? 'disabled' : ''} title="${r.productId ? 'Кейсы попадут в продукт: их увидят следующие запуски и команда' : 'Принять кейсы этого запуска'}">Добавить в проект (${r.cases.length})</button>` : '<span class="chip ok">в проекте</span>'}
      </div></div>`;
  const rows = r.cases.map((c) => {
    const fs = caseFindings(r, c, false), op = fs.filter((f) => f.status === 'open'), done = fs.length - op.length;
    const worst = ['critical', 'major', 'minor'].find((k) => op.some((f) => f.severity === k));
    return `<li class="draft-case${worst ? ' sev-' + worst : ''}">
      <div class="draft-case-h">${selCB(c)}<span class="mono">${esc(c.dispId)}</span><span class="chip">${TL[c.type]}</span>${c.status && r.mode === 'update' ? `<span class="chip">${esc(UPD_ST[c.status] || c.status)}</span>` : ''}<span class="draft-t">${esc(pickTitleText(c.testCase))}</span>
        ${op.length ? `<span class="chip sev-${worst}">замечаний ${op.length}</span>` : r.findings ? `<span class="chip ok">${done ? `исправлено ${done}` : 'без замечаний'}</span>` : ''}</div>
      ${op.length ? `<ul class="draft-fd">${op.map((f) => `<li><span class="chip sev-${f.severity}">${SEV_RU[f.severity]}</span> ${esc(f.message)}${f.suggestion ? `<span class="muted small"> — ${esc(f.suggestion)}</span>` : ''}</li>`).join('')}</ul>` : ''}
      <div class="case-acts">${op.length ? `<button class="btn sm" type="button" data-act="draft-fix" data-uid="${c.uid}" ${lock ? 'disabled' : ''}>Исправить</button>` : ''}<button class="btn sm" type="button" data-act="draft-open" data-uid="${c.uid}">Открыть</button>${draft ? `<button class="btn sm" type="button" data-act="draft-drop" data-uid="${c.uid}" ${lock ? 'disabled' : ''} title="Убрать кейс из черновика">Убрать</button>` : ''}</div>
    </li>`;
  }).join('');
  return head + `<div class="sel-bar">${selBarHTML(r.cases, 'draft')}</div><ul class="draft-list">${rows}</ul>`;
}
function gotoFinding(f) {
  const r = S.run, t = findingTarget(r, f);
  if (!t) return toast('Объект замечания удалён.', 'err');
  if (f.kind === 'case') { S.tab = 'cases'; S.filter = { type: 'all', suite: 'all', q: '' }; caseUI(t.uid).open = true; renderTabs(); renderTab(); document.getElementById('case-' + t.uid)?.scrollIntoView({ block: 'center' }); }
  else if (f.kind === 'checklist') { S.tab = 'checklist'; S.clFilter = { type: 'all', suite: 'all' }; renderTabs(); renderTab(); document.getElementById('cl-' + t.id)?.scrollIntoView({ block: 'center' }); }
  else { S.tab = 'reqs'; S.reqOpen.add(t.id); renderTabs(); renderTab(); }
}

/* ================= events ================= */
function armed(btn, label) {
  if (btn.classList.contains('armed')) return true;
  const old = btn.textContent;
  btn.classList.add('armed'); btn.textContent = label;
  setTimeout(() => { if (btn.isConnected) { btn.classList.remove('armed'); btn.textContent = old; } }, 4000);
  return false;
}
const findCase = (uid) => S.run?.cases.find((c) => c.uid === uid);
const findItem = (id) => (S.run ? checklistItems(S.run).find((i) => i.id === id) : null);
function toggleSuite(arr, s) { return arr.includes(s) ? arr.filter((x) => x !== s) : SUITES.filter((x) => x === s || arr.includes(x)); }
function leaveHelp(mode) { S.settings.mode = mode === 'update' ? 'update' : 'generate'; saveSettings(); renderMode(); }
function onTabClick(e) {
  if (e.target.closest?.('input.case-sel, input.sel-all-cb, label.sel-all')) return; // флажок выбора не разворачивает кейс
  const el = e.target.closest('[data-act]');
  if (!el || el.disabled) return;
  const act = el.dataset.act, uid = el.dataset.uid, r = S.run;
  const c = uid ? findCase(uid) : null;
  const ui = uid ? caseUI(uid) : null;
  const fd = el.dataset.id && r?.findings ? r.findings.find((x) => x.id === el.dataset.id) : null;
  switch (act) {
    case 'go-tab': if (S.settings.mode === 'help') leaveHelp(); S.tab = el.dataset.tab; renderTabs(); renderTab(); saveSession(); break;
    case 'pp-toggle': S.prodOpen = !S.prodOpen; lsSet('qapro.prodOpen', S.prodOpen); renderProduct(true); break;
    case 'help-send': sendHelp(); break;
    case 'help-view': S.helpView = el.dataset.v; lsSet('qapro.kbView', S.helpView); renderHelp(true); if (S.helpView === 'qa') $('#help-input')?.focus(); break;
    case 'kb-fold': S.kbFold = !S.kbFold; lsSet('qapro.kbFold', S.kbFold); renderKbPane(true); $('.kb-list-h .fold-btn')?.focus(); break;
    case 'kb-open': S.kb.open = el.dataset.id; S.kb.edit = null; S.helpView = 'blocks'; lsSet('qapro.kbView', 'blocks'); renderHelp(true); $('#help-view')?.scrollIntoView({ block: 'start', behavior: 'smooth' }); break;
    case 'kb-back': S.kb.open = null; S.kb.edit = null; renderHelp(true); break;
    case 'kb-run': kbRun(kbPending()); break;
    case 'kb-synth': kbSynthJob(kbStale().map((b) => b.id)); break;
    case 'kb-report-hide': S.kb.synthReport = null; renderHelp(true); break;
    case 'kb-synth-one': kbSynthJob([el.dataset.id]); break;
    case 'kb-stop': S.kb.job.ctl?.abort(); break;
    case 'kb-ask': { const b = S.kb.cache[el.dataset.id]; S.helpView = 'qa'; lsSet('qapro.kbView', 'qa'); S.help.draft = b ? `Раздел «${b.title}»: ` : ''; renderHelp(true); const ta = $('#help-input'); if (ta) { ta.value = S.help.draft; ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length); } break; }
    case 'kb-rename': S.kb.edit = el.dataset.id; renderHelp(true); break;
    case 'kb-rename-cancel': S.kb.edit = null; renderHelp(true); break;
    case 'kb-rename-save': { const v = $('#kb-title-input')?.value; S.kb.edit = null; document.activeElement?.blur(); renderHelp(true); kbRename(el.dataset.id, v); break; }
    case 'kb-del': if (armed(el, 'Удалить раздел?')) kbDelete(el.dataset.id); break;
    case 'help-suggest': $('#help-input').value = el.dataset.q; S.help.draft = el.dataset.q; sendHelp(); break;
    case 'help-stop': S.help.ctl?.abort(); break;
    case 'help-clear': if (armed(el, 'Очистить всю историю?')) { S.help.items = []; saveHelp(); renderHelp(); } break;
    case 'help-open-add': { const it = S.help.items.find((x) => x.id === el.dataset.id); if (it) { el.disabled = true; addOpenQuestion(it); } break; }
    case 'help-ans-open': { const o = openQuestions()[Number(el.dataset.i)]; if (o) { S.help.ans[o.line] = ''; renderHelp(true); $(`[data-help-ans="${el.dataset.i}"]`)?.focus(); } break; }
    case 'help-ans-cancel': { const o = openQuestions()[Number(el.dataset.i)]; if (o) { delete S.help.ans[o.line]; renderHelp(true); } break; }
    case 'help-ans-save': { const o = openQuestions()[Number(el.dataset.i)]; if (o) { el.disabled = true; answerOpenQuestion(o.line, S.help.ans[o.line]); } break; }
    case 'cfg-export': openSettings('export'); $('#cfg-export')?.focus(); break;
    case 'cfg-review': openSettings('review'); break;
    case 'open-settings': openSettings(el.dataset.tab); break;
    case 'open-conns': openSettings('model'); break;
    case 'standalone': downloadStandalone(); break;
    case 'stop': S.ctl?.abort(); break;
    case 'toggle-req': { const id = el.dataset.id; S.reqOpen.has(id) ? S.reqOpen.delete(id) : S.reqOpen.add(id); renderTab(); break; }
    case 'cover-req': runCover(el.dataset.id, el.dataset.variant); break;
    case 'req-edit': { const q = S.run?.reqById[el.dataset.id]; if (!q) break; S.reqEdit = q.id; S.reqOpen.add(q.id); renderTab(); break; }
    case 'req-cancel': S.reqEdit = null; renderTab(); break;
    case 'req-save': {
      const q = S.run?.reqById[el.dataset.id], title = $('#req-ed-title')?.value.trim();
      if (!q) break;
      if (!title) { toast('Введите название требования.', 'err'); break; }
      q.title = title; q.description = $('#req-ed-desc').value.trim();
      q.criteria = $('#req-ed-crit').value.split('\n').map((x) => x.trim()).filter(Boolean);
      S.reqEdit = null; renderTabs(); renderTab(); queueSave(S.run); break;
    }
    case 'goto-case': {
      S.tab = 'cases'; S.filter = { type: 'all', suite: 'all', q: '' }; caseUI(uid).open = true; renderTabs(); renderTab();
      document.getElementById('case-' + uid)?.scrollIntoView({ block: 'center' });
      break;
    }
    case 'apply-answers': applyAnswers(); break;
    case 'ftype': S.filter.type = el.dataset.t; renderTab(); break;
    case 'cases-scope': S.casesScope = el.dataset.s === 'product' ? 'product' : 'run'; S.secEdit = null; renderTab(); break;
    case 'pc-type': S.pc.type = el.dataset.t; renderTab(); break;
    case 'pc-del-all': if (armed(el, 'Удалить все кейсы продукта?')) deleteAllProductCases(); break;
    case 'pc-open': {   // открыть запуск с этим кейсом и показать кейс
      const runId = el.dataset.r, id = el.dataset.i;
      (async () => {
        if (S.run?.id !== runId && !(await openHistory(runId, { tab: 'cases' }))) return;
        const c = S.run?.cases.find((x) => x.dispId === id);
        if (!c) return toast('Кейс не найден в запуске — возможно, его удалили.', 'err');
        S.casesScope = 'run'; S.filter = { type: 'all', suite: 'all', q: '' }; S.tab = 'cases'; caseUI(c.uid).open = true; renderTabs(); renderTab();
        document.getElementById('case-' + c.uid)?.scrollIntoView({ block: 'center' });
      })();
      break;
    }
    case 'sec-rename': S.secEdit = { key: el.dataset.key, doc: el.dataset.doc, value: secName(el.dataset.doc) }; renderTab(); break;
    case 'sec-cancel': S.secEdit = null; renderTab(); break;
    case 'sec-save': case 'sec-reset': {
      const ed = S.secEdit; if (!ed) break;
      const v = act === 'sec-reset' ? '' : ($('#sec-in')?.value ?? ed.value);
      S.secEdit = null;
      renameSection(ed.doc, v).then(() => { renderTab(); toast(v.trim() && v.trim() !== secDefault(ed.doc) ? 'Название раздела сохранено' : 'Раздел назван по документу'); }).catch(() => { renderTab(); toast('Не удалось сохранить название — нужны права на изменение.', 'err'); });
      renderTab(); break;
    }
    case 'fsuite': S.filter.suite = S.filter.suite === el.dataset.s ? 'all' : el.dataset.s; renderTab(); break;
    case 'fstatus': S.filter.status = S.filter.status === el.dataset.s ? 'all' : el.dataset.s; renderTab(); break;
    case 'toggle-src': ui.showSrc = !ui.showSrc; renderCaseList(); break;
    case 'case-obsolete':
      if (c.status === 'obsolete') { c.status = c.prevStatus && c.prevStatus !== 'obsolete' ? c.prevStatus : 'same'; c.note = c.prevNote || 'Возвращён в актуальные вручную'; }
      else { c.prevStatus = c.status; c.prevNote = c.note; c.status = 'obsolete'; c.note = 'Помечен устаревшим вручную'; }
      renderTabs(); renderTab(); queueSave(r); break;
    case 'expand-all': for (const x of filteredCases()) caseUI(x.uid).open = true; renderCaseList(); break;
    case 'collapse-all': for (const x of filteredCases()) { const u = caseUI(x.uid); if (u.mode === 'view' && !u.busy) u.open = false; } renderCaseList(); break;
    case 'toggle-case': if (ui.mode === 'view' || !ui.open) { ui.open = !ui.open; ui.note = ''; renderCaseList(); } break;
    case 'case-suite': c.suites = toggleSuite(c.suites || [], el.dataset.s); renderTab(); renderTabs(); queueSave(r); break; // перерисовка вкладки обновляет и счётчики фильтров
    case 'add-case': addManualCase(el.dataset.t); break;
    case 'form-case': enterForm(c); renderCaseList(); break;
    case 'ff-row': {
      const k = el.dataset.key, i = Number(el.dataset.i), arr = ui.form[k];
      if (!Array.isArray(arr)) break;
      const op = el.dataset.op;
      if (op === 'add') arr.push(blankFrom(arr[arr.length - 1] || rowShape(c.type, k) || { action: '', expected: '' }));
      else if (op === 'del') arr.splice(i, 1);
      else if (op === 'up' && i > 0) [arr[i - 1], arr[i]] = [arr[i], arr[i - 1]];
      else if (op === 'down' && i < arr.length - 1) [arr[i + 1], arr[i]] = [arr[i], arr[i + 1]];
      renumber(arr); renderCaseList(); break;
    }
    case 'ff-save': {
      for (const [k, raw] of Object.entries(ui.formJSON || {})) {
        const p = tryParse(raw);
        if (!p.ok) { ui.error = `Поле «${label(k)}»: ошибка JSON — ${p.error}`; renderCaseList(); return; }
        ui.form[k] = p.value;
      }
      const info = tplInfo(c.type);
      if (info.ok && info.idField) ui.form[info.idField] = c.dispId;
      if (!ui.isNew) ui.prev = c.testCase;
      c.testCase = orderLikeTemplate(ui.form, info); c.suites = withCritical(c.testCase.priority, c.suites || []);
      c.requirementIds = String(ui.formReqs || '').split(/[\s,;]+/).map((x) => x.trim()).filter(Boolean);
      if (!ui.isNew) touchCase(c, 'Исправлено вручную');
      ui.mode = 'view'; ui.isNew = false; ui.note = 'Изменения сохранены.'; ui.error = '';
      renderTabs(); renderCaseList(); renderTmsBar(); queueSave(r); break;
    }
    case 'ff-cancel':
      if (ui.isNew) { r.cases = r.cases.filter((x) => x.uid !== uid); S.caseUI.delete(uid); r.counters[c.type]--; renderTabs(); renderTab(); break; }
      ui.mode = 'view'; ui.error = ''; renderCaseList(); break;
    case 'ff-json': ui.mode = 'edit'; ui.draft = JSON.stringify(ui.form, null, 2); ui.error = ''; renderCaseList(); break;
    case 'edit-case': ui.mode = 'edit'; ui.draft = JSON.stringify(c.testCase, null, 2); ui.error = ''; ui.note = ''; renderCaseList(); $('#ed-' + uid)?.focus(); break;
    case 'refine-case': ui.mode = 'refine'; ui.error = ''; ui.note = ''; renderCaseList(); $('#rf-' + uid)?.focus(); break;
    case 'cancel-mode':
      if (ui.isNew) { r.cases = r.cases.filter((x) => x.uid !== uid); S.caseUI.delete(uid); r.counters[c.type]--; renderTabs(); renderTab(); break; }
      ui.mode = 'view'; ui.error = ''; renderCaseList(); if (S.pendingCasesRender && !anyEditing()) renderTab(); break;
    case 'save-edit': {
      const p = tryParse(ui.draft);
      if (!p.ok || !p.value || typeof p.value !== 'object' || Array.isArray(p.value)) { ui.error = p.ok ? 'Нужен JSON-объект.' : 'Ошибка JSON: ' + p.error; renderCaseList(); break; }
      if (!ui.isNew) { ui.prev = c.testCase; touchCase(c, 'Исправлено вручную'); }
      c.testCase = p.value; c.suites = withCritical(c.testCase.priority, c.suites || []); ui.mode = 'view'; ui.isNew = false; ui.note = 'Изменения сохранены.'; ui.error = '';
      renderCaseList(); queueSave(r); break;
    }
    case 'do-refine': {
      const comment = (ui.comment || '').trim();
      if (!comment) { ui.error = 'Опишите, что нужно исправить.'; renderCaseList(); break; }
      refineCase(c, comment); break;
    }
    case 'stop-refine': ui.ctl?.abort(); break;
    case 'undo-case': if (ui.prev) { const cur = c.testCase; c.testCase = ui.prev; ui.prev = cur; ui.note = 'Возвращён прежний вариант.'; renderCaseList(); queueSave(r); } break;
    case 'copy-case': copyText(JSON.stringify(c.testCase, null, 2)); break;
    case 'del-case':
      if (!armed(el, 'Точно удалить?')) break;
      r.cases = r.cases.filter((x) => x.uid !== uid); S.caseUI.delete(uid);
      renderTabs(); renderTab(); queueSave(r); if (!isDraft(r)) productSync(r); toast(`Кейс ${c.dispId} удалён`); break;
    case 'retry-failed': retryFailed(); break;
    case 'resume-run': resumeRun(); break;
    case 'resume-cancel': cancelResumeCountdown(); renderTab(); renderRunControls(); break;
    case 'tms-upload': tmsUpload(tmsPending()); break;
    case 'tms-stop': S.tmsCtl?.abort(); break;
    case 'tms-settings': openTms(); break;
    case 'sfera-json': { const list = activeCases(S.run); if (list.length) downloadFile('qa-pro-sfera.json', sferaExportJSON(list)); break; }
    case 'sfera-zip': downloadUploaderZip(); break;
    case 'relay-copy': copyText(QA_PRO_URL); break;
    case 'bridge-mcpb': downloadBridge(); break;
    // чек-лист
    case 'gen-checklist': generateChecklistNow(); break;
    case 'cl-regen': if (armed(el, 'Заменить чек-лист?')) generateChecklistNow(); break;
    case 'go-cl': { S.tab = 'checklist'; S.clFilter = { type: 'all', suite: 'all' }; renderTabs(); renderTab(); const n = document.getElementById('cl-' + el.dataset.id); if (n) { n.scrollIntoView({ block: 'center' }); n.classList.add('flash'); setTimeout(() => n.classList.remove('flash'), 1600); } break; }
    case 'cl-new-manual': r.checklist = { groups: [{ title: 'Проверки', items: [] }] }; r.settings.outputs = { ...outputsOf(r), checklist: true }; newChecklistItem(r, 0); break;
    case 'cl-newgroup': r.checklist.groups.push({ title: 'Новая группа', items: [] }); S.clGroupEdit = r.checklist.groups.length - 1; S.clFilter = { type: 'all', suite: 'all' }; renderTab(); $('#clg-input')?.select(); break;
    case 'cl-gedit': S.clGroupEdit = Number(el.dataset.gi); renderTab(); $('#clg-input')?.select(); break;
    case 'cl-gcancel': S.clGroupEdit = null; renderTab(); break;
    case 'cl-gsave': { const g = r.checklist.groups[Number(el.dataset.gi)], v = $('#clg-input')?.value.trim(); if (g && v) g.title = v; S.clGroupEdit = null; renderTab(); queueSave(r); break; }
    case 'cl-gdel': {
      const gi = Number(el.dataset.gi), g = r.checklist.groups[gi];
      if (g.items.length && !armed(el, `Удалить ${g.items.length} ${plural(g.items.length, 'пункт', 'пункта', 'пунктов')}?`)) break;
      r.checklist.groups.splice(gi, 1); renderTabs(); renderTab(); queueSave(r); break;
    }
    case 'cl-add': newChecklistItem(r, Number(el.dataset.gi)); break;
    case 'cl-ftype': S.clFilter.type = el.dataset.t; renderTab(); break;
    case 'cl-fsuite': S.clFilter.suite = S.clFilter.suite === el.dataset.s ? 'all' : el.dataset.s; renderTab(); break;
    case 'cl-suite': { const it = findItem(el.dataset.id); if (it) { it.suites = toggleSuite(it.suites, el.dataset.s); renderTab(); queueSave(r); } break; }
    case 'cl-edit': S.clEdit = el.dataset.id; S.clRefine = null; renderTab(); $('#cl-input')?.focus(); break;
    case 'cl-cancel': {
      if (S.clNewId === el.dataset.id) { const it = findItem(el.dataset.id); if (it && !it.check) removeChecklistItem(r, it.id); }
      S.clEdit = null; S.clNewId = null; renderTabs(); renderTab(); break;
    }
    case 'cl-save': {
      const it = findItem(el.dataset.id), v = $('#cl-input')?.value.trim();
      if (!it) break;
      if (!v) { toast('Введите формулировку пункта.', 'err'); break; }
      it.check = v; it.expected = ($('#cl-exp')?.value || '').trim(); it.kind = $('#cl-kind')?.value === 'negative' ? 'negative' : 'positive'; it.type = $('#cl-type').value; it.priority = $('#cl-prio').value; it.suites = withCritical(it.priority, it.suites || []);
      it.requirementIds = $('#cl-reqs').value.split(/[\s,;]+/).map((x) => x.trim()).filter(Boolean);
      const gi = Number($('#cl-group').value), from = r.checklist.groups.find((g) => g.items.includes(it)), to = r.checklist.groups[gi];
      if (to && from !== to) { from.items = from.items.filter((x) => x !== it); to.items.push(it); }
      S.clEdit = null; S.clNewId = null; renderTabs(); renderTab(); queueSave(r); break;
    }
    case 'cl-del': {
      removeChecklistItem(r, el.dataset.id);
      renderTabs(); renderTab(); queueSave(r); toast(`Пункт ${el.dataset.id} удалён`); break;
    }
    case 'cl-refine': S.clRefine = { id: el.dataset.id, comment: '', busy: false, error: '' }; S.clEdit = null; renderTab(); $('#clr-input')?.focus(); break;
    case 'cl-refine-cancel': S.clRefine = null; renderTab(); break;
    case 'cl-refine-stop': S.clRefine?.ctl?.abort(); break;
    case 'cl-refine-go': {
      const it = findItem(el.dataset.id), comment = (S.clRefine?.comment || '').trim();
      if (!comment) { S.clRefine.error = 'Опишите замечание.'; renderTab(); break; }
      refineItemUI(it, comment); break;
    }
    case 'cl-copy': copyText(checklistMarkdown(r)); break;
    case 'cl-dl-md': downloadFile(clFileName(r, 'md'), checklistMarkdown(r)); break;
    case 'cl-dl-pdf': checklistPdf(r); break;
    case 'cl-dl-xlsx': checklistXlsx(r); break;
    case 'cl-dl-json': downloadFile(`checklist_${new Date(r.createdAt).toISOString().slice(0, 10)}.json`, JSON.stringify(checklistJSON(r), null, 2)); break;
    // ревью
    case 'start-review': startReview(); break;
    case 'start-review-full': startReview(true); break;
    case 'fd-filter': S.fdFilter = el.dataset.f; renderTab(); break;
    case 'fd-fixall': fixFindings(r.findings.filter((x) => x.status === 'open')); break;
    case 'sel-del': if (armed(el, `Удалить выбранные (${S.caseSel.size})?`)) deleteSelected(el.dataset.where); break;
    case 'sel-none': S.caseSel.clear(); if (S.tab === 'cases') renderCaseList(); else renderTab(); break;
    case 'draft-review': startReview(false, 'draft'); break;
    case 'draft-fixall': fixDraftAll(); break;
    case 'draft-fix': fixCaseFindings(el.dataset.uid); break;
    case 'draft-drop': if (armed(el, 'Убрать?')) dropDraftCase(el.dataset.uid); break;
    case 'draft-clear': if (armed(el, 'Удалить все кейсы черновика?')) clearDraft(); break;
    case 'etalon-open': openEtalon(); break;
    case 'etalon-result': openEtalon('result'); break;
    case 'draft-add': { const crit = (r?.findings || []).filter((f) => f.status === 'open' && f.kind === 'case' && f.severity === 'critical').length; if (!crit || armed(el, `Есть критичные замечания (${crit}) — всё равно добавить?`)) addDraftToProduct(); break; }
    case 'draft-open': { const t = findCase(el.dataset.uid); if (t) { S.tab = 'cases'; S.filter = { type: 'all', suite: 'all', q: '' }; caseUI(t.uid).open = true; renderTabs(); renderTab(); document.getElementById('case-' + t.uid)?.scrollIntoView({ block: 'center' }); } break; }
    case 'fd-fix': if (fd) fixFindings([fd]); break;
    case 'fd-dismiss': S.fdUI.set(fd.id, { dismissing: true, reason: '' }); renderTab(); $('#fdr-' + fd.id)?.focus(); break;
    case 'fd-dismiss-cancel': S.fdUI.delete(fd.id); renderTab(); break;
    case 'fd-dismiss-ok': dismissFinding(fd, S.fdUI.get(fd.id)?.reason); S.fdUI.delete(fd.id); renderTabs(); renderTab(); break;
    case 'fd-reopen': fd.status = 'open'; fd.reason = ''; renderTabs(); renderTab(); queueSave(r); break;
    case 'fd-goto': if (fd) gotoFinding(fd); break;
    // экспорт и история
    case 'run-export': runExport(); break;
    case 'rebuild-export': S.expCache.clear(); S.exp = null; runExport(); break;
    case 'stop-export': S.expCtl?.abort(); break;
    case 'dl-out': downloadOutput(el.dataset.w === 'default' ? S.defaultOut : S.exp.output); break;
    case 'copy-out': { const o = el.dataset.w === 'default' ? S.defaultOut : S.exp.output; copyText(o.kind === 'xlsx' ? [o.columns, ...o.rows].map((row) => row.map((x) => String(x).replace(/[\t\r\n]+/g, ' ')).join('\t')).join('\n') : o.text); break; }
    case 'reload-hist': S.historyState = 'idle'; renderTab(); renderProduct(); break;
    case 'open-hist': if (S.settings.mode === 'help') leaveHelp(el.dataset.mode); openHistory(el.dataset.id, { pid: el.dataset.pid || null }); break;
    case 'del-hist': if (armed(el, 'Точно удалить?')) deleteHistory(el.dataset.id, el.dataset.pid || null); break;
    case 'move-hist': el.disabled = true; moveRunToProduct(el.dataset.id); break;
    // продукт
    case 'prod-new': openProdDialog('new'); break;
    case 'prod-edit': openProdDialog('edit'); break;
    case 'prod-del': if (armed(el, 'Удалить со всеми документами и запусками?')) deleteProduct(S.productId); break;
    case 'know-learn': learnFromDocs(); break;
    case 'know-relearn': if (armed(el, 'Прочитать все заново?')) learnFromDocs(true); break;
    case 'prod-export': exportProduct(); break;
    case 'prod-import': $('#prod-import-file')?.click(); break;
    case 'know-stop': S.know.ctl?.abort(); break;
    case 'run-knowledge': updateKnowledgeNow(); break;
    case 'pass-edit': S.passEdit = { text: knowOf(null)?.passport || '' }; renderProduct(true); $('#pass-text')?.focus(); break;
    case 'pass-new': S.passEdit = { text: PASSPORT_SECTIONS.slice(0, 4).map((h) => `## ${h}\n- `).join('\n\n') }; renderProduct(true); $('#pass-text')?.focus(); break;
    case 'pass-cancel': S.passEdit = null; renderProduct(true); break;
    case 'pass-save': {
      const text = String(S.passEdit?.text || '').trim().slice(0, PASSPORT_MAX);
      el.disabled = true;
      savePassport(S.productId, text, null).then(() => { S.passEdit = null; renderProduct(true); toast('Знания о продукте сохранены'); })
        .catch(() => { el.disabled = false; toast('Не удалось сохранить — нужны права на изменение.', 'err'); });
      break;
    }
    case 'pass-prev': if (armed(el, 'Вернуть прежнюю версию?')) restorePrevPassport(); break;
    case 'trace-run': runTrace(); break;
    case 'q-xlsx': downloadOutput(questionsExport(S.run)); break;
    case 'q-md': downloadFile(`questions_${new Date(S.run.createdAt).toISOString().slice(0, 10)}.md`, questionsMarkdown(S.run)); break;
    case 'q-letter': copyText(questionsLetter(S.run)); break;
    case 'q-import': { const f = $('#q-file'); if (f) { f.value = ''; f.click(); } break; }
  }
  renderRunControls(); // любое действие могло изменить черновик: кнопки «Перегенерировать» и «Сократить» пересчитываются
}
let qSaveT = null;
function onAISelect(e) {
  S.settings.reviewAI = e.target.value; saveSettings(); renderAIHint(); renderRunControls();
  if (S.tab === 'review' || S.tab === 'agent') renderTab();
}
function bind() {
  bindEtalon(); // окно сравнения с эталоном
  // documents
  const drop = $('#drop'), fi = $('#file-input'), dp = $('#docs-panel');
  fi.addEventListener('change', () => { addFiles([...fi.files]); fi.value = ''; });
  drop.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fi.click(); } });
  ['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); }));
  ['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove('over'); }));
  drop.addEventListener('drop', (e) => { const files = [...(e.dataTransfer?.files || [])]; if (files.length) addFiles(files); });
  $('#docs-fold').addEventListener('click', () => toggleDocsFold());
  $('#docs-sum').addEventListener('click', (e) => {
    const b = e.target.closest('[data-docs-act]');
    if (b?.dataset.docsAct === 'add') fi.click(); else if (b) toggleDocsFold(true);
  });
  // свёрнутая панель тоже принимает файлы: перетащите их на заголовок или сводку
  const withFiles = (e) => [...(e.dataTransfer?.types || [])].includes('Files');
  ['dragenter', 'dragover'].forEach((ev) => dp.addEventListener(ev, (e) => { if (!docsFolded() || !withFiles(e)) return; e.preventDefault(); dp.classList.add('over'); }));
  dp.addEventListener('dragleave', (e) => { if (!dp.contains(e.relatedTarget)) dp.classList.remove('over'); });
  dp.addEventListener('drop', (e) => {
    dp.classList.remove('over');
    if (!docsFolded() || drop.contains(e.target)) return;
    e.preventDefault();
    const files = [...(e.dataTransfer?.files || [])];
    if (files.length) addFiles(files);
  });
  $('#doc-list').addEventListener('click', (e) => {
    const b = e.target.closest('[data-doc-act]');
    if (!b) return;
    const d = S.docs.find((x) => x.id === b.dataset.id);
    if (!d) return;
    if (b.dataset.docAct === 'conf') return openDocConflicts(d);
    if (b.dataset.docAct === 'remove') {
      if (d.pid && (d.savedParts || d.sample) && !b.classList.contains('armed')) {
        b.classList.add('armed'); b.title = 'Нажмите ещё раз — документ удалится из продукта для всей команды';
        setTimeout(() => { if (b.isConnected) { b.classList.remove('armed'); b.title = 'Удалить из продукта'; } }, 4000);
        return toast('Нажмите ещё раз, чтобы удалить документ из продукта');
      }
      S.docs = S.docs.filter((x) => x !== d); setRunDoc(d.id, false); invalidateIndex(); dropDocText(d);
    } else if (b.dataset.docAct === 'unrun') setRunDoc(d.id, false); // убрать из запуска: документ остаётся в продукте и базе знаний
    else d.preview = !d.preview;
    renderDocs(); renderRunControls();
    renderProduct(); if (S.tab === 'agent' && !S.run) renderTab();
  });
  $('#docs-note').addEventListener('click', (e) => {
    if (e.target.closest('[data-docs-act=kb]')) { S.settings.mode = 'help'; saveSettings(); renderMode(); }
  });
  $('#qa-ctx-tabs').addEventListener('click', (e) => { const b = e.target.closest('[data-ctx]'); if (!b) return; S.qaCtxType = b.dataset.ctx; renderQaCtx(); $('#qa-ctx').focus(); });
  $('#qa-ctx').addEventListener('input', (e) => {
    S.qaCtx[S.qaCtxType] = e.target.value;
    renderQaCtx();
    if (S.run && !S.running && S.run.fromHistory !== 'follow' && S.run.fromHistory !== 'readonly') { S.run.qaCtx = { ...S.qaCtx }; queueSave(S.run); }
    if (S.productId) queueCtxSave();
  });
  // режим и файл с тест-кейсами для актуализации
  $('#mode-seg').addEventListener('click', (e) => {
    const b = e.target.closest('[data-mode]');
    if (!b || b.dataset.mode === S.settings.mode) return;
    S.settings.mode = b.dataset.mode; saveSettings(); renderMode();
    if (S.settings.mode === 'help') $('#help-input')?.focus();
  });
  const ud = $('#upd-drop'), ui2 = $('#upd-input');
  ui2.addEventListener('change', () => { const f = ui2.files[0]; if (f) setTestsFile(f); ui2.value = ''; });
  ud.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ui2.click(); } });
  ['dragenter', 'dragover'].forEach((ev) => ud.addEventListener(ev, (e) => { e.preventDefault(); ud.classList.add('over'); }));
  ['dragleave', 'drop'].forEach((ev) => ud.addEventListener(ev, (e) => { e.preventDefault(); ud.classList.remove('over'); }));
  ud.addEventListener('drop', (e) => { const f = e.dataTransfer?.files?.[0]; if (f) setTestsFile(f); });
  $('#upd-info').addEventListener('click', (e) => {
    const b = e.target.closest('[data-upd-act]');
    if (!b || !S.upd.file) return;
    const a = b.dataset.updAct;
    if (a === 'remove') S.upd.file = null;
    else if (a === 'preview') S.upd.file.preview = !S.upd.file.preview;
    else if (a === 'replace') { ui2.click(); return; }
    renderUpd(); renderRunControls();
    if (S.tab === 'agent' && !S.run) renderTab();
  });
  $('#btn-sample').addEventListener('click', () => { addSampleDoc(); renderDocs(); renderRunControls(); renderProduct(); if (S.tab === 'agent' && !S.run) renderTab(); });
  $('#btn-newses').addEventListener('click', () => newSession());
  $('#prod-select').addEventListener('change', (e) => {
    const v = e.target.value;
    if (v === '__new') { e.target.value = S.productId || ''; openProdDialog('new'); return; }
    if (v && v !== S.productId) switchProduct(v);
  });
  $('#prod-body').addEventListener('input', (e) => { const k = e.target.dataset.pf; if (k && S.prodDlg) S.prodDlg[k] = e.target.value; });
  $('#prod-body').addEventListener('click', (e) => { if (e.target.closest('[data-pact="save"]')) saveProdDialog(); });
  $('#prod-body').addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target.id === 'prod-name') { e.preventDefault(); saveProdDialog(); } });
  $('#auto-resume').checked = S.settings.autoResume;
  $('#auto-resume').addEventListener('change', (e) => { S.settings.autoResume = e.target.checked; saveSettings(); if (!e.target.checked) { cancelResumeCountdown(); renderAll(); } });
  // страницу закрывают посреди генерации: сохраняем прогресс и отмечаем, что вкладка больше не работает
  window.addEventListener('pagehide', () => {
    if (!S.running || !S.run) return;
    S.unloading = true;
    saveChain = saveChain.then(() => saveRun(S.run)).catch(() => {});
    flushSessionNow();
  });
  window.addEventListener('pageshow', (e) => { if (e.persisted && S.unloading) { S.unloading = false; flushSessionNow(); } });
  window.addEventListener('beforeunload', (e) => {
    if (!S.running || !S.run) return;
    if (S.workerPeer?.online && !S.workerPeer.self) { saveChain = saveChain.then(() => saveRun(S.run)).catch(() => {}); return; } // доделает фоновый исполнитель
    saveChain = saveChain.then(() => saveRun(S.run)).catch(() => {});
    e.preventDefault(); e.returnValue = '';
  });
  // params
  $('#outs').addEventListener('change', (e) => { const k = e.target.dataset.out; if (!k) return; S.settings.outputs[k] = e.target.checked; saveSettings(); renderRunControls(); });
  $('#types').addEventListener('change', (e) => { const t = e.target.dataset.type; if (!t) return; S.settings.types[t] = e.target.checked; saveSettings(); renderRunControls(); });
  $('#depth').addEventListener('click', (e) => { const b = e.target.closest('[data-depth]'); if (!b) return; S.settings.depth = b.dataset.depth; saveSettings(); renderParams(); });
  $('#review-ai').addEventListener('change', onAISelect);
  $('#stage-models').addEventListener('change', (e) => {
    const id = e.target.dataset?.stage;
    if (!id || !STAGES.some((x) => x.id === id) || !STAGE_TIER_VALUES.includes(e.target.value)) return;
    S.settings.stages[id] = e.target.value; saveSettings(); renderParams();
  });
  $('#stage-models').addEventListener('click', (e) => {
    const act = e.target.closest('[data-stage-act]')?.dataset.stageAct;
    if (!act) return;
    for (const x of STAGES) S.settings.stages[x.id] = act === 'apply' ? x.rec : 'same';
    saveSettings(); renderParams();
    toast(act === 'apply' ? 'Применена рекомендуемая раскладка моделей по этапам' : 'Все этапы идут на основной модели');
  });
  $('#prov-list').addEventListener('change', onProvInput);
  $('#prov-list').addEventListener('input', (e) => { if (e.target.matches('[data-pk],[data-pm],[data-pu]')) onProvInput(e); });
  $('#prov-list').addEventListener('click', onProvClick);
  $('#agent-tools').addEventListener('change', (e) => { S.settings.agentTools = e.target.checked; saveSettings(); });
  $('#strict-rules').addEventListener('change', (e) => { S.settings.strictRules = e.target.checked; saveSettings(); });
  $('#skip-existing').addEventListener('change', (e) => { S.settings.skipExisting = e.target.checked; saveSettings(); renderProduct(); });
  $('#economy').addEventListener('change', (e) => { S.settings.economy = e.target.checked; saveSettings(); renderParams(); });
  $('#reuse-analysis').addEventListener('change', (e) => { S.settings.reuseAnalysis = e.target.checked; saveSettings(); });
  // dialogs
  $('#tms-body').addEventListener('click', onTmsClick);
  $('#tms-body').addEventListener('input', onTmsInput);
  $('#tms-body').addEventListener('change', (e) => { if (e.target.tagName === 'SELECT') onTmsInput(e); });
  $('#bg-body').addEventListener('change', onBgChange);
  $('#bg-body').addEventListener('click', (e) => { if (e.target.closest('[data-act="relay-copy"]')) copyText(QA_PRO_URL); });
  $('#mat-body').addEventListener('click', (e) => { const b = e.target.closest('[data-conf-open]'); if (b) openKbSection(b.dataset.confOpen); });
  for (const id of ['prod-ov', 'set-ov', 'mat-ov', 'etalon-ov']) {
    $('#' + id).addEventListener('click', (e) => { if (e.target.id === id || e.target.closest('[data-close]')) closeDialog(id); });
  }
  // указания агенту
  $('#set-tabs').addEventListener('click', (e) => { const b = e.target.closest('[data-settab]'); if (!b) return; S.setTab = b.dataset.settab; renderCfg(); });
  $('#btn-settings').addEventListener('click', () => openSettings());
  $('#cfg-rules').addEventListener('input', (e) => { S.cfg.rules = e.target.value; markCfgDirty('rules'); });
  $('#rules-panel').addEventListener('click', (e) => {
    const b = e.target.closest('[data-cfg],[data-open-settings]');
    if (!b) return;
    if (b.dataset.openSettings) return openSettings(b.dataset.openSettings);
    if (b.dataset.cfg === 'expand-rules') openEditor('rules');
    else if (b.dataset.cfg === 'save') saveCfg('rules');
    else if (b.dataset.cfg === 'revert') revertCfg('rules');
  });
  const cfgBody = $('#cfg-body');
  cfgBody.addEventListener('input', (e) => {
    const t = e.target, ty = S.cfgType;
    if (t.id === 'cfg-export') { S.cfg.exportFormat = t.value; markCfgDirty('export'); }
    else if (t.id === 'cfg-review') { S.cfg.reviewRules = t.value; markCfgDirty('review'); }
    else if (t.id === 'cfg-example') { S.cfg.tpl[ty].example = t.value; markCfgDirty(ty); }
    else if (t.id === 'cfg-tplrules') { S.cfg.tpl[ty].rules = t.value; markCfgDirty(ty); }
    else if (t.id === 'cfg-prefix') { S.cfg.tpl[ty].idPrefix = t.value; markCfgDirty(ty); }
  });
  cfgBody.addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target.id === 'lesson-new') { e.preventDefault(); cfgBody.querySelector('[data-cfg="lesson-add"]')?.click(); } });
  cfgBody.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-cfg],[data-cfgtype]');
    if (!b) return;
    if (b.dataset.cfgtype) { S.cfgType = b.dataset.cfgtype; renderCfg(); return; }
    const a = b.dataset.cfg;
    if (a === 'expand') openEditor();
    else if (a === 'load') { const f = $('#cfg-file'); f.value = ''; f.click(); }
    else if (a === 'load-md') { const f = $('#cfg-md'); f.value = ''; f.click(); }
    else if (a === 'default') { S.cfg.tpl[S.cfgType] = { ...DEFAULT_TPL[S.cfgType] }; markCfgDirty(S.cfgType); renderCfg(); toast('Подставлен стандартный пример'); }
    else if (a === 'lesson-del') deleteLesson(b.dataset.id);
    else if (a === 'lesson-add') {
      const inp = $('#lesson-new'), v = inp.value.trim();
      if (!v) return;
      const ok = await addLesson(v, $('#lesson-scope').value, 'manual');
      if (ok) { inp.value = ''; toast('Правило добавлено в память агента'); } else toast('Такое правило уже есть.', 'err');
    }
  });
  cfgBody.addEventListener('change', async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    const text = decodeText(await f.arrayBuffer());
    if (e.target.id === 'cfg-file') {
      const p = tryParse(text);
      if (!p.ok) return toast('В файле некорректный JSON: ' + p.error, 'err');
      S.cfg.tpl[S.cfgType].example = JSON.stringify(p.value, null, 2); markCfgDirty(S.cfgType); renderCfg();
      toast('Пример загружен');
    } else if (e.target.id === 'cfg-md') {
      if (f.size > 300000) return toast('Файл слишком большой — до 300 КБ.', 'err');
      S.cfg.reviewRules = text.trim(); markCfgDirty('review'); renderCfg();
      toast(`Правила ревью загружены из ${f.name}`);
    }
  });
  $('#cfg-foot').addEventListener('click', (e) => {
    const b = e.target.closest('[data-cfg]');
    if (!b) return;
    if (b.dataset.cfg === 'save') saveCfg(b.dataset.k || cfgKeyOfTab());
    else if (b.dataset.cfg === 'revert') revertCfg(b.dataset.k || cfgKeyOfTab());
  });
  // overlay editor
  $('#ov-text').addEventListener('input', (e) => {
    if (!ovKey) return;
    const src = $(ovKey.src);
    if (src) { src.value = e.target.value; src.dispatchEvent(new Event('input', { bubbles: true })); }
    updateOvValid();
  });
  $('#ov-done').addEventListener('click', closeEditor);
  $('#ov-close').addEventListener('click', closeEditor);
  $('#overlay').addEventListener('click', (e) => { if (e.target.id === 'overlay') closeEditor(); });
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    if (ovKey) closeEditor();
    else { const top = ['mat-ov', 'prod-ov', 'set-ov'].find((id) => !$('#' + id).hidden); if (top) closeDialog(top); }
  });
  // run
  $('#btn-run').addEventListener('click', runAgent);
  const af = $('#api-filter');
  if (af) {
    af.value = S.settings.apiFilter || '';
    af.addEventListener('input', () => { S.settings.apiFilter = af.value.slice(0, 300); saveSettings(); scheduleApiFilter(); });
  }
  const tn = $('#target-n');
  if (tn) {
    tn.value = S.settings.target || '';
    tn.addEventListener('change', () => { const v = Math.round(Number(tn.value)); S.settings.target = v >= 1 && v <= 300 ? v : null; tn.value = S.settings.target || ''; saveSettings(); });
  }
  $('#btn-review').addEventListener('click', startReview);
  $('#btn-regen').addEventListener('click', (e) => { if (armed(e.currentTarget, 'Заменить кейсы черновика?')) regenDrafts(); });
  $('#btn-reduce').addEventListener('click', openReduce);
  $('#reduce-cancel').addEventListener('click', closeReduce);
  $('#reduce-go').addEventListener('click', reduceGo);
  $('#reduce-n').addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); reduceGo(); } });
  $('#reduce-n').addEventListener('input', resetReduceWarn);
  $('#btn-stop').addEventListener('click', () => S.ctl?.abort());
  // tabs
  $('#tabs').addEventListener('click', (e) => { const b = e.target.closest('[data-tab]'); if (!b) return; S.tab = b.dataset.tab; S.clEdit = null; S.clRefine = null; renderTabs(); renderTab(); saveSession(); });
  const body = $('#tab-body');
  body.addEventListener('click', onTabClick);
  body.addEventListener('input', (e) => {
    if (e.target.id !== 'trace-desc' && e.target.id !== 'trace-stack') return;
    S.trace[e.target.id === 'trace-desc' ? 'description' : 'stack'] = e.target.value;
    const run = document.querySelector('[data-act=trace-run]');
    if (run) run.disabled = S.trace.busy || !S.trace.description.trim() || !aiReady(S.settings.genAI);
  });
  body.addEventListener('change', (e) => {
    const t = e.target;
    if (t.id === 'q-file' && t.files?.[0]) { importAnswers(t.files[0]); return; }
    if (t.classList?.contains('case-sel')) { if (t.checked) S.caseSel.add(t.dataset.uid); else S.caseSel.delete(t.dataset.uid); }
    else if (t.classList?.contains('sel-all-cb')) {
      const list = t.dataset.where === 'cases' ? filteredCases() : S.run?.cases || [];
      for (const c of list) { if (t.checked) S.caseSel.add(c.uid); else S.caseSel.delete(c.uid); }
    } else return;
    if (S.tab === 'cases') renderCaseList(); else renderTab();
  });
  initTheme();
  migrateProviders();
  const tb = document.querySelector('.topbar');
  if (tb) { const setTop = () => document.documentElement.style.setProperty('--top-h', tb.offsetHeight + 'px'); setTop(); if (window.ResizeObserver) new ResizeObserver(setTop).observe(tb); }
  const pp = $('#prod-panel');
  pp.addEventListener('click', onTabClick);
  pp.addEventListener('input', (e) => { if (e.target.id === 'pass-text' && S.passEdit) S.passEdit.text = e.target.value; });
  body.addEventListener('keydown', (e) => {
    if ((e.key === 'Enter' || e.key === ' ') && e.target.matches('.case-h,.req-row')) { e.preventDefault(); e.target.click(); }
    if (e.key === 'Enter' && e.target.id === 'clg-input') { e.preventDefault(); body.querySelector('[data-act="cl-gsave"]')?.click(); }
    if (e.key === 'Enter' && !e.shiftKey && e.target.id === 'help-input') { e.preventDefault(); sendHelp(); }
    if (e.key === 'Enter' && e.target.id === 'kb-title-input') { e.preventDefault(); body.querySelector('[data-act="kb-rename-save"]')?.click(); }
    if (e.key === 'Escape' && e.target.id === 'kb-title-input') { S.kb.edit = null; renderHelp(true); }
    if (e.key === 'Enter' && e.target.dataset.helpAns != null) { e.preventDefault(); body.querySelector(`[data-act="help-ans-save"][data-i="${e.target.dataset.helpAns}"]`)?.click(); }
    if (e.key === 'Escape' && (e.target.id === 'cl-input' || e.target.id === 'clg-input')) { S.clEdit = null; S.clGroupEdit = null; renderTab(); }
  });
  body.addEventListener('toggle', (e) => { if (e.target.matches?.('.kb-parts')) S.kb.partsOpen = e.target.open ? S.kb.open : null; }, true);
  $('#prod-import-file').addEventListener('change', (e) => { const f = e.target.files?.[0]; if (f) importProduct(f); e.target.value = ''; });
  body.addEventListener('change', (e) => { if (e.target.id === 'kb-auto') { S.settings.kbAuto = e.target.checked; saveSettings(); return; } if (e.target.id === 'tms-reup') { S.tmsReup = e.target.checked; renderTmsBar(); } else if (e.target.dataset.kind === 'bool') e.target.dispatchEvent(new Event('input', { bubbles: true })); });
  body.addEventListener('keydown', (e) => {
    if (e.target.id === 'sec-in') { if (e.key === 'Enter') { e.preventDefault(); body.querySelector('[data-act="sec-save"]')?.click(); } else if (e.key === 'Escape') { e.preventDefault(); S.secEdit = null; renderTab(); } }
    else if (e.target.classList?.contains('pc-row') && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); e.target.click(); }
  });
  body.addEventListener('input', (e) => {
    const t = e.target;
    if (t.id === 'case-q') { S.filter.q = t.value; renderCaseList(); renderTmsBar(); return; }
    if (t.id === 'pc-q') { S.pc.q = t.value; renderProdCases(); return; }
    if (t.id === 'sec-in') { if (S.secEdit) S.secEdit.value = t.value; return; }
    if (t.dataset.fp && t.dataset.uid) {
      const u = caseUI(t.dataset.uid), parts = t.dataset.fp.split('|'), kind = t.dataset.kind;
      if (kind === 'json') { u.formJSON[parts[0]] = t.value; return; }
      const val = kind === 'num' ? (t.value === '' ? 0 : Number(t.value)) : kind === 'bool' ? t.checked : kind === 'lines' ? t.value.split('\n').map((x) => x.trim()).filter(Boolean) : t.value;
      setPath(u.form, parts, val);
      return;
    }
    if (t.dataset.meta === 'reqs' && t.dataset.uid) { caseUI(t.dataset.uid).formReqs = t.value; return; }
    if (t.dataset.uid && t.dataset.field) { caseUI(t.dataset.uid)[t.dataset.field] = t.value; return; }
    if (t.dataset.fd) { const u = S.fdUI.get(t.dataset.fd); if (u) u.reason = t.value; return; }
    if (t.id === 'clr-input' && S.clRefine) { S.clRefine.comment = t.value; return; }
    if (t.id === 'pass-text' && S.passEdit) { S.passEdit.text = t.value; return; }
    if (t.id === 'help-input') { S.help.draft = t.value; return; }
    if (t.id === 'kb-q') { S.kb.q = t.value; if (S.kbFold && t.value.trim()) { S.kbFold = false; lsSet('qapro.kbFold', false); } renderKbPane(); return; }
    if (t.dataset.helpAns != null) { const o = openQuestions()[Number(t.dataset.helpAns)]; if (o) S.help.ans[o.line] = t.value; return; }
    if (t.dataset.q && S.run) {
      const q = S.run.questions.find((x) => x.id === t.dataset.q);
      if (!q) return;
      q.answer = t.value;
      const st = qStatus(q);
      $('#q-' + q.id).className = 'q-item ' + st;
      $('#qst-' + q.id).innerHTML = qChip(q);
      $('#q-actions').innerHTML = qActionsHTML(S.run);
      renderTabs();
      clearTimeout(qSaveT); qSaveT = setTimeout(() => queueSave(S.run, 0), 1200);
    }
  });
}

/* ================= capabilities ================= */
/* База артефакта отдаёт снимки замороженными целиком, включая вложенные массивы. Приложение во многих местах
   дополняет загруженное (журналы шагов, выдержки разделов, кейсы запуска), поэтому каждый прочитанный документ —
   редактируемая копия. Записи и подписки уходят в базу как есть. */
const thawData = (d) => (d == null ? d : structuredClone(d));
const thawSnap = (s) => s && { id: s.id, exists: s.exists, metadata: s.metadata, ref: s.ref, data: () => thawData(s.data()) };
const thawQSnap = (q) => q && { docs: q.docs.map(thawSnap), size: q.size, empty: q.empty, metadata: q.metadata, docChanges: () => q.docChanges().map((c) => ({ ...c, doc: thawSnap(c.doc) })), forEach: (fn) => q.docs.map(thawSnap).forEach(fn) };
function thawDoc(r) {
  if (!r) return r;
  return {
    id: r.id, path: r.path,
    get: () => r.get().then(thawSnap), set: (d) => r.set(d), update: (d) => r.update(d), delete: () => r.delete(),
    acquire: typeof r.acquire === 'function' ? (o) => r.acquire(o) : undefined,
    onSnapshot: (next, err) => r.onSnapshot((snap) => next(thawSnap(snap)), err),
    collection: (p) => thawCol(r.collection(p)),
  };
}
function thawCol(q) {
  if (!q) return q;
  return {
    id: q.id, path: q.path,
    where: (...a) => thawCol(q.where(...a)), orderBy: (...a) => thawCol(q.orderBy(...a)), limit: (n) => thawCol(q.limit(n)),
    get: () => q.get().then(thawQSnap), onSnapshot: (next, err) => q.onSnapshot((snap) => next(thawQSnap(snap)), err),
    doc: typeof q.doc === 'function' ? (...a) => thawDoc(q.doc(...a)) : undefined,
    add: typeof q.add === 'function' ? (d) => q.add(d).then(thawDoc) : undefined,
  };
}
const thawDb = (db) => db && { doc: (p) => thawDoc(db.doc(p)), collection: (p) => thawCol(db.collection(p)) };
function initCaps() {
  if (!inClaude) {
    Object.assign(S.caps, {
      ready: true, sample: null, db: makeLocalDB(), uid: 'local', canEdit: true,
      downloads: { save: async ({ filename, data }) => { anchorDownload(filename, data); return { status: 'saved' }; } },
    });
    if (parseAI(S.settings.genAI)?.kind !== 'conn' && S.conns[0]) { S.settings.genAI = 'conn:' + S.conns[0].id; saveSettings(); }
    subscribeCfg(); subscribeLessons();
    renderParams(); renderAll(); renderCfg();
    initProducts();
    return;
  }
  const c = window.claude;
  const get = (n) => Promise.resolve().then(() => c.use(n)).catch(() => null);
  const pSample = get('sample').then(async (sample) => {
    S.caps.sample = sample;
    if (sample) { try { const lim = await sample.limits(); S.caps.tools = !!lim?.tools; } catch { S.caps.tools = false; } }
    renderStatus(); renderAIHint(); renderRunControls(); if (S.tab === 'agent') renderTab();
  });
  const pUser = get('user').then(async (user) => {
    S.caps.user = user;
    if (user) {
      try { S.caps.uid = await user.id(); } catch { S.caps.uid = null; }
      try { S.caps.canEdit = !!(await user.canEdit()); } catch { S.caps.canEdit = false; }
    }
  });
  const pDb = get('db').then((db) => { S.caps.db = thawDb(db); if (db) { subscribeCfg(); subscribeLessons(); } });
  const pDl = get('downloads').then((d) => { S.caps.downloads = d; });
  const pMcp = get('mcp').then(async (mcp) => {
    S.caps.mcp = mcp;
    // мост приложения Claude виден в списке только внутри приложения; список ничего не спрашивает у пользователя
    if (mcp) { try { const r = await mcp.listTools(); S.hostListed = !!r?.servers?.some((x) => HOST_NAMES.includes(x.server)); } catch { S.hostListed = false; } }
  });
  Promise.allSettled([pSample, pUser, pDb, pDl, pMcp]).then(() => {
    S.caps.ready = true; renderAll(); renderAIHint(); renderCfgFoot();
    if (S.caps.db && S.caps.uid) initProducts(); else { S.sessionReady = true; S.prodReady = true; renderAll(); }
    if (relayOn()) sferaPing().then(() => { if (S.tab === 'cases') renderTmsBar(); }); // вкладка с загрузчиком начинает принимать задания
    if (S.caps.db && S.caps.uid && inClaude) { workerPeer(); setTimeout(workerStart, 1500); }
  });
}

/* ================= boot ================= */
addSampleDoc();
renderParams();
renderMode();
renderQaCtx();
renderCfg();
bind();
renderAll();
if (window.__qaTest) window.__qa = { parsePdf, parseSheet, checklistRows, checklistMarkdown, checklistJSON, checklistPdfDoc, checklistPdfBlob, capChecklist, clCheckText, planFromChecklistOn, ask, downloadBridge, stageTier, stageModel, matchBatch, normPrio, withCritical, ruleViolations, applyRuleFixes, capChecks, prioClass, prioRu, PRIOS, templateBlock, pickTitleText, orderLikeTemplate, tagTitle, titleTagFor, titleTagOk, tplInfo, S, newRun, renderAll, renderTabs, renderTab, caseUI, deHtml, cleanCase, cleanPre, tmsCase, sferaCase, sferaExportJSON, unfence, docsFor, kbFit, kbBySubs, kbPack, kbMaterial, kbPages, kbPartsHash, kbProgress, kbIdxRead, kbIdxWrite, kbOutline, outOfScope, noReqRefs, addDraftToProduct, kbRead, loadKb, savePassport, productBlock, readProduct, kbGenBlock, kbRank, kbSections, kbStale, kbSynthBody, kbLoadAll, makeTools, openHistory, readSession, cleanCase, cleanPre, deHtml, tmsCase, reduceSelect, reduceDraft, questionsExport, questionsLetter, questionsMarkdown, runEtalon, etalonDecide, promptEtalon, etalonFit, openEtalon, ctxSwitch, ctxRefresh, ctxConnect, ctxKbParse, ctxKbSerialize, kbSave, kbBlock, ctxParseTpl, ctxMakeTpl, ctxParseLessons, ctxMakeLessons, ctxParseQaCtx, ctxMakeQaCtx, ctxPut, ctxFlush, ctxExportPlan, ctxSend, ctxAutoRun, ctxAutoToggle, ctxPickFolder, hydrateProd, curProduct, saveCfg, addLesson, knowBlocks, makeTools }; // только для автотестов
initCaps();
})();
