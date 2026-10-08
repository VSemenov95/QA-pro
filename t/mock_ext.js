(() => {
  const realFetch = window.fetch.bind(window);
  window.__ext = [];
  const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json' } });
  window.fetch = async (url, opts = {}) => {
    const u = String(url);
    if (u.startsWith('https://api.anthropic.com/')) {
      const body = JSON.parse(opts.body || '{}');
      window.__ext.push({ u, key: opts.headers?.['x-api-key'], model: body.model });
      const c = body.messages[0].content, prompt = Array.isArray(c) ? c.map((b) => b.text).join('') : c;
      const out = await window.__mockJSON(prompt);
      return json({ content: [{ type: 'text', text: JSON.stringify(out) }], stop_reason: 'end_turn', usage: { input_tokens: 100, output_tokens: 50 } });
    }
    if (u.startsWith('http://ai.test/') || u.startsWith('https://api.openai.com/') || u.startsWith('https://chat.aicenter.inno.tech/')) {
      const body = JSON.parse(opts.body || '{}');
      window.__ext.push({ u, auth: opts.headers?.Authorization, model: body.model, stream: body.stream, temp: body.temperature });
      const prompt = body.messages.find((m) => m.role === 'user').content;
      await new Promise((r) => setTimeout(r, window.__delay || 0));
      const out = await window.__mockJSON(prompt);
      return json({ choices: [{ message: { role: 'assistant', content: '```json\n' + JSON.stringify(out) + '\n```' } }] });
    }
    if (u.startsWith('http://tms.test/')) {
      window.__ext.push({ u, auth: opts.headers?.Authorization, body: opts.body ? JSON.parse(opts.body) : null });
      if (u.includes('/api/v2/projects/')) return json({ name: 'Демо-проект' });
      if (u.includes('/api/v2/workItems')) return json({ id: 'uuid', globalId: 1000 + window.__ext.length });
      return json({}, 404);
    }
    return realFetch(url, opts);
  };
})();
