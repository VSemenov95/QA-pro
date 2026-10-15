"""Обучающее видео по QA pro: запись экрана по сценарию + русская озвучка (espeak-ng, голос ru) + сборка MP4.

Запуск из корня репозитория:
    python3 training-video/record.py

Нужны: Chromium для Playwright, espeak-ng (голос ru), ffmpeg. Сборка приложения — python3 build.py.
Результат: training-video/qa-pro-training.mp4 (не длиннее 5 минут).
"""
import os
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_MP4 = os.path.join(OUT_DIR, 'qa-pro-training.mp4')
MAX_SEC = 300

from playwright.sync_api import sync_playwright  # noqa: E402
from tests.conftest import launch_kwargs  # noqa: E402
from tests.support import files  # noqa: E402
from tests.support.app import open_app  # noqa: E402

# Сценарий: текст диктора и действие на экране. Текст — тот же, что в narration.md.
SCENES = [
    ('QA pro превращает документацию в тест-кейсы и чек-лист. Агент читает ваши документы, выделяет требования, пишет кейсы по шаблонам команды, проверяет их ревьюером и передаёт в проект.', 'intro'),
    ('Вверху — статусы подключения, выбор продукта и кнопка «Новый запуск». Режимов три: генерация, актуализация кейсов и база знаний.', 'modes'),
    ('В карточке продукта можно переименовать продукт, выгрузить его целиком или загрузить из файла. Продукт хранит документы, кейсы и историю запусков.', 'product'),
    ('В блоке документов загружаются техническое задание и спецификации: файлы docx, pdf, xlsx, csv, txt и md. Для примера уже добавлен документ.', 'docs'),
    ('В параметрах выбирается, что генерировать, виды тестов: A-P-I, U-I и E-2-E, и глубина покрытия. Поле «Тестов всего» необязательно: оно ограничивает число проверок.', 'params'),
    ('Загрузите спецификацию в формате json или yaml. Тогда поле «А-П-И, для которого нужны тесты» становится активным: укажите эндпоинт, например password-reset.', 'openapi'),
    ('Нажмите «Сгенерировать тест-кейсы». Вкладка «Агент» показывает шаги: разбор документов, анализ требований, чек-лист, план и генерацию кейсов.', 'run'),
    ('Кейсы попадают в черновик. Здесь их можно перегенерировать по правилам, сократить число тестов, убрать лишний кейс или добавить черновик в проект.', 'draft'),
    ('На вкладке «Тест-кейсы» кейсы фильтруются по видам тестов и наборам «Смоук» и «Регресс». Кейс раскрывается по щелчку.', 'cases'),
    ('Вкладка «Ревью» показывает замечания ревьюера. Критичные и существенные замечания видны отдельно, мелкие приходят одной строкой. Замечание можно исправить или отклонить.', 'review'),
    ('Вкладка «Экспорт» выгружает кейсы в нужный формат. Формат описывается словами в настройках. Если формат не задан, выгружается стандартный json.', 'export'),
    ('Режим «База знаний» хранит разделы о продукте и ответы на вопросы. В этом режиме кнопка «Новый запуск» неактивна.', 'kb'),
    ('Подробное руководство — в файле INSTRUCTION точка md, устройство приложения — в файле ARCHITECTURE точка md. Спасибо за внимание.', 'outro'),
]


def speak(text, path):
    subprocess.run(['espeak-ng', '-v', 'ru', '-s', '150', '-w', path, text], check=True)


def duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                         check=True, capture_output=True, text=True).stdout
    return float(out.strip())


def run_actions(app, name, tmp):
    page = app.page
    if name == 'modes':
        app.mode('update')
        page.wait_for_timeout(800)
        app.mode('generate')
    elif name == 'params':
        try:
            page.click('#depth button:has-text("Полный")')
        except Exception:
            pass
    elif name == 'openapi':
        app.upload(files.openapi_spec(tmp))
        page.fill('#api-filter', 'password-reset')
        page.dispatch_event('#api-filter', 'input')
        page.wait_for_timeout(900)
    elif name == 'run':
        page.click('#btn-run')
        app.wait_idle(120000)
    elif name == 'draft':
        app.tab('draft')
    elif name == 'cases':
        app.tab('cases')
        try:
            page.click('#case-list article:first-child .case-h')
        except Exception:
            pass
    elif name == 'review':
        app.tab('review')
        page.click('[data-act=start-review]')
        app.wait_idle(120000)
    elif name == 'export':
        app.tab('export')
    elif name == 'kb':
        app.mode('help')
    # остальные сцены — пояснение на экране без действий


def main():
    if os.environ.get('QA_PRO_NO_BUILD') != '1':
        subprocess.run([sys.executable, os.path.join(ROOT, 'build.py')], check=True, cwd=ROOT)
    work = tempfile.mkdtemp(prefix='qa-pro-video-')
    vid_dir = os.path.join(work, 'video')
    os.makedirs(vid_dir)
    audio = []
    for i, (text, name) in enumerate(SCENES):
        wav = os.path.join(work, f'scene{i:02d}.wav')
        speak(text, wav)
        audio.append((wav, duration(wav), name))

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs(p))
        orig_new_context = browser.new_context

        def new_context(**kw):
            kw.setdefault('record_video_dir', vid_dir)
            kw.setdefault('record_video_size', {'width': 1360, 'height': 900})
            return orig_new_context(**kw)
        browser.new_context = new_context

        t0 = time.time()
        app = open_app(browser, kind='artifact', viewport=(1360, 900))
        app.page.wait_for_timeout(1500)
        starts = []
        for (wav, dur, name), (text, _) in zip(audio, SCENES):
            start = time.time() - t0
            starts.append(start)
            try:
                run_actions(app, name, work)
            except Exception as e:  # сцена остаётся на экране, озвучка продолжается
                print('сцена', name, 'без действия:', str(e)[:120])
            left = start + dur + 1.0 - (time.time() - t0)
            if left > 0:
                app.page.wait_for_timeout(left * 1000)
        video_path = app.page.video.path()
        app.ctx.close()
        browser.close()

    total = max(s + d + 1.0 for s, (_, d, _) in zip(starts, audio))
    if total > MAX_SEC:
        raise SystemExit(f'видео {total:.0f} с длиннее {MAX_SEC} с')
    inputs = ['-i', video_path]
    filters = []
    labels = []
    for i, ((wav, dur, _), start) in enumerate(zip(audio, starts)):
        inputs += ['-i', wav]
        ms = int(start * 1000)
        filters.append(f'[{i + 1}:a]adelay={ms}|{ms},aresample=44100[a{i}]')
        labels.append(f'[a{i}]')
    filters.append(f'{"".join(labels)}amix=inputs={len(labels)}:normalize=0[aout]')
    cmd = ['ffmpeg', '-v', 'error', '-y', *inputs, '-filter_complex', ';'.join(filters),
           '-map', '0:v', '-map', '[aout]', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'veryfast', '-crf', '26',
           '-c:a', 'aac', '-b:a', '128k', '-t', f'{total:.1f}', '-movflags', '+faststart', OUT_MP4]
    subprocess.run(cmd, check=True)
    print('готово:', OUT_MP4, f'{duration(OUT_MP4):.0f} с')


if __name__ == '__main__':
    main()
