import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import type { Agent, Blast, ChangeVerdict, Control, Graph, Result, Route } from "./types";
import { DecisionCard } from "./views/DecisionCard";
import { GraphView } from "./views/GraphView";
import { EffortChart } from "./views/EffortChart";
import { OptimizerPanel } from "./views/OptimizerPanel";

export default function App() {
  const [twinId, setTwinId] = useState("current");
  const [scenario, setScenario] = useState("golden");
  const [graph, setGraph] = useState<Graph | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentId, setAgentId] = useState("external");
  const [catalogue, setCatalogue] = useState<Control[]>([]);
  const [picked, setPicked] = useState<string[]>([]);
  const [baseline, setBaseline] = useState<Result | null>(null);
  const [paths, setPaths] = useState<{ naive_count: number; count: number; routes: Route[] } | null>(null);
  const [prevRisk, setPrevRisk] = useState<number | null>(null);
  const [verdict, setVerdict] = useState<ChangeVerdict | null>(null);
  const [route, setRoute] = useState<Route | null>(null);
  const [blast, setBlast] = useState<Blast | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async (id: string, agent: string) => {
    const [g, c, b, p] = await Promise.all([api.graph(id), api.controls(id), api.simulate(id, agent), api.paths(id, agent)]);
    setGraph(g); setCatalogue(c.catalogue); setBaseline(b); setPaths(p); setTwinId(g.twin_id);
  }, []);

  useEffect(() => {
    (async () => {
      try { setAgents(await api.agents()); await refresh("current", agentId); } catch (e) { setError(String(e)); }
    })();
  }, []); // eslint-disable-line

  useEffect(() => {
    if (!picked.length) { setVerdict(null); setRoute(null); return; }
    let live = true;
    api.evaluate(twinId, picked, [agentId]).then((v) => { if (live) { setVerdict(v); setRoute(v.delta.substituted_paths[0] ?? null); setBlast(null); } })
      .catch((e) => setError(String(e)));
    return () => { live = false; };
  }, [picked, twinId, agentId]);

  const toggle = (id: string) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));

  const loadScenario = async (name: string) => {
    setPrevRisk(baseline?.weighted_risk ?? null);
    await api.load(name);
    setScenario(name); setPicked([]); setVerdict(null); setRoute(null); setBlast(null);
    await refresh("current", agentId);
  };

  const selectAsset = async (id: string) => {
    const b = await api.blast(twinId, id);
    setBlast(b); setRoute(null);
  };

  const riskDelta = prevRisk !== null && baseline ? baseline.weighted_risk - prevRisk : null;

  return (
    <div className="mx-auto max-w-[1500px] p-5">
      <header className="mb-4 flex flex-wrap items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold">Security Change Sandbox</h1>
          <div className="text-xs text-slate-400">Propose a control. See the attacker's new route, the business flows you would sever, the cost, and how sure we are — before you deploy.</div>
        </div>
        <div className="ml-auto flex items-center gap-2 text-sm">
          <label className="text-slate-400">scenario</label>
          <select value={scenario} onChange={(e) => loadScenario(e.target.value)} className="rounded bg-slate-800 px-2 py-1">
            <option value="golden">FinBank (golden)</option>
            <option value="golden_sync">FinBank after sync (contractor admin on jump-01)</option>
          </select>
          <label className="ml-3 text-slate-400">adversary</label>
          <select value={agentId} onChange={(e) => { setAgentId(e.target.value); refresh(twinId, e.target.value); }} className="rounded bg-slate-800 px-2 py-1">
            {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
          <button onClick={() => loadScenario("golden")} className="ml-3 rounded border border-slate-600 px-2 py-1 text-xs hover:bg-slate-800">reset demo</button>
        </div>
      </header>

      {error && <div className="mb-3 rounded bg-red-900/60 p-2 text-sm">{error} — is uvicorn running on :8000?</div>}

      {baseline && (
        <div className="mb-4 flex flex-wrap gap-6 rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3 text-sm">
          <span>twin <span className="font-mono text-slate-400">{twinId.slice(0, 10)}</span></span>
          <span>critical paths to crown jewel: <b>{paths?.naive_count ?? "…"}</b></span>
          <span>p(success) <b>{baseline.p_success.toFixed(2)}</b> <span className="text-slate-500">[{baseline.p_success_ci[0].toFixed(2)}–{baseline.p_success_ci[1].toFixed(2)}]</span></span>
          <span>mean effort <b>{baseline.mean_effort?.toFixed(1) ?? "—"}</b></span>
          <span>weighted risk <b>{baseline.weighted_risk.toFixed(2)}</b>
            {riskDelta !== null && <span className={riskDelta > 0 ? "ml-1 text-red-300" : "ml-1 text-emerald-300"}>({riskDelta > 0 ? "+" : ""}{riskDelta.toFixed(2)} after sync)</span>}
          </span>
          <span className="text-slate-500">top route: {baseline.routes[0] ? `${baseline.routes[0].route.map((e) => e.technique).join(" › ")} (p_select ${baseline.routes[0].p_select.toFixed(2)})` : "none"}</span>
        </div>
      )}

      <div className="grid grid-cols-[280px_1fr] gap-4">
        <aside className="rounded-xl border border-slate-800 bg-slate-900 p-3">
          <div className="mb-2 text-xs uppercase tracking-widest text-slate-400">Propose controls</div>
          {catalogue.map((c) => (
            <label key={c.id} className={`mb-1 flex cursor-pointer items-start gap-2 rounded px-2 py-1 text-sm hover:bg-slate-800 ${picked.includes(c.id) ? "bg-slate-800" : ""}`}>
              <input type="checkbox" checked={picked.includes(c.id)} onChange={() => toggle(c.id)} className="mt-1" />
              <span><span className="font-medium">{c.name}</span><span className="block text-xs text-slate-500">{c.id} · cost {c.cost}</span></span>
            </label>
          ))}
          <button onClick={() => setPicked([])} className="mt-2 text-xs text-slate-400 hover:underline">clear</button>
        </aside>

        <main className="flex flex-col gap-4">
          <DecisionCard verdict={verdict} catalogue={catalogue} onPick={setPicked} onHighlight={setRoute} />
          <GraphView graph={graph} route={route} blast={blast} onSelectAsset={selectAsset} />
          {blast && (
            <div className="rounded-xl border border-slate-800 bg-slate-900 p-3 text-sm">
              <b>Blast radius of {blast.asset_id}</b>: with its sessions and credentials, an attacker reaches{" "}
              <span className="text-amber-300">{blast.reachable.join(", ") || "nothing"}</span>
              {blast.crown_jewels_hit.length > 0 && <span className="text-red-300"> — including crown jewel {blast.crown_jewels_hit.join(", ")}</span>}.
              <span className="text-slate-500"> Topological upper bound ignoring credentials: {blast.upper_bound.length} assets.</span>
            </div>
          )}
          <EffortChart before={verdict?.before ?? null} after={verdict?.after ?? null} />
          <OptimizerPanel catalogue={catalogue} run={(b) => api.optimize(twinId, b, agents.map((a) => a.id))} onPick={setPicked} />
        </main>
      </div>
    </div>
  );
}
