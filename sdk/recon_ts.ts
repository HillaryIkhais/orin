// Recon TypeScript SDK
export class Recon {
  constructor(private baseUrl: string) {}
  private async post(path: string, body: unknown) {
    const r = await fetch(this.baseUrl + path, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    return r.json();
  }
  record(fact_id: string, value: unknown, extra: Record<string, unknown> = {}) {
    return this.post("/observations", { fact_id, value, ...extra });
  }
  decide(decision_id: string, objective: string, dependencies: string[], scope = {}) {
    return this.post("/decisions", { decision_id, objective, dependencies, scope });
  }
  revalidate(decision_id: string) {
    return this.post("/revalidate", { decision_id });
  }
  authorize(decision_id: string, action_id: string, action = {}) {
    return this.post("/authorize", { decision_id, action_id, action });
  }
}
