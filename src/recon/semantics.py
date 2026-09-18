"""Rule-based semantic classifier + impact scorer. No LLM needed (offline-validatable)."""
import json, re

HIGH = [r"auth", r"login", r"password", r"token", r"payment", r"checkout", r"charge",
        r"refund", r"stripe", r"retry", r"middleware", r"permission", r"secret", r"crypto",
        r"transfer", r"withdraw", r"billing"]
MEDIUM = [r"dependenc", r"package\.json", r"requirements", r"sdk", r"version", r"upgrade",
          r"migration", r"schema", r"config", r"endpoint", r"api", r"database", r"query"]
LOW = [r"copy", r"typo", r"comment", r"readme", r"\.css", r"style", r"font", r"logo", r"i18n"]

def _blob(c) -> str:
    return (c.get("key", "") + " " + json.dumps({"b": c.get("before"), "a": c.get("after")}, default=str)).lower()

def classify_change(change: dict) -> dict:
    blob = _blob(change)
    if any(re.search(p, blob) for p in HIGH):
        cat, impact = "behavior/auth/payment", "HIGH"
    elif any(re.search(p, blob) for p in MEDIUM):
        cat, impact = "dependency/config/schema", "MEDIUM"
    elif change["type"] in ("added", "removed"):
        cat, impact = "structural", "MEDIUM"
    elif any(re.search(p, blob) for p in LOW):
        cat, impact = "cosmetic/copy", "LOW"
    else:
        # size heuristic: big text churn without keywords = medium
        before = json.dumps(change.get("before"), default=str)
        cat, impact = ("content", "MEDIUM") if abs(len(json.dumps(change.get("after"), default=str)) - len(before)) > 500 else ("content", "LOW")
    change = dict(change)
    change.update({"category": cat, "impact": impact})
    return change

def impact_score(change: dict) -> int:
    return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(change.get("impact", "LOW"), 1)
