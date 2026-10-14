(() => {
'use strict';

/* ================= constants ================= */
const TYPES = ['api', 'ui', 'e2e'];
const TITLE_TAG = { api: '[BE]', ui: '[FE]', e2e: '[E2E]' }, KAFKA_TAG = '[Kafka]';   // метка вида теста в начале названия кейса
const TL = { api: 'API', ui: 'UI', e2e: 'E2E' };
const TYPE_DESC = { api: 'Эндпоинты, коды ответов', ui: 'Экраны, формы, сообщения', e2e: 'Сквозные сценарии' };
const DEPTHS = [
  { id: 'smoke', label: 'Смоук', hint: 'Только ключевые позитивные проверки, 1–2 на требование.',
    prompt: 'Смоук: только ключевые позитивные проверки основного функционала, 1–2 проверки на требование.' },
  { id: 'standard', label: 'Базовый', hint: 'Позитивные, основные негативные и граничные проверки, 2–5 на требование.',
    prompt: 'Базовый: позитивные проверки, основные негативные сценарии и граничные значения, 2–5 проверок на требование.' },
  { id: 'full', label: 'Полный', hint: 'Техники тест-дизайна: классы эквивалентности, границы, состояния, ошибки, права.',
    prompt: 'Полный: применяй техники тест-дизайна — классы эквивалентности, граничные значения, таблицы решений, переходы состояний, обработку ошибок, базовые проверки безопасности и прав доступа; 4–10 проверок на требование.' },
];
const TIER_LABEL = { quick: 'быстрая', default: 'стандартная', complex: 'максимальная' };
/* Модель по этапам: «как основная» или уровень (быстрая ≈ класс Haiku, стандартная ≈ Sonnet, максимальная ≈ Opus).
   Рекомендации — по замеру расхода на тестовом ТЗ (141 кейс, 73 вызова) и ценам API на октябрь 2026. */
const STAGE_TIER_VALUES = ['same', 'quick', 'default', 'complex'];
const STAGES = [
  { id: 'analyze', title: 'Анализ, план и сверка', desc: 'требования, чек-лист, план проверок, сверка кейсов при актуализации', rec: 'default',
    why: 'Здесь формируются требования и план: пропущенное требование не попадёт ни в один кейс, а при актуализации ошибка сверки оставит устаревший кейс. Ответы длинные (около 5 тыс. токенов), поэтому максимальная модель редко окупается. Быстрая чаще упускает критерии приёмки — на нашем ТЗ это не проверялось.' },
  { id: 'generate', title: 'Тест-кейсы', desc: 'написание, доработка и актуализация кейсов', rec: 'default',
    why: 'Самый чувствительный к качеству этап и около половины расхода токенов (на нашем ТЗ — 45% входа и 53% выхода). Стандартная модель дала около 4,7 балла из 5 по слепой оценке. Максимальную берите для сложных предметных областей и сквозных сценариев.' },
  { id: 'review', title: 'Ревью', desc: 'проверка кейсов и пунктов чек-листа', rec: 'quick',
    why: 'Ревью расходует почти столько же, сколько генерация (47% входных токенов), а проверяет по готовым критериям. Быстрая модель по входу примерно в 20 раз дешевле (Haiku 5.5 — $0,10, Sonnet 5.5 — $2 за 1 млн токенов). На быстрой ревью не проверялось: если замечаний станет слишком много или они окажутся ложными, вернитесь на стандартную.' },
  { id: 'aux', title: 'Служебные шаги', desc: 'покрытие, знания о продукте, справка по базе знаний, сокращение набора, формат экспорта', rec: 'quick',
    why: 'Короткие ответы и несложные решения (3–9 тыс. токенов на вызов), поэтому быстрой, как правило, хватает, а экономия заметна. Если справка отвечает неточно или сокращение оставляет лишнее, поднимите до стандартной.' },
];
// какой этап использует шаг запроса (шаг — поле step у ask)
const STAGE_OF_STEP = { analyze: 'analyze', checklist: 'analyze', plan: 'analyze', map: 'analyze', generate: 'generate', coverage: 'generate', actualize: 'generate', refine: 'generate', answers: 'generate', fix: 'generate', review: 'review', knowledge: 'aux', kb: 'aux', help: 'aux', lesson: 'aux', export: 'aux', other: 'aux' };
const CHUNK = 24000;          // знаков на один вызов анализа
const FULLDOC_LIMIT = 15000;  // до этого объёма документы целиком идут в генерацию
const CONCURRENCY = 2;
const STEPS = [
  { id: 'parse', title: 'Разбор документов', desc: 'Текст извлекается из DOCX, PDF, XLSX, CSV, TXT и MD прямо в браузере — файлы никуда не загружаются.' },
  { id: 'analyze', title: 'Анализ требований', desc: 'Агент выделяет проверяемые требования, критерии приёмки и вопросы к документации.' },
  { id: 'checklist', title: 'Чек-лист', desc: 'Короткие пункты проверок по функциональным областям с отметками «Смоук» и «Регресс».' },
  { id: 'map', mode: 'update', title: 'Сверка кейсов с ТЗ', desc: 'Каждый кейс из файла сопоставляется с требованиями: актуален, нужно исправить или устарел — с причиной.' },
  { id: 'actualize', mode: 'update', title: 'Актуализация', desc: 'Кейсы переписываются по шаблонам команды API, UI и E2E, расхождения с документацией исправляются.' },
  { id: 'plan', title: 'План тестирования', desc: 'Требования распределяются по видам тестов, для каждой группы составляется список проверок с учётом глубины.',
    titleUpd: 'План новых проверок', descUpd: 'Требования, которые не покрыты кейсами из файла, распределяются по видам тестов.' },
  { id: 'generate', title: 'Генерация тест-кейсов', desc: 'Кейсы пишутся строго по шаблонам и размечаются наборами «Смоук» и «Регресс». В агентном режиме модель сама ищет в документах форматы, коды и тексты ошибок.',
    titleUpd: 'Новые тест-кейсы', descUpd: 'Агент дописывает кейсы для непокрытых требований по шаблонам команды.' },
  { id: 'coverage', title: 'Проверка покрытия', desc: 'Требования без кейсов находятся автоматически, агент дописывает для них проверки.' },
  { id: 'knowledge', title: 'Знания о продукте', desc: 'Агент дополняет паспорт продукта: модули, роли, экраны, API, бизнес-правила и термины. Следующие генерации опираются на него и не повторяют готовые проверки.', optional: true, auto: true },
  { id: 'answers', title: 'Учёт ответов на вопросы', desc: 'Агент определяет, какие кейсы затрагивают ответы, исправляет их и дописывает недостающие проверки.', optional: true },
  { id: 'review', title: 'Ревью', desc: 'Субагент-ревьюер проверяет чек-лист и кейсы по документации, шаблонам и правилам ревью.', optional: true },
  { id: 'fix', title: 'Исправление замечаний', desc: 'Агент исправляет кейсы и пункты по замечаниям ревьюера.', optional: true },
];
const stepsOf = (mode) => STEPS.filter((s) => !s.mode || s.mode === mode);
const stepTitle = (s, mode) => (mode === 'update' && s.titleUpd ? s.titleUpd : s.title);
const stepDesc = (s, mode) => (mode === 'update' && s.descUpd ? s.descUpd : s.desc);
const UPD_ST = { same: 'Без изменений', changed: 'Изменён', new: 'Новый', obsolete: 'Устарел' };
const SUITES = ['smoke', 'regression'];
const SUITE_RU = { smoke: 'Смоук', regression: 'Регресс' };
const LIBS = {
  mammoth: ['https://cdn.jsdelivr.net/npm/mammoth@1.8.0/mammoth.browser.min.js', 'https://unpkg.com/mammoth@1.8.0/mammoth.browser.min.js'],
  pdf: ['https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.min.js', 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js'],
  pdfWorker: ['https://cdn.jsdelivr.net/npm/pdfjs-dist@3.11.174/build/pdf.worker.min.js', 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js'],
  xlsx: ['https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js', 'https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js'],
  yaml: ['https://cdnjs.cloudflare.com/ajax/libs/js-yaml/4.1.0/js-yaml.min.js', 'https://cdn.jsdelivr.net/npm/js-yaml@4.1.0/dist/js-yaml.min.js'],
};

/* ================= default templates (заменяются шаблонами команды) ================= */
const DEFAULT_TPL = /*@tpl*/null; // шаблоны по умолчанию: templates/*.md (подставляет build.py)
const SAMPLE_DOC = `# ТЗ: Восстановление пароля в личном кабинете
Версия 1.3

## 1. Назначение
Пользователь, забывший пароль, восстанавливает доступ к личному кабинету по ссылке, отправленной на email, указанный при регистрации.

## 2. Экран «Восстановление пароля»
2.1. На странице входа /login под полем пароля отображается ссылка «Забыли пароль?». По нажатию открывается экран «Восстановление пароля».
2.2. Экран содержит поле Email (обязательное, до 254 символов) и кнопку «Отправить ссылку». Кнопка неактивна, пока поле пустое.
2.3. Если введён email неверного формата, под полем выводится сообщение «Введите корректный email». Запрос на сервер не отправляется.
2.4. После отправки показывается сообщение «Если адрес зарегистрирован, мы отправили на него ссылку для сброса пароля». Сообщение одинаково для зарегистрированных и незарегистрированных адресов.
2.5. Экран «Новый пароль» открывается по ссылке из письма и содержит поля «Новый пароль», «Повторите пароль» и кнопку «Сохранить».
2.6. Требования к паролю: от 8 до 64 символов, минимум одна заглавная латинская буква и одна цифра. Нарушения показываются под полем: «Пароль должен содержать от 8 до 64 символов», «Добавьте заглавную букву и цифру». При несовпадении паролей — «Пароли не совпадают».

## 3. API
3.1. POST /api/v1/password-reset
Тело: {"email": string}. Ответы:
- 202 Accepted — {"status": "sent"} для любого корректного email, в том числе незарегистрированного;
- 400 Bad Request — {"code": "INVALID_EMAIL"} при неверном формате;
- 429 Too Many Requests — {"code": "RATE_LIMIT", "retryAfter": <секунды>} при превышении лимита.
3.2. POST /api/v1/password-reset/confirm
Тело: {"token": string, "password": string}. Ответы:
- 200 OK — пароль изменён, все активные сессии пользователя завершаются;
- 400 Bad Request — {"code": "WEAK_PASSWORD"} при нарушении требований п. 2.6;
- 410 Gone — {"code": "TOKEN_EXPIRED"}, если ссылка просрочена или уже использована.

## 4. Ограничения
4.1. Ссылка действует 30 минут и может быть использована один раз.
4.2. Не более 3 запросов на сброс для одного email за 15 минут. При превышении на экране показывается «Слишком много попыток. Повторите через N мин.».
4.3. Письмо отправляется в течение 1 минуты с адреса no-reply@example.ru, тема «Восстановление пароля».

## 5. Сквозной сценарий
Пользователь запрашивает ссылку, получает письмо, переходит по ссылке, задаёт новый пароль и входит в личный кабинет с новым паролем. Старый пароль после смены не принимается.`;

/* ================= utils ================= */
const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const fmtN = (n) => Number(n || 0).toLocaleString('ru-RU');
const rid = (p = '') => p + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
const pad = (n, w = 3) => String(n).padStart(w, '0');
function plural(n, one, few, many) {
  const a = Math.abs(n) % 100, b = a % 10;
  if (a > 10 && a < 20) return many;
  if (b > 1 && b < 5) return few;
  if (b === 1) return one;
  return many;
}
function fmtDate(ts) {
  const d = new Date(ts);
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }) + ' ' + d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}
function fmtDur(ms) {
  if (ms == null || ms < 0) return '';
  const s = Math.round(ms / 1000);
  return s < 60 ? `${s} с` : `${Math.floor(s / 60)} мин ${pad(s % 60, 2)} с`;
}
function fmtClock(ms) { const s = Math.max(0, Math.floor(ms / 1000)); return `${Math.floor(s / 60)}:${pad(s % 60, 2)}`; }
function fmtKChars(n) { return n >= 1000 ? `${(n / 1000).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} тыс. знаков` : `${n} ${plural(n, 'знак', 'знака', 'знаков')}`; }
function tryParse(s) { try { return { ok: true, value: JSON.parse(s) }; } catch (e) { return { ok: false, error: e.message }; } }
function lsGet(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch { return d; } }
function lsSet(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* storage unavailable */ } }
function toast(msg, kind = '') {
  const el = document.createElement('div');
  el.className = 'toast ' + kind;
  el.textContent = msg;
  $('#toasts').append(el);
  setTimeout(() => el.remove(), kind === 'err' ? 6000 : 3000);
}
async function copyText(text) {
  try { await navigator.clipboard.writeText(text); toast('Скопировано в буфер обмена'); }
  catch { toast('Браузер не дал доступ к буферу. Выделите текст и скопируйте вручную.', 'err'); }
}
async function pool(items, n, fn, signal) {
  let i = 0;
  const worker = async () => { while (i < items.length && !signal?.aborted) { const k = i++; await fn(items[k], k); } };
  await Promise.all(Array.from({ length: Math.min(n, items.length) }, worker));
}

/* ================= state ================= */
const saved = lsGet('tca.settings', {});
const inClaude = !!(window.claude && typeof window.claude.use === 'function');
const freshPc = () => ({ type: 'all', q: '', runs: {}, order: [], busy: false, loaded: false, at: 0, error: '' });
const S = {
  docs: [],
  settings: {
    outputs: { cases: true, checklist: true, ...(saved.outputs || {}) },
    types: { api: true, ui: true, e2e: true, ...(saved.types || {}) },
    depth: saved.depth || 'standard',
    genAI: saved.genAI || (saved.tier ? 'claude:' + saved.tier : 'claude:default'),
    reviewAI: saved.reviewAI || 'same',
    agentTools: saved.agentTools !== false,
    autoResume: saved.autoResume !== false,
    skipExisting: saved.skipExisting !== false,
    mode: ['update', 'help'].includes(saved.mode) ? saved.mode : 'generate',
    economy: !!saved.economy,                       // экономный режим: быстрая модель для вспомогательных шагов, меньше контекста
    target: Math.round(Number(saved.target)) >= 1 && Math.round(Number(saved.target)) <= 300 ? Math.round(Number(saved.target)) : null,   // сколько проверок в плане; null — без ограничения
    strictRules: saved.strictRules === true,   // строгий режим: при ревью исправлять нарушения правил запросом к модели (тратит запросы)
    apiFilter: typeof saved.apiFilter === 'string' ? saved.apiFilter.slice(0, 300) : '',   // для OpenAPI/Swagger: какие эндпоинты брать
    reuseAnalysis: saved.reuseAnalysis !== false,   // не анализировать заново те же документы
    kbAuto: saved.kbAuto !== false,                 // разбирать новые документы по разделам базы знаний автоматически
    stages: Object.fromEntries(STAGES.map((x) => [x.id, STAGE_TIER_VALUES.includes(saved.stages?.[x.id]) ? saved.stages[x.id] : 'same'])),   // модель по этапам: same | quick | default | complex
  },
  upd: { file: null },   // актуализация: файл с тест-кейсами
  help: { pid: null, items: [], loaded: false, busy: false, draft: '', ctl: null, error: '', ans: {} },   // база знаний: вопросы и ответы
  helpView: lsGet('qapro.kbView', 'blocks'),    // база знаний: «Разделы», «Вопросы» или «Материалы»
  kb: { pid: null, index: { blocks: [], docs: {} }, loaded: false, cache: {}, open: null, q: '', queue: [], synthQ: [], job: { busy: false, log: [], error: '', ctl: null, doc: '' }, edit: null },
  // указания агенту: правила, шаблоны API/UI/E2E, формат экспорта
  cfg: { rules: '', tpl: { api: { ...DEFAULT_TPL.api }, ui: { ...DEFAULT_TPL.ui }, e2e: { ...DEFAULT_TPL.e2e } }, exportFormat: '', reviewRules: '' },
  cfgTeam: { rules: null, api: null, ui: null, e2e: null, export: null, review: null }, // {updatedAt, value} — сохранённая версия команды
  cfgDirty: { rules: false, api: false, ui: false, e2e: false, export: false, review: false },
  conns: lsGet('qapro.conns', []),          // подключения к другим ИИ — ключи только в этом браузере
  connEdit: null, connTest: null,
  tms: { kind: 'sfera', baseUrl: '', token: '', user: '', project: '', section: '', state: 'NotReady', duration: 10, url: '', headers: '', mode: 'case', ...lsGet('qapro.tms', {}) },
  tmsTest: null, tmsLog: [], tmsBusy: false, tmsReup: false,
  qaCtx: { all: '', api: '', ui: '', e2e: '' }, qaCtxType: 'all', ctxDirty: false,   // доп. контекст от QA
  // продукты: общий для команды контекст — документы, доп. контекст, запуски и знания агента
  products: [], productId: null, prodReady: false, prodIndex: { pid: null, cases: [], checklist: [] }, prodKnown: { reqs: [], qa: [], docs: [] },
  runDocs: new Set(), runDocsFresh: false, caseSel: new Set(), know: { busy: false, log: [], error: '', ctl: null }, passEdit: null, prodDlg: null, legacy: [],
  tabId: rid('tab'), sessionReady: false, follow: null, resume: null,   // сессия: восстановление и продолжение
  lessons: [],                              // память агента: правила из замечаний пользователя
  fdFilter: 'open', fdUI: new Map(),
  clGroupEdit: null, clRefine: null,
  cfgTab: 'tpl', cfgType: 'api', setTab: 'model',
  run: null,
  running: false,
  ctl: null,
  tab: 'agent',
  prodOpen: lsGet('qapro.prodOpen', true) !== false,
  docsFold: lsGet('qapro.docsFold', {}),     // список документов свёрнут — отдельно для каждого режима
  kbFold: lsGet('qapro.kbFold', false) === true, // список разделов базы знаний свёрнут
  caps: { ready: false, sample: null, tools: false, db: null, user: null, downloads: null, uid: null, canEdit: false },
  history: [], historyState: 'idle',
  caseUI: new Map(),
  reqOpen: new Set(),
  filter: { type: 'all', suite: 'all', q: '' },
  casesScope: 'run',     // вкладка «Тест-кейсы»: 'run' — кейсы открытого запуска, 'product' — все кейсы продукта
  pc: freshPc(),         // кейсы продукта: фильтры и прочитанные запуски
  secEdit: null,         // переименование раздела: { key, doc, value }
  localSections: lsGet('qapro.sections', {}),   // названия разделов без продукта
  clFilter: { type: 'all', suite: 'all' },
  clEdit: null,
  exp: null, expCtl: null, expCache: new Map(),
  pendingCasesRender: false,
};
function saveSettings() { lsSet('tca.settings', S.settings); }
const CFG_KEYS = ['rules', 'api', 'ui', 'e2e', 'export', 'review'];
function cfgValue(k) { return k === 'rules' ? S.cfg.rules : k === 'export' ? S.cfg.exportFormat : k === 'review' ? S.cfg.reviewRules : S.cfg.tpl[k]; }
function setCfgValue(k, v) { if (k === 'rules') S.cfg.rules = v; else if (k === 'export') S.cfg.exportFormat = v; else if (k === 'review') S.cfg.reviewRules = v; else S.cfg.tpl[k] = v; }
function cfgDefault(k) { return TYPES.includes(k) ? { ...DEFAULT_TPL[k] } : ''; }
const saveConns = () => lsSet('qapro.conns', S.conns);
const saveTms = () => lsSet('qapro.tms', S.tms);
function saveDrafts() {
  const d = {};
  for (const k of CFG_KEYS) if (S.cfgDirty[k]) d[k] = cfgValue(k);
  lsSet('qapro.cfgDraft', d);
}
(function loadDrafts() {
  const d = lsGet('qapro.cfgDraft', null);
  if (d) {
    for (const k of CFG_KEYS) if (d[k] != null) { setCfgValue(k, typeof d[k] === 'object' ? { ...cfgDefault(k), ...d[k] } : String(d[k])); S.cfgDirty[k] = true; }
  } else if (saved.extra) { S.cfg.rules = saved.extra; S.cfgDirty.rules = true; }
})();

/* ================= автономная версия: локальное хранилище и скачивание ================= */
function makeLocalDB() {
  const P = 'qapro.db:';
  const subs = new Set();
  const keys = () => { const out = []; try { for (let i = 0; i < localStorage.length; i++) { const k = localStorage.key(i); if (k && k.startsWith(P)) out.push(k.slice(P.length)); } } catch { /* storage unavailable */ } return out; };
  const read = (p) => { try { const v = localStorage.getItem(P + p); return v ? JSON.parse(v) : undefined; } catch { return undefined; } };
  const write = (p, d) => {
    try { if (d === undefined) localStorage.removeItem(P + p); else localStorage.setItem(P + p, JSON.stringify(d)); }
    catch { throw { code: 'quota_exceeded', message: 'Хранилище браузера заполнено — удалите старые запуски из истории.' }; }
    setTimeout(() => subs.forEach((f) => f()), 0);
  };
  const snap = (p) => { const d = read(p); return { id: p.split('/').pop(), exists: d !== undefined, data: () => d, metadata: {} }; };
  const doc = (p) => ({
    id: p.split('/').pop(), path: p, get: async () => snap(p),
    set: async (d) => write(p, JSON.parse(JSON.stringify(d))), update: async (d) => write(p, { ...(read(p) || {}), ...d }),
    delete: async () => write(p, undefined),
    onSnapshot: (next) => { const f = () => next(snap(p)); subs.add(f); setTimeout(f, 0); return () => subs.delete(f); },
  });
  const query = (p, filters = [], ord = null, lim = 1000) => {
    const run = () => {
      let docs = keys().filter((k) => k.startsWith(p + '/') && !k.slice(p.length + 1).includes('/')).map(snap).filter((x) => x.exists);
      for (const [f, op, v] of filters) if (op === '==') docs = docs.filter((x) => x.data()[f] === v);
      if (ord) docs.sort((a, b) => ((a.data()[ord[0]] ?? 0) > (b.data()[ord[0]] ?? 0) ? 1 : -1) * (ord[1] === 'desc' ? -1 : 1));
      docs = docs.slice(0, lim);
      return { docs, size: docs.length, empty: !docs.length, docChanges: () => [], metadata: {} };
    };
    return {
      path: p, where: (f, op, v) => query(p, [...filters, [f, op, v]], ord, lim), orderBy: (f, d) => query(p, filters, [f, d], lim),
      limit: (n) => query(p, filters, ord, n), get: async () => run(), doc: (id) => doc(p + '/' + (id || rid('d'))),
      onSnapshot: (next) => { const f = () => next(run()); subs.add(f); setTimeout(f, 0); return () => subs.delete(f); },
    };
  };
  return { doc, collection: (p) => query(p) };
}
function anchorDownload(filename, data) {
  const blob = data instanceof Blob ? data : new Blob([data], { type: 'application/octet-stream' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = filename; document.body.append(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1500);
}

/* ================= libraries ================= */
const libCache = {};
function loadScriptFrom(url) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = url; s.async = true;
    s.onload = () => resolve();
    s.onerror = () => { s.remove(); reject(new Error('load failed: ' + url)); };
    document.head.append(s);
  });
}
function lib(name) {
  if (!libCache[name]) {
    libCache[name] = (async () => {
      for (const u of LIBS[name]) { try { await loadScriptFrom(u); return; } catch { /* next mirror */ } }
      throw new Error('Не удалось загрузить библиотеку разбора файлов. Проверьте подключение и попробуйте снова.');
    })();
    libCache[name].catch(() => { delete libCache[name]; });
  }
  return libCache[name];
}

