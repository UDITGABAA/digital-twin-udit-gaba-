import { useEffect, useRef, useState } from "react";
import { Play, Pause, SkipForward, ArrowCounterClockwise, Check, X, WarningOctagon, Crosshair } from "@phosphor-icons/react";
import type { Step, Trial } from "../types";
import type { ReplayState } from "./Stage";
import { edgeKey } from "./Stage";
import { HoldButton } from "../components/HoldButton";

const SPEEDS = [1, 2, 4] as const;

export function Replay({ trials, noiseBudget, label, onState, onRun, running }: {
  trials: Trial[] | null; noiseBudget: number; label: string;
  onState: (s: ReplayState | null) => void; onRun: () => void; running: boolean;
}) {
  const [ti, setTi] = useState(0);
  const [si, setSi] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]>(1);
  const feedRef = useRef<HTMLDivElement>(null);

  const trial = trials?.[ti] ?? null;
  const steps = trial?.steps ?? [];
  const shown = steps.slice(0, si + 1);
  const last: Step | undefined = shown[shown.length - 1];
  const done = trial !== null && si >= steps.length - 1;

  useEffect(() => { setTi(0); setSi(-1); setPlaying(!!trials?.length); }, [trials]);

  useEffect(() => {
    if (!playing || !trial) return;
    if (si >= steps.length - 1) {
      const t = setTimeout(() => { if (ti < (trials?.length ?? 0) - 1) { setTi(ti + 1); setSi(-1); } else setPlaying(false); }, 1400 / speed);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setSi(si + 1), 620 / speed);
    return () => clearTimeout(t);
  }, [playing, si, ti, trial, steps.length, trials, speed]);

  useEffect(() => {
    if (!trial) { onState(null); return; }
    const breached = new Set<string>(), traversed = new Set<string>();
    shown.forEach((s) => { if (s.succeeded) { breached.add(s.dst); traversed.add(edgeKey(s.src, s.dst, s.technique)); } });
    if (shown[0]) breached.add(shown[0].src);
    onState({
      breached, traversed,
      active: last && !done ? last.dst : null,
      activeEdge: last ? edgeKey(last.src, last.dst, last.technique) : null,
      failedEdge: last && !last.succeeded ? edgeKey(last.src, last.dst, last.technique) : null,
      detected: !!last?.detected,
    });
  }, [si, ti, trial]); // eslint-disable-line

  useEffect(() => { feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight, behavior: "smooth" }); }, [si]);

  const noise = last?.noise_so_far ?? 0;
  const outcome = !trial || !done ? null : trial.detected ? "detected" : trial.success ? "success" : "gave up";
  const successes = trials ? trials.filter((t) => t.success).length : 0;

  return (
    <section className="card flex min-h-[460px] flex-col p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="label">Attack replay</div>
          <div className="mt-1 truncate text-[15px] font-medium text-ink" title={label}>{label}</div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {trials && (
            <>
              <button className="btn btn-icon" onClick={() => setPlaying((p) => !p)} aria-label={playing ? "pause" : "play"}>{playing ? <Pause weight="bold" /> : <Play weight="bold" />}</button>
              <button className="btn btn-icon" aria-label="skip" onClick={() => { setPlaying(false); if (done) { if (ti < trials.length - 1) { setTi(ti + 1); setSi(-1); } } else setSi(steps.length - 1); }}><SkipForward weight="bold" /></button>
              <button className="btn btn-icon" aria-label="restart" onClick={() => { setTi(0); setSi(-1); setPlaying(true); }}><ArrowCounterClockwise weight="bold" /></button>
              <button className="btn mono" onClick={() => setSpeed(SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length])}>{speed}×</button>
            </>
          )}
          <HoldButton onComplete={onRun} disabled={running} className="ml-1"><Crosshair weight="bold" />{running ? "simulating…" : trials ? "hold to run again" : "hold to run attack"}</HoldButton>
        </div>
      </div>

      {!trials ? (
        <div className="mt-8 flex flex-1 flex-col justify-center">
          <p className="max-w-[40ch] text-[15px] leading-relaxed text-muted">
            Replays the first trials of the seeded simulation, step by step — the same dice the thousand-trial statistics are built from.
            Trial <i>i</i> here is trial <i>i</i> of the statistics.
          </p>
          <p className="mt-3 text-sm text-faint">Hold the orange button. Change the proposal and run again to watch the attacker fail where the control bites.</p>
        </div>
      ) : (
        <>
          <div className="mt-5 grid grid-cols-4 gap-2">
            <div className="inset px-3 py-2"><div className="label">trial</div><div className="mt-0.5 font-semibold text-ink">{ti + 1} <span className="text-faint">/ {trials.length}</span></div></div>
            <div className="inset px-3 py-2"><div className="label">route</div><div className="mt-0.5 font-semibold text-ink">#{(trial?.route_index ?? 0) + 1} <span className="text-faint">· {steps.length ? new Set(steps.map((s) => s.dst)).size : 0} hops</span></div></div>
            <div className="inset px-3 py-2"><div className="label">effort</div><div className="mt-0.5 font-semibold text-ink">{(last?.effort_so_far ?? 0).toFixed(0)}</div></div>
            <div className="inset px-3 py-2">
              <div className="label">noise · budget</div>
              <div className="mt-1.5 meter"><div style={{ width: `${Math.min(100, (noise / noiseBudget) * 100)}%` }} /></div>
              <div className="mono mt-1 text-[11px] text-muted">{noise.toFixed(1)} / {noiseBudget.toFixed(1)}</div>
            </div>
          </div>

          <div ref={feedRef} className="mt-3 h-[224px] space-y-1 overflow-y-auto pr-1">
            {shown.map((s, i) => (
              <div key={`${ti}-${i}`} className={`feed-line ${s.detected ? "detected" : s.succeeded ? "ok" : "fail"}`}>
                <span>{s.detected ? <WarningOctagon className="text-red-ink" weight="fill" /> : s.succeeded ? <Check className="text-green-ink" weight="bold" /> : <X className="text-yellow-ink" weight="bold" />}</span>
                <span className="text-ink">
                  <span className="font-medium">{s.technique}</span>
                  <span className="text-muted"> {s.src === s.dst ? `on ${s.dst}` : `${s.src} → ${s.dst}`}{s.identity_id ? ` as ${s.identity_id}` : ""}</span>
                  {s.detected && <span className="text-red-ink"> — noise over budget, attacker detected</span>}
                </span>
                <span className="mono text-muted">{s.roll === null ? "—" : `roll ${s.roll.toFixed(2)} ${s.succeeded ? "<" : "≥"} p ${s.p_success.toFixed(2)}`}{s.attempt > 1 ? ` · try ${s.attempt}` : ""}</span>
              </div>
            ))}
            {outcome && (
              <div className={`feed-line mt-2 font-medium ${outcome === "success" ? "bg-accent-tint text-accent-deep" : outcome === "detected" ? "detected text-red-ink" : "bg-raised text-muted"}`} style={{ gridTemplateColumns: "1fr" }}>
                {outcome === "success" ? `Crown jewel reached — effort ${trial!.effort.toFixed(0)}, noise ${trial!.noise.toFixed(1)}` : outcome === "detected" ? "Attacker detected before reaching the target" : "Attacker gave up after three failed attempts"}
              </div>
            )}
          </div>
          <div className="mt-3 text-[12px] text-faint"><b className="text-ink">{successes}</b> of {trials.length} replayed trials reach the crown jewel · seed 1</div>
        </>
      )}
    </section>
  );
}
