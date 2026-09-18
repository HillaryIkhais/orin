"""Structural diff: added / removed / modified with unified context."""
import difflib, json

def _s(v) -> str:
    return v if isinstance(v, str) else json.dumps(v, default=str, sort_keys=True)

def structural_diff(prev: dict, curr: dict) -> list:
    changes = []
    for k in sorted(set(curr) - set(prev)):
        changes.append({"key": k, "type": "added", "after": curr[k], "before": None})
    for k in sorted(set(prev) - set(curr)):
        changes.append({"key": k, "type": "removed", "before": prev[k], "after": None})
    for k in sorted(set(prev) & set(curr)):
        a, b = _s(prev[k]), _s(curr[k])
        if a != b:
            udiff = list(difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm=""))
            changes.append({"key": k, "type": "modified", "before": prev[k], "after": curr[k],
                            "unified_diff": udiff[:50]})
    return changes

import csv, io

def normalize_records(source_type: str, payload) -> dict:
    st = (source_type or "json").lower()
    if st in ("json", "api", "db", "csv_snapshot", "database"):
        if isinstance(payload, dict):
            return {str(k): v for k, v in payload.items()}
        if isinstance(payload, list):
            out = {}
            for i, item in enumerate(payload):
                if isinstance(item, dict) and "id" in item:
                    out[str(item["id"])] = item
                else:
                    out[str(i)] = item
            return out
        if isinstance(payload, str):
            try:
                import json as _j
                return normalize_records("json", _j.loads(payload))
            except Exception:
                return {"content": payload}
        return {"value": payload}
    if st == "csv":
        text = payload if isinstance(payload, str) else ""
        rows = list(csv.DictReader(io.StringIO(text)))
        out = {}
        for i, r in enumerate(rows):
            key = r.get("id") or r.get("key") or r.get("path") or str(i)
            out[str(key)] = r
        return out
    if st in ("files", "github", "repo"):
        if isinstance(payload, dict):
            return {str(k): v for k, v in payload.items()}
        if isinstance(payload, list):
            return {str(x.get("path", i)): x.get("content", x) for i, x in enumerate(payload)}
        return {"content": str(payload)}
    if st in ("web", "text", "page"):
        import json as _j
        text = payload if isinstance(payload, str) else _j.dumps(payload)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return {"line_%d" % i: l for i, l in enumerate(lines)}
    import json as _j
    return {"content": payload if isinstance(payload, str) else _j.dumps(payload, default=str)}
