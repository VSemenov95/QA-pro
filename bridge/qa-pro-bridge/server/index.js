#!/usr/bin/env node
// QA pro — локальный мост между приложением Claude и загрузчиком в Сферу ФТ (расширение Chrome).
//
// Этот файл — MCP-сервер (stdio), который запускает приложение Claude. Сам он лёгкий: вся работа — в ядре
// (core.js), которое живёт отдельным фоновым процессом и поэтому не останавливается, когда приложение
// закрывают. Обёртка находит ядро, при необходимости запускает или обновляет его и передаёт ему вызовы.
// Если отдельный процесс запустить нельзя, ядро работает внутри обёртки (как в версии 1.0).
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const core = require('./core.js');

const VERSION = core.VERSION;
const PORT = core.PORT;
const log = (...a) => process.stderr.write('[qa-pro-bridge] ' + a.join(' ') + '\n');
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ---------------- связь с ядром ---------------- */
function request(method, urlPath, body, { timeout = 3000, token = '' } = {}) {
  return new Promise((resolve, reject) => {
    const data = body === undefined ? null : Buffer.from(JSON.stringify(body));
    const req = http.request({ host: '127.0.0.1', port: PORT, method, path: urlPath, timeout,
      headers: { ...(data ? { 'Content-Type': 'application/json', 'Content-Length': data.length } : {}), ...(token ? { 'x-qa-pro-bridge-token': token } : {}) } }, (res) => {
      let s = ''; res.setEncoding('utf8');
      res.on('data', (c) => { s += c; });
      res.on('end', () => { try { resolve({ status: res.statusCode, json: JSON.parse(s || '{}') }); } catch { resolve({ status: res.statusCode, json: null }); } });
    });
    req.on('timeout', () => req.destroy(new Error('timeout')));
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}
const health = () => request('GET', '/health', undefined, { timeout: 800 }).then((r) => (r.json?.name === 'qa-pro-bridge' ? r.json : { foreign: true })).catch(() => null);
const readToken = () => { try { return fs.readFileSync(path.join(core.DIR, 'token'), 'utf8').trim(); } catch { return ''; } };

let mode = null, local = null, starting = null;
async function ensureCore() {
  if (starting) return starting;
  starting = (async () => {
    let h = await health();
    if (h && !h.foreign && h.version !== VERSION && h.mode === 'standalone') {
      log('обновляю фоновое ядро', h.version, '→', VERSION);
      await request('POST', '/shutdown', {}, { token: readToken() }).catch(() => {});
      for (let i = 0; i < 20 && (await health()); i++) await sleep(150);
      h = null;
    }
    if (h && !h.foreign && h.version === VERSION) { mode = 'remote'; return mode; }
    if (h && (h.foreign || h.mode !== 'standalone')) { mode = 'busy'; return mode; } // порт занят чужой программой
    try {
      const child = spawn(process.execPath, [path.join(__dirname, 'core.js')], { detached: true, stdio: 'ignore', windowsHide: true, env: { ...process.env, QA_PRO_BRIDGE_PORT: String(PORT), NODE_USE_ENV_PROXY: '1' } }); // прокси из системы — для скачивания распознавателя и модели
      child.on('error', (e) => log('фоновое ядро не запустилось:', e.message));
      child.unref();
      for (let i = 0; i < 40; i++) { await sleep(100); const h2 = await health(); if (h2 && !h2.foreign && h2.version === VERSION) { mode = 'remote'; log('фоновое ядро запущено, pid', h2.pid); return mode; } }
    } catch (e) { log('фоновое ядро не запустилось:', e.message); }
    log('работаю внутри приложения: мост остановится вместе с ним');
    local = core.start({ mode: 'inprocess' });
    const r = await local.ready;
    mode = r.ok ? 'local' : 'busy';
    return mode;
  })().finally(() => { starting = null; });
  return starting;
}
async function coreCall(tool, args) {
  if (!mode || mode === 'busy') await ensureCore();
  if (mode === 'local') return local.callTool(tool, args);
  if (mode === 'busy') throw new Error(`Порт ${PORT} занят другой программой. Укажите другой порт в настройках расширения «QA pro — мост» в приложении Claude и тот же порт в настройках загрузчика.`);
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const r = await request('POST', '/rpc', { tool, args }, { token: readToken(), timeout: 30000 });
      if (r.status === 403) throw Object.assign(new Error('Фоновое ядро моста не приняло секрет — перезапустите приложение Claude.'), { fatal: true });
      if (!r.json) throw new Error('Ядро моста ответило непонятно.');
      if (!r.json.ok) throw Object.assign(new Error(r.json.error || 'Ошибка моста'), { fatal: true });
      return r.json.result;
    } catch (e) {
      if (e.fatal || attempt) throw e;
      mode = null; await ensureCore(); // ядро могли закрыть — поднимаем заново
      if (mode === 'local') return local.callTool(tool, args);
    }
  }
}
// Пока приложение Claude открыто, напоминаем ядру о себе: без приложения оно само завершится через трое суток.
setInterval(() => { if (mode === 'remote') coreCall('ping', {}).catch(() => {}); }, 300e3).unref();

