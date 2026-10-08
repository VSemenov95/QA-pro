(() => {
  // большой раздел: факты «- Факт ID: …» из выдержек и «- ID: до N, код (источники)» из сжатого материала и прежней сводки
  const merge = (text) => {
    const m = new Map();
    for (const ex of text.matchAll(/<excerpt document="([^"]+)"[^>]*>\n([\s\S]*?)\n<\/excerpt>/g)) {
      const label = ex[1], own = /^(прежняя|сжатый)/.test(label) ? '' : label.replace(/\.[a-z]+$/i, '');
      for (const l of ex[2].split('\n')) {
        let id, v, code, srcs;
        const raw = /^- Факт (\S+): .*?до (\d+) символов, ошибка (\d+)/.exec(l) || /^- Факт (U\S+): (.*)$/.exec(l);
        const cmp = /^- ((?:F|U)\S+): (.*) \(([^)]*)\)$/.exec(l);
        if (raw && own) { id = raw[1]; v = raw[3] ? raw[2] : 'роль'; code = raw[3] || ''; srcs = [own]; }
        else if (cmp) { id = cmp[1]; const d = /до (\d+), (\d+)/.exec(cmp[2]); v = d ? d[1] : 'роль'; code = d ? d[2] : ''; srcs = cmp[3].split(';').map((x) => x.trim()).filter(Boolean); }
        else continue;
        const key = id + '|' + v, e = m.get(key) || { id, v, code, srcs: new Set() };
        srcs.forEach((x) => e.srcs.add(x)); m.set(key, e);
      }
    }
    const byId = new Map();
    for (const e of m.values()) byId.set(e.id, [...(byId.get(e.id) || []), e]);
    const line = (e) => `- ${e.id}: ${e.v === 'роль' ? 'особое поле' : `до ${e.v}, ${e.code}`} (${[...e.srcs].sort().join('; ')})`;
    const conflicts = [...byId.values()].filter((a) => a.length > 1).map((a) => `${a[0].id}: ` + a.map((e) => `${[...e.srcs].sort().join('; ')} — до ${e.v}`).join('; '));
    return { all: [...m.values()].map(line), clean: [...byId.values()].filter((a) => a.length === 1).map((a) => line(a[0])), conflicts };
  };
  window.__mockMerge = merge;
})();
(() => {
  window.__calls = [];
  window.__mockJSON = async (prompt) => {
    window.__calls.push(prompt.slice(0, 70)); (window.__prompts = window.__prompts || []).push(prompt);
    if (prompt.includes('Ты ведёшь «паспорт продукта»') && prompt.includes('Верни только изменения паспорта')) {
      window.__passDelta = (window.__passDelta || 0) + 1;
      return { ops: [{ op: 'add', section: 'Бизнес-правила и ограничения', text: 'Не более 3 запросов на сброс за 15 минут (дельта ' + window.__passDelta + ')' }, { op: 'remove', old: 'Что происходит при 4-м запросе через UI?' }, { op: 'add', section: 'Термины', text: '- Токен сброса — одноразовая ссылка на 30 минут' }] };
    }
    if (prompt.includes('Составь спецификацию преобразования')) {
      return { fileType: 'csv', filename: 'testit-import', mode: 'map', rowMode: 'step', delimiter: ';', notes: 'CSV для Test IT, шаг на строку.',
        cols: [{ header: 'ID', value: '{{id}}', firstOnly: true }, { header: 'Название', value: '{{title}}', firstOnly: true }, { header: 'Предусловия', value: '{{preconditions|; }}', firstOnly: true }, { header: 'Шаг', value: '{{step.n}}. {{step.action}}' }, { header: 'Ожидаемый результат', value: '{{step.expected}}' }, { header: 'Приоритет', value: '{{priority=high:Высокий,medium:Средний,low:Низкий}}', firstOnly: true }, { header: 'Теги', value: '{{suites|, }}', firstOnly: true }],
        itemRules: 'по шаблону' };
    }
    if (prompt.includes('Ты ведёшь «паспорт продукта»')) {
      const prev = (prompt.split('## Текущий паспорт\n')[1] || '').split('\n')[0];
      const n = (window.__passN = (window.__passN || 0) + 1);
      if (window.__bigPassport) return { passport: Array.from({length: 9}, (_, k) => `## Раздел ${k + 1}\n` + Array.from({length: 12}, (_, j) => `- Факт ${k}.${j}: экран «Профиль клиента», роль Оператор, поле Email до 254 символов, ответ 202/400/429`).join('\n')).join('\n\n') };
      return { passport: `## Назначение и границы\n- Восстановление пароля в личном кабинете (ТЗ v1.3)\n- Версия знаний ${n}${prev.startsWith('Пока пуст') ? '' : ', дополнено'}\n\n## Экраны и навигация\n- **Восстановление пароля**: /login → ссылка «Забыли пароль?»\n- Экран «Новый пароль» — по ссылке из письма\n\n## API и интеграции\n- \`POST /api/v1/password-reset\` — 202 / 400 INVALID_EMAIL / 429 RATE_LIMIT\n\n## Открытые вопросы\n1. Что происходит при 4-м запросе через UI?` };
    }
    if (prompt.includes('Сопоставь каждый существующий тест-кейс')) {
      const blocks = prompt.split(/\n### #/).slice(1).map((b) => ({ i: Number(b.match(/^(\d+)/)[1]), t: b.split('\n```\n')[0] }));
      return { cases: blocks.map(({ i, t }) => {
        const type = /POST|api/i.test(t) ? 'api' : /Сквозн|e2e/i.test(t) ? 'e2e' : 'ui';
        const st = /SMS/.test(t) ? 'obsolete' : /Неверный email/.test(t) ? 'changed' : 'same';
        return { index: i, type, requirementIds: type === 'api' ? ['R-002'] : type === 'e2e' ? ['R-003'] : ['R-001'], status: st, reason: st === 'obsolete' ? 'Восстановления по SMS в ТЗ v1.3 нет' : st === 'changed' ? 'п. 2.3: текст ошибки другой' : 'Соответствует ТЗ', instruction: st === 'changed' ? 'Ожидаемый результат: «Неверный email» → «Введите корректный email»' : '' };
      }) };
    }
    if (prompt.includes('Перепиши существующие тест-кейсы')) {
      const blocks = prompt.split(/\n### #/).slice(1).map((b) => ({ i: Number(b.match(/^(\d+)/)[1]), changed: /Статус: "changed"/.test(b) }));
      return { cases: blocks.map(({ i, changed }) => ({ index: i, suites: ['regression'], changes: changed ? ['Ожидаемый результат: «Неверный email» → «Введите корректный email»'] : [], testCase: { id: '', title: 'Актуализированный кейс #' + i, priority: 'High', preconditions: ['Открыта /login'], steps: [{ step: 1, action: 'Действие', expected: changed ? 'Введите корректный email' : 'Результат' }], expectedResult: 'ok', tags: ['upd'] } })) };
    }
    if (prompt.includes('Раздели фрагмент документа на функциональные разделы')) {
      const name = (prompt.match(/## Фрагмент документа «([^»]+)»/) || [])[1] || '';
      if (/big\d+/i.test(name)) {
        if (!/часть 1 из/.test(prompt)) return { blocks: [] };
        const k = Number(name.match(/big(\d+)/i)[1]);
        const gen = (prompt.match(/\n- (kb[a-z0-9]+) · Общие сведения/) || [])[1];
        const SUBS = ['Описание', 'Поля и элементы', 'Бизнес-правила и ограничения', 'Сообщения и ошибки'];
        const lines = (si) => {
          const out = [];
          for (let j = 0; j < 20; j++) { const v = si === 2 && j === 7 && k === 11 ? 5 : 10 * (j + 1); out.push(`- Факт F${si}-${j}: поле «Поле ${j}» на экране «Профиль клиента» — до ${v} символов, ошибка 4${j % 10}0 «Проверьте поле ${j}»`); }
          for (let j = 0; j < 2; j++) out.push(`- Факт U${k}-${si}-${j}: поле «Особое ${j}» видно только роли «Оператор ${k}» и сохраняется кнопкой «Сохранить»`);
          return out.join('\n');
        };
        return { blocks: [{ blockId: gen || null, title: 'Общие сведения', summary: 'Общие сведения о системе', sections: ['1'], content: SUBS.map((s, si) => `### ${s}\n${lines(si)}`).join('\n') }] };
      }
      const known = [...prompt.matchAll(/\n- (kb[a-z0-9]+) · ([^\n—]+?)(?: — |\n)/g)].map((m) => ({ id: m[1], title: m[2].trim() }));
      const reset = known.find((k) => /Восстановление пароля/.test(k.title));
      if (/extra|лимит/i.test(name)) return { blocks: [{ blockId: reset ? reset.id : null, title: 'Восстановление пароля', summary: 'x', sections: ['Лимиты'], content: '### Бизнес-правила и ограничения\n- Не более 3 запросов за 15 минут (из доп. документа)' }] };
      if (/созвон|call/i.test(name)) return { blocks: [{ blockId: reset ? reset.id : null, title: 'Восстановление пароля', summary: 'x', sections: ['созвон'], content: '### Бизнес-правила и ограничения\n- Не более 5 запросов за 15 минут (со слов аналитика)\n### Сообщения и ошибки\n- «Слишком много попыток. Повторите через 30 минут»' }] };
      return { blocks: [
        { blockId: null, title: 'Восстановление пароля', summary: 'Сброс пароля по ссылке из письма.', sections: ['2', '4'], content: '### Описание\n- Пользователь восстанавливает доступ по ссылке из письма\n### Экраны и навигация\n- /login → «Забыли пароль?» → экран «Восстановление пароля»\n### Сообщения и ошибки\n- «Введите корректный email»' },
        { blockId: null, title: 'API сброса пароля', summary: 'Эндпоинты запроса и подтверждения сброса.', sections: ['3.1', '3.2'], content: '### API и интеграции\n- `POST /api/v1/password-reset` — 202 / 400 INVALID_EMAIL / 429 RATE_LIMIT\n- `POST /api/v1/password-reset/confirm` — 200 / 400 WEAK_PASSWORD / 410 TOKEN_EXPIRED' },
      ] };
    }
    if (prompt.includes('справочная служба QA-команды')) {
      const q = (prompt.split('## Вопрос\n')[1] || '').split('\n')[0];
      const k = (prompt.match(/\n\[(K\d+)\]/) || [])[1], d = (prompt.match(/\n\[(D\d+)\]/) || [])[1];
      if (/оплат/i.test(q)) return { status: 'not_found', answer: 'В базе знаний нет сведений об оплате картой.', sources: [], missing: 'Описание оплаты' };
      const bb = (prompt.match(/\n\[(B\d+)\]/) || [])[1];
      if (/лимит|огранич/i.test(q)) return { status: 'answered', answer: '- Не более **3 запросов** на сброс за 15 минут\n- Ссылка действует 30 минут', sources: [bb, d || k, 'UI-001', 'X-999'].filter(Boolean), missing: '' };
      return { status: 'partial', answer: 'Известно только про экран «Восстановление пароля».', sources: [k].filter(Boolean), missing: 'Нет описания ролей' };
    }
    if (prompt.includes('Проверь полноту')) {
      window.__moreCalls = (window.__moreCalls || 0) + 1;
      if (!window.__covMock) return { requirements: [], criteria: [] };
      return { requirements: [{ title: 'Блокировка после 5 неудачных попыток', description: 'После 5 неверных паролей вход блокируется на 30 минут', types: ['ui', 'api'], priority: 'high', doc: 'Пример', section: '4', quote: 'блокируется', criteria: ['6-я попытка — сообщение «Вход заблокирован на 30 минут»'] }, { title: 'Ссылка «Забыли пароль?»', description: 'дубль' }],
        criteria: [{ title: 'Ссылка «Забыли пароль?»', add: ['Ссылка ведёт на /password-reset'] }] };
    }
    if (prompt.includes('Проверь, что тест-кейсы покрывают каждое требование целиком')) {
      window.__auditCalls = (window.__auditCalls || 0) + 1;
      if (!window.__covMock) return { gaps: [] };
      const ids = [...prompt.matchAll(/### (R-\d+) /g)].map((m) => m[1]);
      return { gaps: ids.includes('R-001') ? [{ requirementId: 'R-001', type: 'ui', checks: ['Ссылка ведёт на /password-reset', 'Проверить запись в таблице users напрямую в БД'] }] : [] };
    }
    if (prompt.includes('Выдели из проектной документации')) return { requirements: [
      { title: 'Ссылка «Забыли пароль?»', description: 'На /login есть ссылка', types: ['ui'], priority: 'high', doc: 'Пример', section: '2.1', quote: 'отображается ссылка', criteria: ['Ссылка видна под полем пароля'] },
      { title: 'API запроса сброса', description: 'POST /api/v1/password-reset', types: ['api'], priority: 'high', doc: 'Пример', section: '3.1', quote: 'POST', criteria: ['202 для корректного email', '400 INVALID_EMAIL'] },
      { title: 'Сквозное восстановление', description: 'Полный путь', types: ['e2e'], priority: 'high', doc: 'Пример', section: '5', quote: '', criteria: [] },
      { title: 'Лимит запросов', types: ['api', 'ui'], priority: 'medium', criteria: ['3 запроса за 15 минут'] },
    ], questions: ['Что происходит при 4-м запросе через UI?'] };
    if (prompt.includes('Составь чек-лист') && window.__scopeMock) return { groups: [{ title: 'Смешанное', items: [
      { check: 'Ссылка «Забыли пароль?» видна', type: 'ui', priority: 'high', suites: ['smoke'], requirementIds: ['R-001'] },
      { check: 'В выпадающем списке SELECT «Роль» есть «Оператор»', type: 'ui', priority: 'low', suites: ['regression'], requirementIds: ['R-001'] },
      { check: 'После сброса SELECT * FROM users показывает новый хэш', type: 'api', priority: 'medium', suites: ['regression'], requirementIds: ['R-002'] },
      { check: 'Исследовательское тестирование формы восстановления', type: 'ui', priority: 'low', suites: ['regression'], requirementIds: ['R-001'] }] }] };
    if (prompt.includes('Составь чек-лист')) return { groups: [
      { title: 'Форма восстановления', items: [{ check: 'Ссылка «Забыли пароль?» видна под полем пароля', type: 'ui', priority: 'high', suites: ['smoke', 'regression'], requirementIds: ['R-001'] }, { check: 'Email без @ — сообщение «Введите корректный email»', type: 'ui', priority: 'medium', suites: ['regression'], requirementIds: ['R-001'] }] },
      { title: 'API сброса', items: [{ check: 'POST /api/v1/password-reset с корректным email — 202', type: 'api', priority: 'high', suites: ['smoke', 'regression'], requirementIds: ['R-002'] }, { check: 'Четвёртый запрос за 15 минут — 429 RATE_LIMIT', type: 'api', priority: 'medium', suites: ['regression'], requirementIds: ['R-004'] }] }] };
    if (prompt.includes('Составь план') && prompt.includes('## Уже есть в продукте')) {
      const e2e = (prompt.match(/- (E2E-\d+) \[e2e\]/) || [])[1];
      return { items: [
        { type: 'ui', title: 'Форма — новые проверки', requirementIds: ['R-001'], checks: ['Кнопка неактивна при пустом поле'] },
        { type: 'api', title: 'API — новые проверки', requirementIds: ['R-002'], checks: ['429 на четвёртый запрос'] },
      ], alreadyCovered: e2e ? [{ requirementId: 'R-003', caseIds: [e2e] }, { requirementId: 'R-004', caseIds: ['NOPE-1'] }] : [] };
    }
    if (prompt.includes('Составь план') && window.__scopeMock) return { items: [
      { type: 'api', title: 'API', requirementIds: ['R-002'], checks: ['202 для корректного email', 'DELETE /api/v1/password-reset/1 — 405', 'Выполнить INSERT INTO users и проверить ответ', 'Проверить запись в БД после запроса'] },
      { type: 'ui', title: 'Исследовательское тестирование формы', requirementIds: ['R-001'], checks: ['Свободное исследование формы'] },
      { type: 'ui', title: 'Форма', requirementIds: ['R-001'], checks: ['Ссылка видна', 'Исследовательская проверка на усмотрение тестировщика'] },
    ] };
    if (prompt.includes('Составь план')) return { items: [
      { type: 'ui', title: 'Форма', requirementIds: ['R-001'], checks: ['Ссылка видна', 'Переход на экран'] },
      { type: 'api', title: 'API', requirementIds: ['R-002'], checks: ['202', '400'] },
      { type: 'e2e', title: 'E2E', requirementIds: ['R-003', 'R-002'], checks: ['Полный путь'] },
    ] };
    if (prompt.includes('Напиши тест-кейсы') && (window.__genMax || window.__genFail)) {
      // имитация обрезанного ответа: проверок больше, чем «помещается», или конкретная проверка всегда обрывается
      const cover = (prompt.split('## Что покрыть')[1] || '').split('\n## ')[0];
      const checks = [...cover.matchAll(/^\d+\. (.+)$/gm)].map((m) => m[1]);
      (window.__genLog = window.__genLog || []).push(checks.length);
      if ((window.__genMax && checks.length > window.__genMax) || (window.__genFail && checks.some((c) => c.includes(window.__genFail)))) throw { code: 'invalid_json', message: 'Модель ответила не в формате JSON.' };
      const pi = (cover.match(/### ([A-Z]+-\d+)\./) || [])[1];
      return { cases: checks.map((c) => ({ planItem: pi, requirementIds: [], suites: ['regression'], testCase: { title: 'Кейс: ' + c, id: '', priority: 'High', preconditions: ['—'], steps: [{ step: 1, action: c, expected: 'ok' }], expectedResult: 'ok', tags: ['t'] } })) };
    }
    if (prompt.includes('Напиши тест-кейсы')) {
      const items = [...prompt.matchAll(/### ([A-Z]+-\d+)\./g)].map((m) => m[1]);
      if (window.__mockHtml) return { cases: items.map((id) => ({ planItem: id, requirementIds: [], suites: ['regression'], testCase: { title: 'Кейс ' + id, id: '', priority: 'High', preconditions: ['<p>Пользователь&nbsp;зарегистрирован</p>'], steps: [{ step: 1, action: '<p>Открыть /login</p><p>Ввести &lt;email&gt;</p>', expected: '<ul><li>Открыта страница</li><li>Поле <b>Email</b></li></ul>' }], expectedResult: '<p>ok<br>готово</p>', tags: ['t'] } })) };
      return { cases: items.map((id, k) => ({ planItem: id, requirementIds: [], suites: k === 0 ? ['smoke', 'regression'] : ['regression'], testCase: { title: 'Кейс для ' + id + ': проверка восстановления пароля', id: '', priority: 'High', preconditions: ['Пользователь зарегистрирован'], steps: [{ step: 1, action: 'Открыть /login', expected: 'Открыта страница' }, { step: 2, action: 'Нажать «Забыли пароль?»', expected: 'Открыт экран' }], expectedResult: 'ok', tags: ['t'] } })) };
    }
    if (prompt.includes('строгий ревьюер')) {
      const id = (prompt.match(/"id": "([A-Z0-9-]+)"/) || prompt.match(/(CL-\d+)/) || [])[1];
      return { findings: id ? [{ targetId: id, severity: id.startsWith('CL') ? 'minor' : 'critical', category: 'Соответствие ТЗ', message: 'Ожидаемый результат не совпадает с п. 3.1: должен быть код 202.', suggestion: 'Указать код 202 и тело {"status":"sent"}.' }] : [] };
    }
    if (prompt.includes('базу правил')) return { rule: 'В ожидаемом результате API-кейсов всегда указывай код ответа и ключевые поля тела', scope: 'both' };
    if (prompt.includes('Доработай пункт чек-листа')) return { check: 'Исправленный пункт с конкретным лимитом 3 запроса', priority: 'high', suites: ['regression'] };
    if (prompt.includes('Аналитик ответил')) return { criteria: [{ requirementId: 'R-004', add: ['На 4-й запрос UI показывает таймер'] }], update: [], add: [], checklistUpdate: [] };
    if (prompt.includes('Доработай тест-кейс')) return { id: 'X', title: 'Доработанный кейс', priority: 'Low', steps: [{ step: 1, action: 'a', expected: 'b' }] };
    if (prompt.includes('Исправь тест-кейсы')) return { cases: [] };
    if (prompt.includes('Проверка связи')) return { ok: true, model: 'mock' };
    if (prompt.includes('Сожми материал подраздела')) {
      window.__condCalls = (window.__condCalls || 0) + 1;
      if (window.__synthMode === 'limit') throw { code: 'rate_limited', message: '' };
      return { text: window.__mockMerge(prompt.split('## Материал подраздела')[1].split('\n## Правила')[0]).all.join('\n') };
    }
    if (prompt.includes('Раздел «') && prompt.includes('Собери часть')) {
      window.__partCalls = (window.__partCalls || 0) + 1;
      if (window.__synthMode === 'limit') throw { code: 'rate_limited', message: '' };
      const mat = prompt.split('\n## Материал\n')[1].split(/\n## (?:Расхождения из прежней сводки|Другие разделы)/)[0];
      const prevConf = ((prompt.split('\n## Расхождения из прежней сводки\n')[1] || '').split('\n## ')[0]).split('\n').filter((l) => l.startsWith('- ')).map((l) => l.slice(2));
      const out = [], conflicts = [];
      for (const sc of mat.split(/^### /m).slice(1)) { const sub = sc.split('\n')[0].trim(), r = window.__mockMerge(sc); out.push(`### ${sub}\n${r.clean.join('\n')}`); conflicts.push(...r.conflicts); }
      for (const c of prevConf) if (!conflicts.some((x) => x.split(':')[0] === c.split(':')[0])) conflicts.push(c);
      return { summary: 'Общие сведения о системе: поля, правила и сообщения', synth: out.join('\n'), conflicts, links: [] };
    }
    if (prompt.includes('Собери единую сводку раздела')) {
      if (window.__synthMode === 'limit') throw { code: 'rate_limited', message: '' };
      if (window.__synthMode === 'trunc' && !/не больше 3000 знаков/.test(prompt)) { window.__synthTrunc = (window.__synthTrunc || 0) + 1; throw { code: 'invalid_json', message: 'Модель ответила не в формате JSON.' }; }
      const title = (prompt.match(/сводку раздела «([^»]+)»/) || [])[1] || '';
      const ex = [...prompt.matchAll(/<excerpt document="([^"]+)"[^>]*>\n([\s\S]*?)\n<\/excerpt>/g)].map((m) => ({ doc: m[1].replace(/\.[a-z]+$/i, ''), md: m[2] }));
      const facts = [];
      for (const e of ex) for (const l of e.md.split('\n')) if (/^- /.test(l) && !/5 запросов|3 запросов/.test(l)) facts.push(`${l} (${e.doc})`);
      const three = ex.find((e) => /3 запросов/.test(e.md)), five = ex.find((e) => /5 запросов/.test(e.md));
      const conflicts = three && five ? [`Лимит запросов на сброс: ${three.doc} — не более 3 за 15 минут; ${five.doc} — не более 5 за 15 минут`] : [];
      if (three && !five) facts.push(`- Не более 3 запросов за 15 минут (${three.doc})`);
      if (five && !three) facts.push(`- Не более 5 запросов за 15 минут (${five.doc})`);
      const others = [...prompt.matchAll(/\n- (kb[a-z0-9]+) · ([^\n]+)/g)].map((m) => ({ id: m[1], title: m[2] }));
      const link = others.find((o) => /API/.test(o.title) && /Восстановление/.test(title)) || others.find((o) => /Восстановление/.test(o.title) && /API/.test(title));
      window.__synthCalls = (window.__synthCalls || 0) + 1;
      return { summary: 'Сводка: ' + title, synth: '### Описание\n' + facts.join('\n') + (conflicts.length ? '\n### Расхождения между документами\n- ' + conflicts.join('\n- ') : ''), conflicts, links: link ? [link.id] : [] };
    }
    if (prompt.includes('Ты помогаешь найти ответ в базе знаний продукта')) {
      const q = (prompt.split('## Вопрос\n')[1] || '').split('\n')[0];
      const secs = [...prompt.matchAll(/\n- (kb[a-z0-9]+) · ([^\n—]+)/g)].map((m) => ({ id: m[1], title: m[2].trim() }));
      window.__expandCalls = (window.__expandCalls || 0) + 1;
      const pick = /помни|доступ|забыл/i.test(q) ? secs.filter((x) => /Восстановление/.test(x.title)).map((x) => x.id) : [];
      return { sections: pick, terms: pick.length ? ['восстановление пароля', 'сброс пароля', 'Забыли пароль?', 'password reset'] : [] };
    }
    if (prompt.includes('Ты помогаешь QA-команде разобрать видео')) {
      const n = [...prompt.matchAll(/кадр (\d+) — \[([\d:]+)\]/g)];
      return { frames: n.map((m, k) => ({ n: Number(m[1]), skip: k === 1, screen: 'Экран в ' + m[2], details: 'Мок-описание кадра ' + m[1] })) };
    }
    if (prompt.includes('Ты — аналитик QA-команды. Это')) return { summary: 'Созвон о восстановлении пароля.', points: ['Показали вход и восстановление пароля'], requirements: ['После трёх неудачных попыток вход блокируется на 30 минут'], decisions: [], questions: ['Сколько живёт ссылка восстановления?'] };
    return {};
  };
})();