/* ================= parsing ================= */
function decodeText(buf) {
  let t = new TextDecoder('utf-8').decode(buf);
  const bad = t.split(String.fromCharCode(0xFFFD)).length - 1;
  if (bad > 3 && bad > t.length / 500) {
    try { t = new TextDecoder('windows-1251').decode(buf); } catch { /* keep utf-8 */ }
  }
  return t.charCodeAt(0) === 0xFEFF ? t.slice(1) : t;
}
function htmlToText(html) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const out = [];
  const clean = (s) => s.replace(/\s+/g, ' ').trim();
  const walk = (node) => {
    for (const el of node.children) {
      const tag = el.tagName.toLowerCase();
      if (/^h[1-6]$/.test(tag)) { const t = clean(el.textContent); if (t) out.push('#'.repeat(+tag[1]) + ' ' + t); }
      else if (tag === 'p') { const t = clean(el.textContent); if (t) out.push(t); }
      else if (tag === 'ul' || tag === 'ol') {
        out.push([...el.children].map((li, i) => (tag === 'ol' ? `${i + 1}. ` : '- ') + clean(li.textContent)).join('\n'));
      } else if (tag === 'table') {
        out.push([...el.querySelectorAll('tr')].map((tr) => '| ' + [...tr.children].map((td) => clean(td.textContent)).join(' | ') + ' |').join('\n'));
      } else walk(el);
    }
  };
  walk(doc.body);
  return out.join('\n\n');
}
async function parsePdf(buf) {
  await lib('pdf');
  await lib('pdfWorker');
  const pdfjs = window.pdfjsLib;
  if (!pdfjs) throw new Error('Библиотека PDF не загрузилась.');
  const doc = await pdfjs.getDocument({ data: new Uint8Array(buf), isEvalSupported: false, disableFontFace: true }).promise;
  const pages = [];
  for (let p = 1; p <= doc.numPages; p++) {
    const page = await doc.getPage(p);
    const tc = await page.getTextContent();
    let s = '', lastX = null, lastY = null;
    for (const it of tc.items) {
      if (typeof it.str !== 'string') continue;
      const x = it.transform[4], y = it.transform[5];
      if (lastY !== null && Math.abs(y - lastY) > 2 && !s.endsWith('\n')) s += '\n';
      else if (lastX !== null && x - lastX > 1.5 && !/[\s\n]$/.test(s) && !it.str.startsWith(' ')) s += ' ';
      s += it.str;
      lastX = x + (it.width || 0); lastY = y;
      if (it.hasEOL) { s += '\n'; lastX = null; }
    }
    pages.push(`--- Страница ${p} ---\n` + s.replace(/[ \t]+\n/g, '\n').replace(/[ \t]{2,}/g, ' ').trim());
  }
  return { text: pages.join('\n\n'), pages: doc.numPages };
}
async function parseSheet(buf) {
  await lib('xlsx');
  const X = window.XLSX;
  const wb = X.read(buf, { type: 'array' });
  return wb.SheetNames.map((n) => {
    const rows = X.utils.sheet_to_json(wb.Sheets[n], { header: 1, blankrows: false, defval: '', raw: false });
    const lines = rows.map((r) => r.map((c) => String(c).replace(/\s+/g, ' ').trim()))
      .filter((r) => r.some(Boolean)).map((r) => '| ' + r.join(' | ') + ' |');
    return `### Лист «${n}»\n` + lines.join('\n');
  }).join('\n\n');
}
/* OpenAPI / Swagger → текст для анализа: эндпоинты, подходящие под поле «API» (путь, метод, тег, operationId, summary), с параметрами, телом и ответами.
   Дальше документ идёт по тем же правилам, что и обычный текст: анализ, план, генерация, сверка. */