/* ---------------- инструменты MCP ---------------- */
const CASE_SCHEMA = {
  type: 'object',
  properties: {
    ref: { type: ['string', 'null'] }, qaId: { type: 'string' }, name: { type: 'string' }, description: { type: 'string' },
    preConditions: { type: 'array' }, steps: { type: 'array' }, postConditions: { type: 'array' },
    priority: { type: 'string' }, suites: { type: 'array', items: { type: 'string' } },
  },
  required: ['name'],
};
const TOOLS = [
  {
    name: 'ping', title: 'Состояние моста',
    description: 'Проверить мост QA pro: работает ли он и подключён ли загрузчик в Сферу ФТ из Chrome.',
    inputSchema: { type: 'object', properties: {}, additionalProperties: false },
    annotations: { title: 'Состояние моста', readOnlyHint: true, openWorldHint: false },
  },
  {
    name: 'sfera_upload', title: 'Передать тест-кейсы загрузчику',
    description: 'Передать тест-кейсы QA pro загрузчику в Chrome. Загрузчик откроет своё окно: там пользователь выбирает раздел Сферы ФТ и подтверждает загрузку. Возвращает номер задания.',
    inputSchema: {
      type: 'object',
      properties: { title: { type: 'string', description: 'Откуда кейсы — показывается в окне загрузчика' }, cases: { type: 'array', items: CASE_SCHEMA, minItems: 1, maxItems: 2000 } },
      required: ['cases'], additionalProperties: false,
    },
    annotations: { title: 'Передать тест-кейсы загрузчику', readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: false },
  },
  {
    name: 'sfera_job', title: 'Состояние задания',
    description: 'Состояние задания на загрузку: queued (загрузчик не подключён), sent, opened (окно открыто), done (с результатами по кейсам), cancelled, error. С waitMs ждёт изменения до 25 секунд.',
    inputSchema: {
      type: 'object',
      properties: { jobId: { type: 'string' }, since: { type: 'number', description: 'updatedAt из прошлого ответа' }, waitMs: { type: 'number', minimum: 0, maximum: 25000 } },
      required: ['jobId'], additionalProperties: false,
    },
    annotations: { title: 'Состояние задания', readOnlyHint: true, openWorldHint: false },
  },
  {
    name: 'sfera_cancel', title: 'Отменить задание',
    description: 'Отменить задание на загрузку: если окно загрузчика уже открыто, оно закроется без загрузки.',
    inputSchema: { type: 'object', properties: { jobId: { type: 'string' } }, required: ['jobId'], additionalProperties: false },
    annotations: { title: 'Отменить задание', readOnlyHint: false, destructiveHint: false, idempotentHint: true, openWorldHint: false },
  },
  {
    name: 'sfera_call', title: 'Операция Сферы через загрузчик',
    description: 'Выполнить операцию API Сферы через загрузчик в Chrome под входом пользователя: tasks.search, tasks.create, tasks.get, tasks.attach, tasks.link (Сфера.Задачи), repo.branches, repo.tree, repo.file, repo.branch, repo.commit, repo.mr (репозиторий). Адреса операций задаются в настройках загрузчика.',
    inputSchema: {
      type: 'object',
      properties: { op: { type: 'string' }, args: { type: 'object' }, timeoutMs: { type: 'number', minimum: 1000, maximum: 25000 } },
      required: ['op'], additionalProperties: false,
    },
    annotations: { title: 'Операция Сферы через загрузчик', readOnlyHint: false, destructiveHint: false, idempotentHint: false, openWorldHint: true },
  },
  {
    name: 'project_list', title: 'Файлы репозитория автотестов',
    description: 'Список текстовых файлов локального репозитория автотестов (без .git, build, target, node_modules).',
    inputSchema: { type: 'object', properties: { root: { type: 'string', description: 'Полный путь к папке репозитория' }, max: { type: 'number' } }, required: ['root'], additionalProperties: false },
    annotations: { title: 'Файлы репозитория автотестов', readOnlyHint: true, openWorldHint: false },
  },
  {
    name: 'project_read', title: 'Прочитать файлы репозитория',
    description: 'Прочитать текстовые файлы локального репозитория автотестов (до 300 КБ на файл).',
    inputSchema: { type: 'object', properties: { root: { type: 'string' }, paths: { type: 'array', items: { type: 'string' }, maxItems: 400 } }, required: ['root', 'paths'], additionalProperties: false },
    annotations: { title: 'Прочитать файлы репозитория', readOnlyHint: true, openWorldHint: false },
  },
  {
    name: 'project_write', title: 'Записать автотесты в репозиторий',
    description: 'Записать сгенерированные автотесты в локальный репозиторий: создать или перезаписать файлы внутри папки репозитория. Коммит и пуш делает пользователь.',
    inputSchema: {
      type: 'object',
      properties: { root: { type: 'string' }, files: { type: 'array', maxItems: 100, items: { type: 'object', properties: { path: { type: 'string' }, content: { type: 'string' } }, required: ['path', 'content'] } } },
      required: ['root', 'files'], additionalProperties: false,
    },
    annotations: { title: 'Записать автотесты в репозиторий', readOnlyHint: false, destructiveHint: true, idempotentHint: true, openWorldHint: false },
  },
];
async function callTool(name, args) {
  try {
    const payload = await coreCall(name, args);
    if (name === 'ping') payload.core = mode === 'remote' ? 'background' : mode === 'local' ? 'app' : 'none';
    return { content: [{ type: 'text', text: JSON.stringify(payload) }], structuredContent: payload };
  } catch (e) {
    return { isError: true, content: [{ type: 'text', text: String(e?.message || e) }] };
  }
}

