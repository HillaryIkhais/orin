# RECON — temporal integrity layer for AI agents

> **AI agents remember what they knew. They don't know when that knowledge stops being valid.**

RECON tracks the evidence behind decisions and **blocks consequential actions when that evidence becomes invalid**.

```
WORLD CHANGES -> EVIDENCE INVALIDATED -> DECISION REVALIDATED -> ACTION BLOCKED
```

**Invariant: no valid decision → no consequential action.** A decision is permission to act only while the evidence that justified it remains true.

## The gate (the product)

| Call | Result |
|---|---|
| `POST /observations` (`recon.record`) | authoritative fact + `valid_until` + `content_hash` + version |
| `POST /decisions` | decision + objective + dependencies + scope |
| `POST /revalidate` (`recon.revalidate`) | `VALID / INVALIDATED / RECHECK_REQUIRED / UNKNOWN` + causes |
| `POST /authorize` (`recon.authorize`) | `ALLOW / BLOCK` + reason — the money shot |
| `GET /decisions/:id/receipt`, `GET /impact/:id` | evidence receipt, blast radius |
| `POST /inspect` (`recon.inspect`) | task-conditioned semantic diff (v1 capability, kept) |
| `POST /mcp` | JSON-RPC `tools/list` + `tools/call` for all of the above |

Verdicts are **repeatable (no LLM judge)** — no LLM in the verdict path (I8). Unknown fails closed (I6).

## Demo (60 seconds)

1. Record cert/insurance valid → decision D-104 VALID → payment A-772 ALLOWED.
2. Mutate `cert:ABC` → EXPIRED → D-104 INVALIDATED → payment BLOCKED with cause.
3. `GET /decisions/D-104/receipt` shows the exact causal chain.

Run: `pip install -r requirements.txt && uvicorn server:app --port 8000`, then `./verification/smoke-test.sh` or `python3 -m pytest -q` (12 tests: gate, 10-attack lab coverage, 300-case fuzz).

SDKs: `sdk/recon_py.py`, `sdk/recon_ts.ts`. Invariants: `docs/invariants.md`.
