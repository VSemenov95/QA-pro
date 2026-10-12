"""Тестовое видео для материалов: создаётся ffmpeg на лету (VP9 + Opus — их умеет декодировать тестовый Chromium).
Нет ffmpeg или кодеков — тесты с видео пропускаются."""
import shutil
import subprocess

import pytest


def ffmpeg_ok():
    if not shutil.which('ffmpeg'):
        return 'нет ffmpeg'
    enc = subprocess.run(['ffmpeg', '-hide_banner', '-encoders'], capture_output=True, text=True).stdout
    for name in ('libvpx-vp9', 'libopus', 'libx264'):
        if name not in enc:
            return f'в ffmpeg нет кодировщика {name}'
    return ''


def need_ffmpeg():
    why = ffmpeg_ok()
    if why:
        pytest.skip(why + ': видео для проверки не создать')


COLORS = ['red', 'blue', 'green', 'yellow', 'white', 'orange']   # кадр с чёрным квадратом: однотонные кадры приложение пропускает


def make_video(path, speech=((6, True), (5, False), (6, True)), audio=True, video=True, fragmented=False, size='320x240', codecs='vp9-opus'):
    """speech — участки звука: (секунды, есть ли «речь»). «Речь» — тон 300 Гц, тишина — цифровой ноль.
    Картинка: на каждый участок свой цвет (смена кадра = смена цвета)."""
    need_ffmpeg()
    args = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y']
    inputs, fparts, labels_v, labels_a = 0, [], [], []
    for i, (sec, talk) in enumerate(speech):
        if video:
            args += ['-f', 'lavfi', '-i', f'color=c={COLORS[i % len(COLORS)]}:s={size}:r=5:d={sec},drawbox=x=30:y=30:w=120:h=90:color=black:t=fill,format=yuv420p']
            labels_v.append(f'[{inputs}:v]')
            inputs += 1
        if audio:
            args += ['-f', 'lavfi', '-i', (f'sine=frequency=300:sample_rate=48000:d={sec}' if talk else f'anullsrc=r=48000:cl=mono:d={sec}')]
            labels_a.append(f'[{inputs}:a]')
            inputs += 1
    n = len(speech)
    if video:
        fparts.append(''.join(labels_v) + f'concat=n={n}:v=1:a=0[v]')
    if audio:
        fparts.append(''.join(labels_a) + f'concat=n={n}:v=0:a=1[a]')
    args += ['-filter_complex', ';'.join(fparts)]
    if video:
        args += ['-map', '[v]'] + (['-c:v', 'libx264', '-preset', 'ultrafast'] if codecs == 'h264-aac' else ['-c:v', 'libvpx-vp9', '-b:v', '80k', '-g', '10'])
    if audio:
        args += ['-map', '[a]'] + (['-c:a', 'aac', '-b:a', '48k'] if codecs == 'h264-aac' else ['-c:a', 'libopus', '-b:a', '32k'])
    if fragmented:
        args += ['-movflags', 'frag_keyframe+empty_moov']
    args += [str(path)]
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip('ffmpeg не смог создать тестовое видео: ' + r.stderr[-200:])
    return str(path)
