# Implementation plan v2.1 — phased, with verifiable exits

> **Status (solo build, repo `UDITGABAA/digital-twin-udit-gaba-`, branch `main`):**
> P0–P4 complete. `pytest` = 35 green, including `test_scenario.py` which pins every number in
> `docs/DEMO_SCRIPT.md`. Built: `engine/` (models, clone/hash, search, walk, results, blast,
> scenario), `rules/` (loader, compile, evaluate, optimize), `server/app.py`, `dashboard/`
> (decision card, graph, effort histograms, optimiser, sync, blast radius),
> `scenarios/golden.json` + `golden_sync.json`, `scripts/build_golden.py`.
> Cut for solo: `/matrix` view, lineage view, generated `types.ts`, CI, narration cache.
> Phase 5 so far: fresh-clone regression green, CI added, every run-sheet beat driven through
> the API in < 100 ms (see `docs/STATUS.md`). Remaining: two timed spoken rehearsals, slides,
> video fallback, second laptop.
> The four-track split below is kept as the file map; one person owns all of it now.

Six phases. Each has an **exit criterion that is a command someone runs**, not a feeling.
Nobody advances a phase on "it looks done."

Hours are from kickoff and assume ~24 hours of real build time. If the event is 36, the
slack goes into Phase 5, not into new features.

This plan supersedes v1. What changed and why is in §A at the end. The contract it builds
against is `CLAUDE.md` §5; the function signatures between tracks are `docs/INTERFACES.md`.

---

## Phase 0 — Base workflow (hour 0 → 1.5) · ALL FOUR TOGETHER

Nobody writes feature code. This ninety minutes is what makes the next twenty parallel.
Everything below is done on one screen, everyone watching, and pushed before anyone splits.

**Do, in this order:**

1. Repo is `UDITGABAA/digital-twin-udit-gaba-`, integration branch `main`, layout
   `engine/ rules/ scenarios/ server/ tests/ dashboard/`. CI runs `pytest` and the dashboard
   build on every push.
2. The engine ported from the previous repo's prototype was reviewed and consolidated
   (§Migration below records what was kept); nothing from the old prototype is imported.
3. Write `engine/models.py` — copy from `CLAUDE.md` §5. Argue about it now, never
   later. Add the canonical `twin_hash()` next to it.
4. Write `rules/techniques.yaml` — the ten entries, each with its ATT&CK ID and
   channel.
5. Write `docs/INTERFACES.md` — the four cross-track signatures. This file is the contract
   between AI sessions (GOVERNANCE §9).
6. Write `scenarios/golden.json` **v0** — the FinBank assets, identities,
   grants, edges and flows from §Golden below. **No controls yet.** Every track now has real
   data from hour 1.5.
7. `scripts/gen_types.py` → `dashboard/src/types.ts` (Pydantic JSON schema →
   `json-schema-to-typescript`).
8. `docs/STATUS.md` with the empty gate table.

**Exit (Gate G0) — all four must pass on their own machine:**

```bash
python -c "from engine.models import Twin, CompiledEdge, FlowSelector; print('ok')"
pytest --collect-only          # collects, zero errors
cd dashboard && npm run dev     # serves
```

**Trap:** designing the data model before deciding the demo story. The story tells you
which fields you actually need. `FlowSelector` has `src_assets` and `identity_ids` because
the demo must distinguish an allowed payroll workload from an attacker on an HR workstation
holding payroll credentials — not because selectors are conceptually nice.

---

## Phase 1 — Walking skeleton (hour 1.5 → 4) · PARALLEL

End-to-end pipe with fake logic inside. **Do not skip this phase.** Proving the frontend
can call the real backend at hour 4 turns integration from an hour-18 catastrophe into an
hour-4 annoyance.

