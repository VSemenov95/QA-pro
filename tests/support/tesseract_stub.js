/* Заглушка tesseract.js для тестов: «распознанный» текст — цвет левой верхней точки картинки.
   Считает вызовы (__ocr.calls), одновременные распознавания (__ocr.max) и созданные движки (__ocr.workers); __ocr.delay — задержка, мс.
   __ocr.hangInit — движок не загружается никогда (как в окне, где не скачались языковые данные); __ocr.inits — попытки загрузки;
   __ocr.hangRecognize — распознавание не заканчивается никогда; __ocr.hangAfter — зависает каждое распознавание после первых N;
   __ocr.paths — откуда движок брал файлы при каждой загрузке (null — с CDN); __ocr.failLocal — свои файлы движка не работают */
window.__ocr = window.__ocr || { calls: 0, now: 0, max: 0, workers: 0, delay: 30 };
window.Tesseract = {
  createWorker: async (langs, oem, opts) => {
    const o = window.__ocr;
    o.inits = (o.inits || 0) + 1;
    o.paths = [...(o.paths || []), opts?.workerPath ? { workerPath: opts.workerPath, corePath: opts.corePath, langs: Array.isArray(langs) ? langs.map((l) => `${l.code}:${l.data?.length}`) : langs } : null];
    if (o.hangInit || (o.failLocal && opts?.workerPath)) return o.failLocal && opts?.workerPath ? Promise.reject(new Error('local core blocked')) : new Promise(() => {});
    o.workers++;
    return {
      recognize: async (src) => {
        o.calls++; o.now++; o.max = Math.max(o.max, o.now);
        if (o.hangRecognize || (o.hangAfter != null && o.calls > o.hangAfter)) return new Promise(() => {});
        await new Promise((r) => setTimeout(r, o.delay));
        o.now--;
        let text = 'Картинка';
        if (src && src.getContext) { const [r, g, b] = src.getContext('2d').getImageData(0, 0, 1, 1).data; text = `Экран цвета ${r}-${g}-${b}`; }
        return { data: { text } };
      },
      terminate: async () => {},
    };
  },
};
