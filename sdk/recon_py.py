"""Recon Python SDK — tiny wrapper over the online API."""
import urllib.request, json

class Recon:
    def __init__(self, base_url):
        self.base = base_url.rstrip("/")

    def _post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        return json.load(urllib.request.urlopen(req))

    def record(self, fact_id, value, **kw):
        return self._post("/observations", {"fact_id": fact_id, "value": value, **kw})

    def decide(self, decision_id, objective, dependencies, scope=None):
        return self._post("/decisions", {"decision_id": decision_id, "objective": objective,
                                         "dependencies": dependencies, "scope": scope or {}})

    def revalidate(self, decision_id):
        return self._post("/revalidate", {"decision_id": decision_id})

    def authorize(self, decision_id, action_id, action=None):
        return self._post("/authorize", {"decision_id": decision_id, "action_id": action_id,
                                         "action": action or {}})
