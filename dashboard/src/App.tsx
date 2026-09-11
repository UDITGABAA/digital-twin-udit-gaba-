import { useCallback, useEffect, useState } from "react";
import { ArrowsClockwise, Warning, ShieldCheck, ArrowUUpLeft, CheckCircle } from "@phosphor-icons/react";
import { api } from "./api/client";
import type { Agent, Blast, ChangeVerdict, Control, Graph, Result, Route, Trial } from "./types";
import { DecisionCard } from "./views/DecisionCard";
import { Stage, type ReplayState } from "./views/Stage";
import { Replay } from "./views/Replay";
import { EffortChart } from "./views/EffortChart";
import { OptimizerPanel } from "./views/OptimizerPanel";
import { SegmentedTabs } from "./components/SegmentedTabs";
import { Stat } from "./components/Stat";

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
  const [applied, setApplied] = useState<Control[]>([]);
  const [history, setHistory] = useState<{ id: string; label: string }[]>([]);   // adopted twins, oldest first
  const [notice, setNotice] = useState<string | null>(null);

  const agent = agents.find((a) => a.id === agentId) ?? null;

  const refresh = useCallback(async (id: string, ag: string) => {
    const [g, c, b, p] = await Promise.all([api.graph(id), api.controls(id), api.simulate(id, ag), api.paths(id, ag)]);
    setGraph(g); setCatalogue(c.catalogue); setApplied(c.applied); setBaseline(b); setPaths(p); setTwinId(g.twin_id); setError(null);
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
    setHistory([]); setNotice(null);
    await refresh("current", agentId);
  };

  /* Adopting a change is the only action that alters the twin. Everything else is a what-if.
     The child twin becomes current; the top numbers move; the chips show the control as applied. */
  const adopt = async () => {
    if (!verdict) return;
    const label = verdict.control_ids.map((id) => catalogue.find((c) => c.id === id)?.name ?? id).join(" + ");
    setPrev(baseline ? { p: baseline.p_success, risk: baseline.weighted_risk } : null);
    const child = await api.clone(twinId, verdict.control_ids, label);
    setHistory((h) => [...h, { id: twinId, label: h.length ? "previous twin" : scenario === "golden" ? "FinBank" : "FinBank after sync" }]);
    setPicked([]); setVerdict(null); setRoute(null); setTrials(null); setReplay(null); setBlast(null);
    setNotice(`Adopted: ${label}. The twin now includes it; the numbers above are the new baseline. Nothing was deployed anywhere real.`);
    await refresh(child.id, agentId);
  };

  const undo = async () => {
    const last = history[history.length - 1];
    if (!last) return;
    setPrev(baseline ? { p: baseline.p_success, risk: baseline.weighted_risk } : null);
    setHistory((h) => h.slice(0, -1));
    setPicked([]); setVerdict(null); setRoute(null); setTrials(null); setReplay(null); setBlast(null);
    setNotice("Reverted to the previous twin.");
    await refresh(last.id, agentId);
  };

  const switchAgent = (id: string) => { setAgentId(id); refresh(twinId, id); };

  const runAttack = async () => {
    setRunning(true);
    try { setRoute(null); setBlast(null); setTrials(await api.trace(twinId, agentId, picked, 12)); }
    catch (e) { setError(String(e)); } finally { setRunning(false); }
  };

  const selectAsset = async (id: string) => { setBlast(await api.blast(twinId, id)); setRoute(null); setReplay(null); setTrials(null); };

  const pDelta = prev && baseline ? baseline.p_success - prev.p : null;
  const internetReached = blast?.reachable.some((a) => graph?.assets.find((x) => x.id === a)?.kind === "internet");
  const proposalLabel = picked.length ? picked.map((id) => catalogue.find((c) => c.id === id)?.name ?? id).join(" + ") : "the current twin";

  return (
    <div className="min-h-dvh">
      <header className="sticky top-0 z-20 border-b border-line bg-canvas/85 backdrop-blur-sm">
        <nav className="mx-auto flex max-w-[1480px] flex-wrap items-center gap-x-6 gap-y-2 px-6 py-3">
          <div className="flex items-center gap-2.5">
            <span className="grid h-7 w-7 place-items-center rounded-md bg-accent text-white"><ShieldCheck weight="bold" className="h-4 w-4" /></span>
            <span className="text-[15px] font-semibold text-ink">Security Change Sandbox</span>
            <span className="hidden text-[13px] text-faint md:inline">· what can I deploy safely, within budget, and how sure are we</span>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-3">
            <SegmentedTabs value={agentId} onChange={switchAgent} items={agents.map((a) => ({ id: a.id, title: a.name, hint: `starts in ${a.start_zones.join(", ")}` }))} />
            <select value={scenario} onChange={(e) => loadScenario(e.target.value)} aria-label="scenario"
              className="rounded-md border border-line bg-surface px-2.5 py-1.5 text-[13px] text-ink">
              <option value="golden">FinBank</option>
              <option value="golden_sync">FinBank after sync — contractor admin on jump-01</option>
            </select>
            <button onClick={() => loadScenario("golden", true)} className="btn"><ArrowsClockwise weight="bold" />reset demo</button>
          </div>
        </nav>
      </header>

      <main id="main" className="mx-auto max-w-[1480px] px-6 pb-16 pt-6">
        {error && <div className="mb-5 flex items-center gap-2 rounded-lg border border-red-ink/30 bg-red-tint px-3 py-2 text-sm text-red-ink"><Warning weight="bold" />{error} — is uvicorn running?</div>}
        {notice && (
          <div className="mb-5 flex items-center gap-2 rounded-lg border border-green-ink/30 bg-green-tint px-3 py-2 text-sm text-green-ink" role="status">
            <CheckCircle weight="fill" />{notice}
            <button className="ml-auto text-xs underline" onClick={() => setNotice(null)}>dismiss</button>
          </div>
        )}

        {baseline && (
          <div className="mb-6 flex flex-wrap items-end gap-x-10 gap-y-3">
            <Stat label="critical paths to crown jewel" value={paths?.naive_count} />
            <Stat label="p(success)" value={baseline.p_success} format={{ minimumFractionDigits: 2, maximumFractionDigits: 2 }}
              sub={`${baseline.p_success_ci[0].toFixed(2)}–${baseline.p_success_ci[1].toFixed(2)}`}
              delta={pDelta !== null && pDelta !== 0 ? `${pDelta > 0 ? "+" : ""}${pDelta.toFixed(2)} since last twin` : undefined} deltaBad={(pDelta ?? 0) > 0} />
            <Stat label="mean attacker effort" value={baseline.mean_effort ?? 0} format={{ minimumFractionDigits: 1, maximumFractionDigits: 1 }} />
            <Stat label="weighted risk" value={baseline.weighted_risk} format={{ minimumFractionDigits: 2, maximumFractionDigits: 2 }} />
            <Stat label="favourite route" sub={baseline.routes[0] ? `p_select ${baseline.routes[0].p_select.toFixed(2)}` : undefined}>
              <span className="mono text-[12px] font-normal text-text">{baseline.routes[0] ? baseline.routes[0].route.map((e) => e.technique).join(" › ") : "none"}</span>
            </Stat>
            <span className="ml-auto flex items-center gap-3 text-[11px] text-faint">
              {history.length > 0 && <span>{[...history.map((h) => h.label), applied.map((c) => c.name).slice(-1)[0] ?? "current"].join(" → ")}</span>}
              <span className="mono">twin {twinId.slice(0, 10)} · seed 1 · 1,000 trials</span>
              {history.length > 0 && <button className="btn btn-icon" onClick={undo} aria-label="revert to previous twin" title="revert to previous twin"><ArrowUUpLeft weight="bold" /></button>}
            </span>
          </div>
        )}

        <section className="mb-5">
          <div className="mb-2 flex items-baseline gap-3">
            <div className="label">Propose controls</div>
            {picked.length > 0 && <button onClick={() => setPicked([])} className="text-xs text-muted hover:text-ink">clear</button>}
          </div>
          <div className="flex flex-wrap gap-2">
            {catalogue.map((c) => {
              const isApplied = applied.some((a) => a.id === c.id);
              return (
                <button key={c.id} type="button" className="chip" aria-pressed={picked.includes(c.id)} disabled={isApplied} onClick={() => toggle(c.id)}
                  title={isApplied ? "already part of this twin" : undefined} style={isApplied ? { opacity: 0.55, cursor: "default" } : undefined}>
                  <span>{c.name}</span>
                  {isApplied ? <span className="tag tag-green">applied</span> : <span className="cost">cost {c.cost}</span>}
                </button>
              );
            })}
          </div>
        </section>

        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
          <DecisionCard verdict={verdict} catalogue={catalogue} onPick={setPicked} onAdopt={adopt} onHighlight={(r) => { setRoute(r); setTrials(null); setReplay(null); }} />
          <Replay trials={trials} noiseBudget={agent?.noise_budget ?? 3} running={running} onRun={runAttack} onState={setReplay}
            label={`${agent?.name ?? agentId} against ${proposalLabel}`} />
        </div>

        <div className="mt-5">
          <Stage graph={graph} route={route} blast={blast} replay={replay} startZones={agent?.start_zones ?? []} onSelectAsset={selectAsset} />
        </div>

        {blast && (
          <div className="card mt-5 px-5 py-3 text-sm text-text">
            <span className="label mr-3">Blast radius</span>
            <b className="text-ink">{blast.asset_id}</b> falls → with its sessions and credentials an attacker reaches{" "}
            <span className="text-yellow-ink">{blast.reachable.filter((a) => graph?.assets.find((x) => x.id === a)?.kind !== "internet").join(", ") || "nothing"}</span>
            {blast.crown_jewels_hit.length > 0 && <span className="text-red-ink"> — including crown jewel {blast.crown_jewels_hit.join(", ")}</span>}
            {internetReached && <span className="text-muted"> (and can exfiltrate to the internet)</span>}.
            <span className="text-faint"> Topological upper bound ignoring credentials: {blast.upper_bound.length} assets.</span>
          </div>
        )}

        <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]">
          <EffortChart before={verdict?.before ?? null} after={verdict?.after ?? null} />
          <OptimizerPanel catalogue={catalogue} run={(b) => api.optimize(twinId, b, agents.map((a) => a.id))} onPick={setPicked} />
        </div>

        <footer className="mt-12 flex flex-wrap gap-x-6 gap-y-1 border-t border-line pt-4 text-[12px] text-faint">
          <span>Seeded Monte Carlo over a frozen twin — rehearsed numbers equal stage numbers.</span>
          <span>Ten MITRE ATT&CK techniques in YAML.</span>
          <span>Every grant, flow and edge carries its evidence.</span>
          <span className="ml-auto">MUJ HackX 4.0 · PS #13</span>
        </footer>
      </main>
    </div>
  );
}
