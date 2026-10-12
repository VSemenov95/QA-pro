// Возможность mcp приложения Claude для тестов: вызовы host:<мост> уходят в Python (window.__mcp), а оттуда в настоящий мост.
// Подключается после caps.js (он создаёт window.claude).
(() => {
  // как в приложении Claude: мост из .mcpb виден под отображаемым именем, при ручной настройке — под ключом конфига
  const SERVER = window.__mcpServerName || 'host:QA_pro_____________________________';
  const DECLARED = ['host:QA_pro_____________________________', 'host:qa-pro-bridge'];
  window.__mcpCalls = [];
  const mcp = Object.freeze({
    listTools: async (server) => ({ servers: DECLARED.filter((n) => !server || n === server).map((n) => ({ server: n, authStatus: 'unknown', tools: ['ping', 'sfera_upload', 'sfera_job', 'sfera_cancel'].map((name) => ({ name, description: '' })) })) }),
    callTool: async (server, tool, input) => {
      window.__mcpCalls.push(server.slice(5, 12) + ':' + tool);
      if (!DECLARED.includes(server)) throw { code: 'not_in_manifest', message: 'not declared' };
      if (server !== SERVER) throw { code: 'server_not_connected', message: 'no such local server' };
      if (window.__mcpTools && !window.__mcpTools.includes(tool)) throw { code: 'not_in_manifest', message: 'tool not declared' };
      const r = await window.__mcp(tool, input || {});
      if (r && r.__err) throw { code: r.__err, message: r.message || '' };
      if (r.isError) throw { code: 'tool_error', message: (r.content && r.content[0] && r.content[0].text) || '', result: r };
      return { ...r, payload: r.structuredContent };
    },
  });
  const orig = window.claude.use;
  window.claude = { use: (n) => (n === 'mcp' ? new Promise((r) => setTimeout(() => r(mcp), 30)) : orig(n)) };
})();
