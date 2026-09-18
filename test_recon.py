from fastapi.testclient import TestClient
from server import app
c = TestClient(app)

def test_killer_demo_checkout():
    prev = {"checkout/payment.ts": "retry(3)", "package.json": "stripe@12", "README.md": "hello",
            "styles.css": "blue", "about.ts": "x=1", "docs/a.md": "a"}
    curr = {"checkout/payment.ts": "retry(1)", "package.json": "stripe@14", "README.md": "hello world",
            "styles.css": "red", "about.ts": "x=1", "docs/a.md": "a"}
    r = c.post("/inspect", json={"source": "files", "previous": prev, "current": curr,
                                 "objective": "Check whether this release could break checkout",
                                 "sensitivity": "medium"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["total_changes"] == 4, d
    keys = [x["key"] for x in d["important_changes"]]
    assert "checkout/payment.ts" in keys and "package.json" in keys, d
    assert d["ignored_count"] >= 1
    assert any("payment" in a for a in d["suggested_agent_actions"]), d

def test_mcp_tools_call():
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert "recon.inspect" in str(r.json())
    r = c.post("/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                             "params": {"name": "recon.inspect",
                                        "arguments": {"source": "json",
                                                      "previous": {"leads": [{"id": "1", "risk": "low"}]},
                                                      "current": {"leads": [{"id": "1", "risk": "high"}]},
                                                      "objective": "which leads became risky"}}})
    assert r.status_code == 200 and "structuredContent" in str(r.json()), r.text
