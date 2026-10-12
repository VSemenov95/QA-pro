"""Мост qa-pro-bridge под управлением теста: MCP-обёртка (stdio), ядро (фоновый процесс) и «загрузчик» по WebSocket.

    br = Bridge(tmp_path / 'bridge')            # своя папка данных и свободный порт, чужой ~/.qa-pro-bridge не трогаем
    br.start()                                  # обёртка + ядро, ждёт готовности
    br.tool('ping')                             # structuredContent ответа; ошибка моста -> BridgeError
    ws = br.ws()                                # WebSocket от имени расширения Chrome
    ws.send({'t': 'hello', 'version': '1.5.0'})
    ws.wait(lambda m: m['t'] == 'job')          # ждать сообщение от моста
    br.stop()                                   # закрыть приложение Claude, остановить ядро
"""
import base64
import json
import os
import queue
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BRIDGE_SRC = os.path.join(ROOT, 'bridge', 'qa-pro-bridge')
SERVER = os.path.join(BRIDGE_SRC, 'server')
EXT_ORIGIN = 'chrome-extension://abcdefghijklmnopabcdefghijklmnop'


class BridgeError(Exception):
    """Инструмент моста вернул isError: в приложении Claude это текст ошибки."""


def have_node():
    return shutil.which('node') is not None


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def clean_env(**extra):
    """Окружение для Node: без прокси (мост ходит только на 127.0.0.1)."""
    env = {k: v for k, v in os.environ.items() if k.lower() not in ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy', 'node_use_env_proxy')}
    env['NO_PROXY'] = '127.0.0.1,localhost'
    env.update({k: str(v) for k, v in extra.items()})
    return env


def http(port, method, path, body=None, headers=None, timeout=5):
    """Запрос к ядру: (код, json-или-текст)."""
    data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            code, raw = r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        code, raw = e.code, e.read().decode('utf-8', 'replace')
    try:
        return code, json.loads(raw)
    except ValueError:
        return code, raw


class WsClient:
    """Минимальный WebSocket-клиент: подключается к /ext ядра моста с заданным Origin."""

    def __init__(self, port, origin=EXT_ORIGIN, path='/ext'):
        self.msgs, self.closed, self._cv = [], False, threading.Condition()
        self.sock = socket.create_connection(('127.0.0.1', port), timeout=5)
        key = base64.b64encode(os.urandom(16)).decode()
        head = f'GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nConnection: Upgrade\r\nUpgrade: websocket\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n'
        if origin:
            head += f'Origin: {origin}\r\n'
        self.sock.sendall((head + '\r\n').encode())
        buf = b''
        while b'\r\n\r\n' not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        head_raw, _, self._buf = buf.partition(b'\r\n\r\n')
        self.status = int(head_raw.split(b' ')[1]) if head_raw.startswith(b'HTTP/') else 0
        self.sock.settimeout(None)
        if self.status == 101:
            threading.Thread(target=self._read, daemon=True).start()
        else:
            self.closed = True

    def _read(self):
        buf = self._buf
        try:
            while True:
                while len(buf) >= 2:
                    op, ln, off = buf[0] & 0x0f, buf[1] & 0x7f, 2
                    if ln == 126:
                        if len(buf) < 4:
                            break
                        ln, off = int.from_bytes(buf[2:4], 'big'), 4
                    elif ln == 127:
                        if len(buf) < 10:
                            break
                        ln, off = int.from_bytes(buf[2:10], 'big'), 10
                    if len(buf) < off + ln:
                        break
                    payload, buf = buf[off:off + ln], buf[off + ln:]
                    if op == 1:
                        with self._cv:
                            self.msgs.append(json.loads(payload.decode('utf-8')))
                            self._cv.notify_all()
                    elif op == 8:
                        return
                chunk = self.sock.recv(65536)
                if not chunk:
                    return
                buf += chunk
        except OSError:
            pass
        finally:
            with self._cv:
                self.closed = True
                self._cv.notify_all()

    def send(self, obj):
        payload = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        mask = os.urandom(4)
        n = len(payload)
        head = bytes([0x81, 0x80 | n]) if n < 126 else bytes([0x81, 0x80 | 126]) + n.to_bytes(2, 'big') if n < 65536 else bytes([0x81, 0x80 | 127]) + n.to_bytes(8, 'big')
        self.sock.sendall(head + mask + bytes(b ^ mask[i & 3] for i, b in enumerate(payload)))

    def of(self, t):
        with self._cv:
            return [m for m in self.msgs if m.get('t') == t]

    def wait(self, pred, timeout=10):
        """Ждёт сообщение, подходящее под условие; возвращает его."""
        end = time.time() + timeout
        seen = 0
        with self._cv:
            while True:
                for m in self.msgs[seen:]:
                    if pred(m):
                        return m
                seen = len(self.msgs)
                left = end - time.time()
                if left <= 0:
                    raise AssertionError(f'мост не прислал нужное сообщение за {timeout} с; пришло: {self.msgs}')
                self._cv.wait(left)

    def wait_closed(self, timeout=10):
        end = time.time() + timeout
        with self._cv:
            while not self.closed:
                left = end - time.time()
                if left <= 0:
                    return False
                self._cv.wait(left)
        return True

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class Bridge:
    """Обёртка MCP (server/index.js), как её запускает приложение Claude, и фоновое ядро (core.js)."""

    def __init__(self, directory, port=None, env=None):
        self.dir, self.port = str(directory), port or free_port()
        os.makedirs(self.dir, exist_ok=True)
        self.env = clean_env(QA_PRO_BRIDGE_PORT=self.port, QA_PRO_BRIDGE_DIR=self.dir, **(env or {}))
        self.proc, self.stderr, self._ws = None, [], []
        self._pending, self._ids, self._lock = {}, 0, threading.Lock()

    # ---------- жизненный цикл ----------
    def start(self, ping=True):
        """Запускает обёртку, делает initialize; ping=True ждёт, пока ядро поднимется (первый вызов инструмента)."""
        self.proc = subprocess.Popen(['node', os.path.join(SERVER, 'index.js')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env, text=True, encoding='utf-8')
        threading.Thread(target=self._read_out, daemon=True).start()
        threading.Thread(target=self._read_err, daemon=True).start()
        self.rpc('initialize', {'protocolVersion': '2025-06-18', 'capabilities': {}, 'clientInfo': {'name': 'test', 'version': '1'}})
        if ping:
            self.call('ping')
        return self

    def _read_out(self):
        for line in self.proc.stdout:
            try:
                m = json.loads(line)
            except ValueError:
                continue
            q = self._pending.pop(m.get('id'), None)
            if q:
                q.put(m)

    def _read_err(self):
        for line in self.proc.stderr:
            self.stderr.append(line.rstrip())

    def rpc(self, method, params=None, timeout=60):
        with self._lock:
            self._ids += 1
            i = self._ids
        q = queue.Queue()
        self._pending[i] = q
        self.proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': i, 'method': method, 'params': params or {}}, ensure_ascii=False) + '\n')
        self.proc.stdin.flush()
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            raise AssertionError(f'обёртка моста не ответила на {method} за {timeout} с; stderr: {self.stderr[-5:]}')

    def raw(self, text):
        """Строка прямо в stdin обёртки (для проверки разбора ввода)."""
        self.proc.stdin.write(text + '\n')
        self.proc.stdin.flush()

    def call(self, name, args=None, timeout=60):
        """Результат tools/call как есть: {content, structuredContent} или {isError, content}."""
        return self.rpc('tools/call', {'name': name, 'arguments': args or {}}, timeout)['result']

    def tool(self, name, args=None, timeout=60):
        r = self.call(name, args, timeout)
        if r.get('isError'):
            raise BridgeError(r['content'][0]['text'])
        return r['structuredContent']

    def tools(self):
        return self.rpc('tools/list')['result']['tools']

    def token(self):
        with open(os.path.join(self.dir, 'token'), encoding='utf-8') as f:
            return f.read().strip()

    def health(self):
        try:
            code, body = http(self.port, 'GET', '/health', timeout=1)
            return body if code == 200 else None
        except OSError:
            return None

    def ws(self, origin=EXT_ORIGIN, path='/ext', hello='1.5.0'):
        """Подключение «загрузчика»; hello — версия в приветствии (None — не здороваться)."""
        c = WsClient(self.port, origin, path)
        self._ws.append(c)
        if hello and c.status == 101:
            c.send({'t': 'hello', 'version': hello})
        return c

    def close_app(self):
        """Приложение Claude закрыли: обёртка завершается, ядро остаётся."""
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.stdin.close()
            except OSError:
                pass
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def shutdown_core(self, wait=True):
        try:
            http(self.port, 'POST', '/shutdown', {}, {'x-qa-pro-bridge-token': self.token()}, timeout=2)
        except (OSError, ValueError, FileNotFoundError):
            pass
        if wait:
            end = time.time() + 5
            while time.time() < end and self.health():
                time.sleep(0.05)

    def stop(self):
        for c in self._ws:
            c.close()
        self.close_app()
        pid = (self.health() or {}).get('pid')
        self.shutdown_core()
        if self.health() and pid:
            try:
                os.kill(pid, 9)
            except OSError:
                pass