| Track | Builds | Verifies with |
|---|---|---|
| **A** | Replace `DigitalTwin`/`find_all_attack_paths` with an `engine/search.py` skeleton reading `CompiledEdge` (no logic yet). `engine/twin.py` — `clone()`, `twin_hash()`. `engine/results.py` — `Result`, `Delta`, `ChangeVerdict` as frozen types with hardcoded values. Delete the old engine files in the same PR. | `python -c "from engine.results import Result"`; old `engine/` gone |
| **B** | Write `rules/loader.py` (YAML → technique table, validated: every technique has an ATT&CK ID, only allowed placeholders). `rules/compile.py` skeleton with the `matches(selector, channel)` function and its test. `rules/_stub_policy.py`. | `pytest tests/test_rules.py -k matches` |
| **C** | Vite + React + TS + Tailwind scaffold. `api/mocks.ts` with one fake `Result` and one fake `ChangeVerdict`. **The decision card**, rendering the mock verdict exactly as `CLAUDE.md` §2 shows it. | `npm run dev` shows the card |
| **D** | FastAPI app, `/twin/{id}` and `/simulate` returning the hardcoded `Result` from `server/stubs.py`. CORS for Vite. `golden.json` v1 — adds the eight controls from §Golden. | `curl.exe -X POST localhost:8000/simulate ...` |

**Exit (Gate G1):**

```bash
curl.exe -X POST localhost:8000/simulate -H "Content-Type: application/json" -d "{\"twin_id\":\"golden\",\"agent_id\":\"external\",\"n\":100,\"seed\":1}"
# returns a valid Result
```

and the decision card displays those numbers **fetched from the real API**, mocks switched
off. Demo it to each other, screen shared. If the numbers on screen came from `mocks.ts`,
the gate has not passed.

---

## Phase 2 — Engine correctness (hour 4 → 9) · A and B in parallel, both critical

The only phase where wrong code is invisible. Everything downstream inherits its errors.

**A — in this exact order:**

1. **`tests/test_fixture.py` FIRST, before `search.py` has logic.** Hand-build a 6-node
   graph of `CompiledEdge` tuples on paper where every valid path is known by inspection,
   including one path reachable *only* after collecting a credential two hops earlier
   (`cred_dump` on node 2 grants `creds:x`; the edge into node 5 requires `creds:x`).
   Assert exact path counts and the exact path list. Fixture edges are hand-built — A does
   **not** wait for `compile.py`.
2. `engine/search.py` — complete path search. State is `(node, frozenset(caps))`. Dedupe on
   the **full state**, not the node. DFS simple paths to `agent.target`. Hard caps
   `max_depth=8`, `max_paths=5000`, raise `SearchBudgetExceeded` rather than hang. Loop
   until the fixture is green.
3. `engine/walk.py` — `route_policy(inventory, agent)` first (deterministic, no RNG, unit-test
   it: top-5, noise filter, `p_select` sums to 1, skill=1 concentrates on the best). Then
   `trial(rng)` and `simulate(twin, agent, n, seed)`. `random.Random(seed)`; pre-draw
   uniforms in bulk.
4. `engine/results.py` — real `Result` from trial records, `diff()` producing `Delta`
   including `substituted_paths` and the `route_eliminated` / `None` handling.
5. `tests/test_invariants.py` — adding a control never increases `p_success`; `clone`
   never mutates its input (compare `twin_hash` before/after); identical seed gives
   identical `Result`.

**B — in this exact order:**

1. `rules/compile.py` complete: for each `Edge`, look up **its one declared technique**,
   expand `creds:who` over grants on `dst` (one `CompiledEdge` per candidate identity;
   `admin:dst` added when the grant is `admin`), expand `creds:sessions@src`, then apply
   every control impact through `matches()` (`naive=True` drops, else degrades).
2. `tests/test_rules.py`:
   - **no invented transitions**: `{(e.src, e.dst, e.technique) for e in compiled} ⊆ {… for
     e in twin.edges}` for every twin, and `==` when `controls=()`;
   - scoped segmentation: `ws-hr → prod-db` as `svc.payroll` is dropped, `backup-01 →
     prod-db` as `svc.backup` survives, flow F1 not broken, F2 not broken;
   - `mfa_humans` degrades a `u.dev` edge, leaves a `svc.backup` edge, breaks no flow;
   - `mfa_all` breaks F1, F2, F4.
3. Start `rules/evaluate.py` against `_stub_policy.py` — broken-flow detection and the
   verdict rules can be finished before A's `route_policy` merges.

