# RECON invariants

- **I1 — No-valid-decision, no-action:** `authorize(action) => decision.verdict = VALID`, else BLOCK.
- **I2 — Evidence integrity:** observations carry `content_hash`; duplicates detected, replay of older versions bumps version forward (never silently valid).
- **I3 — Temporal validity:** `now > valid_until => INVALIDATED`.
- **I4 — Dependency integrity:** decision valid only if EVERY required dependency valid.
- **I5 — Non-expanding consequence:** `action.scope ⊆ decision.scope`, else SCOPE_EXPANSION block.
- **I6 — Fail closed:** `UNKNOWN != VALID`; missing/ambiguous evidence blocks.
- **I7 — Race safety:** authorize compares `state_version` at revalidation vs execution; mismatch => BLOCK/RACE_STATE_CHANGED.
- **I8 — Deterministic verdict:** same evidence + state + objective => same verdict. No LLM in the verdict path.
