"""RECON 3.0 gate + attack lab tests. Deterministic verdicts, fail-closed."""
import time
from fastapi.testclient import TestClient
from server import app
from src.recon.store import STORE
from src.recon import temporal as T

c = TestClient(app)

def setup_function(_):
    STORE.reset()

def vendor_flow():
    T.record("cert:ABC", "valid")
    T.record("ins:ABC", "valid")
    T.record("price:ABC", {"amount": 8400})
    T.create_decision("D-104", "approve vendor ABC", ["cert:ABC", "ins:ABC", "price:ABC"],
                      scope={"amount": 10000})

def test_happy_path_allow_then_block():
    vendor_flow()
    assert T.revalidate("D-104")["verdict"] == "VALID"
    assert T.authorize("D-104", "A-772", {"amount": 8400})["verdict"] == "ALLOW"
    T.record("cert:ABC", "EXPIRED")  # world changes
    v = T.revalidate("D-104")
    assert v["verdict"] == "INVALIDATED", v
    a = T.authorize("D-104", "A-772", {"amount": 8400})
    assert a["allowed"] is False and a["verdict"] == "BLOCK", a

def test_irrelevant_change_stays_valid():
    vendor_flow()
    T.record("vendor.phone", "+234-000")
    assert T.revalidate("D-104")["verdict"] == "VALID"

def test_ambiguous_requires_recheck():
    vendor_flow()
    T.record("cert:ABC", "UNKNOWN")
    assert T.revalidate("D-104")["verdict"] == "RECHECK_REQUIRED"

def test_expiry_invalidates():
    T.record("cert:ABC", "valid", valid_until=time.time() - 1)
    T.create_decision("D-1", "x", ["cert:ABC"])
    assert T.revalidate("D-1")["verdict"] == "INVALIDATED"

def test_missing_dependency_unknown_not_valid():
    T.create_decision("D-2", "x", ["ghost:fact"])
    v = T.revalidate("D-2")
    assert v["verdict"] == "UNKNOWN"
    assert T.authorize("D-2", "A-1")["allowed"] is False  # fail closed I6

def test_scope_non_expanding():
    vendor_flow()
    a = T.authorize("D-104", "A-9", {"amount": 50000})
    assert a["reason"] == "SCOPE_EXPANSION" and not a["allowed"]

def test_objective_change_blocked():
    vendor_flow()
    a = T.authorize("D-104", "A-9", {"amount": 100, "objective": "buy fastest delivery"})
    assert a["reason"] == "OBJECTIVE_CHANGED"

def test_cascade_blocks_downstream():
    T.record("F1", "valid")
    T.create_decision("D1", "o", ["F1"])
    T.record("F1", "EXPIRED")
    assert T.revalidate("D1")["verdict"] == "INVALIDATED"
    assert T.authorize("D1", "A1")["allowed"] is False

def test_api_end_to_end():
    c.post("/reset")
    c.post("/observations", json={"fact_id": "cert:ABC", "value": "valid"})
    c.post("/observations", json={"fact_id": "ins:ABC", "value": "valid"})
    c.post("/decisions", json={"decision_id": "D-104", "objective": "approve",
                               "dependencies": ["cert:ABC", "ins:ABC"]})
    assert c.post("/authorize", json={"decision_id": "D-104", "action_id": "A-1"}).json()["verdict"] == "ALLOW"
    c.post("/observations", json={"fact_id": "cert:ABC", "value": "EXPIRED"})
    r = c.post("/authorize", json={"decision_id": "D-104", "action_id": "A-1"}).json()
    assert r["verdict"] == "BLOCK"
    assert "RECON_RECEIPT" in str(c.get("/decisions/D-104/receipt").json())

def test_fuzz_no_valid_on_bad_evidence():
    import random
    random.seed(7)
    bad = 0
    for i in range(300):
        STORE.reset()
        T.record("F", random.choice(["valid", "EXPIRED", "UNKNOWN", {"status": "REVOKED"}]))
        T.create_decision("D", "o", ["F"])
        v = T.revalidate("D")["verdict"]
        a = T.authorize("D", "A")
        if v in ("INVALIDATED", "RECHECK_REQUIRED", "UNKNOWN"):
            assert not a["allowed"], (v, a)
            bad += 1
    assert bad > 100  # invariant I1 held every time
