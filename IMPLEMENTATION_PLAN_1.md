# Implementation plan — phased, with verifiable exits

Six phases. Each has an **exit criterion that is a command someone runs**, not a feeling.
Nobody advances a phase on "it looks done."

Hours are from kickoff and assume ~24 hours of real build time. If the event is 36, the
slack goes into Phase 5, not into new features.

---

## Phase 0 — Contract (hour 0 → 1) · ALL FOUR TOGETHER

Nobody writes feature code. This hour is what makes the next twenty parallel.

**Do:**

1. `git init`, push to GitHub, add `.gitignore`, invite all four, protect `main`.
2. Write `backend/core/models.py` together, on a screen everyone can see. Copy from
   `CLAUDE.md` §5. Argue about it now, never later.
3. Write the first ten entries of `backend/rules/techniques.yaml` together, each with a
   real MITRE ATT&CK ID.
4. Agree the golden scenario in words: which assets, which crown jewel, which service
   flow will be the one that segmentation breaks. **Design the story before the data.**
5. C generates `frontend/src/types.ts` from the models.
6. Everyone clones, installs, and confirms `pytest` and `npm run dev` both start.

**Exit — all four must pass:**

```bash
python -c "from backend.core.models import Twin; print(Twin.model_json_schema())"
pytest --collect-only          # collects, zero errors
cd frontend && npm run dev     # serves
```

**Trap:** designing the data model before deciding the demo story. The story tells you
which fields you actually need. A `ServiceFlow` exists because segmentation must break
something visible — not because flows are conceptually nice.

---

## Phase 1 — Walking skeleton (hour 1 → 4) · PARALLEL

End-to-end pipe with fake logic inside. **Do not skip this phase.** Proving the frontend
can call the real backend at hour 4 turns integration from an hour-18 catastrophe into an
hour-4 annoyance.

| Track | Builds |
|---|---|
| **A** | `core/twin.py` — `clone()`, deterministic twin hashing. `core/results.py` — `Result`, `Delta`, `ChangeVerdict` as frozen types returning hardcoded values. |
| **B** | `rules/loader.py` — YAML → technique table, validated against the models. |
| **C** | Vite + React + TS + Tailwind scaffold. `api/mocks.ts` with one fake `Result`. Dashboard renders the numbers from the mock. |
| **D** | FastAPI app, `/twin/{id}` and `/simulate` returning the hardcoded `Result`. CORS. `data/scenarios/golden.json` — 20 nodes, hand-written, correct shape. |

**Exit (Gate G1):**

```bash
curl localhost:8000/simulate -X POST -d '{"twin_id":"golden","agent_id":"external","n":100}'
# returns a valid Result
```

and the frontend dashboard displays those numbers **fetched from the real API**, mocks
switched off. Demo it to each other, screen shared. If the numbers on screen came from
`mocks.ts`, the gate has not passed.

---

## Phase 2 — Engine correctness (hour 4 → 9) · A leads, others parallel

The only phase where wrong code is invisible. Everything downstream inherits its errors.

**A — in this exact order:**

1. **`tests/test_fixture.py` FIRST, before `search.py` exists.** Hand-build a 6-node graph
   on paper where every valid path is known by inspection, including one path reachable
   *only* after collecting a credential two hops earlier. Assert exact path counts.
2. `core/search.py` — complete path search. State is
   `(node, frozenset(capabilities_held))`. Dedupe on the **full state**, not the node.
   Hard caps `max_depth=8`, `max_states=5000`, raising a loud exception rather than
   hanging. Loop until the fixture is green.
3. `core/walk.py` — sampled agent walk. At each step enumerate only edges admissible from
   the current position given held capabilities; score; pick probabilistically; move.
   Seeded RNG.
4. `tests/test_invariants.py` — three properties: adding a control never increases
   attacker success; `clone` never mutates its input; identical seed gives identical output.

**In parallel:** B builds the technique table to 15 entries and starts `evaluate.py`.
C builds the React Flow graph view and the attack-path animation against mocks.
D builds `data/generator.py` producing a 200+ node synthetic environment.

