/* ================= templates & helpers ================= */
const ID_KEYS = ['id', 'ID', 'Id', 'key', 'caseId', 'testCaseId', 'externalId', 'code'];
function tplInfo(type) {
  const t = S.cfg.tpl[type];
  const p = tryParse(t.example);
  if (!p.ok) return { ok: false, error: 'Пример тест-кейса — некорректный JSON (' + p.error + ')' };
  // старые сохранённые примеры содержат High/Medium/Low: в запросы к модели идут уже четыре значения приоритета
  const examples = (Array.isArray(p.value) ? p.value : [p.value]).filter((x) => x && typeof x === 'object' && !Array.isArray(x)).map((x) => { const { request, ...rest } = x; return typeof rest.priority === 'string' ? { ...rest, priority: normPrio(rest.priority) } : rest; });   // блока request в кейсе больше нет
  if (!examples.length) return { ok: false, error: 'Пример должен быть JSON-объектом или массивом объектов' };
  const structure = examples[0];
  return { ok: true, examples, structure, idField: ID_KEYS.find((k) => k in structure) || null, fields: Object.keys(structure) };
}
const selectedTypes = () => TYPES.filter((t) => S.settings.types[t]);
const arrOf = (v) => (Array.isArray(v) ? v : []);
const arrStr = (v) => (Array.isArray(v) ? v : v ? [v] : []).map((x) => (typeof x === 'string' ? x : JSON.stringify(x))).map((s) => s.trim()).filter(Boolean);
/* приоритет — только четыре значения; старые записи (high/medium/low, High/Medium/Low) приводятся к ним */
const PRIOS = ['P4_CRITICAL', 'P3_HIGH', 'P2_MEDIUM', 'P1_LOW'];
const normPrio = (p) => { const s = String(p || '').toLowerCase(); return /p4|крит|critical/.test(s) ? 'P4_CRITICAL' : /p3|high|выс/.test(s) ? 'P3_HIGH' : /p1|low|низ/.test(s) ? 'P1_LOW' : 'P2_MEDIUM'; };
const PRIO_RU = { P4_CRITICAL: 'Критический', P3_HIGH: 'Высокий', P2_MEDIUM: 'Средний', P1_LOW: 'Низкий' };
const prioRu = (p) => PRIO_RU[normPrio(p)];
const normKey = (s) => String(s).toLowerCase().replace(/ё/g, 'е').replace(/[^a-zа-я0-9]+/g, ' ').trim();
function normSuites(v) {
  const out = new Set();
  for (const s of arrStr(v)) {
    const x = s.toLowerCase();
    if (/smoke|смоук|дым/.test(x)) out.add('smoke');
    if (/regress|регресс/.test(x)) out.add('regression');
  }
  return SUITES.filter((s) => out.has(s));
}
/* проверка с приоритетом P4_CRITICAL всегда входит в смоук и в регресс (код, а не просьба модели) */
const withCritical = (prio, suites) => (normPrio(prio) === 'P4_CRITICAL' ? [...SUITES] : suites);
function indexReqs(run) { run.reqById = Object.fromEntries(run.requirements.map((r) => [r.id, r])); }
function hash(str) {
  let h1 = 0xdeadbeef, h2 = 0x41c6ce57;
  for (let i = 0; i < str.length; i++) { const ch = str.charCodeAt(i); h1 = Math.imul(h1 ^ ch, 2654435761); h2 = Math.imul(h2 ^ ch, 1597334677); }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(36);
}
const outputsOf = (run) => run.settings.outputs || { cases: true, checklist: false };
const checklistItems = (run) => (run.checklist?.groups || []).flatMap((g) => g.items);

/* ================= prompts ================= */
const fence = '```';
const typesListText = (types) => types.map((t) => `"${t}"`).join(', ');
const rulesText = () => S.cfg.rules.trim();
function clarBlock(run) {
  const qa = (run?.questions || []).filter((q) => q.answer && q.answer.trim());
  return (qa.length ? `\n## Уточнения аналитика (ответы на вопросы к документации)\n${qa.map((q) => `- Вопрос: ${q.text}\n  Ответ: ${q.answer.trim()}`).join('\n')}\n` : '') + lessonsBlock('generation');
}
/* дополнительный контекст от QA: общий и по видам тестов */
const ctxHas = (c) => !!c && ['all', ...TYPES].some((k) => c[k] && c[k].trim());
const ctxOf = (run) => (run?.qaCtx || S.qaCtx);
function qaCtxBlock(ctx, type, forReview) {
  const c = ctx || {}, parts = [];
  if (c.all?.trim()) parts.push(`Для всех видов тестов:\n${c.all.trim()}`);
  for (const t of type ? [type] : TYPES) if (c[t]?.trim()) parts.push(`Для ${TL[t]}-тестов:\n${c[t].trim()}`);
  if (!parts.length) return '';
  return `\n## Дополнительный контекст от QA\n${forReview
    ? 'Тестировщик дал этот контекст к документации. Шаги, предусловия, экраны и тестовые данные, взятые из него, не считай ошибкой или выдумкой.'
    : 'Учитывай его при составлении проверок, предусловий, шагов и тестовых данных: экраны и навигация к ним, окружения, роли, учётные записи, данные. Если контекст уточняет документацию — следуй контексту. Не придумывай на его основе функциональность, которой нет в документах.'}\n${parts.join('\n\n')}\n`;
}
function lessonsBlock(scope) {
  const ls = S.lessons.filter((l) => l.scope === 'both' || l.scope === scope).slice(-60);
  return ls.length ? `\n## Правила из замечаний команды — соблюдай обязательно\n${ls.map((l) => '- ' + l.text).join('\n')}\n` : '';
}
/* знания о продукте: паспорт и уже готовые кейсы и пункты чек-листа */
// паспорт без ограничения длины: хранится отдельной записью meta/passport (длинный — частями), в запросы идут пункты по теме
function knowOf(run) {
  const pid = run ? run.productId : S.productId;
  if (!pid || pid !== S.productId) return null;
  const p = curProduct();
  const idx = S.prodIndex.pid === pid ? S.prodIndex : { cases: [], checklist: [] };
  return { name: p?.name || 'Продукт', passport: String(p?.passport?.text || ''), cases: idx.cases, checklist: idx.checklist };
}
/* из паспорта в запрос попадают только пункты, близкие к теме запроса */
const KNOW_CAP = { single: 8000, batch: 4000, analyze: 3000, review: 3000 };
function passportFor(passport, focus, cap) {
  const text = String(passport || '').trim();
  if (text.length <= cap) return text;
  const q = new Set(tokens(focus || ''));
  const items = []; let head = '';
  for (const line of text.split('\n')) {
    if (/^#{1,3}\s/.test(line)) { head = line.replace(/^#+\s*/, '').trim(); continue; }
    if (!line.trim()) continue;
    const s0 = [...new Set(tokens(line))].reduce((a, t) => a + (q.has(t) ? 1 : 0), 0);
    items.push({ head, line, s: s0 + (/термин/i.test(head) ? 0.5 : 0), k: items.length });
  }
  const pick = items.filter((x) => x.s > 0).sort((a, b) => b.s - a.s || a.k - b.k);
  const out = []; let size = 0;
  for (const x of pick) { if (size + x.line.length + 1 > cap) continue; out.push(x); size += x.line.length + 1; }
  out.sort((a, b) => a.k - b.k);
  let cur = null; const lines = [];
  for (const x of out) { if (x.head !== cur) { cur = x.head; if (cur) lines.push(`## ${cur}`); } lines.push(x.line); }
  return lines.join('\n');
}
function productBlock(run, mode = 'batch', focus = '') {
  if (run?.noKb) return ''; // перегенерация по правилам: паспорт продукта не используется
  const k = knowOf(run);
  if (!k || !k.passport.trim()) return '';
  const cap = Math.round((KNOW_CAP[mode] || KNOW_CAP.batch) * (economy() ? 0.6 : 1));
  const body = passportFor(k.passport, focus, cap);
  if (!body) return '';
  const lead = mode === 'review'
    ? 'Накопленные знания о продукте. Названия экранов, роли, термины и правила, взятые из них, не считай выдумкой. Если кейс противоречит этим знаниям и документам — это замечание.'
    : mode === 'analyze'
      ? 'Агент накопил эти знания по прошлым документам продукта. Используй их, чтобы понимать термины и связи между модулями; требования выделяй только из документов этого фрагмента.'
      : 'Агент накопил эти знания по прошлым документам и запускам продукта. Используй те же названия экранов, ролей, сущностей и термины, учитывай связи с другими модулями. Если текущие документы противоречат знаниям — приоритет у документов.';
  return `\n## Знания о продукте «${k.name}»${body.length < k.passport.trim().length ? ' — пункты по теме запроса' : ''}\n${lead}\n${body}\n`;
}
/* ---------- база знаний в генерации ----------
   В каждый запрос анализа, чек-листа, плана, кейсов, доработки и ревью идут сводки разделов базы знаний по теме этого
   запроса — собранные из всех документов продукта, включая расшифровки созвонов и демо. Так генерация учитывает правила,
   лимиты, роли и связи из документов, которых нет среди документов запуска. Отбор локальный: по словам запроса,
   редкие слова весят больше частых (idf), совпадение с названием раздела — втрое больше. */
const KB_GEN_CAP = { single: 12000, batch: 8000, analyze: 5000, review: 5000 };
const KB_GEN_LEAD = {
  analyze: 'Сводки разделов базы знаний по теме фрагмента — собраны агентом из всех документов продукта, включая расшифровки созвонов и демо (источник указан в скобках). Используй их, чтобы понимать термины и связи; требования выделяй только из документов этого фрагмента. Если фрагмент расходится со сводкой или по этой теме отмечены расхождения между документами — задай конкретный вопрос в questions.',
  single: 'Сводки разделов базы знаний по теме этих требований — собраны агентом из всех документов продукта, включая расшифровки созвонов и демо (источник указан в скобках). Учитывай их в проверках: бизнес-правила, лимиты, роли и права, тексты сообщений, связи с соседними разделами и сквозные сценарии — даже если в требованиях это описано короче. Названия экранов, полей и кнопок бери дословно. Если сводка расходится с требованиями запуска, следуй требованиям; спорное из «Расхождений между документами» не выдавай за факт.',
  batch: 'Сводки разделов базы знаний по теме этих кейсов — из всех документов продукта, включая расшифровки созвонов и демо. Бери из них конкретику: точные названия, значения, тексты сообщений, роли, предусловия и связи с другими разделами. Приоритет — у требований; спорное из «Расхождений между документами» не используй как ожидаемый результат.',
  review: 'Сводки разделов базы знаний по теме — из всех документов продукта. Названия, правила и значения из них не считай выдумкой. Если кейс противоречит и требованиям, и базе знаний — это замечание; если требования и база знаний расходятся между собой — отметь это как вопрос, а не ошибку кейса.',
};
const kbTokMemo = new WeakMap();
function kbToks(d, b) {
  let v = kbTokMemo.get(d);
  if (!v) { v = { head: new Set(helpTokens(`${b.title} ${b.summary || d.summary || ''}`)), body: new Set(helpTokens(kbSectionText(d))) }; kbTokMemo.set(d, v); }
  return v;
}
// разделы, загруженные целиком (сводка или выдержки), — для генерации и инструментов агента
function kbSections(pid) {
  const own = !pid || S.kb.pid !== pid ? [] : S.kb.index.blocks.map((b) => ({ b, d: S.kb.cache[b.id] })).filter((x) => x.d && (x.d.synth || arrOf(x.d.parts).length));
  return own; // при подключённой папке оглавление и разделы уже из её файлов (kbIdxRead → ctxKbIndex)
}
function kbRank(focus, secs) {
  const q = new Set(helpTokens(focus));
  if (!q.size || !secs.length) return [];
  const toks = secs.map((x) => kbToks(x.d, x.b)), df = new Map();
  for (const t of toks) for (const w of new Set([...t.head, ...t.body])) df.set(w, (df.get(w) || 0) + 1);
  const idf = (w) => Math.log(1 + secs.length / (df.get(w) || 1));
  return secs.map((x, i) => { let sc = 0; for (const w of q) sc += toks[i].head.has(w) ? 3 * idf(w) : toks[i].body.has(w) ? idf(w) : 0; return { ...x, s: sc }; })
    .filter((x) => x.s > 0).sort((a, b) => b.s - a.s);
}
// текст раздела в лимит: строки по теме запроса и расхождения — в первую очередь, порядок и подзаголовки сохраняются
// длинный текст — страницами не больше cap знаков по границам строк
function kbPages(text, cap) {
  const pages = [];
  let cur = '';
  for (const ln of String(text || '').split('\n')) {
    for (let s = ln; ; ) {
      const take = s.slice(0, cap); s = s.slice(cap);
      if (cur && cur.length + take.length + 1 > cap) { pages.push(cur); cur = ''; }
      cur += (cur ? '\n' : '') + take;
      if (!s.length) break;
    }
  }
  if (cur || !pages.length) pages.push(cur);
  return pages;
}
function kbFitText(text, focus, cap) {
  const t = String(text || '').trim();
  if (t.length <= cap) return t;
  const q = new Set(helpTokens(focus));
  const lines = t.split('\n').filter((l) => l.trim());
  const scored = lines.map((l, k) => ({ l, k, h: /^#{1,4}\s/.test(l), s: /^#{1,4}\s/.test(l) ? 0 : [...new Set(helpTokens(l))].reduce((a, w) => a + (q.has(w) ? 1 : 0), 0) + (/расхожд/i.test(l) ? 2 : 0) + 0.01 }));
  const keep = new Set(); let size = 0;
  for (const x of scored.filter((y) => !y.h).sort((a, b) => b.s - a.s || a.k - b.k)) { if (size + x.l.length + 1 > cap) continue; keep.add(x.k); size += x.l.length + 1; }
  const out = [];
  for (let k = 0; k < scored.length; k++) {
    const x = scored[k];
    if (x.h) { const next = scored.slice(k + 1).find((y) => y.h || keep.has(y.k)); if (next && !next.h) out.push(x.l); }
    else if (keep.has(k)) out.push(x.l);
  }
  return out.join('\n');
}
function kbGenBlock(run, mode = 'batch', focus = '') {
  if (run?.noKb) return ''; // перегенерация по правилам: разделы базы знаний не используются
  const pid = run ? run.productId : S.productId;
  const secs = kbSections(pid);
  if (!secs.length || !String(focus || '').trim()) return '';
  const cap = Math.round((KB_GEN_CAP[mode] || KB_GEN_CAP.batch) * (economy() ? 0.6 : 1));
  const ranked = kbRank(focus, secs);
  if (!ranked.length) return '';
  const pick = ranked.filter((x) => x.s >= ranked[0].s * 0.3).slice(0, 8);
  const titleOf = new Map(S.kb.index.blocks.map((b) => [b.id, b.title]));
  const out = []; let left = cap;
  for (const x of pick) {
    if (left < 500) break;
    const conf = arrOf(x.d.conflicts).length;
    const body = kbFitText(kbSectionText(x.d), focus, Math.min(left - 150, Math.max(1500, Math.round(cap / Math.min(pick.length, 3))))).replace(/^###\s/gm, '#### ');
    if (!body) continue;
    const links = arrOf(x.d.links).map((id) => titleOf.get(id)).filter(Boolean);
    const piece = `### Раздел «${x.b.title}»${conf ? ` · расхождений между документами: ${conf}` : ''}\n${body}${links.length ? `\nСвязан с разделами: ${links.join(', ')}` : ''}`;
    out.push(piece); left -= piece.length + 2;
  }
  return out.length ? `\n## База знаний продукта — разделы по теме\n${KB_GEN_LEAD[mode] || KB_GEN_LEAD.batch}\n${out.join('\n\n')}\n` : '';
}
const knowBlocks = (run, mode, focus) => productBlock(run, mode, focus) + kbGenBlock(run, mode, focus);
const chunkFocus = (ch) => ch.blocks.map((b) => b.text).join(' ').slice(0, 20000);
// перед генерацией: свежее оглавление и все разделы — запросы собираются синхронно
async function kbLoadAll(pid) {
  if (!pid || !S.caps.db || pid !== S.productId) return 0;
  await loadKb(pid);
  if (S.kb.pid !== pid) return 0;
  const need = S.kb.index.blocks.filter((b) => { const c = S.kb.cache[b.id]; return !c || (c.updatedAt || 0) < (b.updatedAt || 0); });
  await pool(need, 4, async (b) => { try { const d = await kbRead(pid, b.id); if (d && S.kb.pid === pid) S.kb.cache[b.id] = d; } catch { /* без раздела */ } });
  return kbSections(pid).length;
}
const kbToolsHint = (run) => (kbSections(run?.productId).length ? ' Сведения из других документов продукта и расшифровок созвонов ищи в базе знаний: search_knowledge_base и read_knowledge_section.' : '');
/* документы: небольшие — целиком, большие — только фрагменты по теме запроса */
const SMALL_DOCS = 4000;
function docsBlock(run, focus, mode = {}) {
  const docs = docsFor(run), total = docs.reduce((a, d) => a + d.chars, 0);
  if (!total) return '';
  if (total <= SMALL_DOCS) return `\n## Исходные документы\n${docs.map((d) => `<document name="${d.name}">\n${d.text}\n</document>`).join('\n\n')}\n`;
  const cap = economy() ? 3000 : 4500;
  ensureIndex();
  const names = new Set(docs.map((d) => d.name));
  const q = [...new Set(tokens(focus || ''))];
  const scored = INDEX.filter((x) => names.has(x.doc)).map((x) => { let sc = 0; for (const t of q) { const c = x.tf.get(t); if (c) sc += 1 + Math.log(c); } return { x, sc }; })
    .filter((o) => o.sc > 0).sort((a, b) => b.sc - a.sc);
  const out = []; let size = 0;
  for (const o of scored) { if (size + o.x.text.length > cap) continue; out.push(o.x); size += o.x.text.length; if (size > cap * 0.9) break; }
  if (!out.length) return '';
  out.sort((a, b) => (a.doc === b.doc ? a.offset - b.offset : a.doc < b.doc ? -1 : 1));
  return `\n## Фрагменты исходных документов\nВыбраны по теме этого запроса${mode.tools ? '; остальное найди инструментами' : ''}.\n${out.map((x) => `<excerpt document="${x.doc}" offset="${x.offset}">\n${x.text}\n</excerpt>`).join('\n')}\n`;
}
const reqText = (r) => (r ? `${r.title} ${r.description} ${r.criteria.join(' ')} ${r.quote || ''}` : '');
function relevantExisting(run, kind, type, limit, text) {
  const k = knowOf(run);
  if (!k || run?.settings?.skipExisting === false) return [];
  const all = (kind === 'cases' ? k.cases : k.checklist).filter((x) => x.r !== run?.id && (!type || x.t === type));
  if (!all.length) return [];
  const src = text || (run?.requirements || []).filter((r) => r.inScope).map((r) => `${r.title} ${r.description} ${r.criteria.join(' ')}`).join(' ');
  const q = new Set(tokens(src));
  return all.map((x) => ({ x, s: [...new Set(tokens(x.n))].reduce((a, t) => a + (q.has(t) ? 1 : 0), 0) }))
    .filter((o) => o.s > 0).sort((a, b) => b.s - a.s).slice(0, limit).map((o) => o.x);
}
function relevantSrc(run, reqs) {
  const q = new Set(tokens(reqs.map((r) => `${r.title} ${r.description} ${r.criteria.join(' ')}`).join(' ')));
  return activeCases(run).filter((c) => c.status !== 'new').map((c) => ({ i: c.dispId, t: c.type, n: pickTitleText(c.testCase).slice(0, 140) }))
    .map((x) => ({ x, s: [...new Set(tokens(x.n))].reduce((a, t) => a + (q.has(t) ? 1 : 0), 0) })).filter((o) => o.s > 0).sort((a, b) => b.s - a.s).slice(0, 120).map((o) => o.x);
}
function existingBlock(list, kind, note) {
  if (!list.length) return '';
  return `\n## Уже есть в продукте\n${kind === 'cases' ? 'Тест-кейсы' : 'Пункты чек-листа'} из прошлых запусков продукта, похожие на текущую работу (id, вид, формулировка):\n${list.map((x) => `- ${x.i} [${x.t}] ${x.n}`).join('\n')}\n${note}\n`;
}
const SUITES_RULE = /*@md:rules/suites.md*/'';
/* объём тестирования: поведение системы через её интерфейсы. Без исследовательских тестов и без отдельных тестов на БД.
   Проверка состояния БД допустима шагом внутри кейса; данные вручную в БД не готовятся — их создаёт сама система */
const SCOPE_RULE = /*@md:rules/scope.md*/'';
const SCOPE_RX_EXPL = /исследовательск|exploratory|свободн[а-яёa-z]*\s+(поиск|исследован|тестирован)|на\s+усмотрение\s+тестировщик/i;
// ручная подготовка данных в БД
const SCOPE_RX_DBW = /\bINSERT\s+INTO\b|\bUPDATE\s+\S+\s+SET\b|\bDELETE\s+FROM\b|(создать|добавить|вставить|изменить|удалить)\s+(запис[а-яё]*|строк[а-яё]*)\s+(в|из)\s+(БД|базе?\s+данных|таблиц)|напрямую\s+в\s+(БД|базу)/i;
// упоминание БД и признаки проверки через интерфейс системы
const SCOPE_RX_DB = /\bSQL\b|\bSELECT\b[\s\S]{0,80}\bFROM\b|(^|[^а-яё])(БД|базе?\s+данных|базу\s+данных)([^а-яё]|$)|в\s+таблиц[а-яё]*\s+\S+/i;
const SCOPE_RX_IFACE = /\b(GET|POST|PUT|PATCH|DELETE)\s+\/|\/api\b|\bAPI\b|запрос|ответ|экран|форм[а-яё]*|кнопк|страниц|интерфейс|\bUI\b|пользовател|через\s+(UI|API)/i;
// проверка вне объёма: исследовательская, ручная подготовка данных в БД или отдельная проверка только БД (без действия через UI или API)
const outOfScope = (t) => { const x = String(t || ''); return SCOPE_RX_EXPL.test(x) || SCOPE_RX_DBW.test(x) || (SCOPE_RX_DB.test(x) && !SCOPE_RX_IFACE.test(x)); };
/* ---------- правила команды, которые проверяет код: модель может их не соблюсти ----------
   applyRuleFixes — безопасные исправления на месте (без обращения к модели);
   ruleViolations — нарушения, которые исправляет модель (замечание ревью, кнопка «Исправить»). */
const SERVICE_STATE_RX = /(сервис|служб|консьюмер|потребител|обработчик|брокер|топик)[^.;\n]{0,80}?(?<![а-яёa-z])(запущен\w*|работа(ет|ют)|подписан\w*|подключ[её]н\w*|развёрнут\w*|развернут\w*|поднят\w*)|подписан\w*\s+на\s+(топик|очеред|канал)/i;
const KAFKA_RX = /kafka|кафк|топик|topic/i;
const HTTP_RX = /\b(GET|POST|PUT|PATCH|DELETE)\b/;
const KAFKA_BANNED_RX = /подготовь(те)?\s+сообщение|отправить\s+подготовленное\s+сообщение/i;
const API_CALL_FORM_RX = /^Вызвать (GET|POST|PUT|PATCH|DELETE) \{baseURL\}\/\S*/;
/* адрес вызова API везде одинаково: {baseURL}/путь, где {baseURL} — адрес тестового стенда.
   Код приводит к этому виду «МЕТОД /путь», «МЕТОД https://хост/путь» и другие записи переменной ({{baseUrl}}, {base_url}, ${host}). */
const BASE_URL_VAR_RX = /\$?\{\{?\s*(?:base[_-]?url|baseurl|base[_-]?uri|host|host[_-]?url|stand|стенд)\s*\}?\}/gi;
const API_ADDR_RX = /\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)(\s+)(?:https?:\/\/[^\s/"'`«»)]+)?(\/[^\s"'`«»),;]*)/g;
const baseUrlText = (s) => String(s).replace(BASE_URL_VAR_RX, '{baseURL}').replace(API_ADDR_RX, (m, meth, sp, path) => `${meth}${sp}{baseURL}${path}`);
const baseUrlDeep = (v) => (typeof v === 'string' ? baseUrlText(v) : Array.isArray(v) ? v.map(baseUrlDeep) : v && typeof v === 'object' ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, baseUrlDeep(x)])) : v);
const API_CALL_VERB_RX = /^(отправить|выполнить|сделать|вызвать)(\s|$)/i;
const REQ_REF_RX = /\bR-\d{3}\b/;
const RULE_TEXT = {
  'service-state': 'В предусловиях или шагах описано состояние сервиса или подписки (запущен, подписан, подключён). Это окружение, оставьте только действия и проверки.',
  'kafka-method': 'Сообщение в Kafka описано с HTTP-методом. Укажите только топик, ключ и тело сообщения.',
  'kafka-steps': 'Шаги «Подготовь сообщение» и «Отправить подготовленное сообщение» не используются: сообщение указывается в шаге «Отправить сообщение:» с блоком кода.',
  'api-call': 'Шаг вызова API не в форме «Вызвать МЕТОД {baseURL}/ЭНДПОИНТ с телом:» с блоком кода для тела.',
  'req-refs': 'В тексте кейса указаны идентификаторы требований (R-NNN). Связь с требованиями хранится отдельно.',
  'scope': 'Кейс выходит за объём тестирования: исследовательская проверка, проверка только в БД или ручная подготовка данных в БД.',
  'priority': 'Приоритет не из четырёх значений: P1_LOW, P2_MEDIUM, P3_HIGH, P4_CRITICAL.',
};
const RULE_LABEL = { 'service-state': 'состояние сервисов', 'kafka-method': 'HTTP-метод в Kafka', 'kafka-steps': 'шаги подготовки Kafka', 'api-call': 'форма вызова API', 'req-refs': 'ссылки на R-NNN', 'scope': 'вне объёма', 'priority': 'приоритет' };
const allStrings = (v, out = []) => {
  if (typeof v === 'string') out.push(v);
  else if (Array.isArray(v)) v.forEach((x) => allStrings(x, out));
  else if (v && typeof v === 'object') Object.values(v).forEach((x) => allStrings(x, out));
  return out;
};
/* безопасные исправления: приоритет, наборы, блок request у API; возвращает число исправлений.
   Метку в названии ревью не дописывает: вручную правленое название остаётся с предупреждением */
function applyRuleFixes(c) {
  const tc = c.testCase || {};
  let n = 0;
  if (c.type === 'api' && 'request' in tc) { delete tc.request; n++; }
  for (const k of Object.keys(tc)) { const v = baseUrlDeep(tc[k]); if (JSON.stringify(v) !== JSON.stringify(tc[k])) { tc[k] = v; n++; } }   // адрес API — {baseURL}/путь
  if (typeof tc.priority === 'string' && tc.priority !== normPrio(tc.priority)) { tc.priority = normPrio(tc.priority); n++; }
  const suites = withCritical(tc.priority, c.suites || []);
  if (suites.length !== (c.suites || []).length) { c.suites = suites; n++; }
  return n;
}
/* нарушения, которые код не исправляет: id правила и текст */
function ruleViolations(c) {
  const tc = c.testCase || {}, texts = allStrings(tc), out = [];
  const add = (id) => out.push({ id, text: RULE_TEXT[id] });
  if (texts.some((t) => SERVICE_STATE_RX.test(t))) add('service-state');
  if (texts.some((t) => KAFKA_RX.test(t) && HTTP_RX.test(t))) add('kafka-method');
  if (texts.some((t) => KAFKA_BANNED_RX.test(t))) add('kafka-steps');
  if (c.type === 'api' && arrOf(tc.steps).some((s) => { const a = String(s?.action || ''); return API_CALL_VERB_RX.test(a) && HTTP_RX.test(a) && !API_CALL_FORM_RX.test(a); })) add('api-call');
  if (texts.some((t) => REQ_REF_RX.test(t))) add('req-refs');
  if (texts.some((t) => outOfScope(t))) add('scope');
  if (typeof tc.priority === 'string' && !PRIOS.includes(tc.priority)) add('priority');
  return out;
}
/* в тексте кейса нет отсылок к требованиям QA pro: связь с требованиями хранится отдельно (requirementIds) */
const REQ_REF_RULE = /*@md:rules/req-refs.md*/'';
const TITLE_TAG_RULE = /*@md:rules/title-tags.md*/'';
const KAFKA_RULE = /*@md:rules/kafka.md*/'';
const PRIORITY_RULE = /*@md:rules/priority.md*/'';
const PRECONDITIONS_RULE = /*@md:rules/preconditions.md*/'';
const API_CALL_RULE = /*@md:rules/api-call.md*/'';
const SERVICE_STEPS_RULE = /*@md:rules/service-steps.md*/'';
const DESC_KEY_RX = /description|описан|objective|цел[ья]|scenario|сценари|summary|назначени|comment|коммент/i;
function noReqRefs(v, desc = false) {
  let t = String(v ?? '');
  if (!/R-\d{2,4}|требовани/i.test(t)) return t;
  if (desc) t = t.split('\n').filter((l) => !/^\s*(?:[-*•]\s*)?(?:проверяем[а-яё]*\s+|покрывает\s+|связанн[а-яё]*\s+|исходн[а-яё]*\s+)?требовани[а-яё]*\s*(?:[:—–-]|R-\d)/i.test(l)).join('\n');
  const cap = /^[A-ZА-ЯЁ]/.test(t.trim());
  t = t.replace(/(провер[а-яё]*)\s+требовани[а-яё]*\s+R-\d{2,4}(?:\s*(?:[,;]|и)\s*R-\d{2,4})*\s*[:—–-]?\s*/gi, '$1: ')
    .replace(/\s*[([]\s*(?:требовани[а-яё]*\s*:?\s*)?R-\d{2,4}(?:\s*(?:[,;]|и)\s*R-\d{2,4})*\s*[)\]]/gi, '')
    .replace(/,?\s*(?:согласно|по|для|в\s+соответствии\s+с)\s+требовани[а-яё]*\s+R-\d{2,4}(?:\s*(?:[,;]|и)\s*R-\d{2,4})*/gi, '')
    .replace(/требовани[а-яё]*\s*:?\s*R-\d{2,4}(?:\s*(?:[,;]|и)\s*R-\d{2,4})*\s*[.:—–-]?\s*/gi, '')
    .replace(/\s*\bR-\d{3}\b(?:\s*[,;]\s*\bR-\d{3}\b)*/g, '')
    .replace(/[ \t]{2,}/g, ' ').replace(/\s+([.,;:])/g, '$1').replace(/^[ \t]*[.,;:—–-][ \t]*/gm, '').replace(/\n{3,}/g, '\n\n').trim();
  return cap && /^[a-zа-яё]/.test(t) ? t[0].toUpperCase() + t.slice(1) : t;
}
const noReqDeep = (v, key = '') => (typeof v === 'string' ? noReqRefs(v, DESC_KEY_RX.test(key)) : Array.isArray(v) ? v.map((x) => noReqDeep(x, key)) : v && typeof v === 'object' ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, noReqDeep(x, k)])) : v);
/* Тексты промптов лежат в prompts/<имя>.md; build.py подставляет их в PROMPTS.
   ⟦имя⟧ в тексте заменяется значением из vars (в порядке выражений исходного шаблона). */
const PROMPTS = /*@prompts*/null;
// правила, которые попали в последний собранный промпт: вставки *_RULE без заголовков, по ним видно, что агент применял
const RULE_NAMES = { SCOPE_RULE: 'объём тестов', SUITES_RULE: 'наборы смоук/регресс', LIMIT_RULE: 'лимит количества', REQ_REF_RULE: 'ссылки на требования', TITLE_TAG_RULE: 'метки названий', KAFKA_RULE: 'правила Kafka', PRIORITY_RULE: 'приоритеты', API_CALL_RULE: 'вызов API', SERVICE_STEPS_RULE: 'шаги с сервисами', PRECONDITIONS_RULE: 'предусловия' };
let lastRules = [];
function renderPrompt(name, vars) {
  lastRules = Object.keys(vars).filter((k) => /_RULE$/.test(k) && String(vars[k] || '').trim()).map((k) => RULE_NAMES[k] || k);
  return PROMPTS[name].replace(/⟦(\w+)⟧/g, (m, k) => (Object.prototype.hasOwnProperty.call(vars, k) ? String(vars[k]) : m));
}
function promptAnalyze(chunk, i, total, types, ctx, run) {
  const rules = rulesText();
  const qctx = qaCtxBlock(ctx);
  const pk = knowBlocks(run, 'analyze', chunkFocus(chunk));
  return renderPrompt("promptAnalyze", { "e1": i + 1, "total": total, "e3": chunk.blocks.map((b) => `<document name="${b.doc}" part="${b.part}/${b.parts}">\n${b.text}\n</document>`).join('\n\n'), "e4": typesListText(types), "SCOPE_RULE": SCOPE_RULE, "e6": rules ? `\n8. Правила команды: ${rules}` : '', "e7": qctx ? `\n${qctx}Используй контекст QA как дополнительный источник: если в нём есть проверяемые утверждения о поведении системы, выдели их как требования с doc "Контекст QA". Экраны, навигацию, окружения и тестовые данные требованиями не считай.\n` : '', "pk": pk });
}
// проверка полноты анализа: что пропущено во фрагменте
function promptAnalyzeMore(chunk, i, total, types, found) {
  return renderPrompt("promptAnalyzeMore", { "e1": i + 1, "total": total, "e3": chunk.blocks.map((b) => `<document name="${b.doc}" part="${b.part}/${b.parts}">\n${b.text}\n</document>`).join('\n\n'), "e4": found.map((r) => `- «${String(r?.title || '')}»${arrStr(r?.criteria).length ? ': ' + arrStr(r.criteria).join('; ') : ''}`).join('\n'), "e5": typesListText(types), "SCOPE_RULE": SCOPE_RULE });
}
// сверка покрытия: какие критерии требований не проверяет ни один кейс
function promptCoverageAudit(run, reqs, types) {
  const caseLine = (c) => { const tc = c.testCase || {}, ek = Object.keys(tc).find((k) => /^(expectedResult|expected_result|ожидаемый_?результат|result)$/i.test(k)); return `  - ${c.dispId} [${c.type}] ${pickTitleText(tc)}${ek ? ` → ${String(typeof tc[ek] === 'string' ? tc[ek] : JSON.stringify(tc[ek])).slice(0, 160)}` : ''}`; };
  const rules = rulesText();   // сверка видит те же правила, что и генерация: иначе дописывает кейсы, которые правила запрещают
  const e4 = `${rules ? `\n## Правила команды\n${rules}\n` : ''}${[TITLE_TAG_RULE, KAFKA_RULE, PRIORITY_RULE, PRECONDITIONS_RULE, API_CALL_RULE, SERVICE_STEPS_RULE, SUITES_RULE, REQ_REF_RULE].join('\n')}`;
  return renderPrompt("promptCoverageAudit", { "e1": typesListText(types), "SCOPE_RULE": SCOPE_RULE, "e4": e4, "e3": reqs.map((r) => `### ${r.id} «${r.title}» [${r.types.join(', ')}]
${r.description}${r.criteria.length ? `\nКритерии: ${r.criteria.map((c, k) => `${k + 1}) ${c}`).join('; ')}` : ''}
Кейсы:
${activeCases(run).filter((c) => c.requirementIds.includes(r.id)).map(caseLine).join('\n') || '  - нет'}`).join('\n\n') });
}
/* покрытие одного требования тремя вариантами; кейсы попадают в черновик запуска, их проверяют ревью и ручная правка */
const COVER_VARIANTS = {
  one: { title: 'Один тест (happy path)', kinds: ['positive'], one: true },
  positive: { title: 'Только позитивные проверки', kinds: ['positive'] },
  full: { title: 'Полное покрытие', kinds: ['positive', 'negative', 'boundary'] },
};
const COVER_MAX_CHECKS = 15;
function promptCoverRequirement(q, types) {
  return renderPrompt('promptCoverRequirement', {
    e1: typesListText(types), SCOPE_RULE,
    e2: `${q.id} «${q.title}» [${q.types.join(', ')}] [${q.priority}]\n${q.description}${q.criteria.length ? `\nКритерии: ${q.criteria.map((c, k) => `${k + 1}) ${c}`).join('; ')}` : ''}${q.quote ? `\nЦитата: «${q.quote}»` : ''}`,
    e3: q.types.join(', '),
  });
}
async function coverRequirement(run, q, variant) {
  const V = COVER_VARIANTS[variant];
  const types = run.settings.types || TYPES;
  const res = await ask(promptCoverRequirement(q, types), { step: 'cover', onProgress: () => {} });
  const kinds = new Set(V.kinds);
  const text = (v) => String(v ?? '').trim();
  let checks = arrOf(res?.checks).map((x) => ({ check: text(x?.check), kind: text(x?.kind).toLowerCase(), type: text(x?.type).toLowerCase() }))
    .filter((x) => x.check && kinds.has(x.kind));
  if (!checks.length) throw { message: `Модель не вернула подходящих проверок для ${q.id}. Попробуйте ещё раз.` };
  checks = checks.slice(0, V.one ? 1 : COVER_MAX_CHECKS);
  const primary = q.types.find((t) => types.includes(t)) || types[0];
  const byType = new Map();
  for (const x of checks) {
    const t = q.types.includes(x.type) && types.includes(x.type) ? x.type : primary;
    if (!byType.has(t)) byType.set(t, []);
    byType.get(t).push(x.check);
  }
  // новые номера после уже написанных пунктов: повторное покрытие не пропускается как уже сделанное
  const seqOf = (key) => Number((/^V-(\d+)#/.exec(key) || [])[1] || 0);
  const seq = 1 + Math.max(0, ...(run.doneKeys || []).map(seqOf));
  const items = [...byType].map(([type, list], k) => ({ id: `V-${pad(seq + k, 3)}`, type, title: `Покрытие: ${q.title}`, requirementIds: [q.id], checks: [...new Set(list)], variant }));
  const before = run.cases.length;
  await generateItems(run, items, 'cover');
  // один кейс на проверку: лишние кейсы из ответа модели не оставляем
  const limit = checks.length;
  if (run.cases.length - before > limit) run.cases.splice(before + limit);
  const added = run.cases.length - before;
  slog(run, 'cover', `${V.title} · ${q.id}: в черновик добавлено ${added} ${plural(added, 'кейс', 'кейса', 'кейсов')}`, added ? 'ok' : 'warn');
  return added;
}
function runCover(id, variant) {
  const run = S.run, q = run?.reqById[id];
  if (!q || !COVER_VARIANTS[variant]) return;
  if (!isDraft(run) || draftLocked(run)) return toast('Покрытие добавляет кейсы в черновик текущего запуска. Если запуск уже добавлен в проект, начните новый запуск.', 'err');
  return runTask('cover', async (r) => {
    const added = await coverRequirement(r, q, variant);
    toast(added ? `В черновик добавлено ${added} ${plural(added, 'кейс', 'кейса', 'кейсов')} для ${q.id}` : `Для ${q.id} кейсы не добавлены`, added ? 'ok' : 'warn');
  }, 'gen');
}
function reqCompact(r) { return `${r.id} [${r.types.join(', ')}] [${r.priority}] ${r.title}: ${r.description}${r.criteria.length ? ' Критерии: ' + r.criteria.join('; ') : ''}`; }
function promptChecklist(run, reqs, types, depth, quota = 0) {
  const d = DEPTHS.find((x) => x.id === depth) || DEPTHS[1];
  const rules = rulesText();
  const ex = relevantExisting(run, 'checklist', null, 200, reqs.map((r) => `${r.title} ${r.description} ${r.criteria.join(' ')}`).join(' '));
  return renderPrompt("promptChecklist", { "e1": typesListText(types), "d_prompt": d.prompt, "e3": rules ? `\nПравила команды: ${rules}` : '', "SCOPE_RULE": SCOPE_RULE, "e5": clarBlock(run), "e6": qaCtxBlock(ctxOf(run)), "e7": knowBlocks(run, 'single', reqs.map(reqText).join(' ')), "e8": existingBlock(ex, 'checklist', 'Не повторяй эти пункты — добавляй только новые проверки. Требование, которое уже полностью проверяют существующие пункты, можно не включать.'), "e9": reqs.map(reqCompact).join('\n'), "SUITES_RULE": SUITES_RULE, "LIMIT_RULE": checklistLimitRule(run, ex.length, quota) });
}
/* лимит проверок: в чек-лист сначала самые приоритетные позитивные, затем негативные; quota — сколько пунктов нужно в этом фрагменте */
function checklistLimitRule(run, hasExisting, quota = 0) {
  const n = strictTarget(run) ? run.settings.target : 0;
  if (!n) return `Каждое требование должно попасть хотя бы в один пункт${hasExisting ? ', кроме уже полностью проверенных существующими пунктами продукта' : ''}.`;
  if (quota) return `Ровно ${quota} ${plural(quota, 'пункт', 'пункта', 'пунктов')} в этом ответе — не меньше и не больше. Один пункт — одна проверка. Сначала самые приоритетные позитивные проверки основного сценария (P4_CRITICAL, затем P3_HIGH, P2_MEDIUM, P1_LOW), негативные — только после них. Если требований больше, чем пунктов, распределяй пункты так, чтобы каждое требование получило хотя бы один.`;
  return `Не больше ${n} ${plural(n, 'пункта', 'пунктов', 'пунктов')} во всём ответе — это строгий лимит. Сначала самые приоритетные позитивные проверки основного сценария (P4_CRITICAL, затем P3_HIGH, P2_MEDIUM, P1_LOW), негативные — только после них, пока не наберётся ${n}. Если пунктов не хватает на все требования, без проверок остаются наименее важные.`;
}
function promptPlan(run, reqs, types, depth) {
  const d = DEPTHS.find((x) => x.id === depth) || DEPTHS[1];
  const rules = rulesText();
  const ex = relevantExisting(run, 'cases', null, 200, reqs.map((r) => `${r.title} ${r.description} ${r.criteria.join(' ')}`).join(' ')).filter((x) => types.includes(x.t));
  const upd = run.mode === 'update' ? `\nКоманда актуализирует существующие тест-кейсы. Ниже — только требования, которые не покрыты кейсами из загруженного файла: составь проверки для них.\n${existingBlock(relevantSrc(run, reqs), 'cases', 'Это актуализированные кейсы из файла. Не повторяй их проверки.')}` : '';
  return renderPrompt("promptPlan", { "upd": upd, "e2": typesListText(types), "d_prompt": d.prompt, "e4": rules ? `\nПравила команды: ${rules}` : '', "SCOPE_RULE": SCOPE_RULE, "e6": clarBlock(run), "e7": qaCtxBlock(ctxOf(run)), "e8": knowBlocks(run, 'single', reqs.map(reqText).join(' ')), "e9": existingBlock(ex, 'cases', 'Не включай в план проверки, которые уже есть в этом списке: новые кейсы должны дополнять существующие, а не повторять их. Если требование уже полностью покрыто существующими кейсами, не создавай для него группу — укажи его в alreadyCovered с id этих кейсов.'), "e10": reqs.map(reqCompact).join('\n'), "e11": ex.length ? ' или в alreadyCovered' : '', "e12": ex.length ? ',"alreadyCovered":[{"requirementId":"R-002","caseIds":["UI-004"]}]' : '' });
}
function reqLine(r) {
  if (!r) return '';
  return `- ${r.id} «${r.title}»: ${r.description}${r.criteria.length ? `\n  Критерии: ${r.criteria.join('; ')}` : ''}${r.doc || r.section ? `\n  Источник: ${r.doc}${r.section ? ', раздел ' + r.section : ''}` : ''}${r.quote ? `\n  Цитата: "${r.quote}"` : ''}`;
}
/* HTML-разметка в тексте кейса (<p>, <br>, списки) — обычным текстом: шаблоны из ТМС часто хранят поля в HTML,
   а кейс QA pro — простой текст; разметку под ТМС добавляет выгрузка (в Сферу — свои <p>). */
const HTML_RX = /<\/?(p|br|div|span|ul|ol|li|b|i|u|s|strong|em|code|pre|h[1-6]|table|tr|td|th|tbody|thead|a|font|blockquote)\b[^>]*>/i;
/* Блок кода в тексте кейса — тело запроса или ответа, сообщение Kafka, SQL: три обратные кавычки (после них можно указать язык).
   В кейсе он остаётся обычным текстом, а при выгрузке в Сферу и в JSON Сферы становится <pre>. */
const FENCE_RX = /```[^\n`]*\n[\s\S]*?```/g;
function splitFences(s) {   // текст → куски: обычный текст и блоки кода (raw — вместе с кавычками, text — только код)
  s = String(s ?? '');
  const out = []; let last = 0, m;
  const rx = new RegExp(FENCE_RX.source, 'g');
  while ((m = rx.exec(s))) {
    if (m.index > last) out.push({ code: false, text: s.slice(last, m.index) });
    out.push({ code: true, raw: m[0], text: m[0].replace(/^```[^\n`]*\n/, '').replace(/\n?```$/, '') });
    last = rx.lastIndex;
  }
  if (last < s.length) out.push({ code: false, text: s.slice(last) });
  return out;
}
const unfence = (s) => (typeof s === 'string' && s.includes('```') ? splitFences(s).map((p) => p.text.replace(/^\n+|\n+$/g, '')).filter(Boolean).join('\n') : s);   // без кавычек: для XLSX
/* Что считаем блоком кода: сообщения Kafka, SQL, тела запроса и ответа API. Берём явные блоки (три обратные кавычки)
   и JSON/SQL, записанные прямо в строке — в том числе в старых кейсах. pretty — разбить длинный JSON по строкам (для экрана). */
function jsonEnd(s, i) {   // конец (не включая) сбалансированного {…} или […], начинающегося с i; -1 — не нашли
  let depth = 0, str = false;
  for (let k = i; k < s.length; k++) {
    const ch = s[k];
    if (str) { if (ch === '\\') k++; else if (ch === '"') str = false; continue; }
    if (ch === '"') str = true;
    else if (ch === '{' || ch === '[') depth++;
    else if (ch === '}' || ch === ']') { if (--depth === 0) return (s[i] === '{') === (ch === '}') ? k + 1 : -1; }
  }
  return -1;
}
function jsonCode(raw, pretty) {   // красивый вид JSON; null — это не JSON-данные
  if (raw.length < 8) return null;
  try {
    const v = JSON.parse(raw);
    if (!v || typeof v !== 'object') return null;
    return pretty && raw.length > 50 ? JSON.stringify(v, null, 2) : raw;
  } catch { return /^\{\s*"[^"]+"\s*:/.test(raw) ? raw : null; }   // с опечаткой в JSON всё равно показываем кодом
}
const SQL_START = /\b(?:SELECT\b[^;\n]*?\bFROM\b|INSERT\s+INTO\b|UPDATE\s+[\w."`\[\]]+\s+SET\b|DELETE\s+FROM\b|MERGE\s+INTO\b)/gi;
const SQL_MORE = /^\s*(?:FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|AND|OR|GROUP|ORDER|HAVING|LIMIT|VALUES|SET|ON|UNION)\b/i;
function sqlParts(text) {   // SQL-запрос в строке: до «;», до конца строки или до « — »; следующие строки с WHERE/JOIN… — продолжение
  const out = []; let last = 0, m;
  const rx = new RegExp(SQL_START.source, 'gi');
  while ((m = rx.exec(text))) {
    let e = m.index;
    for (;;) {
      let nl = text.indexOf('\n', e); if (nl < 0) nl = text.length;
      let line = text.slice(e, nl);
      const semi = line.indexOf(';'), dash = line.search(/\s[—–]\s/);
      const cut = [semi >= 0 ? semi + 1 : -1, dash].filter((x) => x >= 0).sort((a, b) => a - b)[0];
      if (cut !== undefined) { e += cut; break; }
      e = nl;
      if (!SQL_MORE.test(text.slice(nl + 1, text.indexOf('\n', nl + 1) < 0 ? text.length : text.indexOf('\n', nl + 1)))) break;
      e = nl + 1;
    }
    const sql = text.slice(m.index, e).trim();
    if (sql.length < 12) continue;
    if (m.index > last) out.push({ code: false, text: text.slice(last, m.index) });
    out.push({ code: true, text: sql });
    last = rx.lastIndex = e;
  }
  if (last < text.length) out.push({ code: false, text: text.slice(last) });
  return out;
}
function jsonParts(text, pretty) {
  const out = []; let last = 0;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch !== '{' && !(ch === '[' && /^\[\s*[{"]/.test(text.slice(i, i + 6)))) continue;
    const e = jsonEnd(text, i), code = e > 0 ? jsonCode(text.slice(i, e), pretty) : null;
    if (code == null) continue;
    if (i > last) out.push({ code: false, text: text.slice(last, i) });
    out.push({ code: true, text: code });
    i = e - 1; last = e;
  }
  if (last < text.length) out.push({ code: false, text: text.slice(last) });
  return out;
}
const codeParts = (s, pretty = false) => splitFences(s).flatMap((p) => (p.code ? [p] : jsonParts(p.text, pretty))).flatMap((p) => (p.code ? [p] : sqlParts(p.text)));
function deHtml(v) {
  let t = String(v ?? '');
  if (!HTML_RX.test(t) && !/&(nbsp|lt|gt|amp|quot|#39);/.test(t)) return t;
  const kept = [];   // блоки кода не трогаем: в них бывает XML и другие угловые скобки
  const keep = (code) => `\n\u0000${kept.push(code) - 1}\u0000\n`;
  const un = (s) => s.replace(/&nbsp;/g, ' ').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
  const strip = (s) => s.replace(FENCE_RX, keep)
    .replace(/<pre\b[^>]*>([\s\S]*?)<\/pre>/gi, (m, code) => keep('```\n' + un(code.replace(/<br\s*\/?>/gi, '\n').replace(/<\/?(code|span)\b[^>]*>/gi, '')).trim() + '\n```'))   // <pre> из ТМС → блок кода
    .replace(/<br\s*\/?>/gi, '\n').replace(/<li\b[^>]*>/gi, '\n- ').replace(/<\/(p|div|h[1-6]|tr|blockquote|pre)>/gi, '\n')
    .replace(/<\/?(p|div|span|ul|ol|li|b|i|u|s|strong|em|code|pre|h[1-6]|table|tr|td|th|tbody|thead|a|font|blockquote)\b[^>]*>/gi, '');
  t = un(strip(t));
  if (HTML_RX.test(t)) t = strip(t); // теги, которые были записаны экранированными (&lt;p&gt;)
  t = t.replace(/[ \t]+\n/g, '\n').replace(/\n{3,}/g, '\n\n').trim();
  return t.replace(/\u0000(\d+)\u0000/g, (m, i) => kept[i]);
}
/* Предусловия и постусловия: каждый пункт — отдельная строка без HTML и без буквальных «\n» (модель иногда пишет их как есть) */
const PRE_KEY_RX = /precond|предусл|postcond|постусл/i;
const cleanText = (s) => splitFences(deHtml(s)).map((p) => (p.code ? p.raw : p.text.replace(/\\r\\n|\\n|\\r/g, '\n'))).join('');
const cleanLine = (s) => s.replace(/^\s*-\s+/, '').trim();
function preItems(s) {   // текст → пункты, по строке на пункт; блок кода входит в пункт перед ним
  const out = [];
  for (const p of splitFences(cleanText(s))) {
    if (!p.code) out.push(...p.text.split('\n').map(cleanLine).filter(Boolean));
    else if (out.length) out[out.length - 1] += '\n' + p.raw;
    else out.push(p.raw);
  }
  return out;
}
const mergeCode = (items) => items.reduce((a, x) => { if (typeof x === 'string' && x.startsWith('```') && typeof a[a.length - 1] === 'string') a[a.length - 1] += '\n' + x; else a.push(x); return a; }, []);
function cleanPre(v) {
  if (typeof v === 'string') return preItems(v).join('\n');
  if (Array.isArray(v)) return mergeCode(v.flatMap((x) => (typeof x === 'string' ? preItems(x) : [cleanCase(x)])));
  return v;
}
/* Текст кейса без HTML и экранирования; ключи предусловий и постусловий приводятся к списку строк */
function cleanCase(v, key = '') {
  if (Array.isArray(v)) return PRE_KEY_RX.test(key) ? cleanPre(v) : v.map((x) => cleanCase(x, key));
  if (v && typeof v === 'object') return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, cleanCase(x, k)]));
  if (typeof v === 'string') return PRE_KEY_RX.test(key) ? cleanPre(v) : deHtml(v);
  return v;
}
const plainDeep = (v) => (typeof v === 'string' ? deHtml(v) : Array.isArray(v) ? v.map(plainDeep) : v && typeof v === 'object' ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, plainDeep(x)])) : v);
/* старые сохранённые правила оформления пишут приоритет как High/Medium/Low: в запросах — только P1_LOW…P4_CRITICAL */
const prioInText = (s) => String(s || '').replace(/(priority\s*:\s*)(High|Medium|Low|Critical)\b/gi, (m, pre, v) => pre + normPrio(v))
  .replace(/\b(High|Medium|Low|Critical)(?=\s*—)/g, (m) => normPrio(m));
function templateBlock(type) {
  const t = S.cfg.tpl[type], info = tplInfo(type);
  const more = info.examples.slice(1, 3).map(plainDeep);
  return `${t.rules ? `Правила оформления:\n${prioInText(t.rules)}\n\n` : ''}Образец тест-кейса. Повторяй точно его поля, вложенность, типы значений и стиль; значения пиши свои:
${fence}json
${JSON.stringify(plainDeep(info.structure))}
${fence}
Пиши значения обычным текстом, без HTML-разметки (<p>, <br>, <ul> и т. п.), даже если в образце она была: разметку под ТМС добавит выгрузка. Не пиши буквальные экранированные переносы строк (обратная косая черта и n) ни в одном поле. Предусловия и постусловия — отдельные элементы массива строк, без переносов внутри элемента; списки в других полях — строками «- …». Исключение — тело запроса и тело ответа API, сообщение Kafka и SQL-запрос: в предусловиях, шагах и ожидаемых результатах каждое такое значение оформляй блоком кода (даже если в образце оно записано в одну строку, например «Тело ответа: {…}»), внутри того же значения: сначала строка с пояснением, затем строка из трёх обратных кавычек (после них можно указать язык: json, sql, xml), само значение и закрывающая строка из трёх обратных кавычек. Переносы внутри блока допустимы и в предусловиях. HTML-теги (<pre> и др.) для этого не пиши, даже если правила команды описывают такую разметку: нужную разметку добавит выгрузка.${more.length ? `\nЕщё образцы того же шаблона:\n${more.map((e) => fence + 'json\n' + JSON.stringify(e) + '\n' + fence).join('\n')}` : ''}`;
}
function promptGenerate(run, b, mode = {}) {
  const info = tplInfo(b.type);
  const focus = b.items.map((it) => `${it.title} ${it.checks.join(' ')} ${it.requirementIds.map((id) => reqText(run.reqById[id])).join(' ')}`).join(' ');
  const ex = relevantExisting(run, 'cases', b.type, 25, focus);
  const rules = rulesText();
  return renderPrompt("promptGenerate", { "TITLE_TAG_RULE": TITLE_TAG_RULE, "KAFKA_RULE": KAFKA_RULE, "PRIORITY_RULE": PRIORITY_RULE, "PRECONDITIONS_RULE": PRECONDITIONS_RULE, "API_CALL_RULE": API_CALL_RULE, "SERVICE_STEPS_RULE": SERVICE_STEPS_RULE, "e1": TL[b.type], "e2": TL[b.type], "e3": templateBlock(b.type), "e4": rules ? `\n## Правила команды\n${rules}\n` : '', "e5": clarBlock(run), "e6": qaCtxBlock(ctxOf(run), b.type), "e7": SCOPE_RULE.replace(/\n/g, '\n  '), "REQ_REF_RULE": REQ_REF_RULE, "e9": info.idField ? `\n- Поле "${info.idField}" оставь пустой строкой — идентификаторы проставит система.` : '', "SUITES_RULE": SUITES_RULE, "CACHE_MARK": CACHE_MARK, "e12": b.items.map((it) => `### ${it.id}. ${it.title}
Проверки — каждая становится отдельным тест-кейсом:
${it.checks.map((c, k) => `${k + 1}. ${c}`).join('\n')}${it.checks.some(clIdOf) ? '\nЭто пункты чек-листа. Кейс пиши по названию и ожидаемому результату пункта, приоритет кейса — как у пункта. В объекте ответа рядом с planItem укажи checklistId — номер пункта (CL-…), по которому написан кейс.' : ''}
Требования:
${it.requirementIds.map((id) => reqLine(run.reqById[id])).join('\n')}`).join('\n\n'), "e13": knowBlocks(run, 'batch', focus), "e14": existingBlock(ex, 'cases', 'Не повторяй эти кейсы. Называй экраны, кнопки, роли и сущности так же, как в них и в знаниях о продукте.'), "e15": mode.fullDocs !== false ? docsBlock(run, focus, mode) : '', "e16": mode.tools ? `\n## Инструменты
Если для конкретики не хватает деталей (форматы полей, лимиты, коды и тексты ошибок, названия элементов), найди их в исходных документах инструментами search_documents и read_document.${kbToolsHint(run)} Не больше 4 обращений.\n` : '' });
}
function promptRefine(run, c, comment) {
  const info = tplInfo(c.type);
  const reqs = c.requirementIds.map((id) => reqLine(run.reqById?.[id])).filter(Boolean).join('\n');
  return renderPrompt("promptRefine", { "TITLE_TAG_RULE": TITLE_TAG_RULE, "KAFKA_RULE": KAFKA_RULE, "PRIORITY_RULE": PRIORITY_RULE, "PRECONDITIONS_RULE": PRECONDITIONS_RULE, "API_CALL_RULE": API_CALL_RULE, "SERVICE_STEPS_RULE": SERVICE_STEPS_RULE, "e1": TL[c.type], "e2": templateBlock(c.type), "e3": reqs ? `\n## Требования, которые покрывает кейс\n${reqs}\n` : '', "e4": clarBlock(run), "e5": qaCtxBlock(ctxOf(run), c.type), "e6": knowBlocks(run, 'batch', `${pickTitleText(c.testCase)} ${comment} ${c.requirementIds.map((id) => reqText(run.reqById?.[id])).join(' ')}`), "fence": fence, "e8": JSON.stringify(c.testCase), "comment": comment, "REQ_REF_RULE": REQ_REF_RULE, "e12": info.ok && info.idField ? ` Значение поля "${info.idField}" не меняй.` : '' });
}
function promptImpact(run, qs) {
  const cases = run.cases.map((c) => `${c.dispId} [${c.type}] ${c.requirementIds.join(',')}: ${pickTitleText(c.testCase)}`).join('\n');
  const cl = checklistItems(run);
  return renderPrompt("promptImpact", { "e1": qs.map((q) => `${q.id}. ${q.text}\nОтвет: ${q.answer.trim()}`).join('\n\n'), "e2": clarBlock({ questions: run.questions.filter((q) => !qs.includes(q)) }), "e3": qaCtxBlock(ctxOf(run)), "e4": run.requirements.filter((r) => r.inScope).map(reqCompact).join('\n'), "e5": cases || 'нет', "e6": cl.length ? `\n## Пункты чек-листа\n${cl.slice(0, 300).map((i) => `${i.id} [${i.type}] ${i.requirementIds.join(',')}: ${i.check}`).join('\n')}\n` : '', "e7": typesListText(run.settings.types || TYPES) });
}
function promptReviseBatch(run, type, ups) {
  const info = tplInfo(type);
  return renderPrompt("promptReviseBatch", { "TITLE_TAG_RULE": TITLE_TAG_RULE, "KAFKA_RULE": KAFKA_RULE, "PRIORITY_RULE": PRIORITY_RULE, "PRECONDITIONS_RULE": PRECONDITIONS_RULE, "API_CALL_RULE": API_CALL_RULE, "SERVICE_STEPS_RULE": SERVICE_STEPS_RULE, "e1": TL[type], "e2": templateBlock(type), "e3": clarBlock(run), "e4": qaCtxBlock(ctxOf(run), type), "e5": knowBlocks(run, 'batch', ups.map((u) => `${pickTitleText(u.c.testCase)} ${u.instruction}`).join(' ')), "e6": ups.map((u) => `### ${u.c.dispId}
Инструкция: ${u.instruction}
Требования:
${u.c.requirementIds.map((id) => reqLine(run.reqById[id])).join('\n')}
${fence}json
${JSON.stringify(u.c.testCase)}
${fence}`).join('\n\n'), "REQ_REF_RULE": REQ_REF_RULE, "e8": info.ok && info.idField ? ` Значение поля "${info.idField}" не меняй.` : '', "SUITES_RULE": SUITES_RULE, "e10": ups[0].c.dispId });
}
/* ---------- актуализация: сверка и переписывание кейсов из файла ---------- */
const srcBlock = (sc) => `### #${sc.index}${sc.srcId ? ` (ID в файле: ${sc.srcId})` : ''}${sc.typeHint ? ` · подсказка вида: ${sc.typeHint}` : ''}\n${fence}json\n${JSON.stringify(sc.raw).slice(0, 6000)}\n${fence}`;
function promptMap(run, batch) {
  const rules = rulesText();
  const focus = batch.map((x) => `${x.title} ${JSON.stringify(x.raw).slice(0, 600)}`).join(' ');
  return renderPrompt("promptMap", { "e1": rules ? `\nПравила команды: ${rules}\n` : '', "e2": clarBlock(run), "e3": qaCtxBlock(ctxOf(run)), "e4": run.requirements.map(reqCompact).join('\n'), "CACHE_MARK": CACHE_MARK, "e6": knowBlocks(run, 'batch', focus), "e7": run.source?.name || 'тесты', "e8": batch.map(srcBlock).join('\n\n') });
}
function promptActualize(run, type, batch) {
  const info = tplInfo(type);
  const rules = rulesText();
  const focus = batch.map((x) => `${x.title} ${x.instruction || ''} ${x.reqIds.map((id) => reqText(run.reqById[id])).join(' ')}`).join(' ');
  return renderPrompt("promptActualize", { "TITLE_TAG_RULE": TITLE_TAG_RULE, "KAFKA_RULE": KAFKA_RULE, "PRIORITY_RULE": PRIORITY_RULE, "PRECONDITIONS_RULE": PRECONDITIONS_RULE, "API_CALL_RULE": API_CALL_RULE, "SERVICE_STEPS_RULE": SERVICE_STEPS_RULE, "e1": TL[type], "e2": TL[type], "e3": templateBlock(type), "e4": clarBlock(run), "e5": qaCtxBlock(ctxOf(run), type), "e6": rules ? `\n## Правила команды\n${rules}\n` : '', "REQ_REF_RULE": REQ_REF_RULE, "e8": info.ok && info.idField ? `\n- Поле "${info.idField}" оставь пустой строкой — идентификатор проставит система.` : '', "SUITES_RULE": SUITES_RULE, "CACHE_MARK": CACHE_MARK, "e11": knowBlocks(run, 'batch', focus), "e12": batch.map((sc) => `${srcBlock(sc)}
Статус: ${sc.status === 'changed' ? '"changed" — исправить' : sc.status === 'obsolete' ? '"obsolete" — устарел' : '"same" — без изменений по сути'}${sc.status === 'changed' && sc.instruction ? `\nЧто исправить: ${sc.instruction}` : ''}
Требования:
${sc.reqIds.map((id) => reqLine(run.reqById[id])).filter(Boolean).join('\n') || 'не сопоставлены'}`).join('\n\n') });
}
function casePayload(c) {
  const o = { id: c.dispId, type: c.type, suites: c.suites || [], requirementIds: c.requirementIds, testCase: c.testCase };
  if (c.status) Object.assign(o, { status: c.status, changes: c.changes || [], reason: c.note || '', sourceId: c.sourceId || null });
  return o;
}
function promptExportSpec(fmt, run) {
  return renderPrompt("promptExportSpec", { "fmt": fmt, "fence": fence, "e3": JSON.stringify(run.cases.slice(0, 2).map(casePayload)), "e5": run.mode === 'update' ? `
Это результат актуализации: у каждого кейса есть status ("same" — без изменений, "changed" — изменён, "new" — новый, "obsolete" — устарел), reason — причина статуса, changes — список изменений «было → стало», sourceId — ID кейса в исходном файле. Если пользователь не описал, что делать со статусами, добавь их в файл отдельным полем или колонкой «Статус актуализации» с русскими названиями и не пропускай устаревшие кейсы.` : '' });
}
function promptExportItems(spec, fmt, cases) {
  const tab = spec.fileType === 'csv' || spec.fileType === 'xlsx';
  const shape = spec.fileType === 'json' ? '{"items":[{"caseId":"API-001","value":{ ...элемент файла для кейса... }}]}'
    : tab ? `{"items":[{"caseId":"API-001","rows":[["значение 1","значение 2"]]}]} — одна или несколько строк на кейс, в каждой строке ровно ${spec.columns.length} значений в порядке колонок, значения — строки`
      : '{"items":[{"caseId":"API-001","text":"фрагмент файла для кейса"}]}';
  return renderPrompt("promptExportItems", { "spec_fileType": spec.fileType, "fmt": fmt, "spec_itemRules": spec.itemRules, "e4": tab ? `\nКолонки: ${spec.columns.join(' | ')}` : '', "fence": fence, "e6": JSON.stringify(cases.map(casePayload), null, 2), "shape": shape });
}

/* ================= Claude calls ================= */
const FATAL = new Set(['not_granted', 'sampling_disabled', 'not_declared', 'capability_disabled', 'capability_removed', 'session_expired', 'rate_limited', 'auth', 'network', 'provider_unavailable']);
/* трассировка ошибки: описание дефекта и необязательный стек трейса → шаги по слоям (раздел «Трассировка ошибки») */
function promptTrace(desc, stack) {
  return renderPrompt('promptTrace', {
    e1: desc,
    e2: stack ? `\n${fence}\n${stack}\n${fence}\n` : 'не приложен',
    e3: knowBlocks(null, 'single', `${desc} ${stack}`) || 'Сведений о продукте нет: опирайся только на описание и стек трейса, остальное помечай как «нет данных».',
    e4: qaCtxBlock(ctxOf(null)),
  });
}
function normTrace(res) {
  const o = res && typeof res === 'object' && !Array.isArray(res) ? res : {};
  const str = (v) => String(v ?? '').trim();
  const obj = (v) => (v && typeof v === 'object' && !Array.isArray(v) ? v : {});
  const steps = arrOf(o.steps).map((s, i) => ({ n: Number(obj(s).n) || i + 1, title: str(obj(s).title), layer: str(obj(s).layer), details: arrStr(obj(s).details) })).filter((s) => s.title);
  const f = obj(o.failure), rs = obj(o.response);
  return { steps, failure: { error: str(f.error), location: str(f.location), cause: str(f.cause) }, response: { status: str(rs.status), body: str(rs.body) }, result: str(o.result), summary: str(o.summary), questions: arrStr(o.questions) };
}
async function runTrace() {
  const T = S.trace;
  if (T.busy || !T.description.trim()) return;
  if (!aiReady(S.settings.genAI)) return toast(aiProblem(S.settings.genAI), 'err');
  T.busy = true; T.error = ''; T.result = null; renderTab();
  try {
    const res = await ask(promptTrace(T.description.trim(), T.stack.trim()), { step: 'trace' });
    T.result = normTrace(res);
    if (!T.result.steps.length) throw { message: 'Модель не вернула шаги трассировки. Уточните описание или приложите стек трейс.' };
  } catch (e) {
    T.result = null;
    if (e?.code !== 'cancelled') T.error = errText(e);
  } finally {
    T.busy = false;
    if (S.settings.mode === 'trace') renderTab();
  }
}
/* ================= баг-репорт по трассировке: шаблон команды, связанные кейсы, поиск дублей ================= */
const SEVERITIES = ['blocker', 'critical', 'major', 'minor', 'trivial'];
const DSEV_RU = { blocker: 'Блокирующий', critical: 'Критичный', major: 'Значительный', minor: 'Незначительный', trivial: 'Тривиальный' };
const DPRIOS = ['high', 'medium', 'low'];
const DPRIO_RU = { high: 'Высокий', medium: 'Средний', low: 'Низкий' };
const DEFECT_MAX = 300;   // дефектов в индексе продукта
const defIdxPath = (pid) => `${prodPath(pid)}/meta/defects`;
const defPath = (pid, id) => `${prodPath(pid)}/defects/${id}`;
function traceText(r) {
  if (!r) return 'не выполнена';
  const out = r.steps.map((s) => `${s.n}. ${s.title}${s.layer ? ` [${s.layer}]` : ''}${s.details.length ? '\n' + s.details.map((d) => `   - ${d}`).join('\n') : ''}`);
  if (r.failure.error || r.failure.location || r.failure.cause) out.push(`Место сбоя: ${[r.failure.error, r.failure.location, r.failure.cause].filter(Boolean).join(' · ')}`);
  if (r.response.status || r.response.body) out.push(`Ответ сервера: ${[r.response.status, r.response.body].filter(Boolean).join(' · ')}`);
  if (r.result) out.push(`Результат для пользователя: ${r.result}`);
  if (r.summary) out.push(`Резюме: ${r.summary}`);
  return out.join('\n');
}
/* кандидаты для модели: кейсы и дефекты продукта, ближайшие к описанию по словам */
function nearest(items, text, of, n) {
  const q = [...new Set(helpTokens(text))];
  if (!q.length) return [];
  return items.map((x) => ({ x, s: helpScore(q, of(x)) })).filter((o) => o.s >= Math.min(2, q.length)).sort((a, b) => b.s - a.s).slice(0, n).map((o) => o.x);
}
function defectFocus(T) {
  const r = T.result;
  return `${T.description} ${r ? `${r.failure.error} ${r.failure.location} ${r.failure.cause} ${r.result} ${r.steps.map((s) => s.title + ' ' + s.details.join(' ')).join(' ')}` : ''}`;
}
function defectCandidates(T) {
  const focus = defectFocus(T);
  const cases = S.prodIndex.pid === S.productId ? nearest(S.prodIndex.cases, focus, (x) => x.n, 20) : [];
  const dups = S.defects.pid === S.productId ? nearest(S.defects.items, focus, (x) => `${x.title} ${x.actual} ${x.location}`, 15) : [];
  return { cases, dups };
}
function promptDefect(T, cand) {
  const focus = defectFocus(T);
  return renderPrompt('promptDefect', {
    e1: T.description.trim(),
    e2: T.stack.trim() ? `\n${fence}\n${T.stack.trim().slice(0, 12000)}\n${fence}\n` : 'не приложен',
    e3: traceText(T.result),
    e4: S.cfg.defectTpl.trim() || 'Не задан — используй стандартные поля из формата ответа, "fields" оставь пустым.',
    e5: knowBlocks(null, 'single', focus) || 'Сведений о продукте нет.',
    e6: qaCtxBlock(ctxOf(null)),
    e7: cand.cases.length ? cand.cases.map((x) => `- ${x.i}: ${x.n}`).join('\n') : 'нет',
    e8: cand.dups.length ? cand.dups.map((x) => `- ${x.id}: ${x.title}${x.actual ? ` | фактически: ${x.actual}` : ''}${x.location ? ` | место сбоя: ${x.location}` : ''}`).join('\n') : 'нет',
  });
}
function normDefect(res, cand) {
  const o = res && typeof res === 'object' && !Array.isArray(res) ? res : {};
  const str = (v, n = 4000) => String(v ?? '').trim().slice(0, n);
  const lo = (v) => str(v, 20).toLowerCase();
  const caseIds = new Set(cand.cases.map((x) => x.i)), dupIds = new Set(cand.dups.map((x) => x.id));
  const steps = arrStr(o.steps).map((x) => x.replace(/^\s*\d+[.)]\s*/, '').trim()).filter(Boolean);
  return {
    title: str(o.title, 200), severity: SEVERITIES.includes(lo(o.severity)) ? lo(o.severity) : 'major', priority: DPRIOS.includes(lo(o.priority)) ? lo(o.priority) : 'medium',
    component: str(o.component, 200), environment: str(o.environment, 400), preconditions: arrStr(o.preconditions).filter(Boolean), steps,
    expected: str(o.expected), actual: str(o.actual), analysis: str(o.analysis),
    fields: arrOf(o.fields).map((f) => ({ name: str(f?.name, 120), value: str(f?.value) })).filter((f) => f.name),
    relatedCases: [...new Set(arrStr(o.relatedCases).map((x) => x.trim()))].filter((x) => caseIds.has(x)).slice(0, 5),
    duplicates: arrOf(o.duplicates).map((d) => ({ id: str(d?.id, 40), reason: str(d?.reason, 400) })).filter((d) => dupIds.has(d.id)),
  };
}
async function runDefect() {
  const T = S.trace;
  if (T.defectBusy || !T.result) return;
  if (!aiReady(S.settings.genAI)) return toast(aiProblem(S.settings.genAI), 'err');
  T.defectBusy = true; T.defectError = ''; renderTab();
  try {
    if (S.productId && S.caps.db && S.defects.pid !== S.productId) await loadDefects(S.productId);
    const cand = defectCandidates(T);
    const res = await ask(promptDefect(T, cand), { step: 'defect' });
    const d = normDefect(res, cand);
    if (!d.title || !d.steps.length) throw { message: 'Модель не вернула заголовок и шаги воспроизведения. Уточните описание дефекта и повторите.' };
    T.defect = { id: '', ...d, stack: T.stack.trim(), createdAt: 0 };
    T.defectPid = S.productId; T.defectSavedAt = 0;
  } catch (e) {
    if (e?.code !== 'cancelled') T.defectError = errText(e);
  } finally {
    T.defectBusy = false;
    if (S.settings.mode === 'trace') renderTab();
  }
}
/* текст для трекера: plain — для полей Сферы и Jira без разметки, md — Markdown */
function defectText(d, md) {
  const h = (t) => (md ? `**${t}**` : `${t}:`);
  const list = (a, num) => a.map((x, i) => `${num ? `${i + 1}.` : '-'} ${x}`).join('\n');
  const out = [md ? `## ${d.title}` : d.title, '',
    `${h('Серьёзность')} ${DSEV_RU[d.severity] || d.severity} · ${h('Приоритет')} ${DPRIO_RU[d.priority] || d.priority}`];
  if (d.component) out.push(`${h('Компонент')} ${d.component}`);
  if (d.environment) out.push(`${h('Окружение')} ${d.environment}`);
  if (d.preconditions.length) out.push('', h('Предусловия'), list(d.preconditions));
  out.push('', h('Шаги воспроизведения'), list(d.steps, true), '', `${h('Ожидаемый результат')} ${d.expected}`, `${h('Фактический результат')} ${d.actual}`);
  for (const f of d.fields) out.push(`${h(f.name)} ${f.value}`);
  if (d.analysis) out.push('', `${h('Анализ')} ${d.analysis}`);
  if (d.relatedCases.length) out.push(`${h('Связанные тест-кейсы')} ${d.relatedCases.join(', ')}`);
  if (d.stack) out.push('', h('Стек трейс'), md ? `${fence}\n${d.stack}\n${fence}` : d.stack);
  return out.join('\n');
}
async function loadDefects(pid) {
  if (!pid || !S.caps.db) { S.defects = { pid, items: [], loaded: true, open: null }; return; }
  let items = [];
  try { items = arrOf((await S.caps.db.doc(defIdxPath(pid)).get()).data()?.items); } catch { /* дефектов ещё нет */ }
  if (S.productId === pid) { S.defects = { pid, items, loaded: true, open: null }; if (S.settings.mode === 'trace' && !isTyping($('#tab-body'))) renderTab(); }
}
const defIdxItem = (d) => ({ id: d.id, title: d.title.slice(0, 200), severity: d.severity, actual: d.actual.replace(/\s+/g, ' ').slice(0, 200), location: (S.trace.result?.failure.location || d.component || '').slice(0, 140), createdAt: d.createdAt, by: d.by || '' });
let defChain = Promise.resolve();
async function saveDefect() {
  const T = S.trace, d = T.defect, pid = S.productId;
  if (!d || !pid || !S.caps.db) return;
  if (!d.title.trim() || !d.steps.some((x) => x.trim())) return toast('Заполните заголовок и шаги воспроизведения.', 'err');
  d.steps = d.steps.map((x) => x.trim()).filter(Boolean); d.preconditions = d.preconditions.map((x) => x.trim()).filter(Boolean);
  const job = defChain.then(async () => {
    const ref = S.caps.db.doc(defIdxPath(pid));
    const cur = arrOf((await ref.get()).data()?.items);
    if (!d.id) {
      const n = cur.reduce((m, x) => Math.max(m, Number((/(\d+)$/.exec(String(x.id)) || [])[1] || 0)), 0) + 1;
      d.id = `D-${pad(n, 3)}`; d.createdAt = Date.now(); d.by = S.caps.uid || '';
    }
    d.updatedAt = Date.now();
    await S.caps.db.doc(defPath(pid, d.id)).set({ ...d, trace: T.result || null, description: T.description });
    const next = [...cur.filter((x) => x.id !== d.id), defIdxItem(d)].slice(-DEFECT_MAX);
    await ref.set({ items: next, updatedAt: Date.now() });
    if (S.productId === pid) S.defects = { ...S.defects, pid, items: next, loaded: true };
  });
  defChain = job.catch(() => {});
  try { await job; T.defectSavedAt = Date.now(); toast(`Дефект ${d.id} сохранён в продукт`); }
  catch { toast('Не удалось сохранить дефект — нужны права на изменение продукта.', 'err'); }
  if (S.settings.mode === 'trace') renderTab();
}
async function openDefect(id) {
  const pid = S.productId;
  try {
    const data = (await S.caps.db.doc(defPath(pid, id)).get()).data();
    if (!data) return toast('Дефект не найден — возможно, его удалили.', 'err');
    const T = S.trace;
    T.description = String(data.description || ''); T.stack = String(data.stack || '');
    T.result = data.trace ? normTrace(data.trace) : null; T.error = '';
    T.defect = { ...normDefect(data, { cases: (data.relatedCases || []).map((i) => ({ i })), dups: (data.duplicates || []).map((x) => ({ id: x.id })) }), id: data.id, stack: String(data.stack || ''), createdAt: data.createdAt || 0, by: data.by || '' };
    T.defectPid = pid; T.defectSavedAt = data.updatedAt || data.createdAt || 0; T.defectError = '';
    renderTab();
    document.querySelector('#defect-card')?.scrollIntoView({ block: 'start' });
  } catch { toast('Не удалось открыть дефект.', 'err'); }
}
async function deleteDefect(id) {
  const pid = S.productId;
  const job = defChain.then(async () => {
    const ref = S.caps.db.doc(defIdxPath(pid));
    const next = arrOf((await ref.get()).data()?.items).filter((x) => x.id !== id);
    await ref.set({ items: next, updatedAt: Date.now() });
    await S.caps.db.doc(defPath(pid, id)).delete();
    if (S.productId === pid) S.defects = { ...S.defects, items: next };
    if (S.trace.defect?.id === id) S.trace.defect.id = '';
  });
  defChain = job.catch(() => {});
  try { await job; toast(`Дефект ${id} удалён`); } catch { toast('Не удалось удалить дефект.', 'err'); }
  if (S.settings.mode === 'trace') renderTab();
}
function errText(e) {
  const map = {
    not_granted: 'Доступ к Claude для этой страницы не разрешён. Перезагрузите страницу и разрешите доступ в запросе.',
    sampling_disabled: 'Claude недоступен для этого аккаунта или организации.',
    not_declared: 'Приложение не может обращаться к Claude в этой версии.',
    capability_disabled: 'Обращение к Claude недоступно в этом окне. Откройте приложение на claude.ai.',
    capability_removed: 'Обращение к Claude недоступно в этом окне. Обновите приложение Claude или откройте страницу в браузере.',
    session_expired: 'Сессия истекла — войдите в claude.ai заново и повторите.',
    rate_limited: 'Слишком много запросов или исчерпан лимит использования. Подождите и запустите снова.',
    prompt_too_large: 'Слишком большой объём текста для одного запроса. Уменьшите документы или разделите их.',
    invalid_json: 'Модель ответила не в формате JSON.',
    refused: 'Модель отказалась обрабатывать этот фрагмент.',
    empty_completion: 'Модель вернула пустой ответ.',
    upstream_error: 'Сбой связи с сервисом.',
    tools_unavailable: 'Поиск по документам недоступен в этом окне.',
    invalid_request: 'Некорректный запрос к модели.',
  };
  if (e?.code) return e.message && !map[e.code] ? e.message : map[e.code] || e.message || 'Сбой связи с сервисом.';
  return e?.message || String(e);
}

/* ---------- выбор ИИ: Claude на claude.ai или подключённые модели ---------- */
const CLAUDE_TIERS = { quick: 'быстрая', default: 'стандартная', complex: 'максимальная' };
function parseAI(v) {
  if (typeof v !== 'string') return null;
  if (v.startsWith('claude:')) { const t = v.slice(7); return { kind: 'claude', tier: CLAUDE_TIERS[t] ? t : 'default' }; }
  if (v.startsWith('conn:')) { const conn = S.conns.find((c) => c.id === v.slice(5)); return conn ? { kind: 'conn', conn } : null; }
  return null;
}
const aiValue = (role) => (role === 'review' && S.settings.reviewAI !== 'same' ? S.settings.reviewAI : S.settings.genAI);
function aiLabel(v) {
  const t = parseAI(v);
  if (!t) return 'не выбран';
  return t.kind === 'claude' ? `Claude · ${CLAUDE_TIERS[t.tier]}` : (t.conn.name || t.conn.model || 'Подключение');
}
function aiProblem(v) {
  const t = parseAI(v);
  if (!t) return 'ИИ не выбран — выберите подключение: шестерёнка → Модель.';
  if (t.kind === 'claude') {
    if (S.caps.sample) return '';
    if (!inClaude) return 'В автономной версии вход через аккаунт Claude недоступен — укажите ключ API Claude, ChatGPT или Иннокода: шестерёнка → Модель.';
    return S.caps.ready ? 'Claude недоступен в этом окне: откройте приложение на claude.ai под своим аккаунтом.' : 'Подключение к Claude ещё проверяется…';
  }
  if (inClaude) return `«${aiAbbrName(t.conn)}» работает только в автономной версии: на claude.ai страница изолирована от интернета.`;
  const pv = provOfConn(t.conn.id);
  if (pv && !t.conn.apiKey) return `Укажите ключ API для подключения «${PROVIDERS[pv].title}»: шестерёнка → Модель.`;
  if (!t.conn.baseUrl || !t.conn.model) return `В подключении «${aiAbbrName(t.conn)}» не заполнены адрес или модель.`;
  return '';
}
const aiAbbrName = (c) => c.name || c.model || 'Подключение';
// подпись модели с учётом выбора по этапам
function aiLabelStage(v, stage) {
  const t = parseAI(v), f = stageTier(stage);
  if (t?.kind === 'claude' && f) return `Claude · ${CLAUDE_TIERS[f]}`;
  if (t?.kind === 'conn' && f) { const m = stageModel(t.conn, f); if (m) return `${aiAbbrName(t.conn)} · ${m}`; }
  return aiLabel(v);
}
const aiReady = (v) => !aiProblem(v);
function toolsAvailable(v) { const t = parseAI(v); return !!t && (t.kind === 'claude' ? S.caps.tools : !!t.conn.tools); }

/* ---------- расход токенов: оценка по объёму текста, точные цифры — если их вернул API ---------- */
const CACHE_MARK = '\n\u2063<<VAR>>\u2063\n';   // граница: до неё — общая для пакетов часть запроса (кэшируется провайдером)
const JSON_TAIL = '\n\nОтвет — один компактный JSON без отступов и пояснений.';
function estTok(s) { const t = String(s || ''); const cyr = (t.match(/[А-Яа-яЁё]/g) || []).length; return Math.round(cyr / 2.6 + (t.length - cyr) / 3.8); }
const STEP_RU = { gen_api: 'генерация API', gen_ui: 'генерация UI', gen_e2e: 'генерация E2E', cover: 'покрытие требования', trace: 'трассировка', defect: 'баг-репорт', kb: 'разделы базы знаний', help: 'база знаний', analyze: 'анализ', checklist: 'чек-лист', plan: 'план', generate: 'генерация', coverage: 'покрытие', map: 'сверка', actualize: 'актуализация', answers: 'ответы', review: 'ревью', fix: 'исправления', knowledge: 'знания', export: 'экспорт', refine: 'доработка', lesson: 'правила', other: 'прочее' };
// что берёт агент в запрос этапа: по заголовкам промпта; размер — наибольший запрос этапа. Текст последнего запроса — только в памяти текущего окна
const PROMPT_PARTS = [['Правила команды:', 'правила команды'], ['## Правила из замечаний команды', 'замечания команды'], ['## Шаблон', 'шаблон кейса'], ['## Знания о продукте', 'паспорт продукта'], ['## Дополнительный контекст от QA', 'контекст QA'], ['## Исходные документы', 'документы'], ['## Фрагменты исходных документов', 'фрагменты документов'], ['## База знаний продукта', 'база знаний'], ['## Уже есть в продукте', 'уже есть в продукте'], ['## Уточнения аналитика', 'ответы аналитика']];
function notePrompt(step, full) {
  const run = S.run;
  if (!run || !step || step === 'help' || step === 'kb' || run.fromHistory === 'readonly' || run.fromHistory === 'follow') return;
  const sections = [...PROMPT_PARTS.filter(([h]) => full.includes(h)).map(([, n]) => n), ...lastRules];
  lastRules = [];   // правила относятся только к одному запросу
  run.usage = run.usage || { in: 0, out: 0, cached: 0, calls: 0, by: {} };
  const b = run.usage.by[step] || (run.usage.by[step] = { in: 0, out: 0, calls: 0 });
  b.sections = [...new Set([...(b.sections || []), ...sections])];
  b.chars = Math.max(b.chars || 0, full.length);
  run.stepPrompt = { ...(run.stepPrompt || {}), [step]: full };
}
function meterAdd(step, inT, outT, cached = 0) {
  const run = S.run;
  const add = (u) => { u.in += inT; u.out += outT; u.cached += cached; u.calls++; const b = u.by[step] || (u.by[step] = { in: 0, out: 0, calls: 0 }); b.in += inT; b.out += outT; b.calls++; };
  S.usage = S.usage || { in: 0, out: 0, cached: 0, calls: 0, by: {} }; add(S.usage);
  if (step !== 'help' && step !== 'kb' && run && run.fromHistory !== 'readonly' && run.fromHistory !== 'follow') { run.usage = run.usage || { in: 0, out: 0, cached: 0, calls: 0, by: {} }; add(run.usage); }
}
const economy = () => !!S.settings.economy;
const auxTier = (t) => (economy() ? 'quick' : t);
/* модель этапа из настроек: null — «как основная» */
const stageTier = (stage) => { const v = S.settings.stages?.[stage]; return v === 'quick' || v === 'default' || v === 'complex' ? v : null; };
const stageOf = (step, stage) => stage || STAGE_OF_STEP[step] || 'aux';
// у подключения по ключу Claude уровень задаёт модель; у ChatGPT и Иннокода одна модель — уровень ничего не меняет
const stageModel = (conn, tier) => { const pv = provOfConn(conn.id); return (tier && pv && PROVIDERS[pv].tiers?.[tier]) || ''; };
async function ask(prompt, { tools, onProgress, cache, signal, role = 'gen', tier, ai, step = 'other', stage, schema } = {}) {
  const v = ai || (role === 'gen' ? (S.run?.settings.genAI || S.settings.genAI) : aiValue('review'));
  const t = parseAI(v);
  const problem = aiProblem(v);
  if (problem) throw { code: 'provider_unavailable', message: problem };
  const sig = signal || S.ctl?.signal;
  const full = prompt + JSON_TAIL;
  notePrompt(step, full);
  if (t.kind === 'claude') {
    const flat = full.replace(CACHE_MARK, '\n');
    const opts = { signal: sig, modelTier: stageTier(stageOf(step, stage)) || tier || t.tier };
    if (onProgress) opts.onText = ({ text }) => onProgress(text.length);
    let rounds = 0;
    if (tools) opts.tools = tools.map((x) => ({ ...x, execute: (input, o) => { rounds++; return x.execute(input, o); } }));
    else if (cache === false) opts.cache = false;
    const res = await S.caps.sample.json(flat, opts);
    meterAdd(step, estTok(flat) * (1 + rounds), estTok(JSON.stringify(res)));
    return res;
  }
  let usage = null;
  const res = await extJSON(t.conn, full, { tools: tools && t.conn.tools ? tools : null, onProgress, signal: sig, onUsage: (u) => { usage = u; }, model: stageModel(t.conn, stageTier(stageOf(step, stage))), schema });
  if (usage) meterAdd(step, usage.in, usage.out, usage.cached || 0);
  else meterAdd(step, estTok(full), estTok(JSON.stringify(res)));
  return res;
}

/* ---------- внешние ИИ: OpenAI-совместимые API и Anthropic API ---------- */
/* три способа подключения: аккаунт Claude (на claude.ai) или ключ Claude Console, ChatGPT по ключу OpenAI, Иннокод по ключу innoGPT */
const PROVIDERS = {
  claude: { id: 'p-claude', kind: 'anthropic', name: 'Claude', title: 'Аккаунт Claude', baseUrl: 'https://api.anthropic.com', model: 'claude-opus-5-5', models: ['claude-opus-5-5', 'claude-sonnet-5-5', 'claude-haiku-5-5'], tiers: { quick: 'claude-haiku-5-5', default: 'claude-sonnet-5-5', complex: 'claude-opus-5-5' }, tools: true, keyPh: 'sk-ant-…', keyWhere: 'Ключ создаётся в Claude Console (platform.claude.com) → API Keys.' },
  openai: { id: 'p-openai', kind: 'openai', name: 'ChatGPT', title: 'ChatGPT (OpenAI)', baseUrl: 'https://api.openai.com/v1', model: 'gpt-5.5', models: ['gpt-5.5'], tools: true, noTemp: true, keyPh: 'sk-…', keyWhere: 'Ключ создаётся на platform.openai.com → API keys. Оплата — по токенам с баланса OpenAI, а не из подписки ChatGPT Plus или Pro.' },
  innocode: { id: 'p-innocode', kind: 'openai', name: 'Иннокод', title: 'Иннокод', baseUrl: 'https://chat.aicenter.inno.tech/v1', model: 'qwen', models: ['qwen'], tools: false, noTemp: false, keyPh: 'ключ Иннокода', keyWhere: 'Ключ API Иннокода — тот же, что в настройках расширения QA Toolkit (раздел «ИнноКод»). Модель по умолчанию — qwen.' },
};
const PROV_IDS = Object.keys(PROVIDERS);
const provOfConn = (id) => PROV_IDS.find((p) => PROVIDERS[p].id === id) || null;
const provConn = (pid) => S.conns.find((c) => c.id === PROVIDERS[pid].id) || null;
function ensureProv(pid) {
  const P = PROVIDERS[pid];
  let c = provConn(pid);
  if (!c) { c = { id: P.id, preset: pid, kind: P.kind, name: P.name, baseUrl: P.baseUrl, apiKey: '', auth: 'Bearer', model: P.model, headers: '', tools: P.tools, noTemp: !!P.noTemp }; S.conns.push(c); }
  else Object.assign(c, { preset: pid, kind: P.kind, name: P.name, tools: P.tools, noTemp: !!P.noTemp, baseUrl: c.baseUrl || P.baseUrl, model: c.model || P.model });
  return c;
}
/* прежний вариант «Иннокода» (innoGPT) заменён на ИИ-центр inno.tech: старое подключение убираем, выбор переносим */
function migrateProviders() {
  const old = S.conns.find((c) => c.id === 'p-innogpt');
  if (!old) return;
  S.conns = S.conns.filter((c) => c.id !== 'p-innogpt');
  if (S.settings.genAI === 'conn:p-innogpt') S.settings.genAI = 'conn:' + ensureProv('innocode').id;
  if (S.settings.reviewAI === 'conn:p-innogpt') S.settings.reviewAI = 'same';
  saveConns(); saveSettings();
}
function curProv() {
  const v = String(S.settings.genAI || '');
  if (v.startsWith('claude:')) return 'claude';
  return v.startsWith('conn:') ? provOfConn(v.slice(5)) : null;
}
function parseLoose(text) {
  const s = String(text || '').trim();
  const tryP = (x) => { try { return { ok: true, v: JSON.parse(x) }; } catch { return { ok: false }; } };
  let r = tryP(s);
  if (r.ok) return r.v;
  const m = /```(?:json)?\s*([\s\S]*?)```/.exec(s);
  if (m) { r = tryP(m[1].trim()); if (r.ok) return r.v; }
  const a = s.search(/[[{]/), b = Math.max(s.lastIndexOf('}'), s.lastIndexOf(']'));
  if (a >= 0 && b > a) { r = tryP(s.slice(a, b + 1)); if (r.ok) return r.v; }
  throw { code: 'invalid_json', message: 'Модель ответила не в формате JSON.', text: s };
}
const hostOf = (u) => { try { return new URL(u).host; } catch { return u || 'сервер'; } };
async function httpJSON(url, { method = 'POST', headers = {}, body, signal, what = 'Сервер' } = {}) {
  let res;
  try {
    res = await fetch(url, { method, headers: body !== undefined ? { 'Content-Type': 'application/json', ...headers } : headers, body: body !== undefined ? JSON.stringify(body) : undefined, signal });
  } catch (e) {
    if (signal?.aborted) throw { code: 'cancelled', message: 'Остановлено' };
    throw { code: 'network', message: inClaude ? 'На claude.ai страница изолирована от интернета — внешние сервисы доступны только в автономной версии QA pro.' : `${what} ${hostOf(url)} недоступен. Проверьте адрес и сеть. Если сервис в другом домене, разрешите в нём запросы из браузера (CORS) или подключите через прокси.` };
  }
  if (!res.ok) {
    const t = await res.text().catch(() => '');
    throw { code: res.status === 401 || res.status === 403 ? 'auth' : res.status === 429 ? 'rate_limited' : 'http', message: `${what} ${hostOf(url)} ответил ${res.status}${res.status === 401 || res.status === 403 ? ' — проверьте ключ или токен' : ''}: ${t.slice(0, 300)}` };
  }
  return res;
}
function connHeaders(conn) {
  const h = {};
  const extra = tryParse(conn.headers || '{}');
  if (conn.kind === 'anthropic') {
    h['x-api-key'] = conn.apiKey || ''; h['anthropic-version'] = '2023-06-01'; h['anthropic-dangerous-direct-browser-access'] = 'true';
  } else if (conn.apiKey) {
    h.Authorization = conn.auth === 'Api-Key' ? 'Api-Key ' + conn.apiKey : conn.auth === 'none' ? conn.apiKey : 'Bearer ' + conn.apiKey;
  }
  if (extra.ok && extra.value && typeof extra.value === 'object') for (const [k, v] of Object.entries(extra.value)) h[k] = String(v);
  return h;
}
const SYS_JSON = 'Ты — помощник QA-команды. Отвечай строго в формате JSON, без пояснений вне JSON.';
async function openaiCall(conn, messages, { tools, signal, onText, model }) {
  const body = { model: model || conn.model, messages };
  if (!conn.noTemp) body.temperature = 0.2;
  if (tools) body.tools = tools.map((t) => ({ type: 'function', function: { name: t.name, description: t.description, parameters: t.inputSchema || { type: 'object', properties: {} } } }));
  const stream = !tools && !!onText;
  if (stream) body.stream = true;
  const res = await httpJSON(conn.baseUrl.replace(/\/+$/, '') + '/chat/completions', { headers: connHeaders(conn), body, signal, what: 'ИИ' });
  if (stream && /event-stream/.test(res.headers.get('content-type') || '')) {
    const reader = res.body.getReader(), dec = new TextDecoder();
    let buf = '', text = '';
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let k;
      while ((k = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, k).trim(); buf = buf.slice(k + 1);
        if (!line.startsWith('data:')) continue;
        const d = line.slice(5).trim();
        if (d === '[DONE]') continue;
        try { const j = JSON.parse(d); const delta = j.choices?.[0]?.delta?.content; if (delta) { text += delta; onText(text.length); } } catch { /* неполная строка */ }
      }
    }
    return { content: text };
  }
  const j = await res.json();
  const m = { ...(j.choices?.[0]?.message || { content: '' }) };
  if (j.usage) Object.defineProperty(m, '__usage', { value: j.usage, enumerable: false });
  return m;
}
const SCHEMA_TOOL = 'submit_result';
async function anthropicCall(conn, messages, { tools, signal, model, schema }) {
  const body = { model: model || conn.model, max_tokens: Number(conn.maxTokens) || 16000, system: SYS_JSON, messages };
  // Claude 5.x и новее не принимают нестандартную температуру (ответ 400); прежние поколения и чужие шлюзы — принимают
  if (!/^claude-[a-z]+-(?:[5-9]|\d\d)(?:\D|$)/.test(body.model)) body.temperature = 0.2;
  if (tools) body.tools = tools.map((t) => ({ name: t.name, description: t.description, input_schema: t.inputSchema || { type: 'object', properties: {} } }));
  // схема ответа: модель обязана вернуть результат через инструмент с этой схемой, свободного текста не будет
  if (schema && !tools) {
    body.tools = [{ name: SCHEMA_TOOL, description: 'Передай результат в структурированном виде.', input_schema: schema }];
    body.tool_choice = { type: 'tool', name: SCHEMA_TOOL };
  }
  const res = await httpJSON((conn.baseUrl || 'https://api.anthropic.com').replace(/\/+$/, '') + '/v1/messages', { headers: connHeaders(conn), body, signal, what: 'ИИ' });
  return res.json();
}
async function runTool(tools, name, input, signal) {
  const t = tools.find((x) => x.name === name);
  if (!t) return 'Error: unknown tool';
  try { const r = await t.execute(input || {}, { signal }); return typeof r === 'string' ? r : JSON.stringify(r); } catch (e) { return 'Error: ' + (e?.message || e); }
}
async function extJSON(conn, prompt, { tools, onProgress, signal, onUsage, model, schema }) {
  const u = { in: 0, out: 0, cached: 0 }, report = () => onUsage?.(u);
  if (conn.kind === 'anthropic') {
    const k = prompt.indexOf(CACHE_MARK);
    const content = k > 0 ? [{ type: 'text', text: prompt.slice(0, k), cache_control: { type: 'ephemeral' } }, { type: 'text', text: prompt.slice(k + CACHE_MARK.length) }] : prompt;
    const messages = [{ role: 'user', content }];
    for (let round = 0; round < 6; round++) {
      const j = await anthropicCall(conn, messages, { tools: tools && round < 5 ? tools : null, signal, model, schema: schema && round === 0 ? schema : null });
      if (j.usage) { u.in += (j.usage.input_tokens || 0) + (j.usage.cache_creation_input_tokens || 0) + (j.usage.cache_read_input_tokens || 0); u.cached += j.usage.cache_read_input_tokens || 0; u.out += j.usage.output_tokens || 0; report(); }
      const forced = (j.content || []).find((b) => b.type === 'tool_use' && b.name === SCHEMA_TOOL);
      if (forced?.input) { onProgress?.(JSON.stringify(forced.input).length); return forced.input; }
      const uses = (j.content || []).filter((b) => b.type === 'tool_use');
      if (uses.length && j.stop_reason === 'tool_use') {
        messages.push({ role: 'assistant', content: j.content });
        const results = [];
        for (const u of uses) results.push({ type: 'tool_result', tool_use_id: u.id, content: await runTool(tools, u.name, u.input, signal) });
        messages.push({ role: 'user', content: results });
        continue;
      }
      const text = (j.content || []).filter((b) => b.type === 'text').map((b) => b.text).join('');
      onProgress?.(text.length);
      return parseLoose(text);
    }
    throw { code: 'empty_completion' };
  }
  const messages = [{ role: 'system', content: SYS_JSON }, { role: 'user', content: prompt.replace(CACHE_MARK, '\n') }];
  const take = (msg) => { const us = msg?.__usage; if (us) { u.in += us.prompt_tokens || 0; u.out += us.completion_tokens || 0; u.cached += us.prompt_tokens_details?.cached_tokens || 0; report(); } };
  if (tools) {
    for (let round = 0; round < 6; round++) {
      const msg = await openaiCall(conn, messages, { tools: round < 5 ? tools : null, signal, model });
      take(msg);
      if (msg.tool_calls?.length) {
        messages.push({ role: 'assistant', content: msg.content || '', tool_calls: msg.tool_calls });
        for (const tc of msg.tool_calls) {
          let args = {};
          try { args = JSON.parse(tc.function?.arguments || '{}'); } catch { /* пустые аргументы */ }
          messages.push({ role: 'tool', tool_call_id: tc.id, content: await runTool(tools, tc.function?.name, args, signal) });
        }
        continue;
      }
      onProgress?.((msg.content || '').length);
      return parseLoose(msg.content);
    }
    throw { code: 'empty_completion' };
  }
  const msg = await openaiCall(conn, messages, { signal, onText: onProgress, model });
  take(msg);
  return parseLoose(msg.content);
}
async function testConn(conn) {
  const ctl = new AbortController();
  setTimeout(() => ctl.abort(), 60000);
  const r = await extJSON(conn, 'Проверка связи. Ответь JSON-объектом {"ok": true, "model": "<как тебя зовут>"}.', { signal: ctl.signal });
  return r;
}
/* неудавшиеся запросы запуска для баннера «Готово с ошибками»: пачка (вид, пункты плана) и причина */
function failedInfo(run) {
  const step = (id) => { const st = STEPS.find((x) => x.id === id); return st ? stepTitle(st, run.mode) : ''; };
  const live = arrOf(run.failed).map((f) => {
    if (f.kind === 'src') return { where: step(f.step), items: [], error: String(f.error || '') };
    const items = arrOf(f.batch?.items);
    return { where: `${TL[f.batch?.type] || ''} · ${[...new Set(items.map((i) => i.id))].join(', ')}`.replace(/^ · /, ''), items: [...new Set(items.map((i) => i.title).filter(Boolean))].slice(0, 6), error: String(f.error || '') };
  });
  if (live.length) return live;
  if (arrOf(run.failedInfo).length) return run.failedInfo;
  // запуск из истории до этой версии: причины — из журнала шагов
  const out = [];
  for (const st of stepsOf(run.mode)) for (const l of arrOf(run.steps?.[st.id]?.log)) if (l.kind === 'err') out.push({ where: stepTitle(st, run.mode), items: [], error: String(l.text || '') });
  return out.slice(-30);
}
function handleCallError(run, e, line, label) {
  if (e?.code === 'cancelled') { line.text = `${label}: остановлено`; line.kind = 'warn'; return; }
  line.text = `${label}: ${errText(e)}`; line.kind = 'err';
  if (FATAL.has(e?.code)) { run.fatal = errText(e); S.ctl?.abort(); }
}
function makeTools(run, stepId) {
  const docs = docsFor(run); // документы запуска; остальное о продукте — в базе знаний
  const tools = [
    {
      name: 'search_documents',
      description: 'Полнотекстовый поиск по документам запуска (ТЗ, по которому идёт генерация). Возвращает до 5 наиболее релевантных фрагментов: document, offset, text (до 700 знаков). Используй, чтобы уточнить форматы полей, лимиты, коды и тексты ошибок, названия элементов.',
      inputSchema: { type: 'object', properties: { query: { type: 'string', description: 'Ключевые слова на языке документа' } }, required: ['query'] },
      execute: (input) => {
        const q = String(input?.query || '').slice(0, 200);
        const res = searchDocs(q, docs);
        slog(run, stepId, `Поиск в документах: «${q}» — ${res.length} ${plural(res.length, 'фрагмент', 'фрагмента', 'фрагментов')}`, 'tool');
        return res.length ? res : 'Ничего не найдено. Попробуй другие слова.';
      },
    },
    {
      name: 'read_document',
      description: 'Читает фрагмент документа запуска по имени и позиции (из результатов search_documents). Возвращает до 3000 знаков текста.',
      inputSchema: { type: 'object', properties: { document: { type: 'string' }, offset: { type: 'number' }, length: { type: 'number', description: 'До 3000' } }, required: ['document', 'offset'] },
      execute: (input) => {
        const r = readDoc(String(input?.document || ''), input?.offset, input?.length, docs);
        slog(run, stepId, `Чтение: ${r.document}, позиция ${fmtN(r.offset)}`, 'tool');
        return r;
      },
    },
  ];
  if (!kbSections(run.productId).length) return tools;
  tools.push({
    name: 'search_knowledge_base',
    description: 'Поиск по базе знаний продукта — сводкам функциональных разделов, собранным из всех документов продукта, включая расшифровки созвонов и демо. Возвращает до 3 разделов: id, title, summary, conflicts (расхождения между документами) и самые подходящие строки сводки (до 1500 знаков). Используй, чтобы найти правила, лимиты, роли, тексты сообщений и связи, которых нет в документах запуска.',
    inputSchema: { type: 'object', properties: { query: { type: 'string', description: 'Ключевые слова: функция, экран, поле, роль, сообщение' } }, required: ['query'] },
    execute: (input) => {
      const q = String(input?.query || '').slice(0, 200);
      const res = kbRank(q, kbSections(run.productId)).slice(0, 3).map((x) => ({ id: x.b.id, title: x.b.title, summary: x.d.summary || x.b.summary || '', conflicts: arrOf(x.d.conflicts).slice(0, 5), text: kbFitText(kbSectionText(x.d), q, 1500) }));
      slog(run, stepId, `База знаний: «${q}» — ${res.length} ${plural(res.length, 'раздел', 'раздела', 'разделов')}`, 'tool');
      return res.length ? res : 'Ничего не найдено. Попробуй другие слова.';
    },
  }, {
    name: 'read_knowledge_section',
    description: 'Читает сводку раздела базы знаний по id из search_knowledge_base: все сведения о функции из всех документов продукта с источниками, расхождения и связанные разделы. Длинная сводка отдаётся частями до 6000 знаков: в ответе part и parts, следующую часть читай с part на 1 больше.',
    inputSchema: { type: 'object', properties: { id: { type: 'string', description: 'id раздела' }, part: { type: 'number', description: 'Часть длинной сводки, с 1' } }, required: ['id'] },
    execute: (input) => {
      const key = String(input?.id || '').trim(), secs = kbSections(run.productId);
      const x = secs.find((y) => y.b.id === key) || secs.find((y) => normKey(y.b.title) === normKey(key));
      if (!x) return 'Раздел не найден — возьми id из search_knowledge_base.';
      slog(run, stepId, `База знаний: читаю «${x.b.title}»`, 'tool');
      const titleOf = new Map(S.kb.index.blocks.map((b) => [b.id, b.title]));
      const pages = kbPages(kbSectionText(x.d), 6000), k = Math.min(pages.length, Math.max(1, Math.round(Number(input?.part) || 1)));
      return { id: x.b.id, title: x.b.title, part: k, parts: pages.length, text: pages[k - 1], ...(k === 1 ? { conflicts: arrOf(x.d.conflicts), links: arrOf(x.d.links).map((id) => titleOf.get(id)).filter(Boolean) } : {}) };
    },
  });
  return tools;
}

/* ================= run model ================= */
function newRun() {
  const docs = docsFor(null);
  const base = S.productId ? productCounters(S.productId) : { api: 0, ui: 0, e2e: 0, cl: 0 };
  const upd = S.settings.mode === 'update' && S.upd.file?.status === 'ready';
  const f = S.upd.file;
  if (upd) for (const t of TYPES) {
    const pre = S.cfg.tpl[t].idPrefix || '';
    if (!pre) continue;
    for (const c of f.cases) if (c.srcId.startsWith(pre)) { const n = Number((/(\d+)\s*$/.exec(c.srcId) || [])[1] || 0); if (n > base[t]) base[t] = n; }
  }
  return {
    id: rid('run_'), createdAt: Date.now(), finishedAt: null, productId: S.productId || null, by: S.caps.uid || '',
    mode: upd ? 'update' : 'generate',
    source: upd ? { name: f.name, ext: f.ext, count: f.cases.length, note: f.note || '' } : null,
    srcCases: upd ? f.cases.map((c) => ({ ...c, reqIds: [], status: '', reason: '', instruction: '', mapped: false, done: false })) : [],
    docs: docs.map((d) => ({ name: d.name, chars: d.chars })), docIds: docs.map((d) => d.id),
    settings: { outputs: upd ? { cases: true, checklist: !!S.settings.outputs.checklist } : { ...S.settings.outputs }, types: selectedTypes(), depth: S.settings.depth, genAI: S.settings.genAI, agentTools: S.settings.agentTools, skipExisting: S.settings.skipExisting, target: S.settings.target || null },
    findings: null, qaCtx: { ...S.qaCtx }, coveredExisting: [],
    requirements: [], reqById: {}, questions: [], plan: [], cases: [], failed: [], checklist: null, doneKeys: [],
    counters: { ...base }, baseCounters: { ...base },
    stage: 'draft', addedAt: null, // кейсы сначала в черновике: в продукт — только по кнопке «Добавить в проект»
    steps: Object.fromEntries(STEPS.map((s) => [s.id, { status: 'pending', log: [], t0: null, t1: null, note: '' }])),
    status: 'running', error: null, fatal: null, fromHistory: false,
  };
}
function slog(run, id, text, kind = '') {
  const st = run.steps[id];
  const line = { text, kind };
  st.log.push(line);
  if (st.log.length > 250) st.log.splice(0, st.log.length - 250);
  scheduleRender(); markDirty(run);
  return line;
}
function sstart(run, id) { const st = run.steps[id]; st.status = 'running'; st.t0 = st.t0 || Date.now(); st.t1 = null; scheduleRender(); markDirty(run); }
function send(run, id, status = 'done') { const st = run.steps[id]; st.status = status; st.t1 = Date.now(); scheduleRender(); markDirty(run); }
function skipStep(run, id, note = 'не выбрано') { run.steps[id].status = 'skipped'; run.steps[id].note = note; }
function markRunning(run, status, msg) {
  for (const s of STEPS) {
    const st = run.steps[s.id];
    if (st.status === 'running') { st.status = status; st.t1 = Date.now(); if (msg) st.log.push({ text: msg, kind: 'err' }); }
    else if (st.status === 'pending' && !s.optional) st.status = 'skipped';
  }
}
const abortErr = () => Object.assign(new Error('aborted'), { code: 'cancelled' });
const activeCases = (run) => run.cases.filter((c) => c.status !== 'obsolete');
const coveredByProduct = (run, reqId) => (run.coveredExisting || []).find((a) => a.requirementId === reqId) || null;
function isCovered(run, reqId) {
  return outputsOf(run).cases ? activeCases(run).some((c) => c.requirementIds.includes(reqId)) || !!coveredByProduct(run, reqId) : checklistItems(run).some((i) => i.requirementIds.includes(reqId));
}
function uncovered(run) { const act = activeCases(run); return run.requirements.filter((r) => r.inScope && !act.some((c) => c.requirementIds.includes(r.id)) && !coveredByProduct(run, r.id)); }
/* ручная или ИИ-правка актуализированного кейса делает его «изменённым» */
function touchCase(c, note) {
  if (c.status !== 'same') return;
  c.status = 'changed'; c.changes = [...(c.changes || []), note].slice(-8);
}
function nextDispId(run, type) {
  const taken = new Set(run.cases.map((c) => c.dispId));
  let id;
  do id = (S.cfg.tpl[type].idPrefix || '') + pad(++run.counters[type]); while (taken.has(id));
  return id;
}
function coveragePct(run) {
  const scope = run.requirements.filter((r) => r.inScope);
  if (!scope.length) return null;
  return Math.round(100 * scope.filter((r) => isCovered(run, r.id)).length / scope.length);
}
const qStatus = (q) => (!q.answer?.trim() ? 'none' : q.answer.trim() === (q.appliedAnswer || '') ? 'applied' : 'pending');

function buildChunks(docs) {
  const split = (t) => {
    if (t.length <= CHUNK) return [t];
    const out = []; let cur = '';
    for (const p of t.split(/\n{2,}/)) {
      if (p.length > CHUNK) { if (cur) { out.push(cur); cur = ''; } for (let i = 0; i < p.length; i += CHUNK) out.push(p.slice(i, i + CHUNK)); continue; }
      if (cur.length + p.length + 2 > CHUNK) { out.push(cur); cur = ''; }
      cur += (cur ? '\n\n' : '') + p;
    }
    if (cur) out.push(cur);
    return out;
  };
  const chunks = []; let cur = null;
  for (const d of docs) {
    const pieces = split(d.text);
    pieces.forEach((text, i) => {
      const block = { doc: d.name, part: i + 1, parts: pieces.length, text };
      if (cur && cur.size + text.length <= CHUNK) { cur.blocks.push(block); cur.size += text.length; }
      else { cur = { blocks: [block], size: text.length }; chunks.push(cur); }
    });
  }
  return chunks;
}
function makeBatches(items, done, dchk = null) {
  const LIM = { api: 8, ui: 8, e2e: 4 };
  const batches = [];
  for (const t of TYPES) {
    let parts = [];
    for (const it of items.filter((x) => x.type === t)) {
      const lim = LIM[t];
      for (let i = 0, k = 0; i < Math.max(1, it.checks.length); i += lim, k++) parts.push({ ...it, checks: it.checks.slice(i, i + lim), key: `${it.id}#${k}` });
    }
    // проверки, уже написанные частями (ответ не уместился и пачка делилась), повторно не пишем
    if (dchk?.size) parts = parts.map((p) => ({ ...p, checks: p.checks.filter((c) => !dchk.has(p.key + '|' + c)) }));
    parts = parts.filter((p) => p.checks.length && !(done && done.has(p.key)));
    let cur = null;
    for (const p of parts) {
      if (!cur || cur.n + p.checks.length > LIM[t] || cur.items.length >= 3) { cur = { type: t, items: [], n: 0 }; batches.push(cur); }
      cur.items.push(p); cur.n += p.checks.length;
    }
  }
  return batches;
}
/* Метка вида теста в начале названия: [BE] — API, [Kafka] — сообщения Kafka (вместо [BE]), [FE] — UI, [E2E] — сквозные.
   Метку ставит модель по правилу; здесь она проверяется и при необходимости дописывается. Названия без ключа из TITLE_KEYS не трогаем. */
const KNOWN_TAG_RX = /^\s*(?:\[(?:BE|FE|UI|API|E2E|Kafka|Кафка|Back-?end|Front-?end)\]\s*)+/i;
function titleTagFor(type, title) {
  if (type !== 'api') return TITLE_TAG[type] || '';
  const given = title.match(KNOWN_TAG_RX)?.[0] || '';
  if (given) return /\[(?:kafka|кафка)\]/i.test(given) ? KAFKA_TAG : TITLE_TAG.api;
  return !/^\s*(?:GET|POST|PUT|PATCH|DELETE)\s/i.test(title) && /kafka|кафка/i.test(title) ? KAFKA_TAG : TITLE_TAG.api;
}
function tagTitle(tc, type) {
  const { key, text } = pickTitle(tc);
  if (!TITLE_TAG[type] || !key || !TITLE_KEYS.includes(key)) return tc;
  const rest = text.replace(KNOWN_TAG_RX, '').trim();
  if (rest) tc[key] = `${titleTagFor(type, text)} ${rest}`;
  return tc;
}
const titleTagOk = (c) => { const tc = { ...(c.testCase || {}) }, was = pickTitle(tc).text; return pickTitle(tagTitle(tc, c.type)).text === was; };
function orderLikeTemplate(tc, info, type) {
  tc = baseUrlDeep(noReqDeep(cleanCase(tc))); // без <p>, HTML и буквальных «\n», без отсылок к требованиям QA pro; адрес API — {baseURL}/путь
  if (type) tagTitle(tc, type);
  if (typeof tc.priority === 'string') tc.priority = normPrio(tc.priority);
  if (type === 'api') delete tc.request;
  if (!info.ok) return tc;
  const ordered = {};
  for (const k of info.fields) if (k in tc) ordered[k] = tc[k];
  for (const k of Object.keys(tc)) if (!(k in ordered)) ordered[k] = tc[k];
  return ordered;
}
function acceptCases(run, b, res) {
  const info = tplInfo(b.type);
  const arr = Array.isArray(res) ? res : Array.isArray(res?.cases) ? res.cases : Array.isArray(res?.testCases) ? res.testCases : [];
  const itemIds = b.items.map((i) => i.id);
  // пункты чек-листа в пачке: planItem → номера пунктов; каждый пункт достаётся одному кейсу
  const clIn = new Map(), clUsed = new Set();
  for (const it of b.items) for (const ch of it.checks) { const id = clIdOf(ch); if (id) { if (!clIn.has(it.id)) clIn.set(it.id, []); clIn.get(it.id).push(id); } }
  const clAll = new Set([...clIn.values()].flat());
  let added = 0;
  for (const c of arr) {
    if (!c || typeof c !== 'object') continue;
    // строгое число тестов: модель могла вернуть больше кейсов, чем проверок — лишние не добавляем (покрытие требования считает свой лимит)
    if (strictTarget(run) && !run.regenFrom && !b.items.some((it) => it.variant) && run.cases.length >= run.settings.target) break;
    let tc = c.testCase && typeof c.testCase === 'object' && !Array.isArray(c.testCase) ? c.testCase : null;
    if (!tc) { tc = { ...c }; delete tc.planItem; delete tc.requirementIds; delete tc.suites; }
    const hasCase = (id) => run.cases.some((x) => x.planItem === id);
    let planItem = itemIds.includes(c.planItem) ? c.planItem : itemIds[0];
    if (b.items.some((it) => it.regen)) {
      // перегенерация: ровно один кейс на прежний кейс; без номера пункта — первому пункту пачки, у которого кейса ещё нет
      if (!itemIds.includes(c.planItem)) planItem = itemIds.find((id) => !hasCase(id)) || '';
      if (!planItem || hasCase(planItem)) continue;
    }
    let reqIds = arrStr(c.requirementIds).filter((id) => run.reqById[id]);
    if (!reqIds.length) reqIds = (b.items.find((i) => i.id === planItem)?.requirementIds || []).slice();
    const dispId = nextDispId(run, b.type);
    if (info.ok && info.idField) tc[info.idField] = dispId;
    tc = orderLikeTemplate(tc, info, b.type);
    let clId = '';
    if (clAll.size) {
      clId = String(c.checklistId || '').trim().toUpperCase();
      // номер не указан или чужой — следующий свободный пункт той же группы плана; у группы без пунктов чек-листа связи нет
      if (!clAll.has(clId) || clUsed.has(clId)) clId = (clIn.get(planItem) || []).find((x) => !clUsed.has(x)) || '';
    }
    const cl = clId ? checklistItems(run).find((i) => i.id === clId) : null;
    if (cl) {
      clUsed.add(clId);
      if (typeof tc.priority === 'string') tc.priority = normPrio(cl.priority); // приоритет — как у пункта чек-листа
      if (!arrStr(c.requirementIds).some((id) => run.reqById[id]) && cl.requirementIds.length) reqIds = cl.requirementIds.slice();
    }
    const nc = { uid: rid('c'), type: b.type, planItem, requirementIds: reqIds, suites: withCritical(tc.priority, normSuites(c.suites).length ? normSuites(c.suites) : cl?.suites || []), testCase: tc, dispId, ...(cl ? { checklistId: clId } : {}) };
    if (run.mode === 'update') Object.assign(nc, { status: 'new', note: 'Новая проверка: требование не было покрыто кейсами из файла', changes: [] });
    run.cases.push(nc);
    added++;
  }
  return added;
}

/* ================= pipeline ================= */
async function runAgent() {
  if (S.running) return;
  const docs = docsFor(null), types = selectedTypes(), out = S.settings.outputs;
  const note = (t) => { $('#run-note').textContent = t; $('#run-note').className = 'run-note err'; };
  if (!aiReady(S.settings.genAI)) return note(aiProblem(S.settings.genAI));
  if (S.caps.db && S.caps.uid && !S.prodReady) return note('Загружаю продукт — подождите несколько секунд.');
  if (runDocList().some((d) => d.status === 'parsing' || d.status === 'loading')) return note('Дождитесь окончания загрузки и разбора файлов.');
  if (!docs.length) return note(S.productId ? 'Загрузите ТЗ для этого запуска — остальное о продукте агент возьмёт из базы знаний.' : 'Добавьте хотя бы один документ с текстом.');
  const upd = S.settings.mode === 'update';
  if (upd && S.upd.file?.status !== 'ready') return note(S.upd.file?.status === 'parsing' ? 'Дождитесь разбора файла с тест-кейсами.' : 'Загрузите файл с тест-кейсами для актуализации: .xlsx или .json.');
  if (!upd && !out.cases && !out.checklist) return note('Выберите, что сгенерировать: тест-кейсы, чек-лист или оба.');
  if (!types.length) return note('Выберите хотя бы один вид тестов.');
  if (out.cases || upd) for (const t of upd ? TYPES : types) {
    const info = tplInfo(t);
    if (!info.ok) { note(`Шаблон ${TL[t]}: ${info.error}`); S.cfgType = t; openSettings('tpl'); return; }
  }
  stopFollow(); cancelResumeCountdown();
  if (S.ctxDirty && S.productId) saveProductCtx();
  const run = S.run = newRun();
  S.caseUI.clear(); S.reqOpen.clear(); S.filter = { type: 'all', suite: 'all', q: '' }; S.clFilter = { type: 'all', suite: 'all' }; S.clEdit = null; S.exp = null;
  S.tab = 'agent';
  executeRun(run, false);
}
/* шаги, которые уже выполнены, при продолжении пропускаются */
const MAIN_STEPS = ['parse', 'analyze', 'checklist', 'map', 'actualize', 'plan', ...GEN_STEPS, 'coverage'];
const srcPending = (run, flag) => (run.srcCases || []).some((c) => !c[flag]);
/* шаг в статусе error не завершён: при «Продолжить» он запускается заново, уже готовые части (кэш анализа, готовые пачки) не повторяются */
const stepComplete = (run, id) => { const st = run.steps[id]; return st.status === 'done' || (st.status === 'skipped' && st.note === 'не выбрано'); };
function pendingParts(run, prefix, type) {
  const done = new Set(run.doneKeys || []);
  return makeBatches(run.plan.filter((p) => (!prefix || p.id.startsWith(prefix)) && (!type || p.type === type)), done, new Set(run.doneChecks || [])).reduce((a, b) => a + b.items.length, 0);
}
function canResume(run) {
  if (!run || S.running || S.follow || run.fromHistory === 'readonly' || !run.steps) return false;
  const out = outputsOf(run);
  if (!stepComplete(run, 'analyze')) return true;
  if (out.checklist && !stepComplete(run, 'checklist')) return true;
  if (run.mode === 'update' && (!stepComplete(run, 'map') || !stepComplete(run, 'actualize') || srcPending(run, 'mapped') || srcPending(run, 'done'))) return true;
  if (out.cases && (!stepComplete(run, 'plan') || GEN_STEPS.some((id) => !stepComplete(run, id)) || !stepComplete(run, 'coverage'))) return true;
  return !!out.cases && pendingParts(run, 'P-') + pendingParts(run, 'G-') > 0;
}
async function pipeline(run) {
  const docs = docsFor(run), types = run.settings.types || selectedTypes(), out = outputsOf(run);
  const noDocs = 'Документы этого запуска не сохранились — загрузите их снова и запустите генерацию.';
  // база знаний продукта: сводки разделов из всех документов — в контекст анализа, чек-листа, плана, кейсов и ревью
  let kbN = 0;
  try { kbN = run.noKb ? 0 : await kbLoadAll(run.productId); } catch { kbN = 0; }
  if (!stepComplete(run, 'parse')) {
    if (!docs.length) throw new Error(noDocs);
    sstart(run, 'parse');
    for (const d of docs) slog(run, 'parse', `${d.name} — ${fmtKChars(d.chars)}${d.warn ? ' · ' + d.warn : ''}`, d.warn ? 'warn' : 'ok');
    const total = docs.reduce((a, d) => a + d.chars, 0);
    slog(run, 'parse', `Итого ${fmtKChars(total)} в ${docs.length} ${plural(docs.length, 'документе', 'документах', 'документах')}`);
    if (run.mode === 'update') slog(run, 'parse', `Файл с кейсами: ${run.source.name} — ${run.srcCases.length} ${plural(run.srcCases.length, 'кейс', 'кейса', 'кейсов')}${run.source.note ? ' (' + run.source.note + ')' : ''}`, 'ok');
    const cx = ['all', ...TYPES].filter((k) => run.qaCtx?.[k]?.trim());
    slog(run, 'parse', cx.length ? `Доп. контекст от QA: ${cx.map((k) => (k === 'all' ? 'для всех' : TL[k])).join(', ')}` : 'Доп. контекста от QA нет — работаю только по документам', cx.length ? 'ok' : '');
    if (run.productId) {
      const st = kbN ? kbStale().length : 0;
      slog(run, 'parse', kbN ? `База знаний: ${kbN} ${plural(kbN, 'раздел', 'раздела', 'разделов')} из всех документов продукта — сводки по теме идут в анализ, чек-лист, план, кейсы и ревью${st ? ` (без свежей сводки: ${st} — по ним агент берёт выдержки из документов)` : ''}` : 'База знаний продукта пока пуста — работаю по документам запуска', kbN ? 'ok' : '');
    }
    send(run, 'parse');
  }
  if (!stepComplete(run, 'analyze')) {
    if (!docs.length) throw new Error(noDocs);
    run.requirements = []; run.reqById = {}; run.questions = [];
    await stepAnalyze(run, docs, types);
  } else indexReqs(run);
  if (out.checklist) { if (!stepComplete(run, 'checklist')) { run.counters.cl = run.baseCounters?.cl || 0; await stepChecklist(run); } }
  else skipStep(run, 'checklist');
  if (run.mode === 'update') {
    if (!stepComplete(run, 'map') || srcPending(run, 'mapped')) await stepMap(run);
    if (!stepComplete(run, 'actualize') || srcPending(run, 'done')) await stepActualize(run);
    if (srcPending(run, 'mapped') || srcPending(run, 'done')) { slog(run, 'actualize', 'Новые кейсы агент допишет, когда все кейсы из файла будут обработаны — нажмите «Продолжить с места остановки»', 'warn'); return; }
  } else { skipStep(run, 'map'); skipStep(run, 'actualize'); }
  if (out.cases) {
    if (!stepComplete(run, 'plan')) {
      await stepPlan(run, types);
      if (run.regenTpl) { for (const line of run.regenTpl) slog(run, 'plan', 'Перегенерация по текущим шаблонам · ' + line, 'ok'); delete run.regenTpl; }
    }
    // отдельный этап на каждый вид тестов: API → UI → E2E, у каждого свой журнал, статус и продолжение
    for (const t of TYPES) {
      const id = GEN_STEP[t], items = run.plan.filter((p) => p.id.startsWith('P-') && p.type === t);
      if (!types.includes(t)) { skipStep(run, id); continue; }
      if (stepComplete(run, id) && !pendingParts(run, 'P-', t)) continue;
      if (!items.length) {
        sstart(run, id);
        slog(run, id, run.mode === 'update' ? 'Новые кейсы не нужны' : `В плане нет проверок ${TL[t]}`, 'ok');
        send(run, id);
        continue;
      }
      sstart(run, id);
      await generateItems(run, items, id);
      send(run, id, run.failed.some((f) => f.batch?.type === t) ? 'error' : 'done');
    }
    if (run.regenFrom?.length) await regenTopUp(run);
    else {
      if (strictTarget(run)) await strictTopUp(run);
      if (!stepComplete(run, 'coverage') || pendingParts(run, 'G-')) await stepCoverage(run);
    }
  } else { skipStep(run, 'plan'); for (const id of GEN_STEPS) skipStep(run, id); skipStep(run, 'coverage'); }
  if (run.productId && !stepComplete(run, 'knowledge') && (run.cases.length || checklistItems(run).length)) await stepKnowledge(run);
}
async function executeRun(run, resumed) {
  S.ctl = new AbortController(); S.running = true;
  run.status = 'running'; run.error = null; run.fatal = null; run.finishedAt = null; run.failed = []; run.fromHistory = false; run.interrupted = null;
  if (resumed) {
    run.taskStart = Date.now();
    const st = MAIN_STEPS.filter((id) => run.mode === 'update' || (id !== 'map' && id !== 'actualize')).find((id) => !stepComplete(run, id)) || 'gen_api';
    slog(run, st, 'Продолжаю с места остановки — готовые шаги и запросы не повторяются', 'warn');
  }
  renderAll(); startTicker();
  if (S.caps.db && S.caps.uid) saveChain = saveChain.then(() => saveRun(run)).catch(() => {});
  startHeartbeat(run);
  if (window.innerWidth < 960) $('.work')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  try {
    await pipeline(run);
    run.status = run.failed.length ? 'partial' : 'done';
  } catch (e) {
    if (run.fatal) { run.status = 'error'; run.error = run.fatal; markRunning(run, 'error'); }
    else if (S.ctl.signal.aborted) { run.status = 'stopped'; markRunning(run, 'stopped'); }
    else { run.status = 'error'; run.error = errText(e); markRunning(run, 'error', run.error); }
  } finally {
    run.finishedAt = Date.now();
    S.running = false; stopTicker(); stopHeartbeat();
    renderAll();
    const n = checklistItems(run).length;
    // кейсы готовы — сразу на проверку в черновик
    if (run.stage === 'draft' && run.cases.length && run.status !== 'stopped' && S.run === run && S.tab === 'agent') { S.tab = 'draft'; renderTabs(); renderTab(); }
    if (run.status !== 'stopped' && (run.cases.length || n)) toast(`Готово: ${[run.cases.length ? `${run.cases.length} ${plural(run.cases.length, 'тест-кейс', 'тест-кейса', 'тест-кейсов')}` : '', n ? `чек-лист из ${n} ${plural(n, 'пункта', 'пунктов', 'пунктов')}` : ''].filter(Boolean).join(', ')}`);
    // сначала сохраняем итог запуска, потом снимаем отметку «идёт генерация» — иначе другая вкладка решит, что запуск прерван
    if (S.caps.db && S.caps.uid && (run.requirements.length || resumed)) saveChain = saveChain.then(() => saveRun(run)).catch(() => {});
    saveChain = saveChain.then(() => flushSessionNow()).then(() => productSync(run));
  }
}
function resumeRun() {
  const run = S.run;
  cancelResumeCountdown();
  if (!run || S.running) return;
  const v = run.settings.genAI || S.settings.genAI;
  if (!aiReady(v)) return toast(aiProblem(v), 'err');
  S.tab = 'agent';
  executeRun(run, true);
}
/* кэш анализа: тот же фрагмент документов с теми же видами тестов, правилами и контекстом повторно не отправляется модели */
const anaKey = (run, ch, types) => 'a2_' + hash(JSON.stringify([ch.blocks.map((b) => [b.doc, b.text]), [...types].sort(), rulesText(), run.qaCtx || {}, hash(kbGenBlock(run, 'analyze', chunkFocus(ch)))]));
async function anaCacheGet(run, key) {
  if (!run.productId || !S.caps.db || S.settings.reuseAnalysis === false) return null;
  try { return (await S.caps.db.doc(`${prodPath(run.productId)}/cache/${key}`).get()).data() || null; } catch { return null; }
}
async function anaCachePut(run, key, res) {
  if (!run.productId || !S.caps.db) return;
  const data = { requirements: arrOf(res?.requirements), questions: arrStr(res?.questions), at: Date.now() };
  if (!data.requirements.length || JSON.stringify(data).length * 2 > 240000) return;
  try { await S.caps.db.doc(`${prodPath(run.productId)}/cache/${key}`).set(data); } catch { /* кэш — необязательный */ }
}
async function stepAnalyze(run, docs, types) {
  sstart(run, 'analyze');
  const chunks = buildChunks(docs);
  if (chunks.length > 1) slog(run, 'analyze', `Документы разбиты на ${chunks.length} ${plural(chunks.length, 'фрагмент', 'фрагмента', 'фрагментов')} до ${CHUNK / 1000} тыс. знаков`);
  const results = [];
  await pool(chunks, CONCURRENCY, async (ch, i) => {
    const label = chunks.length > 1 ? `Фрагмент ${i + 1}/${chunks.length}` : 'Анализ';
    const key = anaKey(run, ch, types);
    const hit = await anaCacheGet(run, key);
    if (hit) {
      results[i] = hit;
      const n = arrOf(hit.requirements).length;
      slog(run, 'analyze', `${label}: ${n} ${plural(n, 'требование', 'требования', 'требований')} — эти документы уже анализировались, результат взят из кэша продукта`, 'ok');
      return;
    }
    const line = slog(run, 'analyze', `${label}: модель читает документы…`);
    try {
      const res = await ask(promptAnalyze(ch, i, chunks.length, types, run.qaCtx, run), { step: 'analyze',
        onProgress: (n) => { line.text = `${label}: пишет ответ — ${fmtKChars(n)}`; scheduleRender(); },
      });
      const n = Array.isArray(res?.requirements) ? res.requirements.length : 0;
      line.text = `${label}: ${n} ${plural(n, 'требование', 'требования', 'требований')} — проверяю полноту…`; scheduleRender();
      // второй проход: модель сверяет фрагмент со списком и добавляет пропущенные требования и критерии
      let added = 0, crit = 0;
      if (n) {
        try {
          const more = await ask(promptAnalyzeMore(ch, i, chunks.length, types, arrOf(res.requirements)), { step: 'analyze', onProgress: (k) => { line.text = `${label}: проверка полноты — ${fmtKChars(k)}`; scheduleRender(); } });
          const have = new Set(arrOf(res.requirements).map((r) => normKey(r?.title || '')));
          for (const r of arrOf(more?.requirements)) if (r && r.title && !have.has(normKey(r.title))) { res.requirements.push(r); have.add(normKey(r.title)); added++; }
          for (const x of arrOf(more?.criteria)) {
            const t = arrOf(res.requirements).find((r) => normKey(r?.title || '') === normKey(x?.title || ''));
            if (!t) continue;
            t.criteria = arrStr(t.criteria);
            for (const c of arrStr(x?.add)) if (!t.criteria.some((y) => normKey(y) === normKey(c))) { t.criteria.push(c); crit++; }
          }
        } catch (e) { if (e?.code === 'cancelled') throw e; if (FATAL.has(e?.code)) handleCallError(run, e, line, label); }
      }
      results[i] = res;
      anaCachePut(run, key, res);
      const m = arrOf(res?.requirements).length;
      line.text = `${label}: ${m} ${plural(m, 'требование', 'требования', 'требований')}${added || crit ? ` (проверка полноты: ${[added ? `+${added} ${plural(added, 'требование', 'требования', 'требований')}` : '', crit ? `+${crit} ${plural(crit, 'критерий', 'критерия', 'критериев')}` : ''].filter(Boolean).join(', ')})` : ''}`; line.kind = m ? 'ok' : 'warn';
    } catch (e) { handleCallError(run, e, line, label); }
    scheduleRender();
  }, S.ctl.signal);
  if (S.ctl.signal.aborted) throw abortErr();
  const seen = new Map(), qSeen = new Set();
  let n = 0;
  for (const res of results) {
    if (!res) continue;
    for (const r of Array.isArray(res.requirements) ? res.requirements : []) {
      if (!r || typeof r !== 'object' || !r.title) continue;
      const key = normKey(r.title);
      if (seen.has(key)) { const ex = seen.get(key); for (const c of arrStr(r.criteria)) if (!ex.criteria.includes(c)) ex.criteria.push(c); continue; }
      const tps = arrStr(r.types).map((x) => x.toLowerCase()).filter((x) => types.includes(x));
      const req = {
        id: 'R-' + pad(++n), title: String(r.title), description: String(r.description || ''),
        types: [...new Set(tps)], priority: normPrio(r.priority), doc: String(r.doc || ''), section: String(r.section || ''),
        quote: String(r.quote || '').slice(0, 400), criteria: arrStr(r.criteria),
      };
      req.inScope = req.types.length > 0;
      seen.set(key, req); run.requirements.push(req);
    }
    for (const q of arrStr(res.questions)) {
      if (qSeen.has(normKey(q))) continue;
      qSeen.add(normKey(q));
      run.questions.push({ id: 'Q-' + pad(run.questions.length + 1, 2), text: q, answer: '', appliedAnswer: '' });
    }
  }
  indexReqs(run);
  if (!run.requirements.length) throw new Error(results.some(Boolean) ? 'В документах не найдено проверяемых требований.' : 'Не удалось проанализировать документы.');
  const outN = run.requirements.filter((r) => !r.inScope).length;
  slog(run, 'analyze', `Итого ${run.requirements.length} ${plural(run.requirements.length, 'требование', 'требования', 'требований')}${outN ? `, из них ${outN} вне выбранных видов тестов` : ''}; вопросов к документации: ${run.questions.length}`, 'ok');
  send(run, 'analyze', results.filter(Boolean).length < chunks.length ? 'error' : 'done');
  if (!run.requirements.some((r) => r.inScope)) throw new Error('Ни одно требование не относится к выбранным видам тестов.');
}
const clKind = (k) => (/negat|негатив|boundary|гранич|error|ошиб/i.test(String(k || '')) ? 'negative' : 'positive');
function normChecklistItem(run, it, types) {
  const type = String(it?.type || '').toLowerCase();
  return {
    id: '', check: String(it?.check || it?.title || it?.text || '').trim(), expected: String(it?.expected || it?.expectedResult || '').trim(), kind: clKind(it?.kind),
    type: types.includes(type) ? type : types[0],
    priority: normPrio(it?.priority), suites: withCritical(it?.priority, normSuites(it?.suites)), requirementIds: arrStr(it?.requirementIds).filter((id) => run.reqById[id]),
  };
}
/* порядок отбора при лимите: позитивные по убыванию приоритета, затем негативные */
const PRIO_RANK = { P4_CRITICAL: 0, P3_HIGH: 1, P2_MEDIUM: 2, P1_LOW: 3 };
const clRank = (i) => (i.kind === 'negative' ? 10 : 0) + (PRIO_RANK[normPrio(i.priority)] ?? 2);
function splitQuota(n, sizes) {
  const q = sizes.map((s) => Math.floor((n * s) / (sizes.reduce((a, x) => a + x, 0) || 1)));
  if (!q.length) return q;
  let rest = n - q.reduce((a, x) => a + x, 0);
  for (let i = 0; rest > 0; i = (i + 1) % q.length, rest--) q[i]++;
  return q;
}
function capChecklist(groups, n) {
  const all = groups.flatMap((g, gi) => g.items.map((it, k) => ({ it, gi, k })));
  if (all.length <= n) return { groups, total: all.length };
  const keep = new Set(all.slice().sort((a, b) => clRank(a.it) - clRank(b.it) || a.gi - b.gi || a.k - b.k).slice(0, n).map((x) => x.it));
  const out = groups.map((g) => ({ ...g, items: g.items.filter((it) => keep.has(it)).sort((a, b) => clRank(a) - clRank(b)) })).filter((g) => g.items.length);
  return { groups: out, total: all.length };
}
function addChecklistGroup(run, title, items) {
  run.checklist = run.checklist || { groups: [] };
  const key = normKey(title);
  let g = run.checklist.groups.find((x) => normKey(x.title) === key);
  if (!g) { g = { title, items: [] }; run.checklist.groups.push(g); }
  for (const it of items) { it.id = 'CL-' + pad(++run.counters.cl); g.items.push(it); }
}
async function stepChecklist(run) {
  sstart(run, 'checklist');
  const types = run.settings.types;
  const reqs = run.requirements.filter((r) => r.inScope);
  const chunks = [];
  for (let i = 0; i < reqs.length; i += 40) chunks.push(reqs.slice(i, i + 40));
  const results = [];
  // строгое число проверок делится между фрагментами пропорционально числу требований в них
  const quotas = strictTarget(run) ? splitQuota(run.settings.target, chunks.map((c) => c.length)) : [];
  await pool(chunks, CONCURRENCY, async (ch, i) => {
    const label = chunks.length > 1 ? `Чек-лист ${i + 1}/${chunks.length}` : 'Чек-лист';
    const line = slog(run, 'checklist', `${label}: модель думает…`);
    try {
      const res = await ask(promptChecklist(run, ch, types, run.settings.depth, quotas[i] || 0), { step: 'checklist',
        onProgress: (n) => { line.text = `${label}: пишет пункты — ${fmtKChars(n)}`; scheduleRender(); },
      });
      results[i] = res;
      const n = arrOf(res?.groups).reduce((a, g) => a + arrOf(g?.items).length, 0);
      line.text = `${label}: ${n} ${plural(n, 'пункт', 'пункта', 'пунктов')}`; line.kind = n ? 'ok' : 'warn';
    } catch (e) { handleCallError(run, e, line, label); }
  }, S.ctl.signal);
  if (S.ctl.signal.aborted) throw abortErr();
  run.checklist = { groups: [] };
  let groups = [];
  for (const res of results) {
    for (const g of arrOf(res?.groups)) {
      const items = arrOf(g?.items).map((it) => normChecklistItem(run, it, types)).filter((it) => it.check && !outOfScope(it.check));
      if (items.length) groups.push({ title: String(g?.title || 'Проверки'), items });
    }
  }
  if (strictTarget(run)) {
    const n = run.settings.target, cap = capChecklist(groups, n);
    groups = cap.groups;
    if (cap.total > n) slog(run, 'checklist', `Чек-лист ограничен числом проверок: ${n} (было ${cap.total}) — сначала самые приоритетные позитивные, затем негативные`, 'ok');
  }
  for (const g of groups) addChecklistGroup(run, g.title, g.items);
  const items = checklistItems(run);
  if (strictTarget(run)) {
    const got = new Set(items.flatMap((i) => i.requirementIds)), gaps = reqs.filter((r) => !got.has(r.id)).map((r) => r.id);
    if (gaps.length && items.length) slog(run, 'checklist', `Строгое число проверок (${run.settings.target}): без пунктов чек-листа остались требования ${gaps.join(', ')}`, 'warn');
    if (items.length < run.settings.target) slog(run, 'checklist', `Модель вернула ${items.length} из ${run.settings.target} проверок — не добавляю пункты сверх ответа модели`, 'warn');
  }
  const smoke = items.filter((i) => i.suites.includes('smoke')).length;
  if (items.length) slog(run, 'checklist', `Итого ${items.length} ${plural(items.length, 'пункт', 'пункта', 'пунктов')} в ${run.checklist.groups.length} ${plural(run.checklist.groups.length, 'группе', 'группах', 'группах')}, смоук: ${smoke}`, 'ok');
  send(run, 'checklist', items.length && results.filter(Boolean).length === chunks.length ? 'done' : 'error');
}
/* оставить не больше n проверок: сначала по одной из каждой группы (покрытие требований), затем остальные по порядку */
// строгое число проверок действует для генерации и сверки; актуализация его не использует
const strictTarget = (run) => !!run.settings.target && run.mode !== 'update';
function capChecks(items, n) {
  const out = items.map((it) => ({ ...it, checks: [] }));
  let left = n;
  items.forEach((it, i) => { if (left > 0 && it.checks.length) { out[i].checks.push(it.checks[0]); left--; } });
  items.forEach((it, i) => { for (let k = 1; k < it.checks.length && left > 0; k++) { out[i].checks.push(it.checks[k]); left--; } });
  return out.filter((it) => it.checks.length);
}
/* Выбраны и чек-лист, и тест-кейсы: кейсы пишутся по пунктам чек-листа — один пункт, один кейс. Номер пункта идёт
   в начале проверки («CL-012 · …»), по нему кейс связывается с пунктом. */
const clCheckText = (i) => `${i.id} · ${i.check}${i.expected ? `. Ожидаемый результат: ${i.expected}` : ''} (приоритет: ${PRIO_RU[normPrio(i.priority)].toLowerCase()}, ${i.kind === 'negative' ? 'негативная' : 'позитивная'})`;
const clIdOf = (check) => (/^(CL-\d+) · /.exec(String(check || '')) || [])[1] || '';
const planFromChecklistOn = (run) => run.mode !== 'update' && !!outputsOf(run).checklist && checklistItems(run).some((i) => i.check);
function planFromChecklist(run, types) {
  sstart(run, 'plan');
  const items = [];
  for (const g of run.checklist.groups) for (const t of TYPES) {
    const its = g.items.filter((i) => i.type === t && i.check);
    if (!its.length) continue;
    if (!types.includes(t)) continue;
    items.push({ type: t, title: g.title, requirementIds: [...new Set(its.flatMap((i) => i.requirementIds))], checks: its.map(clCheckText), fromChecklist: true });
  }
  const n = items.reduce((a, it) => a + it.checks.length, 0);
  // требования, которых нет в чек-листе, — как в обычном плане: по критериям приёмки (при строгом лимите не добавляем)
  const got = new Set(items.flatMap((it) => it.requirementIds));
  const miss = strictTarget(run) ? [] : run.requirements.filter((r) => r.inScope && r.types.some((t) => types.includes(t)) && !got.has(r.id));
  if (miss.length) items.push(...fallbackItems(miss, types));
  items.forEach((it, i) => { it.id = 'P-' + pad(i + 1, 2); });
  run.plan = items; run.coveredExisting = [];
  if (miss.length) slog(run, 'plan', `Нет в чек-листе: ${miss.map((r) => r.id).join(', ')} — добавлены по критериям приёмки`, 'warn');
  const off = checklistItems(run).filter((i) => i.check && !types.includes(i.type)).length;
  slog(run, 'plan', `План — по чек-листу: ${n} ${plural(n, 'пункт', 'пункта', 'пунктов')} → ${n} ${plural(n, 'тест-кейс', 'тест-кейса', 'тест-кейсов')}${off ? `; пропущено пунктов невыбранных видов: ${off}` : ''}`, 'ok');
  for (const t of types) {
    const g = items.filter((x) => x.type === t);
    if (g.length) slog(run, 'plan', `${TL[t]}: ${g.reduce((a, x) => a + x.checks.length, 0)} ${plural(g.reduce((a, x) => a + x.checks.length, 0), 'пункт', 'пункта', 'пунктов')} чек-листа`);
  }
  send(run, 'plan');
}
// перегенерация: план — прежние кейсы, по одному на пункт плана (кейс → проверка с названием и ожидаемым результатом)
function planFromRegen(run) {
  sstart(run, 'plan');
  run.plan = run.regenFrom.map((x, i) => ({ id: 'P-' + pad(i + 1, 2), type: x.type, title: x.title.slice(0, 140), requirementIds: x.reqs.filter((id) => run.reqById[id]),
    checks: [`${x.cl ? x.cl + ' · ' : ''}${x.title}${x.exp ? `. Ожидаемый результат: ${x.exp}` : ''}`], regen: true }));
  run.coveredExisting = [];
  const n = run.plan.length;
  slog(run, 'plan', `Перегенерация того же набора: ${n} ${plural(n, 'кейс', 'кейса', 'кейсов')} — каждый переписывается по текущим правилам и шаблонам`, 'ok');
  for (const t of TYPES) { const k = run.plan.filter((p) => p.type === t).length; if (k) slog(run, 'plan', `${TL[t]}: ${k}`); }
  send(run, 'plan');
}
// строгое число тестов: проверки плана, по которым модель не вернула кейс (или пачка упала), дописываются — до числа проверок
async function strictTopUp(run) {
  const plan = run.plan.filter((p) => p.id.startsWith('P-'));
  const want = Math.min(run.settings.target, plan.reduce((a, p) => a + p.checks.length, 0));
  for (let k = 0; k < 2 && run.cases.length < want; k++) {
    // пункты плана, по которым кейсов меньше, чем проверок в пункте (модель пропустила проверку или пачка упала)
    const miss = plan.filter((p) => run.cases.filter((c) => c.planItem === p.id).length < p.checks.length);
    if (!miss.length) break;
    const ids = new Set(miss.map((p) => p.id));
    slog(run, 'coverage', `Кейсов ${run.cases.length} из ${want}: дописываю пункты плана, где модель вернула меньше кейсов — ${miss.length}`, 'warn');
    run.doneKeys = (run.doneKeys || []).filter((key) => !ids.has(key.split('#')[0]));
    run.failed = run.failed.filter((f) => !f.batch?.items?.some((it) => ids.has(it.id)));
    await generateItems(run, miss, 'coverage');
  }
  const n = run.cases.length;
  if (n < want) slog(run, 'coverage', `Кейсов ${n} из ${want}: модель не вернула ${want - n} — нажмите «Продолжить с места остановки»`, 'warn');
}
// перегенерация: кейсы, которых модель не вернула, дописываются — число кейсов как было
async function regenTopUp(run) {
  sstart(run, 'coverage');
  const want = run.plan.filter((p) => p.regen).length;
  for (let k = 0; k < 2; k++) {
    const miss = run.plan.filter((p) => p.regen && !run.cases.some((c) => c.planItem === p.id));
    if (!miss.length) break;
    slog(run, 'coverage', `Модель не вернула ${miss.length} ${plural(miss.length, 'кейс', 'кейса', 'кейсов')} — дописываю`, 'warn');
    const ids = new Set(miss.map((p) => p.id));
    run.doneKeys = (run.doneKeys || []).filter((key) => !ids.has(key.split('#')[0]));
    run.doneChecks = (run.doneChecks || []).filter((key) => !ids.has(key.split('#')[0]));
    run.failed = run.failed.filter((f) => !f.batch?.items?.some((it) => ids.has(it.id)));
    await generateItems(run, miss, 'coverage');
  }
  const n = run.cases.length;
  slog(run, 'coverage', n >= want ? `Кейсов столько же, сколько было: ${want}` : `Кейсов ${n} из ${want}: модель не вернула ${want - n} — нажмите «Продолжить с места остановки»`, n >= want ? 'ok' : 'warn');
  send(run, 'coverage', n >= want ? 'done' : 'error');
  if (n >= want) delete run.regenFrom;
}
async function stepPlan(run, types) {
  if (run.regenFrom?.length) return planFromRegen(run);
  if (planFromChecklistOn(run)) return planFromChecklist(run, types);
  sstart(run, 'plan');
  if (run.mode !== 'update' && outputsOf(run).checklist) slog(run, 'plan', 'Чек-лист пуст — план составлен по требованиям', 'warn');
  const reqs = run.mode === 'update' ? uncovered(run) : run.requirements.filter((r) => r.inScope);
  if (run.mode === 'update' && !reqs.length) {
    run.plan = []; run.coveredExisting = [];
    slog(run, 'plan', 'Все требования покрыты актуализированными кейсами — новые не нужны', 'ok');
    send(run, 'plan'); return;
  }
  if (run.mode === 'update') slog(run, 'plan', `Не покрыты кейсами из файла: ${reqs.map((r) => r.id).join(', ')}`);
  const reqSet = new Set(reqs.map((r) => r.id));
  const line = slog(run, 'plan', 'Составляю план проверок…');
  let res = null;
  try {
    res = await ask(promptPlan(run, reqs, types, run.settings.depth), { step: 'plan',
      onProgress: (n) => { line.text = `Пишет план — ${fmtKChars(n)}`; scheduleRender(); },
    });
    line.text = 'План получен'; line.kind = 'ok';
  } catch (e) {
    handleCallError(run, e, line, 'План');
    if (S.ctl.signal.aborted) throw abortErr();
  }
  const items = arrOf(res?.items).map((it) => ({
    type: String(it?.type || '').toLowerCase(), title: String(it?.title || 'Группа проверок'),
    requirementIds: arrStr(it?.requirementIds).filter((id) => run.reqById[id] && reqSet.has(id)), checks: arrStr(it?.checks),
  })).map((it) => ({ ...it, checks: it.checks.filter((c) => !outOfScope(c)) })).filter((it) => types.includes(it.type) && it.checks.length && it.requirementIds.length && !SCOPE_RX_EXPL.test(it.title));
  const dropped = arrOf(res?.items).reduce((a, it) => a + arrStr(it?.checks).filter(outOfScope).length, 0);
  if (dropped) slog(run, 'plan', `Убрано проверок вне объёма (исследовательские, только на БД или ручная подготовка данных в БД): ${dropped}`, 'warn');
  const exIds = new Set((knowOf(run)?.cases || []).filter((x) => x.r !== run.id).map((x) => x.i));
  run.coveredExisting = arrOf(res?.alreadyCovered).map((a) => ({ requirementId: String(a?.requirementId || ''), caseIds: arrStr(a?.caseIds).filter((id) => exIds.has(id)) }))
    .filter((a) => run.reqById[a.requirementId] && a.caseIds.length && !items.some((it) => it.requirementIds.includes(a.requirementId)));
  if (run.coveredExisting.length) slog(run, 'plan', `Уже покрыто кейсами продукта, новые не нужны: ${run.coveredExisting.map((a) => `${a.requirementId} (${a.caseIds.join(', ')})`).join('; ')}`, 'ok');
  const covered = new Set([...items.flatMap((it) => it.requirementIds), ...run.coveredExisting.map((a) => a.requirementId)]);
  const miss = reqs.filter((r) => !covered.has(r.id));
  if (miss.length) {
    if (items.length) slog(run, 'plan', `Не попали в план: ${miss.map((r) => r.id).join(', ')} — добавлены по критериям`, 'warn');
    else slog(run, 'plan', 'План построен по критериям приёмки требований', 'warn');
    items.push(...fallbackItems(miss, run.settings.types));
  }
  const target = strictTarget(run) ? run.settings.target : null;
  if (target) {
    const kept = capChecks(items, target), total = items.reduce((a, it) => a + it.checks.length, 0);
    if (kept.length !== items.length || kept.reduce((a, it) => a + it.checks.length, 0) !== total) slog(run, 'plan', `План ограничен числом проверок: ${target} (было ${total})`, 'ok');
    items.splice(0, items.length, ...kept);
  }
  items.forEach((it, i) => { it.id = 'P-' + pad(i + 1, 2); });
  run.plan = items;
  for (const t of types) {
    const g = items.filter((x) => x.type === t);
    if (g.length) slog(run, 'plan', `${TL[t]}: ${g.length} ${plural(g.length, 'группа', 'группы', 'групп')}, ${g.reduce((a, x) => a + x.checks.length, 0)} проверок`);
  }
  send(run, 'plan');
}
/* актуализация: сверка кейсов из файла с требованиями */
const MAP_BATCH = 10;
/* Ответ модели по пакету кейсов → кейс пакета. Модель иногда нумерует кейсы заново с 1 вместо номеров из заголовков («### #11»).
   Сопоставляем по номеру из заголовка, затем по порядковому номеру в пакете, затем по позиции (если кейсов вернули поровну).
   Один ответ достаётся только одному кейсу. */
function matchBatch(items, arr) {
  const list = arrOf(arr).filter((x) => x && typeof x === 'object');
  const byNum = new Map();
  for (const x of list) if (!byNum.has(Number(x.index))) byNum.set(Number(x.index), x);   // при повторе номера берём первый ответ, как раньше
  const hitAbs = items.filter((sc) => byNum.has(sc.index)).length, hitRel = items.filter((_, k) => byNum.has(k + 1)).length;
  const used = new Set();
  const take = (x) => { if (!x || used.has(x)) return null; used.add(x); return x; };
  const found = items.map((sc, k) => take(hitAbs >= hitRel ? byNum.get(sc.index) : byNum.get(k + 1)));
  const claimed = (x) => items.some((sc, j) => Number(x.index) === (hitAbs >= hitRel ? sc.index : j + 1));   // ответ с номером другого кейса по позиции не раздаём
  return found.map((r, k) => r || (list.length === items.length && list[k] && !claimed(list[k]) ? take(list[k]) : null));
}
async function stepMap(run) {
  sstart(run, 'map');
  const todo = run.srcCases.filter((c) => !c.mapped);
  const batches = [];
  for (let i = 0; i < todo.length; i += MAP_BATCH) batches.push(todo.slice(i, i + MAP_BATCH));
  if (batches.length) slog(run, 'map', `${todo.length} ${plural(todo.length, 'кейс', 'кейса', 'кейсов')} — ${batches.length} ${plural(batches.length, 'запрос', 'запроса', 'запросов')} к модели`);
  run.failed = run.failed.filter((f) => f.step !== 'map');
  await pool(batches, CONCURRENCY, async (b) => {
    const label = `Кейсы #${b[0].index}–${b[b.length - 1].index}`;
    const line = slog(run, 'map', `${label}: модель сверяет с ТЗ…`);
    try {
      const res = await ask(promptMap(run, b), { step: 'map', tier: auxTier(), cache: false, onProgress: (n) => { line.text = `${label}: пишет оценку — ${fmtKChars(n)}`; scheduleRender(); } });
      const rs = matchBatch(b, res?.cases);
      for (const [k, sc] of b.entries()) {
        const r = rs[k];
        const st = String(r?.status || '').toLowerCase();
        const ty = String(r?.type || '').toLowerCase();
        sc.type = TYPES.includes(ty) ? ty : sc.typeHint || 'ui';
        sc.reqIds = arrStr(r?.requirementIds).filter((id) => run.reqById[id]);
        sc.status = r ? (st === 'changed' || st === 'obsolete' ? st : 'same') : 'same';
        sc.reason = r ? String(r.reason || '').trim() : 'Агент не дал оценку — кейс перенесён без изменений';
        sc.instruction = sc.status === 'changed' ? String(r?.instruction || '').trim() : '';
        sc.mapped = true;
      }
      const n = (k) => b.filter((x) => x.status === k).length;
      line.text = `${label}: без изменений ${n('same')}, исправить ${n('changed')}, устарело ${n('obsolete')}`; line.kind = 'ok';
      markDirty(run);
    } catch (e) {
      handleCallError(run, e, line, label);
      if (e?.code !== 'cancelled' && !run.fatal) run.failed.push({ kind: 'src', step: 'map', batch: { items: [] }, error: errText(e) });
    }
    scheduleRender();
  }, S.ctl.signal);
  if (S.ctl.signal.aborted) throw abortErr();
  const all = run.srcCases, n = (k) => all.filter((x) => x.mapped && x.status === k).length;
  slog(run, 'map', `Итого: без изменений ${n('same')}, нужно исправить ${n('changed')}, устарело ${n('obsolete')}${srcPending(run, 'mapped') ? `; не сверено ${all.filter((x) => !x.mapped).length} — можно продолжить` : ''}`, srcPending(run, 'mapped') ? 'warn' : 'ok');
  send(run, 'map', srcPending(run, 'mapped') ? 'error' : 'done');
}
/* актуализация: перенос в шаблоны команды и исправление по ТЗ */
async function stepActualize(run) {
  sstart(run, 'actualize');
  const lim = { api: 5, ui: 5, e2e: 3 };
  const batches = [];
  for (const t of TYPES) {
    const list = run.srcCases.filter((c) => c.mapped && !c.done && c.type === t);
    for (let i = 0; i < list.length; i += lim[t]) batches.push({ type: t, items: list.slice(i, i + lim[t]) });
  }
  const total = batches.reduce((a, b) => a + b.items.length, 0);
  if (batches.length) slog(run, 'actualize', `${total} ${plural(total, 'кейс', 'кейса', 'кейсов')} по шаблонам ${[...new Set(batches.map((b) => TL[b.type]))].join(', ')} — ${batches.length} ${plural(batches.length, 'запрос', 'запроса', 'запросов')}`);
  run.failed = run.failed.filter((f) => f.step !== 'actualize');
  const takenSrc = new Set(run.cases.map((c) => c.dispId));
  await pool(batches, CONCURRENCY, async (b) => {
    const label = `${TL[b.type]} · #${b.items.map((x) => x.index).join(', #')}`;
    const line = slog(run, 'actualize', `${label}: модель переписывает…`);
    try {
      const res = await ask(promptActualize(run, b.type, b.items), { step: 'actualize', cache: false, onProgress: (n) => { line.text = `${label}: пишет кейсы — ${fmtKChars(n)}`; scheduleRender(); } });
      const info = tplInfo(b.type);
      const rs = matchBatch(b.items, res?.cases);
      let ok = 0;
      for (const [k, sc] of b.items.entries()) {
        const r = rs[k];
        let tc = r?.testCase && typeof r.testCase === 'object' && !Array.isArray(r.testCase) ? r.testCase : null;
        if (!tc) continue;
        let dispId = sc.srcId && !takenSrc.has(sc.srcId) ? sc.srcId : '';
        if (!dispId) dispId = sc.srcId ? `${sc.srcId}-${sc.index}` : nextDispId(run, b.type);
        takenSrc.add(dispId);
        if (info.ok && info.idField) tc[info.idField] = dispId;
        tc = orderLikeTemplate(tc, info, b.type);
        run.cases.push({
          uid: rid('c'), type: b.type, planItem: 'SRC', requirementIds: sc.reqIds.slice(), suites: withCritical(tc.priority, normSuites(r.suites)), testCase: tc, dispId,
          status: sc.status, note: sc.reason, changes: sc.status === 'changed' ? arrStr(r.changes).slice(0, 8) : [], srcIdx: sc.index, sourceId: sc.srcId || null,
        });
        sc.done = true; ok++;
      }
      line.text = `${label}: готово ${ok} из ${b.items.length}`; line.kind = ok === b.items.length ? 'ok' : 'warn';
      if (ok < b.items.length) run.failed.push({ kind: 'src', step: 'actualize', batch: { items: [] }, error: 'Модель вернула не все кейсы' });
      S.pendingCasesRender = true; markDirty(run);
    } catch (e) {
      handleCallError(run, e, line, label);
      if (e?.code !== 'cancelled' && !run.fatal) run.failed.push({ kind: 'src', step: 'actualize', batch: { items: [] }, error: errText(e) });
    }
    scheduleRender();
  }, S.ctl.signal);
  if (S.ctl.signal.aborted) throw abortErr();
  // кейсы из файла — в исходном порядке, новые — следом
  run.cases.sort((a, b) => (a.srcIdx ?? 1e9) - (b.srcIdx ?? 1e9));
  const left = run.srcCases.filter((c) => !c.done).length;
  slog(run, 'actualize', left ? `Не переписано: ${left} — можно продолжить с места остановки` : `Все ${run.srcCases.length} ${plural(run.srcCases.length, 'кейс', 'кейса', 'кейсов')} из файла переписаны по шаблонам`, left ? 'warn' : 'ok');
  send(run, 'actualize', left ? 'error' : 'done');
}
function fallbackItems(reqs, types) {
  return reqs.map((r) => ({
    type: r.types.find((t) => types.includes(t)) || types[0],
    title: 'Дополнительно: ' + r.title,
    requirementIds: [r.id],
    checks: r.criteria.filter((c) => !outOfScope(c)).length ? r.criteria.filter((c) => !outOfScope(c)).slice(0, 6).map((c) => `Проверить: ${c}`) : [`Позитивная проверка: ${r.title}`, `Негативная проверка: ${r.title}`],
  }));
}
function genMode() {
  const total = docsFor(S.run).reduce((a, d) => a + d.chars, 0);
  const small = total > 0 && total <= SMALL_DOCS;
  // инструменты поиска дорогие (каждое обращение пересылает весь запрос), поэтому только для больших документов и не в экономном режиме
  return { small, tools: !economy() && total > FULLDOC_LIMIT && S.settings.agentTools && toolsAvailable(S.run?.settings.genAI || S.settings.genAI) };
}
async function generateItems(run, items, stepId) {
  const batches = makeBatches(items, new Set(run.doneKeys || []), new Set(run.doneChecks || []));
  if (!batches.length) return;
  const mode = genMode();
  if (!docsFor(run).length) slog(run, stepId, 'Документы недоступны — детали берутся из цитат и критериев требований', 'warn');
  slog(run, stepId, `${batches.length} ${plural(batches.length, 'запрос', 'запроса', 'запросов')} к модели, до ${CONCURRENCY} одновременно`);
  slog(run, stepId, mode.small ? 'Документы небольшие — модель видит их целиком'
    : mode.tools ? 'Модель получает фрагменты документов по теме и может искать остальное сама' : 'Модель получает фрагменты документов по теме каждой группы проверок');
  await pool(batches, CONCURRENCY, (b) => genBatch(run, b, stepId, mode), S.ctl.signal);
  if (S.ctl.signal.aborted) throw abortErr();
}
/* пачка кейсов делится пополам, пока ответ не уместится: длинные кейсы (тела запросов, много шагов) обрезают JSON */
const GEN_SPLITTABLE = new Set(['invalid_json', 'empty_completion', 'output_too_long', 'max_tokens']);
function splitBatch(b) {
  if (b.items.length > 1) { const k = Math.ceil(b.items.length / 2); return [{ ...b, items: b.items.slice(0, k) }, { ...b, items: b.items.slice(k) }]; }
  const it = b.items[0];
  if (!it || it.checks.length < 2) return null;
  const k = Math.ceil(it.checks.length / 2);
  return [{ ...b, items: [{ ...it, checks: it.checks.slice(0, k) }] }, { ...b, items: [{ ...it, checks: it.checks.slice(k) }] }];
}
/* схема ответа генерации (Anthropic по ключу): приоритет и набор — только допустимые значения, остальное проверяет код */
const CASES_SCHEMA = {
  type: 'object',
  properties: {
    cases: { type: 'array', items: { type: 'object', properties: {
      planItem: { type: 'string' },
      requirementIds: { type: 'array', items: { type: 'string' } },
      suites: { type: 'array', items: { type: 'string', enum: ['smoke', 'regression'] } },
      testCase: { type: 'object', properties: { title: { type: 'string' }, priority: { type: 'string', enum: PRIOS } }, required: ['title'] },
    }, required: ['testCase'] } },
  },
  required: ['cases'],
};
async function genBatch(run, b, stepId, mode, depth = 0) {
  const label = `${TL[b.type]} · ${[...new Set(b.items.map((i) => i.id))].join(', ')}${depth ? ` (часть, ${b.items.reduce((a, i) => a + i.checks.length, 0)} ${plural(b.items.reduce((a, i) => a + i.checks.length, 0), 'проверка', 'проверки', 'проверок')})` : ''}`;
  const line = slog(run, stepId, `${label}: модель думает…`);
  const useTools = mode.tools;
  const done = () => {
    if (!depth) (run.doneKeys = run.doneKeys || []).push(...b.items.map((p) => p.key));
    else (run.doneChecks = run.doneChecks || []).push(...b.items.flatMap((p) => p.checks.map((c) => p.key + '|' + c)));
    markDirty(run);
  };
  try {
    const res = await ask(promptGenerate(run, b, { tools: useTools }), { step: stepId,
      tools: useTools ? makeTools(run, stepId) : undefined, cache: false, schema: useTools ? undefined : CASES_SCHEMA,
      onProgress: (n) => { line.text = `${label}: пишет кейсы — ${fmtKChars(n)}`; scheduleRender(); },
    });
    const added = acceptCases(run, b, res);
    line.text = `${label}: ${added} ${plural(added, 'кейс', 'кейса', 'кейсов')}`; line.kind = added ? 'ok' : 'warn';
    if (!added) { if (!depth) run.failed.push({ batch: b, error: 'Модель не вернула ни одного кейса' }); }
    else done();
    S.pendingCasesRender = true;
    scheduleRender();
    return added > 0;
  } catch (e) {
    if (e?.code === 'tools_unavailable') {
      line.text = `${label}: поиск недоступен — повтор без него`; line.kind = 'warn';
      return genBatch(run, b, stepId, { ...mode, tools: false }, depth);
    }
    // ответ не уместился (обрезанный JSON) — делим пачку пополам и пишем по частям
    const halves = GEN_SPLITTABLE.has(e?.code) && depth < 4 ? splitBatch(b) : null;
    if (halves && !S.ctl?.signal.aborted) {
      line.text = `${label}: ответ не уместился — пишу по частям (${halves.length})`; line.kind = 'warn'; scheduleRender();
      let ok = true;
      for (const h of halves) if (!(await genBatch(run, h, stepId, mode, depth + 1))) ok = false;
      if (ok && !depth) { run.doneKeys = run.doneKeys || []; run.doneKeys.push(...b.items.map((p) => p.key)); markDirty(run); }
      if (!ok && !depth && !run.fatal && !S.ctl?.signal.aborted) run.failed.push({ batch: b, error: 'Часть кейсов не получилась: ' + errText(e) + ' Повтор допишет только недостающие проверки.' });
      scheduleRender();
      return ok;
    }
    handleCallError(run, e, line, label);
    if (!depth && e?.code !== 'cancelled' && !run.fatal) run.failed.push({ batch: b, error: errText(e) });
    scheduleRender();
    return false;
  }
}
async function stepCoverage(run) {
  sstart(run, 'coverage');
  const existing = run.plan.filter((p) => p.id.startsWith('G-'));
  let gaps = uncovered(run);
  if (existing.length) {
    if (pendingParts(run, 'G-')) { slog(run, 'coverage', 'Дописываю кейсы для оставшихся требований'); await generateItems(run, existing, 'coverage'); }
  } else if (gaps.length && strictTarget(run)) {
    // строгое число: дополнительные проверки не добавляем, требования без кейсов только называем
    slog(run, 'coverage', `Строгое число проверок (${run.settings.target}): без кейсов остались требования ${gaps.map((r) => r.id).join(', ')}. Увеличьте число тестов или сгенерируйте недостающие отдельно`, 'warn');
    run.coverageGaps = gaps.map((r) => ({ requirementId: r.id, type: '', checks: [] }));
  } else if (gaps.length) {
    slog(run, 'coverage', `Без кейсов: ${gaps.map((r) => r.id).join(', ')} — дописываю`, 'warn');
    const items = fallbackItems(gaps, run.settings.types);
    items.forEach((it, i) => { it.id = 'G-' + pad(i + 1, 2); });
    run.plan.push(...items);
    await generateItems(run, items, 'coverage');
  }
  // покрытие по критериям: модель сверяет кейсы с критериями каждого требования и называет непроверенное
  if (outputsOf(run).cases && !run.auditDone) await coverageAudit(run);
  else if (pendingParts(run, 'C-')) { slog(run, 'coverage', 'Дописываю кейсы для непокрытых критериев'); await generateItems(run, run.plan.filter((p) => p.id.startsWith('C-')), 'coverage'); }
  gaps = uncovered(run);
  run.failed = run.failed.filter((f) => f.kind === 'src' || f.batch.items.some((it) => it.requirementIds.some((id) => !run.cases.some((c) => c.requirementIds.includes(id)))));
  slog(run, 'coverage', gaps.length ? `Остались без кейсов: ${gaps.map((r) => r.id).join(', ')}` : 'Все требования выбранных видов покрыты', gaps.length ? 'warn' : 'ok');
  send(run, 'coverage', gaps.length ? 'error' : 'done');
}
async function coverageAudit(run) {
  const types = run.settings.types || TYPES;
  const reqs = run.requirements.filter((r) => r.inScope && !coveredByProduct(run, r.id));
  if (!reqs.length) { run.auditDone = true; return; }
  // пачки по ~20 требований, чтобы запрос не разрастался
  const packs = [];
  let cur = [], size = 0;
  for (const r of reqs) {
    const n = 300 + r.criteria.join(' ').length + activeCases(run).filter((c) => c.requirementIds.includes(r.id)).length * 160;
    if (cur.length && (cur.length >= 20 || size + n > 16000)) { packs.push(cur); cur = []; size = 0; }
    cur.push(r); size += n;
  }
  if (cur.length) packs.push(cur);
  slog(run, 'coverage', `Сверяю покрытие критериев: ${reqs.length} ${plural(reqs.length, 'требование', 'требования', 'требований')}, ${packs.length} ${plural(packs.length, 'запрос', 'запроса', 'запросов')}`);
  const found = [];
  let ok = 0;
  await pool(packs, CONCURRENCY, async (pk, k) => {
    const label = packs.length > 1 ? `Сверка ${k + 1}/${packs.length}` : 'Сверка покрытия';
    const line = slog(run, 'coverage', `${label}: модель сверяет кейсы с критериями…`);
    try {
      const res = await ask(promptCoverageAudit(run, pk, types), { step: 'coverage', stage: 'aux', onProgress: (n) => { line.text = `${label}: пишет — ${fmtKChars(n)}`; scheduleRender(); } });
      const ids = new Set(pk.map((r) => r.id));
      const g = arrOf(res?.gaps).map((x) => ({ requirementId: String(x?.requirementId || ''), type: String(x?.type || '').toLowerCase(), checks: arrStr(x?.checks).filter((c) => !outOfScope(c)) }))
        .filter((x) => ids.has(x.requirementId) && x.checks.length);
      found.push(...g); ok++;
      const nc = g.reduce((a, x) => a + x.checks.length, 0);
      line.text = `${label}: ${nc ? `непокрытых проверок ${nc} в ${g.length} ${plural(g.length, 'требовании', 'требованиях', 'требованиях')}` : 'все критерии покрыты'}`; line.kind = nc ? 'warn' : 'ok';
    } catch (e) { handleCallError(run, e, line, label); }
    scheduleRender();
  }, S.ctl.signal);
  if (S.ctl.signal.aborted) throw abortErr();
  if (ok === packs.length) run.auditDone = true;
  if (!found.length) { if (ok) slog(run, 'coverage', 'Критерии всех требований покрыты кейсами', 'ok'); return; }
  // строгое число тестов: сверка не добавляет кейсы, а предупреждает о требованиях без проверок
  if (strictTarget(run)) {
    const gaps = [...new Set(found.map((x) => x.requirementId))];
    slog(run, 'coverage', `Строгое число проверок (${run.settings.target}): без проверок остались требования ${gaps.join(', ')}. Увеличьте число тестов или сгенерируйте недостающие отдельно`, 'warn');
    run.coverageGaps = found;
    return;
  }
  const items = [];
  for (const x of found) {
    const r = run.reqById[x.requirementId];
    const type = types.includes(x.type) ? x.type : (r.types.find((t) => types.includes(t)) || types[0]);
    items.push({ type, title: 'Покрытие критериев: ' + r.title, requirementIds: [r.id], checks: [...new Set(x.checks)].slice(0, 8) });
  }
  const base = run.plan.filter((p) => p.id.startsWith('C-')).length;
  items.forEach((it, i) => { it.id = 'C-' + pad(base + i + 1, 2); });
  run.plan.push(...items); markDirty(run);
  const nc = items.reduce((a, it) => a + it.checks.length, 0);
  slog(run, 'coverage', `Дописываю ${nc} ${plural(nc, 'кейс', 'кейса', 'кейсов')} для непокрытых критериев`, 'warn');
  await generateItems(run, items, 'coverage');
}
/* дополнительные задачи над готовым запуском: повтор, чек-лист, учёт ответов */
async function runTask(stepId, fn, role = 'gen') {
  const run = S.run;
  if (S.running || !run) return;
  const v = role === 'review' ? aiValue('review') : (run.settings.genAI || S.settings.genAI);
  if (role !== 'none' && !aiReady(v)) return toast(aiProblem(v), 'err');
  S.ctl = new AbortController(); S.running = true;
  run.status = 'running'; run.error = null; run.fatal = null; run.finishedAt = null; run.taskStart = Date.now(); run.fromHistory = false; run.interrupted = null;
  sstart(run, stepId);
  renderAll(); startTicker(); startHeartbeat(run);
  try {
    await fn(run);
    run.status = run.failed.length ? 'partial' : 'done';
  } catch (e) {
    if (run.fatal) { run.status = 'error'; run.error = run.fatal; markRunning(run, 'error'); }
    else if (S.ctl.signal.aborted) { run.status = 'stopped'; markRunning(run, 'stopped'); }
    else { run.status = 'error'; run.error = errText(e); markRunning(run, 'error', run.error); }
  } finally {
    run.finishedAt = Date.now(); S.running = false; stopTicker(); stopHeartbeat(); renderAll();
    if (S.caps.db && S.caps.uid) saveChain = saveChain.then(() => saveRun(run)).catch(() => {});
    saveChain = saveChain.then(() => flushSessionNow()).then(() => productSync(run));
  }
}
function retryFailed() { resumeRun(); }
function generateChecklistNow() {
  S.tab = 'checklist';
  runTask('checklist', async (run) => {
    run.steps.checklist.log = [];
    run.settings.outputs = { ...outputsOf(run), checklist: true };
    run.counters.cl = run.baseCounters?.cl || 0;
    await stepChecklist(run);
  });
}
async function refineCaseCore(run, c, comment, signal) {
  const res = await ask(promptRefine(run, c, comment), { step: 'refine', cache: false, signal });
  const tc = res && typeof res === 'object' && !Array.isArray(res) ? (res.testCase && typeof res.testCase === 'object' ? res.testCase : res) : null;
  if (!tc) throw new Error('Модель вернула не объект тест-кейса.');
  const info = tplInfo(c.type);
  if (info.ok && info.idField) tc[info.idField] = c.dispId;
  const ui = caseUI(c.uid);
  ui.prev = c.testCase; c.testCase = orderLikeTemplate(tc, info, c.type); c.suites = withCritical(c.testCase.priority, c.suites || []);
  touchCase(c, 'Доработано: ' + String(comment).split('\n')[0].slice(0, 160));
}
async function refineCase(c, comment) {
  const ui = caseUI(c.uid);
  if (!aiReady(S.run.settings.genAI || S.settings.genAI)) { ui.error = aiProblem(S.run.settings.genAI || S.settings.genAI); return renderCaseList(); }
  ui.busy = true; ui.error = ''; ui.ctl = new AbortController(); renderCaseList();
  try {
    await refineCaseCore(S.run, c, comment, ui.ctl.signal);
    ui.mode = 'view'; ui.comment = ''; ui.note = 'Кейс доработан.';
    queueSave(S.run);
    learnFromRemark('тест-кейс', `${c.dispId} (${TL[c.type]}): ${pickTitleText(c.testCase)}`, comment);
  } catch (e) {
    ui.error = e?.code === 'cancelled' ? '' : errText(e);
  } finally { ui.busy = false; renderCaseList(); }
}
function applyAnswers() {
  const run = S.run;
  const qs = (run?.questions || []).filter((q) => qStatus(q) === 'pending');
  if (!qs.length) return;
  runTask('answers', async (run) => {
    slog(run, 'answers', `Ответы: ${qs.map((q) => q.id).join(', ')}`);
    const line = slog(run, 'answers', 'Анализирую, что меняют ответы…');
    let res;
    try {
      res = await ask(promptImpact(run, qs), { step: 'answers', cache: false, onProgress: (n) => { line.text = `Анализ влияния — ${fmtKChars(n)}`; scheduleRender(); } });
    } catch (e) { handleCallError(run, e, line, 'Анализ влияния'); throw e; }
    let nCrit = 0;
    for (const c of arrOf(res?.criteria)) {
      const r = run.reqById[String(c?.requirementId || '')];
      if (!r) continue;
      for (const a of arrStr(c.add)) if (!r.criteria.includes(a)) { r.criteria.push(a); nCrit++; }
    }
    const updates = arrOf(res?.update).map((u) => ({ c: run.cases.find((x) => x.dispId === String(u?.caseId || '')), instruction: String(u?.instruction || '').trim() })).filter((u) => u.c && u.instruction);
    const adds = arrOf(res?.add).map((a) => ({ type: String(a?.type || '').toLowerCase(), requirementIds: arrStr(a?.requirementIds).filter((id) => run.reqById[id]), check: String(a?.check || '').trim(), suites: normSuites(a?.suites) }))
      .filter((a) => a.check && (run.settings.types || TYPES).includes(a.type));
    const clUpd = arrOf(res?.checklistUpdate).map((u) => ({ item: checklistItems(run).find((i) => i.id === String(u?.itemId || '')), check: String(u?.check || '').trim() })).filter((u) => u.item && u.check);
    line.text = `Критериев добавлено: ${nCrit}; кейсов исправить: ${updates.length}; новых проверок: ${adds.length}${run.checklist ? `; пунктов чек-листа изменить: ${clUpd.length}` : ''}`; line.kind = 'ok';
    if (updates.length) await reviseCases(run, updates);
    if (adds.length && (outputsOf(run).cases || run.cases.length)) {
      const groups = new Map();
      for (const a of adds) { const k = a.type + '|' + a.requirementIds.join(','); if (!groups.has(k)) groups.set(k, { type: a.type, requirementIds: a.requirementIds, checks: [] }); groups.get(k).checks.push(a.check); }
      const items = [...groups.values()].map((g, i) => ({ ...g, id: 'A-' + pad((run.plan.filter((p) => p.id.startsWith('A-')).length) + i + 1, 2), title: 'По ответам на вопросы' }));
      run.plan.push(...items);
      await generateItems(run, items, 'answers');
    }
    if (run.checklist) {
      for (const u of clUpd) u.item.check = u.check;
      if (adds.length) addChecklistGroup(run, 'Уточнения по ответам на вопросы', adds.map((a) => ({ id: '', check: a.check, type: a.type, priority: 'P2_MEDIUM', suites: a.suites, requirementIds: a.requirementIds })));
    }
    for (const q of qs) q.appliedAnswer = q.answer.trim();
    slog(run, 'answers', `Ответы учтены: ${qs.map((q) => q.id).join(', ')}`, 'ok');
    send(run, 'answers', run.failed.length ? 'error' : 'done');
    toast('Ответы учтены в тест-кейсах');
    if (run.productId) await stepKnowledge(run);
  });
}
/* строгий режим: нарушения правил, которые код не исправил, — запросом к модели по кейсам; один проход, потом проверка снова */
async function repairRules(run) {
  const ups = [];
  for (const c of activeCases(run)) {
    applyRuleFixes(c);
    const v = ruleViolations(c);
    if (v.length) ups.push({ c, instruction: 'Исправь по правилам команды, сохранив остальное: ' + v.map((x) => x.text).join(' ') });
  }
  if (!ups.length) return 0;
  slog(run, 'review', `Строгий режим: исправляю нарушения правил в кейсах ${ups.map((u) => u.c.dispId).join(', ')}`, 'warn');
  await reviseCases(run, ups);
  let left = 0;
  for (const c of activeCases(run)) { applyRuleFixes(c); left += ruleViolations(c).length; }
  slog(run, 'review', left ? `После исправления осталось нарушений: ${left}` : 'После исправления нарушений правил не осталось', left ? 'warn' : 'ok');
  return left;
}
async function reviseCases(run, updates) {
  const batches = [];
  for (const t of TYPES) {
    const ups = updates.filter((u) => u.c.type === t);
    for (let i = 0; i < ups.length; i += 4) batches.push({ type: t, ups: ups.slice(i, i + 4) });
  }
  await pool(batches, CONCURRENCY, async (b) => {
    const label = `Исправление ${b.ups.map((u) => u.c.dispId).join(', ')}`;
    const line = slog(run, 'answers', `${label}: модель думает…`);
    try {
      const res = await ask(promptReviseBatch(run, b.type, b.ups), { step: 'answers', cache: false, onProgress: (n) => { line.text = `${label}: ${fmtKChars(n)}`; scheduleRender(); } });
      const info = tplInfo(b.type);
      let n = 0;
      for (const r of arrOf(res?.cases)) {
        const u = b.ups.find((x) => x.c.dispId === String(r?.caseId || '')) || (b.ups.length === 1 ? b.ups[0] : null);
        const tc = r?.testCase && typeof r.testCase === 'object' && !Array.isArray(r.testCase) ? r.testCase : null;
        if (!u || !tc) continue;
        if (info.ok && info.idField) tc[info.idField] = u.c.dispId;
        const ui = caseUI(u.c.uid);
        ui.prev = u.c.testCase; ui.note = 'Исправлено по ответам на вопросы: ' + u.instruction;
        u.c.testCase = orderLikeTemplate(tc, info, b.type);
        touchCase(u.c, 'По ответу аналитика: ' + u.instruction.slice(0, 160));
        if (r.suites !== undefined) u.c.suites = normSuites(r.suites);
        u.c.suites = withCritical(u.c.testCase.priority, u.c.suites || []);
        n++;
      }
      line.text = `${label}: исправлено ${n}`; line.kind = n ? 'ok' : 'warn';
    } catch (e) { handleCallError(run, e, line, label); }
  }, S.ctl.signal);
  if (S.ctl.signal.aborted) throw abortErr();
}

/* ================= export ================= */
function buildDefaultExport(run) {
  const by = (t) => run.cases.filter((c) => c.type === t).map((c) => c.testCase);
  return {
    generatedAt: new Date(run.createdAt).toISOString(),
    sources: run.docs.map((d) => d.name),
    testCases: { api: by('api'), ui: by('ui'), e2e: by('e2e') },
    suites: { smoke: run.cases.filter((c) => c.suites?.includes('smoke')).map((c) => c.dispId), regression: run.cases.filter((c) => c.suites?.includes('regression')).map((c) => c.dispId) },
    traceability: run.requirements.filter((r) => r.inScope).map((r) => ({ requirement: r.id, title: r.title, testCases: run.cases.filter((c) => c.requirementIds.includes(r.id)).map((c) => c.dispId) })),
    ...(run.mode === 'update' ? { actualization: {
      source: run.source?.name || '', summary: Object.fromEntries(Object.keys(UPD_ST).map((k) => [k, run.cases.filter((c) => c.status === k).length])),
      cases: run.cases.map((c) => ({ id: c.dispId, sourceId: c.sourceId || null, status: c.status || 'new', statusRu: UPD_ST[c.status || 'new'], reason: c.note || '', changes: c.changes || [] })),
    } } : {}),
  };
}
const EXP_TYPES = ['json', 'csv', 'xlsx', 'xml', 'md', 'txt'];
function normSpec(res) {
  const r = res && typeof res === 'object' ? res : {};
  const fileType = EXP_TYPES.includes(String(r.fileType || '').toLowerCase()) ? String(r.fileType).toLowerCase() : 'json';
  let wrapper = r.wrapper ?? '%%ALL%%';
  if (fileType === 'json' && typeof wrapper === 'string' && wrapper.trim() !== '%%ALL%%') { const p = tryParse(wrapper); if (p.ok) wrapper = p.value; }
  if (fileType !== 'json' && typeof wrapper !== 'string') wrapper = '%%ALL%%';
  const delim = [',', ';', '\t', '|'].includes(r.delimiter) ? r.delimiter : ';';
  return {
    fileType, wrapper, delimiter: delim,
    filename: String(r.filename || 'test-cases').replace(/[^\p{L}\p{N}._-]+/gu, '-').replace(/^-+|-+$/g, '').slice(0, 60) || 'test-cases',
    columns: arrStr(r.columns), separator: typeof r.separator === 'string' ? r.separator : '\n',
    itemRules: String(r.itemRules || ''), notes: String(r.notes || ''),
    mode: r.mode === 'map' ? 'map' : 'ai', rowMode: r.rowMode === 'step' ? 'step' : 'case',
    cols: arrOf(r.cols).filter((c) => c && typeof c === 'object' && typeof c.value === 'string').map((c) => ({ header: String(c.header ?? ''), value: c.value, firstOnly: !!c.firstOnly })),
    item: r.item && typeof r.item === 'object' ? r.item : typeof r.item === 'string' ? r.item : null,
    itemText: typeof r.itemText === 'string' ? r.itemText : null,
  };
}
/* ---------- сборка экспорта без модели: шаблоны полей ---------- */
function tplGet(ctx, path) {
  if (path === '.') return ctx.__this;
  let v = ctx;
  for (const k of path.split('.')) { if (v == null) return undefined; v = v[k]; }
  return v;
}
function tplVal(v, sep = '\n') {
  if (v == null) return '';
  if (Array.isArray(v)) return v.map((x) => (x && typeof x === 'object' ? JSON.stringify(x) : String(x))).join(sep);
  return typeof v === 'object' ? JSON.stringify(v) : String(v);
}
const tplScope = (ctx, x, i) => ({ ...ctx, ...(x && typeof x === 'object' && !Array.isArray(x) ? x : {}), __this: x, n: x?.n ?? i + 1 });
function renderTpl(tpl, ctx) {
  let s = String(tpl ?? '');
  s = s.replace(/\{\{#([\w.]+)\}\}([\s\S]*?)\{\{\/\1\}\}/g, (m, path, inner) => { const arr = tplGet(ctx, path); return Array.isArray(arr) ? arr.map((x, i) => renderTpl(inner, tplScope(ctx, x, i))).join('') : ''; });
  return s.replace(/\{\{\s*([\w.]+)\s*(?:([|=])([^}]*))?\}\}/g, (m, path, op, arg) => {
    const v = tplGet(ctx, path);
    if (op === '=') {
      const map = {};
      for (const pair of arg.split(',')) { const k = pair.indexOf(':'); if (k > 0) map[pair.slice(0, k).trim()] = pair.slice(k + 1); }
      const key = tplVal(v);
      return key in map ? map[key] : key;
    }
    return tplVal(v, op === '|' ? arg.replace(/\\n/g, '\n') : '\n');
  });
}
function renderJSONTpl(t, ctx) {
  if (typeof t === 'string') { const m = /^\{\{\s*([\w.]+)\s*\}\}$/.exec(t); if (m) { const v = tplGet(ctx, m[1]); return v === undefined ? '' : v; } return renderTpl(t, ctx); }
  if (Array.isArray(t)) return t.map((x) => renderJSONTpl(x, ctx));
  if (t && typeof t === 'object') {
    if (typeof t.$each === 'string') { const arr = tplGet(ctx, t.$each); return Array.isArray(arr) ? arr.map((x, i) => renderJSONTpl(t.item ?? '{{.}}', tplScope(ctx, x, i))) : []; }
    const o = {};
    for (const [k, v] of Object.entries(t)) o[k] = renderJSONTpl(v, ctx);
    return o;
  }
  return t;
}
function exportCtx(c) {
  const n = tmsCase(c), tc = c.testCase || {};
  const ek = Object.keys(tc).find((x) => /^(expectedResult|expected_result|ожидаемый_?результат|result)$/i.test(x));
  return {
    id: c.dispId, type: c.type, typeRu: TL[c.type], title: n.title, description: n.description.split('\n\n').filter((x) => !x.startsWith('ID в QA pro:')).join('\n\n'),
    preconditions: n.pre, postconditions: n.post, steps: n.steps.map((st, i) => ({ n: i + 1, action: st.action, expected: st.expected, data: st.data })),
    expectedResult: ek ? tplVal(tc[ek]) : '', priority: n.priority, priorityRu: PRIO_RU[n.priority],
    suites: c.suites || [], suitesRu: (c.suites || []).map((x) => SUITE_RU[x]).join(', '), smoke: c.suites?.includes('smoke') ? 'да' : '', regression: c.suites?.includes('regression') ? 'да' : '',
    tags: n.tags, requirementIds: c.requirementIds, status: c.status || '', statusRu: c.status ? UPD_ST[c.status] : '', reason: c.note || '', changes: c.changes || [], sourceId: c.sourceId || '', tc,
  };
}
const canMapLocally = (spec) => spec.mode === 'map' && ((spec.fileType === 'csv' || spec.fileType === 'xlsx') ? spec.cols.length > 0 : spec.fileType === 'json' ? spec.item != null : typeof spec.itemText === 'string');
function mapCaseLocally(spec, c) {
  const ctx = exportCtx(c);
  if (spec.fileType === 'csv' || spec.fileType === 'xlsx') {
    const steps = spec.rowMode === 'step' && ctx.steps.length ? ctx.steps : [null];
    return steps.map((st, k) => spec.cols.map((col) => (col.firstOnly && k > 0 ? '' : renderTpl(col.value, st ? { ...ctx, step: st } : { ...ctx, step: { n: '', action: '', expected: '', data: '' } }))));
  }
  if (spec.fileType === 'json') return renderJSONTpl(spec.item, ctx);
  return renderTpl(spec.itemText, ctx);
}
const specHash = (spec) => hash(JSON.stringify([spec.fileType, spec.itemRules, spec.columns]));
const itemKey = (fmtH, spec, c) => `${fmtH}:${specHash(spec)}:${hash(JSON.stringify(casePayload(c)))}`;
const exportKey = (run, fmt) => hash(fmt + '|' + JSON.stringify(run.cases.map(casePayload)));
function csvCell(v, d) { const s = v == null ? '' : String(v); return /["\r\n]/.test(s) || s.includes(d) ? '"' + s.replace(/"/g, '""') + '"' : s; }
function assembleExport(spec, run, fmtH) {
  const items = run.cases.map((c) => ({ c, it: S.expCache.get(itemKey(fmtH, spec, c)) }));
  const missing = items.filter((x) => x.it === undefined).map((x) => x.c.dispId);
  const sel = (f) => items.filter((x) => x.it !== undefined && f(x.c)).map((x) => x.it);
  const sets = {
    ALL: sel(() => true), API: sel((c) => c.type === 'api'), UI: sel((c) => c.type === 'ui'), E2E: sel((c) => c.type === 'e2e'),
    SMOKE: sel((c) => c.suites?.includes('smoke')), REGRESSION: sel((c) => c.suites?.includes('regression')),
  };
  const def = buildDefaultExport(run);
  const meta = { GENERATED_AT: def.generatedAt, SOURCES: def.sources, REQUIREMENTS: run.requirements.map((r) => ({ id: r.id, title: r.title })), TRACEABILITY: def.traceability };
  const base = { filename: spec.filename, missing, notes: spec.notes, fileType: spec.fileType };
  if (spec.fileType === 'json') {
    const walk = (v) => {
      if (typeof v === 'string') {
        const m = /^%%([A-Z_0-9]+)%%$/.exec(v.trim());
        if (m && sets[m[1]]) return sets[m[1]];
        if (m && meta[m[1]] !== undefined) return meta[m[1]];
        return v.replace(/%%GENERATED_AT%%/g, meta.GENERATED_AT);
      }
      if (Array.isArray(v)) return v.flatMap((x) => (typeof x === 'string' && /^%%(ALL|API|UI|E2E|SMOKE|REGRESSION)%%$/.test(x.trim()) ? walk(x) : [walk(x)]));
      if (v && typeof v === 'object') { const o = {}; for (const k of Object.keys(v)) o[k] = walk(v[k]); return o; }
      return v;
    };
    return { ...base, kind: 'text', ext: 'json', text: JSON.stringify(walk(spec.wrapper), null, 2) };
  }
  if (spec.fileType === 'csv' || spec.fileType === 'xlsx') {
    const n = spec.columns.length;
    const rows = sets.ALL.flatMap((it) => (!Array.isArray(it) ? [] : it.every(Array.isArray) ? it : [it]))
      .map((r) => { const row = r.map((x) => (x == null ? '' : typeof x === 'object' ? JSON.stringify(x) : String(x))); while (n && row.length < n) row.push(''); return n ? row.slice(0, n) : row; });
    const text = [spec.columns, ...rows].map((r) => r.map((x) => csvCell(x, spec.delimiter)).join(spec.delimiter)).join('\r\n');
    return { ...base, kind: spec.fileType === 'xlsx' ? 'xlsx' : 'text', ext: spec.fileType, columns: spec.columns, rows, text };
  }
  const text = String(spec.wrapper).replace(/%%([A-Z_0-9]+)%%/g, (m, k) => (sets[k] ? sets[k].map(String).join(spec.separator) : meta[k] !== undefined ? (typeof meta[k] === 'string' ? meta[k] : JSON.stringify(meta[k], null, 2)) : m));
  return { ...base, kind: 'text', ext: spec.fileType, text };
}
async function runExport() {
  const run = S.run, fmt = S.cfg.exportFormat.trim();
  if (!run?.cases.length || !fmt || S.exp?.status === 'running') return;
  if (!aiReady(S.settings.genAI)) return toast(aiProblem(S.settings.genAI), 'err');
  const fmtH = hash(fmt);
  const ctl = S.expCtl = new AbortController();
  const prev = S.exp && S.exp.fmtH === fmtH ? S.exp : null;
  const exp = S.exp = { status: 'running', fmtH, key: exportKey(run, fmt), spec: prev?.spec || null, output: prev?.output || null, progress: 'Определяю формат по описанию…', error: '' };
  if (S.tab === 'export') renderTab();
  try {
    if (!exp.spec) exp.spec = normSpec(await ask(promptExportSpec(fmt, run), { step: 'export', signal: ctl.signal }));
    const spec = exp.spec;
    if (canMapLocally(spec)) {
      if ((spec.fileType === 'csv' || spec.fileType === 'xlsx')) spec.columns = spec.cols.map((c) => c.header);
      try {
        for (const c of run.cases) S.expCache.set(itemKey(fmtH, spec, c), mapCaseLocally(spec, c));
        exp.local = true;
      } catch { spec.mode = 'ai'; }
    }
    if ((spec.fileType === 'csv' || spec.fileType === 'xlsx') && !spec.columns.length) throw new Error('Модель не определила колонки файла. Уточните описание формата.');
    const todo = run.cases.filter((c) => !S.expCache.has(itemKey(fmtH, spec, c)));
    const batches = [];
    for (let i = 0; i < todo.length; i += 8) batches.push(todo.slice(i, i + 8));
    let done = run.cases.length - todo.length;
    exp.progress = `Преобразую кейсы: ${done} из ${run.cases.length}`; if (S.tab === 'export') renderTab();
    let failed = 0;
    await pool(batches, CONCURRENCY, async (b) => {
      try {
        const res = await ask(promptExportItems(spec, fmt, b), { step: 'export', cache: false, signal: ctl.signal });
        for (const it of arrOf(res?.items)) {
          const c = b.find((x) => x.dispId === String(it?.caseId || ''));
          if (!c) continue;
          const val = spec.fileType === 'json' ? it.value : (spec.fileType === 'csv' || spec.fileType === 'xlsx') ? (Array.isArray(it.rows) ? it.rows : null) : (typeof it.text === 'string' ? it.text : null);
          if (val === undefined || val === null) continue;
          S.expCache.set(itemKey(fmtH, spec, c), val); done++;
        }
      } catch (e) {
        if (e?.code === 'cancelled') return;
        failed++;
        if (FATAL.has(e?.code)) { exp.error = errText(e); ctl.abort(); }
      }
      exp.progress = `Преобразую кейсы: ${done} из ${run.cases.length}`; if (S.tab === 'export') renderTab();
    }, ctl.signal);
    if (ctl.signal.aborted && !exp.error) { exp.status = prev?.output ? 'done' : 'idle'; exp.output = prev?.output || null; return; }
    if (exp.error) throw new Error(exp.error);
    exp.output = assembleExport(spec, run, fmtH);
    exp.status = 'done';
    if (failed || exp.output.missing.length) exp.error = `Не удалось преобразовать: ${exp.output.missing.join(', ')}. Нажмите «Собрать файл» ещё раз — повторно обработаются только они.`;
  } catch (e) {
    exp.status = 'error'; exp.error = errText(e);
  } finally { if (S.tab === 'export') renderTab(); }
}

/* ================= history: запуски продукта (общие) и личные запуски без продукта ================= */
let saveTimer = null, saveChain = Promise.resolve();
const prodPath = (pid) => `products/${pid}`;
const runBase = (pid) => (pid ? `${prodPath(pid)}/runs` : `data/users/${S.caps.uid}`);
const runPath = (run) => `${runBase(run.productId)}/${run.id}`;
function queueSave(run, delay = 1500) {
  if (!S.caps.db || !S.caps.uid || !run || run.fromHistory === 'readonly' || run.fromHistory === 'follow') return;
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => { saveChain = saveChain.then(() => saveRun(run)).then(() => { if (!S.running) productSync(run); }).catch(() => toast('Не удалось сохранить запуск в историю.', 'err')); }, delay);
}
function packParts(cases) {
  const parts = []; let cur = [], size = 0;
  for (const c of cases) {
    const o = { uid: c.uid, type: c.type, planItem: c.planItem, requirementIds: c.requirementIds, suites: c.suites || [], testCase: c.testCase, dispId: c.dispId, tms: c.tms || null };
    if (c.status) Object.assign(o, { status: c.status, note: c.note || '', changes: c.changes || [], srcIdx: c.srcIdx ?? null, sourceId: c.sourceId || null });
    if (c.revHash) o.revHash = c.revHash;
    const sz = JSON.stringify(o).length * 2;
    if (cur.length && (size + sz > 180000 || cur.length >= 40)) { parts.push(cur); cur = []; size = 0; }
    cur.push(o); size += sz;
  }
  if (cur.length) parts.push(cur);
  return parts;
}
async function saveRun(run) {
  const db = S.caps.db, base = runBase(run.productId);
  const parts = packParts(run.cases);
  const counts = Object.fromEntries(TYPES.map((t) => [t, run.cases.filter((c) => c.type === t).length]));
  counts.checklist = checklistItems(run).length;
  if (run.mode === 'update') counts.upd = Object.fromEntries(Object.keys(UPD_ST).map((k) => [k, run.cases.filter((c) => c.status === k).length]));
  const srcParts = [];
  if (run.mode === 'update') {
    let cur = [], size = 0;
    for (const c of run.srcCases) {
      const sz = JSON.stringify(c).length * 2;
      if (cur.length && (size + sz > 180000 || cur.length >= 60)) { srcParts.push(cur); cur = []; size = 0; }
      cur.push(c); size += sz;
    }
    if (cur.length) srcParts.push(cur);
  }
  let reqs = run.requirements, checklist = run.checklist;
  const meta = () => ({
    kind: 'run', id: run.id, createdAt: run.createdAt, updatedAt: Date.now(), finishedAt: run.finishedAt,
    docs: run.docs, settings: run.settings, requirements: reqs, questions: run.questions, checklist, findings: run.findings ? run.findings.slice(0, 300) : null,
    plan: run.plan.map((p) => ({ id: p.id, type: p.type, title: p.title, requirementIds: p.requirementIds, checks: p.checks })),
    counts, coverage: coveragePct(run), partsCount: parts.length, status: run.status, counters: run.counters, error: run.error || null,
    stage: run.stage || 'added', addedAt: run.addedAt || null, auditDone: !!run.auditDone, reduced: !!run.reduced,
    doneKeys: run.doneKeys || [], doneChecks: run.doneChecks || [], taskStart: run.taskStart || null, qaCtx: run.qaCtx || null, usage: run.usage || null,
    productId: run.productId || null, docIds: run.docIds || null, coveredExisting: run.coveredExisting || [], baseCounters: run.baseCounters || null, by: run.by || '', failedInfo: run.failed.length ? failedInfo(run).slice(0, 40).map((f) => ({ ...f, error: f.error.slice(0, 500) })) : null,
    hb: S.running && !S.unloading && run === S.run ? Date.now() : 0, hbTab: S.tabId,
    mode: run.mode || 'generate', source: run.source || null, srcParts: srcParts.length, etalon: run.etalon || null,
    steps: Object.fromEntries(STEPS.map((s) => { const st = run.steps[s.id]; return [s.id, { status: st.status, t0: st.t0, t1: st.t1, note: st.note || '', log: st.log.slice(-40) }]; })),
  });
  let m = meta();
  if (JSON.stringify(m).length * 2 > 240000) { reqs = reqs.map((r) => ({ ...r, quote: r.quote.slice(0, 80) })); m = meta(); m.plan = []; }
  if (JSON.stringify(m).length * 2 > 240000 && checklist) { checklist = { groups: checklist.groups.map((g) => ({ ...g, items: g.items.slice(0, 40) })) }; m = meta(); m.plan = []; }
  const prevParts = run.savedParts || 0;
  run.partHashes = run.partHashes || [];
  for (let i = 0; i < parts.length; i++) {
    const h = hash(JSON.stringify(parts[i]));
    if (run.partHashes[i] !== h) { await db.doc(`${base}/${run.id}/parts/p${i}`).set({ cases: parts[i] }); run.partHashes[i] = h; }
  }
  for (let i = parts.length; i < prevParts; i++) await db.doc(`${base}/${run.id}/parts/p${i}`).delete();
  run.partHashes.length = parts.length;
  run.srcHashes = run.srcHashes || [];
  for (let i = 0; i < srcParts.length; i++) {
    const h = hash(JSON.stringify(srcParts[i]));
    if (run.srcHashes[i] !== h) { await db.doc(`${base}/${run.id}/src/s${i}`).set({ cases: srcParts[i] }); run.srcHashes[i] = h; }
  }
  await db.doc(`${base}/${run.id}`).set(m);
  run.savedParts = parts.length;
  if (S.historyState === 'ready') { if (S.tab === 'history' && !S.running) loadHistory(); else S.historyState = 'idle'; }
}
async function loadHistory() {
  if (!S.caps.db || !S.caps.uid) { S.historyState = 'unavailable'; if (S.tab === 'history') renderTab(); renderProduct(); return; }
  if (S.historyState !== 'ready') S.historyState = 'loading';
  if (S.tab === 'history') renderTab();
  const pid = S.productId;
  const q = (base) => S.caps.db.collection(base).where('kind', '==', 'run').orderBy('createdAt', 'desc').limit(30).get().then((snap) => snap.docs.map((d) => d.data()).filter(Boolean));
  try {
    const [mine, legacy] = await Promise.all([pid ? q(runBase(pid)) : Promise.resolve([]), q(`data/users/${S.caps.uid}`).catch(() => [])]);
    if (pid !== S.productId) return;
    S.history = pid ? mine : legacy; S.legacy = pid ? legacy : [];
    S.historyState = 'ready';
  } catch { S.historyState = 'error'; }
  if (S.tab === 'history') renderTab();
  renderProduct();
}
async function openHistory(id, opts = {}) {
  if (S.running) { if (!opts.silent) toast('Дождитесь окончания текущего запуска.', 'err'); return false; }
  try {
    const pid = opts.pid !== undefined ? opts.pid : S.productId;
    const base = runBase(pid);
    const meta = (await S.caps.db.doc(`${base}/${id}`).get()).data();
    if (!meta) throw new Error('not found');
    const cases = [], srcCases = [];
    for (let i = 0; i < (meta.partsCount || 0); i++) {
      const p = (await S.caps.db.doc(`${base}/${id}/parts/p${i}`).get()).data();
      if (p?.cases) cases.push(...p.cases.map((c) => ({ ...c, requirementIds: c.requirementIds || [], suites: c.suites || [] })));
    }
    for (let i = 0; i < (meta.srcParts || 0); i++) {
      const p = (await S.caps.db.doc(`${base}/${id}/src/s${i}`).get()).data();
      if (p?.cases) srcCases.push(...p.cases);
    }
    const run = {
      ...newRun(), id: meta.id, createdAt: meta.createdAt, finishedAt: meta.finishedAt,
      docs: meta.docs || [], settings: { outputs: { cases: true, checklist: !!meta.checklist }, ...(meta.settings || {}) },
      requirements: (meta.requirements || []).map((r) => ({ ...r, criteria: r.criteria || [], types: r.types || [] })),
      questions: (meta.questions || []).map((q, i) => (typeof q === 'string' ? { id: 'Q-' + pad(i + 1, 2), text: q, answer: '', appliedAnswer: '' } : q)),
      checklist: meta.checklist || null, findings: meta.findings || null, plan: meta.plan || [], cases, counters: { api: 0, ui: 0, e2e: 0, cl: 0, ...(meta.counters || {}) },
      status: meta.status || 'done', error: meta.error || null, fromHistory: true, savedParts: meta.partsCount || 0,
      stage: meta.stage || 'added', addedAt: meta.addedAt || null, auditDone: meta.auditDone !== false, reduced: !!meta.reduced, // запуски до черновика — уже в продукте; до сверки покрытия — не сверять задним числом
      doneKeys: meta.doneKeys || null, doneChecks: meta.doneChecks || [], taskStart: meta.taskStart || null, updatedAt: meta.updatedAt, usage: meta.usage || null, etalon: meta.etalon || null,
      qaCtx: meta.qaCtx ? { all: '', api: '', ui: '', e2e: '', ...meta.qaCtx } : null,
      productId: pid || null, docIds: meta.docIds || null, coveredExisting: meta.coveredExisting || [], by: meta.by || '', failedInfo: meta.failedInfo || null,
      baseCounters: meta.baseCounters || { api: 0, ui: 0, e2e: 0, cl: 0 }, hb: meta.hb || 0, hbTab: meta.hbTab || '',
      mode: meta.mode || 'generate', source: meta.source || null, srcCases, srcHashes: [],
    };
    if (meta.steps) for (const s of STEPS) { if (meta.steps[s.id]) run.steps[s.id] = { ...run.steps[s.id], ...meta.steps[s.id], log: meta.steps[s.id].log || [] }; }
    else for (const s of STEPS) run.steps[s.id].status = s.optional ? 'pending' : 'done';
    // запуски до разделения генерации по видам тестов: общий этап «generate» раскладывается на API, UI и E2E
    if (meta.steps?.generate && !GEN_STEPS.some((id) => meta.steps[id])) {
      const g = meta.steps.generate, types = run.settings.types || TYPES;
      for (const t of TYPES) {
        const own = (g.log || []).filter((l) => String(l.text || '').startsWith(TL[t] + ' ·'));
        run.steps[GEN_STEP[t]] = types.includes(t) ? { ...run.steps[GEN_STEP[t]], ...g, log: own } : { ...run.steps[GEN_STEP[t]], status: 'skipped', note: 'не выбрано', log: [] };
      }
    }
    if (!run.doneKeys) run.doneKeys = makeBatches(run.plan).flatMap((b) => b.items.map((p) => p.key));
    indexReqs(run);
    const same = S.run?.id === run.id;
    S.run = run;
    if (!same) { S.caseUI.clear(); S.reqOpen.clear(); S.filter = { type: 'all', suite: 'all', q: '' }; S.clFilter = { type: 'all', suite: 'all' }; S.exp = null; }
    S.tab = opts.tab || (opts.follow ? S.tab : run.cases.length ? 'cases' : checklistItems(run).length ? 'checklist' : 'agent');
    if (opts.follow) run.fromHistory = 'follow';
    else await reconcileRunning(run, { auto: !!opts.auto });
    renderAll();
    if (!opts.silent) { toast('Запуск загружен из истории'); saveSession(); }
    return true;
  } catch (e) { if (window.__QA_DEBUG) console.error('openHistory', e?.stack || e); if (!opts.silent) toast('Не удалось открыть запуск.', 'err'); return false; }
}
async function deleteHistory(id, pid) {
  try {
    const base = runBase(pid);
    const h = [...S.history, ...S.legacy].find((x) => x.id === id);
    for (let i = 0; i < (h?.partsCount || 0); i++) await S.caps.db.doc(`${base}/${id}/parts/p${i}`).delete();
    for (let i = 0; i < (h?.srcParts || 0); i++) await S.caps.db.doc(`${base}/${id}/src/s${i}`).delete();
    await S.caps.db.doc(`${base}/${id}`).delete();
    S.history = S.history.filter((x) => x.id !== id); S.legacy = S.legacy.filter((x) => x.id !== id);
    if (S.run?.id === id) S.run.fromHistory = 'readonly';
    if (pid) dropFromIndex(pid, id);
    renderTab(); toast('Запуск удалён из истории');
  } catch { toast('Не удалось удалить запуск.', 'err'); }
}
/* ================= память агента: правила из замечаний пользователя ================= */
function subscribeLessons() {
  S.caps.db.collection('lessons').onSnapshot((snap) => {
    const list = snap.docs.map((d) => ({ id: d.id, ...(d.data() || {}) })).filter((l) => l.text).sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0));
    if (ctxOwnsCfg()) { S.ctx.backup.lessons = list; return; } // память агента сейчас из источника контекста
    S.lessons = list;
    if (S.setTab === 'review' && !isTyping($('#cfg-body'))) renderCfg(); else renderCfgTabs();
  }, () => { /* хранилище недоступно — правила живут только в этом окне */ });
}
async function addLesson(text, scope = 'generation', source = 'manual') {
  const t = String(text || '').trim().slice(0, 400);
  if (!t || S.lessons.some((l) => normKey(l.text) === normKey(t))) return false;
  const l = { text: t, scope: ['generation', 'review', 'both'].includes(scope) ? scope : 'generation', source, createdAt: Date.now(), by: S.caps.uid || '' };
  if (ctxOwnsCfg()) return ctxAddLesson(l);
  const id = rid('l');
  if (S.caps.db) {
    try { await S.caps.db.doc('lessons/' + id).set(l); }
    catch { S.lessons.push({ id, ...l, local: true }); toast('Правило сохранено только в этом окне — нет прав на запись в общее хранилище.', 'err'); }
  } else S.lessons.push({ id, ...l, local: true });
  if (!S.caps.db) renderCfg();
  return true;
}
async function deleteLesson(id) {
  const l = S.lessons.find((x) => x.id === id);
  if (!l) return;
  if (ctxOwnsCfg()) return ctxDeleteLesson(id);
  if (S.caps.db && !l.local) { try { await S.caps.db.doc('lessons/' + id).delete(); } catch { return toast('Не удалось удалить правило — нужны права на изменение.', 'err'); } }
  S.lessons = S.lessons.filter((x) => x.id !== id);
  renderCfg();
}
const LESSON_SCOPE_RU = { generation: 'генерация', review: 'ревью', both: 'генерация и ревью' };
function promptLesson(kind, context, remark) {
  return renderPrompt("promptLesson", { "kind": kind, "context": context, "remark": remark, "e4": S.lessons.map((l) => '- ' + l.text).join('\n') || 'нет' });
}
async function learnFromRemark(kind, context, remark, defScope = 'generation') {
  const text = String(remark || '').trim();
  if (text.length < 5 || !aiReady(S.settings.genAI)) return;
  try {
    const res = await ask(promptLesson(kind, context, text), { step: 'lesson', ai: S.settings.genAI, tier: 'quick', cache: false, signal: new AbortController().signal });
    const rule = typeof res?.rule === 'string' ? res.rule.trim() : '';
    if (!rule) return;
    const ok = await addLesson(rule, ['generation', 'review', 'both'].includes(res.scope) ? res.scope : defScope, 'remark');
    if (ok) toast('Запомнил правило: ' + rule);
  } catch { /* обобщение — необязательный шаг */ }
}

/* ================= ревью субагентом ================= */
const SEV_RU = { critical: 'Критичное', major: 'Существенное', minor: 'Мелкое' };
const normSev = (s) => { const x = String(s || '').toLowerCase(); return /crit|крит|block|блок/.test(x) ? 'critical' : /minor|мелк|low|низ|cosm|стил/.test(x) ? 'minor' : 'major'; };
function reviewRulesBlock() {
  const r = S.cfg.reviewRules.trim();
  return `## Правила ревью команды\n${r || 'Не заданы — используй стандартные критерии ниже.'}\n${lessonsBlock('review')}`;
}
const REVIEW_CRITERIA = `## Стандартные критерии
1. Соответствие документации: ожидаемые результаты, коды ответов, тексты сообщений, лимиты и форматы совпадают с документами; нет выдуманных эндпоинтов, полей и текстов.
2. Кейс действительно проверяет заявленные требования; нет пропущенных негативных и граничных проверок.
3. Воспроизводимость: конкретные тестовые данные и предусловия, однозначные шаги.
4. Ожидаемый результат проверяемый и конкретный.
5. Соответствие шаблону команды: поля заполнены, формат как в образце.
6. Атомарность, отсутствие дублей.
7. Корректность приоритета и отметок «Смоук» / «Регресс».
8. Объём: нет исследовательских тестов и отдельных тестов только на БД (проверка БД шагом внутри кейса допустима); нет ручной подготовки данных в БД (INSERT/UPDATE/DELETE, «создать запись в таблице») — данные создаёт сама система через UI или API. Нарушение — "major".
9. В тексте кейса нет отсылок к требованиям (id R-…, «по требованию …»). Нарушение — "minor".`;
function promptReviewCases(run, type, cases, mode = {}) {
  const reqIds = [...new Set(cases.flatMap((c) => c.requirementIds))];
  const focus = cases.map((c) => `${pickTitleText(c.testCase)} ${c.requirementIds.map((id) => reqText(run.reqById[id])).join(' ')}`).join(' ');
  const ex = relevantExisting(run, 'cases', type, 30, focus);
  return renderPrompt("promptReviewCases", { "e1": TL[type], "e2": reviewRulesBlock(), "e3": qaCtxBlock(ctxOf(run), type, true), "REVIEW_CRITERIA": REVIEW_CRITERIA, "e5": TL[type], "e6": templateBlock(type), "e7": (run.questions || []).some((q) => q.answer?.trim()) ? `\n## Уточнения аналитика\n${run.questions.filter((q) => q.answer?.trim()).map((q) => `- ${q.text} — ${q.answer.trim()}`).join('\n')}\n` : '', "CACHE_MARK": CACHE_MARK, "e9": knowBlocks(run, 'review', focus), "e10": existingBlock(ex, 'cases', 'Если кейс на ревью повторяет один из них — замечание категории «Дубли» с id существующего кейса.'), "e11": reqIds.map((id) => reqLine(run.reqById[id])).filter(Boolean).join('\n') || 'нет', "e12": docsBlock(run, focus, mode), "e13": mode.tools ? `\n## Инструменты\nСверяй детали с документами инструментами search_documents и read_document.${kbToolsHint(run)} Не больше 4 обращений.\n` : '', "fence": fence, "e15": JSON.stringify(cases.map(casePayload)) });
}
function promptReviewChecklist(run, items) {
  const reqIds = [...new Set(items.flatMap((i) => i.requirementIds))];
  return renderPrompt("promptReviewChecklist", { "e1": reviewRulesBlock(), "e2": qaCtxBlock(ctxOf(run), null, true), "e3": knowBlocks(run, 'review', items.map((i) => i.check).join(' ')), "e4": reqIds.length ? reqIds.map((id) => reqLine(run.reqById[id])).filter(Boolean).join('\n') : run.requirements.filter((r) => r.inScope).map(reqCompact).join('\n'), "e5": items.map((i) => `${i.id} [${i.type}] [${i.priority}] [${i.suites.join(',') || 'без набора'}] ${i.requirementIds.join(',')}: ${i.check}`).join('\n') });
}
function addFinding(run, f) {
  const key = normKey(f.targetId + ' ' + f.message);
  if (run.findings.some((x) => normKey(x.targetId + ' ' + x.message) === key)) return;
  const n = run.findings.reduce((m, x) => Math.max(m, Number(String(x.id).slice(2)) || 0), 0) + 1;
  run.findings.push({ id: 'F-' + pad(n), status: 'open', reason: '', ...f });
}
/* отпечаток для повторного ревью: кейс не менялся и правила ревью те же — модель его не перечитывает */
const reviewSig = () => hash(S.cfg.reviewRules + '|' + S.lessons.filter((l) => l.scope !== 'generation').map((l) => l.text).join('|'));
const caseRevHash = (sig, c) => hash(sig + JSON.stringify(casePayload(c)));
const itemRevHash = (sig, it) => hash(sig + JSON.stringify([it.check, it.type, it.priority, it.suites, it.requirementIds]));
function findingTarget(run, f) {
  if (f.kind === 'case') return run.cases.find((c) => c.dispId === f.targetId) || null;
  if (f.kind === 'checklist') return checklistItems(run).find((i) => i.id === f.targetId) || null;
  return run.reqById[f.targetId] || null;
}
const openFindingsFor = (run, kind, id) => (run?.findings || []).filter((f) => f.status === 'open' && f.kind === kind && f.targetId === id);
function startReview(full = false, tab = 'review') {
  const run = S.run;
  if (!run || (!run.cases.length && !checklistItems(run).length)) return toast('Сначала сгенерируйте чек-лист или тест-кейсы.', 'err');
  S.tab = tab; S.fdFilter = 'open';
  runTask('review', async (run) => {
    run.steps.review.log = [];
    if (S.settings.strictRules) await repairRules(run);
    const prev = run.findings || [];
    const dismissed = prev.filter((f) => f.status === 'dismissed').map((f) => normKey(f.targetId + ' ' + f.message));
    const sig = reviewSig();
    const keepCase = new Set(), keepItem = new Set();
    if (!full && run.findings) {
      for (const c of activeCases(run)) if (c.revHash && c.revHash === caseRevHash(sig, c)) keepCase.add(c.dispId);
      for (const it of checklistItems(run)) if (it.revHash && it.revHash === itemRevHash(sig, it)) keepItem.add(it.id);
    }
    run.findings = prev.filter((f) => f.source === 'ai' && ((f.kind === 'case' && keepCase.has(f.targetId)) || (f.kind === 'checklist' && keepItem.has(f.targetId))));
    S.fdUI.clear();
    slog(run, 'review', `Ревьюер: ${aiLabelStage(aiValue('review'), 'review')}${S.cfg.reviewRules.trim() ? ' · правила ревью команды' : ''}${S.lessons.length ? ` · правил из замечаний: ${S.lessons.length}` : ''}`);
    if (keepCase.size + keepItem.size) slog(run, 'review', `Не менялись с прошлого ревью: ${keepCase.size ? `кейсов ${keepCase.size}` : ''}${keepCase.size && keepItem.size ? ', ' : ''}${keepItem.size ? `пунктов чек-листа ${keepItem.size}` : ''} — их замечания сохранены, повторно не проверяю`, 'ok');
    // проверки без модели
    if (run.cases.length && !run.reduced) for (const r of uncovered(run)) addFinding(run, { kind: 'req', targetId: r.id, severity: 'major', category: 'Покрытие', message: `Требование ${r.id} «${r.title}» не покрыто тест-кейсами.`, suggestion: 'Дописать тест-кейсы для этого требования.', source: 'auto' });
    // правила команды: безопасные исправления — на месте, остальное — замечаниями с кнопкой «Исправить»
    let fixed = 0; const byRule = {};
    for (const c of activeCases(run)) {
      fixed += applyRuleFixes(c);
      for (const v of ruleViolations(c)) {
        byRule[v.id] = (byRule[v.id] || 0) + 1;
        addFinding(run, { kind: 'case', targetId: c.dispId, severity: 'major', category: 'Правило', message: v.text, suggestion: 'Исправить кейс по правилу команды (кнопка «Исправить» или «Исправить все открытые»).', source: 'auto', rule: v.id });
      }
    }
    if (fixed) slog(run, 'review', `Исправлено сразу по правилам: ${fixed}`, 'ok');
    const broken = Object.entries(byRule);
    if (broken.length) slog(run, 'review', `Нарушения правил: ${broken.map(([id, n]) => `${id} ×${n}`).join(', ')}`, 'warn');
    for (const c of activeCases(run)) {
      const info = tplInfo(c.type);
      const miss = info.ok ? info.fields.filter((k) => !(k in (c.testCase || {}))) : [];
      if (miss.length) addFinding(run, { kind: 'case', targetId: c.dispId, severity: 'minor', category: 'Шаблон', message: `Нет полей шаблона: ${miss.join(', ')}.`, suggestion: 'Заполнить недостающие поля по образцу шаблона.', source: 'auto' });
      if (!pickTitle(c.testCase || {}).key) addFinding(run, { kind: 'case', targetId: c.dispId, severity: 'major', category: 'Шаблон', message: 'Нет названия кейса.', suggestion: 'Добавить название кейса.', source: 'auto' });
      if (!titleTagOk(c)) { const tag = titleTagFor(c.type, pickTitleText(c.testCase)); addFinding(run, { kind: 'case', targetId: c.dispId, severity: 'minor', category: 'Название', message: `В названии нет метки вида теста ${tag}.`, suggestion: `Начать название с ${tag}.`, source: 'auto' }); }
    }
    const auto = run.findings.length;
    if (auto) slog(run, 'review', `Автоматические проверки: ${auto} ${plural(auto, 'замечание', 'замечания', 'замечаний')}`, 'warn');
    // ревью моделью
    const v = aiValue('review');
    const total = docsFor(run).reduce((a, d) => a + d.chars, 0);
    const useTools = !economy() && total > FULLDOC_LIMIT && toolsAvailable(v);
    const jobs = [];
    for (const t of TYPES) { const cs = activeCases(run).filter((c) => c.type === t && !keepCase.has(c.dispId)); for (let i = 0; i < cs.length; i += 5) jobs.push({ kind: 'case', type: t, cases: cs.slice(i, i + 5) }); }
    const cl = checklistItems(run), clTodo = cl.filter((it) => !keepItem.has(it.id));
    for (let i = 0; i < clTodo.length; i += 80) jobs.push({ kind: 'checklist', items: clTodo.slice(i, i + 80) });
    slog(run, 'review', `${jobs.length} ${plural(jobs.length, 'запрос', 'запроса', 'запросов')} к ревьюеру, до ${CONCURRENCY} одновременно`);
    await pool(jobs, CONCURRENCY, async (job) => {
      const label = job.kind === 'case' ? `Кейсы ${job.cases[0].dispId}–${job.cases[job.cases.length - 1].dispId}` : `Чек-лист ${job.items[0].id}–${job.items[job.items.length - 1].id}`;
      const line = slog(run, 'review', `${label}: ревьюер читает…`);
      try {
        const res = await ask(job.kind === 'case' ? promptReviewCases(run, job.type, job.cases, { tools: useTools }) : promptReviewChecklist(run, job.items), { step: 'review',
          role: 'review', cache: false, tools: job.kind === 'case' && useTools ? makeTools(run, 'review') : undefined,
          onProgress: (n) => { line.text = `${label}: пишет замечания — ${fmtKChars(n)}`; scheduleRender(); },
        });
        let n = 0;
        const minor = [];   // мелкие замечания пакета — одной строкой, а не отдельными карточками
        for (const f of arrOf(res?.findings)) {
          const id = String(f?.targetId || '').trim();
          const kind = run.cases.some((c) => c.dispId === id) ? 'case' : cl.some((i) => i.id === id) ? 'checklist' : run.reqById[id] ? 'req' : null;
          if (!kind || !String(f?.message || '').trim()) continue;
          if (normSev(f.severity) === 'minor') { minor.push(`${id}: ${String(f.message).trim()}`); continue; }
          if (dismissed.includes(normKey(id + ' ' + f.message))) continue;
          addFinding(run, { kind, targetId: id, severity: normSev(f.severity), category: String(f.category || 'Замечание').slice(0, 60), message: String(f.message).trim(), suggestion: String(f.suggestion || '').trim(), source: 'ai' });
          n++;
        }
        const tail = String(res?.minor || '').trim();
        if (tail) minor.push(tail);
        if (minor.length) {
          const first = job.kind === 'case' ? job.cases[0].dispId : job.items[0].id;
          addFinding(run, { kind: job.kind === 'case' ? 'case' : 'checklist', targetId: first, severity: 'minor', category: 'Мелкие замечания', message: `${label}: ${minor.join('; ')}`, suggestion: 'Поправить при следующей правке кейсов этого пакета.', source: 'ai' });
          n++;
        }
        line.text = `${label}: ${n ? `${n} ${plural(n, 'замечание', 'замечания', 'замечаний')}` : 'замечаний нет'}`; line.kind = n ? 'warn' : 'ok';
        if (job.kind === 'case') for (const c of job.cases) c.revHash = caseRevHash(sig, c); else for (const it of job.items) it.revHash = itemRevHash(sig, it);
      } catch (e) { handleCallError(run, e, line, label); }
      scheduleRender();
    }, S.ctl.signal);
    if (S.ctl.signal.aborted) throw abortErr();
    const by = (s) => run.findings.filter((f) => f.severity === s).length;
    slog(run, 'review', `Итого замечаний: ${run.findings.length} — критичных ${by('critical')}, существенных ${by('major')}, мелких ${by('minor')}`, run.findings.length ? 'warn' : 'ok');
    send(run, 'review');
  }, 'review');
}
/* исправление замечаний */
function promptRefineItem(run, it, comment) {
  return renderPrompt("promptRefineItem", { "e1": it.requirementIds.map((id) => reqLine(run.reqById[id])).filter(Boolean).join('\n') || 'нет', "e2": clarBlock(run), "e3": qaCtxBlock(ctxOf(run), it.type), "e4": knowBlocks(run, 'batch', `${it.check} ${comment}`), "it_id": it.id, "it_type": it.type, "it_priority": it.priority, "e8": it.suites.join(','), "it_check": it.check, "it_kind": it.kind === 'negative' ? 'негативная' : 'позитивная', "it_expected": it.expected || 'не указан', "comment": comment });
}
async function refineItemCore(run, it, comment, signal) {
  const res = await ask(promptRefineItem(run, it, comment), { step: 'refine', cache: false, signal });
  const check = String(res?.check || '').trim();
  if (!check) throw new Error('Модель не вернула формулировку пункта.');
  it.prevCheck = it.check; it.check = check;
  if (typeof res.expected === 'string' && res.expected.trim()) it.expected = res.expected.trim();
  if (res.kind) it.kind = clKind(res.kind);
  if (res.priority) it.priority = normPrio(res.priority);
  it.suites = withCritical(it.priority, it.suites || []);
  if (res.suites !== undefined) it.suites = normSuites(res.suites);
}
const findingComment = (fs) => fs.map((f) => `Замечание ревьюера (${SEV_RU[f.severity].toLowerCase()}, ${f.category}): ${f.message}${f.suggestion ? ` Рекомендация: ${f.suggestion}` : ''}`).join('\n');
// вопрос агенту по кейсу: почему кейс составлен так. Ответ — по данным кейса, требований, пункта чек-листа и правил
async function askCase(run, c, question) {
  const ui = caseUI(c.uid);
  ui.busy = true; ui.error = ''; renderCaseList();
  try {
    const reqs = arrStr(c.requirementIds).map((id) => reqLine(run.reqById?.[id])).filter(Boolean);
    const cl = c.checklistId ? checklistItems(run).find((i) => i.id === c.checklistId) : null;
    const pl = c.planItem ? (run.plan || []).find((p) => p.id === c.planItem) : null;
    const prompt = renderPrompt("promptAskCase", {
      "e1": JSON.stringify(c.testCase, null, 2),
      "e2": reqs.length ? '## Требования, которые проверяет кейс\n' + reqs.join('\n') + '\n' : '',
      "e3": cl ? `## Пункт чек-листа, из которого сделан кейс\n${cl.id} · ${cl.check}${cl.expected ? ' → ' + cl.expected : ''}\n` : '',
      "e4": pl ? `## План проверок для кейса\n${pl.title || pl.id}: ${arrOf(pl.checks).join('; ')}\n` : '',
      "e5": rulesText() || 'нет',
      "e6": question,
    });
    const res = await ask(prompt, { step: 'other' });
    c.askLog = [...(c.askLog || []), { q: question, a: String(res?.answer || '').trim() || 'Ответ пустой.', at: Date.now() }];
    ui.comment = ''; ui.mode = 'view';
    queueSave(run);
  } catch (e) { if (e?.code !== 'cancelled') ui.error = errText(e); }
  finally { ui.busy = false; renderCaseList(); }
}
async function fixFindings(list) {
  const open = list.filter((f) => f.status === 'open');
  if (!open.length) return;
  runTask('fix', async (run) => {
    const groups = new Map();
    for (const f of open) { const k = f.kind + '|' + f.targetId; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(f); }
    slog(run, 'fix', `Исправляю: ${open.length} ${plural(open.length, 'замечание', 'замечания', 'замечаний')} по ${groups.size} ${plural(groups.size, 'объекту', 'объектам', 'объектам')}`);
    const reqGaps = [];
    const jobs = [];
    for (const [, fs] of groups) { if (fs[0].kind === 'req') reqGaps.push(...fs); else jobs.push(fs); }
    await pool(jobs, CONCURRENCY, async (fs) => {
      const target = findingTarget(run, fs[0]);
      const line = slog(run, 'fix', `${fs[0].targetId}: исправляю…`);
      if (!target) { line.text = `${fs[0].targetId}: объект не найден`; line.kind = 'warn'; return; }
      try {
        if (fs[0].kind === 'case') { await refineCaseCore(run, target, findingComment(fs), S.ctl.signal); caseUI(target.uid).note = 'Исправлено по замечаниям ревьюера.'; }
        else await refineItemCore(run, target, findingComment(fs), S.ctl.signal);
        fs.forEach((f) => { f.status = 'fixed'; });
        line.text = `${fs[0].targetId}: исправлено`; line.kind = 'ok';
        S.pendingCasesRender = true;
      } catch (e) { handleCallError(run, e, line, fs[0].targetId); }
      scheduleRender();
    }, S.ctl.signal);
    if (S.ctl.signal.aborted) throw abortErr();
    if (reqGaps.length) {
      const reqs = [...new Set(reqGaps.map((f) => f.targetId))].map((id) => run.reqById[id]).filter(Boolean);
      const items = fallbackItems(reqs, run.settings.types || TYPES);
      items.forEach((it, i) => { it.id = 'X-' + pad(run.plan.length + i + 1, 2); });
      run.plan.push(...items);
      await generateItems(run, items, 'fix');
      for (const f of reqGaps) if (run.cases.some((c) => c.requirementIds.includes(f.targetId))) f.status = 'fixed';
    }
    const left = open.filter((f) => f.status === 'open').length;
    slog(run, 'fix', left ? `Не удалось исправить: ${left}` : 'Все выбранные замечания исправлены', left ? 'warn' : 'ok');
    send(run, 'fix', left ? 'error' : 'done');
  });
}
/* ---------- черновик: проверка кейсов перед добавлением в проект ---------- */
const isDraft = (run) => !!run && run.stage === 'draft';
const caseFindings = (run, c, open = true) => (run?.findings || []).filter((f) => f.kind === 'case' && f.targetId === c.dispId && (!open || f.status === 'open'));
const draftLocked = (run) => !run || S.running || run.fromHistory === 'readonly' || run.fromHistory === 'follow';
function fixCaseFindings(uid) {
  const run = S.run, c = run?.cases.find((x) => x.uid === uid);
  if (c) fixFindings(caseFindings(run, c));
}
// «Исправить все» берёт только выбранную серьёзность: критичные, существенные или мелкие; «все» и «открытые» — без отбора
const fixScope = (list, sev) => (['critical', 'major', 'minor'].includes(sev) ? list.filter((f) => f.severity === sev) : list);
const SEV_FIX_RU = { critical: 'критичные', major: 'существенные', minor: 'мелкие' };
function fixDraftAll() {
  const run = S.run;
  if (run) fixFindings(fixScope((run.findings || []).filter((f) => f.status === 'open' && f.kind === 'case'), S.draftFilter));
}
function dropDraftCase(uid) {
  const run = S.run, c = run?.cases.find((x) => x.uid === uid);
  if (!c || draftLocked(run)) return;
  run.cases = run.cases.filter((x) => x !== c);
  if (run.findings) run.findings = run.findings.filter((f) => !(f.kind === 'case' && f.targetId === c.dispId));
  S.caseUI.delete(uid); queueSave(run); renderTabs(); renderTab(); renderRunControls();
  toast(`${c.dispId} убран из черновика`);
}
function clearDraft() {
  const run = S.run;
  if (!run || draftLocked(run) || !run.cases.length) return;
  const n = run.cases.length;
  run.cases = []; S.caseUI.clear();
  if (run.findings) run.findings = run.findings.filter((f) => f.kind !== 'case');
  // номера кейсов не заняты: следующая генерация начнёт с тех же
  if (isDraft(run)) for (const t of TYPES) run.counters[t] = run.baseCounters?.[t] || 0;
  queueSave(run); renderTabs(); renderTab(); renderRunControls();
  toast(`Черновик очищен: ${n} ${plural(n, 'кейс', 'кейса', 'кейсов')} удалено`);
}
/* перегенерировать черновик по текущим правилам: кейсы черновика и шаги плана, генерации и покрытия пересоздаются;
   анализ требований и чек-лист остаются (их не трогаем) */
// какие правила шаблонов пойдут в перегенерацию: видно в журнале, что учтена последняя правка
function tplDigest(types) {
  return types.filter((t) => S.cfg.tpl[t]).map((t) => {
    const rules = String(S.cfg.tpl[t].rules || '').split('\n').map((l) => l.replace(/^\s*[-*]\s*/, '').trim()).filter(Boolean);
    return `${TL[t]}: правил оформления ${rules.length}${rules.length ? ` (последнее — «${rules[rules.length - 1].slice(0, 120)}»)` : ''}${S.cfgDirty[t] ? ', есть несохранённая правка' : ''}`;
  });
}
async function regenDrafts() {
  const run = S.run;
  if (!run || draftLocked(run) || !isDraft(run) || !run.cases.length || S.running) return;
  // шаблоны и правила могли поправить прямо в файлах источника — перечитываем изменённые файлы перед генерацией
  if (ctxActive(run.productId || S.productId) && S.ctx.src.kind !== 'folder') {
    toast('Перечитываю шаблоны и правила из источника…');
    try { await ctxRefresh({ quiet: true }); } catch { /* источник недоступен — работаем с прочитанной копией */ }
    if (S.run !== run || S.running) return;
  }
  const n = run.cases.length;
  // тот же набор кейсов: каждый старый кейс переписывается по текущим правилам и шаблонам — число кейсов не меняется
  const expOf = (tc) => { const st = arrOf(tc?.steps), v = tc?.expectedResult ?? tc?.expected ?? tc?.expected_result ?? (st.length ? st[st.length - 1]?.expected ?? st[st.length - 1]?.expectedResult : ''); return typeof v === 'string' ? v : JSON.stringify(v ?? ''); };
  run.reduced = false;
  run.regenFrom = run.cases.map((c) => ({ type: c.type, title: String(pickTitleText(c.testCase) || c.dispId).replace(KNOWN_TAG_RX, '').trim(), exp: String(expOf(c.testCase)).replace(/\s+/g, ' ').trim().slice(0, 300), reqs: arrStr(c.requirementIds), cl: c.checklistId || '' }));
  run.cases = []; S.caseUI.clear();
  if (run.findings) run.findings = run.findings.filter((f) => f.kind !== 'case');
  for (const t of TYPES) run.counters[t] = run.baseCounters?.[t] || 0;
  run.plan = []; run.coveredExisting = []; run.doneKeys = []; run.doneChecks = []; run.failed = [];
  run.noKb = true; // в этом запуске база знаний и паспорт продукта не используются
  run.regenTpl = tplDigest(run.settings.types || TYPES);
  for (const id of ['plan', ...GEN_STEPS, 'coverage']) run.steps[id] = { status: 'pending', log: [], t0: null, t1: null, note: '' };
  queueSave(run);
  toast(`Переписываю ${n} ${plural(n, 'кейс', 'кейса', 'кейсов')} по текущим правилам и шаблонам — столько же, сколько было`);
  stopFollow(); cancelResumeCountdown();
  S.tab = 'agent';
  executeRun(run, false);
}
/* сокращение черновика до N кейсов: модель предлагает набор, код приводит его к ровно N кейсам и проверяет покрытие требований */
function reduceSelect(cases, keepIds, target) {
  const byId = new Map(cases.map((c) => [c.dispId, c]));
  const reqsOf = (id) => byId.get(id).requirementIds || [];
  const rankOf = (id) => PRIOS.indexOf(normPrio(byId.get(id).testCase?.priority));
  const all = new Set(cases.flatMap((c) => c.requirementIds || []));
  const cov = (ids) => { const s = new Set(); for (const id of ids) for (const r of reqsOf(id)) s.add(r); return s; };
  const covers = (ids) => { const s = cov(ids); return [...all].every((r) => s.has(r)); };
  const gainOf = (ids, id) => { const s = cov(ids); return reqsOf(id).filter((r) => !s.has(r)).length; };
  // жадный набор, покрывающий все требования: если он больше N, покрытие при N не сохранить
  const minCov = [], left = new Set(all);
  while (left.size) {
    let best = null, bg = 0;
    for (const id of byId.keys()) { if (minCov.includes(id)) continue; const g = reqsOf(id).filter((r) => left.has(r)).length; if (g > bg || (g === bg && g && best && rankOf(id) < rankOf(best))) { best = id; bg = g; } }
    if (!best) break;
    minCov.push(best); for (const r of reqsOf(best)) left.delete(r);
  }
  // жадный набор не всегда минимальный: точный поиск набора не больше k кейсов (ветвление по самому редкому требованию)
  const exactCover = (k) => {
    let steps = 0, found = null;
    const rec = (chosen, uncovered) => {
      if (found || steps++ > 200000) return;
      if (!uncovered.size) { found = chosen; return; }
      if (chosen.length >= k) return;
      let rq = null, opts = null;
      for (const r of uncovered) { const o = [...byId.keys()].filter((x) => reqsOf(x).includes(r)); if (!opts || o.length < opts.length) { rq = r; opts = o; } }
      for (const x of opts.sort((a, b) => rankOf(a) - rankOf(b))) {
        const nu = new Set(uncovered); for (const r of reqsOf(x)) nu.delete(r);
        rec([...chosen, x], nu);
        if (found) return;
      }
    };
    rec([], new Set(all));
    return found;
  };
  if (minCov.length > target && !exactCover(target)) {
    // покрытие при таком N не сохранить: предлагаем набор с максимальным покрытием, но просим подтверждения
    const pick = [], left = new Set(all);
    while (pick.length < target) {
      let best = null, bg = 0;
      for (const id of byId.keys()) { if (pick.includes(id)) continue; const g = reqsOf(id).filter((r) => left.has(r)).length; if (g > bg || (g === bg && g && best && rankOf(id) < rankOf(best))) { best = id; bg = g; } }
      if (!best) break;
      pick.push(best); for (const r of reqsOf(best)) left.delete(r);
    }
    while (pick.length < target) { const pool = [...byId.keys()].filter((x) => !pick.includes(x)); if (!pool.length) break; pool.sort((a, b) => rankOf(a) - rankOf(b)); pick.push(pool[0]); }
    return { warn: true, min: minCov.length, keep: pick, uncovered: left.size };
  }
  // лишние убираем: сначала те, без которых покрытие не падает, с наименьшим приоритетом
  const trim = (ids, protect) => {
    while (ids.length > target) {
      const cands = ids.filter((x) => x !== protect);
      const red = (x) => covers(ids.filter((y) => y !== x)) ? 0 : 1;
      cands.sort((a, b) => red(a) - red(b) || rankOf(b) - rankOf(a));
      ids.splice(ids.indexOf(cands[0]), 1);
    }
    return ids;
  };
  // недостающие добираем: сначала кейсы, которые закрывают больше ещё не покрытых требований, затем по приоритету
  const fill = (ids) => {
    while (ids.length < target) {
      const pool = [...byId.keys()].filter((x) => !ids.includes(x));
      if (!pool.length) break;
      pool.sort((a, b) => gainOf(ids, b) - gainOf(ids, a) || rankOf(a) - rankOf(b));
      ids.push(pool[0]);
    }
    return ids;
  };
  // база — набор модели, если он покрывает все требования; иначе — минимальное покрытие (оно есть, раз minCov ≤ N).
  // обрезка убирает только лишние кейсы и покрытие не ломает, добор только добавляет — покрытие сохраняется
  const cover = exactCover(target) || [...minCov];   // набор, покрывающий всё, не больше N
  let base = [...new Set((keepIds || []).filter((id) => byId.has(id)))];
  if (!covers(base)) base = [...cover];
  let keep = fill(trim(base));
  if (!covers(keep)) keep = fill([...cover]);   // обрезка набора модели могла потерять покрытие — тогда от найденного покрытия
  if (keep.length !== target || !covers(keep)) return { error: 'Не удалось сохранить покрытие требований при таком количестве. Попробуйте больше кейсов.', min: minCov.length };
  return { keep };
}
const REDUCE_DOCS_CAP = 60000; // знаков документации в запрос сокращения
function promptReduce(run, cases, target) {
  const reqIds = [...new Set(cases.flatMap((c) => c.requirementIds || []))];
  const reqs = reqIds.map((id) => run.reqById?.[id]).filter(Boolean).map((r) => `${r.id} «${r.title}»: ${r.description || ''}${r.criteria?.length ? ' Критерии: ' + r.criteria.join('; ') : ''}`).join('\n') || '—';
  const lines = cases.map((c) => `${c.dispId} | ${TL[c.type] || c.type} | ${PRIO_RU[normPrio(c.testCase?.priority)] || '—'} | ${(c.requirementIds || []).join(', ') || '—'} | ${pickTitleText(c.testCase || {})}`).join('\n');
  // документация, по которой написаны кейсы: фрагменты, близкие к требованиям и заголовкам кейсов
  const docs = docsFor(run);
  const focus = reqs + ' ' + cases.map((c) => pickTitleText(c.testCase || {})).join(' ');
  const per = docs.length ? Math.floor(REDUCE_DOCS_CAP / docs.length) : 0;
  const docText = docs.map((d) => `### Документ «${d.name}»\n${kbFitText(d.text, focus, per)}`).join('\n\n') || 'Документы этого запуска недоступны — опирайся на требования и кейсы.';
  return renderPrompt('promptReduceCases', { e1: lines, e2: reqs, e3: String(target), e4: docText });
}
let reducing = false;
/* набор, ожидающий подтверждения (когда покрытие при заданном N не сохранить) */
let reducePending = null;
function applyReduce(run, keepIds) {
  const keep = new Set(keepIds), removed = run.cases.filter((c) => !keep.has(c.dispId));
  run.cases = run.cases.filter((c) => keep.has(c.dispId));
  run.reduced = true;   // после сокращения ревью не проверяет полноту покрытия: набор выбран осознанно
  for (const c of removed) S.caseUI.delete(c.uid);
  if (run.findings) run.findings = run.findings.filter((f) => !(f.kind === 'case' && removed.some((c) => c.dispId === f.targetId)));
  queueSave(run); renderTabs(); renderTab();
  return { removed: removed.length, kept: run.cases.length };
}
/* возвращает { removed, kept }, { warn, message } (нужно подтверждение) или { error } */
async function reduceDraft(target, { confirmed = false } = {}) {
  const run = S.run;
  if (reducing) return { error: 'Сокращение уже идёт.' };
  if (!run || draftLocked(run) || !isDraft(run) || S.running) return { error: 'Сократить можно только черновик, когда генерация не идёт.' };
  const cases = run.cases.filter((c) => c.status !== 'obsolete');
  if (!(target >= 1 && target < cases.length)) return { error: `Оставить можно от 1 до ${cases.length - 1}.` };
  if (confirmed && reducePending && reducePending.run === run && reducePending.target === target) {
    const p = reducePending; reducePending = null;
    return applyReduce(run, p.keep);
  }
  reducePending = null;
  reducing = true;
  try {
    const res = await ask(promptReduce(run, cases, target), { step: 'other' });
    if (S.run !== run) return { error: 'Запуск сменился — сокращение отменено.' };
    const sel = reduceSelect(cases, arrStr(res?.keep), target);
    if (sel.error) return sel;
    if (sel.warn) {
      reducePending = { run, target, keep: sel.keep };
      const u = sel.uncovered;
      return { warn: true, message: `При ${target} ${plural(target, 'тесте', 'тестах', 'тестах')} ${u} ${plural(u, 'требование останется', 'требования останутся', 'требований останутся')} без проверок: для полного покрытия нужно минимум ${sel.min} ${plural(sel.min, 'тест', 'теста', 'тестов')}. Сократить всё равно?` };
    }
    return applyReduce(run, sel.keep);
  } catch (e) {
    return { error: 'Не удалось сократить: ' + (e?.message || 'модель не ответила') };
  } finally { reducing = false; }
}
/* в проект: кейсы попадают в индекс продукта (их видят «Уже есть в продукте», повторы и нумерация). Если пока кейсы
   лежали в черновике, номера заняли другие запуски — кейсы получают следующие свободные номера продукта */
async function addDraftToProduct() {
  const run = S.run;
  if (!run || draftLocked(run) || !isDraft(run) || !run.cases.length) return;
  if (run.productId && S.prodIndex.pid === run.productId) {
    const others = S.prodIndex.cases.filter((x) => x.r !== run.id), taken = new Set(others.map((x) => x.i));
    const p = productById(run.productId), ctr = {};
    for (const t of TYPES) ctr[t] = Math.max(Number(p?.counters?.[t]) || 0, idxMax(others, t));
    const ren = new Map();
    for (const c of run.cases) {
      if (!taken.has(c.dispId)) { taken.add(c.dispId); continue; }
      let id;
      do id = (S.cfg.tpl[c.type].idPrefix || '') + pad(++ctr[c.type]); while (taken.has(id) || run.cases.some((x) => x !== c && x.dispId === id));
      taken.add(id); ren.set(c.dispId, id);
      const info = tplInfo(c.type);
      if (info.ok && info.idField && c.testCase) c.testCase[info.idField] = id;
      c.dispId = id; run.counters[c.type] = Math.max(run.counters[c.type] || 0, ctr[c.type]);
    }
    if (ren.size && run.findings) for (const f of run.findings) if (f.kind === 'case' && ren.has(f.targetId)) f.targetId = ren.get(f.targetId);
    if (ren.size) toast(`Номера заняли другие запуски — ${ren.size} ${plural(ren.size, 'кейс получил', 'кейса получили', 'кейсов получили')} следующие свободные номера`);
  }
  run.stage = 'added'; run.addedAt = Date.now();
  queueSave(run); renderRunControls();
  await productSync(run);
  renderTabs(); renderTab(); renderProduct(); renderRunControls();
  const n = run.cases.length;
  toast(run.productId ? `${n} ${plural(n, 'кейс добавлен', 'кейса добавлены', 'кейсов добавлены')} в продукт «${productById(run.productId)?.name || 'Продукт'}»` : 'Кейсы отмечены как принятые');
}
function dismissFinding(f, reason) {
  f.status = 'dismissed'; f.reason = String(reason || '').trim();
  queueSave(S.run);
  if (f.reason) learnFromRemark('отклонённое замечание ревьюера', `${f.targetId}: ${f.message}`, `Это не ошибка: ${f.reason}`, 'review');
}
async function refineItemUI(it, comment) {
  const st = S.clRefine;
  if (!aiReady(S.run.settings.genAI || S.settings.genAI)) { st.error = aiProblem(S.run.settings.genAI || S.settings.genAI); return renderTab(); }
  st.busy = true; st.error = ''; st.ctl = new AbortController(); renderTab();
  try {
    await refineItemCore(S.run, it, comment, st.ctl.signal);
    S.clRefine = null; queueSave(S.run); toast(`Пункт ${it.id} доработан`);
    learnFromRemark('пункт чек-листа', `${it.id}: ${it.prevCheck}`, comment);
  } catch (e) { if (S.clRefine) { st.error = e?.code === 'cancelled' ? '' : errText(e); st.busy = false; } }
  if (S.clRefine) S.clRefine.busy = false;
  renderTab();
}

/* ================= загрузка в ТМС ================= */
const TMS_KINDS = {
  sfera: { name: 'Сфера ФТ', hint: 'Через расширение «QA pro — загрузчик в Сферу ФТ»: вход берётся из Сферы, открытой в этом браузере, раздел выбирается в окне загрузчика. Смоук — метка SMOKE, регресс — отметка «Регрессионный».' },
  testit: { name: 'Test IT', hint: 'Адрес вида https://company.testit.software. Токен — «Секретный ключ API» из профиля Test IT. ID проекта и раздела — UUID из адресной строки.' },
  qase: { name: 'Qase', hint: 'Адрес API по умолчанию https://api.qase.io/v1. Токен — из настроек Qase (API tokens), проект — его код (например, DEMO).' },
  testrail: { name: 'TestRail', hint: 'Адрес вида https://company.testrail.io. Логин — email, токен — API-ключ из «My Settings». Раздел — ID секции (section_id).' },
  custom: { name: 'Свой API', hint: 'POST на указанный адрес: по одному кейсу или все кейсы одним запросом. Тело — JSON кейса из QA pro.' },
};
function tmsCase(c) {
  const tc = c.testCase || {};
  const keys = Object.keys(tc);
  const str = (v) => (v == null ? '' : typeof v === 'string' ? noReqRefs(deHtml(v)) : typeof v === 'object' ? JSON.stringify(noReqDeep(plainDeep(v)), null, 2) : String(v));
  const lines = (v) => (Array.isArray(v) ? v.map(str) : v ? preItems(str(v)) : []).map((x) => x.trim()).filter(Boolean);
  const k = (re) => keys.find((x) => re.test(x));
  const stepsKey = k(/^(steps|testSteps|шаги)$/i) || keys.find((x) => Array.isArray(tc[x]) && tc[x].some((s) => s && typeof s === 'object'));
  const steps = arrOf(tc[stepsKey]).map((s) => {
    if (!s || typeof s !== 'object') return { action: str(s), expected: '', data: '' };
    const sk = Object.keys(s);
    const pick = (re) => { const key = sk.find((x) => re.test(x)); return key ? str(s[key]) : ''; };
    const action = pick(/action|действ|^step_?text$|description|описан|^text$|^name$/i);
    return { action, expected: pick(/expect|ожид|result|результат/i), data: pick(/data|данн/i) };
  });
  const pre = lines(cleanPre(tc[k(/precond|предусл/i)])), post = lines(cleanPre(tc[k(/postcond|постусл/i)]));
  const desc = [];
  const dk = k(/^(description|описание|scenario|сценарий|objective|цель)$/i);
  if (dk) desc.push(noReqRefs(str(tc[dk]), true));
  const rk = k(/^(request|запрос)$/i);
  if (rk) desc.push('Запрос:\n' + str(tc[rk]));
  const tdk = k(/^(testData|test_data|тестовые_?данные|data)$/i);
  if (tdk && tdk !== stepsKey) desc.push('Тестовые данные:\n' + str(tc[tdk]));
  const ek = k(/^(expectedResult|expected_result|ожидаемый_?результат|result)$/i);
  if (ek) desc.push('Ожидаемый результат: ' + str(tc[ek]));
  if (!steps.length && ek) steps.push({ action: pickTitleText(tc), expected: str(tc[ek]), data: '' });
  const tags = [...new Set([...arrStr(tc[k(/^(tags|теги)$/i)]), ...(c.suites || []), c.type])];
  return { title: pickTitleText(tc), description: desc.join('\n\n'), pre, post, steps, priority: normPrio(prioOf(tc)), tags };
}
/* ---------- Сфера ФТ: через расширение-загрузчик (мост window.postMessage) ---------- */
const BRIDGE_PAGE = 'qa-pro', BRIDGE_EXT = 'qa-pro-sfera-uploader', BRIDGE_EVT_IN = 'qa-pro:to-uploader', BRIDGE_EVT_OUT = 'qa-pro:from-uploader';
// Адрес окна QA pro и окон над ним — для диагностики, когда загрузчик не видит страницу.
function frameWhere() {
  const parts = [];
  try { parts.push(/^(about|blob|data):/.test(location.href) ? location.href.slice(0, 40) : location.origin !== 'null' ? location.origin : location.protocol + '//' + location.host + ' (изолированное окно)'); } catch { /* нет доступа */ }
  try { for (const o of location.ancestorOrigins || []) parts.push(o); } catch { /* браузер не сообщает */ }
  return parts.filter(Boolean).join(' ← ');
}
function sferaNoExtText(x = S.sferaExt) {
  if (x?.stage === 'ext') return `Загрузчик видит эту страницу, но не отвечает${x.error ? ` (${x.error})` : ''}. Откройте chrome://extensions, нажмите «Обновить» у загрузчика, затем обновите страницу QA pro.`;
  return 'Загрузчик не видит эту страницу. Обновите страницу (Ctrl+F5) после установки загрузчика и проверьте, что QA pro открыт в Chrome, Edge или Яндекс Браузере, а не в приложении Claude.';
}
const bridgeWait = new Map(), bridgeSeen = new Set();
function onBridgeMsg(d) {
  if (!d || d.source !== BRIDGE_EXT || typeof d.id !== 'string' || typeof d.type !== 'string') return;
  if (d.type === 'SFERA_TICK') { if (S.running && S.run) beat(); workerTick(); return; } // пульс от загрузчика будит фоновую вкладку
  const key = d.type + ':' + d.id; // мост отвечает двумя каналами — берём первый ответ
  if (bridgeSeen.has(key)) return;
  bridgeSeen.add(key);
  if (bridgeSeen.size > 300) bridgeSeen.delete(bridgeSeen.values().next().value);
  if (d.type === 'SFERA_RESULT' && !relayCallIds.has(d.id)) sferaApply(d);
  const w = bridgeWait.get(d.id);
  if (!w) return;
  if (w.until.includes(d.type)) { bridgeWait.delete(d.id); w.done(d); }
  else w.on?.(d);
}
window.addEventListener('message', (e) => { if (e.source === window) onBridgeMsg(e.data); });
document.addEventListener(BRIDGE_EVT_OUT, (e) => { if (typeof e.detail !== 'string') return; try { onBridgeMsg(JSON.parse(e.detail)); } catch { /* не наше */ } });
const relayCallIds = new Set();
function bridgeCall(msg, { timeout = 0, until, signal, on, relay = false } = {}) {
  return new Promise((resolve) => {
    const id = rid('br');
    if (relay) relayCallIds.add(id);
    const finish = (d) => { if (t) clearTimeout(t); resolve(d); };
    const t = timeout ? setTimeout(() => { bridgeWait.delete(id); resolve(null); }, timeout) : null;
    signal?.addEventListener('abort', () => { bridgeWait.delete(id); finish({ type: 'ABORTED' }); });
    bridgeWait.set(id, { until, done: finish, on });
    const m = { source: BRIDGE_PAGE, id, ...msg };
    // Два канала: postMessage и событие документа — на случай, если окружение страницы фильтрует postMessage.
    try { window.postMessage(m, '*'); } catch { /* окно закрывается */ }
    try { document.dispatchEvent(new CustomEvent(BRIDGE_EVT_IN, { detail: JSON.stringify(m) })); } catch { /* нет документа */ }
  });
}
async function sferaPing() {
  // Мост сразу отвечает SFERA_HELLO, затем фоновая часть расширения — SFERA_PONG (после сна ей нужно до пары секунд).
  let hello = false;
  const ac = new AbortController();
  const quiet = setTimeout(() => { if (!hello) ac.abort(); }, 1500);
  const r = await bridgeCall({ type: 'SFERA_PING' }, { timeout: 5000, until: ['SFERA_PONG', 'SFERA_ERROR'], signal: ac.signal, on: (d) => { if (d.type === 'SFERA_HELLO') hello = true; } });
  clearTimeout(quiet);
  S.sferaExt = r?.type === 'SFERA_PONG' ? { ok: true, version: r.version || '', baseUrl: r.baseUrl || '', bridge: !!r.bridge, bridgeVersion: r.bridgeVersion || '' }
    : { ok: false, stage: hello || r?.type === 'SFERA_ERROR' ? 'ext' : 'none', error: r?.type === 'SFERA_ERROR' ? r.error || '' : '', where: frameWhere() };
  if (S.sferaExt.ok) relayReceiverStart();
  return S.sferaExt;
}
const uuid4 = () => (typeof crypto?.randomUUID === 'function' ? crypto.randomUUID() : 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => { const r = Math.random() * 16 | 0; return (c === 'x' ? r : (r & 3) | 8).toString(16); }));
// Блок кода → <pre> редактора Сферы (как в самой Сфере): пояснение, пустой абзац, <pre data-id style> с переводом строки после тега, пустой абзац.
// Высоту редактор пересчитывает сам; здесь — по числу строк (в образце из Сферы: 1 строка кода = 47,99px).
const sferaPre = (code) => `<pre data-id="${uuid4()}" style="height: ${(code.split('\n').length + 1) * 24}px">\n${code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</pre>`;
function hp(s) {
  const out = [];
  for (const p of codeParts(s)) {   // явные блоки и JSON/SQL в строке (тела запроса и ответа API, Kafka, SQL)
    if (p.code) { out.push('<p></p>', sferaPre(p.text), '<p></p>'); continue; }
    const t = p.text.trim();
    if (t) out.push(`<p>${esc(t).replace(/\n/g, '<br>')}</p>`);
  }
  return out.length ? out.join('\n') : '<p></p>';
}
function sferaCase(c) {
  const t = tmsCase(c);
  return {
    ref: c.uid,
    qaId: c.dispId,
    name: t.title.slice(0, 256),
    description: t.description ? hp(t.description) : '',
    preConditions: t.pre.map((x) => ({ action: hp(x), expectedResult: '<p></p>' })),
    steps: t.steps.map((s) => ({ action: hp(s.action + (s.data ? `\nДанные: ${s.data}` : '')), expectedResult: hp(s.expected || '') })),
    postConditions: t.post.map((x) => ({ action: hp(x), expectedResult: '<p></p>' })),
    priority: normPrio(t.priority),
    suites: c.suites || [],
  };
}
function sferaApply(d, run = S.run) {
  if (!run || d.cancelled) return 0;
  let ok = 0;
  for (const r of d.results || []) {
    const c = run.cases.find((x) => x.uid === r.ref);
    if (!c) continue;
    if (r.ok) { c.tms = { kind: 'sfera', id: String(r.code || ''), url: '', at: Date.now() }; ok++; }
    else S.tmsLog.push({ kind: 'err', text: `${c.dispId}: Сфера ответила ${r.status || 'ошибкой'} — ${String(r.error || '').slice(0, 200)}` });
  }
  if (ok) queueSave(run);
  if (S.tab === 'cases') { renderCaseList(); renderTmsBar(); }
  return ok;
}
async function sferaUpload(cases) {
  if (S.tmsBusy || !cases.length) return;
  const ext = inDesktopApp && (relayOn() || hostOn()) ? { ok: false } : await sferaPing(); // в приложении Claude расширений не бывает
  if (!ext.ok && hostOn()) {
    // мост приложения → загрузчик напрямую; если загрузчик к мосту не подключён, а QA pro в Chrome на связи — через вкладку
    const h = await hostPing();
    if (h.ok && h.extension?.connected) return hostSend(cases);
    if (h.ok && !(relayOn() && (await relayPresence())?.online)) return hostSend(cases);
  }
  if (!ext.ok && relayOn()) return relaySend(cases);
  if (!ext.ok) { S.tmsLog = [{ kind: 'err', text: sferaNoExtText(ext) + ' Подробнее — шестерёнка → ТМС.' }]; return renderTmsBar(); }
  S.tmsBusy = true; S.tmsCtl = new AbortController();
  S.tmsLog = [{ kind: '', text: `Передаю ${cases.length} ${plural(cases.length, 'кейс', 'кейса', 'кейсов')} загрузчику…` }];
  renderTmsBar();
  const title = [curProduct()?.name, S.run?.docs?.[0]?.name].filter(Boolean).join(' · ');
  const r = await bridgeCall({ type: 'SFERA_UPLOAD', cases: cases.map(sferaCase), title }, {
    until: ['SFERA_RESULT', 'SFERA_ERROR'], signal: S.tmsCtl.signal,
    on: (d) => { if (d.type !== 'SFERA_OPENED') return; S.tmsLog[0] = { kind: '', text: 'Открылось окно загрузчика: выберите раздел Сферы ФТ и нажмите «Загрузить».' }; renderTmsBar(); },
  });
  S.tmsBusy = false;
  const ok = (r?.results || []).filter((x) => x.ok).length, bad = (r?.results || []).length - ok;
  S.tmsLog[0] = r?.type === 'ABORTED' ? { kind: 'warn', text: 'Перестал ждать загрузчик. Если загрузите кейсы в его окне, отметки всё равно появятся здесь.' }
    : r?.type === 'SFERA_ERROR' ? { kind: 'err', text: r.error || 'Загрузчик не ответил.' }
      : r?.cancelled ? { kind: 'warn', text: 'Окно загрузчика закрыто без загрузки.' }
        : { kind: bad ? 'warn' : 'ok', text: `Сфера ФТ: загружено ${ok}${bad ? `, с ошибкой ${bad}` : ''}${r?.section?.projectCode ? ` · проект ${r.section.projectCode}, раздел ${r.section.sectionId}` : ''}` };
  if (S.tab === 'cases') { renderCaseList(); renderTmsBar(); }
}
/* ---------- Сфера ФТ из приложения Claude для компьютера (и любого окна без загрузчика) ----------
   В приложении нет расширений браузера, поэтому задание идёт так:
   QA pro здесь → личная часть общей базы артефакта (data/users/<id>, видна только этому человеку)
   → QA pro, открытый во вкладке Chrome с загрузчиком (подхватывает задание) → мост → окно загрузчика → Сфера ФТ
   → результат обратно в базу → отметки «в ТМС» здесь. Кейсы лежат частями (документ базы — до 256 КиБ). */
const QA_PRO_URL = 'https://claude.ai/artifact/TrWQGTAs4Wqe5XjZBcQFCp';
const inDesktopApp = /Electron|Claude\//i.test(navigator.userAgent || '');
const RELAY_KIND = 'sfera_job', RELAY_TTL = 6 * 3600e3, RELAY_PRESENCE = 'sfera-relay', RELAY_BEAT = 120e3;
const relayOn = () => inClaude && !!S.caps.db && !!S.caps.uid;
// Устройство (браузер или приложение), отправившее задание: результат применяет только оно — даже после перезагрузки.
const DEVICE_ID = (() => { try { let v = localStorage.getItem('qapro.device'); if (!v) { v = rid('dev'); localStorage.setItem('qapro.device', v); } return v; } catch { return rid('dev'); } })();
const relayPath = (id) => `data/users/${S.caps.uid}/${id}`;
const relayRef = (id) => S.caps.db.doc(relayPath(id));
async function relayWriteParts(id, sub, items, maxBytes = 170000) {
  const chunks = []; let cur = [], size = 0;
  for (const x of items) {
    const n = new Blob([JSON.stringify(x)]).size;
    if (cur.length && size + n > maxBytes) { chunks.push(cur); cur = []; size = 0; }
    cur.push(x); size += n;
  }
  if (cur.length) chunks.push(cur);
  for (let i = 0; i < chunks.length; i++) await S.caps.db.doc(`${relayPath(id)}/${sub}/p${i}`).set({ items: chunks[i] });
  return chunks.length;
}
async function relayReadParts(id, sub, n) {
  const out = [];
  for (let i = 0; i < (n || 0); i++) out.push(...((await S.caps.db.doc(`${relayPath(id)}/${sub}/p${i}`).get()).data()?.items || []));
  return out;
}
async function relayDrop(id, d) {
  for (const [sub, n] of [['parts', d?.parts], ['res', d?.resParts]]) for (let i = 0; i < (n || 0); i++) { try { await S.caps.db.doc(`${relayPath(id)}/${sub}/p${i}`).delete(); } catch { /* уже удалён */ } }
  try { await relayRef(id).delete(); } catch { /* уже удалён */ }
}
async function relayPresence() {
  if (!relayOn()) return null;
  try {
    const d = (await relayRef(RELAY_PRESENCE).get()).data();
    S.relayPeer = d?.at ? { at: d.at, online: Date.now() - d.at < 2.5 * RELAY_BEAT, version: d.version || '' } : { online: false };
  } catch { S.relayPeer = { online: false }; }
  return S.relayPeer;
}
const RELAY_TEXT = {
  pending: () => S.relayPeer?.online ? 'Задание передано QA pro в Chrome — сейчас там откроется окно загрузчика.'
    : 'Задание ждёт QA pro в Chrome: откройте QA pro в Chrome, где установлен загрузчик, — окно загрузчика откроется там само.',
  taken: () => 'QA pro в Chrome принял задание и открывает окно загрузчика…',
  opened: () => 'В Chrome открылось окно загрузчика: выберите раздел Сферы ФТ и нажмите «Загрузить».',
};

// ----- отправитель (здесь нет загрузчика) -----
async function relaySend(cases) {
  const run = S.run;
  if (!run || S.tmsBusy) return;
  const items = cases.map(sferaCase), id = 'sfjob-' + rid('j');
  const title = [curProduct()?.name, run.docs?.[0]?.name].filter(Boolean).join(' · ') + (inDesktopApp ? ' · из приложения Claude' : '');
  S.tmsBusy = true; S.tmsCtl = new AbortController();
  S.relay = { id, run, status: 'sending', unsub: null };
  S.tmsLog = [{ kind: '', text: `Загрузчика в этом окне нет — передаю ${items.length} ${plural(items.length, 'кейс', 'кейса', 'кейсов')} через QA pro в Chrome…` }];
  renderTmsBar();
  relayPresence().then(() => { if (S.relay?.id === id && S.relay.status === 'pending') { S.tmsLog[0] = { kind: '', text: RELAY_TEXT.pending() }; renderTmsBar(); } });
  let d;
  try {
    const parts = await relayWriteParts(id, 'parts', items);
    d = { kind: RELAY_KIND, status: 'pending', createdAt: Date.now(), runId: run.id, productId: run.productId || '', title, count: items.length, parts, from: S.tabId, fromDevice: DEVICE_ID };
    await relayRef(id).set(d);
  } catch (e) {
    S.tmsBusy = false; S.relay = null;
    S.tmsLog = [{ kind: 'err', text: 'Не удалось передать задание в Chrome: ' + (e?.code === 'quota_exceeded' ? 'база артефакта заполнена — удалите старые запуски из истории.' : errText(e)) }];
    relayDrop(id, { parts: 99 }).catch(() => {});
    return renderTmsBar();
  }
  S.tmsCtl.signal.addEventListener('abort', () => relayCancel(id));
  relayWatch(id, run);
}
function relayWatch(id, run, status = 'sending') {
  S.tmsBusy = true;
  S.relay = { id, run, status, unsub: null };
  S.relay.unsub = relayRef(id).onSnapshot((snap) => relayOnSnap(id, snap), () => { /* подписка умерла — проверим при следующем открытии кейсов */ });
}
async function relayOnSnap(id, snap) {
  const st = S.relay;
  if (!st || st.id !== id) return;
  if (!snap.exists) { // задание удалили (отменили или завершили в другом окне)
    if (st.status === 'sending') return;
    st.unsub?.(); S.relay = null; S.tmsBusy = false;
    S.tmsLog = [{ kind: 'warn', text: 'Задание отменено или завершено в другом окне QA pro.' }];
    if (S.tab === 'cases') renderTmsBar();
    return;
  }
  const d = snap.data();
  if (!d || d.status === st.status) return;
  st.status = d.status;
  if (RELAY_TEXT[d.status]) { S.tmsLog[0] = { kind: '', text: RELAY_TEXT[d.status]() }; if (S.tab === 'cases') renderTmsBar(); return; }
  if (['done', 'cancelled', 'error'].includes(d.status)) await relayFinish(id, d, st.run);
}
async function relayFinish(id, d, run) {
  if (S.relay?.id === id) { S.relay.unsub?.(); S.relay = null; S.tmsBusy = false; }
  let results = [];
  if (d.status === 'done') { try { results = await relayReadParts(id, 'res', d.resParts); } catch { results = []; } }
  const target = (S.run?.id === d.runId ? S.run : null) || run; // запуск мог перезагрузиться из базы — берём актуальный объект
  if (d.status === 'done' && !target) return; // запуск не открыт — применим, когда его откроют
  S.tmsLog = [S.tmsLog[0] || { kind: '', text: '' }];
  const ok = d.status === 'done' ? sferaApply({ results }, target) : 0, bad = results.length - ok;
  S.tmsLog[0] = d.status === 'error' ? { kind: 'err', text: 'Загрузка через Chrome не удалась: ' + (d.error || 'загрузчик не ответил.') }
    : d.status === 'cancelled' ? { kind: 'warn', text: d.cancelledBy === 'sender' ? 'Задание отменено.' : 'Окно загрузчика в Chrome закрыто без загрузки.' }
      : { kind: bad ? 'warn' : 'ok', text: `Сфера ФТ (через Chrome): загружено ${ok}${bad ? `, с ошибкой ${bad}` : ''}${d.section?.projectCode ? ` · проект ${d.section.projectCode}, раздел ${d.section.sectionId}` : ''}` };
  await relayDrop(id, d);
  if (S.tab === 'cases') { renderCaseList(); renderTmsBar(); }
}
async function relayCancel(id) {
  const st = S.relay;
  if (!st || st.id !== id) return;
  st.unsub?.(); S.relay = null; S.tmsBusy = false;
  let d = null;
  try { d = (await relayRef(id).get()).data(); } catch { /* нет связи */ }
  if (!d || d.status === 'pending') {
    try { await relayRef(id).update({ status: 'cancelled', cancelledBy: 'sender' }); } catch { /* уже нет */ }
    relayDrop(id, d || { parts: 99 }).catch(() => {});
    S.tmsLog = [{ kind: 'warn', text: 'Задание отменено.' }];
  } else S.tmsLog = [{ kind: 'warn', text: 'Перестал ждать. Если загрузите кейсы в окне загрузчика в Chrome, отметки появятся здесь, когда вы снова откроете этот запуск.' }];
  if (S.tab === 'cases') renderTmsBar();
}
// После перезагрузки страницы или при открытии запуска: подхватываем свои незавершённые задания и готовые результаты.
const relayChecked = new Set();
async function relayCheck(run = S.run) {
  if (!relayOn() || !run || relayChecked.has(run.id) || S.relay) return;
  relayChecked.add(run.id);
  let snap;
  try { snap = await S.caps.db.collection(`data/users/${S.caps.uid}`).where('kind', '==', RELAY_KIND).where('runId', '==', run.id).get(); } catch { return; }
  for (const doc of snap.docs) {
    const d = doc.data();
    if (!d) continue;
    if (Date.now() - (d.createdAt || 0) > RELAY_TTL) { relayDrop(doc.id, d).catch(() => {}); continue; }
    if (d.fromDevice !== DEVICE_ID) continue; // чужое задание (например, принятое этой вкладкой Chrome) не трогаем
    if (['done', 'cancelled', 'error'].includes(d.status)) { if (run === S.run) await relayFinish(doc.id, d, run); }
    else if (!S.relay && run === S.run) {
      relayWatch(doc.id, run, d.status);
      S.tmsCtl = new AbortController(); S.tmsCtl.signal.addEventListener('abort', () => relayCancel(doc.id));
      S.tmsLog = [{ kind: '', text: (RELAY_TEXT[d.status] || RELAY_TEXT.pending)() }];
      if (S.tab === 'cases') renderTmsBar();
    }
  }
}

// ----- приёмник (QA pro во вкладке Chrome, где есть загрузчик) -----
let relayRx = null, relayBeatTimer = null;
const relayTaking = new Set();
function relayReceiverStart() {
  if (relayRx || !relayOn() || !S.sferaExt?.ok) return;
  const q = S.caps.db.collection(`data/users/${S.caps.uid}`).where('kind', '==', RELAY_KIND).where('status', '==', 'pending');
  relayRx = q.onSnapshot((snap) => { for (const doc of snap.docs) relayTake(doc.id, doc.data()); }, () => { relayRx = null; clearInterval(relayBeatTimer); });
  const beat = () => relayRef(RELAY_PRESENCE).set({ kind: 'sfera_relay', at: Date.now(), version: S.sferaExt?.version || '', tab: S.tabId }).catch(() => {});
  beat(); relayBeatTimer = setInterval(beat, RELAY_BEAT);
}
async function relayTake(id, d) {
  if (relayTaking.has(id) || !d || d.status !== 'pending' || d.from === S.tabId) return;
  relayTaking.add(id);
  const ref = relayRef(id);
  if (Date.now() - (d.createdAt || 0) > RELAY_TTL) return;
  let w = Promise.resolve(); // одна запись в документ за раз
  const write = (patch) => (w = w.then(() => ref.update(patch)).catch(() => {}));
  try {
    if (typeof ref.acquire === 'function') { const l = await ref.acquire({ holder: S.tabId, ttlMs: 20000 }); if (!l?.acquired) return; }
    const cur = (await ref.get()).data();
    if (!cur || cur.status !== 'pending') return;
    await write({ status: 'taken', takenBy: S.tabId, takenAt: Date.now() });
    const cases = await relayReadParts(id, 'parts', cur.parts);
    toast(`Задание из ${/приложения Claude/.test(cur.title || '') ? 'приложения Claude' : 'другого окна QA pro'}: ${cases.length} ${plural(cases.length, 'кейс', 'кейса', 'кейсов')} — открываю окно загрузчика`);
    const r = await bridgeCall({ type: 'SFERA_UPLOAD', cases, title: cur.title || 'QA pro' }, {
      until: ['SFERA_RESULT', 'SFERA_ERROR'], relay: true,
      on: (m) => { if (m.type === 'SFERA_OPENED') write({ status: 'opened', openedAt: Date.now() }); },
    });
    if (r?.type === 'SFERA_ERROR') await write({ status: 'error', error: String(r.error || '').slice(0, 300) });
    else if (r?.cancelled) await write({ status: 'cancelled', cancelledBy: 'uploader' });
    else {
      const res = (r?.results || []).map((x) => ({ ref: x.ref ?? null, ok: !!x.ok, code: String(x.code || ''), status: x.status || 0, error: String(x.error || '').slice(0, 300) }));
      const resParts = await relayWriteParts(id, 'res', res);
      await write({ status: 'done', resParts, section: r?.section || null, okCount: res.filter((x) => x.ok).length, doneAt: Date.now() });
    }
  } catch (e) { await write({ status: 'error', error: 'QA pro в Chrome: ' + errText(e) }); }
}
/* ---------- Сфера ФТ из приложения Claude через локальный мост qa-pro-bridge ----------
   Мост — расширение приложения Claude (MCP-сервер на этом компьютере). QA pro зовёт его как host:qa-pro-bridge,
   мост по WebSocket передаёт кейсы загрузчику в Chrome, загрузчик открывает своё окно и возвращает результат. */
// Приложение Claude называет установленный мост по его отображаемому имени (из .mcpb), заменяя всё,
// кроме латиницы, цифр, «_» и «-», на «_». При ручной настройке (claude_desktop_config.json) имя — ключ qa-pro-bridge.
const HOST_DISPLAY = 'QA pro — мост к загрузчику Сферы ФТ', HOST_KEY = 'qapro.hostjob', HOST_NAME_KEY = 'qapro.hostname';
const HOST_NAMES = ['host:' + HOST_DISPLAY.replace(/[^A-Za-z0-9_-]/g, '_'), 'host:qa-pro-bridge'];
let hostName = (() => { try { const v = localStorage.getItem(HOST_NAME_KEY); return HOST_NAMES.includes(v) ? v : HOST_NAMES[0]; } catch { return HOST_NAMES[0]; } })();
const hostOn = () => inClaude && !!S.caps.mcp && (S.hostListed || inDesktopApp);
const pause = (ms) => new Promise((r) => setTimeout(r, ms));
function hostErr(e) {
  switch (e?.code) {
    case 'server_not_connected': return 'Мост qa-pro-bridge не найден в приложении Claude: установите его (шестерёнка → ТМС → «Скачать мост») и перезапустите приложение.';
    case 'not_in_manifest': return 'Доступ QA pro к мосту выключен — включите его в разрешениях этой страницы.';
    case 'cancelled': return 'Вызов моста отклонён в окне подтверждения приложения.';
    case 'server_unavailable': return 'Мост не ответил вовремя — попробуйте ещё раз.';
    case 'tool_error': return 'Мост: ' + (e.message || 'ошибка');
    case 'not_granted': case 'capability_disabled': case 'capability_removed': return 'В этом окне QA pro не может обращаться к программам на компьютере.';
    default: return 'Мост не ответил' + (e?.message ? ': ' + e.message : '.');
  }
}
async function hostCall(tool, input, opts = {}) {
  const t0 = Date.now();
  diag(`мост → ${tool} ${input?.op || ''} ${(JSON.stringify(input) || '').length} зн.`, true);
  let r;
  try { r = await S.caps.mcp.callTool(hostName, tool, input, { cache: false, ...opts }); }
  catch (e) { diag(`мост ✗ ${tool} ${e?.code || ''} ${Date.now() - t0} мс`, true); throw e; }
  const p = r?.payload;
  diag(`мост ← ${tool} ${typeof p === 'string' ? p.length : (JSON.stringify(p) || '').length} зн. ${Date.now() - t0} мс`, true);
  if (typeof p === 'string') { const t = tryParse(p); return t.ok ? t.value : p; }
  return p;
}
async function hostPing() {
  try {
    let p, last;
    // Пробуем известные имена моста: сначала то, что сработало в прошлый раз.
    for (const name of [hostName, ...HOST_NAMES.filter((x) => x !== hostName)]) {
      try {
        p = (await S.caps.mcp.callTool(name, 'ping', {}, { cache: false }))?.payload;
        if (typeof p === 'string') { const t = tryParse(p); p = t.ok ? t.value : p; }
        hostName = name; try { localStorage.setItem(HOST_NAME_KEY, name); } catch { /* только память */ }
        last = null; break;
      } catch (e) { last = e; if (!['server_not_connected', 'not_in_manifest', 'server_not_found'].includes(e?.code)) break; }
    }
    if (last) throw last;
    S.hostBridge = { ok: !!p?.ok && p?.listening !== false, version: p?.version || '', core: p?.core || '', error: p?.error || '', extension: p?.extension || { connected: false } };
  } catch (e) { S.hostBridge = { ok: false, code: e?.code || '', error: hostErr(e), extension: { connected: false } }; }
  return S.hostBridge;
}
const HOST_TEXT = {
  queued: 'Задание у моста, но загрузчик в Chrome сейчас не подключён: откройте Chrome с загрузчиком — окно появится, как только он подключится.',
  sent: 'Задание передано загрузчику — в Chrome открывается окно…',
  opened: 'В Chrome открылось окно загрузчика: выберите раздел Сферы ФТ и нажмите «Загрузить».',
};
async function hostSend(cases) {
  const run = S.run;
  if (!run || S.tmsBusy) return;
  const items = cases.map(sferaCase);
  const size = new Blob([JSON.stringify(items)]).size;
  if (size > 900e3) { S.tmsLog = [{ kind: 'err', text: `Мост принимает за раз до ~900 КБ, а здесь ${Math.round(size / 1024)} КБ. Загрузите частями — например, отфильтровав кейсы по типу.` }]; return renderTmsBar(); }
  const title = [curProduct()?.name, run.docs?.[0]?.name].filter(Boolean).join(' · ') + ' · из приложения Claude';
  S.tmsBusy = true; S.tmsCtl = new AbortController();
  S.tmsLog = [{ kind: '', text: `Передаю ${items.length} ${plural(items.length, 'кейс', 'кейса', 'кейсов')} загрузчику через мост…` }];
  renderTmsBar();
  let p;
  try { p = await hostCall('sfera_upload', { cases: items, title }); }
  catch (e) { S.tmsBusy = false; S.tmsLog = [{ kind: e?.code === 'cancelled' ? 'warn' : 'err', text: hostErr(e) }]; return renderTmsBar(); }
  try { localStorage.setItem(HOST_KEY, JSON.stringify({ jobId: p.jobId, runId: run.id })); } catch { /* только память */ }
  hostFollow(p, run);
}
async function hostFollow(p, run) {
  const jobId = p.jobId;
  S.tmsBusy = true; S.hostJob = { jobId, run };
  if (!S.tmsCtl || S.tmsCtl.signal.aborted) S.tmsCtl = new AbortController();
  S.tmsCtl.signal.addEventListener('abort', () => hostCancel(jobId));
  let fails = 0;
  while (S.hostJob?.jobId === jobId) {
    if (['done', 'cancelled', 'error'].includes(p.status)) return hostFinish(p, run);
    if (HOST_TEXT[p.status] && S.tmsLog[0]?.text !== HOST_TEXT[p.status]) { S.tmsLog[0] = { kind: '', text: HOST_TEXT[p.status] }; if (S.tab === 'cases') renderTmsBar(); }
    try { p = await hostCall('sfera_job', { jobId, since: p.updatedAt || 0, waitMs: 20000 }); fails = 0; }
    catch (e) {
      if (S.hostJob?.jobId !== jobId) return;
      if (e?.code === 'tool_error' || e?.code === 'server_not_connected' || ++fails > 5) {
        hostDone(); S.tmsLog = [{ kind: 'err', text: hostErr(e) }];
        if (S.tab === 'cases') renderTmsBar();
        return;
      }
      await pause(1500 * fails);
    }
  }
}
function hostDone() { S.hostJob = null; S.tmsBusy = false; try { localStorage.removeItem(HOST_KEY); } catch { /* только память */ } }
function hostFinish(p, run) {
  hostDone();
  const target = (S.run?.id === run?.id ? S.run : null) || run;
  const results = p.results || [];
  S.tmsLog = [{ kind: '', text: '' }];
  const okN = p.status === 'done' ? sferaApply({ results }, target) : 0, bad = results.length - okN;
  S.tmsLog[0] = p.status === 'error' ? { kind: 'err', text: 'Загрузка не удалась: ' + (p.error || 'загрузчик не ответил.') }
    : p.status === 'cancelled' ? { kind: 'warn', text: 'Окно загрузчика закрыто без загрузки или задание отменено.' }
      : { kind: bad ? 'warn' : 'ok', text: `Сфера ФТ (через мост): загружено ${okN}${bad ? `, с ошибкой ${bad}` : ''}${p.section?.projectCode ? ` · проект ${p.section.projectCode}, раздел ${p.section.sectionId}` : ''}` };
  if (S.tab === 'cases') { renderCaseList(); renderTmsBar(); }
}
async function hostCancel(jobId) {
  if (S.hostJob?.jobId !== jobId) return;
  hostDone();
  S.tmsLog = [{ kind: 'warn', text: 'Отменяю задание…' }];
  if (S.tab === 'cases') renderTmsBar();
  try { await hostCall('sfera_cancel', { jobId }); S.tmsLog = [{ kind: 'warn', text: 'Задание отменено.' }]; }
  catch (e) { S.tmsLog = [{ kind: 'warn', text: 'Перестал ждать. ' + hostErr(e) }]; }
  if (S.tab === 'cases') renderTmsBar();
}
// После перезагрузки страницы продолжаем следить за своим заданием.
let hostResumed = false;
function hostResume() {
  if (hostResumed || !hostOn() || S.tmsBusy || !S.run) return;
  let saved = null;
  try { saved = JSON.parse(localStorage.getItem(HOST_KEY) || 'null'); } catch { /* нет хранилища */ }
  if (!saved?.jobId || saved.runId !== S.run.id) return;
  hostResumed = true;
  const run = S.run;
  hostCall('sfera_job', { jobId: saved.jobId })
    .then((p) => { if (!S.tmsBusy && p?.jobId) { S.tmsLog = [{ kind: '', text: HOST_TEXT[p.status] || 'Проверяю задание…' }]; hostFollow(p, run); } })
    .catch(() => { try { localStorage.removeItem(HOST_KEY); } catch { /* только память */ } });
}
function sferaExportJSON(cases) {
  return JSON.stringify({ format: 'qa-pro/sfera-v1', generatedAt: new Date().toISOString(), product: curProduct()?.name || '', cases: cases.map(sferaCase) }, null, 2);
}
function tmsHeaders(cfg) {
  if (cfg.kind === 'testit') return { Authorization: 'PrivateToken ' + cfg.token };
  if (cfg.kind === 'qase') return { Token: cfg.token };
  if (cfg.kind === 'testrail') return { Authorization: 'Basic ' + btoa(unescape(encodeURIComponent(`${cfg.user}:${cfg.token}`))) };
  const h = {};
  const p = tryParse(cfg.headers || '{}');
  if (p.ok && p.value && typeof p.value === 'object') for (const [a, b] of Object.entries(p.value)) h[a] = String(b);
  if (cfg.token && !Object.keys(h).some((x) => x.toLowerCase() === 'authorization')) h.Authorization = 'Bearer ' + cfg.token;
  return h;
}
const tmsBase = (cfg) => String(cfg.kind === 'custom' ? cfg.url : cfg.baseUrl || (cfg.kind === 'qase' ? 'https://api.qase.io/v1' : '')).replace(/\/+$/, '');
function tmsProblem(cfg = S.tms) {
  if (cfg.kind === 'sfera') return S.sferaExt?.ok === false && !relayOn() && !hostOn() ? sferaNoExtText() : '';
  const base = tmsBase(cfg);
  if (!base) return 'Укажите адрес API в настройках ТМС.';
  if (!cfg.token && cfg.kind !== 'custom') return 'Укажите токен в настройках ТМС.';
  if (cfg.kind === 'testit' && !cfg.project) return 'Укажите ID проекта Test IT.';
  if (cfg.kind === 'qase' && !cfg.project) return 'Укажите код проекта Qase.';
  if (cfg.kind === 'testrail' && (!cfg.section || !cfg.user)) return 'Укажите логин и ID раздела TestRail.';
  return '';
}
function tmsSummary(cfg = S.tms) {
  const p = tmsProblem(cfg);
  if (cfg.kind === 'sfera') return S.sferaExt?.ok ? `Сфера ФТ · через загрузчик ${S.sferaExt.version}${S.sferaExt.baseUrl ? ' · ' + hostOf(S.sferaExt.baseUrl) : ''}` : S.sferaExt && hostOn() && S.hostBridge?.ok ? `Сфера ФТ · через мост · загрузчик ${S.hostBridge.extension?.connected ? 'подключён' : 'не подключён'}` : S.sferaExt && relayOn() ? `Сфера ФТ · через QA pro в Chrome${S.relayPeer ? (S.relayPeer.online ? ' · на связи' : ' · не открыт') : ''}` : S.sferaExt ? 'Сфера ФТ · загрузчик не найден' : 'Сфера ФТ · проверяю загрузчик…';
  if (p) return 'ТМС не настроена';
  return `${TMS_KINDS[cfg.kind].name} · ${hostOf(tmsBase(cfg))}${cfg.project ? ' · проект ' + cfg.project : ''}`;
}
async function tmsTestConn(cfg) {
  if (cfg.kind === 'sfera') { const x = inDesktopApp && hostOn() ? { ok: false } : await sferaPing(); if (!x.ok && !S.sferaExt) S.sferaExt = x; let hostMsg = '';
    if (!x.ok && hostOn()) {
      const h = await hostPing();
      if (h.ok) return h.extension?.connected ? `Мост работает (${h.version}), загрузчик в Chrome подключён (${h.extension.version || 'версия неизвестна'}). Можно загружать.` : `Мост работает (${h.version}), но загрузчик в Chrome к нему не подключён: откройте Chrome и обновите загрузчик до версии 1.3 или новее.`;
      if (!relayOn()) throw { code: 'network', message: h.error };
      hostMsg = h.error;
    }
    if (!x.ok && relayOn()) { const peer = await relayPresence(); if (!peer?.online) throw { code: 'network', message: hostMsg ? `${hostMsg} Запасной путь — QA pro во вкладке Chrome — тоже не на связи.` : 'Загрузчика в этом окне нет, и QA pro в Chrome сейчас не на связи. Откройте QA pro в Chrome, где установлен загрузчик, и проверьте снова.' }; return hostMsg ? `Мост не найден — загрузка пойдёт запасным путём, через QA pro во вкладке Chrome (на связи, загрузчик ${peer.version || ''}).` : `Загрузчика в этом окне нет — загрузка пойдёт через QA pro в Chrome (на связи, загрузчик ${peer.version || ''}).`; } if (!x.ok) throw { code: 'network', message: sferaNoExtText(x) }; return `Загрузчик найден, версия ${x.version}. Сфера: ${x.baseUrl || 'адрес по умолчанию'}. Вход проверяется в окне загрузчика.`; }
  const base = tmsBase(cfg), h = tmsHeaders(cfg), signal = AbortSignal.timeout ? AbortSignal.timeout(30000) : undefined;
  if (cfg.kind === 'testit') { const r = await httpJSON(`${base}/api/v2/projects/${encodeURIComponent(cfg.project)}`, { method: 'GET', headers: h, signal, what: 'Test IT' }); const j = await r.json(); return `Проект найден: ${j.name || cfg.project}`; }
  if (cfg.kind === 'qase') { const r = await httpJSON(`${base}/project/${encodeURIComponent(cfg.project)}`, { method: 'GET', headers: h, signal, what: 'Qase' }); const j = await r.json(); return `Проект найден: ${j.result?.title || cfg.project}`; }
  if (cfg.kind === 'testrail') { const r = await httpJSON(`${base}/index.php?/api/v2/get_section/${encodeURIComponent(cfg.section)}`, { method: 'GET', headers: h, signal, what: 'TestRail' }); const j = await r.json(); return `Раздел найден: ${j.name || cfg.section}`; }
  return 'Для своего API проверка не выполняется — загрузите один кейс, чтобы проверить.';
}
const TI_PRIO = { P4_CRITICAL: 'Critical', P3_HIGH: 'High', P2_MEDIUM: 'Medium', P1_LOW: 'Low' };
async function tmsUpload(cases) {
  const cfg = S.tms;
  if (cfg.kind === 'sfera') return sferaUpload(cases);
  if (S.tmsBusy || !cases.length) return;
  const problem = inClaude ? 'На claude.ai страница изолирована от интернета, поэтому загрузка в ТМС работает в автономной версии QA pro.' : tmsProblem(cfg);
  if (problem) { S.tmsLog = [{ kind: 'err', text: problem }]; return renderTmsBar(); }
  S.tmsBusy = true; S.tmsCtl = new AbortController();
  const signal = S.tmsCtl.signal, base = tmsBase(cfg), h = tmsHeaders(cfg), name = TMS_KINDS[cfg.kind].name;
  S.tmsLog = [{ kind: '', text: `Загружаю ${cases.length} ${plural(cases.length, 'кейс', 'кейса', 'кейсов')} в ${name}…` }];
  renderTmsBar();
  let ok = 0, fail = 0;
  const mark = (c, id, url) => { c.tms = { kind: cfg.kind, id: String(id ?? ''), url: url || '', at: Date.now() }; ok++; };
  const err = (c, e) => { fail++; S.tmsLog.push({ kind: 'err', text: `${c ? c.dispId + ': ' : ''}${errText(e)}` }); };
  try {
    if (cfg.kind === 'qase') {
      for (let i = 0; i < cases.length && !signal.aborted; i += 20) {
        const chunk = cases.slice(i, i + 20);
        try {
          const body = { cases: chunk.map((c) => { const t = tmsCase(c); const o = { title: t.title, description: t.description, preconditions: t.pre.join('\n'), postconditions: t.post.join('\n'), priority: { P1_LOW: 3, P2_MEDIUM: 2, P3_HIGH: 1, P4_CRITICAL: 1 }[t.priority], steps: t.steps.map((s) => ({ action: s.action, expected_result: s.expected, data: s.data })), tags: t.tags }; if (cfg.section) o.suite_id = Number(cfg.section); return o; }) };
          const r = await httpJSON(`${base}/case/${encodeURIComponent(cfg.project)}/bulk`, { headers: h, body, signal, what: 'Qase' });
          const j = await r.json().catch(() => ({}));
          const ids = arrOf(j.result?.ids);
          chunk.forEach((c, k) => mark(c, ids[k]));
        } catch (e) { if (e?.code === 'cancelled') break; chunk.forEach((c) => err(c, e)); if (FATAL.has(e?.code)) break; }
        renderTmsBar();
      }
    } else if (cfg.kind === 'custom' && cfg.mode === 'all') {
      try {
        const r = await httpJSON(base, { headers: h, body: { generatedAt: new Date().toISOString(), cases: cases.map((c) => ({ ...casePayload(c), normalized: tmsCase(c) })) }, signal, what: 'API' });
        await r.text().catch(() => '');
        cases.forEach((c) => mark(c, ''));
      } catch (e) { if (e?.code !== 'cancelled') cases.forEach((c) => err(c, e)); }
    } else {
      let stop = false;
      await pool(cases, 2, async (c) => {
        if (stop) return;
        const t = tmsCase(c);
        try {
          if (cfg.kind === 'testit') {
            const step = (s) => ({ action: s.action, expected: s.expected, testData: s.data, comments: '' });
            const body = {
              projectId: cfg.project, name: t.title, entityTypeName: 'TestCases', state: cfg.state || 'NotReady', priority: TI_PRIO[t.priority],
              duration: Math.max(1, Number(cfg.duration) || 10) * 60000, description: t.description, attributes: {},
              preconditionSteps: t.pre.map((p) => step({ action: p, expected: '', data: '' })), steps: t.steps.map(step),
              postconditionSteps: t.post.map((p) => step({ action: p, expected: '', data: '' })), tags: t.tags.map((x) => ({ name: x })), links: [],
            };
            if (cfg.section) body.sectionId = cfg.section;
            const r = await httpJSON(`${base}/api/v2/workItems`, { headers: h, body, signal, what: 'Test IT' });
            const j = await r.json().catch(() => ({}));
            mark(c, j.globalId || j.id, '');
          } else if (cfg.kind === 'testrail') {
            const body = {
              title: t.title, priority_id: { P1_LOW: 1, P2_MEDIUM: 2, P3_HIGH: 3, P4_CRITICAL: 4 }[t.priority], custom_preconds: t.pre.join('\n'), refs: c.requirementIds.join(','),
              custom_steps_separated: t.steps.map((s) => ({ content: s.action + (s.data ? `\nДанные: ${s.data}` : ''), expected: s.expected })),
            };
            const r = await httpJSON(`${base}/index.php?/api/v2/add_case/${encodeURIComponent(cfg.section)}`, { headers: h, body, signal, what: 'TestRail' });
            const j = await r.json().catch(() => ({}));
            mark(c, j.id ? 'C' + j.id : '', j.id ? `${base}/index.php?/cases/view/${j.id}` : '');
          } else {
            const r = await httpJSON(base, { headers: h, body: { ...casePayload(c), normalized: t }, signal, what: 'API' });
            const j = await r.json().catch(() => ({}));
            mark(c, j.id || j.key || '');
          }
        } catch (e) { if (e?.code === 'cancelled') { stop = true; return; } err(c, e); if (FATAL.has(e?.code)) stop = true; }
        renderTmsBar();
      }, signal);
    }
  } finally {
    S.tmsBusy = false;
    S.tmsLog[0] = { kind: fail ? 'warn' : 'ok', text: `${name}: загружено ${ok}${fail ? `, с ошибкой ${fail}` : ''}${signal.aborted ? ' · остановлено' : ''}` };
    if (ok) queueSave(S.run);
    if (S.tab === 'cases') { renderCaseList(); renderTmsBar(); }
  }
}

/* ================= сессия: восстановление и продолжение ================= */
const HB_STALE = 90000; // фоновая вкладка браузера отмечается не чаще раза в минуту — оставляем запас
let dirtyNote = null;
function markDirty(run) {
  if (!run || !S.caps.db || !S.caps.uid || run !== S.run || run.fromHistory === 'readonly' || run.fromHistory === 'follow' || !S.running) return;
  if (run._dt) return;
  run._dt = setTimeout(() => {
    run._dt = null;
    saveChain = saveChain.then(() => saveRun(run)).catch(() => { if (!dirtyNote) { dirtyNote = 1; toast('Не удалось сохранить прогресс — проверьте место в хранилище.', 'err'); } });
  }, 2500);
}
const sesBase = () => `data/users/${S.caps.uid}/session`;
const sesRef = () => (S.caps.db && S.caps.uid ? S.caps.db.doc(sesBase()) : null);
async function readSession() { const ref = sesRef(); if (!ref) return null; try { return (await ref.get()).data() || null; } catch { return null; } }
let sesTimer = null, sesChain = Promise.resolve(), hbTimer = null;
function saveSession() { clearTimeout(sesTimer); sesTimer = setTimeout(flushSessionNow, 700); }
function flushSessionNow() {
  clearTimeout(sesTimer);
  const ref = sesRef();
  if (!ref || !S.sessionReady || S.follow) return sesChain;
  if (workerOn() && !S.running) return sesChain; // сессия — окна, где работает человек; фоновый исполнитель пишет её только во время генерации
  const open = S.run && S.run.fromHistory !== 'readonly' ? S.run : null;
  const data = {
    kind: 'session', updatedAt: Date.now(), tab: S.tab, productId: S.productId || null,
    runId: open ? open.id : null, runPid: open ? open.productId || null : null,
    runningBy: S.running && !S.unloading ? S.tabId : null, heartbeat: S.running && !S.unloading ? Date.now() : 0,
  };
  sesChain = sesChain.then(() => ref.set(data)).catch(() => {});
  return sesChain;
}
/* пульс идёт и в личную сессию, и в сам запуск — так коллеги видят, что генерация ещё идёт */
function beat() {
  flushSessionNow();
  const run = S.run;
  if (!S.running || !run || S.unloading || !S.caps.db || !S.caps.uid) return;
  saveChain = saveChain.then(() => S.caps.db.doc(runPath(run)).update({ hb: Date.now(), hbTab: S.tabId })).catch(() => {});
}
function startHeartbeat() { stopHeartbeat(); flushSessionNow(); hbTimer = setInterval(beat, 10000); }
function stopHeartbeat() { clearInterval(hbTimer); hbTimer = null; }
async function restoreRun(ses) {
  if (!ses) return;
  if (!ses.runId || S.run || S.running) { if (ses.tab && !S.running && !S.run) S.tab = ses.tab; return; }
  const pid = 'runPid' in ses ? ses.runPid || null : null;
  if (pid && pid !== S.productId) return;
  const ok = await openHistory(ses.runId, { silent: true, tab: ses.tab, auto: true, pid });
  if (!ok && ses.runningBy && ses.runningBy !== S.tabId && Date.now() - (ses.heartbeat || 0) < HB_STALE) startFollow(ses.runId, pid);
  else if (ok && !S.follow && S.run?.status !== 'interrupted') toast('Сессия восстановлена');
}
async function reconcileRunning(run, { auto = false } = {}) {
  if (run.status !== 'running') return;
  const ses = await readSession();
  const sesAlive = ses && ses.runId === run.id && ses.runningBy && ses.runningBy !== S.tabId && Date.now() - (ses.heartbeat || 0) < HB_STALE;
  const metaAlive = run.hb && run.hbTab !== S.tabId && Date.now() - run.hb < HB_STALE;
  if (sesAlive || metaAlive) { run.fromHistory = 'follow'; startFollow(run.id, run.productId || null); return; }
  const st = STEPS.find((s) => run.steps[s.id].status === 'running');
  for (const s of STEPS) {
    const step = run.steps[s.id];
    if (step.status !== 'running') continue;
    step.status = 'stopped';
    for (const l of step.log) if (!l.kind && /думает|читает|пишет|Дополняю/.test(l.text)) { l.text = l.text.replace(/(: .*|…)$/, ': прервано при закрытии страницы'); l.kind = 'warn'; }
  }
  run.finishedAt = run.updatedAt || Date.now();
  if (st?.optional) { run.status = 'stopped'; run.interrupted = st.id; }
  else {
    run.status = 'interrupted';
    const mine = !run.by || run.by === S.caps.uid;
    if (auto && mine && S.settings.autoResume && aiReady(run.settings.genAI || S.settings.genAI)) startResumeCountdown();
  }
}
function startFollow(runId, pid = S.productId) {
  stopFollow();
  const f = S.follow = { runId, pid, last: 0, t: null };
  const tick = async () => {
    if (S.follow !== f) return;
    try {
      const meta = (await S.caps.db.doc(`${runBase(pid)}/${runId}`).get()).data();
      const ses = await readSession();
      if (S.follow !== f) return;
      if (meta && meta.updatedAt !== f.last) { f.last = meta.updatedAt; await openHistory(runId, { silent: true, follow: true, pid }); }
      const sesAlive = ses && ses.runId === runId && ses.runningBy && ses.runningBy !== S.tabId && Date.now() - (ses.heartbeat || 0) < HB_STALE;
      const metaAlive = meta && meta.hb && meta.hbTab !== S.tabId && Date.now() - meta.hb < HB_STALE;
      const alive = sesAlive || metaAlive;
      f.stale = alive ? 0 : (f.stale || 0) + 1;
      if (f.stale === 1 && meta?.status === 'running') { f.t = setTimeout(tick, 3000); return; } // ждём финальное сохранение
      if (!alive || (meta && meta.status !== 'running')) {
        stopFollow();
        if (S.run?.id === runId) {
          S.run.fromHistory = true;
          if (S.run.status === 'running') { S.run.hb = 0; await reconcileRunning(S.run, { auto: true }); }
          toast(meta?.status === 'running' ? 'Генерация в другой вкладке остановилась — её можно продолжить здесь' : 'Генерация в другой вкладке завершена');
          if (S.run.productId && S.run.productId === S.productId) loadProductIndex(S.productId);
        } else if (meta && !S.running) {
          await openHistory(runId, { silent: true, pid });
        }
        renderAll();
        return;
      }
    } catch (e) { if (window.__QA_DEBUG) console.error('follow tick', e?.stack || e); }
    if (S.follow !== f) return;
    f.t = setTimeout(tick, 4000);
    renderRunControls();
  };
  tick();
}
function stopFollow() { if (S.follow?.t) clearTimeout(S.follow.t); S.follow = null; }
function startResumeCountdown() {
  cancelResumeCountdown();
  const r = S.resume = { left: 5, t: null };
  r.t = setInterval(() => {
    if (S.resume !== r) return;
    r.left--;
    if (r.left <= 0) { resumeRun(); return; }
    const el = $('#resume-left');
    if (el) el.textContent = r.left;
  }, 1000);
}
function cancelResumeCountdown() { if (S.resume?.t) clearInterval(S.resume.t); S.resume = null; }
/* ================= фоновый исполнитель ================= */
// QA pro, открытый во вкладке браузера (лучше Chrome с загрузчиком), может быть «фоновым исполнителем»: когда окно,
// где шла работа, закрывают, он её доделывает — продолжает генерацию с места остановки, разбирает новые документы
// в базу знаний и принимает задания на загрузку в Сферу. Включается в этом браузере: шестерёнка → Фон.
const WORKER_KEY = 'qapro.worker', WORKER_DOC = 'worker', WORKER_TICK = 20000, WORKER_FRESH = 180000;
const workerAllowed = () => inClaude && !!S.caps.db && !!S.caps.uid && !inDesktopApp;
const workerOn = () => workerAllowed() && lsGet(WORKER_KEY, false) === true;
const W = { timer: null, unsub: null, busy: false, last: 0, beatAt: 0, note: '', kbSkip: new Map() };
function workerStart() {
  if (!workerOn() || W.timer) return;
  W.timer = setInterval(workerTick, WORKER_TICK);
  try { W.unsub = sesRef()?.onSnapshot(() => workerTick(), () => { W.unsub = null; }) || null; } catch { W.unsub = null; }
  workerBeat(true);
  workerTick();
}
function workerStop() {
  clearInterval(W.timer); W.timer = null; W.unsub?.(); W.unsub = null;
  if (S.caps.db && S.caps.uid) relayRef(WORKER_DOC).delete().catch(() => {});
}
function workerBeat(force) {
  if (!force && Date.now() - W.beatAt < 50000) return;
  W.beatAt = Date.now();
  relayRef(WORKER_DOC).set({ kind: 'worker', at: Date.now(), tab: S.tabId, ai: aiLabel(S.settings.genAI), aiReady: aiReady(S.settings.genAI), uploader: !!S.sferaExt?.ok, doing: W.note || '' }).catch(() => {});
}
async function workerPeer() {
  if (!S.caps.db || !S.caps.uid) return (S.workerPeer = null);
  try {
    const d = (await relayRef(WORKER_DOC).get()).data();
    S.workerPeer = d?.at ? { ...d, online: Date.now() - d.at < WORKER_FRESH, self: d.tab === S.tabId } : { online: false };
  } catch { S.workerPeer = { online: false }; }
  return S.workerPeer;
}
async function workerTick() {
  if (!workerOn() || !S.prodReady || !S.sessionReady) return;
  workerBeat();
  if (S.running || S.kb.job.busy || S.switching || S.follow || S.resume) return;
  if (W.busy || Date.now() - W.last < 3000) { clearTimeout(W.retry); W.retry = setTimeout(workerTick, 3200); return; } // изменение не теряем: проверим чуть позже
  W.busy = true; W.last = Date.now();
  try { if (!(await workerTakeRun())) await workerKb(); }
  catch (e) { if (window.__QA_DEBUG) console.error('worker', e?.stack || e); }
  finally { W.busy = false; if (!S.running && !S.kb.job.busy && W.note) { W.note = ''; workerBeat(true); } }
}
// Генерация, брошенная закрытым окном: пульса нет (или окно успело сказать, что закрывается), запуск мой и не завершён.
async function workerTakeRun() {
  const ses = await readSession();
  if (!ses?.runId) return false;
  const pid = 'runPid' in ses ? ses.runPid || null : null;
  const ref = S.caps.db.doc(`${runBase(pid)}/${ses.runId}`);
  let meta = null;
  try { meta = (await ref.get()).data(); } catch { return false; }
  if (!meta || meta.status !== 'running' || (meta.by && meta.by !== S.caps.uid)) return false;
  const sesAlive = ses.runningBy && ses.runningBy !== S.tabId && Date.now() - (ses.heartbeat || 0) < HB_STALE;
  const metaAlive = meta.hb && meta.hbTab !== S.tabId && Date.now() - meta.hb < HB_STALE;
  if (sesAlive || metaAlive) return false; // окно с генерацией ещё работает
  if (!aiReady(S.settings.genAI)) { W.note = 'ждёт модель'; workerBeat(true); return false; }
  if (typeof ref.acquire === 'function') {
    try { if (!(await ref.acquire({ holder: S.tabId, ttlMs: 60000 }))?.acquired) return false; } catch { return false; }
  }
  if (pid && pid !== S.productId && !(await switchProduct(pid, { restore: true }))) return false;
  const ok = await openHistory(ses.runId, { silent: true, pid, tab: 'agent' });
  if (!ok || S.run?.id !== ses.runId || S.follow || S.run.status !== 'interrupted') return false;
  if (!aiReady(S.run.settings.genAI)) S.run.settings.genAI = S.settings.genAI; // модель окна-источника здесь недоступна (ключ хранится там)
  cancelResumeCountdown();
  W.note = 'генерация'; workerBeat(true);
  toast('Фоновый исполнитель продолжает генерацию из закрытого окна');
  resumeRun();
  return true;
}
// Документы, добавленные в окне, которое закрыли до конца разбора в базу знаний.
async function workerKb() {
  if (!S.settings.kbAuto || !aiReady(S.settings.genAI)) return false;
  diag('фон: проверка базы знаний');
  const ses = await readSession();
  const pid = ses?.productId || S.productId;
  if (!pid || !S.products.some((p) => p.id === pid)) return false;
  const sig = () => S.docs.map((d) => d.id + ':' + (d.chars || 0)).join('|');
  const skip = W.kbSkip.get(pid);
  if (pid === S.productId && skip && skip.until > Date.now() && skip.sig === sig()) return false; // документы не менялись — проверено недавно
  if (pid !== S.productId && !(await switchProduct(pid, { restore: true }))) return false;
  if (S.docs.some((d) => d.status === 'loading')) return false; // документы ещё загружаются — посмотрим на следующем такте
  if (!S.kb.loaded) return false;
  const pend = kbPending();
  if (!pend.length) { W.kbSkip.set(pid, { until: Date.now() + 600000, sig: sig() }); return false; }
  W.note = 'база знаний'; workerBeat(true);
  await kbRun(pend);
  W.kbSkip.set(pid, { until: Date.now() + 120000, sig: sig() }); // неудачные документы повторим не раньше чем через 2 минуты
  return true;
}
/* «Новый запуск»: закрываем текущий результат, документы и знания продукта остаются */
async function newSession() {
  if (S.running) return toast('Сначала остановите генерацию.', 'err');
  stopFollow(); cancelResumeCountdown();
  S.run = null; S.tab = 'agent'; S.caseUI.clear(); S.reqOpen.clear(); S.exp = null;
  // новый запуск — с чистого списка документов: они остаются в продукте и базе знаний
  if (S.productId) { S.runDocs.clear(); saveRunDocs(); }
  await flushSessionNow();
  renderAll(); toast(S.productId ? 'Результат сохранён в «Истории». Загрузите документы для нового запуска — база знаний и контекст продукта на месте.' : 'Результат сохранён в «Истории».');
}

/* ================= продукты: общий для команды контекст ================= */
const DOC_CH = 90000;
const IDX_MAX = 110000;
const sortProducts = (list) => list.slice().sort((a, b) => String(a.name || '').localeCompare(String(b.name || ''), 'ru'));
const productById = (pid) => S.products.find((p) => p.id === pid) || null;
function curProduct() { return productById(S.productId); }
/* «Что агент знает о продукте» хранится отдельной записью meta/passport вместе с прежней версией; длинный текст —
   частями по 60 тыс. знаков (meta/passport_t1…, прежняя версия — meta/passport_p0…): запись хранилища — до 240 КБ,
   а в карточке продукта — только отметка { ext, updatedAt, len }: так карточка не упирается в лимит записи и вмещает
   список из сотен документов. Старые паспорта прямо в карточке читаются как раньше и переезжают при первом сохранении. */
const passRef = (pid) => S.caps.db.doc(`${prodPath(pid)}/meta/passport`);
const passCache = {}, passLoading = {};
const PASSPORT_PART = 60000;      // знаков в одной части: даже по 4 байта на знак — меньше 240 КБ
const PASSPORT_INLINE = 200000;   // байт: до этого паспорт и прежняя версия — одной записью, как раньше
const passPartRef = (pid, kind, i) => S.caps.db.doc(`${prodPath(pid)}/meta/passport_${kind}${i}`);
const passChunks = (s) => { const out = []; for (let i = 0; i < s.length; i += PASSPORT_PART) out.push(s.slice(i, i + PASSPORT_PART)); return out.length ? out : ['']; };
async function passWrite(pid, rec) {
  const prevText = String(rec.prev?.text || '');
  if (new TextEncoder().encode(rec.text + prevText).length <= PASSPORT_INLINE) return passRef(pid).set(rec); // одной записью
  const t = passChunks(rec.text), p = rec.prev ? passChunks(prevText) : [];
  for (let i = 1; i < t.length; i++) await passPartRef(pid, 't', i).set({ s: t[i] });
  for (let i = 0; i < p.length; i++) await passPartRef(pid, 'p', i).set({ s: p[i] });
  // главная запись — последней: первая часть текста и число частей; прежняя версия — только в частях
  return passRef(pid).set({ ...rec, text: t[0], parts: t.length, prev: rec.prev ? { updatedAt: rec.prev.updatedAt || 0, text: '', parts: p.length } : null });
}
async function passRead(pid) {
  const d = (await passRef(pid).get()).data() || {};
  let text = String(d.text || '');
  for (let i = 1; i < (d.parts || 1); i++) text += ((await passPartRef(pid, 't', i).get()).data() || {}).s || '';
  let prev = d.prev || null;
  if (prev && prev.parts) {
    let pt = '';
    for (let i = 0; i < prev.parts; i++) pt += ((await passPartRef(pid, 'p', i).get()).data() || {}).s || '';
    prev = { text: pt, updatedAt: prev.updatedAt || 0 };
  }
  return { ...d, text, prev };
}
function hydrateProd(p) {
  const ov = ctxPassportFor(p?.id); // источник контекста — репозиторий: паспорт из products/<папка>/passport.md
  if (ov != null) return { ...p, passport: { ...(p.passport || {}), text: ov } };
  if (!p?.passport?.ext) return p;
  const c = passCache[p.id];
  if (c && c.at === p.passport.updatedAt) return { ...p, passport: { ...p.passport, text: c.text }, passportPrev: c.prev || null };
  loadPassText(p.id, p.passport.updatedAt);
  return p;
}
async function loadPassText(pid, at) {
  if (passLoading[pid] === at || !S.caps.db) return;
  passLoading[pid] = at;
  try {
    const d = await passRead(pid);
    passCache[pid] = { at: d.updatedAt || at, text: String(d.text || ''), prev: d.prev || null };
    const cur = S.products.find((x) => x.id === pid);
    if (cur) { upsertLocalProduct(pid, cur); if (S.productId === pid) { renderProduct(); if (S.tab === 'agent' && !S.run) renderTab(); } }
  } catch { /* загрузится при следующем обращении */ }
  finally { if (passLoading[pid] === at) delete passLoading[pid]; }
}
function upsertLocalProduct(pid, data) {
  const p = hydrateProd({ ...data, id: pid });
  S.products = sortProducts([...S.products.filter((x) => x.id !== pid), p]);
  return p;
}
async function readProduct(pid) {
  const d = (await S.caps.db.doc(prodPath(pid)).get()).data();
  if (!d) return null;
  const p = { ...d, id: pid };
  if (p.passport?.ext && passCache[pid]?.at !== p.passport.updatedAt) {
    try { const x = await passRead(pid); passCache[pid] = { at: x.updatedAt || p.passport.updatedAt, text: String(x.text || ''), prev: x.prev || null }; } catch { /* без текста */ }
  }
  return hydrateProd(p);
}
let prodChain = Promise.resolve();
/* изменения продукта идут по очереди; mut получает свежую версию документа */
function updateProduct(pid, mut) {
  const job = prodChain.then(async () => {
    const ref = S.caps.db.doc(prodPath(pid));
    const cur = (await ref.get()).data();
    if (!cur) throw new Error('Продукт не найден');
    const patch = typeof mut === 'function' ? mut(cur) : { ...mut };
    if (!patch || Object.keys(patch).every((k) => JSON.stringify(cur[k]) === JSON.stringify(patch[k]))) return upsertLocalProduct(pid, cur);
    patch.updatedAt = Date.now();
    await ref.update(patch);
    return upsertLocalProduct(pid, { ...cur, ...patch });
  });
  prodChain = job.catch(() => {});
  return job;
}
async function createProduct(name, description = '', seed = {}) {
  const id = seed.id || rid('p'), now = Date.now();
  const data = {
    kind: 'product', name: String(name || 'Продукт').trim().slice(0, 80) || 'Продукт', description: String(description || '').trim().slice(0, 500),
    createdAt: now, createdBy: S.caps.uid || '', updatedAt: now,
    qaCtx: { all: '', api: '', ui: '', e2e: '', ...(seed.qaCtx || {}) }, docs: seed.docs || [],
    passport: null, passportPrev: null, counters: { api: 0, ui: 0, e2e: 0, cl: 0 }, stats: { cases: 0, checklist: 0, lastRunAt: 0 },
  };
  await S.caps.db.doc(prodPath(id)).set(data);
  upsertLocalProduct(id, data);
  return id;
}
/* ---------- документы продукта ---------- */
function docMeta(d) { return { id: d.id, name: d.name, ext: d.ext, chars: d.chars, warn: d.warn || '', parts: d.savedParts || 0, sample: !!d.sample, addedAt: d.addedAt || Date.now(), by: d.by || S.caps.uid || '', ...(d.openapi ? { openapi: true } : {}), ...(d.source ? { source: d.source, video: d.video || null } : {}) }; }
async function addDocMeta(pid, d) {
  try { await updateProduct(pid, (p) => ({ docs: [...arrOf(p.docs).filter((x) => x.id !== d.id), docMeta(d)] })); }
  catch { toast(`Документ «${d.name}» не добавлен в продукт — нет прав на запись.`, 'err'); }
}
let apiFilterT = null;
function scheduleApiFilter() { clearTimeout(apiFilterT); apiFilterT = setTimeout(applyApiFilter, 500); }
/* фильтр «API» применяется к спецификациям этой сессии сразу; восстановленные из продукта — при следующей загрузке файла */
async function applyApiFilter() {
  const hint = $('#api-hint');
  const specs = S.docs.filter((d) => d.openapi && d.pid === S.productId);
  const live = specs.filter((d) => rawSpecs.has(d.id));
  for (const d of live) {
    const raw = rawSpecs.get(d.id);
    let r = null;
    try { r = await parseSpec(raw.ext, raw.buf); } catch (e) { d.status = 'error'; d.error = e.message || String(e); d.text = ''; d.chars = 0; d.warn = ''; continue; }
    d.status = 'ready'; d.error = '';
    d.text = r.text; d.chars = d.text.length; d.warn = r.warn;
    if (d.savedParts) {
      for (let i = 0; i < d.savedParts; i++) { try { await S.caps.db.doc(`${prodPath(d.pid)}/docparts/${d.id}_${i}`).delete(); } catch { /* части уже нет */ } }
      d.savedParts = 0; await persistDocText(d);
    }
  }
  if (hint && specs.length) hint.textContent = live.length ? 'Фильтр применён к загруженной спецификации.' : 'Спецификация сохранена в продукте: фильтр применится, когда загрузите её заново.';
  invalidateIndex(); renderDocs(); renderRunControls(); renderProduct();
}
async function persistDocText(d) {
  const pid = d.pid;
  if (d.sample || d.savedParts || !pid || !S.caps.db || !S.caps.uid) return;
  const n = Math.max(1, Math.ceil(d.text.length / DOC_CH));
  d.persisting = true;
  try {
    for (let i = 0; i < n; i++) await S.caps.db.doc(`${prodPath(pid)}/docparts/${d.id}_${i}`).set({ docId: d.id, i, text: d.text.slice(i * DOC_CH, (i + 1) * DOC_CH) });
    d.savedParts = n;
    await addDocMeta(pid, d);
    if (S.settings.kbAuto) kbQueue(d);
  } catch { toast(`Документ «${d.name}» не сохранён в продукте — не хватило места или прав.`, 'err'); }
  finally { d.persisting = false; }
}
async function dropDocText(d) {
  const pid = d.pid;
  if (!pid || !S.caps.db) return;
  try { await updateProduct(pid, (p) => ({ docs: arrOf(p.docs).filter((x) => x.id !== d.id) })); } catch { return toast('Не удалось убрать документ из продукта.', 'err'); }
  S.kb.queue = S.kb.queue.filter((x) => x.id !== d.id);
  kbForgetDoc(pid, d.id).then((ids) => {
    renderKbAny();
    if (ids?.length && S.settings.kbAuto && aiReady(S.settings.genAI) && S.productId === pid) kbSynthJob(ids);
  }).catch(() => {});
  for (let i = 0; i < (d.savedParts || 0); i++) { try { await S.caps.db.doc(`${prodPath(pid)}/docparts/${d.id}_${i}`).delete(); } catch { /* уже удалён */ } }
}
async function loadDocText(pid, m) {
  let text = '';
  for (let i = 0; i < (m.parts || 0); i++) text += (await S.caps.db.doc(`${prodPath(pid)}/docparts/${m.id}_${i}`).get()).data()?.text || '';
  return text;
}
function docFromMeta(pid, m) {
  if (m.sample) return { ...sampleDocObj(), id: m.id, pid, addedAt: m.addedAt, by: m.by };
  return { id: m.id, pid, name: m.name, ext: m.ext, size: (m.chars || 0) * 2, status: 'loading', text: '', chars: m.chars || 0, error: '', warn: m.warn || '', preview: false, savedParts: m.parts, addedAt: m.addedAt, by: m.by, ...(m.openapi ? { openapi: true } : {}), ...(m.source ? { source: m.source, video: m.video || null } : {}) };
}
/* список документов продукта сверяется с хранилищем: коллеги могли добавить или убрать файлы */
async function syncProductDocs(prod) {
  const pid = prod.id;
  if (S.productId !== pid) return;
  const metas = arrOf(prod.docs), ids = new Set(metas.map((m) => m.id));
  const before = S.docs.length;
  S.docs = S.docs.filter((d) => !(d.pid === pid && (d.savedParts || d.sample) && !d.persisting && !ids.has(d.id)));
  let changed = S.docs.length !== before;
  const loads = [];
  // впервые в продукте на этом компьютере: если в нём только пример ТЗ — он и идёт в запуск, чтобы сразу попробовать генерацию
  if (S.runDocsFresh) { S.runDocsFresh = false; if (metas.length && metas.every((m) => m.sample)) { for (const m of metas) S.runDocs.add(m.id); saveRunDocs(); } }
  for (const m of metas) {
    if (S.docs.some((d) => d.id === m.id)) continue;
    const d = docFromMeta(pid, m);
    S.docs.push(d); changed = true;
    if (!m.sample) loads.push(loadDocText(pid, m).then((t) => { d.text = t; d.chars = t.length; d.status = t ? 'ready' : 'error'; if (!t) d.error = 'Текст документа не найден в хранилище'; })
      .catch(() => { d.status = 'error'; d.error = 'Не удалось загрузить документ'; }));
  }
  if (changed) { invalidateIndex(); renderDocs(); renderRunControls(); }
  if (!loads.length) return;
  await Promise.all(loads);
  if (S.productId !== pid) return;
  invalidateIndex(); renderDocs(); renderRunControls();
  renderProduct(); if (S.tab === 'agent' && !S.run) renderTab();
}
/* ---------- индекс готовых кейсов и пунктов чек-листа продукта ---------- */
async function loadProductIndex(pid) {
  const out = { pid, cases: [], checklist: [] };
  let known = null;
  try {
    const [a, b, k] = await Promise.all([S.caps.db.doc(`${prodPath(pid)}/meta/cases`).get(), S.caps.db.doc(`${prodPath(pid)}/meta/checklist`).get(), readKnown(pid)]);
    out.cases = arrOf(a.data()?.items); out.checklist = arrOf(b.data()?.items); known = k;
  } catch { /* индекса ещё нет */ }
  if (S.productId === pid) { S.prodIndex = out; S.prodKnown = known || { reqs: [], qa: [], docs: [] }; renderProduct(); }
  return out;
}
function trimIdx(items) {
  while (items.length && JSON.stringify(items).length > IDX_MAX) items.splice(0, Math.max(1, Math.ceil(items.length * 0.05)));
  return items;
}
function idxMax(items, t) {
  let m = 0;
  const pre = t ? S.cfg.tpl[t]?.idPrefix || '' : '';
  for (const x of items) if ((!t || x.t === t) && (!pre || String(x.i).startsWith(pre))) { const n = Number((/(\d+)\s*$/.exec(String(x.i)) || [])[1] || 0); if (n > m) m = n; }
  return m;
}
function productCounters(pid) {
  const p = productById(pid), idx = S.prodIndex.pid === pid ? S.prodIndex : { cases: [], checklist: [] };
  const c = {};
  for (const t of TYPES) c[t] = Math.max(Number(p?.counters?.[t]) || 0, idxMax(idx.cases, t));
  c.cl = Math.max(Number(p?.counters?.cl) || 0, idxMax(idx.checklist));
  return c;
}
let idxChain = Promise.resolve();
async function writeIdx(pid, kind, fn) {
  const ref = S.caps.db.doc(`${prodPath(pid)}/meta/${kind}`);
  const cur = arrOf((await ref.get()).data()?.items);
  const next = trimIdx(fn(cur));
  if (JSON.stringify(next) !== JSON.stringify(cur)) await ref.set({ items: next, updatedAt: Date.now() });
  return next;
}
/* после запуска и правок: кейсы и пункты запуска попадают в индекс продукта, нумерация продолжается */
function productSync(run) {
  if (!run?.productId || !S.caps.db || !S.caps.uid || run.fromHistory === 'follow' || run.fromHistory === 'readonly') return idxChain;
  const pid = run.productId, draft = run.stage === 'draft'; // черновик: кейсы ещё не в продукте и номера не заняты
  const mk = (i, t, n) => ({ r: run.id, i: String(i), t, n: String(n || '').replace(/\s+/g, ' ').trim().slice(0, 140) });
  const cs = draft ? [] : arrOf(run.cases).filter((c) => c.status !== 'obsolete').map((c) => mk(c.dispId, c.type, pickTitleText(c.testCase)));
  const cl = checklistItems(run).map((it) => mk(it.id, it.type, it.check));
  idxChain = idxChain.then(async () => {
    const cases = await writeIdx(pid, 'cases', (cur) => [...cur.filter((x) => x.r !== run.id), ...cs]);
    const checklist = await writeIdx(pid, 'checklist', (cur) => [...cur.filter((x) => x.r !== run.id), ...cl]);
    if (S.productId === pid) S.prodIndex = { pid, cases, checklist };
    await updateProduct(pid, (p) => {
      const c = {};
      for (const t of TYPES) c[t] = Math.max(Number(p.counters?.[t]) || 0, draft ? 0 : Number(run.counters?.[t]) || 0, idxMax(cases, t));
      c.cl = Math.max(Number(p.counters?.cl) || 0, Number(run.counters?.cl) || 0, idxMax(checklist));
      return { counters: c, stats: { cases: cases.length, checklist: checklist.length, lastRunAt: Math.max(Number(p.stats?.lastRunAt) || 0, run.createdAt || 0) } };
    });
    if (S.productId === pid) { S.pc.at = 0; renderProduct(); }
  }).catch(() => {});
  return idxChain;
}
function dropFromIndex(pid, runId) {
  idxChain = idxChain.then(async () => {
    const cases = await writeIdx(pid, 'cases', (cur) => cur.filter((x) => x.r !== runId));
    const checklist = await writeIdx(pid, 'checklist', (cur) => cur.filter((x) => x.r !== runId));
    if (S.productId === pid) { S.prodIndex = { pid, cases, checklist }; S.pc.at = 0; }
    await updateProduct(pid, { stats: { ...(productById(pid)?.stats || {}), cases: cases.length, checklist: checklist.length } });
  }).catch(() => {});
  return idxChain;
}
/* ---------- переключение, создание, удаление ---------- */
let switchTok = 0;
async function switchProduct(pid, { restore = false } = {}) {
  if (S.running) { toast('Дождитесь окончания генерации.', 'err'); renderProdSelect(); return false; }
  const tok = ++switchTok;
  stopFollow(); cancelResumeCountdown();
  if (S.ctxDirty && S.productId) await saveProductCtx();
  const prod = productById(pid) || await readProduct(pid).catch(() => null);
  if (tok !== switchTok) return false;
  if (!prod) { toast('Продукт не найден.', 'err'); renderProdSelect(); return false; }
  S.know.ctl?.abort(); S.kb.job.ctl?.abort();
  S.productId = pid; lsSet('qapro.product', pid);
  S.qaCtx = { all: '', api: '', ui: '', e2e: '', ...(prod.qaCtx || {}) }; S.ctxDirty = false; renderQaCtx(true);
  const rd = lsGet('qapro.runDocs.' + pid, null);
  S.runDocs = new Set(arrOf(rd)); S.runDocsFresh = rd === null;
  S.docs = []; invalidateIndex();
  S.run = null; S.caseUI.clear(); S.reqOpen.clear(); S.exp = null; S.passEdit = null;
  S.history = []; S.legacy = []; S.historyState = 'idle';
  S.know = { busy: false, log: [], error: '', ctl: null };
  S.prodIndex = { pid, cases: [], checklist: [] };
  S.pc = freshPc(); S.secEdit = null; S.casesScope = 'run';
  if (!restore && S.tab !== 'history') S.tab = 'agent';
  renderProdSelect(); renderAll();
  S.defects = { pid: null, items: [], loaded: false, open: null };
  // источник контекста продукта (база QA pro, папка, git или GitHub) подключается, даже если что-то из данных продукта не загрузилось
  try { await Promise.all([syncProductDocs(prod), loadProductIndex(pid), loadHelp(), loadKb(pid), loadDefects(pid)]); }
  finally { if (tok === switchTok) await ctxSwitch(pid).catch(() => {}); }
  if (tok !== switchTok) return false;
  if (!restore) saveSession();
  renderAll();
  return true;
}
async function migrateLegacy(ses) {
  const db = S.caps.db, id = rid('p'), now = Date.now(), by = S.caps.uid || '';
  const docs = [];
  const sampleMeta = (did) => ({ id: did || rid('d'), name: sampleDocObj().name, ext: 'md', chars: SAMPLE_DOC.length, warn: '', parts: 0, sample: true, addedAt: now, by });
  for (const m of arrOf(ses?.docs)) {
    if (m.sample) { docs.push(sampleMeta(m.id)); continue; }
    let n = 0;
    try {
      for (let i = 0; i < (m.parts || 0); i++) {
        const p = (await db.doc(`${sesBase()}/docparts/${m.id}_${i}`).get()).data();
        if (!p) break;
        await db.doc(`${prodPath(id)}/docparts/${m.id}_${i}`).set(p); n++;
      }
    } catch { /* документ не переносится */ }
    if (n && n === m.parts) docs.push({ id: m.id, name: m.name, ext: m.ext, chars: m.chars, warn: m.warn || '', parts: n, sample: false, addedAt: now, by });
  }
  if (!docs.length) docs.push(sampleMeta());
  await createProduct('Мой продукт', '', { id, docs, qaCtx: ses?.qaCtx || S.qaCtx });
  return id;
}
async function initProducts() {
  let ses = null;
  try {
    ses = await readSession();
    const snap = await S.caps.db.collection('products').get();
    S.products = sortProducts(snap.docs.map((d) => hydrateProd({ ...(d.data() || {}), id: d.id })).filter((p) => p.kind === 'product'));
    if (!S.products.length) await migrateLegacy(ses);
    const want = [ses?.productId, lsGet('qapro.product', null)].find((x) => x && S.products.some((p) => p.id === x)) || S.products[0]?.id;
    if (want) await switchProduct(want, { restore: true });
    S.prodReady = true;
    subscribeProducts();
    await restoreRun(ses);
  } catch (e) {
    if (window.__QA_DEBUG) console.error('initProducts', e?.stack || e);
    S.prodReady = true;
    if (ses && !S.run) await restoreRun(ses).catch(() => {});
  } finally { S.sessionReady = true; renderProdSelect(); renderAll(); }
}
let prodSig = '';
function subscribeProducts() {
  if (S.prodUnsub || !S.caps.db) return;
  S.prodUnsub = S.caps.db.collection('products').onSnapshot((snap) => {
    const list = sortProducts(snap.docs.map((d) => hydrateProd({ ...(d.data() || {}), id: d.id })).filter((p) => p.kind === 'product'));
    const sig = JSON.stringify(list.map((p) => [p.id, p.updatedAt, p.name]));
    if (sig === prodSig) return;
    prodSig = sig; S.products = list;
    renderProdSelect();
    const cur = curProduct();
    if (!cur) {
      if (S.productId && !S.running && !S.switching && list.length) { toast('Текущий продукт удалён — открываю другой.', 'err'); switchProduct(list[0].id); }
      return;
    }
    if (!S.ctxDirty && !isTyping($('#qa-ctx-box')) && !ctxActive(cur.id)) {
      const c = { all: '', api: '', ui: '', e2e: '', ...(cur.qaCtx || {}) };
      if (JSON.stringify(c) !== JSON.stringify(S.qaCtx)) { S.qaCtx = c; renderQaCtx(); }
    }
    syncProductDocs(cur);
    if (cur.kbUpdatedAt && cur.kbUpdatedAt > (S.kb.stamp || 0) + 2000 && !S.kb.job.busy) loadKb();
    if (!S.passEdit) renderProduct();
    if (S.tab === 'agent' && !S.run) renderTab();
  }, () => { /* подписка недоступна — продукты обновятся при перезагрузке */ });
}
async function deleteProduct(pid) {
  if (S.running) return toast('Дождитесь окончания генерации.', 'err');
  const db = S.caps.db, p = productById(pid);
  S.switching = true;
  try {
    const runs = await db.collection(runBase(pid)).get();
    for (const d of runs.docs) {
      const m = d.data() || {};
      for (let i = 0; i < (m.partsCount || 0); i++) await db.doc(`${runBase(pid)}/${d.id}/parts/p${i}`).delete();
      for (let i = 0; i < (m.srcParts || 0); i++) await db.doc(`${runBase(pid)}/${d.id}/src/s${i}`).delete();
      await db.doc(`${runBase(pid)}/${d.id}`).delete();
    }
    for (const m of arrOf(p?.docs)) for (let i = 0; i < (m.parts || 0); i++) await db.doc(`${prodPath(pid)}/docparts/${m.id}_${i}`).delete();
    for (const k of ['cases', 'checklist', 'known', 'kb', 'passport']) await db.doc(`${prodPath(pid)}/meta/${k}`).delete();
    try { for (const d of (await db.collection(`${prodPath(pid)}/meta`).get()).docs) if (/^kb_\d+$/.test(d.id)) await db.doc(`${prodPath(pid)}/meta/${d.id}`).delete(); } catch { /* страниц нет */ }
    try { for (const d of (await db.collection(`${prodPath(pid)}/kb`).get()).docs) await db.doc(`${prodPath(pid)}/kb/${d.id}`).delete(); } catch { /* разделов нет */ }
    try { for (const d of (await db.collection(`${prodPath(pid)}/cache`).get()).docs) await db.doc(`${prodPath(pid)}/cache/${d.id}`).delete(); } catch { /* кэша нет */ }
    // история вопросов к базе знаний хранится у пользователя, а не в продукте: удаляем вместе с продуктом
    if (S.caps.uid) { try { await db.doc(`data/users/${S.caps.uid}/help_${pid}`).delete(); } catch { /* истории не было */ } }
    await db.doc(prodPath(pid)).delete();
    S.products = S.products.filter((x) => x.id !== pid);
    const next = S.products[0]?.id || await createProduct('Мой продукт');
    S.productId = null;
    await switchProduct(next);
    toast(`Продукт «${p?.name || ''}» удалён`);
  } catch { toast('Не удалось удалить продукт полностью — нужны права на изменение. Попробуйте ещё раз.', 'err'); }
  finally { S.switching = false; }
}
async function moveRunToProduct(id) {
  const pid = S.productId, db = S.caps.db;
  if (!pid || S.running) return;
  const src = `data/users/${S.caps.uid}/${id}`, dst = `${runBase(pid)}/${id}`;
  try {
    const meta = (await db.doc(src).get()).data();
    if (!meta) throw new Error('not found');
    const cases = [];
    for (let i = 0; i < (meta.partsCount || 0); i++) {
      const part = (await db.doc(`${src}/parts/p${i}`).get()).data();
      if (part) { await db.doc(`${dst}/parts/p${i}`).set(part); cases.push(...arrOf(part.cases)); }
    }
    for (let i = 0; i < (meta.srcParts || 0); i++) {
      const part = (await db.doc(`${src}/src/s${i}`).get()).data();
      if (part) await db.doc(`${dst}/src/s${i}`).set(part);
    }
    await db.doc(dst).set({ ...meta, productId: pid, updatedAt: Date.now(), hb: 0 });
    for (let i = 0; i < (meta.partsCount || 0); i++) await db.doc(`${src}/parts/p${i}`).delete();
    for (let i = 0; i < (meta.srcParts || 0); i++) await db.doc(`${src}/src/s${i}`).delete();
    await db.doc(src).delete();
    if (S.run?.id === id) { S.run.productId = pid; saveSession(); }
    await productSync({ id, productId: pid, cases, checklist: meta.checklist || null, counters: meta.counters || {}, createdAt: meta.createdAt });
    S.historyState = 'idle'; await loadHistory();
    toast(`Запуск перенесён в продукт «${curProduct()?.name || ''}» — агент учтёт его кейсы`);
  } catch { toast('Не удалось перенести запуск.', 'err'); }
}
let ctxTimer = null;
function queueCtxSave() { S.ctxDirty = true; clearTimeout(ctxTimer); ctxTimer = setTimeout(saveProductCtx, 900); }
async function saveProductCtx() {
  clearTimeout(ctxTimer);
  const pid = S.productId;
  if (ctxActive(pid)) return ctxSaveQaCtx(); // доп. контекст — в products/<папка>/context.md
  if (!pid || !S.caps.db) { S.ctxDirty = false; return; }
  const snap = { ...S.qaCtx };
  try {
    await updateProduct(pid, { qaCtx: snap });
    if (JSON.stringify(snap) === JSON.stringify(S.qaCtx)) S.ctxDirty = false;
  } catch { toast('Не удалось сохранить доп. контекст в продукте.', 'err'); }
}

/* ================= знания о продукте: паспорт ================= */
const PASSPORT_SECTIONS = ['Назначение и границы', 'Модули и функциональные области', 'Роли и пользователи', 'Экраны и навигация', 'API и интеграции', 'Сущности, статусы и данные', 'Бизнес-правила и ограничения', 'Термины', 'Окружения и тестовые данные', 'Уточнения команды', 'Открытые вопросы'];
/* что уже усвоено паспортом: отпечатки требований, ответов и документов — повторно модели не отправляются */
const reqHash = (r) => hash(normKey(`${r.title} ${r.description} ${r.criteria.join(' ')}`));
const qaHash = (q) => hash(normKey(`${q.text} ${q.answer}`));
const docHashMemo = new WeakMap();
const docHash = (d) => { const c = docHashMemo.get(d); if (c && c.t === d.text) return c.h; const h = hash(d.text || ''); docHashMemo.set(d, { t: d.text, h }); return h; };
async function readKnown(pid) {
  try { const d = (await S.caps.db.doc(`${prodPath(pid)}/meta/known`).get()).data(); return { reqs: arrOf(d?.reqs), qa: arrOf(d?.qa), docs: arrOf(d?.docs) }; }
  catch { return { reqs: [], qa: [], docs: [] }; }
}
async function addKnown(pid, add, reset = false) {
  const cur = reset ? { reqs: [], qa: [], docs: [] } : await readKnown(pid);
  const next = {};
  for (const k of ['reqs', 'qa', 'docs']) next[k] = [...new Set([...cur[k], ...(add[k] || [])])].slice(-4000);
  try { await S.caps.db.doc(`${prodPath(pid)}/meta/known`).set({ ...next, updatedAt: Date.now() }); } catch { /* не критично */ }
  if (S.productId === pid) S.prodKnown = next;
  return next;
}
function promptPassport(prod, src) {
  const cur = String(prod.passport?.text || '').trim();
  const delta = !!src.delta;
  let body;
  if (src.kind === 'run') {
    const run = src.run;
    const reqs = (src.reqs || run.requirements).slice(0, 250).map(reqCompact).join('\n').slice(0, 40000);
    const qa = (src.qa || []).map((q) => `- ${q.text} — ${q.answer.trim()}`).join('\n');
    const open = (src.open || []).slice(0, 30).map((q) => `- ${q.text}`).join('\n');
    body = `## Новые сведения: запуск от ${fmtDate(run.createdAt)}
Документы: ${run.docs.map((d) => d.name).join(', ') || 'нет'}
${reqs ? `\n### Требования, которых ещё нет в паспорте\n${reqs}\n` : ''}${qa ? `\n### Ответы аналитика на вопросы\n${qa}\n` : ''}${open ? `\n### Вопросы без ответа\n${open}\n` : ''}`;
  } else {
    body = `## Новые сведения: документы продукта (часть ${src.i + 1} из ${src.total})
${src.chunk.blocks.map((b) => `<document name="${b.doc}" part="${b.part}/${b.parts}">\n${b.text}\n</document>`).join('\n\n')}`;
  }
  const head = `Ты — ведущий QA-аналитик. Ты ведёшь «паспорт продукта» — краткую базу знаний, на которую QA-агент опирается при составлении чек-листов и тест-кейсов, чтобы с каждым запуском знать о продукте больше. ${delta ? 'Дополни' : 'Обнови'} паспорт продукта «${prod.name}» по новым сведениям.
${prod.description ? `Описание продукта от команды: ${prod.description}\n` : ''}
## Текущий паспорт
${cur || 'Пока пуст — составь первую версию.'}
${qaCtxBlock(src.ctx || prod.qaCtx)}
${body}`;
  const facts = 'Только факты из источников, без домыслов и общих фраз. Конкретика важнее всего: названия экранов, кнопок и полей, пути навигации, роли и права, эндпоинты, коды и тексты ошибок, лимиты, форматы, статусы сущностей, связи между модулями. Где важно, в конце пункта укажи источник в скобках.';
  if (delta) {
    return renderPrompt("promptPassportDelta", { "head": head, "e2": PASSPORT_SECTIONS.join(', '), "facts": facts, "e4": '' });
  }
  return renderPrompt("promptPassportFull", { "head": head, "facts": facts, "e3": PASSPORT_SECTIONS.join(', '), "e4": 10000 });
}
function normPassport(res) {
  const t = typeof res === 'string' ? res : typeof res?.passport === 'string' ? res.passport : '';
  return t.replace(/\r/g, '').trim();
}
/* применяем правки паспорта локально: добавить пункт в раздел, заменить или убрать строку */
function applyPassportOps(text, ops) {
  const secs = []; let cur = { head: '', lines: [] };
  for (const line of String(text || '').split('\n')) {
    const m = /^#{1,3}\s+(.*)$/.exec(line);
    if (m) { secs.push(cur); cur = { head: m[1].trim(), lines: [] }; } else cur.lines.push(line);
  }
  secs.push(cur);
  const norm = (x) => normKey(String(x || '').replace(/^\s*([-*•]|\d+[.)])\s*/, ''));
  const findLine = (old) => {
    const k = norm(old);
    if (!k) return null;
    for (const s of secs) { const i = s.lines.findIndex((l) => norm(l) === k); if (i >= 0) return { s, i }; }
    for (const s of secs) { const i = s.lines.findIndex((l) => { const n = norm(l); return n && Math.min(n.length, k.length) > 15 && (n.includes(k) || k.includes(n)); }); if (i >= 0) return { s, i }; }
    return null;
  };
  const sectionOf = (name) => {
    const head = String(name || 'Прочее').replace(/^#+\s*/, '').trim() || 'Прочее';
    let s = secs.find((x) => x.head && normKey(x.head) === normKey(head));
    if (s) return s;
    s = { head, lines: [] };
    const order = PASSPORT_SECTIONS.map(normKey), idx = order.indexOf(normKey(head));
    let pos = secs.length;
    if (idx >= 0) for (let j = 1; j < secs.length; j++) { const o = order.indexOf(normKey(secs[j].head)); if (o > idx) { pos = j; break; } }
    secs.splice(pos, 0, s);
    return s;
  };
  const exists = (line) => secs.some((s) => s.lines.some((l) => norm(l) === norm(line)));
  let applied = 0;
  for (const op of arrOf(ops)) {
    const kind = String(op?.op || '').toLowerCase();
    const txt = String(op?.text || '').trim();
    const line = txt ? (/^\s*([-*•]|\d+[.)])\s/.test(txt) ? txt : '- ' + txt) : '';
    if (kind === 'add' && line) {
      if (exists(line)) continue;
      const s = sectionOf(op.section);
      while (s.lines.length && !s.lines[s.lines.length - 1].trim()) s.lines.pop();
      s.lines.push(line); applied++;
    } else if ((kind === 'replace' || kind === 'update') && line) {
      const f = findLine(op.old);
      if (f) { f.s.lines[f.i] = line; applied++; }
      else if (!exists(line)) { const s = sectionOf(op.section); s.lines.push(line); applied++; }
    } else if (kind === 'remove' || kind === 'delete') {
      const f = findLine(op.old);
      if (f) { f.s.lines.splice(f.i, 1); applied++; }
    }
  }
  const out = [];
  for (const s of secs) {
    const body = s.lines.join('\n').replace(/\n{3,}/g, '\n\n').trim();
    if (!body) continue;
    out.push(s.head ? `## ${s.head}\n${body}` : body);
  }
  return { text: out.join('\n\n'), applied };
}
async function savePassport(pid, text, runId) {
  const cur = await readProduct(pid);
  const now = Date.now(), by = S.caps.uid || '';
  const prev = cur?.passport?.text && cur.passport.text !== text ? { text: cur.passport.text, updatedAt: cur.passport.updatedAt || 0 } : (cur?.passportPrev?.text ? cur.passportPrev : null);
  await passWrite(pid, { text, updatedAt: now, by, runId: runId || null, prev });
  passCache[pid] = { at: now, text, prev };
  ctxAfterPassport(pid, text); // источник контекста — репозиторий: паспорт пишется и в products/<папка>/passport.md
  return updateProduct(pid, () => ({ passport: { ext: true, text: '', len: text.length, updatedAt: now, by, runId: runId || null }, passportPrev: prev ? { ext: true, updatedAt: prev.updatedAt || 0 } : null }));
}
/* один запрос к модели: полный паспорт, если он пуст или переполнен, иначе — только правки */
async function passportStep(pid, prod, src, signal, onProgress) {
  const cur = String(prod.passport?.text || '').trim();
  const delta = !!cur; // большой паспорт целиком не переписываем — длинный ответ обрезается; только правки
  const res = await ask(promptPassport(prod, { ...src, delta }), { step: 'knowledge', tier: auxTier(), cache: false, signal, onProgress });
  if (!delta) {
    const text = normPassport(res);
    if (!text) throw new Error('Модель не вернула паспорт продукта.');
    return { prod: await savePassport(pid, text, src.runId || null), note: `паспорт ${fmtKChars(text.length)}` };
  }
  const ops = arrOf(res?.ops);
  if (!ops.length && typeof res?.passport === 'string') return { prod: await savePassport(pid, normPassport(res), src.runId || null), note: 'паспорт переписан' };
  const r = applyPassportOps(cur, ops);
  if (!r.applied) return { prod, note: 'новых фактов нет' };
  return { prod: await savePassport(pid, r.text, src.runId || null), note: `${r.applied} ${plural(r.applied, 'правка', 'правки', 'правок')}` };
}
async function stepKnowledge(run) {
  if (!run.productId || !S.caps.db || run.productId !== S.productId) return;
  const pid = run.productId;
  sstart(run, 'knowledge');
  const line = slog(run, 'knowledge', 'Проверяю, что нового для знаний о продукте…');
  try {
    const prod = await readProduct(pid);
    if (!prod) throw new Error('Продукт не найден.');
    const empty = !String(prod.passport?.text || '').trim();
    const known = empty ? { reqs: [], qa: [] } : await readKnown(pid);
    const kr = new Set(known.reqs), kq = new Set(known.qa);
    const reqs = run.requirements.filter((r) => !kr.has(reqHash(r)));
    const qa = run.questions.filter((q) => q.answer?.trim() && !kq.has(qaHash(q)));
    if (!reqs.length && !qa.length) {
      line.text = 'Новых сведений нет — все требования и ответы уже учтены в знаниях о продукте, запрос к модели не нужен'; line.kind = 'ok';
      send(run, 'knowledge'); return;
    }
    line.text = `Дополняю знания: новых требований ${reqs.length}${qa.length ? `, ответов ${qa.length}` : ''}…`;
    const open = run.questions.filter((q) => !q.answer?.trim());
    const r = await passportStep(pid, prod, { kind: 'run', run, reqs, qa, open, ctx: run.qaCtx, runId: run.id }, undefined, (n) => { line.text = `Пишет правки паспорта — ${fmtKChars(n)}`; scheduleRender(); });
    await addKnown(pid, { reqs: reqs.map(reqHash), qa: qa.map(qaHash) }, empty);
    line.text = `Знания о продукте обновлены: ${r.note}`; line.kind = 'ok';
    send(run, 'knowledge');
  } catch (e) {
    if (e?.code === 'cancelled' || S.ctl?.signal.aborted) throw abortErr();
    line.text = 'Знания о продукте не обновлены: ' + errText(e); line.kind = 'warn';
    send(run, 'knowledge', 'error');
  }
}
function updateKnowledgeNow() { S.tab = 'agent'; runTask('knowledge', async (run) => { run.steps.knowledge.log = []; await stepKnowledge(run); }); }
let knowRaf = false;
function renderKnow(pid) {
  if (knowRaf) return;
  knowRaf = true;
  requestAnimationFrame(() => { knowRaf = false; if (S.productId === pid && !S.passEdit) renderProduct(); });
}
const newDocsForKnowledge = () => { const k = new Set(S.prodKnown?.docs || []); return readyDocs().filter((d) => !k.has(docHash(d))); };
/* «Изучить документы»: агент читает документы продукта, которые ещё не изучал, и дополняет паспорт */
async function learnFromDocs(all = false, only = null) {
  const pid = S.productId;
  if (!pid || S.running || S.know.busy) return;
  if (!aiReady(S.settings.genAI)) return toast(aiProblem(S.settings.genAI), 'err');
  const docs = only ? only.filter((d) => d.status === 'ready') : all ? readyDocs() : newDocsForKnowledge();
  if (!docs.length) return only ? undefined : toast(readyDocs().length ? 'Все документы продукта уже изучены.' : 'В продукте нет документов с текстом.', 'err');
  const chunks = buildChunks(docs);
  const K = S.know = { busy: true, log: [], error: '', ctl: new AbortController() };
  renderKnow(pid);
  try {
    let prod = await readProduct(pid);
    for (let i = 0; i < chunks.length && !K.ctl.signal.aborted; i++) {
      const label = chunks.length > 1 ? `Часть ${i + 1}/${chunks.length}` : 'Документы';
      const names = [...new Set(chunks[i].blocks.map((b) => b.doc))].join(', ');
      const line = { text: `${label}: модель читает ${names}…`, kind: '' };
      K.log.push(line); renderKnow(pid);
      const r = await passportStep(pid, prod, { kind: 'docs', chunk: chunks[i], i, total: chunks.length, ctx: { ...S.qaCtx } }, K.ctl.signal, (n) => { line.text = `${label}: пишет — ${fmtKChars(n)}`; renderKnow(pid); });
      prod = r.prod;
      line.text = `${label}: ${r.note}`; line.kind = 'ok';
      const learned = docs.filter((d) => chunks[i].blocks.some((b) => b.doc === d.name) && !chunks.slice(i + 1).some((c) => c.blocks.some((b) => b.doc === d.name)));
      if (learned.length) await addKnown(pid, { docs: learned.map(docHash) });
    }
    if (!K.ctl.signal.aborted) toast('Знания о продукте обновлены');
  } catch (e) { K.error = e?.code === 'cancelled' ? '' : errText(e); }
  finally { K.busy = false; renderKnow(pid); }
}
async function restorePrevPassport() {
  const pid = S.productId, p = curProduct();
  if (!pid || !p?.passportPrev?.text) return;
  try { await savePassport(pid, p.passportPrev.text, null); toast('Возвращена предыдущая версия знаний'); renderTab(); }
  catch { toast('Не удалось вернуть версию — нужны права на изменение.', 'err'); }
}
/* ---------- разделы тест-кейсов: по документу, из которого взяты требования кейса ---------- */
const NO_DOC = 'Без документа';
const docBase = (name) => String(name || '').replace(/\.[a-z0-9]{1,5}$/i, '').trim();
const secKey = (doc) => normKey(docBase(doc)) || '-';
const secDefault = (doc) => docBase(doc) || NO_DOC;
function docOfCase(run, c) {   // документ большинства требований кейса; без требований — пустая строка
  const cnt = new Map();
  for (const id of arrOf(c.requirementIds)) { const d = String(run?.reqById?.[id]?.doc || '').trim(); if (d) cnt.set(d, (cnt.get(d) || 0) + 1); }
  let best = '', n = 0;
  for (const [d, k] of cnt) if (k > n) { best = d; n = k; }
  return best;
}
const cleanSections = (m) => Object.fromEntries(Object.entries(m && typeof m === 'object' && !Array.isArray(m) ? m : {}).map(([k, v]) => [String(k).slice(0, 80), String(v || '').replace(/\s+/g, ' ').trim().slice(0, 120)]).filter(([, v]) => v).slice(0, 300));
const secStore = () => (S.productId ? productById(S.productId)?.caseSections : S.localSections) || {};
const secName = (doc) => String(secStore()[secKey(doc)] || '').trim() || secDefault(doc);
/* название раздела можно изменить вручную; пустое или совпадающее с названием документа — возвращает название документа */
async function renameSection(doc, name) {
  const key = secKey(doc), v = String(name || '').replace(/\s+/g, ' ').trim().slice(0, 120), next = { ...secStore() };
  if (!v || v === secDefault(doc)) delete next[key]; else next[key] = v;
  if (!S.productId) { S.localSections = next; lsSet('qapro.sections', next); return; }
  if (!S.caps.db) { upsertLocalProduct(S.productId, { ...productById(S.productId), caseSections: next }); return; }
  await updateProduct(S.productId, { caseSections: next });
}
/* Кейсы продукта берутся из сохранённых запусков, а не из индекса: в индексе нет черновиков, а при большом объёме он обрезается с начала.
   Запуск читается заново только если изменилась его отметка (updatedAt, стадия, число частей). */
const prodCaseItem = (run, c, doc) => ({ r: run.id, i: String(c.dispId), t: c.type, n: String(pickTitleText(c.testCase || {})).replace(/\s+/g, ' ').trim().slice(0, 200), doc, draft: run.stage === 'draft', obs: c.status === 'obsolete' });
const liveRunItems = (run) => arrOf(run.cases).map((c) => prodCaseItem(run, c, docOfCase(run, c)));
async function readRunItems(pid, m) {
  const base = runBase(pid), reqById = Object.fromEntries(arrOf(m.requirements).map((r) => [r.id, r])), items = [];
  for (let i = 0; i < (m.partsCount || 0); i++) {
    const p = (await S.caps.db.doc(`${base}/${m.id}/parts/p${i}`).get()).data();
    for (const c of arrOf(p?.cases)) items.push(prodCaseItem({ id: m.id, stage: m.stage }, c, docOfCase({ reqById }, c)));
  }
  return items;
}
function prodItems() {   // кейсы продукта по порядку запусков; открытый запуск берётся из памяти
  const pc = S.pc, out = [];
  for (const id of pc.order) out.push(...(S.run?.id === id ? liveRunItems(S.run) : pc.runs[id]?.items || []));
  if (S.run && S.run.productId === S.productId && !pc.order.includes(S.run.id)) out.push(...liveRunItems(S.run));
  if (!out.length && pc.error && !pc.order.length) return S.prodIndex.cases.map((x) => ({ ...x, doc: '', draft: false, obs: false }));   // запуски не прочитались — хотя бы индекс
  return out;
}
async function ensureProdCases(force = false) {
  const pid = S.productId, pc = S.pc;
  if (!pid || !S.caps.db || pc.busy || (!force && pc.at && Date.now() - pc.at < 8000)) return;
  pc.busy = true; pc.error = '';
  try {
    const metas = (await S.caps.db.collection(runBase(pid)).get()).docs.map((d) => d.data()).filter((m) => m?.kind === 'run' && m.id).sort((a, b) => (a.createdAt || 0) - (b.createdAt || 0) || String(a.id).localeCompare(String(b.id)));
    if (S.productId !== pid) return;
    const stamp = (m) => `${m.updatedAt || 0}:${m.stage || ''}:${m.partsCount || 0}`, need = metas.filter((m) => pc.runs[m.id]?.at !== stamp(m));
    let next = 0;
    await Promise.all(Array.from({ length: Math.min(3, need.length) }, async () => {
      while (next < need.length && S.productId === pid) {
        const m = need[next++];
        try { pc.runs[m.id] = { at: stamp(m), items: await readRunItems(pid, m) }; } catch { pc.error = 'Часть запусков не удалось прочитать.'; pc.runs[m.id] = { at: '', items: [] }; }
      }
    }));
    pc.order = metas.map((m) => m.id);
    for (const id of Object.keys(pc.runs)) if (!pc.order.includes(id)) delete pc.runs[id];
  } catch { pc.error = 'Не удалось прочитать запуски продукта.'; }
  finally { pc.busy = false; if (S.productId === pid) { pc.loaded = true; pc.at = Date.now(); } }
  if (S.productId === pid) afterProdCases();
}
/* удалить все кейсы продукта: части запусков, индекс и открытый запуск; сами запуски и их документы остаются */
async function deleteAllProductCases() {
  const pid = S.productId, db = S.caps.db;
  if (!pid || !db || S.running) return toast('Дождитесь окончания генерации.', 'err');
  const n = prodItems().length;
  if (!n) return;
  try {
    for (const id of S.pc.order) {
      const base = `${runBase(pid)}/${id}`, meta = (await db.doc(base).get()).data();
      if (!meta) continue;
      for (let i = 0; i < (meta.partsCount || 0); i++) await db.doc(`${base}/parts/p${i}`).delete();
      await db.doc(base).update({ partsCount: 0, updatedAt: Date.now() });
    }
    if (S.run && S.run.productId === pid) { S.run.cases = []; S.caseUI.clear(); S.caseSel.clear(); queueSave(S.run); }
    await db.doc(`${prodPath(pid)}/meta/cases`).set({ items: [], updatedAt: Date.now() });
    await updateProduct(pid, (p) => ({ stats: { ...(p.stats || {}), cases: 0 } }));
    if (S.productId === pid) { S.prodIndex = { ...S.prodIndex, cases: [] }; S.pc = freshPc(); }
    renderAll();
    toast(`Удалено кейсов продукта: ${n}`);
  } catch { toast('Не удалось удалить кейсы — нужны права на изменение.', 'err'); S.pc.at = 0; renderAll(); }
}
/* ================= экспорт и импорт продукта ================= */
const slugName = (s) => String(s || 'product').toLowerCase().replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-+|-+$/g, '').slice(0, 40) || 'product';
async function exportProduct() {
  const pid = S.productId, db = S.caps.db;
  if (!pid || !db) return;
  S.prodIO = { busy: true, text: 'Собираю продукт: документы, знания, запуски…' }; renderProduct();
  try {
    const p = await readProduct(pid);
    const docs = [];
    for (const m of arrOf(p.docs)) docs.push({ ...m, text: m.sample ? '' : await loadDocText(pid, m) });
    const meta = async (k) => (await db.doc(`${prodPath(pid)}/meta/${k}`).get()).data() || null;
    const [cases, checklist, known] = [await meta('cases'), await meta('checklist'), await meta('known')];
    const ki = await kbIdxRead(pid), kbIdx = { blocks: ki.blocks, docs: ki.docs };
    const kb = [];
    for (const b of arrOf(kbIdx?.blocks)) { const d = await kbRead(pid, b.id); if (d) { delete d.more; kb.push(d); } }
    const runs = [];
    for (const d of (await db.collection(runBase(pid)).get()).docs) {
      const m = d.data();
      if (!m || m.kind !== 'run') continue;
      const parts = [], src = [];
      for (let i = 0; i < (m.partsCount || 0); i++) parts.push((await db.doc(`${runBase(pid)}/${d.id}/parts/p${i}`).get()).data() || { cases: [] });
      for (let i = 0; i < (m.srcParts || 0); i++) src.push((await db.doc(`${runBase(pid)}/${d.id}/src/s${i}`).get()).data() || { cases: [] });
      runs.push({ meta: m, parts, src });
    }
    const out = {
      format: 'qa-pro-product', version: 1, exportedAt: new Date().toISOString(),
      product: { name: p.name, description: p.description || '', qaCtx: p.qaCtx || {}, passport: p.passport || null, passportPrev: p.passportPrev || null, counters: p.counters || {}, stats: p.stats || {}, createdAt: p.createdAt, caseSections: p.caseSections || {} },
      docs, index: { cases: arrOf(cases?.items), checklist: arrOf(checklist?.items) }, known: known || null, runs,
      kb: { index: kbIdx || null, blocks: kb },
    };
    await downloadFile(`qa-pro-${slugName(p.name)}-${new Date().toISOString().slice(0, 10)}.json`, JSON.stringify(out));
  } catch { toast('Не удалось выгрузить продукт.', 'err'); }
  finally { S.prodIO = null; renderProduct(); }
}
async function importProduct(file) {
  const db = S.caps.db;
  if (!db || S.running) return;
  const parsed = tryParse(decodeText(await file.arrayBuffer()));
  const d = parsed.ok ? parsed.value : null;
  if (!d || d.format !== 'qa-pro-product' || !d.product) return toast('Это не файл продукта QA pro: нужен JSON, выгруженный кнопкой «Экспорт продукта».', 'err');
  let name = String(d.product.name || 'Продукт').slice(0, 70), k = 1;
  while (S.products.some((x) => normKey(x.name) === normKey(name))) name = `${String(d.product.name || 'Продукт').slice(0, 60)} (копия${k++ > 1 ? ' ' + (k - 1) : ''})`;
  const id = rid('p');
  S.prodIO = { busy: true, text: `Загружаю продукт «${name}»…` }; renderProduct();
  try {
    const docs = [];
    for (const doc of arrOf(d.docs)) {
      const did = String(doc.id || rid('d')).replace(/[^\w-]/g, '').slice(0, 40) || rid('d');
      const base = { id: did, name: String(doc.name || 'Документ'), ext: String(doc.ext || 'txt'), warn: doc.warn || '', addedAt: doc.addedAt || Date.now(), by: doc.by || '' };
      if (doc.sample) { docs.push({ ...base, chars: SAMPLE_DOC.length, parts: 0, sample: true }); continue; }
      const text = String(doc.text || '');
      if (!text) continue;
      const n = Math.max(1, Math.ceil(text.length / DOC_CH));
      for (let i = 0; i < n; i++) await db.doc(`${prodPath(id)}/docparts/${did}_${i}`).set({ docId: did, i, text: text.slice(i * DOC_CH, (i + 1) * DOC_CH) });
      docs.push({ ...base, chars: text.length, parts: n, sample: false });
    }
    await createProduct(name, d.product.description || '', { id, docs, qaCtx: d.product.qaCtx || {} });
    if (d.product.passport?.text) { await savePassport(id, String(d.product.passport.text), null); }
    await db.doc(prodPath(id)).update({ ...(d.product.passport?.text ? {} : { passport: null, passportPrev: null }), counters: { api: 0, ui: 0, e2e: 0, cl: 0, ...(d.product.counters || {}) }, stats: { cases: 0, checklist: 0, lastRunAt: 0, ...(d.product.stats || {}) }, caseSections: cleanSections(d.product.caseSections) });
    const fresh = (await db.doc(prodPath(id)).get()).data(); if (fresh) upsertLocalProduct(id, fresh);   // локальная копия продукта — с названиями разделов и счётчиками
    if (d.index) {
      await db.doc(`${prodPath(id)}/meta/cases`).set({ items: arrOf(d.index.cases), updatedAt: Date.now() });
      await db.doc(`${prodPath(id)}/meta/checklist`).set({ items: arrOf(d.index.checklist), updatedAt: Date.now() });
    }
    if (d.known) await db.doc(`${prodPath(id)}/meta/known`).set({ reqs: arrOf(d.known.reqs), qa: arrOf(d.known.qa), docs: arrOf(d.known.docs), updatedAt: Date.now() });
    if (d.kb?.index) {
      for (const b of arrOf(d.kb.blocks)) { const bid = String(b.id || '').replace(/[^\w-]/g, ''); if (bid && b.kind !== 'kbmore') { const { more, ...x } = b; await kbWrite(id, bid, { ...x, id: bid, parts: arrOf(x.parts) }); } }
      await kbIdxWrite(id, arrOf(d.kb.index.blocks), d.kb.index.docs || {}, null);
    }
    let nr = 0;
    for (const r of arrOf(d.runs)) {
      const m = r?.meta;
      if (!m?.id || m.kind !== 'run') continue;
      const rid0 = String(m.id).replace(/[^\w-]/g, '');
      for (let i = 0; i < arrOf(r.parts).length; i++) await db.doc(`${runBase(id)}/${rid0}/parts/p${i}`).set(r.parts[i]);
      for (let i = 0; i < arrOf(r.src).length; i++) await db.doc(`${runBase(id)}/${rid0}/src/s${i}`).set(r.src[i]);
      await db.doc(`${runBase(id)}/${rid0}`).set({ ...m, id: rid0, productId: id, hb: 0, status: m.status === 'running' ? 'stopped' : m.status, partsCount: arrOf(r.parts).length, srcParts: arrOf(r.src).length });
      nr++;
      S.prodIO.text = `Загружаю продукт «${name}»: запуски ${nr} из ${arrOf(d.runs).length}…`; renderProduct();
    }
    S.prodIO = null;
    await switchProduct(id);
    if (arrOf(d.runs).some((r) => arrOf(r?.parts).some((p) => arrOf(p?.cases).length))) { S.tab = 'cases'; S.casesScope = 'product'; renderAll(); }   // загруженные кейсы (в том числе черновики) сразу видны на вкладке «Тест-кейсы»
    toast(`Продукт «${name}» загружен: документов ${docs.length}, запусков ${nr}`);
  } catch (e) {
    S.prodIO = null; renderProduct();
    toast(e?.code === 'quota_exceeded' ? e.message : 'Не удалось загрузить продукт — проверьте файл и права на запись.', 'err');
  }
}
/* ================= справка по функциональности: ответы строго по базе знаний продукта ================= */
const HELP_STOP = new Set(['как', 'что', 'где', 'когда', 'какие', 'какой', 'какая', 'какое', 'каких', 'какому', 'есть', 'ли', 'для', 'при', 'это', 'этот', 'эта', 'если', 'или', 'чем', 'чего', 'нужно', 'можно', 'будет', 'быть', 'есть', 'про', 'над', 'под', 'все', 'всех', 'его', 'она', 'они', 'the', 'and', 'what', 'how', 'with']);
/* лёгкая нормализация русских словоформ: «роли» и «роль», «экран» и «экраны» совпадают */
function helpTokens(s) {
  return (String(s || '').toLowerCase().replace(/ё/g, 'е').match(/[a-zа-я0-9_./-]{2,}/g) || [])
    .filter((w) => !HELP_STOP.has(w))
    .map((w) => (/^[a-z0-9_./-]+$/.test(w) ? w : w.length <= 4 ? w.slice(0, 3) : w.slice(0, Math.max(4, Math.min(6, w.length - 2)))));
}
const helpScore = (q, text) => { const t = new Set(helpTokens(text)); let n = 0; for (const x of q) if (t.has(x)) n++; return n; };
function kbSig() {
  const p = curProduct();
  return hash(JSON.stringify([p?.passport?.updatedAt || 0, (p?.docs || []).map((d) => d.id + ':' + d.chars), S.prodIndex.cases.length, S.prodIndex.checklist.length, S.qaCtx, S.kb.stamp || 0]));
}
function kbStats() {
  const k = knowOf(null);
  return { passport: (k?.passport || '').trim().length, docs: readyDocs().length, cases: S.prodIndex.cases.length, checklist: S.prodIndex.checklist.length, ctx: ctxHas(S.qaCtx), blocks: S.kb.index.blocks.length };
}
/* отбор фрагментов базы знаний под вопрос — локально, без модели */
function helpContext(question, kbBlocks = []) {
  const q = [...new Set(helpTokens(question))];
  const blocks = [];
  let relevant = 0;
  const eco = economy();
  // разделы базы знаний по теме вопроса
  kbBlocks.forEach((blk, i) => {
    const cap = eco ? 2500 : 4000;
    const lines = kbSectionText(blk).split('\n').filter((l) => l.trim());
    let text = lines.join('\n');
    if (text.length > cap) {
      const scored = lines.map((l, k) => ({ l, k, s: helpScore(q, l) + (/^#{1,4}\s/.test(l) ? 0.1 : 0) })).sort((a, b) => b.s - a.s || a.k - b.k);
      const keep = []; let size = 0;
      for (const x of scored) { if (size + x.l.length > cap) continue; keep.push(x); size += x.l.length + 1; }
      text = keep.sort((a, b) => a.k - b.k).map((x) => x.l).join('\n');
    }
    relevant += 1;
    blocks.push({ id: 'B' + (i + 1), kind: 'kb', label: `Раздел «${blk.title}»`, text, score: 1, kbId: blk.id });
  });
  // знания о продукте: разделы паспорта
  const pass = String(knowOf(null)?.passport || '').trim();
  if (pass) {
    const secs = []; let cur = { head: 'Общее', lines: [] };
    for (const line of pass.split('\n')) { const m = /^#{1,3}\s+(.*)$/.exec(line); if (m) { if (cur.lines.length) secs.push(cur); cur = { head: m[1].trim(), lines: [] }; } else if (line.trim()) cur.lines.push(line); }
    if (cur.lines.length) secs.push(cur);
    const cap = eco ? 2500 : 4500;
    let picked = secs.map((s) => ({ head: s.head, lines: s.lines.map((l) => ({ l, s: helpScore(q, s.head + ' ' + l) })) }));
    if (pass.length > cap) {
      const all = picked.flatMap((s, si) => s.lines.map((x, li) => ({ si, li, s: x.s, len: x.l.length }))).filter((x) => x.s > 0).sort((a, b) => b.s - a.s);
      const keep = new Set(); let size = 0;
      for (const x of all) { if (size + x.len > cap) continue; keep.add(x.si + ':' + x.li); size += x.len; }
      picked = picked.map((s, si) => ({ head: s.head, lines: s.lines.filter((x, li) => keep.has(si + ':' + li)) }));
    }
    picked.filter((s) => s.lines.length).forEach((s, i) => {
      const sc = s.lines.reduce((a, x) => a + x.s, 0);
      relevant += sc;
      blocks.push({ id: 'K' + (i + 1), kind: 'know', label: `Знания о продукте — «${s.head}»`, text: s.lines.map((x) => x.l).join('\n'), score: sc });
    });
  }
  // доп. контекст от QA
  const ctx = CTX_TABS.filter(([id]) => S.qaCtx[id]?.trim()).map(([id, n]) => `${id === 'all' ? 'Для всех' : n}: ${S.qaCtx[id].trim()}`);
  if (ctx.length) { const sc = helpScore(q, ctx.join(' ')); relevant += sc; blocks.push({ id: 'QA', kind: 'ctx', label: 'Доп. контекст от QA', text: ctx.join('\n'), score: sc }); }
  // документы продукта: фрагменты по теме вопроса
  if (readyDocs().length) {
    ensureIndex();
    const cap = kbBlocks.length ? (eco ? 1500 : 2500) : eco ? 2500 : 4500;
    const scored = INDEX.map((x) => ({ x, s: helpScore(q, x.text) })).filter((o) => o.s > 0).sort((a, b) => b.s - a.s);
    let size = 0, n = 0;
    for (const o of scored) {
      if (size + o.x.text.length > cap) continue;
      size += o.x.text.length; relevant += o.s;
      blocks.push({ id: 'D' + (++n), kind: 'doc', label: `Документ «${o.x.doc}»`, doc: o.x.doc, offset: o.x.offset, text: o.x.text, score: o.s });
      if (n >= 6) break;
    }
  }
  // готовые тест-кейсы и пункты чек-листа продукта
  const rel = (items) => items.map((x) => ({ x, s: helpScore(q, x.n) })).filter((o) => o.s > 0).sort((a, b) => b.s - a.s).slice(0, eco ? 8 : 15).map((o) => o.x);
  const cs = rel(S.prodIndex.cases), cl = rel(S.prodIndex.checklist);
  if (cs.length) { relevant += cs.length; blocks.push({ id: 'TC', kind: 'cases', label: 'Тест-кейсы продукта', text: cs.map((x) => `${x.i} [${TL[x.t] || x.t}] ${x.n}`).join('\n'), ids: cs.map((x) => x.i), names: Object.fromEntries(cs.map((x) => [x.i, x.n])) }); }
  if (cl.length) { relevant += cl.length; blocks.push({ id: 'CL', kind: 'checklist', label: 'Пункты чек-листа продукта', text: cl.map((x) => `${x.i} [${TL[x.t] || x.t}] ${x.n}`).join('\n'), ids: cl.map((x) => x.i), names: Object.fromEntries(cl.map((x) => [x.i, x.n])) }); }
  const small = pass && pass.length <= (eco ? 2500 : 4500);
  return { blocks, relevant: relevant > 0 || (small && !!pass) };
}
function promptHelp(prod, question, blocks, history) {
  return renderPrompt("promptHelp", { "e1": prod?.name || 'Продукт', "e2": history ? `\n## Предыдущий вопрос в этом диалоге (для понимания контекста; фактов он не добавляет)\n${history}\n` : '', "e3": blocks.map((b) => `[${b.id}] ${b.label}${b.doc ? `, позиция ${b.offset}` : ''}\n${b.text}`).join('\n\n'), "question": question });
}
const helpRef = (pid) => (S.caps.db && S.caps.uid && pid ? S.caps.db.doc(`data/users/${S.caps.uid}/help_${pid}`) : null);
async function loadHelp() {
  const pid = S.productId;
  S.help?.ctl?.abort();
  S.help = { pid, items: [], loaded: false, busy: false, draft: S.help?.pid === pid ? S.help.draft : '', ctl: null, error: '', ans: {} };
  const ref = helpRef(pid);
  if (ref) { try { S.help.items = arrOf((await ref.get()).data()?.items); } catch { /* истории нет */ } }
  if (S.productId === pid) { S.help.loaded = true; if (S.settings.mode === 'help') renderHelp(); }
}
let helpChain = Promise.resolve();
function saveHelp(H = S.help) {
  const ref = helpRef(H.pid);
  if (!ref) return;
  let items = H.items.filter((x) => x.status !== 'pending').slice(-100);
  while (items.length > 1 && JSON.stringify(items).length * 2 > 230000) items = items.slice(1);
  helpChain = helpChain.then(() => ref.set({ kind: 'help', productId: H.pid, items, updatedAt: Date.now() })).catch(() => {});
}
const renderHelpIf = (H) => { if (S.help === H) renderHelp(); };
async function askHelp(question) {
  const q = String(question || '').trim();
  const H = S.help;
  if (!q || H.busy) return;
  const item = { id: rid('h'), q, at: Date.now(), status: 'pending', answer: '', sources: [], missing: '', tok: 0, cached: false };
  H.items.push(item); H.draft = ''; H.error = '';
  const sig = kbSig();
  // тот же вопрос при неизменной базе знаний — ответ из истории, без модели
  const prev = [...H.items].reverse().find((x) => x !== item && x.kbSig === sig && normKey(x.q) === normKey(q) && ['answered', 'partial', 'not_found'].includes(x.status));
  if (prev) {
    Object.assign(item, { status: prev.status, answer: prev.answer, sources: prev.sources, missing: prev.missing, kbSig: sig, cached: true });
    saveHelp(H); renderHelpIf(H); return;
  }
  const st = kbStats();
  if (!st.passport && !st.docs && !st.cases && !st.ctx && !st.blocks) {
    Object.assign(item, { status: 'not_found', answer: 'База знаний продукта пуста: загрузите документы, запустите генерацию или нажмите «Изучить документы» в карточке продукта слева.', kbSig: sig });
    saveHelp(H); renderHelpIf(H); return;
  }
  const v = S.settings.genAI, ai = aiReady(v);
  H.busy = true; H.ctl = new AbortController(); renderHelpIf(H);
  try {
    let exp = { sections: [], terms: [] };
    if (ai) { try { exp = await helpExpand(q, H.ctl.signal); } catch (e) { if (e?.code === 'cancelled') throw e; /* ищем по словам вопроса */ } }
    item.terms = exp.terms;
    const qx = [q, ...exp.terms].join(' ');
    let kbb = [];
    try { kbb = await kbForQuestion(qx, economy() ? 1 : 2, exp.sections); } catch { /* без разделов */ }
    const ctx = helpContext(qx, kbb);
    if (!ctx.relevant || !ctx.blocks.length) {
      Object.assign(item, { status: 'not_found', answer: 'В базе знаний продукта нет сведений по этому вопросу.', missing: 'Нет ни одного фрагмента знаний, документов или кейсов по теме вопроса.', kbSig: sig, local: true });
      return;
    }
    if (!ai) { item.status = 'error'; item.answer = aiProblem(v); return; }
    const last = H.items.filter((x) => x !== item && x.status !== 'error' && x.status !== 'pending').slice(-1)[0];
    const history = last && Date.now() - last.at < 30 * 60000 ? `Вопрос: ${last.q}\nОтвет: ${String(last.answer).slice(0, 600)}` : '';
    const prompt = promptHelp(curProduct(), q, ctx.blocks, history);
    const res = await ask(prompt, { step: 'help', tier: auxTier(), cache: false, signal: H.ctl.signal, ai: v, onProgress: () => {} });
    const status = ['answered', 'partial', 'not_found'].includes(res?.status) ? res.status : 'partial';
    const ids = new Map();
    for (const b of ctx.blocks) {
      ids.set(b.id, { id: b.id, label: b.label, preview: b.text.slice(0, 400), kbId: b.kbId || null });
      for (const cid of b.ids || []) ids.set(cid, { id: cid, label: `${b.kind === 'cases' ? 'Кейс' : 'Пункт чек-листа'} ${cid}`, preview: b.names?.[cid] || '' });
    }
    const srcs = arrStr(res?.sources).map((x) => x.replace(/[[\]]/g, '').trim()).filter((x, i, a) => a.indexOf(x) === i).map((x) => ids.get(x)).filter(Boolean);
    Object.assign(item, {
      status: status === 'answered' && !srcs.length ? 'partial' : status,
      answer: String(res?.answer || '').trim() || 'Модель не дала ответа.', sources: srcs, missing: String(res?.missing || '').trim(),
      nosrc: status === 'answered' && !srcs.length, kbSig: sig, tok: estTok(prompt) + estTok(JSON.stringify(res)),
    });
  } catch (e) {
    if (e?.code === 'cancelled') { H.items = H.items.filter((x) => x !== item); }
    else { item.status = 'error'; item.answer = errText(e); }
  } finally {
    H.busy = false; H.ctl = null;
    saveHelp(H); renderHelpIf(H);
  }
}
/* открытые вопросы живут в паспорте продукта — их видит и закрывает вся команда */
function openQuestions() {
  const pass = String(knowOf(null)?.passport || '');
  const out = []; let inSec = false;
  for (const line of pass.split('\n')) {
    const m = /^#{1,3}\s+(.*)$/.exec(line);
    if (m) { inSec = /открыт.*вопрос/i.test(m[1]); continue; }
    if (inSec && line.trim()) out.push({ line, text: line.replace(/^\s*([-*•]|\d+[.)])\s*/, '').trim() });
  }
  return out;
}
async function addOpenQuestion(item) {
  const pid = S.productId, p = curProduct();
  if (!pid || !p) return;
  const cur = String(p.passport?.text || '');
  const r = applyPassportOps(cur, [{ op: 'add', section: 'Открытые вопросы', text: `- ${item.q} (из базы знаний, ${new Date().toLocaleDateString('ru-RU')})` }]);
  try {
    if (r.applied) await savePassport(pid, r.text, null);
    item.openAdded = true; saveHelp(); renderHelp(); toast('Вопрос добавлен в «Открытые вопросы» — команда увидит его в знаниях о продукте');
  } catch { toast('Не удалось добавить вопрос — нужны права на изменение.', 'err'); }
}
async function answerOpenQuestion(line, answer) {
  const pid = S.productId, p = curProduct();
  const a = String(answer || '').trim();
  if (!pid || !p || !a) return;
  const qText = line.replace(/^\s*([-*•]|\d+[.)])\s*/, '').replace(/\s*\(из (справки|базы знаний)[^)]*\)\s*$/, '').trim();
  const r = applyPassportOps(String(p.passport?.text || ''), [{ op: 'remove', old: line }, { op: 'add', section: 'Уточнения команды', text: `- ${qText} — ${a} (ответ команды, ${new Date().toLocaleDateString('ru-RU')})` }]);
  try { await savePassport(pid, r.text, null); delete S.help.ans[line]; toast('Ответ добавлен в знания о продукте'); renderHelp(true); }
  catch { toast('Не удалось сохранить ответ — нужны права на изменение.', 'err'); }
}
/* ================= база знаний: разделы по функциональности ================= */
/* каждый раздел — статья из частей: одна часть на фрагмент документа. Повторно сливать текст моделью не нужно,
   а при удалении документа его части просто уходят из разделов */
const KB_SUBHEADS = ['Описание', 'Экраны и навигация', 'Поля и элементы', 'Бизнес-правила и ограничения', 'API и интеграции', 'Сообщения и ошибки', 'Роли и права', 'Сценарии', 'Открытые вопросы'];
const KB_PART_MAX = 12000, KB_PARTS_MAX = 200; // выдержек в разделе: по объёму раздел держит kbFit
const kbPath = (pid, id) => `${prodPath(pid)}/kb/${id}`;
/* Хранение без потолка одной записи (256 КиБ):
   - раздел: основная запись kb/<id> (сводка, расхождения, связи и сколько поместится выдержек) и записи-продолжения
     kb/<id>__p1, __p2… с остальными выдержками (поле more — сколько их);
   - оглавление: meta/kb (сведения о документах и первая страница разделов) и страницы meta/kb_2, meta/kb_3… (поле pages). */
const KB_PAGE_BYTES = 200000, KB_MORE_MAX = 12; // раздел — до 13 записей ≈ 3 МБ (≈1,5 млн знаков выдержек)
const kbMorePath = (pid, id, i) => `${kbPath(pid, id)}__p${i}`;
const kbIdxRef = (pid, i = 0) => S.caps.db.doc(`${prodPath(pid)}/meta/kb${i ? '_' + (i + 1) : ''}`);
/* Источник контекста — папка или репозиторий: база знаний живёт в его файлах (products/<папка>/kb/*.md и knowledge/*.md),
   оглавление собирается из них, отметки о разобранных документах — products/<папка>/qa-pro-docs.json (appctx.js).
   Ниже — переходники: в этом режиме чтение и запись разделов идут в файлы, иначе — в хранилище QA pro. */
async function kbIdxRead(pid) { return ctxKbOn(pid) ? ctxKbIndex() : kbIdxReadDb(pid); }
async function kbIdxWrite(pid, blocks, docs, old) { return ctxKbOn(pid) ? ctxKbDocsWrite(blocks, docs) : kbIdxWriteDb(pid, blocks, docs, old); }
async function kbRead(pid, id) { return ctxKbOn(pid) ? ctxKbRead(id) : kbReadDb(pid, id); }
async function kbWrite(pid, id, next, prevMore = 0) { return ctxKbOn(pid) ? ctxKbWrite(id, next) : kbWriteDb(pid, id, next, prevMore); }
async function kbIdxReadDb(pid) {
  const d = (await kbIdxRef(pid).get()).data() || null;
  if (!d) return { blocks: [], docs: {}, pages: 1, raw: [null], updatedAt: 0 };
  const pages = Math.max(1, Number(d.pages) || 1), raw = [d];
  let blocks = arrOf(d.blocks);
  for (let i = 1; i < pages; i++) { const x = (await kbIdxRef(pid, i).get()).data() || null; raw.push(x); blocks = blocks.concat(arrOf(x?.blocks)); }
  return { blocks, docs: d.docs && typeof d.docs === 'object' ? d.docs : {}, pages, raw, updatedAt: d.updatedAt || 0 };
}
async function kbIdxWriteDb(pid, blocks, docs, old) {
  const pages = [];
  let cur = [], size = kbBytes({ docs }) + 200;
  for (const b of blocks) { const n = kbBytes(b) + 1; if (cur.length && size + n > KB_PAGE_BYTES) { pages.push(cur); cur = []; size = 200; } cur.push(b); size += n; }
  pages.push(cur);
  const now = Date.now();
  // сначала страницы-продолжения (только изменившиеся), последней — основная: читатель не увидит ссылку на ещё не записанную страницу
  for (let i = pages.length - 1; i >= 1; i--) {
    if (old?.raw?.[i] && JSON.stringify(arrOf(old.raw[i].blocks)) === JSON.stringify(pages[i])) continue;
    await kbIdxRef(pid, i).set({ blocks: pages[i], page: i + 1, updatedAt: now });
  }
  await kbIdxRef(pid).set({ blocks: pages[0], docs, pages: pages.length, updatedAt: now });
  for (let i = pages.length; i < (old?.pages || 1); i++) { try { await kbIdxRef(pid, i).delete(); } catch { /* уже нет */ } }
  return { blocks, docs, updatedAt: now };
}
async function loadKb(pid = S.productId) {
  if (!pid || !S.caps.db) return;
  diag('база знаний: загрузка');
  if (S.kb.pid !== pid) S.kb = { ...S.kb, pid, index: { blocks: [], docs: {} }, loaded: false, cache: {}, open: null, q: '', queue: [], synthQ: [], edit: null };
  try {
    const d = await kbIdxRead(pid);
    if (S.kb.pid !== pid) return;
    S.kb.index = { blocks: d.blocks, docs: d.docs }; S.kb.missing = {};
    S.kb.stamp = d.updatedAt;
    if (ctxKbOn(pid)) for (const b of d.blocks) S.kb.cache[b.id] = ctxKbRead(b.id); // файлы уже прочитаны — разделы сразу в памяти
  } catch { /* разделов ещё нет */ }
  S.kb.loaded = true;
  if (S.settings.mode === 'help') renderHelp();
  renderDocs();
}
// раздел целиком: основная запись и продолжения с выдержками
async function kbReadDb(pid, id) {
  const d = (await S.caps.db.doc(kbPath(pid, id)).get()).data() || null;
  if (!d || !d.more) return d;
  let parts = arrOf(d.parts);
  for (let i = 1; i <= d.more; i++) { const x = (await S.caps.db.doc(kbMorePath(pid, id, i)).get()).data(); parts = parts.concat(arrOf(x?.parts)); }
  return { ...d, parts };
}
async function kbWriteDb(pid, id, next, prevMore = 0) {
  const head = { ...next, parts: [] }, main = [], rest = [];
  let size = kbBytes(head) + 50;
  for (const p of next.parts) { const n = kbBytes(p) + 1; if (!rest.length && size + n <= KB_DOC_BYTES) { main.push(p); size += n; } else rest.push(p); }
  const chunks = [];
  let cur = [], cs = 200;
  for (const p of rest) { const n = kbBytes(p) + 1; if (cur.length && cs + n > KB_DOC_BYTES) { chunks.push(cur); cur = []; cs = 200; } cur.push(p); cs += n; }
  if (cur.length) chunks.push(cur);
  for (let i = 0; i < chunks.length; i++) await S.caps.db.doc(kbMorePath(pid, id, i + 1)).set({ kind: 'kbmore', of: id, i: i + 1, parts: chunks[i] });
  await S.caps.db.doc(kbPath(pid, id)).set({ ...head, parts: main, more: chunks.length });
  for (let i = chunks.length + 1; i <= prevMore; i++) { try { await S.caps.db.doc(kbMorePath(pid, id, i)).delete(); } catch { /* уже нет */ } }
}
async function kbBlock(id, pid = S.productId) {
  if (S.kb.cache[id] && S.kb.pid === pid) return S.kb.cache[id];
  const d = await kbRead(pid, id);
  if (d && S.kb.pid === pid) S.kb.cache[id] = d;
  // раздел есть в оглавлении, но записи нет (удалили в другом окне): запоминаем, иначе экран будет читать базу по кругу
  if (!d && S.kb.pid === pid) S.kb.missing = { ...(S.kb.missing || {}), [id]: true };
  return d;
}
// строка оглавления для раздела
const kbIdxEntry = (id, d) => ({ id, title: d.title, summary: String(d.summary || '').slice(0, 300), docIds: [...new Set(arrOf(d.parts).map((p) => p.docId))], parts: arrOf(d.parts).length, size: arrOf(d.parts).reduce((a, p) => a + (p.md || '').length, 0) || String(d.synth || '').length, updatedAt: d.updatedAt || 0, ph: d.ph, sh: d.synthHash || '', conf: arrOf(d.conflicts).length, ...(arrOf(d.conflicts).length ? { cf: arrOf(d.conflicts).slice(0, 6).map((c) => String(c).slice(0, 300)) } : {}), ...(d.human ? { human: true } : {}) });
let kbChain = Promise.resolve();
/* изменения раздела и оглавления — по очереди, с перечитыванием свежей версии */
function kbSave(pid, id, mut) {
  const job = kbChain.then(async () => {
    const cur = await kbRead(pid, id);
    const next = mut(cur);
    const idx = await kbIdxRead(pid);
    let blocks = idx.blocks.filter((b) => b.id !== id);
    if (next && (arrOf(next.parts).length || (next.human && String(next.synth || '').trim()))) {   // раздел, написанный человеком в папке, живёт и без выдержек
      next.updatedAt = Date.now();
      kbFit(next);
      next.ph = kbPartsHash(next.parts);
      delete next.more;
      await kbWrite(pid, id, next, cur?.more || 0);
      blocks.push(kbIdxEntry(id, next));
      if (S.kb.pid === pid) S.kb.cache[id] = next;
    } else {
      if (cur && ctxKbOn(pid)) ctxKbDelete(id);
      else if (cur) {
        await S.caps.db.doc(kbPath(pid, id)).delete();
        for (let i = 1; i <= (cur.more || 0); i++) { try { await S.caps.db.doc(kbMorePath(pid, id, i)).delete(); } catch { /* уже нет */ } }
      }
      if (S.kb.pid === pid) delete S.kb.cache[id];
    }
    blocks = blocks.sort((a, b) => String(a.title).localeCompare(String(b.title), 'ru'));
    const data = await kbIdxWrite(pid, blocks, idx.docs, idx);
    if (S.kb.pid === pid) { S.kb.index = { blocks, docs: data.docs }; S.kb.stamp = data.updatedAt; }
    return next;
  });
  kbChain = job.catch(() => {});
  return job;
}
function kbMarkDoc(pid, docId, info) {
  const job = kbChain.then(async () => {
    const idx = await kbIdxRead(pid);
    const docs = { ...idx.docs };
    if (info) docs[docId] = info; else delete docs[docId];
    const data = await kbIdxWrite(pid, idx.blocks, docs, idx);
    if (S.kb.pid === pid) { S.kb.index = { blocks: idx.blocks, docs }; S.kb.stamp = data.updatedAt; }
  });
  kbChain = job.catch(() => {});
  return job;
}
/* документ удалён или разбирается заново — его части уходят из всех разделов */
async function kbForgetDoc(pid, docId, keepMark = false) {
  if (!pid || !S.caps.db) return [];
  const idx = await kbIdxRead(pid).catch(() => ({ blocks: [] }));
  const ids = [];
  for (const b of arrOf(idx.blocks).filter((x) => arrOf(x.docIds).includes(docId))) {
    // документ разбирается заново: его сведения в прежней сводке устарели — следующая сводка возьмёт их только из новых выдержек
    await kbSave(pid, b.id, (cur) => {
      if (!cur) return null;
      const name = arrOf(cur.parts).find((p) => p.docId === docId)?.docName;
      return { ...cur, parts: arrOf(cur.parts).filter((p) => p.docId !== docId), ...(keepMark && name ? { redo: [...new Set([...arrOf(cur.redo), name])] } : {}) };
    });
    ids.push(b.id);
  }
  if (!keepMark) await kbMarkDoc(pid, docId, null);
  return ids; // этим разделам нужна новая сводка
}
/* ---------- сводка раздела по всем документам ----------
   Разбор документа кладёт в раздел выдержку «что этот документ говорит о функции». Сводка — следующий шаг: модель читает
   выдержки из всех документов раздела (и прежнюю сводку) и пишет единый текст с источниками у каждого пункта,
   выносит противоречия между документами в «Расхождения» и отмечает связанные разделы. Сводку учитывают ответы и генерация.
   Выдержки не обрезаются: небольшой раздел сводится одним запросом, большой — по подзаголовкам, а подзаголовок, который
   не помещается в запрос, сначала сжимается моделью без потери фактов (повторы и лишние слова уходят, значения остаются). */
const KB_SYNTH_MAX = 24000, KB_DOC_BYTES = 240000;
// весь раздел (основная запись и продолжения) — до 13 записей; только сверх этого сведённые выдержки убираются
const KB_TOTAL_BYTES = KB_DOC_BYTES * 13;
// один запрос сводки: материал на входе и текст на выходе (длинный JSON обрезается по длине или времени — выход держим умеренным)
const KB_REQ_IN = 24000, KB_REQ_OUT = 6000, KB_DIRECT_MAX = 13000, KB_BIG_OUT = 22000;
// сжатый повтор: если ответ не уместился — та же выборка, но короче текст
const KB_SYNTH_MODES = [{ out: KB_REQ_OUT }, { out: 3000 }];
const KB_SYNTH_V = 2; // сводка собрана из выдержек целиком — их можно убирать из раздела, когда он не помещается
const KB_CONF_HEAD = 'Расхождения между документами';
const kbPartH = (p) => p.h || hash(p.md || '');
const kbPartsHash = (parts) => hash(arrOf(parts).map((p) => `${p.docId}:${p.chunk}:${kbPartH(p)}`).sort().join('|'));
// раздел, у которого нет сводки или выдержки поменялись после неё
// устаревшая сводка — только у раздела с выдержками из документов: раздел без выдержек (написан вручную или в старом
// формате файла источника) сам и есть сводка, сводить нечего
const kbIsStale = (b) => !b.human && (b.parts == null || b.parts > 0) && (!b.sh || (!!b.ph && b.ph !== b.sh));
const kbStale = () => S.kb.index.blocks.filter(kbIsStale);
const kbSectionText = (blk) => String(blk?.synth || '').trim() || arrOf(blk?.parts).map((p) => p.md).filter(Boolean).join('\n\n');
const kbBytes = (o) => new TextEncoder().encode(JSON.stringify(o)).length;
const kbCovered = (blk, p) => !!(p.md && blk.synth && (blk.synthV || 0) >= KB_SYNTH_V && (p.at || 0) <= (blk.synthAt || 0));
// выдержки, которых ещё нет в сводке, — если их много, раздел сводится сразу, не дожидаясь конца разбора
const kbFreshBytes = (blk) => arrOf(blk?.parts).filter((p) => p.md && !kbCovered(blk, p)).reduce((a, p) => a + new TextEncoder().encode(p.md).length, 0);
/* раздел хранится в основной записи и продолжениях (kbWrite) — до 13 записей по 240 КБ, ≈1,5 млн знаков выдержек.
   Только если и этого мало, выдержки, уже сведённые в полную сводку, убираются (остаётся отметка «документ, фрагмент»,
   сведения хранит сводка); самые старые несведённые — в крайнем случае. */
function kbFit(next) {
  next.parts = [...next.parts]; // массив из базы — только для чтения: меняем копию
  if (next.synth) next.synth = String(next.synth).slice(0, KB_SYNTH_MAX);
  if (kbBytes(next) <= KB_TOTAL_BYTES) return;
  const order = next.parts.map((p, i) => i).sort((a, b) => (next.parts[a].at || 0) - (next.parts[b].at || 0));
  for (const i of order) {
    if (kbBytes(next) <= KB_TOTAL_BYTES) return;
    const p = next.parts[i];
    if (kbCovered(next, p)) next.parts[i] = { ...p, md: '', h: kbPartH(p), cut: true };
  }
  for (const i of order) {
    if (kbBytes(next) <= KB_TOTAL_BYTES) return;
    const p = next.parts[i];
    if (p.md) { next.parts[i] = { ...p, md: '', h: kbPartH(p), cut: true, lost: true }; next.lost = (next.lost || 0) + 1; }
  }
}
// текст по подзаголовкам «### …» из списка KB_SUBHEADS; текст до первого подзаголовка — к first
function kbBySubs(md, first = KB_SUBHEADS[0]) {
  const out = new Map();
  let cur = first;
  for (const line of String(md || '').split('\n')) {
    const m = /^#{2,4}\s+(.+?)\s*$/.exec(line);
    if (m) {
      const k = normKey(m[1]) === normKey(KB_CONF_HEAD) ? KB_CONF_HEAD : KB_SUBHEADS.find((s) => normKey(s) === normKey(m[1]));
      if (k) { cur = k; continue; }
    }
    out.set(cur, (out.get(cur) || '') + line + '\n');
  }
  for (const [k, v] of [...out]) { const t = v.trim(); if (t) out.set(k, t); else out.delete(k); }
  return out;
}
const kbLiveParts = (blk) => arrOf(blk.parts).filter((p) => p.md).sort((a, b) => (a.docName === b.docName ? (a.chunk || 0) - (b.chunk || 0) : String(a.docName).localeCompare(String(b.docName), 'ru')));
// материал сводки: выдержки документов и прежняя сводка, разложенные по подзаголовкам
function kbMaterial(blk) {
  const items = [];
  for (const p of kbLiveParts(blk)) for (const [sub, text] of kbBySubs(p.md)) if (sub !== KB_CONF_HEAD) items.push({ sub, doc: p.docName, sections: arrOf(p.sections), text });
  for (const [sub, text] of kbBySubs(blk.synth)) if (sub !== KB_CONF_HEAD) items.push({ sub, doc: '', kind: 'prev', text });
  return items;
}
const kbSize = (items) => items.reduce((a, x) => a + x.text.length, 0);
const kbRedoNote = (blk) => (arrOf(blk.redo).length ? ` Документы ${arrOf(blk.redo).map((n) => `«${n}»`).join(', ')} обновлены после прежней сводки: их сведения из прежней сводки устарели — бери их только из выдержек.` : '');
// материал — пачками не больше cap знаков; слишком длинный кусок делится по абзацам и строкам
function kbPack(items, cap) {
  const pieces = [];
  for (const it of items) {
    if (it.text.length <= cap) { pieces.push(it); continue; }
    let cur = '';
    for (const ln of it.text.split('\n')) {
      for (let s = ln; s.length; ) {
        const take = s.slice(0, cap); s = s.slice(cap);
        if (cur && cur.length + take.length + 1 > cap) { pieces.push({ ...it, text: cur }); cur = ''; }
        cur += (cur ? '\n' : '') + take;
      }
    }
    if (cur) pieces.push({ ...it, text: cur });
  }
  const packs = [];
  let cur = null;
  for (const it of pieces) {
    if (cur && cur.size + it.text.length <= cap) { cur.items.push(it); cur.size += it.text.length; }
    else packs.push(cur = { items: [it], size: it.text.length });
  }
  return packs.map((p) => p.items);
}
const kbItemLabel = (x) => (x.kind === 'prev' ? 'прежняя сводка — источники в скобках у пунктов' : x.kind === 'cond' ? 'сжатый материал — источники в скобках у пунктов' : x.doc);
const kbItemsText = (items) => items.map((x) => `<excerpt document="${kbItemLabel(x)}"${arrOf(x.sections).length ? ` sections="${x.sections.join(', ')}"` : ''}>\n${x.text}\n</excerpt>`).join('\n\n');
function promptKbSynth(prod, blk, docNames, others, mode = KB_SYNTH_MODES[0]) {
  const parts = kbLiveParts(blk);
  const prev = String(blk.synth || '');
  return renderPrompt("promptKbSynth", { "e1": prod?.name || 'Продукт', "blk_title": blk.title, "e3": docNames.map((n) => '- ' + n).join('\n') || '- нет', "e4": prev ? `\n## Прежняя сводка раздела\n${prev}\n` : '', "e5": parts.map((p) => `<excerpt document="${p.docName}"${arrOf(p.sections).length ? ` sections="${p.sections.join(', ')}"` : ''}>\n${String(p.md || '')}\n</excerpt>`).join('\n\n') || 'новых выдержек нет — сведения есть в прежней сводке', "e6": kbOutline(others, `${blk.title} ${blk.summary || ''} ${String(blk.synth || '').slice(0, 4000)}`, { top: 150, cap: 12000, sum: 0 }) || 'нет', "e7": KB_SUBHEADS.join(', '), "e8": kbRedoNote(blk), "KB_CONF_HEAD": KB_CONF_HEAD, "mode_out": mode.out });
}
// большой раздел, шаг 1: сжать материал подзаголовка без потери фактов
function promptKbCondense(prod, blk, sub, items, docNames, out) {
  return renderPrompt("promptKbCondense", { "e1": prod?.name || 'Продукт', "blk_title": blk.title, "sub": sub, "e4": docNames.map((n) => '- ' + n).join('\n') || '- нет', "e6": kbItemsText(items), "e7": kbRedoNote(blk), "out": out });
}
// большой раздел, шаг 2: сводка по группе подзаголовков
function promptKbSynthPart(prod, blk, grp, k, n, docNames, others, prevConf, scale = 1) {
  const subs = grp.subs.map((g) => g.sub), lim = (x) => Math.max(400, Math.round(x * scale));
  return renderPrompt("promptKbSynthPart", { "e1": prod?.name || 'Продукт', "blk_title": blk.title, "k": k, "n": n, "e5": subs.map((s) => `«${s}»`).join(', '), "e6": docNames.map((x) => '- ' + x).join('\n') || '- нет', "e7": grp.subs.map((g) => `### ${g.sub}\n${kbItemsText(g.items)}`).join('\n\n'), "e8": prevConf.length ? `\n## Расхождения из прежней сводки\n${prevConf.map((c) => '- ' + c).join('\n')}\n` : '', "e9": kbOutline(others, `${blk.title} ${blk.summary || ''} ${String(blk.synth || '').slice(0, 4000)}`, { top: 150, cap: 12000, sum: 0 }) || 'нет', "e10": subs.join(', '), "e11": kbRedoNote(blk), "e12": grp.subs.map((g) => `«${g.sub}» — до ${lim(g.out)} знаков`).join(', '), "e13": lim(grp.out), "e14": subs[0] });
}
// ответы шагов большого раздела помним до перезагрузки: повтор после лимита или сбоя не делает готовые шаги заново
const kbStepCache = new Map();
async function kbAskStep(prompt, J, onProgress, keep) {
  const key = keep ? hash(prompt) : '';
  if (key && kbStepCache.has(key)) return kbStepCache.get(key);
  const res = await ask(prompt, { step: 'kb', tier: auxTier(), cache: false, signal: J.ctl.signal, ai: S.settings.genAI, onProgress });
  if (key && res && typeof res === 'object') {
    if (kbStepCache.size > 300) kbStepCache.delete(kbStepCache.keys().next().value);
    kbStepCache.set(key, res);
  }
  return res;
}
// повтор шага с более коротким ответом; ошибки лимита, доступа и сети — сразу наверх
async function kbTryStep(make, J, line, what, keep = true) {
  let lastErr = null;
  for (let a = 0; a < KB_SYNTH_MODES.length; a++) {
    try {
      const res = await kbAskStep(make(KB_SYNTH_MODES[a].out / KB_SYNTH_MODES[0].out), J, (n) => { line.text = `${what}${a ? ' (короче)' : ''}: пишет — ${fmtKChars(n)}`; renderKbAny(); }, keep);
      if (res && typeof res === 'object') return res;
      lastErr = { code: 'empty_completion' };
    } catch (e) {
      if (e?.code === 'cancelled' || KB_FATAL.has(e?.code)) throw e;
      lastErr = e;
    }
  }
  throw lastErr || { code: 'empty_completion' };
}
const kbConfKey = (c) => normKey(c).slice(0, 90);
// большой раздел: подзаголовки сжимаются до размера запроса, затем сводятся группами и собираются в одну сводку
async function kbSynthBig(blk, docNames, others, J, line, M) {
  const prod = curProduct(), items = kbMaterial(blk);
  const T = Math.min(KB_BIG_OUT, Math.max(KB_REQ_OUT, Math.round(M * 0.4)));
  const subs = KB_SUBHEADS.map((sub) => ({ sub, items: items.filter((x) => x.sub === sub) })).filter((g) => g.items.length);
  for (const g of subs) g.out = Math.min(KB_REQ_OUT, Math.max(600, Math.round((T * kbSize(g.items)) / M)));
  // сколько шагов впереди — для прогресса (сжатие считается по первому кругу, группы — по ожидаемому размеру)
  const est = (g) => { const m = kbSize(g.items); return m > KB_REQ_IN ? Math.min(KB_REQ_IN, Math.round(m * 0.45)) : m; };
  let groupsEst = 0;
  { let o = Infinity, m = Infinity; for (const g of subs) { const s = est(g); if (o + g.out <= KB_REQ_OUT && m + s <= KB_REQ_IN) { o += g.out; m += s; } else { groupsEst++; o = g.out; m = s; } } }
  J.step = { title: blk.title, k: 0, n: subs.reduce((a, g) => a + (kbSize(g.items) > KB_REQ_IN ? kbPack(g.items, KB_REQ_IN).length : 0), 0) + groupsEst };
  const tick = () => { J.step.k++; J.step.n = Math.max(J.step.n, J.step.k); renderKbAny(); };
  line.text = `Сводка «${blk.title}»: раздел большой (${fmtKChars(M)}) — свожу по подзаголовкам, без обрезки`; renderKbAny();
  for (const g of subs) {
    for (let round = 0; kbSize(g.items) > KB_REQ_IN && round < 6; round++) {
      const packs = kbPack(g.items, KB_REQ_IN), next = [];
      for (let i = 0; i < packs.length; i++) {
        if (J.ctl.signal.aborted) throw { code: 'cancelled' };
        tick();
        const out = Math.min(KB_REQ_OUT, Math.max(1500, Math.round(kbSize(packs[i]) * 0.45)));
        const what = `Сводка «${blk.title}»: сжимаю «${g.sub}»${packs.length > 1 ? `, часть ${i + 1}/${packs.length}` : ''}`;
        line.text = what; renderKbAny();
        const r = await kbTryStep((s) => promptKbCondense(prod, blk, g.sub, packs[i], docNames, Math.round(out * s)), J, line, what);
        const text = String(r?.text || '').trim();
        if (text) next.push({ sub: g.sub, doc: '', kind: 'cond', text });
      }
      g.items = next;
    }
  }
  const groups = [];
  let cur = null;
  for (const g of subs) {
    if (!g.items.length) continue;
    const m = kbSize(g.items);
    if (cur && cur.out + g.out <= KB_REQ_OUT && cur.m + m <= KB_REQ_IN) { cur.subs.push(g); cur.out += g.out; cur.m += m; }
    else groups.push(cur = { subs: [g], out: g.out, m });
  }
  J.step.n = J.step.k + groups.length; renderKbAny();
  const prevConf = arrStr(blk.conflicts).slice(0, 30), results = [];
  for (let k = 0; k < groups.length; k++) {
    if (J.ctl.signal.aborted) throw { code: 'cancelled' };
    tick();
    const grp = groups[k], what = `Сводка «${blk.title}»: часть ${k + 1} из ${groups.length} — ${grp.subs.map((g) => g.sub).join(', ')}`;
    line.text = what; renderKbAny();
    const r = await kbTryStep((s) => promptKbSynthPart(prod, blk, grp, k + 1, groups.length, docNames, others, prevConf, s), J, line, what);
    results.push({ grp, r });
  }
  const bySub = new Map();
  for (const { grp, r } of results) {
    for (const [sub, text] of kbBySubs(r?.synth, grp.subs[0].sub)) {
      if (sub === KB_CONF_HEAD) continue;
      bySub.set(sub, [bySub.get(sub), text].filter(Boolean).join('\n'));
    }
  }
  const seen = new Set(), conflicts = [];
  for (const { r } of results) for (const c of arrStr(r?.conflicts)) { const key = kbConfKey(c); if (!seen.has(key)) { seen.add(key); conflicts.push(c); } }
  const freq = new Map();
  for (const { r } of results) for (const l of arrStr(r?.links)) freq.set(l, (freq.get(l) || 0) + 1);
  const synth = [...KB_SUBHEADS.filter((s) => bySub.has(s)).map((s) => `### ${s}\n${bySub.get(s)}`),
    ...(conflicts.length ? [`### ${KB_CONF_HEAD}\n${conflicts.map((c) => '- ' + c).join('\n')}`] : [])].join('\n\n');
  return { summary: results.map((x) => String(x.r?.summary || '').trim()).find(Boolean) || '', synth, conflicts, links: [...freq.entries()].sort((a, b) => b[1] - a[1]).map((x) => x[0]) };
}
async function kbSynthOne(pid, id, J, { soft = false } = {}) {
  let blk = null;
  const t0 = Date.now();
  try { blk = await kbRead(pid, id); } catch { blk = null; }
  if (!blk || !arrOf(blk.parts).length || S.kb.pid !== pid) return false;
  const ph = kbPartsHash(blk.parts), nDocs = new Set(blk.parts.map((p) => p.docId)).size;
  const line = { text: `Сводка «${blk.title}»: модель сводит ${nDocs} ${plural(nDocs, 'документ', 'документа', 'документов')}…`, kind: '' };
  J.log.push(line); renderKbAny();
  // в список «документы продукта сейчас» — только документы, о которых говорят выдержки или прежняя сводка (иначе запрос раздувается)
  const allNames = [...new Set([...arrOf(curProduct()?.docs).map((m) => m.name), ...S.docs.filter((d) => d.pid === pid).map((d) => d.name)])];
  const own = new Set(blk.parts.map((p) => p.docName)), prevText = String(blk.synth || '');
  const docNames = allNames.filter((n) => own.has(n) || prevText.includes(n.replace(/\.[a-z0-9]+$/i, '')));
  const others = S.kb.index.blocks.filter((b) => b.id !== id);
  const M = kbSize(kbMaterial(blk));
  let res, lastErr = null;
  try {
    if (M > KB_DIRECT_MAX) res = await kbSynthBig(blk, docNames, others, J, line, M);
    else res = await kbTryStep((s) => promptKbSynth(curProduct(), blk, docNames, others, s < 1 ? KB_SYNTH_MODES[1] : KB_SYNTH_MODES[0]), J, line, `Сводка «${blk.title}»`, false);
    if (!String(res?.synth || '').trim()) { lastErr = { code: 'empty_completion' }; res = null; }
  } catch (e) {
    if (e?.code === 'cancelled') throw e;
    lastErr = e; res = null;
  } finally { J.step = null; }
  if (!res) {
    line.text = `Сводка «${blk.title}»: ${errText(lastErr)}`; line.kind = 'err';
    const why = errText(lastErr), R = J.report;
    if (R) { R.fail++; R.reasons[why] = (R.reasons[why] || 0) + 1; }
    if (!soft && KB_FATAL.has(lastErr?.code)) { J.stop = lastErr; J.ctl.abort(); }
    renderKbAny();
    return false;
  }
  const synth = String(res.synth).trim().slice(0, KB_SYNTH_MAX);
  if (J.report) J.report.ok++;
  const byKey = new Map(others.map((b) => [normKey(b.title), b.id])), ids = new Set(others.map((b) => b.id));
  const links = [...new Set(arrStr(res?.links).map((x) => (ids.has(x) ? x : byKey.get(normKey(x)) || '')).filter(Boolean))].slice(0, 6);
  const conflicts = arrStr(res?.conflicts).map((x) => x.slice(0, 500)).slice(0, 30);
  await kbSave(pid, id, (cur) => (cur && arrOf(cur.parts).length
    ? { ...cur, synth, summary: String(res?.summary || '').trim().slice(0, 300) || cur.summary, conflicts, links, synthAt: t0, synthHash: ph, synthV: KB_SYNTH_V, big: M > KB_DIRECT_MAX ? M : 0, redo: arrOf(cur.redo).filter((n) => !arrOf(blk.redo).includes(n)) }
    : cur));
  line.text = `Сводка «${blk.title}» готова${M > KB_DIRECT_MAX ? ` · ${fmtKChars(M)} сведено в ${fmtKChars(synth.length)}` : ''}${conflicts.length ? ` · расхождений между документами: ${conflicts.length}` : ''}`; line.kind = conflicts.length ? 'warn' : 'ok';
  renderKbAny();
  return true;
}
async function kbSynthRun(pid, ids, J) {
  const list = [...new Set(ids)].filter((id) => S.kb.index.blocks.some((b) => b.id === id));
  if (!list.length) return 0;
  J.phase = 'synth';
  J.report = { total: list.length, ok: 0, fail: 0, reasons: {} };
  // документ «сведён полностью», когда готовы сводки всех разделов из списка, где он есть
  const docSets = list.map((id) => new Set(arrOf(S.kb.index.blocks.find((b) => b.id === id)?.docIds)));
  const leftByDoc = new Map();
  for (const set of docSets) for (const d of set) leftByDoc.set(d, (leftByDoc.get(d) || 0) + 1);
  J.sp = { total: list.length, done: 0, ok: 0, docsTotal: leftByDoc.size, docsDone: 0, t0: Date.now() };
  renderKbAny();
  let n = 0;
  // по одной: сводки — длинные ответы, параллельные запросы быстрее упираются в лимит
  for (let k = 0; k < list.length; k++) {
    if (J.ctl.signal.aborted) break;
    kbLease(pid);
    if (await kbSynthOne(pid, list[k], J)) { n++; J.sp.ok++; }
    J.sp.done++;
    for (const d of docSets[k]) { const r = leftByDoc.get(d) - 1; leftByDoc.set(d, r); if (!r) J.sp.docsDone++; }
    renderKbAny();
  }
  const R = J.report, left = R.total - R.ok - R.fail;
  if (R.fail || J.stop) S.kb.synthReport = { ...R, left, stop: J.stop ? errText(J.stop) : '', at: Date.now() };
  else S.kb.synthReport = null;
  if (J.stop?.code === 'rate_limited' && S.productId === pid) setTimeout(() => { if (S.productId === pid && !S.kb.job.busy && kbStale().length) kbSynthJob(kbStale().map((b) => b.id)); }, 10 * 60000);
  return n;
}
const KB_FATAL = new Set(['rate_limited', 'not_granted', 'sampling_disabled', 'not_declared', 'capability_disabled', 'capability_removed', 'session_expired', 'auth', 'network', 'provider_unavailable']);
// сводки по запросу (кнопка) и после удаления документа
async function kbSynthJob(ids) {
  const pid = S.productId;
  const list = [...new Set([...(ids || []), ...arrOf(S.kb.synthQ)])];
  S.kb.synthQ = [];
  if (!pid || !S.caps.db || !list.length) return;
  if (S.kb.job.busy) { S.kb.synthQ = list; return; } // доберём после текущей работы
  if (!aiReady(S.settings.genAI)) return toast(aiProblem(S.settings.genAI), 'err');
  if (!(await kbLease(pid))) { S.kb.note = 'Базу знаний сейчас обновляет другое окно QA pro — сводки появятся здесь сами.'; renderKbAny(); return; }
  const J = S.kb.job = { busy: true, log: [], error: '', ctl: new AbortController(), doc: '', phase: 'synth' };
  renderKbAny();
  try {
    const n = await kbSynthRun(pid, list, J);
    if (n) toast(`Сводки разделов обновлены: ${n}`);
    else if (!J.report?.fail && !J.stop && !J.ctl.signal.aborted) toast('Сводить нечего: у выбранных разделов нет выдержек из документов — их текст и есть сводка.');
  }
  catch (e) { if (e?.code !== 'cancelled') J.error = errText(e); }
  finally { J.busy = false; J.doc = ''; J.phase = ''; renderKbAny(); if (S.kb.queue.length) setTimeout(() => kbRun(), 0); }
  if (arrOf(S.kb.synthQ).length && !J.ctl.signal.aborted) setTimeout(() => kbSynthJob([]), 0);
}
// прогресс работы базы знаний — для баннера в «Разделах» и строки под списком документов
function kbProgress(J = S.kb.job) {
  if (!J?.busy) return null;
  const eta = (done, total, t0) => { if (!done || done >= total) return ''; const m = Math.round(((Date.now() - t0) / done) * (total - done) / 60000); return m >= 1 ? `осталось ≈ ${m} мин` : 'осталось меньше минуты'; };
  const step = J.step ? `«${J.step.title}» — шаг ${Math.max(1, J.step.k)} из ${Math.max(J.step.n, J.step.k, 1)}` : '';
  if (J.phase === 'synth' && J.sp) {
    const p = J.sp, fail = p.done - p.ok;
    return { pct: p.total ? Math.round((p.done / p.total) * 100) : 0, title: `Собираю сводки разделов: ${p.done} из ${p.total}`,
      line: [`документов сведено полностью: ${p.docsDone} из ${p.docsTotal}`, fail ? `не получилось: ${fail}` : '', step ? `большой раздел ${step}` : '', eta(p.done, p.total, p.t0)].filter(Boolean).join(' · ') };
  }
  if (J.dp) {
    const p = J.dp, byChunks = p.chunksTotal > 0;
    const pct = byChunks ? Math.round((p.chunksDone / p.chunksTotal) * 100) : p.total ? Math.round((p.done / p.total) * 100) : 0;
    const cur = J.doc ? `сейчас «${J.doc}»${p.part && p.part.n > 1 ? `, часть ${p.part.i} из ${p.part.n}` : ''}` : '';
    return { pct, title: `Разбираю документы по разделам: ${p.done} из ${p.total}`,
      line: [byChunks ? `фрагментов разобрано: ${p.chunksDone} из ${p.chunksTotal}` : '', p.secs.size ? `разделов: ${p.secs.size}${p.fresh.size ? `, новых ${p.fresh.size}` : ''}` : '',
        p.fail ? `не получилось: ${p.fail}` : '', step ? `свожу разросшийся раздел ${step}` : cur,
        byChunks ? eta(p.chunksDone, p.chunksTotal, p.t0) : eta(p.done, p.total, p.t0)].filter(Boolean).join(' · ') };
  }
  return null;
}
// «Что агент знает о продукте» пополняется сразу после разбора новых документов (если идёт генерация — после неё)
function kbAutoLearn(docs, tries = 0) {
  const pid = S.productId, known = new Set(S.prodKnown?.docs || []);
  const need = docs.filter((d) => d.pid === pid && d.status === 'ready' && S.docs.includes(d) && !known.has(docHash(d)));
  if (!need.length || !aiReady(S.settings.genAI)) return;
  if (S.running || S.know.busy) { if (tries < 40) setTimeout(() => { if (S.productId === pid) kbAutoLearn(docs, tries + 1); }, 30000); return; }
  learnFromDocs(false, need);
}
const kbPending = () => { const docs = S.kb.index.docs || {}; return readyDocs().filter((d) => d.pid === S.productId && docs[d.id]?.hash !== docHash(d)); };
function promptKbSplit(prod, doc, chunk, i, total, blocks) {
  return renderPrompt("promptKbSplit", { "e1": prod?.name || 'Продукт', "e2": blocks.length ? kbOutline(blocks, chunk.blocks.map((b) => b.text).join(' '), { top: 120, cap: 90000, sum: 200 }) : 'пока нет', "e3": KB_SUBHEADS.join(', '), "doc_name": doc.name, "e5": i + 1, "total": total, "e7": chunk.blocks.map((b) => `<document name="${b.doc}" part="${b.part}/${b.parts}">\n${b.text}\n</document>`).join('\n\n') });
}
function kbQueue(d) {
  if (!d || !S.caps.db || !d.pid) return;
  if (!S.kb.queue.some((x) => x.id === d.id)) S.kb.queue.push(d);
  if (!S.kb.job.busy && aiReady(S.settings.genAI)) kbRun();
  else renderKbAny();
}
const renderKbAny = () => { renderDocs(); if (S.settings.mode === 'help') renderHelp(); };
/* разбор документов по разделам: по одному запросу на фрагмент документа */
async function kbLease(pid) {
  const ref = S.caps.db.doc(`${prodPath(pid)}/meta/kbjob`);
  if (typeof ref.acquire !== 'function') return true;
  try { return !!(await ref.acquire({ holder: S.tabId, ttlMs: 120000 }))?.acquired; } catch { return true; }
}
// сколько фрагментов (запросов к модели) в документе — для прогресса разбора
/* оглавление разделов для запроса. Пока разделов не больше top — все с описаниями. Больше — сначала ближайшие к теме
   (совпадение слов в названии и описании), с описаниями, затем остальные — одними названиями, пока помещаются в cap:
   так модель видит нужные разделы при любом их числе, а не первые 200 по алфавиту. */
function kbOutline(blocks, focus, { top = 150, cap = 30000, sum = 300 } = {}) {
  const line = (b, full) => `- ${b.id} · ${String(b.title).slice(0, 100)}${full && sum && b.summary ? ' — ' + String(b.summary).slice(0, sum) : ''}`;
  if (blocks.length <= top) return blocks.map((b) => line(b, true)).join('\n');
  const q = new Set(helpTokens(String(focus || '').slice(0, 20000)));
  const sc = blocks.map((b, k) => {
    let s = 0;
    for (const w of new Set(helpTokens(b.title))) if (q.has(w)) s += 3;
    for (const w of new Set(helpTokens(b.summary || ''))) if (q.has(w)) s += 1;
    return { b, s, k };
  }).sort((a, z) => z.s - a.s || a.k - z.k);
  const out = [];
  let size = 0;
  // описания — у ближайших, пока они занимают не больше 40% бюджета; остальные — одной строкой с названием
  for (const x of sc) { const l = line(x.b, out.length < top && size < cap * 0.4); if (size + l.length + 1 > cap) continue; out.push(l); size += l.length + 1; }
  const left = blocks.length - out.length;
  return out.join('\n') + (left ? `\n(ещё ${left} ${plural(left, 'раздел', 'раздела', 'разделов')} далеки от темы и не показаны)` : '');
}
const kbChunkMemo = new WeakMap();
const kbChunksOf = (d) => { let n = kbChunkMemo.get(d); if (n == null) { n = buildChunks([d]).length; kbChunkMemo.set(d, n); } return n; };
// раздел разросся во время разбора: несведённых выдержек столько, что он может не уместиться в базе — сводим сразу
const KB_FRESH_MAX = Math.round(KB_TOTAL_BYTES * 0.6);
async function kbRun(docs) {
  const pid = S.productId;
  if (!pid || !S.caps.db) return;
  // работа уже идёт (разбор или сборка сводок): документ встаёт в очередь и разберётся после неё
  if (S.kb.job.busy) { for (const d of arrOf(docs)) if (!S.kb.queue.some((x) => x.id === d.id)) S.kb.queue.push(d); renderKbAny(); return; }
  if (!aiReady(S.settings.genAI)) return toast(aiProblem(S.settings.genAI), 'err');
  if (!(await kbLease(pid))) { S.kb.note = 'Документы разбирает другое окно QA pro — разделы появятся здесь сами.'; renderKbAny(); setTimeout(() => { if (S.kb.queue.length && !S.kb.job.busy) kbRun(); }, 130000); return; }
  S.kb.note = '';
  if (docs) for (const d of docs) if (!S.kb.queue.some((x) => x.id === d.id)) S.kb.queue.push(d);
  const J = S.kb.job = { busy: true, log: [], error: '', ctl: new AbortController(), doc: '', phase: 'split' };
  renderKbAny();
  let made = 0;
  const changed = new Set(), processed = [];
  const live = (d) => d.status === 'ready' && d.pid === pid;
  const queued = () => S.kb.queue.filter(live);
  // прогресс: документы и фрагменты (один фрагмент — один запрос к модели), найденные разделы, сбои
  J.dp = { done: 0, total: queued().length, chunksDone: 0, chunksTotal: queued().reduce((a, d) => a + kbChunksOf(d), 0), part: null, secs: new Set(), fresh: new Set(), fail: 0, t0: Date.now() };
  try {
    const prod = curProduct();
    while (S.kb.queue.length && !J.ctl.signal.aborted && S.kb.pid === pid) {
      const doc = S.kb.queue.shift();
      if (!live(doc)) { J.dp.total = J.dp.done + queued().length; continue; }
      const chunks = buildChunks([doc]);
      // в очередь могли добавить документы по ходу — пересчитываем, сколько осталось
      J.dp.total = J.dp.done + queued().length + 1;
      J.dp.chunksTotal = J.dp.chunksDone + chunks.length + queued().reduce((a, d) => a + kbChunksOf(d), 0);
      J.doc = doc.name; J.dp.part = { i: 0, n: chunks.length };
      if (S.kb.index.docs?.[doc.id]) for (const id of await kbForgetDoc(pid, doc.id, true)) changed.add(id); // документ изменился — разбираем заново
      let touched = new Set(), ok = true;
      for (let i = 0; i < chunks.length && !J.ctl.signal.aborted; i++) {
        kbLease(pid); // продлеваем аренду: окно живо и разбирает
        J.dp.part = { i: i + 1, n: chunks.length };
        const line = { text: `«${doc.name}»${chunks.length > 1 ? `, часть ${i + 1}/${chunks.length}` : ''}: модель делит на разделы…`, kind: '' };
        J.log.push(line); renderKbAny();
        let res;
        try {
          res = await ask(promptKbSplit(prod, doc, chunks[i], i, chunks.length, S.kb.index.blocks), { step: 'kb', tier: auxTier(), cache: false, signal: J.ctl.signal, ai: S.settings.genAI, onProgress: (n) => { line.text = `«${doc.name}»${chunks.length > 1 ? `, часть ${i + 1}/${chunks.length}` : ''}: пишет разделы — ${fmtKChars(n)}`; renderKbAny(); } });
        } catch (e) {
          if (e?.code === 'cancelled') throw e;
          line.text = `«${doc.name}»${chunks.length > 1 ? `, часть ${i + 1}/${chunks.length}` : ''}: ${errText(e)}`; line.kind = 'err'; ok = false; J.dp.fail++; J.dp.chunksDone++; renderKbAny(); continue;
        }
        const out = arrOf(res?.blocks).filter((b) => b && String(b.content || '').trim() && String(b.title || '').trim());
        const grown = new Set();
        for (const b of out) {
          const known = S.kb.index.blocks;
          const byId = known.find((x) => x.id === String(b.blockId || ''));
          const byTitle = known.find((x) => normKey(x.title) === normKey(b.title));
          const id = (byId || byTitle)?.id || rid('kb');
          if (!byId && !byTitle) J.dp.fresh.add(id);
          const md = String(b.content).trim().slice(0, KB_PART_MAX);
          const part = { docId: doc.id, docName: doc.name, chunk: i, sections: arrStr(b.sections).slice(0, 20), md, h: hash(md), at: Date.now() };
          const saved = await kbSave(pid, id, (cur) => {
            const parts = [...arrOf(cur?.parts).filter((p) => !(p.docId === doc.id && p.chunk === i)), part].slice(-KB_PARTS_MAX);
            // сводка, расхождения и связи остаются: до новой сводки по ним отвечают, и следующая сводка переносит их сведения
            return { ...(cur || {}), kind: 'kbblock', id, title: cur?.title || String(b.title).trim().slice(0, 120), summary: cur?.summary || String(b.summary || '').trim().slice(0, 300), parts, by: S.caps.uid || '' };
          });
          touched.add(id); changed.add(id); J.dp.secs.add(id); made++;
          if (saved && kbFreshBytes(saved) > KB_FRESH_MAX) grown.add(id);
        }
        J.dp.chunksDone++;
        line.text = `«${doc.name}»${chunks.length > 1 ? `, часть ${i + 1}/${chunks.length}` : ''}: ${out.length ? `разделов ${out.length} — ${out.map((b) => b.title).join(', ')}` : 'функциональных разделов не найдено'}`; line.kind = 'ok';
        renderKbAny();
        // разросшийся раздел сводим сейчас: тогда сведённые выдержки можно убрать из него, и новые поместятся без потерь
        for (const id of grown) {
          if (J.ctl.signal.aborted) break;
          J.log.push({ text: `Раздел «${S.kb.index.blocks.find((x) => x.id === id)?.title || id}» разросся — свожу его сейчас, чтобы ничего не потерять`, kind: '' });
          if (await kbSynthOne(pid, id, J, { soft: true })) changed.delete(id);
        }
      }
      if (ok && !J.ctl.signal.aborted) { await kbMarkDoc(pid, doc.id, { hash: docHash(doc), at: Date.now(), name: doc.name, blocks: touched.size }); processed.push(doc); }
      if (!J.ctl.signal.aborted) J.dp.done++;
      J.dp.part = null;
      renderKbAny();
    }
    // сводки: каждый затронутый раздел — по всем его документам
    for (const id of arrOf(S.kb.synthQ)) changed.add(id);
    S.kb.synthQ = [];
    if (changed.size && !J.ctl.signal.aborted && S.kb.pid === pid) { J.doc = ''; await kbSynthRun(pid, [...changed], J); }
    if (S.kb.pid === pid && pid === S.productId) updateProduct(pid, { kbUpdatedAt: Date.now() }).catch(() => {});
    if (made && !J.ctl.signal.aborted) toast('Разделы базы знаний обновлены');
  } catch (e) { if (e?.code !== 'cancelled') J.error = errText(e); }
  finally { J.busy = false; J.doc = ''; J.phase = ''; J.step = null; renderKbAny(); }
  if (processed.length && !J.ctl.signal.aborted && S.productId === pid) kbAutoLearn(processed);
  if (arrOf(S.kb.synthQ).length && !J.ctl.signal.aborted) setTimeout(() => kbSynthJob([]), 0);
  if (S.kb.queue.length && !J.ctl.signal.aborted) setTimeout(() => kbRun(), 0);
}
async function kbRename(id, title) {
  const t = String(title || '').trim().slice(0, 120);
  if (!t) return;
  try { await kbSave(S.productId, id, (cur) => (cur ? { ...cur, title: t } : null)); renderHelp(true); }
  catch { toast('Не удалось переименовать — нужны права на изменение.', 'err'); }
}
async function kbDelete(id) {
  try { await kbSave(S.productId, id, () => null); S.kb.open = null; renderHelp(true); toast('Раздел удалён'); }
  catch { toast('Не удалось удалить раздел — нужны права на изменение.', 'err'); }
}
/* разделы, близкие к вопросу, — для ответов базы знаний: сначала те, что модель выбрала по смыслу, затем совпадения слов */
async function kbForQuestion(question, limit = 2, picked = []) {
  const q = [...new Set(helpTokens(question))];
  const ids = [...new Set(picked)].filter((id) => S.kb.index.blocks.some((b) => b.id === id)).slice(0, 3);
  const scored = S.kb.index.blocks.filter((b) => !ids.includes(b.id)).map((b) => ({ b, s: helpScore(q, `${b.title} ${b.title} ${b.summary}`) })).filter((o) => o.s > 0).sort((a, b) => b.s - a.s);
  const order = [...ids, ...scored.map((o) => o.b.id)].slice(0, Math.max(limit, ids.length));
  const out = [];
  for (const id of order) { try { const d = await kbBlock(id); if (d) out.push(d); } catch { /* пропускаем */ } }
  return out;
}
/* поиск по смыслу: до поиска модель (быстрая) называет разделы, где вероятен ответ, и добавляет синонимы,
   формулировки из документации и термины продукта — так находятся фрагменты, где те же вещи названы иначе */
function promptHelpExpand(prod, question, blocks, terms) {
  return renderPrompt("promptHelpExpand", { "e1": prod?.name || 'Продукт', "question": question, "e3": kbOutline(blocks, question + ' ' + (terms || ''), { top: 200, cap: 60000, sum: 140 }) || 'разделов пока нет', "e4": terms ? `\n## Термины продукта\n${terms}\n` : '' });
}
function passportTerms() {
  let on = false; const out = [];
  for (const line of String(knowOf(null)?.passport || '').split('\n')) {
    const m = /^#{1,3}\s+(.*)$/.exec(line);
    if (m) { on = /термин/i.test(m[1]); continue; }
    if (on && line.trim()) out.push(line.trim());
  }
  return out.join('\n').slice(0, 1500);
}
async function helpExpand(question, signal) {
  const res = await ask(promptHelpExpand(curProduct(), question, S.kb.index.blocks, passportTerms()), { step: 'help', tier: 'quick', cache: false, signal, ai: S.settings.genAI, onProgress: () => {} });
  const ids = new Set(S.kb.index.blocks.map((b) => b.id)), byKey = new Map(S.kb.index.blocks.map((b) => [normKey(b.title), b.id]));
  const sections = [...new Set(arrStr(res?.sections).map((x) => (ids.has(x) ? x : byKey.get(normKey(x)) || '')).filter(Boolean))].slice(0, 3);
  return { sections, terms: arrStr(res?.terms).map((t) => t.slice(0, 80)).slice(0, 12) };
}
const kbArticleText = (blk) => arrOf(blk?.parts).map((p) => p.md).join('\n\n');
/*__CTX__*/
/*__PART3__*/