const OPENAPI_MAX_DEPTH = 6;
function openApiToText(spec, filter) {
  const terms = String(filter || '').toLowerCase().split(/[,;\n]/).map((x) => x.trim()).filter(Boolean);
  const ref = (node, depth = 0) => {
    if (!node || typeof node !== 'object' || depth > OPENAPI_MAX_DEPTH) return node || {};
    if (typeof node.$ref === 'string' && node.$ref.startsWith('#/')) {
      const target = node.$ref.slice(2).split('/').reduce((o, k) => (o ? o[k.replace(/~1/g, '/').replace(/~0/g, '~')] : undefined), spec);
      return target ? ref(target, depth + 1) : {};
    }
    return node;
  };
  const typeOf = (s0) => {
    const s = ref(s0);
    if (s.enum) return `${s.type || 'значение'}: ${s.enum.join(' | ')}`;
    if (s.type === 'array') return `массив из ${typeOf(s.items)}`;
    return s.type || (s.properties ? 'объект' : 'значение');
  };
  const props = (schema, indent, depth) => {
    const s = ref(schema), out = [];
    if (depth > OPENAPI_MAX_DEPTH) return out;
    if (s.type === 'array') return [indent + 'элементы массива:', ...props(s.items, indent + '  ', depth + 1)];
    const req = new Set(s.required || []);
    for (const [name, p0] of Object.entries(s.properties || {})) {
      const p = ref(p0);
      const meta = [typeOf(p), req.has(name) ? 'обязательное' : 'необязательное', p.format ? `формат ${p.format}` : '', p.maxLength ? `до ${p.maxLength} символов` : '',
        p.minimum != null ? `от ${p.minimum}` : '', p.maximum != null ? `до ${p.maximum}` : '', p.example !== undefined ? `пример: ${JSON.stringify(p.example)}` : ''].filter(Boolean).join(', ');
      out.push(`${indent}- ${name} (${meta})${p.description ? ' — ' + String(p.description).replace(/\s+/g, ' ') : ''}`);
      if (p.properties || p.type === 'array') out.push(...props(p, indent + '  ', depth + 1));
    }
    return out;
  };
  const where = { path: 'пути', query: 'запросе', header: 'заголовке', cookie: 'cookie' };
  const paramsOf = (op, item) => [...arrOf(item.parameters), ...arrOf(op.parameters)].map(ref).filter((p) => p.in !== 'body' && p.name).map((p) =>
    `- ${p.name} (в ${where[p.in] || p.in}, ${typeOf(p.schema || p)}, ${p.required || p.in === 'path' ? 'обязательный' : 'необязательный'})${p.description ? ' — ' + String(p.description).replace(/\s+/g, ' ') : ''}`);
  const bodyOf = (op, item) => {
    const rb = ref(op.requestBody);
    if (rb.content) return Object.entries(rb.content).flatMap(([mt, c]) => [`Тело запроса (${mt}):`, ...props(c.schema, '  ', 0)]);
    const bp = [...arrOf(item.parameters), ...arrOf(op.parameters)].map(ref).find((p) => p.in === 'body');
    return bp ? ['Тело запроса:', ...props(bp.schema, '  ', 0)] : [];
  };
  const responsesOf = (op) => Object.entries(op.responses || {}).flatMap(([code, r0]) => {
    const r = ref(r0), sch = r.content ? Object.values(r.content)[0]?.schema : r.schema;
    return [`- ${code}${r.description ? ' — ' + String(r.description).replace(/\s+/g, ' ') : ''}`, ...(sch ? props(sch, '  ', 0) : [])];
  });
  const blocks = [];
  for (const [path, item0] of Object.entries(spec.paths || {})) {
    const item = ref(item0);
    for (const m of ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']) {
      const op = item[m];
      if (!op || typeof op !== 'object') continue;
      const hay = `${m} ${path} ${op.operationId || ''} ${arrOf(op.tags).join(' ')} ${op.summary || ''}`.toLowerCase();
      if (terms.length && !terms.some((t) => hay.includes(t))) continue;
      const head = [`## ${m.toUpperCase()} ${path}`];
      const about = [op.summary, op.description].filter(Boolean).join('. ').replace(/\s+/g, ' ').trim();
      if (about) head.push(about);
      const pr = paramsOf(op, item); if (pr.length) head.push('Параметры:', ...pr);
      const bd = bodyOf(op, item); if (bd.length) head.push(...bd);
      const rs = responsesOf(op); if (rs.length) head.push('Ответы:', ...rs);
      blocks.push(head.join('\n'));
    }
  }
  if (!blocks.length) throw new Error(terms.length ? `В спецификации нет эндпоинтов, подходящих под «${String(filter).trim()}»` : 'В спецификации нет эндпоинтов');
  const info = spec.info || {}, base = spec.servers?.[0]?.url || spec.basePath || '';
  return [`# ${info.title || 'API'}${info.version ? ' ' + info.version : ''}`, base ? `Базовый адрес: ${base}` : '', ...blocks].filter(Boolean).join('\n\n');
}
async function parseSpec(ext, buf) {
  const raw = decodeText(buf);
  let spec = null;
  if (ext === 'json') { const p = tryParse(raw); spec = p.ok ? p.value : null; }
  else { await lib('yaml'); try { spec = window.jsyaml.load(raw); } catch (e) { throw new Error('Не удалось разобрать YAML: ' + (e.message || e)); } }
  if (spec && typeof spec === 'object' && (spec.openapi || spec.swagger)) {
    const filter = S.settings.apiFilter || '';
    return { text: openApiToText(spec, filter), warn: filter.trim() ? '' : 'Поле «API» не заполнено — взяты все эндпоинты спецификации' };
  }
  if (ext === 'json' && spec !== null) return { text: raw };   // обычный JSON без OpenAPI — как текст
  throw new Error('Это не спецификация OpenAPI или Swagger: в файле нет поля openapi или swagger');
}
async function parseFile(file) {
  const ext = (file.name.split('.').pop() || '').toLowerCase();
  const buf = await file.arrayBuffer();
  if (['txt', 'md', 'markdown', 'csv'].includes(ext)) return { text: decodeText(buf) };
  if (['json', 'yaml', 'yml'].includes(ext)) return parseSpec(ext === 'yml' ? 'yaml' : ext, buf);
  if (ext === 'docx') {
    await lib('mammoth');
    const r = await window.mammoth.convertToHtml({ arrayBuffer: buf });
    return { text: htmlToText(r.value) };
  }
  if (ext === 'pdf') {
    const r = await parsePdf(buf);
    const warn = r.text.replace(/--- Страница \d+ ---/g, '').trim().length < 40 * r.pages ? 'Мало текста — возможно, это скан без текстового слоя' : '';
    return { text: r.text, warn };
  }
  if (ext === 'xlsx' || ext === 'xls') return { text: await parseSheet(buf) };
  if (ext === 'doc') throw new Error('Формат .doc не поддерживается — сохраните файл как .docx');
  throw new Error('Неподдерживаемый формат: .' + ext);
}
function addFiles(files) {
  const vids = files.filter((f) => /\.mp4$/i.test(f.name));
  if (vids.length) { // видео не загружаем: такие файлы пропускаем
    files = files.filter((f) => !vids.includes(f));
    toast(`Видео не загружаются: ${vids.map((f) => f.name).join(', ')}`, 'err');
  }
  for (const f of files) {
    const ext = (f.name.split('.').pop() || '').toLowerCase();
    const d = { id: rid('d'), pid: S.productId, name: f.name, ext, size: f.size, status: 'parsing', text: '', chars: 0, error: '', warn: '', preview: false, addedAt: Date.now() };
    S.docs.push(d);
    // в генерации и актуализации загруженный документ идёт в запуск (и, как всегда, сохраняется в продукт и базу знаний)
    if (forRun()) S.runDocs.add(d.id);
    parseFile(f).then((r) => {
      d.text = (r.text || '').trim(); d.chars = d.text.length; d.warn = r.warn || '';
      d.status = d.chars ? 'ready' : 'error';
      if (!d.chars) d.error = 'В файле не найден текст';
    }).catch((e) => { d.status = 'error'; d.error = e.message || String(e); })
      .finally(() => {
        if (d.status === 'ready' && S.docs.includes(d)) {
          // тот же файл уже есть в продукте — второй копии не делаем, в запуск берём имеющийся
          const twin = S.docs.find((x) => x !== d && x.pid === d.pid && x.status === 'ready' && x.chars === d.chars && x.text === d.text);
          if (twin) {
            S.docs = S.docs.filter((x) => x !== d);
            const run = S.runDocs.delete(d.id);
            if (run) S.runDocs.add(twin.id);
            toast(`«${d.name}» уже есть в ${d.pid ? 'продукте' : 'списке'}${run ? ' — беру его в запуск' : ''}`);
          } else persistDocText(d);
        } else if (!S.docs.includes(d)) S.runDocs.delete(d.id);
        saveRunDocs(); invalidateIndex(); renderDocs(); renderRunControls(); renderProduct();
      });
  }
  saveRunDocs(); renderDocs(); renderRunControls();
}
const sampleDocObj = () => ({ id: rid('d'), name: 'Пример — ТЗ восстановление пароля.md', ext: 'md', size: SAMPLE_DOC.length * 2, status: 'ready', text: SAMPLE_DOC, chars: SAMPLE_DOC.length, error: '', warn: '', preview: false, sample: true });
function addSampleDoc() {
  if (S.docs.some((d) => d.sample)) return;
  const d = sampleDocObj();
  d.pid = S.productId;
  S.docs.push(d);
  S.runDocs.add(d.id); saveRunDocs();
  invalidateIndex();
  if (S.productId && S.caps.db) { d.persisting = true; addDocMeta(S.productId, d).then(() => { if (S.settings.kbAuto) kbQueue(d); }).finally(() => { d.persisting = false; }); }
}
const readyDocs = () => S.docs.filter((d) => d.status === 'ready');
/* документы запуска. Генерация и актуализация идут по документам, загруженным для этого запуска, а всё остальное
   о продукте агент берёт из базы знаний (сводки разделов по всем документам продукта). Без продукта документы
   живут только в этом окне — все они и есть документы запуска. */
