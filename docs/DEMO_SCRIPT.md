# Demo run sheet — under four minutes

D drives. A and B stand by for questions. Numbers marked `__` are pinned at hour 20 by
`tests/test_scenario.py`; until then they are targets. **Rehearsed numbers must equal
stage numbers** — seed is fixed, cache is warm from startup precompute.

Reset between panels: the reset button (loads `golden`, clears lineage). Video fallback on
the second laptop.

| # | Beat | Screen | Say | Numbers |
|---|---|---|---|---|
| 0 | 0:00 | Slide 2: prior-art table | "Attack-path tools tell you a control helps. Cloud analyzers tell you it breaks something. Neither tells you both about the same change." Name MAL and Azure yourself. | — |
| 1 | 0:30 | Load `golden` (FinBank). Graph view, zones coloured, `prod-db` marked. | "Ten assets, six identities, their privileges, six legitimate flows that must keep working. All from an inventory export, each item tagged with its evidence." | `__` critical paths to prod-db |
| 2 | 1:00 | Attack paths panel: routes A–D animated. External adversary, 1000 trials. | "The brief asks for paths eliminated — we count them. Our agent also selects among the best five routes and we run it a thousand times." | p_success `__`, mean effort `__` |
| 3 | 1:30 | **Propose `seg_prod_db_full`** → decision card. | "Segment the database. Industry metric: paths `__` → `__`. Attacker effort +`__`%. But — it severs Payroll API → prod-db, a P1 flow. Verdict: BLOCK. And here is the route the attacker takes instead." Route D animates. | paths `__`→`__`, effort +`__`%, F1 in broken flows, confidence Medium, unknown = svc.backup admin@prod-db inferred |
| 4 | 2:15 | Click **Safer option** → `seg_prod_db_scoped + mfa_humans`. Card. | "Scope the segmentation to the two workloads that need the database, add MFA to human accounts — this interactive MFA policy is incompatible with the service identities, so we do not apply it to them. No P1 flow affected. Effort +`__`%. DEPLOY. Confidence Medium because one privilege is inferred, not observed — we tell you which." | effort +`__`%, broken flows none, DEPLOY |
| 5 | 3:00 | Optimiser view: naive top-N vs constrained, budget `__`. Overlaid effort histograms. | "Rank by paths eliminated and you buy full segmentation and break payroll. Constrained to never breaking a P1 flow, the exhaustive optimum is the scoped pair." | naive = `seg_prod_db_full`; constrained = scoped + mfa_humans |
| 6 | 3:30 | Load `golden_sync` — contractor gains admin@jump-01. Risk rises. Lineage tree shows both twins. | "The environment changed; the twin re-synced; risk went up `__`%. Every what-if is a child in the lineage." | weighted risk `__` → `__` |
| — | 3:50 | Back to card. | "What can I deploy safely, within budget, and how sure are we. That is the change board's question, and that is the screen." | — |

## Judge Q&A — rehearsed (CLAUDE.md §12)

1. BloodHound / XM Cyber → approved claim, verbatim. (D)
2. Cycles / state explosion → `(node, caps)` dedupe, simple paths, hard caps that raise. (A)
3. "Your model could be wrong" → decision support, not a guarantee; evidence on every element;
   confidence computed over what decided the verdict; "cannot be determined" when assumed. (B)
4. "Random walk?" → not random: top-5 route table with `p_select` on screen. (A)
5. "Why does scoped segmentation still leave route D?" → because backup-01 is legitimately
   allowed to reach the database — the model shows the hole that the exception creates. That
   is the honest answer, and it is why the verdict is DEPLOY with a named residual, not
   "secure". (B)

## test_scenario.py pins (hour 20)

```
golden / external / seed 1 / n 1000
  naive critical paths                     = __
  p_success                                = __   (ci __ – __)
  mean_effort                              = __
seg_prod_db_full
  naive_path_reduction_pct                 = __
  effort_increase_pct                      = __   (or route_eliminated = True)
  broken_flows                             = [F1, F2, F6]
  recommendation                           = blocked
  confidence.level                         = Medium
  substituted_paths contains route D       = True
seg_prod_db_scoped + mfa_humans
  effort_increase_pct                      = __
  broken_flows                             = []
  recommendation                           = deploy
optimize(budget=__)
  constrained                              = [seg_prod_db_scoped, mfa_humans]
  naive                                    = [seg_prod_db_full, ...]
  |optimiser risk - simulated p_success×5| < 0.05
golden_sync
  weighted_risk > golden.weighted_risk     = True
```
