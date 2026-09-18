"""Core engine: snapshot -> structural diff -> semantic diff -> impact -> MCP result."""
from .diff import structural_diff, normalize_records
from .semantics import classify_change
from .filter import task_relevance

def _summary_text(key, c) -> str:
    b, a = str(c.get("before"))[:160], str(c.get("after"))[:160]
    if c["type"] == "added": return f"{key} added: {a}"
    if c["type"] == "removed": return f"{key} removed (was: {b})"
    return f"{key} changed: {b} → {a}"

def _suggest(changes) -> list:
    out = []
    blob = " ".join(c.get("key", "") for c in changes).lower()
    if any(k in blob for k in ("payment", "checkout", "stripe", "retry")):
        out.append("re-run payment/checkout tests")
    if any(k in blob for k in ("auth", "login", "token", "middleware")):
        out.append("inspect auth middleware + re-run auth tests")
    if any(k in blob for k in ("package.json", "requirements", "sdk", "dependenc")):
        out.append("verify dependency upgrade changelog + lockfile")
    if not out and changes:
        out.append("review listed changes + re-run affected tests")
    return out

def inspect(source: str, previous, current, objective: str = "", sensitivity: str = "medium") -> dict:
    prev = normalize_records(source, previous)
    curr = normalize_records(source, current)
    structural = structural_diff(prev, curr)
    semantic = [classify_change(c) for c in structural]
    ranked = task_relevance(semantic, objective, sensitivity)
    relevant = [c for c in ranked if c["relevant"]]
    ignored = len(ranked) - len(relevant)
    important = [{
        "key": c["key"], "type": c["type"], "impact": c["impact"],
        "category": c["category"], "relevance": c["relevance"],
        "summary": _summary_text(c["key"], c),
        "diff": c.get("unified_diff", [])[:10],
    } for c in relevant]
    return {
        "source": source,
        "objective": objective,
        "total_changes": len(ranked),
        "relevant_count": len(relevant),
        "ignored_count": ignored,
        "important_changes": important,
        "suggested_agent_actions": _suggest(relevant),
        "all_changes": [{"key": c["key"], "type": c["type"], "impact": c["impact"],
                         "category": c["category"], "relevance": c["relevance"]} for c in ranked],
    }
