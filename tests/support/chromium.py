"""Запуск Chromium для Playwright: QA_PRO_CHROMIUM, затем собственная сборка Playwright, затем /opt/pw-browsers."""
import glob
import os


def launch_kwargs(p):
    env = os.environ.get('QA_PRO_CHROMIUM')
    if env:
        return {'executable_path': env}
    try:
        if os.path.exists(p.chromium.executable_path):
            return {}
    except Exception:
        pass
    for pat in ('/opt/pw-browsers/chromium', '/opt/pw-browsers/chromium-*/chrome-linux/chrome', '/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell'):
        found = sorted(glob.glob(pat))
        if found:
            return {'executable_path': found[-1]}
    return {}
