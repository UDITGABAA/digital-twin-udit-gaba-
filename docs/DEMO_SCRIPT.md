# Demo run sheet — under four minutes

Numbers below are **pinned by `tests/test_scenario.py`** (seed 1, n = 1000, agent *External
criminal crew*). If `pytest` is green, these are the numbers on stage. Rehearsed numbers equal
stage numbers.

Before the panel: `uvicorn server.app:app --port 8000` and `npm run dev --prefix dashboard`,
open http://localhost:5173, click **reset demo**. Second laptop running the same build.

| # | Time | Beat | Click | Say | Numbers on screen |
|---|---|---|---|---|---|
| 0 | 0:00 | Prior art | slide 2 | "Attack-path tools tell you a control helps. Cloud analyzers tell you it breaks something. Neither tells you both about the same change." Name MAL Simulator and Azure's rule impact analyzer yourself. | — |
| 1 | 0:30 | Environment model | scenario **FinBank (golden)** | "Ten assets in five zones, six identities and their privileges, six legitimate flows that must keep working, ten ATT&CK techniques in YAML. Every element carries its evidence." Point at the green dashed flows. | **8 critical paths** · p(success) **0.89** [0.86–0.90] · mean effort **8.1** |
| 2 | 1:00 | Attack paths + simulation | hover the status bar | "The brief asks for paths eliminated — we count them, controls treated as perfect. Our agent also scores the feasible routes and picks among the best five, a thousand seeded times. Its favourite: phish HR, dump, hit the file share, find the payroll credential, log into the database." | top route `phish › cred_dump › smb_lateral › creds_in_files › db_login` (p_select 0.63) |
| 3 | 1:30 | **The verdict** | tick **Segment prod-db (deny all inbound)** | "Segment the database. Industry metric: 8 paths → 0, minus 100%. Success drops 0.89 → 0.10. And it **severs Payroll API → core DB, a P1 flow** — plus backup and ops maintenance. Verdict: BLOCK. Confidence Medium, because the backup account's admin right on the database is inferred, not observed." | paths **8 → 0** · effort **+14%** · p **0.89 → 0.10** · BREAKS **F1 (P1), F2 (P2), F6 (P3)** · confidence **Medium (0.83)** · **BLOCK** |
| 4 | 2:15 | Safer option | click the **Safer option** row | "The sandbox already found a cheaper change that breaks nothing: MFA on human accounts plus patching the portal. Effort +22%, success 0.89 → 0.23, cost 5 not 8, DEPLOY. And here is the route the attacker takes instead — through the web portal to the CI runner, with no human credential anywhere on it." Route D animates amber on the graph. | **DEPLOY** · effort **+22%** · p **→ 0.23** · new route `internet → web-dmz → ci-runner → backup-01 → prod-db` |
| 4b | 2:45 | Scoped alternative (if asked) | tick **Segment prod-db (allow…)** + **MFA for user and admin accounts** | "Scope the segmentation to the two workloads and the ops path that legitimately need the database; add MFA to humans — interactive MFA is incompatible with the service identities, so we don't apply it to them. No flow affected, effort +38%, DEPLOY, and route D is still the residual — the exception for the backup server is a real hole, and we show it." | paths **8 → 1** · effort **+38%** · p **→ 0.24** · no flows · **DEPLOY** |
| 5 | 3:00 | Prioritisation | budget **5**, **optimise** | "Rank by paths eliminated and you buy MFA-for-everything and kill the share: it breaks payroll, backup, CI and HR. Constrained to never breaking a P1/P2 flow, scoring all 47 portfolios, the optimum is MFA-humans plus the patch." | naive = `mfa_all + disable_smb_share` breaks **F1 F2 F4 F5** · constrained = `mfa_humans + patch_web_dmz` breaks nothing |
| 6 | 3:30 | Continuous sync + blast radius | scenario **FinBank after sync**; click **jump-01** | "Inventory re-import: a contractor now has admin on the jump host. Success 0.89 → 0.95 with nothing else changed. Click the jump host: with its sessions an attacker reaches the backup server and the crown jewel." | p **0.89 → 0.95** (+0.06) · blast(jump-01) = backup-01, prod-db |
| — | 3:50 | Close | back to the card | "What can I deploy safely, within budget, and how sure are we. That is the change board's question, and that is the screen." | — |

## Judge Q&A — rehearsed

1. **"How is this different from BloodHound / XM Cyber?"** → the approved claim in CLAUDE.md §3, verbatim.
2. **"Cycles / state explosion?"** → state is `(node, held capabilities)`, deduped on the full state; simple paths; an edge is admissible from any held foothold; hard caps `max_depth=8`, `max_paths=5000` that raise instead of hanging.
3. **"Your model could be wrong — so what?"** → "Decision support, not a guarantee. Every grant, flow and edge carries evidence; confidence is computed over the elements that decided this verdict; if one is merely assumed we say *cannot be determined* and never DEPLOY."
4. **"Isn't the agent just a random walk?"** → "No. It scores every feasible route (success × effort × noise), keeps the best five, picks with probability sharpened by skill. Change the twin and the feasible set changes — that is the substituted route you saw."
5. **"Why does effort go *down* for some controls?"** → "Because when you degrade the hard route the agent stops wasting attempts on it and picks the easy one more often — the surviving successes are cheaper. That is exactly why the verdict for *harden the jump host alone* is REVIEW, not DEPLOY. Path count would have called it a 62% win."
6. **"Why is the optimiser's score higher than the simulation's?"** → "The deterministic score ignores detection during retries; it is an upper bound and the test pins it within 15% of the simulation."
7. **"Why does scoped segmentation still leave a route?"** → "Because the backup server is legitimately allowed to reach the database. The exception is a real hole; we show it and call it a residual, not 'secure'."