**C:** React Flow graph view of the golden twin (assets coloured by zone, crown jewel
marked), and the route animation, against mocks.
**D:** `server/cache.py` keyed on `(twin_hash, agent_id, seed, n)`; `/twin/{id}/clone`;
`/lineage`; `golden_sync.json` (golden + contractor `admin@jump-01`).

**Exit (Gate G2):**

```bash
pytest tests/test_fixture.py tests/test_invariants.py tests/test_rules.py -v   # all green on main
```

**Traps.** Running the state-space search inside the Monte Carlo loop — an order of
magnitude slower and a different attacker model; `route_policy` is called once per
`simulate`, not once per trial. Deduping on node rather than on `(node, capabilities)` —
silently drops valid paths. Expanding `Edge × every technique` in `compile.py` — invents
attack paths the twin never declared; the subset test exists to catch exactly this. Letting
an AI session generate `search.py` before the fixture test exists — it will produce
confident, plausible, wrong code and you will not notice for fifteen hours.

---

## Phase 3 — The differentiator (hour 9 → 14) · B leads

Where the product stops being a clone of BloodHound.

**B — `rules/evaluate.py` → `evaluate_change(twin, control_ids, agent_ids, *, seed)`:**

1. `clone` the twin with the controls applied.
2. `compile` before and after, twice each: `naive=True` for the path count, `naive=False`
   for the simulation.
3. `search` both; `simulate` both (`n=1000`, fixed seed).
4. `naive_path_reduction_pct` (**required by the brief — ship it**).
5. `effort_increase_pct` from `mean_effort` before/after; `None` and
   `route_eliminated=True` when `after` has fewer than 20 successful trials.
6. `substituted_paths` — routes in `after.routes` absent from `before.routes`.
7. **`broken_flows`** — every `ServiceFlow` whose channel is matched by some impact's
   `deny` with `breaks_flows=True` and by none of that impact's `exceptions`. Same
   `matches()` as the attack side. ~30 lines, and it is the entire differentiator.
8. **Confidence** — decisive elements are the grants, flows and edges in `broken_flows` and
   on every top-K route before and after. `score = mean(weight)`; High/Medium/Low at
   0.85/0.6; any `assumed` → `undetermined=True`. `unknowns` in words.
9. **Verdict** — the rules in `CLAUDE.md` §7, verbatim. `reasons` lists which rule fired.
10. `alternatives` — from the optimiser's precomputed sweep (Phase 4); until then, the best
    single control that breaks no crit ≥ 4 flow.
11. `tests/test_evaluate.py` — one test per verdict rule, the `None`/`route_eliminated`
    case yields DEPLOY not REVIEW, an `assumed` grant on the decisive route yields
    `undetermined` and REVIEW.

**A:** performance — `simulate(n=1000)` under one second on golden (bulk RNG, no Pydantic
construction inside the loop). `engine/blast.py` — `search` seeded with
`{session:X, admin:X} ∪ creds of sessions on X`; `nx.descendants` returned alongside,
labelled "upper bound ignoring credentials".
**C:** the decision card wired to `/evaluate-change`; the **overlaid before/after
attacker-effort histograms** in Recharts — that chart is the thesis made visible, give it
real design time; the substituted route animated on the graph.
**D:** startup precompute of golden × every agent × every single control; `/evaluate-change`
and `/blast-radius` routes; `stubs.py` deleted.

**Exit (Gate G3):**

```bash
curl.exe -X POST localhost:8000/evaluate-change -H "Content-Type: application/json" -d "{\"twin_id\":\"golden\",\"control_ids\":[\"seg_prod_db_full\"],\"agent_ids\":[\"external\"],\"seed\":1}"
```

returns both metrics, `broken_flows` containing F1, `confidence.level == "Medium"` with
`"svc.backup admin on prod-db — inferred"` in `unknowns`, `recommendation == "blocked"`,
non-empty `alternatives` — and the card renders all of it. **If full segmentation does not
break F1, or no substituted route appears, the scenario is wrong, not the code.** Fix the
data.

---

## Phase 4 — Optimiser, matrix, sync (hour 14 → 18)

