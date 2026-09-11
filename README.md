# Security Change Sandbox — MUJ HackX 4.0, PS #13

> Attack-path tools tell you a control helps. Cloud policy analyzers tell you a control
> breaks something. Neither tells you both about the same change. Propose a control and see
> the attacker's new route, the business flows you would sever, the cost, and how confident
> we are — before you deploy.

Read in this order: [`CLAUDE.md`](CLAUDE.md) (the contract) → [`docs/GOVERNANCE.md`](docs/GOVERNANCE.md)
(who edits what, how AI sessions talk) → [`docs/INTERFACES.md`](docs/INTERFACES.md) (signatures
between tracks) → [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) (phases, gates,
the FinBank scenario) → [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).

## Architecture

```
                     golden.json  (FinBank twin: assets, identities, grants, edges, flows, controls)
                          │
                          ▼
                 ┌──────────────────┐
                 │  frozen Pydantic │   engine/models.py — the contract
                 │       Twin       │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐   rules/compile.py
                 │     COMPILER     │   Edge → its one technique → × grants on dst → × control impacts
                 │  never invents a │   deny/exception selectors act on channels
                 │    transition    │   (attack edges and legit flows share them)
                 └────────┬─────────┘
                          │  CompiledEdge[]
              ┌───────────┴───────────┐
              ▼                       ▼
     ┌─────────────────┐     ┌─────────────────┐
     │ COMPLETE SEARCH │     │  route_policy   │   engine/search.py · engine/walk.py
     │ (node, caps)    │────▶│  top-5 routes   │   search once per twin, cached
     │ once, cached    │     │  plan → execute │   1000 seeded trials, never search inside
     └────────┬────────┘     └────────┬────────┘
              │ path inventory        │ Result
              │ naive path count      │ p_success · effort · substituted routes
              └───────────┬───────────┘
                          ▼
                 ┌──────────────────┐   rules/evaluate.py  — the centrepiece
                 │  EVALUATE CHANGE │
                 │  security Δ      │   naive_path_reduction_pct (brief) + effort_increase_pct (ours)
                 │  broken flows    │   same selectors, applied to ServiceFlows
                 │  confidence      │   computed from evidence on the decisive elements
                 └────────┬─────────┘
                          ▼
                DEPLOY · REVIEW · BLOCK  + safer alternative
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
     ┌─────────────────┐     ┌─────────────────┐
     │    OPTIMIZER    │     │    DASHBOARD    │   decision card first; graph, histograms,
     │ exhaustive ≤1024│     │  React + Flow   │   matrix, blast radius, lineage beneath
     │ same policy     │     │  + Recharts     │
     └─────────────────┘     └─────────────────┘
```

## Run

One command (installs, tests, builds, opens both servers):
```bash
powershell -ExecutionPolicy Bypass -File scripts/demo.ps1
```
(macOS/Linux: `bash scripts/demo.sh`.) By hand:
```bash
pip install -r requirements.txt
```
```bash
python -m uvicorn server.app:app --port 8000
```
```bash
npm install --prefix dashboard && npm run dev --prefix dashboard
```
Open http://localhost:5173. The dashboard proxies `/api` to `:8000`.

**Fallback if Vite misbehaves on stage:** `npm run build --prefix dashboard` once, then
`uvicorn` alone serves the built dashboard at http://localhost:8000 (API under `/api`).

```bash
pytest
```
35 tests: engine fixture + invariants, rules (compiler never invents a transition, scoped
segmentation semantics), evaluate (verdict rules, confidence), and `test_scenario.py`, which
pins every number in `docs/DEMO_SCRIPT.md`.

Regenerate the FinBank scenario after editing `scripts/build_golden.py`:
```bash
PYTHONPATH=. python scripts/build_golden.py
```

Localhost only. Two terminals. Second laptop as hot backup. `curl.exe`, not `curl`, on
Windows.

## Status

Built solo on `main` of this repo. Critical path complete: `models -> compile -> search ->
walk -> evaluate_change -> optimize`, FastAPI surface, dashboard (decision card, graph,
effort histograms, optimiser, sync, blast radius). Cut for solo: `/matrix` view, lineage
view, generated `types.ts` (hand-written), CI workflow.

## Claims we make and do not make

See `CLAUDE.md` §3. Attacker route selection exists in research (MAL Simulator, CAGE);
control-impact simulation exists in cloud platforms (Azure VNM rule impact analyzer). To our
knowledge no product joins security benefit and business breakage on one model for a single
proposed change — which is the decision a change board actually makes.
