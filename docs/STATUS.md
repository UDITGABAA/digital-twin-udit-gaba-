# Status — solo build

| Gate | Done | Evidence |
|---|---|---|
| G0 Contract | yes | `engine/models.py`, `rules/techniques.yaml` (10), `docs/INTERFACES.md`, `scenarios/golden.json` |
| G1 Skeleton | yes | dashboard renders `/simulate`, `/paths` from the real API |
| G2 Engine | yes | `test_fixture.py`, `test_invariants.py`, `test_rules.py` green |
| G3 Differentiator | yes | `/evaluate-change` on `seg_prod_db_full`: BLOCK, F1 named, Medium with unknown, safer option DEPLOY; card renders it |
| G4 Freeze | yes | optimiser, sync, blast radius merged; `pytest` 35 green |
| G5 Rehearsal | pending | run `docs/DEMO_SCRIPT.md` twice under four minutes |
