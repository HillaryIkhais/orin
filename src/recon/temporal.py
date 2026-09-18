import time
from .store import STORE, h


def now():
    return time.time()


def record(fact_id, value, valid_until=None, source="api", valid_from=None):
    ch = h(value)
    with STORE.lock:
        prev = STORE.obs.get(fact_id)
        if prev and ch == prev["content_hash"] and value == prev["value"]:
            d = dict(prev)
            d["note"] = "duplicate"
            return d
        v = (prev["version"] + 1) if prev else 1
        rec = {"fact_id": fact_id, "value": value, "observed_at": now(),
               "valid_from": valid_from or now(), "valid_until": valid_until,
               "source": source, "version": v, "content_hash": ch}
        STORE.obs[fact_id] = rec
        STORE.bump()
        return rec


def create_decision(decision_id, objective, dependencies, scope=None, validity_window=None):
    dh = h([objective, sorted(dependencies), scope])
    with STORE.lock:
        STORE.dec[decision_id] = {"decision_id": decision_id, "objective": objective,
                                  "dependencies": list(dependencies), "scope": scope or {},
                                  "validity_window": validity_window, "created_at": now(),
                                  "decision_hash": dh}
        STORE.bump()
        return dict(STORE.dec[decision_id])


def _obs_status(o):
    t = now()
    if o.get("valid_until") and t > o["valid_until"]:
        return ("EXPIRED", "TEMPORAL_EXPIRY")
    if o.get("valid_from") and t < o["valid_from"]:
        return ("NOT_YET", "NOT_YET_VALID")
    v = o.get("value")
    if isinstance(v, str) and v.upper() in ("EXPIRED", "REVOKED", "INVALID", "UNKNOWN"):
        return ("BAD", "RECHECK_REQUIRED" if v.upper() == "UNKNOWN" else "VALUE_INVALIDATED")
    if isinstance(v, dict):
        s = str(v.get("status", "")).upper()
        if s in ("EXPIRED", "REVOKED", "INVALID"):
            return ("BAD", "VALUE_INVALIDATED")
        if s == "UNKNOWN":
            return ("BAD", "RECHECK_REQUIRED")
    return ("OK", "OK")


def revalidate(decision_id):
    with STORE.lock:
        d = STORE.dec.get(decision_id)
        if not d:
            return {"decision_id": decision_id, "verdict": "UNKNOWN", "reason": "NO_SUCH_DECISION"}
        causes, recheck = [], []
        for dep in d["dependencies"]:
            o = STORE.obs.get(dep)
            if o is None:
                return {"decision_id": decision_id, "verdict": "UNKNOWN",
                        "reason": "MISSING_DEPENDENCY", "missing": dep, "affected_actions": []}
            st, why = _obs_status(o)
            if st != "OK":
                (causes if why != "RECHECK_REQUIRED" else recheck).append(
                    {"fact": dep, "why": why, "value": o["value"], "version": o["version"]})
        vw = d.get("validity_window")
        if vw and now() > vw:
            return {"decision_id": decision_id, "verdict": "INVALIDATED",
                    "reason": "DECISION_WINDOW_EXPIRED", "causes": [], "state_version": STORE.version}
        if causes:
            return {"decision_id": decision_id, "verdict": "INVALIDATED",
                    "reason": "EVIDENCE_INVALIDATED", "causes": causes,
                    "affected_actions": [decision_id + ":*"], "state_version": STORE.version}
        if recheck:
            return {"decision_id": decision_id, "verdict": "RECHECK_REQUIRED",
                    "reason": "AMBIGUOUS_EVIDENCE", "causes": recheck, "state_version": STORE.version}
        return {"decision_id": decision_id, "verdict": "VALID",
                "reason": "ALL_EVIDENCE_CURRENT", "state_version": STORE.version}


def _scope_ok(dec, action):
    sc = dec.get("scope") or {}
    for k, lim in sc.items():
        if k in action:
            try:
                if float(action[k]) > float(lim):
                    return False
            except Exception:
                if action[k] != lim:
                    return False
    return True


def authorize(decision_id, action_id, action=None):
    action = action or {}
    v = revalidate(decision_id)
    sv = v.get("state_version")
    with STORE.lock:
        if sv != STORE.version:
            return {"allowed": False, "verdict": "BLOCK", "reason": "RACE_STATE_CHANGED",
                    "action_id": action_id}
        d = STORE.dec.get(decision_id)
        if v["verdict"] != "VALID":
            return {"allowed": False, "verdict": "BLOCK", "reason": "DECISION_" + v["verdict"],
                    "detail": v, "action_id": action_id}
        if not _scope_ok(d, action):
            return {"allowed": False, "verdict": "BLOCK", "reason": "SCOPE_EXPANSION",
                    "action_id": action_id}
        if action.get("objective") and action["objective"] != d["objective"]:
            return {"allowed": False, "verdict": "BLOCK", "reason": "OBJECTIVE_CHANGED",
                    "action_id": action_id}
        return {"allowed": True, "verdict": "ALLOW", "reason": "DECISION_VALID",
                "action_id": action_id, "state_version": sv}


def impact(fact_id):
    with STORE.lock:
        aff = [did for did, d in STORE.dec.items() if fact_id in d["dependencies"]]
        return {"fact_id": fact_id, "affected_decisions": aff}


def receipt(decision_id):
    v = revalidate(decision_id)
    with STORE.lock:
        d = dict(STORE.dec.get(decision_id, {}))
        ev = {dep: STORE.obs.get(dep) for dep in d.get("dependencies", [])}
        return {"RECON_RECEIPT": True, "decision": d, "verdict": v, "evidence": ev}
