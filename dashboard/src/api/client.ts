import type { Agent, Blast, ChangeVerdict, Control, Graph, Portfolio, Result, Route, Trial, Twin } from "../types";

const BASE = "/api";

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(BASE + path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`);
  return r.json();
}
const post = <T,>(path: string, body: unknown) => call<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  scenarios: () => call<{ scenarios: { id: string; name: string }[]; current: string; current_scenario: string }>("/scenarios"),
  load: (name: string) => post<Twin>(`/scenarios/${name}/load`, {}),
  twin: (id: string) => call<Twin>(`/twin/${id}`),
  clone: (twin_id: string, control_ids: string[], label: string) => post<Twin>(`/twin/${twin_id}/clone`, { control_ids, label }),
  graph: (id: string) => call<Graph>(`/graph/${id}`),
  agents: () => call<Agent[]>("/agents"),
  paths: (id: string, agent_id: string) => call<{ naive_count: number; count: number; routes: Route[] }>(`/paths/${id}?agent_id=${agent_id}`),
  controls: (id: string) => call<{ applied: Control[]; catalogue: Control[] }>(`/controls/${id}`),
  simulate: (twin_id: string, agent_id: string, n = 1000, seed = 1) => post<Result>("/simulate", { twin_id, agent_id, n, seed }),
  evaluate: (twin_id: string, control_ids: string[], agent_ids: string[], seed = 1) =>
    post<ChangeVerdict>("/evaluate-change", { twin_id, control_ids, agent_ids, seed }),
  optimize: (twin_id: string, budget: number, agent_ids: string[]) => post<Portfolio>("/optimize", { twin_id, budget, agent_ids }),
  blast: (twin_id: string, asset_id: string) => call<Blast>(`/blast-radius/${twin_id}/${asset_id}`),
  trace: (twin_id: string, agent_id: string, control_ids: string[], k = 12, seed = 1) =>
    post<Trial[]>("/trace", { twin_id, agent_id, control_ids, k, seed }),
};
