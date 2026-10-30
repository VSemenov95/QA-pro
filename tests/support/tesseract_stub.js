/* Заглушка tesseract.js для тестов: «распознанный» текст — цвет левой верхней точки картинки.
   Считает вызовы (__ocr.calls), одновременные распознавания (__ocr.max) и созданные движки (__ocr.workers); __ocr.delay — задержка, мс */
window.__ocr = window.__ocr || { calls: 0, now: 0, max: 0, workers: 0, delay: 30 };
window.Tesseract = {
  createWorker: async () => {
    window.__ocr.workers++;
    return {
      recognize: async (src) => {
        const o = window.__ocr;
        o.calls++; o.now++; o.max = Math.max(o.max, o.now);
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
