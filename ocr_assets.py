"""Файлы движка распознавания (tesseract.js 5.1.1) для публикации вместе с приложением: папка ocr/ рядом с tc-agent.html.
Приложение берёт движок и языковые данные отсюда, а cdn.jsdelivr.net — только если своих файлов нет (автономная версия).
Файлы скачиваются через npm pack один раз; в git их нет (.gitignore). Запуск: python ocr_assets.py"""
import base64
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'ocr')
# пакет npm → [(файл внутри пакета, куда положить в ocr/)]
FILES = {
    'tesseract.js@5.1.1': [('dist/tesseract.min.js', 'tesseract.min.js'), ('dist/worker.min.js', 'worker.min.js')],
    # ядро: распознавание LSTM (как по умолчанию в tesseract.js), с SIMD и без — движок выбирает сам по браузеру
    'tesseract.js-core@5.1.1': [('tesseract-core-simd-lstm.wasm.js', 'core/tesseract-core-simd-lstm.wasm.js'), ('tesseract-core-lstm.wasm.js', 'core/tesseract-core-lstm.wasm.js')],
    # языковые данные — те же, что движок берёт с CDN по умолчанию (4.0.0_best_int). Артефакт не отдаёт .gz,
    # поэтому они публикуются текстом base64 (.b64.txt): приложение раскодирует их и передаёт движку готовыми байтами
    '@tesseract.js-data/rus@1.0.0': [('4.0.0_best_int/rus.traineddata.gz', 'lang/rus.traineddata.gz.b64.txt')],
    '@tesseract.js-data/eng@1.0.0': [('4.0.0_best_int/eng.traineddata.gz', 'lang/eng.traineddata.gz.b64.txt')],
}
# опубликованный путь → файл на диске: для Artifact publish (files)
PUBLISH = {f'ocr/{dst}': os.path.join(OUT, dst) for items in FILES.values() for _, dst in items}


def ready():
    return all(os.path.isfile(p) and os.path.getsize(p) > 0 for p in PUBLISH.values())


def fetch():
    npm = shutil.which('npm') or 'npm'
    for pkg, items in FILES.items():
        if all(os.path.isfile(os.path.join(OUT, dst)) for _, dst in items):
            continue
        with tempfile.TemporaryDirectory() as tmp:
            out = subprocess.run([npm, 'pack', pkg, '--silent'], cwd=tmp, capture_output=True, text=True, timeout=300)
            name = out.stdout.strip().splitlines()[-1] if out.returncode == 0 and out.stdout.strip() else ''
            if not name:
                raise RuntimeError(f'npm pack {pkg}: {out.stderr[-300:]}')
            with tarfile.open(os.path.join(tmp, name)) as t:
                t.extractall(tmp)
            for src, dst in items:
                p = os.path.join(OUT, dst)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                if p.endswith('.b64.txt'):
                    with open(os.path.join(tmp, 'package', src), 'rb') as f, open(p, 'w', encoding='ascii') as o:
                        o.write(base64.b64encode(f.read()).decode('ascii'))
                else:
                    shutil.copyfile(os.path.join(tmp, 'package', src), p)


if __name__ == '__main__':
    fetch()
    total = sum(os.path.getsize(p) for p in PUBLISH.values())
    for k, p in PUBLISH.items():
        print(f'{k}\t{os.path.getsize(p)}')
    print(f'итого {total} байт', file=sys.stderr)