**B — `rules/optimize.py`:** enumerate every subset of the ≤10-control catalogue within
budget. For each: `clone → compile → search → risk = Σ_agents target_crit × Σ p_select ×
p_route` via `route_policy` — deterministic, no Monte Carlo — and `broken_flows`. Discard
any subset breaking a flow with `criticality >= 4`. Best = maximum risk reduction. No
pruning; 1024 evaluations of a ~10-asset twin is seconds, and it runs at startup. Also
return the naive "top-N by paths eliminated within budget" portfolio so the demo can
contrast them. Wire `alternatives` in `evaluate_change` to this table.
**A:** `route_policy` and `simulate` exposed for `test_scenario.py`'s agreement check;
help D with performance if precompute is slow.
**C:** optimiser view (constrained vs naive, side by side), matrix heatmap, blast-radius
view, lineage tree, "load scenario" dropdown, **reset button**.
**D:** `/optimize`, `/matrix` (loops `evaluate_change` over controls × agents), sync demo
(load `golden_sync.json` → risk goes **up**, the new grant highlighted), pre-generated
route narration in `narration.json`, `tests/test_scenario.py` first draft.

**Exit (Gate G4 — FEATURE FREEZE, hour 18):**

```bash
pytest                                  # everything green
curl.exe localhost:8000/optimize?twin_id=golden^&budget=12   # constrained != naive, constrained breaks no P1 flow
git log origin/main -1               # last feature merge
```

Everything merged. **No new features after this line, ever.** Every hackathon team breaks
its demo in the last three hours by adding one more thing.

---

## Phase 5 — Hardening and rehearsal (hour 18 → 24) · ALL FOUR

Bugs and polish only. The product is done; now make it survivable.

- **Hour 18–20:** bug bash. Everyone clicks everything, on a fresh clone. Fix breaks,
  add nothing.
- **Hour 20–21:** `test_scenario.py` pinned to the exact numbers in `docs/DEMO_SCRIPT.md`,
  plus the assertion that optimiser risk and simulated `p_success × crit` agree within
  0.05. If a late fix shifts a headline number, you find out here rather than on stage.
- **Hour 21–22 (Gate G5):** full rehearsal, timed, under four minutes. Twice. A and B
  rehearse the four answers in `CLAUDE.md` §12 out loud.
- **Hour 22–23:** slides. Prior-art table from `CLAUDE.md` §3 goes on slide two — naming
  MAL and Azure yourself is what makes the narrow claim survive Q&A.
- **Hour 23–24:** screen-record a clean run as video fallback. Second laptop running the
  same build. Sleep if anyone can.

---

## The four tracks — who builds what, in what order, and how they know it works

| | **A — engine** | **B — rules & decisions** | **C — frontend** | **D — integration & demo** |
|---|---|---|---|---|
| Owns | `engine/`, `tests/test_fixture.py`, `tests/test_invariants.py` | `rules/`, `tests/test_rules.py`, `tests/test_evaluate.py` | `dashboard/`, `scripts/gen_types.py` | `server/`, `scenarios/`, `docs/`, `README.md`, `tests/test_scenario.py` |
| First job (P1) | Replace `DigitalTwin` with `engine/search.py` skeleton over `CompiledEdge`; `twin.py`; hardcoded `results.py`; delete old `engine/*` | `loader.py`; `matches()` + test; `_stub_policy.py`; replace `AdversaryAgent._infer_attack_technique` with the YAML | Scaffold; `mocks.ts`; **decision card** | FastAPI + `stubs.py`; CORS; `golden.json` v1 |
| Then, in order | fixture → `search.py` → `route_policy` → `walk.py` → `results.py` → invariants → perf → `blast.py` | `compile.py` → no-invented-transition test → `evaluate.py` (flows, confidence, verdict) → `test_evaluate.py` → `optimize.py` | graph + route animation → card on real API → effort histograms → optimiser / matrix / blast / lineage → dropdown + reset | `cache.py` → clone/lineage → precompute → evaluate/blast routes → optimize/matrix → sync → narration → `test_scenario.py` → run sheet |
| Never blocked because | fixture edges are hand-built `CompiledEdge`s | tests build a 4-node twin inline; `_stub_policy.py` until A merges | `mocks.ts` mirrors `types.ts`; flips at G1 | `stubs.py` until A and B merge |
| Verifies with | `pytest tests/test_fixture.py tests/test_invariants.py`; `simulate(n=1000)` < 1 s | `pytest tests/test_rules.py tests/test_evaluate.py` | `npm run dev` with mocks off shows API numbers; `npm run build` clean | `curl.exe` every endpoint; `pytest tests/test_scenario.py`; timed run < 4 min |
| Reviews | B's PRs | A's PRs | D's PRs | C's PRs; release manager; calls gates |
| On stage | algorithm questions | breakage / confidence / verdict questions | — | drives the demo; prior art |

