"""Видео не загружается в QA pro: ни через общую загрузку, ни через вкладку «Материалы» (её больше нет)."""


def test_upload_picker_does_not_accept_video(app):
    assert '.mp4' not in app.page.get_attribute('#file-input', 'accept')


def test_dropped_video_is_rejected_with_a_message(app, tmp_path):
    video = tmp_path / 'demo.mp4'
    video.write_bytes(b'\x00\x00\x00\x18ftypmp42' + b'\x00' * 64)
    app.page.set_input_files('#file-input', [str(video)])
    app.page.wait_for_function("() => [...document.querySelectorAll('.toast, #toasts > *')].some((e) => e.innerText.includes('Видео не загружаются'))", timeout=10000)
    assert not app.state("S.docs.some((d) => d.name === 'demo.mp4')")


def test_materials_tab_is_gone(app):
    app.mode('help')
    assert app.count('[data-act=help-view][data-v=mat]') == 0 and app.count('#mat-drop') == 0
