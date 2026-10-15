"""Обучающее видео по QA pro: запись экрана по сценарию + русская озвучка (espeak-ng, голос ru) + сборка MP4.

Запуск из корня репозитория:
    python3 training-video/record.py            # видео без звука, текст сцен — титрами
    python3 training-video/record.py --voice    # с русской озвучкой (espeak-ng, голос ru)

Нужны: Chromium для Playwright, ffmpeg, Pillow; для --voice ещё espeak-ng. Сборка приложения — python3 build.py.
Результат: training-video/qa-pro-training.mp4 (без звука) или qa-pro-training-voice.mp4; не длиннее 5 минут.
"""
import os
import subprocess
import sys
import argparse
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
MAX_SEC = 300
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
W, H = 1360, 900

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


def caption_png(text, path):
    """Титр: текст сцены на полосе внизу кадра (Pillow, шрифт с кириллицей)."""
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(FONT, 26)
    probe = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    lines, cur = [], ''
    for word in text.split():
        cand = (cur + ' ' + word).strip()
        if probe.textlength(cand, font=font) > W - 140:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    lines.append(cur)
    line_h = 38
    h = line_h * len(lines) + 30
    img = Image.new('RGBA', (W, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, h), fill=(20, 22, 27, 220))
    for i, line in enumerate(lines):
        draw.text((70, 15 + i * line_h), line, font=font, fill=(255, 255, 255, 255))
    img.save(path)
    return h


def hold_seconds(text):
    """Сколько держать сцену без голоса: время чтения титра примерно 13 знаков в секунду, не меньше 9 секунд."""
    return max(9.0, len(text) / 13 + 2.0)


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
    ap = argparse.ArgumentParser()
    ap.add_argument('--voice', action='store_true', help='русская озвучка вместо титров')
    args = ap.parse_args()
    out_mp4 = os.path.join(OUT_DIR, 'qa-pro-training-voice.mp4' if args.voice else 'qa-pro-training.mp4')

    if os.environ.get('QA_PRO_NO_BUILD') != '1':
        subprocess.run([sys.executable, os.path.join(ROOT, 'build.py')], check=True, cwd=ROOT)
    work = tempfile.mkdtemp(prefix='qa-pro-video-')
    vid_dir = os.path.join(work, 'video')
    os.makedirs(vid_dir)

    # длительность и подписи каждой сцены
    scenes = []
    for i, (text, name) in enumerate(SCENES):
        if args.voice:
            wav = os.path.join(work, f'scene{i:02d}.wav')
            speak(text, wav)
            hold = duration(wav) + 1.0
        else:
            wav = None
            hold = hold_seconds(text)
        png = os.path.join(work, f'cap{i:02d}.png')
        caption_png(text, png)
        scenes.append({'name': name, 'wav': wav, 'hold': hold, 'png': png})

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs(p))
        orig_new_context = browser.new_context

        def new_context(**kw):
            kw.setdefault('record_video_dir', vid_dir)
            kw.setdefault('record_video_size', {'width': W, 'height': H})
            return orig_new_context(**kw)
        browser.new_context = new_context

        t0 = time.time()
        app = open_app(browser, kind='artifact', viewport=(W, H))
        app.page.wait_for_timeout(1500)
        for sc in scenes:
            sc['start'] = time.time() - t0
            try:
                run_actions(app, sc['name'], work)
            except Exception as e:  # сцена остаётся на экране, запись продолжается
                print('сцена', sc['name'], 'без действия:', str(e)[:120])
            left = sc['start'] + sc['hold'] - (time.time() - t0)
            if left > 0:
                app.page.wait_for_timeout(left * 1000)
        video_path = app.page.video.path()
        app.ctx.close()
        browser.close()

    total = max(sc['start'] + sc['hold'] for sc in scenes)
    if total > MAX_SEC:
        raise SystemExit(f'видео {total:.0f} с длиннее {MAX_SEC} с')

    inputs = ['-i', video_path]
    filters = []
    audio_labels = []
    for i, sc in enumerate(scenes):
        inputs += ['-loop', '1', '-t', f'{total:.1f}', '-i', sc['png']]
    # титры: каждый накладывается только на время своей сцены
    chain = '[0:v]'
    for i, sc in enumerate(scenes):
        end = sc['start'] + sc['hold']
        nxt = f'[v{i}]'
        filters.append(f"{chain}[{i + 1}:v]overlay=0:main_h-overlay_h:enable='between(t,{sc['start']:.2f},{end:.2f})'{nxt}")
        chain = nxt
    video_out = chain
    cmd = ['ffmpeg', '-v', 'error', '-y', *inputs]
    if args.voice:
        for i, sc in enumerate(scenes):
            cmd += ['-i', sc['wav']]
        base = len(scenes) + 1
        for i, sc in enumerate(scenes):
            ms = int(sc['start'] * 1000)
            filters.append(f'[{base + i}:a]adelay={ms}|{ms},aresample=44100[a{i}]')
            audio_labels.append(f'[a{i}]')
        filters.append(f'{"".join(audio_labels)}amix=inputs={len(audio_labels)}:normalize=0[aout]')
    cmd += ['-filter_complex', ';'.join(filters), '-map', video_out]
    cmd += ['-map', '[aout]', '-c:a', 'aac', '-b:a', '128k'] if args.voice else ['-an']
    cmd += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-preset', 'veryfast', '-crf', '26',
            '-t', f'{total:.1f}', '-movflags', '+faststart', out_mp4]
    subprocess.run(cmd, check=True)
    print('готово:', out_mp4, f'{duration(out_mp4):.0f} с')


if __name__ == '__main__':
    main()
