"""Тестовые файлы создаются на лету: ничего не хранится в репозитории и не берётся из чужих папок."""
import json
import os


def spec_md(version='1.3', link_minutes=30, limit=3, timer=True, extra=''):
    """ТЗ «Восстановление пароля»; параметры нужны, чтобы сделать «новую версию» для актуализации."""
    timer_line = ' Повторная отправка на этом экране доступна через 60 секунд: кнопка «Отправить ссылку» неактивна, на ней обратный отсчёт «Повторить через N с».' if timer else ''
    return f"""# ТЗ: Восстановление пароля в личном кабинете
Версия {version}

## 1. Назначение
Пользователь, забывший пароль, восстанавливает доступ к личному кабинету по ссылке из письма. Функция доступна неавторизованному пользователю.

## 2. Экран «Восстановление пароля»
2.1. На странице входа /login под полем пароля отображается ссылка «Забыли пароль?». По нажатию открывается экран «Восстановление пароля».
2.2. Экран содержит поле Email (обязательное, до 254 символов) и кнопку «Отправить ссылку».
2.3. Если введён email неверного формата, под полем выводится сообщение «Введите корректный email».
2.4. После отправки показывается сообщение «Если адрес зарегистрирован, мы отправили на него письмо».{timer_line}
2.5. Экран «Новый пароль» открывается по ссылке из письма и содержит поля «Новый пароль» и «Повторите пароль».
2.6. Требования к паролю: от 8 до 64 символов, минимум одна заглавная латинская буква и одна цифра.

## 3. API
3.1. POST /api/v1/password-reset принимает {{"email": "..."}}. Для корректного email возвращает 202 {{"status":"sent"}}, для неверного формата — 400 {{"code":"INVALID_EMAIL"}}.
3.2. POST /api/v1/password-reset/confirm принимает {{"token": "...", "password": "..."}}. При успехе — 200, при просроченной ссылке — 410 {{"code":"TOKEN_EXPIRED"}}.

## 4. Ограничения
4.1. Ссылка действует {link_minutes} минут и может быть использована один раз.
4.2. Не более {limit} запросов на сброс для одного email за 15 минут. При превышении API возвращает 429 {{"code":"RATE_LIMIT"}}, а на экране показывается «Слишком много попыток. Повторите через N мин.».

## 5. Сквозной сценарий
5.1. Пользователь запрашивает ссылку, переходит по ней из письма, задаёт новый пароль и входит с ним на странице входа.
{extra}"""