Critical path:

```
models.py ──▶ compile.py ──▶ search.py ──▶ route_policy/walk.py ──▶ evaluate_change ──▶ optimize
  (P0)          (P2, B)        (P2, A)           (P2, A)                (P3, B)          (P4, B)
```

A and B are both on it and are decoupled in P2 by the hand-built fixture and the stub
policy. Everything else — frontend, API, cache, matrix, blast radius, sync — is off the
critical path and can slip without killing the demo. **If A or B is blocked, the project is
blocked**, and that is the one situation where everyone else drops their track and helps.

---

## Golden scenario — "FinBank"

Design the story before the data. Every demo beat below has a route that makes it true.

**Assets** — `internet` (external) · `web-dmz` (dmz, 3) · `ws-dev`, `ws-hr` (corp, 2) ·
`fileshare` (corp, share, 2) · `ci-runner` (corp, 3) · `jump-01` (mgmt, 3) · `payroll-api`
(prod, 4) · `backup-01` (prod, 3) · **`prod-db`** (prod, database, 5, crown jewel).

**Identities and grants**

| Identity | kind | grants (capability@asset, evidence) |
|---|---|---|
| `u.dev` | user | session@ws-dev · login@jump-01 · login@ci-runner (**inferred**) |
| `u.hr` | user | session@ws-hr · login@fileshare |
| `adm.ops` | admin | session@jump-01 (**observed**) · admin@prod-db · admin@backup-01 |
| `svc.payroll` | service_account | session@payroll-api · login@prod-db |
| `svc.backup` | service_account | session@backup-01 · **admin@prod-db (inferred)** ← the named unknown |
| `svc.ci` | service_account | session@ci-runner · login@backup-01 |

**Attack routes designed in** (each edge is an explicit `Edge` in the JSON):

- **A** `internet →phish→ ws-dev →cred_dump→ (creds:u.dev) →rdp_lateral→ jump-01 →priv_esc_local→ →cred_dump→ (creds:adm.ops) →rdp_lateral→ prod-db`
- **B** `ws-dev →ssh_lateral→ ci-runner →cred_dump→ (creds:svc.ci) →ssh_lateral→ backup-01 →cred_dump→ (creds:svc.backup) →db_login→ prod-db`
- **C** `internet →phish→ ws-hr →smb_lateral→ fileshare →creds_in_files→ (creds:svc.payroll) →db_login→ prod-db` (from ws-hr)
- **D** `internet →exploit_public_app→ web-dmz →exploit_public_app→ ci-runner → (B tail)` — no human credential anywhere on it.

Two modelling rules the routes depend on — settle them in P0, not on stage:
- `phish` grants `session:dst` **and** `admin:dst` (workstation users are local admins — a
  stated, defensible FinBank assumption). `exploit_public_app` grants `session:dst` only.
- `cred_dump` requires `admin:src`, so the JSON lists `priv_esc_local` **self-edges** on
  `jump-01`, `ci-runner` and `backup-01`. Route B/D go `ci-runner →priv_esc_local→
  →cred_dump→`; the same on `backup-01`. Without these self-edges routes B and D do not
  exist and the demo has no substituted path.
- Route C's last hop, `ws-hr →db_login→ prod-db`, is taken *after* the attacker has been to
  `fileshare`; it is admissible because `session:ws-hr` is still held (CLAUDE.md §6: an edge
  is admissible from any state whose caps ⊇ requires). A's fixture must include one such
  "act from an earlier foothold" path.

**Legitimate flows**

| id | flow | identity | crit | evidence |
|---|---|---|---|---|
| F1 | payroll-api → prod-db tcp/5432 | svc.payroll | **5** | inventory |
| F2 | backup-01 → prod-db tcp/5432 | svc.backup | 4 | **inferred** |
| F3 | ws-dev → jump-01 rdp/3389 | u.dev | 2 | observed |
| F4 | ci-runner → backup-01 ssh/22 | svc.ci | 3 | inventory |
| F5 | ws-hr → fileshare smb/445 | u.hr | 2 | observed |
| F6 | jump-01 → prod-db rdp/3389 | adm.ops | 3 | observed |

