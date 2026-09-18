import hashlib, json, threading

def h(v):
    return hashlib.sha256(json.dumps(v, default=str, sort_keys=True).encode()).hexdigest()[:16]

class Store:
    def __init__(self):
        self.lock = threading.Lock()
        self.obs = {}
        self.dec = {}
        self.version = 0

    def bump(self):
        self.version += 1
        return self.version

    def reset(self):
        with self.lock:
            self.obs = {}
            self.dec = {}
            self.version = 0

STORE = Store()
