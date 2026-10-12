"""Библиотеки разбора документов (mammoth, xlsx, pdf.js) приложение грузит с CDN. В тестах CDN отключён,
запросы подменяются локальными копиями из npm; копии скачиваются один раз в tests/.cache/libs. Нет сети — тесты с документами пропускаются."""
import os
import shutil
import subprocess
import tarfile
import tempfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(HERE, '.cache', 'libs')
# адрес на CDN (подстрока) → (пакет npm, файл внутри пакета)
LIBS = {
    'mammoth@1.8.0/mammoth.browser.min.js': ('mammoth@1.8.0', 'mammoth.browser.min.js'),
    'mammoth@1.8.0': ('mammoth@1.8.0', 'mammoth.browser.min.js'),
    'pdfjs-dist@3.11.174/build/pdf.min.js': ('pdfjs-dist@3.11.174', 'build/pdf.min.js'),
    'pdfjs-dist@3.11.174/build/pdf.worker.min.js': ('pdfjs-dist@3.11.174', 'build/pdf.worker.min.js'),
    'pdf.js/3.11.174/pdf.min.js': ('pdfjs-dist@3.11.174', 'build/pdf.min.js'),
    'pdf.js/3.11.174/pdf.worker.min.js': ('pdfjs-dist@3.11.174', 'build/pdf.worker.min.js'),
    'xlsx@0.18.5/dist/xlsx.full.min.js': ('xlsx@0.18.5', 'dist/xlsx.full.min.js'),
    'xlsx/0.18.5/xlsx.full.min.js': ('xlsx@0.18.5', 'dist/xlsx.full.min.js'),
}


def _dir(pkg):
    return os.path.join(CACHE, pkg.replace('@', '-').replace('/', '_'))


def ensure():
    """Возвращает True, если все библиотеки есть локально (при необходимости скачивает через npm pack)."""
    ok = True
    for pkg in {p for p, _ in LIBS.values()}:
        d = _dir(pkg)
        if os.path.isdir(os.path.join(d, 'package')):
            continue
        try:
            os.makedirs(d, exist_ok=True)
            with tempfile.TemporaryDirectory() as tmp:
                out = subprocess.run(['npm', 'pack', pkg, '--silent'], cwd=tmp, capture_output=True, text=True, timeout=180)
                tgz = os.path.join(tmp, out.stdout.strip().splitlines()[-1]) if out.returncode == 0 and out.stdout.strip() else None
                if not tgz or not os.path.exists(tgz):
                    raise RuntimeError(out.stderr[-300:])
                with tarfile.open(tgz) as t:
                    t.extractall(d)
        except Exception:
            shutil.rmtree(d, ignore_errors=True)
            ok = False
    return ok


def local_file(url):
    for key, (pkg, rel) in LIBS.items():
        if key in url:
            p = os.path.join(_dir(pkg), 'package', rel)
            return p if os.path.exists(p) else None
    return None