**Control catalogue** (8 of the ≤10 slots; costs are relative units, shown as ₹L):

| id | impacts | effect on routes | flows broken | verdict alone |
|---|---|---|---|---|
| `seg_prod_db_full` | deny `dst_assets={prod-db}`, breaks | A, B, C, D all cut at the last hop | F1, F2, F6 | **BLOCK** |
| `seg_prod_db_scoped` | same deny + exceptions for the F1, F2 **and F6** channels (`src_assets={jump-01}, protocols={rdp}, ports={3389}, identity_ids={adm.ops}`) | C cut; A, B, D survive (A through the F6 exception — that is the hole `mfa_humans` closes) | none | DEPLOY (moderate) |
| `mfa_humans` | deny `identity_kinds={user,admin}`, eff 0.9, no breakage | A, B, C degraded; D untouched | none | DEPLOY (weak alone) |
| `mfa_all` | + deny `identity_kinds={service_account}`, breaks | everything degraded | F1, F2, F4 — interactive MFA incompatible with non-interactive identities | **BLOCK** |
| `edr_cred_dump` | deny `techniques={cred_dump}`, eff 0.7 | A, B, D degraded | none | DEPLOY |
| `patch_web_dmz` | deny `techniques={exploit_public_app}, dst_assets={web-dmz}`, eff 0.95 | D cut | none | DEPLOY |
| `jump_hardening` | deny `techniques={priv_esc_local}, dst_assets={jump-01}`, eff 0.8 | A degraded | none | REVIEW (weak) |
| `disable_smb_share` | deny `dst_assets={fileshare}, protocols={smb}`, breaks | C cut | F5 (crit 2) | REVIEW |

**Demo beats this guarantees:** full segmentation → BLOCK with F1 named and route D as the
attacker's substitute; `seg_prod_db_scoped + mfa_humans` → the constrained optimum, DEPLOY,
with D still visible as the residual route and `svc.backup admin@prod-db (inferred)` as the
named unknown; naive top-N-by-paths picks `seg_prod_db_full` and breaks payroll; sync import
adds `contractor` admin@jump-01 and risk rises.

Numbers (+18%, +14%, 5 → 2) in `CLAUDE.md` §2 are targets; the real ones are pinned at hour
20 into `DEMO_SCRIPT.md` and `test_scenario.py`.

---

## Migration from the previous repo's engine (historical — done)

What exists is a v0 "BloodHound-lite": mutable Pydantic models, a NetworkX graph,
`nx.all_simple_paths` with no capability state, no identities, no controls model, and
ATT&CK labels inferred from relation strings *after* a path is found. Rule: nothing from it
is imported by new code; each file is read, ported where useful, and deleted in the PR that
adds its replacement. No two implementations alive at once.