**Exit (Gate G2):**

```bash
pytest tests/test_fixture.py tests/test_invariants.py -v   # all green on main
```

**Traps.** Running the state-space search inside the Monte Carlo loop — measured as an
order-of-magnitude error; they are separate functions for separate jobs. Deduping on node
rather than on `(node, capabilities)` — silently drops valid paths. Letting an AI session
generate `search.py` before the fixture test exists — it will produce confident, plausible,
wrong code and you will not notice for fifteen hours.

---

## Phase 3 — The differentiator (hour 9 → 14) · B leads

Where the product stops being a clone of BloodHound.

**B:**

1. `evaluate.py` → `evaluate_change(twin, controls, agents)`:
   - clone the twin with the control applied
   - run both algorithms on before and after
   - compute `naive_path_reduction_pct` (**required by the brief — ship it**)
   - compute `honest_cost_increase_pct` from the attacker-cost distributions
   - compute `substituted_paths` — present in `after`, absent in `before`
   - **`broken_flows`** — intersect the control's blocked techniques × scope with the
     twin's `ServiceFlow` set. Roughly 40 lines, and it is the entire differentiator.
   - `recommendation`: `blocked` if any broken flow has `criticality >= 4`, else `deploy`,
     else `review`.
2. `core/blast_radius.py` — `nx.descendants`, one line, plus asset criticality rollup.

**A:** performance — pre-sample RNG in bulk, make `n=1000` return under a second.
**C:** the what-if view and the **overlaid before/after attacker-cost histograms** in
Recharts. That chart is the thesis made visible; give it real design time.
**D:** `cache.py` content-addressed on `(twin_hash, agent_id, seed, n)`; startup precompute
of the golden scenario.

**Exit (Gate G3):**

```bash
curl localhost:8000/evaluate-change -X POST \
  -d '{"twin_id":"golden","control_ids":["net_seg"],"agent_ids":["external"]}'
```

returns both metrics, a non-empty `broken_flows`, and `recommendation: "blocked"` — and
the frontend renders all three. **If segmentation does not break a flow in the golden
scenario, the scenario is wrong, not the code.** Fix the data.

---

## Phase 4 — Optimiser and matrix (hour 14 → 18)

**B:** `optimize.py` — greedy selection maximising risk reduction subject to budget AND
never breaking a flow with `criticality >= 4`. Report both the naive top-N-by-rank
portfolio and the constrained-optimal one, so the demo can contrast them.
**A:** `/matrix` — controls × agents risk reduction, three adversary profiles.
**C:** optimiser view, matrix heatmap, blast-radius view, lineage tree.
**D:** sync demo (re-import a modified JSON, risk goes **up**), pre-generated and cached
LLM path narration, `tests/test_scenario.py`.

**Exit (Gate G4 — FEATURE FREEZE, hour 18):**

```bash
pytest                    # everything green
git log origin/main -1    # last feature merge
```

Everything merged. **No new features after this line, ever.** Every hackathon team breaks
its demo in the last three hours by adding one more thing.

---

## Phase 5 — Hardening and rehearsal (hour 18 → 24) · ALL FOUR

Bugs and polish only. The product is done; now make it survivable.

- **Hour 18–20:** bug bash. Everyone clicks everything, on a fresh clone. Fix breaks,
  add nothing. Build the "reset demo" button — you will use it between judging panels.
- **Hour 20–21:** `test_scenario.py` pinned to the exact numbers in the run sheet. If a
  late fix shifts a headline number, you find out here rather than on stage.
- **Hour 21–22 (Gate G5):** full rehearsal, timed, under four minutes. Twice. A presents
  the technical answers; rehearse the three questions below out loud.
- **Hour 22–23:** slides. Prior-art table from `CLAUDE.md` §3 goes on slide two — naming
  MAL and Azure yourself is what makes the narrow claim survive Q&A.
- **Hour 23–24:** screen-record a clean run as video fallback. Second laptop running the
  same build. Sleep if anyone can.