const forRun = () => S.settings.mode !== 'help';
const isRunDoc = (d) => !S.productId || S.runDocs.has(d.id);
const runDocList = () => S.docs.filter(isRunDoc);
function saveRunDocs() { if (S.productId) lsSet('qapro.runDocs.' + S.productId, [...S.runDocs]); }
function setRunDoc(id, on) { if (on) S.runDocs.add(id); else S.runDocs.delete(id); saveRunDocs(); }
/* документы нового запуска — загруженные для него; прошлого — те, на которых он был сделан */
function docsFor(run) {
  const ready = readyDocs();
  if (!run) return ready.filter(isRunDoc);
  if (run.docIds?.length) return ready.filter((d) => run.docIds.includes(d.id));
  const names = new Set((run.docs || []).map((d) => d.name));
  return ready.filter((d) => names.has(d.name));
}

/* ================= актуализация: разбор файла с тест-кейсами (.xlsx, .json) ================= */
const RX_TITLE = /(^|[\s_.-])(title|name|summary|название|наименование|заголовок)([\s_.-]|$)|^(тест[- ]?кейс|test ?case|case)$/i;
const RX_ID = /^(id|ид|№|#|key|ключ|номер|код|external ?id|global ?id|case ?id|test ?case ?id|id ?кейса|id ?тест-кейса|автотест id)$/i;
const RX_STEPISH = /step|шаг|expected|ожида|precond|предусл|result|результат|priority|приоритет|action|действ/i;
const RX_TYPE = /^(type|тип|вид|вид теста|test ?type)$/i;
function typeHintOf(...vals) {
  const s = vals.filter(Boolean).join(' ').toLowerCase();
  if (/(^|[^a-zа-я])e2e|сквозн|end.?to.?end/.test(s)) return 'e2e';
  if (/(^|[^a-zа-я])api([^a-zа-я]|$)|rest|endpoint|эндпоинт/.test(s)) return 'api';
  if (/(^|[^a-zа-я])ui([^a-zа-я]|$)|интерфейс|gui|web|экран/.test(s)) return 'ui';
  return '';
}
function trimRaw(v, depth = 0) {
  if (typeof v === 'string') return v.length > 1500 ? v.slice(0, 1500) + '…' : v;
  if (Array.isArray(v)) return v.slice(0, 60).map((x) => trimRaw(x, depth + 1));
  if (v && typeof v === 'object') { if (depth > 6) return '…'; const o = {}; for (const [k, x] of Object.entries(v)) o[k] = trimRaw(x, depth + 1); return o; }
  return v;
}
function srcCaseFrom(raw, i, hints) {
  const keys = Object.keys(raw);
  const idKey = keys.find((k) => RX_ID.test(k.trim())) || ID_KEYS_SRC.find((k) => k in raw);
  const tKey = keys.find((k) => RX_TITLE.test(k.trim()) && typeof raw[k] === 'string' && raw[k].trim());
  const tyKey = keys.find((k) => RX_TYPE.test(k.trim()));
  const title = tKey ? String(raw[tKey]).trim() : (Object.values(raw).find((x) => typeof x === 'string' && x.length > 8) || `Кейс ${i + 1}`);
  return { index: i + 1, srcId: idKey && raw[idKey] != null ? String(raw[idKey]).trim().slice(0, 60) : '', title: String(title).slice(0, 300), typeHint: typeHintOf(tyKey ? String(raw[tyKey]) : '', ...hints) || '', raw: trimRaw(raw) };
}
const ID_KEYS_SRC = ['id', 'ID', 'Id', 'key', 'caseId', 'testCaseId', 'externalId', 'globalId', 'code'];
function looksLikeCase(o) {
  const ks = Object.keys(o);
  const hasTitle = ks.some((k) => RX_TITLE.test(k));
  const stepish = ks.some((k) => RX_STEPISH.test(k));
  return stepish || (hasTitle && ks.length >= 4);
}
function parseTestsJSON(text) {
  const p = tryParse(text);
  if (!p.ok) throw new Error('Некорректный JSON: ' + p.error);
  const found = [];
  const walk = (v, path, depth) => {
    if (depth > 7 || v == null) return;
    if (Array.isArray(v)) {
      const objs = v.filter((x) => x && typeof x === 'object' && !Array.isArray(x));
      if (objs.length && objs.length >= v.length * 0.8 && objs.filter(looksLikeCase).length >= objs.length * 0.6) { found.push({ path, items: objs }); return; }
      v.forEach((x) => walk(x, path, depth + 1));
      return;
    }
    if (typeof v === 'object') {
      if (depth === 0 && looksLikeCase(v) && Object.keys(v).some((k) => /step|шаг/i.test(k))) { found.push({ path, items: [v] }); return; }
      for (const [k, x] of Object.entries(v)) walk(x, [...path, k], depth + 1);
    }
  };
  walk(p.value, [], 0);
  const cases = [];
  for (const f of found) for (const o of f.items) cases.push(srcCaseFrom(o, cases.length, [f.path.join(' ')]));
  return { cases, note: found.length > 1 ? `разделы: ${found.map((f) => f.path.join('.') || 'корень').join(', ')}` : '' };
}
async function parseTestsSheet(buf) {
  await lib('xlsx');
  const X = window.XLSX;
  const wb = X.read(buf, { type: 'array' });
  const cases = [], sheets = [];
  for (const sn of wb.SheetNames) {
    const rows = X.utils.sheet_to_json(wb.Sheets[sn], { header: 1, blankrows: false, defval: '', raw: false }).map((r) => r.map((c) => String(c ?? '').trim()));
    let h = rows.findIndex((r, i) => i < 15 && r.filter(Boolean).length >= 2 && r.some((c) => RX_TITLE.test(c) || RX_ID.test(c) || RX_STEPISH.test(c)));
    if (h < 0) h = rows.findIndex((r) => r.filter(Boolean).length >= 2);
    if (h < 0) continue;
    const head = rows[h].map((c, i) => c || `Колонка ${i + 1}`);
    const idCol = head.findIndex((c) => RX_ID.test(c)), titleCol = head.findIndex((c) => RX_TITLE.test(c));
    let cur = null, n = 0;
    for (const r of rows.slice(h + 1)) {
      if (!r.some(Boolean)) continue;
      const obj = {};
      head.forEach((k, i) => { if (r[i]) obj[k] = r[i]; });
      const sameCase = cur && idCol >= 0 && r[idCol] && r[idCol] === cur.raw[head[idCol]] && (titleCol < 0 || !r[titleCol] || r[titleCol] === cur.raw[head[titleCol]]);
      const starts = !sameCase && ((titleCol < 0 && idCol < 0) || (titleCol >= 0 && !!r[titleCol]) || (idCol >= 0 && !!r[idCol]));
      if (starts || !cur) { cur = { raw: obj, rows: [] }; cases.push({ cur, sheet: sn }); n++; }
      else cur.rows.push(obj);
    }
    if (n) sheets.push(`«${sn}» — ${n}`);
  }
  const out = cases.map(({ cur, sheet }, i) => srcCaseFrom(cur.rows.length ? { ...cur.raw, 'Следующие строки кейса': cur.rows } : cur.raw, i, [wb.SheetNames.length > 1 ? sheet : '']));
  return { cases: out, note: sheets.length > 1 ? `листы: ${sheets.join(', ')}` : '' };
}
async function setTestsFile(file) {
  const ext = (file.name.split('.').pop() || '').toLowerCase();
  const f = S.upd.file = { name: file.name, ext, size: file.size, status: 'parsing', cases: [], note: '', error: '', preview: false };
  renderUpd(); renderRunControls();
  try {
    if (!['xlsx', 'xls', 'json'].includes(ext)) throw new Error('Нужен файл .xlsx или .json');
    const buf = await file.arrayBuffer();
    const r = ext === 'json' ? parseTestsJSON(decodeText(buf)) : await parseTestsSheet(buf);
    if (!r.cases.length) throw new Error(ext === 'json' ? 'В файле не найдено тест-кейсов: нужен массив объектов с названием, шагами или ожидаемым результатом' : 'В файле не найдено тест-кейсов: нужна строка заголовков (Название, Шаги, Ожидаемый результат…) и строки кейсов');
    if (r.cases.length > 1000) { r.cases = r.cases.slice(0, 1000); r.note = (r.note ? r.note + '; ' : '') + 'взяты первые 1000 кейсов'; }
    f.cases = r.cases; f.note = r.note; f.status = 'ready';
  } catch (e) { f.status = 'error'; f.error = e.message || String(e); }
  if (S.upd.file === f) { renderUpd(); renderRunControls(); if (S.tab === 'agent' && !S.run) renderTab(); }
}

/* ================= search index for agent tools ================= */
let INDEX = null, INDEX_KEY = '';
function invalidateIndex() { INDEX = null; }
const stem = (w) => (w.length > 6 ? w.slice(0, w.length > 9 ? 7 : 5) : w);
const tokens = (s) => (s.toLowerCase().replace(/ё/g, 'е').match(/[a-zа-я0-9_./-]{2,}/g) || []).map(stem);
function buildIndex(docs = readyDocs()) {
  const passages = [];
  for (const d of docs) {
    const paras = d.text.split(/\n{2,}/);
    let buf = '', start = 0, pos = 0;
    for (const p of paras) {
      if (buf && buf.length + p.length > 700) { passages.push({ doc: d.name, offset: start, text: buf }); buf = ''; start = pos; }
      buf += (buf ? '\n\n' : '') + p;
      pos += p.length + 2;
    }
    if (buf) passages.push({ doc: d.name, offset: start, text: buf });
  }
  for (const p of passages) { p.tf = new Map(); for (const t of tokens(p.text)) p.tf.set(t, (p.tf.get(t) || 0) + 1); }
  INDEX = passages; INDEX_KEY = docs.map((d) => d.id).join('|');
}
// индекс по нужным документам (по умолчанию — по всем загруженным); пересобирается, если набор другой
function ensureIndex(docs = readyDocs()) { if (!INDEX || INDEX_KEY !== docs.map((d) => d.id).join('|')) buildIndex(docs); return INDEX; }
// поиск агента — по документам запуска (по умолчанию по всем загруженным)
function searchDocs(query, docs = readyDocs()) {
  ensureIndex(docs);
  const q = [...new Set(tokens(query))];
  if (!q.length) return [];
  return INDEX.map((p) => {
    let score = 0;
    for (const t of q) { const c = p.tf.get(t); if (c) score += 1 + Math.log(c); }
    return { p, score };
  }).filter((x) => x.score > 0).sort((a, b) => b.score - a.score).slice(0, 5)
    .map(({ p }) => ({ document: p.doc, offset: p.offset, text: p.text.slice(0, 700) }));
}
function readDoc(name, offset, length, docs = readyDocs()) {
  const d = docs.find((x) => x.name === name) || docs.find((x) => x.name.toLowerCase().includes(String(name).toLowerCase()));
  if (!d) throw new Error('Документ не найден. Доступные: ' + docs.map((x) => x.name).join(', '));
  const off = Math.max(0, Math.min(d.text.length, Number(offset) || 0));
  const len = Math.max(200, Math.min(3000, Number(length) || 2000));
  return { document: d.name, offset: off, totalLength: d.text.length, text: d.text.slice(off, off + len) };
}
/*__PART2__*/