| Existing (old repo, branch `aryan`) | What it did | Became | Owner | Kept |
|---|---|---|---|---|
| `engine/models.py` — `NodeModel`, `EdgeModel(relation, port)`, `EnvironmentModel`, `AttackPath/AttackStep`, `BlastRadiusResult` | mutable `List[...]` models; no identities | replaced by `engine/models.py` v2.1 (frozen) | all (P0) | field names `id`, `name`, `zone`; `port` on edges becomes the technique's `channel`; `is_crown_jewel` → `crown_jewel` |
| `engine/twin.py` — `DigitalTwin.load_environment`, `find_all_attack_paths` (`nx.all_simple_paths`), `compute_blast_radius` (hop distances), `export_graph_json` | graph loading, naive paths, hop-count blast radius | `engine/twin.py` (clone/hash), `engine/search.py`, `engine/blast.py` | A | `export_graph_json`'s node/edge shape for React Flow → D's `/twin/{id}` serialiser; `compute_blast_radius` → `Blast.upper_bound`. **`find_all_attack_paths` is not reusable** — it has no `(node, caps)` state and would fail the creds-two-hops fixture, which is exactly why the fixture is written first |
| `engine/simulator.py` — `AdversaryAgent._infer_attack_technique`, `simulate_attack`, `test_control_effectiveness` | maps relation → ATT&CK label after the fact; control test = remove one edge, recount, restore (mutates the graph) | `rules/techniques.yaml` + `rules/compile.py` (techniques declared on edges, not inferred); `test_control_effectiveness` **is** `naive_path_reduction_pct`, reborn as `clone → compile(naive=True) → search` | B | the ATT&CK ids it already names (T1078, T1021, T1195 → `exploit_public_app`/webhook story) |
| `server/app.py` — `/api/graph`, `/api/simulate`, `/api/test-control`, `/api/choke-points`, `/api/blast-radius`, static dashboard mount | FastAPI, CORS `*`, module-level global twin | `server/app.py` + `server/routes.py` per `docs/INTERFACES.md`; `/api/choke-points` → `Result.edge_frequency` | D | app skeleton, CORS block, scenario-dir listing → `/scenarios` |
| `scenarios/enterprise_cloud.json` — 11 nodes, 13 relation-typed edges, two crown jewels (`rds_core_banking`, `s3_customer_pii_vault`) | FinTech hybrid-cloud story; no identities, grants or flows | **not converted** for the demo — FinBank `golden.json` is written fresh in P0. Keep the file as a P4 stretch second scenario if D has time to add grants/flows | D | the CI/webhook → IAM-role escalation idea is already route D in FinBank |
| `dashboard/index.html` — 521-line static page, Tailwind from a CDN | graph visualiser served by FastAPI | replaced by the Vite + React + TS app in `dashboard/`; delete `index.html` and the static mount in the PR that adds the scaffold | C | nothing structural; reuse zone colours if they look good |
| tests | none exist | — | — | — |

Names that continued unchanged from the prototype: `zone`, `crown_jewel` (was `is_crown_jewel`),
`port`, the scenario directory `scenarios/`, the module names `engine/`, `server/`,
`dashboard/`, and `server/app.py`. Everything else is the v2.1 contract.

---

## Risk register

| Risk | Signal | Response |
|---|---|---|
| Pathfinder silently wrong | Fixture red, or numbers that feel off | Stop everything. Nothing downstream is trustworthy. |
| Compiler invents transitions | Subset test red | B stops; every path count is inflated until fixed. |
| State explosion | `SearchBudgetExceeded` on golden | Tighten depth to 6; remove a grant from the scenario, never raise the cap. |
| Python too slow | `/simulate` over 2 s | Live demo at `n=300`; precompute the rest. |
| Optimiser sweep too slow | startup precompute > 10 s | Cap catalogue at 8 controls (256 subsets). |
| Effort metric undefined | control eliminates every route | `effort_increase_pct=None`, `route_eliminated=True`, UI says "no viable route in 1000 trials". Already in the contract. |
| Optimiser and simulation disagree | `test_scenario` agreement assertion red | Same `route_policy` in both — if they differ, one of them is not using it. |
| React Flow struggles | Lag | Golden is ~10 nodes; if a generator twin lags, render the attack-surface subgraph only. |
| Contract churn after hour 12 | Someone proposes a model change | Default no; work around it. |
| Merge conflicts | Same file, two branches | Someone broke directory ownership — re-read GOVERNANCE §1. |
| Demo numbers drift | `test_scenario` red | Revert the last change; the run sheet is the spec. |
| Judge knows the field | "Isn't this just MAL?" | Approved claim, verbatim. You put MAL on slide two yourself. |
| Judge: "so your attacker is just random" | — | `CLAUDE.md` §12 answer 4. Show the top-5 route table with `p_select`. |
| Windows `curl` | PowerShell returns an object, not JSON | `curl.exe`, everywhere, always. |

---

## First prompts for each track

Paste at the start of each teammate's Claude Code session (GOVERNANCE §9 opener, then this).

**A —**
> I am track A, engine. I may only edit `engine/` and `tests/test_fixture.py`,
> `tests/test_invariants.py`. `models.py` is frozen. `search.py` and `walk.py` read only
> `CompiledEdge` tuples — never `Twin` directly. Start with `tests/test_fixture.py`: six
> nodes of hand-built `CompiledEdge`s with known paths, including one reachable only after a
> credential collected two hops earlier. Do not write `search.py` logic until the test exists
> and fails for the right reason. `route_policy` is deterministic and is called once per
> `simulate`, never once per trial.
> Verify: `pytest tests/test_fixture.py` fails with assertion errors, not import errors.

