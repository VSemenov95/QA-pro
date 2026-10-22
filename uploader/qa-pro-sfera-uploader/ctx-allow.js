const $ = (s) => document.querySelector(s);
const send = (msg) => new Promise((resolve) => chrome.runtime.sendMessage(msg, (r) => resolve(r || { ok: false, error: chrome.runtime.lastError?.message })));
const id = new URLSearchParams(location.search).get('id') || '';
const TEXT = {
  roots: ['Странице QA pro нужен доступ к папке на этом компьютере: читать и записывать правила, шаблоны, память агента и базу знаний.', 'Папка', 'Мост qa-pro-bridge будет работать только с текстовыми файлами (.md, .txt, .json, .yaml) внутри этой папки.'],
  repos: ['Странице QA pro нужно склонировать git-репозиторий на этот компьютер и работать с клоном: читать контекст, обновлять (pull) и отправлять изменения в отдельную ветку.', 'Репозиторий', 'Мост склонирует его в папку ~/.qa-pro-bridge/repos. Вход в git — ваш обычный (ключ SSH или сохранённый пароль).'],
  gh: ['Странице QA pro нужен доступ к репозиторию GitHub с вашим токеном из настроек загрузчика: читать контекст и отправлять изменения в отдельную ветку qa-pro/<дата>.', 'Репозиторий GitHub', 'Токен остаётся в загрузчике — страница его не получает.'],
};
send({ type: 'CTX_ASK_INFO', id }).then((r) => {
  const a = r?.ask;
  if (!a) { $('#what').textContent = 'Запрос устарел — повторите действие в QA pro.'; $('#allow').disabled = true; return; }
  const [what, lbl, note] = TEXT[a.kind] || TEXT.roots;
  $('#what').textContent = what;
  $('#target-lbl').textContent = lbl;
  $('#target').textContent = a.target;
  $('#origin').textContent = a.origin;
  $('#note').textContent = note;
  $('#allow').focus();
});
$('#allow').addEventListener('click', async () => { await send({ type: 'CTX_DECIDE', id, allow: true }); window.close(); });
$('#deny').addEventListener('click', async () => { await send({ type: 'CTX_DECIDE', id, allow: false }); window.close(); });