**Rehearse these three answers:**
1. *"How is this different from BloodHound / XM Cyber?"* → the approved claim, verbatim.
2. *"How does your pathfinder handle cycles / state explosion?"* → A answers from memory.
3. *"Your model could be wrong — so what?"* → confidence scoring, and that the twin is fed
   from inventory exports, so accuracy is an ingestion problem not a modelling one.

---

## Critical path

```
models.py ──▶ search.py ──▶ walk.py ──▶ evaluate_change ──▶ optimize
   (P0)        (P2)          (P2)          (P3)              (P4)
```

Everything else — frontend, generator, API, cache, matrix, blast radius — is off the
critical path and can slip without killing the demo. **If A is blocked, the project is
blocked**, and that is the one situation where everyone else drops their track and helps.

---

## Risk register

| Risk | Signal | Response |
|---|---|---|
| Pathfinder silently wrong | Fixture red, or numbers that feel off | Stop everything. Nothing downstream is trustworthy. |
| State explosion | `max_states` exception | Tighten depth to 6, prune low-probability edges |
| Python too slow | `/simulate` over 2s | Live demo at `n=200`; precompute the rest |
| React Flow struggles | Lag at 200 nodes | Render only the attack-surface subgraph, not full inventory |
| Contract churn after hour 12 | Someone proposes a model change | Default no; work around it |
| Merge conflicts | Same file, two branches | Someone broke directory ownership — re-read GOVERNANCE §1 |
| Demo numbers drift | `test_scenario` red | Revert the last change; the run sheet is the spec |
| Judge knows the field | "Isn't this just MAL?" | Approved claim, verbatim. You put MAL on slide two yourself. |

---

## First prompts for each track

Paste at the start of each teammate's Claude Code session.

**A —**
> Read CLAUDE.md and docs/GOVERNANCE.md. I am track A, engine. I may only edit
> `backend/core/` and `backend/tests/`. Do not touch `models.py` — it is a frozen
> contract. Start with `tests/test_fixture.py`: a 6-node graph with known answers,
> including one path reachable only after a credential collected two hops earlier. Do not
> write `search.py` until the test exists and fails for the right reason.
> Verify: `pytest tests/test_fixture.py` fails with assertion errors, not import errors.

**B —**
> Read CLAUDE.md and docs/GOVERNANCE.md. I am track B, rules and decisions. I may only
> edit `backend/rules/`. `techniques.yaml` is a frozen contract — I may add entries in
> the agreed format but not change the schema. Build `loader.py` first.
> Verify: `pytest tests/test_rules.py` passes and every technique has an ATT&CK ID.

**C —**
> Read CLAUDE.md and docs/GOVERNANCE.md. I am track C, frontend. I own `frontend/`
> entirely and may not edit anything under `backend/`. Scaffold Vite + React + TS +
> Tailwind, then write `src/api/mocks.ts` returning one fake Result matching `types.ts`,
> then build the dashboard against it. Do not wait for the backend.
> Verify: `npm run dev` renders the dashboard with mock numbers.

**D —**
> Read CLAUDE.md and docs/GOVERNANCE.md. I am track D, integration and data. I own
> `backend/api/`, `backend/data/` and `docs/`. Build the FastAPI app with `/twin/{id}` and
> `/simulate` returning a hardcoded Result, plus CORS for the Vite dev server.
> Verify: `curl localhost:8000/simulate -X POST -d '{...}'` returns a valid Result.

---

## What this Claude session builds next, if asked

The base every other track builds around: repo skeleton, `models.py`, the ten-technique
YAML, `twin.py` with `clone()` and hashing, `results.py`, the failing `test_fixture.py`,
the FastAPI app returning hardcoded results, the Vite scaffold with `types.ts` and mocks,
`.gitignore`, CI workflow, and `README.md`.

That is Phase 0 plus most of Phase 1 — so the team opens the repo at hour zero with the
contract already frozen and the skeleton already walking, and spends their first hour
reading rather than scaffolding.
