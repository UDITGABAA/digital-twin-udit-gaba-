import { useCallback, useEffect, useState } from "react";
import { RefreshCcw, ShieldHalf, CircleAlert } from "lucide-react";
import { api } from "./api/client";
import type { Agent, Blast, ChangeVerdict, Control, Graph, Result, Route, Trial } from "./types";
import { DecisionCard } from "./views/DecisionCard";
import { Stage, type ReplayState } from "./views/Stage";
import { Replay } from "./views/Replay";
import { EffortChart } from "./views/EffortChart";
import { OptimizerPanel } from "./views/OptimizerPanel";

type Paths = { naive_count: number; count: number; routes: Route[] };

export default function App() {
  const [twinId, setTwinId] = useState("current");
  const [scenario, setScenario] = useState("golden");
  const [graph, setGraph] = useState<Graph | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [agentId, setAgentId] = useState("external");
  const [catalogue, setCatalogue] = useState<Control[]>([]);
  const [picked, setPicked] = useState<string[]>([]);
  const [baseline, setBaseline] = useState<Result | null>(null);
  const [paths, setPaths] = useState<Paths | null>(null);
  const [prev, setPrev] = useState<{ p: number; risk: number } | null>(null);
  const [verdict, setVerdict] = useState<ChangeVerdict | null>(null);
  const [route, setRoute] = useState<Route | null>(null);
  const [blast, setBlast] = useState<Blast | null>(null);
  const [trials, setTrials] = useState<Trial[] | null>(null);
  const [replay, setReplay] = useState<ReplayState | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const agent = agents.find((a) => a.id === agentId) ?? null;

  const refresh = useCallback(async (id: string, ag: string) => {
    const [g, c, b, p] = await Promise.all([api.graph(id), api.controls(id), api.simulate(id, ag), api.paths(id, ag)]);
    setGraph(g); setCatalogue(c.catalogue); setBaseline(b); setPaths(p); setTwinId(g.twin_id); setError(null);
  }, []);

  useEffect(() => {
    (async () => { try { setAgents(await api.agents()); await refresh("current", agentId); } catch (e) { setError(String(e)); } })();
  }, []); // eslint-disable-line

  useEffect(() => {
    setTrials(null); setReplay(null);
    if (!picked.length) { setVerdict(null); setRoute(null); return; }
    let live = true;
    api.evaluate(twinId, picked, [agentId])
      .then((v) => { if (live) { setVerdict(v); setRoute(v.delta.substituted_paths[0] ?? null); setBlast(null); } })
      .catch((e) => setError(String(e)));
    return () => { live = false; };
  }, [picked, twinId, agentId]);

  const toggle = (id: string) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));

  const loadScenario = async (name: string, reset = false) => {
    setPrev(!reset && baseline ? { p: baseline.p_success, risk: baseline.weighted_risk } : null);
    await api.load(name);
    setScenario(name); setPicked([]); setVerdict(null); setRoute(null); setBlast(null); setTrials(null); setReplay(null);
    await refresh("current", agentId);
  };

  const runAttack = async () => {
    setRunning(true);
    try { setRoute(null); setBlast(null); setTrials(await api.trace(twinId, agentId, picked, 12)); }
    catch (e) { setError(String(e)); } finally { setRunning(false); }
  };

  const selectAsset = async (id: string) => { setBlast(await api.blast(twinId, id)); setRoute(null); setReplay(null); setTrials(null); };

  const pDelta = prev && baseline ? baseline.p_success - prev.p : null;
  const internetReached = blast?.reachable.some((a) => graph?.assets.find((x) => x.id === a)?.kind === "internet");

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-ink-700 bg-ink-950/85 backdrop-blur">
        <div className="mx-auto flex max-w-[1560px] flex-wrap items-center gap-x-6 gap-y-2 px-5 py-3">
          <div className="flex items-center gap-2.5">
            <ShieldHalf className="h-5 w-5 text-signal" />
            <div>
              <div className="text-[15px] font-semibold leading-none">Security Change Sandbox</div>
              <div className="mt-1 text-[11px] text-fg-faint">what can I deploy safely, within budget, and how sure are we</div>
            </div>
          </div>
          <div className="ml-auto flex items-center gap-2 text-sm">
            <label className="text-fg-faint">scenario</label>
            <select value={scenario} onChange={(e) => loadScenario(e.target.value)} className="rounded-md border border-ink-600 bg-ink-800 px-2 py-1.5">
              <option value="golden">FinBank</option>
              <option value="golden_sync">FinBank after sync — contractor admin on jump-01</option>
            </select>
            <label className="ml-2 text-fg-faint">adversary</label>
            <select value={agentId} onChange={(e) => { setAgentId(e.target.value); refresh(twinId, e.target.value); }} className="rounded-md border border-ink-600 bg-ink-800 px-2 py-1.5">
              {agents.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
            <button onClick={() => loadScenario("golden", true)} className="btn ml-2"><RefreshCcw className="h-3.5 w-3.5" />reset demo</button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[1560px] px-5 py-5">
        {error && <div className="mb-4 flex items-center gap-2 rounded-lg border border-block/50 bg-block/10 px-3 py-2 text-sm"><CircleAlert className="h-4 w-4 text-block" />{error} — is uvicorn running on :8000?</div>}

        {baseline && (
          <div className="mb-4 flex flex-wrap gap-x-8 gap-y-2 text-sm">
            <Stat label="critical paths to crown jewel" value={paths?.naive_count ?? "…"} />
            <Stat label="p(success)" value={baseline.p_success.toFixed(2)} sub={`${baseline.p_success_ci[0].toFixed(2)}–${baseline.p_success_ci[1].toFixed(2)}`}
              delta={pDelta !== null && pDelta !== 0 ? `${pDelta > 0 ? "+" : ""}${pDelta.toFixed(2)} since last twin` : undefined} bad={(pDelta ?? 0) > 0} />
            <Stat label="mean attacker effort" value={baseline.mean_effort?.toFixed(1) ?? "—"} />
            <Stat label="weighted risk" value={baseline.weighted_risk.toFixed(2)} />
            <Stat label="favourite route" value={baseline.routes[0] ? baseline.routes[0].route.map((e) => e.technique).join(" › ") : "none"} sub={baseline.routes[0] ? `p_select ${baseline.routes[0].p_select.toFixed(2)}` : undefined} mono />
            <span className="ml-auto self-end text-[11px] text-fg-faint">twin {twinId.slice(0, 10)} · seed 1 · 1,000 trials</span>
          </div>
        )}

        <div className="grid grid-cols-[264px_1fr] gap-4">
          <aside className="panel self-start p-3">
            <div className="label mb-2 px-1">Propose controls</div>
            <div className="space-y-0.5">
              {catalogue.map((c) => {
                const on = picked.includes(c.id);
                return (
                  <label key={c.id} className={`flex cursor-pointer items-start gap-2.5 rounded-lg px-2 py-1.5 text-sm transition-colors ${on ? "bg-ink-800 ring-1 ring-signal/50" : "hover:bg-ink-850"}`}>
                    <input type="checkbox" checked={on} onChange={() => toggle(c.id)} className="mt-1 accent-signal" />
                    <span className="min-w-0">
                      <span className="block font-medium leading-snug">{c.name}</span>
                      <span className="block text-[11px] text-fg-faint">{c.id} · cost {c.cost}</span>
                    </span>
                  </label>
                );
              })}
            </div>
            {picked.length > 0 && <button onClick={() => setPicked([])} className="mt-2 px-2 text-xs text-fg-muted hover:text-fg">clear selection</button>}
          </aside>

          <section className="flex min-w-0 flex-col gap-4">
            <div className="grid grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] gap-4">
              <DecisionCard verdict={verdict} catalogue={catalogue} onPick={setPicked} onHighlight={(r) => { setRoute(r); setTrials(null); setReplay(null); }} />
              <Replay trials={trials} noiseBudget={agent?.noise_budget ?? 3} running={running} onRun={runAttack} onState={setReplay}
                label={picked.length ? `${agent?.name ?? agentId} vs ${picked.map((id) => catalogue.find((c) => c.id === id)?.name ?? id).join(" + ")}` : `${agent?.name ?? agentId} against the current twin`} />
            </div>

            <Stage graph={graph} route={route} blast={blast} replay={replay} startZones={agent?.start_zones ?? []} onSelectAsset={selectAsset} />

            {blast && (
              <div className="panel px-4 py-3 text-sm">
                <span className="label mr-2">Blast radius</span>
                <b>{blast.asset_id}</b> falls → with its sessions and credentials an attacker reaches{" "}
                <span className="text-gold">{blast.reachable.filter((a) => graph?.assets.find((x) => x.id === a)?.kind !== "internet").join(", ") || "nothing"}</span>
                {blast.crown_jewels_hit.length > 0 && <span className="text-block"> — including crown jewel {blast.crown_jewels_hit.join(", ")}</span>}
                {internetReached && <span className="text-fg-muted"> (and can exfiltrate to the internet)</span>}.
                <span className="text-fg-faint"> Topological upper bound ignoring credentials: {blast.upper_bound.length} assets.</span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <EffortChart before={verdict?.before ?? null} after={verdict?.after ?? null} />
              <OptimizerPanel catalogue={catalogue} run={(b) => api.optimize(twinId, b, agents.map((a) => a.id))} onPick={setPicked} />
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}

function Stat({ label, value, sub, delta, bad, mono }: { label: string; value: string | number; sub?: string; delta?: string; bad?: boolean; mono?: boolean }) {
  return (
    <div>
      <div className="label">{label}</div>
      <div className={`mt-0.5 ${mono ? "mono text-[12px]" : "text-base font-semibold"}`}>{value}{sub && <span className="ml-1.5 text-xs font-normal text-fg-faint">{sub}</span>}
        {delta && <span className={`ml-1.5 text-xs font-semibold ${bad ? "text-block" : "text-deploy"}`}>{delta}</span>}</div>
    </div>
  );
}
