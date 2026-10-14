"""Расшифровка видео становится документом продукта и попадает в документы запуска (генерация и актуализация)."""


def transcript():
    text = '# Видео: демонстрация входа\n\nПользователь открывает /login и вводит пароль.'
    return {'id': 'vid-1', 'name': 'Демо входа.md', 'ext': 'md', 'size': len(text) * 2, 'status': 'ready', 'text': text,
            'chars': len(text), 'error': '', 'warn': '', 'preview': False, 'addedAt': 1, 'source': 'video', 'video': {'name': 'demo.mp4'}}


def add_transcript(app):
    app.call("(() => { a.addVideoDoc({ ...arg, pid: S.productId }); return true; })()", transcript())


def test_transcript_goes_into_the_run_in_generate_mode(app):
    add_transcript(app)
    assert app.state("a.docsFor(null).some((d) => d.id === 'vid-1')") is True


def test_transcript_is_not_in_the_run_in_help_mode(app):
    app.mode('help')
    add_transcript(app)
    assert app.state("a.docsFor(null).some((d) => d.id === 'vid-1')") is False
    assert app.state("S.docs.some((d) => d.id === 'vid-1')") is True
