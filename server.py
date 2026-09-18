"""RECON 3.0 — temporal integrity layer. No valid decision -> no consequential action."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Any, Optional
from src.recon.engine import inspect as recon_inspect
from src.recon import temporal as T
from src.recon.store import STORE

app = FastAPI(title="RECON — temporal integrity for AI agents", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---- v1 inspect (kept) ----
class InspectRequest(BaseModel):
    source: str = "json"
    previous: Any = None
    current: Any = None
    objective: str = ""
    sensitivity: str = "medium"

@app.get("/health")
def health():
    return {"status": "ok", "service": "recon", "version": "3.0.0"}

@app.post("/inspect")
def inspect(req: InspectRequest):
    return recon_inspect(req.source, req.previous, req.current, req.objective, req.sensitivity)

# ---- temporal gate ----
class ObsIn(BaseModel):
    fact_id: str
    value: Any
    valid_until: Optional[float] = None
    valid_from: Optional[float] = None
    source: str = "api"

class DecIn(BaseModel):
    decision_id: str
    objective: str
    dependencies: list = []
    scope: dict = {}
    validity_window: Optional[float] = None

class AuthIn(BaseModel):
    decision_id: str
    action_id: str
    action: dict = {}

@app.post("/observations")
def post_obs(o: ObsIn):
    return T.record(o.fact_id, o.value, o.valid_until, o.source, o.valid_from)

@app.post("/decisions")
def post_dec(d: DecIn):
    return T.create_decision(d.decision_id, d.objective, d.dependencies, d.scope, d.validity_window)

@app.post("/revalidate")
def post_reval(b: dict):
    # recon.revalidate
    return T.revalidate(b.get("decision_id", ""))

@app.post("/authorize")
def post_auth(a: AuthIn):
    # recon.authorize — the money shot: ALLOW / BLOCK
    return T.authorize(a.decision_id, a.action_id, a.action)

@app.get("/decisions/{did}")
def get_dec(did: str):
    return T.revalidate(did)

@app.get("/decisions/{did}/receipt")
def get_receipt(did: str):
    return T.receipt(did)

@app.get("/impact/{fact_id}")
def get_impact(fact_id: str):
    return T.impact(fact_id)

@app.post("/reset")
def reset():
    STORE.reset()
    return {"reset": True}

# ---- MCP ----
def _call_tool(name: str, args: dict):
    if name in ("recon.inspect", "recon_inspect"):
        return recon_inspect(args.get("source", "json"), args.get("previous"),
                             args.get("current"), args.get("objective", ""),
                             args.get("sensitivity", "medium"))
    if name in ("recon.record", "recon_record"):
        return T.record(args["fact_id"], args.get("value"),
                        args.get("valid_until"), args.get("source", "api"), args.get("valid_from"))
    if name in ("recon.revalidate", "recon_revalidate"):
        return T.revalidate(args.get("decision_id", ""))
    if name in ("recon.authorize", "recon_authorize"):
        return T.authorize(args.get("decision_id", ""), args.get("action_id", ""), args.get("action", {}))
    if name in ("recon.impact", "recon_impact"):
        return T.impact(args.get("fact_id", ""))
    return {"error": "unknown tool " + name}

TOOLS = [
    {"name": "recon.authorize",
     "description": "Verify an agent decision is still justified before allowing consequential action. Returns ALLOW or BLOCK with reason.",
     "inputSchema": {"type": "object", "properties": {"decision_id": {"type": "string"}, "action_id": {"type": "string"}, "action": {"type": "object"}}, "required": ["decision_id", "action_id"]}},
    {"name": "recon.revalidate",
     "description": "Revalidate a decision against current evidence. Returns VALID, INVALIDATED, RECHECK_REQUIRED or UNKNOWN.",
     "inputSchema": {"type": "object", "properties": {"decision_id": {"type": "string"}}, "required": ["decision_id"]}},
    {"name": "recon.record",
     "description": "Record an authoritative observation with temporal validity and content hash.",
     "inputSchema": {"type": "object", "properties": {"fact_id": {"type": "string"}, "value": {}}, "required": ["fact_id", "value"]}},
    {"name": "recon.impact",
     "description": "List decisions affected by a fact change.",
     "inputSchema": {"type": "object", "properties": {"fact_id": {"type": "string"}}, "required": ["fact_id"]}},
    {"name": "recon.inspect",
     "description": "Task-conditioned semantic change detection. Returns WHAT CHANGED, WHY IT MATTERS, WHAT TO RECHECK.",
     "inputSchema": {"type": "object", "properties": {"source": {"type": "string"}, "previous": {}, "current": {}, "objective": {"type": "string"}, "sensitivity": {"type": "string"}}, "required": ["previous", "current"]}},
]

@app.post("/mcp")
def mcp(body: dict):
    method = body.get("method", "")
    bid = body.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": bid,
                "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}},
                           "serverInfo": {"name": "recon", "version": "3.0.0"}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": bid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        p = body.get("params", {})
        args = p.get("arguments", {}) if "arguments" in p else p
        name = p.get("name", "recon.inspect")
        result = _call_tool(name, args)
        if isinstance(result, dict) and result.get("error"):
            return {"jsonrpc": "2.0", "id": bid, "error": {"code": -32602, "message": result["error"]}}
        return {"jsonrpc": "2.0", "id": bid, "result": {"content": [{"type": "text", "text": str(result)}], "structuredContent": result}}
    return {"jsonrpc": "2.0", "id": bid, "error": {"code": -32601, "message": "unknown method " + method}}

@app.get("/.well-known/mcp")
def mcp_wellknown():
    return {"name": "recon", "endpoint": "/mcp", "tools": TOOLS}