/* ---------------- MCP по stdio (JSON-RPC 2.0, по сообщению в строке) ---------------- */
const send = (msg) => process.stdout.write(JSON.stringify(msg) + '\n');
async function handle(msg) {
  if (!msg || typeof msg !== 'object') return;
  const { id, method, params } = msg;
  if (id === undefined || id === null) return; // уведомления ответа не требуют
  try {
    switch (method) {
      case 'initialize':
        return send({ jsonrpc: '2.0', id, result: {
          protocolVersion: params?.protocolVersion || '2025-06-18',
          capabilities: { tools: { listChanged: false } },
          serverInfo: { name: 'qa-pro-bridge', title: 'QA pro — мост к загрузчику Сферы ФТ', version: VERSION },
          instructions: 'Мост для страницы QA pro: передаёт тест-кейсы загрузчику в Сферу ФТ (расширение Chrome) и возвращает результат.',
        } });
      case 'ping': return send({ jsonrpc: '2.0', id, result: {} });
      case 'tools/list': return send({ jsonrpc: '2.0', id, result: { tools: TOOLS } });
      case 'tools/call': return send({ jsonrpc: '2.0', id, result: await callTool(params?.name, params?.arguments || {}) });
      case 'resources/list': return send({ jsonrpc: '2.0', id, result: { resources: [] } });
      case 'prompts/list': return send({ jsonrpc: '2.0', id, result: { prompts: [] } });
      default: return send({ jsonrpc: '2.0', id, error: { code: -32601, message: 'Method not found: ' + method } });
    }
  } catch (e) {
    send({ jsonrpc: '2.0', id, error: { code: -32603, message: String(e?.message || e) } });
  }
}
let inbuf = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => {
  inbuf += chunk;
  let i;
  while ((i = inbuf.indexOf('\n')) >= 0) {
    const line = inbuf.slice(0, i).trim();
    inbuf = inbuf.slice(i + 1);
    if (!line) continue;
    let msg;
    try { msg = JSON.parse(line); } catch { send({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } }); continue; }
    if (Array.isArray(msg)) msg.forEach(handle); else handle(msg);
  }
});
// Приложение закрыли: обёртка завершается, фоновое ядро продолжает работать.
process.stdin.on('end', () => process.exit(0));
process.on('uncaughtException', (e) => log('ошибка:', e?.stack || e));
ensureCore().then((m) => log('режим ядра:', m)).catch((e) => log('ядро:', e?.message || e));
