# Status — solo build

| Gate | Done | Evidence |
|---|---|---|
| G0 Contract | yes | `engine/models.py`, `rules/techniques.yaml` (10), `docs/INTERFACES.md`, `scenarios/golden.json` |
| G1 Skeleton | yes | dashboard renders `/simulate`, `/paths` from the real API |
| G2 Engine | yes | `test_fixture.py`, `test_invariants.py`, `test_rules.py` green |
| G3 Differentiator | yes | `/evaluate-change` on `seg_prod_db_full`: BLOCK, F1 named, Medium with unknown, safer option DEPLOY; card renders it |
| G4 Freeze | yes | optimiser, sync, blast radius merged; `pytest` 35 green |
| G5 Rehearsal | partial | **fresh clone** installs, tests green, dashboard builds; CI workflow added; every run-sheet beat driven through the API in < 100 ms with no errors. **Pending (human): two timed, spoken runs of `docs/DEMO_SCRIPT.md` under four minutes; build the deck from `docs/SLIDES.md`; three screenshots; video fallback; second laptop.** |

## Phase 5 log

| Step | Result |
|---|---|
| Regression gate | `pytest` 35/35 (repo and fresh clone), `tsc -b` clean, `npm run build` clean |
| CI | `.github/workflows/ci.yml`: pytest + dashboard build on every push |
| Mechanical rehearsal | load 18 ms · paths 13 · simulate 17 · evaluate cold 8 / cached 9 · optimise b=12 57 · sync 6 · blast 5 · matrix 94 |
| Demo polish | graph no longer zooms when the page scrolls (`zoomOnScroll={false}`) |
| Bug bash: insider profile | 2 paths, 3-hop favourite, scoped segmentation DEPLOY +49%; card/graph render |
| Slides | content prepared in `docs/SLIDES.md`; screenshots for backup slides 4–6 still to take |
