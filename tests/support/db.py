"""База артефакта в памяти: то, что в приложении приходит через window.claude.use('db'), здесь живёт в Python и переживает перезагрузку страницы."""
import time


class MemoryDB:
    def __init__(self):
        self.store = {}
        self.leases = {}

    # одна точка входа для window.__dbop(op, path, payload)
    def op(self, op, path, payload=None):
        if op == 'get':
            return self.store.get(path)
        if op == 'set':
            self.store[path] = payload
            return True
        if op == 'update':
            if path not in self.store:
                return 'missing'
            self.store[path] = {**self.store[path], **payload}
            return True
        if op == 'delete':
            self.store.pop(path, None)
            return True
        if op == 'list':
            rows = [[p, d] for p, d in self.store.items() if p.startswith(path + '/') and '/' not in p[len(path) + 1:]]
            for f, o, v in (payload or {}).get('filters', []):
                if o == '==':
                    rows = [r for r in rows if r[1].get(f) == v]
            ordr = (payload or {}).get('ord')
            if ordr:
                f, d = ordr
                rows.sort(key=lambda r: (r[1].get(f) is None, r[1].get(f) or 0), reverse=(d == 'desc'))
            return rows[:(payload or {}).get('lim') or 1000]
        if op == 'acquire':
            now = time.time()
            e = self.leases.get(path)
            if e and e[0] > now and e[1] != payload['holder']:
                return {'acquired': False}
            self.leases[path] = (now + (payload.get('ttlMs') or 30000) / 1000, payload['holder'])
            return {'acquired': True}
        raise ValueError('неизвестная операция базы: ' + str(op))

    # удобные чтения для проверок
    def get(self, path):
        return self.store.get(path)

    def children(self, path):
        return {p: d for p, d in self.store.items() if p.startswith(path + '/') and '/' not in p[len(path) + 1:]}

    def paths(self, prefix=''):
        return sorted(p for p in self.store if p.startswith(prefix))
