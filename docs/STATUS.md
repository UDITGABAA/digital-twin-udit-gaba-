# Status — solo build

| Gate | Done | Evidence |
|---|---|---|
| G0 Contract | yes | `engine/models.py`, `rules/techniques.yaml` (10), `docs/INTERFACES.md`, `scenarios/golden.json` |
| G1 Skeleton | yes | dashboard renders `/simulate`, `/paths` from the real API |
| G2 Engine | yes | `test_fixture.py`, `test_invariants.py`, `test_rules.py` green |
| G3 Differentiator | yes | `/evaluate-change` on `seg_prod_db_full`: BLOCK, F1 named, Medium with unknown, safer option DEPLOY; card renders it |
| G4 Freeze | yes | optimiser, sync, blast radius merged; `pytest` 35 green |
| G5 Rehearsal | partial | **fresh clone** installs, tests green, dashboard builds; CI workflow added; every run-sheet beat driven through the API in < 100 ms with no errors. **Pending (human): two timed, spoken runs of `docs/DEMO_SCRIPT.md` under four minutes; build the deck from `docs/SLIDES.md`; three screenshots; video fallback; second laptop (`scripts/demo.ps1` does the whole setup).** |

## Phase 5 log

| Step | Result |
|---|---|
| Regression gate | `pytest` 35/35 (repo and fresh clone), `tsc -b` clean, `npm run build` clean |
| CI | `.github/workflows/ci.yml`: pytest + dashboard build on every push |
| Mechanical rehearsal | load 18 ms · paths 13 · simulate 17 · evaluate cold 8 / cached 9 · optimise b=12 57 · sync 6 · blast 5 · matrix 94 |
| Demo polish | graph no longer zooms when the page scrolls (`zoomOnScroll={false}`) |
| Bug bash: insider profile | 2 paths, 3-hop favourite, scoped segmentation DEPLOY +49%; card/graph render |
| Bug-fix pass | (1) invariant re-stated and tested for all 8 controls x 2 agents: no route p_route rises, best route never rises, naive count never rises; (2) `/evaluate-change` 422 on empty proposal; (3) negative effort in amber; (4) reset clears the since-last-twin delta; (5) error banner clears on success; (6) blast panel separates "can exfiltrate to internet"; (7) histogram caption; (8) INTERFACES/CLAUDE §7/GOVERNANCE tree match the code; branch is `main` everywhere |
| Hardening 2 | determinism proven under PYTHONHASHSEED 0/1/4242/987654321 (scenario test green, twin hash identical); single-process fallback (`uvicorn` alone serves the built dashboard at :8000, API under `/api`) verified in the browser; global JSON error handler; `scripts/demo.ps1` / `demo.sh` install-test-build-start |
| Immersive dashboard (owner-approved G4 exception) | Operate-mode redesign on the skills in `D:\projects\skills` (impeccable craft floor + operate mode, taste-skill security register): tokens, one typeface, drawn icons, zone-lane stage with breach states, **attack replay** driven by a new `trace()` that shares `simulate()`'s trial loop (pinned numbers unchanged: 886/1000 = 0.886), `/trace` endpoint. Verified: replay 9/12 baseline vs 2/12 under full segmentation |
| Slides | content prepared in `docs/SLIDES.md`; screenshots for backup slides 4–6 still to take |
