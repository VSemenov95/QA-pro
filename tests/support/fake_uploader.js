// «Загрузчик» внутри страницы: отвечает на пинг и на вызовы моста так, как это делает расширение (bridge.js).
// Распознавание речи возвращает window.__voiceText. Нужен, чтобы проверять страницу без настоящих расширения и моста.
window.__voiceText = ''; window.__asrCalls = []; window.__asrTools = []; window.__asrState = { state: 'ready', model: 'small' };
window.__asrFail = ''; window.__extVersion = '1.5.0'; window.__bridgeVersion = '1.2.0'; window.__bridgeUp = true;
window.addEventListener('message', (e) => {
  const d = e.data; if (!d || d.source !== 'qa-pro' || e.source !== window) return;
  const reply = (o) => window.postMessage(Object.assign({ source: 'qa-pro-sfera-uploader', id: d.id }, o), '*');
  if (d.type === 'SFERA_PING') { reply({ type: 'SFERA_HELLO' }); setTimeout(() => reply({ type: 'SFERA_PONG', version: window.__extVersion, baseUrl: '', bridge: window.__bridgeUp, bridgeVersion: window.__bridgeUp ? window.__bridgeVersion : '' }), 20); }
  else if (d.type === 'SFERA_RPC') {
    const t = d.tool, a = d.args || {}; let result = {};
    window.__asrTools.push(t);
    if (t === 'asr_status') result = window.__asrState;
    else if (t === 'asr_prepare') result = { state: 'ready', model: a.model };
    else if (t === 'asr_transcribe') { window.__asrCalls.push({ bytes: (a.audio || '').length, language: a.language }); result = { text: window.__voiceText }; }
    if (t === 'asr_transcribe' && window.__asrFail) { reply({ type: 'SFERA_RPC_RESULT', ok: false, error: window.__asrFail, code: 'bridge' }); return; }
    reply({ type: 'SFERA_RPC_RESULT', ok: true, result });
  }
});
