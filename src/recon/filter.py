"""Task-conditioned relevance ('change budget'): keep only changes that could alter the agent's task."""
import json, re
from .semantics import impact_score

STOP = set("the a an is are was were be to of in on for with and or will would could should tell me whether what which check this that it my your our their his her its".split())

def _tokens(s: str) -> set:
    return {t for t in re.findall(r"[a-z0-9_.\-/]{2,}", (s or "").lower()) if t not in STOP}

def task_relevance(changes: list, objective: str, sensitivity: str = "medium") -> list:
    obj_tok = _tokens(objective or "")
    threshold = {"low": 3.0, "medium": 1.5, "high": 0.5}.get((sensitivity or "medium").lower(), 1.5)
    scored = []
    for c in changes:
        blob = c.get("key", "") + " " + json.dumps({"b": c.get("before"), "a": c.get("after"),
                                                     "cat": c.get("category")}, default=str)
        tok = _tokens(blob)
        overlap = len(obj_tok & tok)
        # boost: HIGH-impact always more relevant; exact file-path token match counts double
        score = overlap + 0.5 * impact_score(c)
        if obj_tok and any(t in blob.lower() for t in obj_tok if len(t) > 4):
            score += 0.5
        c2 = dict(c)
        c2["relevance"] = round(score, 2)
        c2["relevant"] = (score >= threshold) if obj_tok else (impact_score(c) >= 2)
        scored.append(c2)
    scored.sort(key=lambda c: (-c["relevance"], -impact_score(c)))
    return scored