**B —**
> I am track B, rules and decisions. I may only edit `rules/`, `tests/test_rules.py`,
> `tests/test_evaluate.py`. `techniques.yaml` is frozen — I may not change its schema. In
> `compile.py`, each `Edge` has ONE declared technique; expand only over candidate grants on
> `dst`, never over other techniques. First test: compiled `(src,dst,technique)` is a subset
> of the twin's edges. Second test: scoped segmentation denies `ws-hr → prod-db` as
> `svc.payroll` and allows `backup-01 → prod-db` as `svc.backup`. Until A merges
> `route_policy`, use `rules/_stub_policy.py`.
> Verify: `pytest tests/test_rules.py` passes.

**C —**
> I am track C, frontend. I own `dashboard/` and `scripts/gen_types.py` and may not edit
> anything under `engine/`, `rules/`, `server/` or `scenarios/`. Scaffold Vite + React + TS + Tailwind, write
> `src/api/mocks.ts` returning one fake `ChangeVerdict` matching `types.ts`, then build the
> decision card exactly as CLAUDE.md §2 shows it. The card is the hero; the graph comes
> after. Do not wait for the backend.
> Verify: `npm run dev` renders the card with mock numbers.

**D —**
> I am track D, integration and data. I own `server/`, `scenarios/`, `docs/`,
> `README.md`, `tests/test_scenario.py`. Build the FastAPI app with `/twin/{id}` and
> `/simulate` returning a hardcoded `Result` from `server/stubs.py`, plus CORS for the Vite
> dev server. Then `scenarios/golden.json` v1 with the eight FinBank controls from
> `docs/IMPLEMENTATION_PLAN.md`.
> Verify: `curl.exe -X POST localhost:8000/simulate ...` returns a valid Result.

---

## A. What changed from v1, and why

| v1 | v2.1 | Reason |
|---|---|---|
| `broken_flows` = control's blocked techniques × scope ∩ flows | flows carry protocol/port/identity; controls act on channel selectors with selector exceptions | comparing an attack-technique string to a business flow proved nothing |
| `Identity` disconnected from assets | `PrivilegeGrant` (session/login/admin); techniques resolve `creds:who` through grants | brief requires identities and privileges in the twin |
| local random walk, "adaptation is emergent" | `route_policy` over the cached inventory; plan-then-execute | a local walk is not re-planning; this is honest and still keeps search out of the MC loop |
| `confidence` field, uncomputed | evidence on every grant/flow/edge; computed over decisive elements; `undetermined` | "how confident we are" is in the pitch sentence |
| greedy "optimal" | exhaustive ≤1024 subsets, same `route_policy` as the agent, no pruning | greedy misses portfolios; optimiser and simulation must tell the same story |
| `blocked / else deploy / else review` | BLOCK / REVIEW / DEPLOY rules with the `None`-effort case handled | verdict logic was wrong |
| `honest_cost_increase_pct`, "expected cost" | `effort_increase_pct`, "modelled attacker-effort score" | Σ cost/p is a heuristic; do not oversell it |
| 15 techniques | 10 | more ATT&CK entries do not improve the demo |
| hero = graph + histogram | hero = decision card | the product is a decision |
| `blast_radius.py` under B, `/matrix` under A | `engine/blast.py` under A, `/matrix` route under D | v1 violated its own ownership map |
| `nx.descendants` blast radius | `search` seeded from the fallen asset; descendants as labelled upper bound | descendants ignores credentials |
| 200-node generator in P2 | stretch only, ≤80 nodes | endangered G2 for a vanity number |
| `model_dump_json` hash | canonical dump with sorted frozensets | frozenset order is not stable across processes |
| — | `docs/INTERFACES.md`, consumer-owned stubs, GOVERNANCE §9 | four AI sessions need one explicit channel |
| — | migration from the old repo's prototype engine onto `main` | there is prior code; port what is useful, delete the rest, never fork it |
