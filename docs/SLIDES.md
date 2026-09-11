# Slides — eight, no more

The demo is the pitch; slides bracket it. Slides 1–3 before the demo (90 s), 7–8 after (30 s).
Slides 4–6 exist only as backup if the laptop dies (screenshots of the three card states).

---

## 1 — Title

**Security Change Sandbox** — a digital twin that answers the change board's question.
*What can I deploy safely, within budget, and how sure are we?*
PS #13 · Security Digital Twin for Threat Vector Assessment

## 2 — Prior art (say this before a judge does)

| | Finds attack paths | Simulates the attacker | Tells you what a control **breaks** | Both, for one proposed change |
|---|---|---|---|---|
| BloodHound Enterprise, XM Cyber, MS Exposure Mgmt, Wiz | ✅ | — | — | — |
| MAL Simulator (KTH), CAGE / CybORG | ✅ | ✅ adaptive, RL | — | — |
| Azure VNM rule impact analyzer, AWS IAM simulator, MS CA report-only | — | — | ✅ | — |
| **This** | ✅ | ✅ route selection over the twin | ✅ same selectors on legitimate flows | ✅ |

Approved wording, verbatim: *"Adaptive attacker modelling exists in research — MAL Simulator,
the CAGE challenges. Control impact simulation exists in cloud platforms — Azure's rule impact
analyzer. To our knowledge no product joins security benefit and business breakage on one
model for a single proposed change, which is the decision a change board actually makes."*

## 3 — How it works (one diagram)

```
twin (assets · identities · privilege grants · reachability edges · legitimate flows)
  → compile: edge × its declared ATT&CK technique × grants → attack edges  (never invents a transition)
  → complete path search, once, cached                       → "N critical paths" (the brief's metric)
  → agent scores routes, keeps 5, picks by skill, 1000 seeded trials → p(success), attacker effort
  → propose a control = the same selector applied to attack edges AND to payroll/backup/ops flows
  → verdict: BLOCK · REVIEW · DEPLOY, with computed confidence and a safer alternative
```
Ten techniques, each a real MITRE ATT&CK id, in YAML. Every grant, flow and edge carries evidence.

## 4 — (backup) The BLOCK card
Screenshot: *Segment prod-db (deny all inbound)* → paths 8 → 0, effort +14 %, p 0.89 → 0.10,
BREAKS Payroll API → core DB (P1), backup (P2), ops RDP (P3), confidence Medium, BLOCK,
safer option DEPLOY.

## 5 — (backup) The DEPLOY card with the attacker's new route
Screenshot: *MFA for humans + patch the portal* → +22 %, p → 0.23, no flow affected, DEPLOY,
route `internet → web-dmz → ci-runner → backup-01 → prod-db` highlighted.

## 6 — (backup) The optimiser contrast
Screenshot: budget 5 — rank-by-paths buys MFA-for-everything + kill the share (breaks F1 F2 F4
F5); the constrained optimum buys MFA-humans + patch (breaks nothing).

## 7 — Why path count misleads (the thesis, one line each)

- Path count assumes a **perfect control** and a **passive attacker**. We show it anyway — it is the brief's metric — labelled *industry metric*.
- Our agent re-selects among the routes that remain. *Harden the jump host* eliminates 62 % of paths and **raises** attacker success — because the attacker stops wasting time on the hard route. Verdict: REVIEW.
- A control that breaks payroll is not a security win. Verdict: BLOCK, whatever the path count says.
- Confidence is computed, not asserted: *svc.backup admin on prod-db — inferred.* If something is merely assumed we say *cannot be determined* and never DEPLOY.

## 8 — What we did not build, on purpose

No scanner, no exploits, no LLM adversary (seeded Monte Carlo is reproducible; rehearsed
numbers equal stage numbers), no cloud. Twin fed from inventory exports; sync = re-import.
35 tests; `test_scenario.py` pins every number you just saw.

Ask us: cycles and state explosion · why effort can go down · why scoped segmentation still
leaves a route · what "upper bound" means on the optimiser.