def write(path, text):
    os.makedirs(os.path.dirname(str(path)), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    return str(path)


def spec_file(tmp_path, name='ТЗ-восстановление.md', **kw):
    return write(os.path.join(tmp_path, name), spec_md(**kw))


def _case(prefix, i, title, steps, extra=None):
    c = {'id': f'{prefix}-{i:03d}', 'title': title, 'priority': 'High', 'preconditions': ['Пользователь зарегистрирован'],
         'steps': [{'step': k + 1, 'action': a, 'expected': e} for k, (a, e) in enumerate(steps)], 'expectedResult': steps[-1][1]}
    c.update(extra or {})
    return c


def cases_dict(n_api=3, n_ui=4, n_e2e=1):
    """Файл «тест-кейсы для актуализации» в формате выгрузки QA pro: {testCases: {api, ui, e2e}}.
    Кейс с «Неверный email» в тексте модель-мок считает изменившимся, с «SMS» — устаревшим."""
    api = [_case('API', i + 1, f'POST /api/v1/password-reset — проверка {i + 1}', [('Отправить POST /api/v1/password-reset', 'Код ответа 202')], {'request': {'method': 'POST', 'endpoint': '/api/v1/password-reset', 'body': {'email': 'user@example.ru'}}}) for i in range(n_api)]
    ui = [_case('UI', i + 1, f'Экран восстановления: проверка {i + 1}', [('Открыть /login', 'Открыта страница входа'), ('Нажать «Забыли пароль?»', 'Открыт экран «Восстановление пароля»')]) for i in range(n_ui)]
    if ui:
        ui[0]['title'] = 'Экран восстановления: ошибка при email без символа @'
        ui[0]['steps'][-1]['expected'] = 'Сообщение «Неверный email»'
    if len(ui) > 1:
        ui[1]['title'] = 'Восстановление пароля по SMS'
    e2e = [_case('E2E', i + 1, f'Сквозное восстановление доступа {i + 1}', [('Запросить ссылку', 'Письмо отправлено'), ('Задать новый пароль', 'Вход выполнен')]) for i in range(n_e2e)]
    return {'generatedAt': '2026-01-01T00:00:00Z', 'testCases': {'api': api, 'ui': ui, 'e2e': e2e}}


def cases_json(tmp_path, name='cases.json', **kw):
    return write(os.path.join(tmp_path, name), json.dumps(cases_dict(**kw), ensure_ascii=False, indent=1))


def cases_xlsx(tmp_path, name='cases.xlsx', n=4):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Тест-кейсы'
    ws.append(['ID', 'Название', 'Шаг', 'Ожидаемый результат'])
    for i in range(n):
        ws.append([f'TC-{i + 1}', f'Восстановление пароля: проверка {i + 1}', 'Открыть /login', 'Открыта страница входа'])
        ws.append(['', '', 'Нажать «Забыли пароль?»', 'Открыт экран «Восстановление пароля»'])
    p = os.path.join(tmp_path, name)
    wb.save(p)
    return p


def docx_file(tmp_path, name='ТЗ-корзина.docx'):
    from docx import Document
    d = Document()
    d.add_heading('ТЗ: Корзина', 1)
    d.add_paragraph('2.1. Пользователь добавляет товар в корзину кнопкой «В корзину».')
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = 'Поле', 'Ограничение'
    t.cell(1, 0).text, t.cell(1, 1).text = 'Количество', 'от 1 до 99'
    p = os.path.join(tmp_path, name)
    d.save(p)
    return p


def xlsx_requirements(tmp_path, name='требования.xlsx'):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Требования'
    ws.append(['ID', 'Требование'])
    ws.append(['FR-1', 'Сумма заказа превышает 500 рублей — доставка бесплатная'])
    p = os.path.join(tmp_path, name)
    wb.save(p)
    return p


def pdf_file(tmp_path, name='спецификация.pdf'):
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    font = next((f for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf') if os.path.exists(f)), None)
    if not font:
        raise FileNotFoundError('нет шрифта DejaVuSans для PDF')
    pdfmetrics.registerFont(TTFont('DV', font))
    p = os.path.join(tmp_path, name)
    c = canvas.Canvas(p)
    c.setFont('DV', 12)
    c.drawString(72, 760, '3.1. POST /api/v1/cart возвращает 201 Created')
    c.drawString(72, 740, 'Ошибка валидации — 400 Bad Request')
    c.save()
    return p


def openapi_spec(tmp_path, name='auth-api.json', yaml=False):
    """Спецификация OpenAPI 3: два эндпоинта (с $ref в теле и ответах) и один не относящийся к восстановлению."""
    import json as _json
    spec = {
        'openapi': '3.0.3', 'info': {'title': 'Auth API', 'version': '2.1'}, 'servers': [{'url': 'https://api.example.ru'}],
        'paths': {
            '/api/v1/password-reset': {'post': {
                'tags': ['auth'], 'operationId': 'requestPasswordReset', 'summary': 'Запрос ссылки для сброса пароля',
                'requestBody': {'content': {'application/json': {'schema': {'$ref': '#/components/schemas/ResetRequest'}}}},
                'responses': {'202': {'description': 'Ссылка отправлена', 'content': {'application/json': {'schema': {'type': 'object', 'properties': {'status': {'type': 'string', 'enum': ['sent']}}}}}},
                              '400': {'description': 'Неверный формат email', 'content': {'application/json': {'schema': {'$ref': '#/components/schemas/Error'}}}}}}},
            '/api/v1/users/{id}': {'get': {'tags': ['users'], 'summary': 'Карточка пользователя',
                'parameters': [{'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}],
                'responses': {'200': {'description': 'OK'}}}},
        },
        'components': {'schemas': {
            'ResetRequest': {'type': 'object', 'required': ['email'], 'properties': {'email': {'type': 'string', 'format': 'email', 'maxLength': 254, 'example': 'user@example.ru', 'description': 'Email, указанный при регистрации'}}},
            'Error': {'type': 'object', 'properties': {'code': {'type': 'string', 'example': 'INVALID_EMAIL'}, 'message': {'type': 'string'}}},
        }},
    }
    if yaml:
        import json as j
        text = '# OpenAPI\n' + j.dumps(spec, ensure_ascii=False, indent=2)   # JSON — корректный YAML
        return write(os.path.join(str(tmp_path), name.replace('.json', '.yaml')), text)
    return write(os.path.join(str(tmp_path), name), _json.dumps(spec, ensure_ascii=False, indent=1))
