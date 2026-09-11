# Security Change Sandbox — MUJ HackX 4.0

**Every session, every teammate, reads this file first.** It is the shared brain.
Detail lives in `docs/`. This file holds only what must never drift.

- Full build plan → `docs/IMPLEMENTATION_PLAN.md`
- Branching, ownership, PR rules, AI-session protocol → `docs/GOVERNANCE.md`
- Cross-track function signatures → `docs/INTERFACES.md`
- Demo run sheet → `docs/DEMO_SCRIPT.md`
- Slide content (8 slides, prior-art table on slide 2) → `docs/SLIDES.md`
- Gate status and Phase 5 log → `docs/STATUS.md`

---

## 0. Working agreement for AI sessions

You are one of four parallel workstreams. Others are editing this repo right now.

1. **Read `docs/GOVERNANCE.md` and `docs/INTERFACES.md` before writing any file.** You may only
   create or edit files inside the directory your track owns. If a task needs a file outside
   it, stop and say so — do not edit it.
2. **`engine/models.py` and `rules/techniques.yaml` are frozen contracts.**
   Never modify them without an explicit instruction saying the team agreed. Changing a
   contract breaks three other people silently.
3. **Simplest thing that works.** No abstractions for single-use code, no configurability
   nobody asked for, no error handling for impossible states. If it's 200 lines and could
   be 50, rewrite it.
4. **Surgical edits.** Touch only what the task requires. Don't reformat, don't refactor
   working code, don't "improve" neighbouring functions. Match existing style.
5. **Every task ends in a verifiable check.** State it up front: "verify: `pytest
   tests/test_fixture.py` passes". Loop until it does. Never report done without running it.
6. **Surface confusion instead of guessing.** If the spec is ambiguous, name the ambiguity
   and ask. A wrong assumption here costs four people, not one.
7. **If you need a function another track owns and it is not in `docs/INTERFACES.md`, stop
   and say so.** Do not invent a signature.

---

## 1. Context

**Event:** MUJ HackX 4.0. Official format 36 hours; plan against ~24 hours of real build
time. Team of four, working in parallel on GitHub branches. Strong CS ability, little
formal cybersecurity background — the domain is being learned during the build.

**Problem statement:** CyberSecurity & Defence System, **PS #13 — Security Digital Twin
for Threat Vector Assessment**.

Verbatim requirements. Every one must be visibly satisfied:

- **Environment modelling** — assets, network reachability, identities, privileges and
  existing controls as a queryable model.
- **Attack path discovery** — the chains by which an initial foothold escalates to a
  critical asset.
- **Agent based simulation** — adversary agents with defined capabilities run against the
  twin, recording which paths succeed.
- **Control effectiveness testing** — quantify how much a proposed control would reduce
  reachable paths *before it is purchased*.
- **Prioritisation** — rank remediation by **the number of critical paths it eliminates**
  rather than by raw vulnerability count.
- **Continuous synchronisation** — update the twin as the environment changes.
- **Bonus** — blast radius: for any asset, what an attacker reaches next if it falls.

---

## 2. Product thesis

Not "another tool that finds attack paths." A **security change sandbox**.

> Attack-path tools tell you a control helps. Cloud policy analyzers tell you a control
> breaks something. Neither tells you both about the same change. Propose a control and
> see the attacker's new route, the business flows you would sever, the cost, and how
> confident we are — before you deploy.

The decision we serve is the change advisory board's: *what can I deploy safely, within
budget, and how sure are we?*

**The hero screen is a decision, not a graph.** Everything else is a supporting panel.

```
Proposed        Segment prod-db (deny all inbound)
Security        +18% modelled attacker effort   ·   critical paths 5 → 2 (industry metric)
Attacker route  phish → ci-runner → backup-01 (svc.backup) → prod-db        [animated]
Business        BLOCKS Payroll API → prod-db  tcp/5432 as svc.payroll  (P1)
Confidence      Medium — svc.backup admin on prod-db is inferred
Verdict         BLOCK

Safer option    Scoped segmentation + MFA (human accounts)
                +14% effort · no P1 flows affected · cost 9 · DEPLOY
```

---

## 3. Prior art — NON-NEGOTIABLE, do not overclaim

| Prior art | Does | Does not |
|---|---|---|
| BloodHound Enterprise, XM Cyber, MS Security Exposure Management, Wiz, Picus | Path discovery, choke points, prioritisation | No business-breakage model. Needs live estate telemetry. |
| MAL / securiCAD, MAL Simulator (open source, KTH) | Probabilistic simulation, time-to-compromise, **intelligent attacker AND defender agents**, RL | No business-flow model. Research tooling, not procurement decision support. |
| CAGE Challenges, CybORG, CyberBattleSim | Multi-agent RL gyms, adaptive red and blue | Training environments, not decision aids. |
| Azure VNM rule impact analyzer | Simulates a rule's traffic impact pre-deployment; reports "cannot be determined" when data is missing | Its own docs: **no security benefit analysis, no attack path assessment, no risk scoring.** One cloud, one control type. |
| MS Conditional Access report-only, AWS IAM Policy Simulator | Per-policy impact preview | Impact only, no security quantification. |
| IriusRisk, MS TMT, Threat Dragon | Design-time threat modelling | Qualitative checklists. No simulation. |

**BANNED CLAIMS** — each is falsifiable by one informed judge:
- "Nobody models attacker adaptation" — MAL Simulator and the CAGE gyms do.
- "First to simulate control impact before deployment" — Azure does.
- "We invented attack paths / choke points / blast radius" — all commodity.
- "Our attacker adapts emergently" — it selects among routes of the twin it faces. Say that.

**APPROVED CLAIM**, use this wording:
> "Adaptive attacker modelling exists in research — MAL Simulator, the CAGE challenges.
> Control impact simulation exists in cloud platforms — Azure's rule impact analyzer.
> To our knowledge no product joins security benefit and business breakage on one model
> for a single proposed change, which is the decision a change board actually makes."

Attacker route selection is a **mechanism we use**, not the novelty we claim.

---

## 4. Metrics — ship BOTH, labelled

1. `naive_path_reduction_pct` — path-count reduction, computed with every control treated as
   perfect and the attacker as passive. **Required by the brief.** Display it, label it the
   industry-standard metric.
2. `effort_increase_pct` — increase in the **modelled attacker-effort score** (Σ cost / p over
   the route the agent actually selects, realised over 1000 trials). Our argued improvement,
   because path count assumes a perfect control and a passive attacker; ours assumes neither.
   Call it "modelled attacker-effort score". Never "expected cost", never "honest cost".
   It is `None` when the control leaves no viable route — that is a *strong* gain, shown as
   "no viable route in N trials", never a weak one.

Pitch: *"The brief asks us to rank by paths eliminated. We do — and here's why that number
is misleading, and what we propose instead."* Shipping only the second fails a requirement.

---

## 5. Frozen contract — `engine/models.py`

**All collection fields are `tuple[...]` or `frozenset[...]`. Never `list` or `set`.**
Pydantic's `frozen=True` blocks attribute reassignment only; a `list` inside a frozen
model is still mutable and will silently corrupt snapshots and break content-addressed
caching. Everything in the twin must be hashable.

**Twin hash** = sha256 of `model_dump()` canonicalised (`sort_keys=True`, every frozenset
sorted). `model_dump_json()` alone is not stable across processes. Cache key is
`(twin_hash, agent_id, seed, n)`.

**Capability tokens** — closed grammar, nothing else exists:
`session:<asset>` · `admin:<asset>` · `creds:<identity>` · `data:<asset>`

```python
Evidence = Literal["observed", "inventory", "inferred", "assumed"]
# confidence weight: observed 1.0 · inventory 0.9 · inferred 0.5 · assumed 0.0 (= cannot be determined)

class Asset(BaseModel, frozen=True):
    id: str; name: str
    kind: Literal["server","workstation","database","cloud_role","share","internet"]
    zone: str                       # external | dmz | corp | prod | mgmt
    criticality: int                # 1-5
    crown_jewel: bool = False

class Identity(BaseModel, frozen=True):
    id: str; name: str
    kind: Literal["user","admin","service_account","cloud_role"]
    tier: int                       # 0 = most privileged

class PrivilegeGrant(BaseModel, frozen=True):
    """Identity <-> asset. This is what makes identities part of the twin (BloodHound's
    HasSession / CanLogin / AdminTo)."""
    identity_id: str; asset_id: str
    capability: Literal["session","login","admin"]
    evidence: Evidence = "inventory"

class Edge(BaseModel, frozen=True):
    """Reachability: technique T is attemptable src->dst. ONE technique per edge, explicit.
    Host-local techniques (cred_dump, priv_esc_local) are self-edges the twin lists."""
    src: str; dst: str
    technique: str
    evidence: Evidence = "inventory"

class ServiceFlow(BaseModel, frozen=True):
    """A LEGITIMATE dependency that must keep working. A real channel, not a technique name.
    This type is the differentiator."""
    id: str; name: str
    src: str; dst: str              # asset ids
    protocol: str; port: int        # tcp/5432, rdp/3389, ssh/22, smb/445, https/443
    identity_id: str                # what the flow authenticates as
    criticality: int                # 1-5; >=4 must never be broken
    evidence: Evidence = "inventory"

class FlowSelector(BaseModel, frozen=True):
    """One matcher for attack edges AND legitimate flows. Empty field = any."""
    techniques: frozenset[str] = frozenset()
    src_zones: frozenset[str] = frozenset()
    dst_zones: frozenset[str] = frozenset()
    src_assets: frozenset[str] = frozenset()
    dst_assets: frozenset[str] = frozenset()
    protocols: frozenset[str] = frozenset()
    ports: frozenset[int] = frozenset()
    identity_ids: frozenset[str] = frozenset()
    identity_kinds: frozenset[str] = frozenset()

class ControlImpact(BaseModel, frozen=True):
    deny: FlowSelector
    exceptions: tuple[FlowSelector, ...] = ()   # affected iff deny matches AND no exception matches
    efficacy: float                             # matched attack edges: p_success *= (1 - efficacy)
    breaks_flows: bool                          # matched legitimate flows are broken

class Control(BaseModel, frozen=True):
    id: str; name: str
    cost: int
    impacts: tuple[ControlImpact, ...]

class Agent(BaseModel, frozen=True):
    id: str; name: str
    start_zones: tuple[str, ...]
    capabilities: frozenset[str]    # e.g. insider: {"creds:u.hr"}
    objective: Literal["specific_target","exfil"]
    target: str                     # asset id
    noise_budget: float
    skill: float                    # 0-1, sharpens route choice

class Twin(BaseModel, frozen=True):
    id: str
    assets: tuple[Asset, ...]
    identities: tuple[Identity, ...]
    grants: tuple[PrivilegeGrant, ...]
    edges: tuple[Edge, ...]
    flows: tuple[ServiceFlow, ...]
    controls: tuple[Control, ...]
    parent_id: str | None = None    # lineage

class CompiledEdge(BaseModel, frozen=True):
    """The ONLY thing search.py and walk.py read. Produced by rules/compile.py."""
    src: str; dst: str; technique: str
    identity_id: str | None         # which credential this expansion uses
    requires: frozenset[str]; grants: frozenset[str]
    p_success: float; cost: float; noise: float
    evidence: Evidence
```

A **channel** is `(technique|None, src, src_zone, dst, dst_zone, protocol, port, identity_id,
identity_kind)`. Attack edges and service flows both project to a channel; one
`matches(selector, channel)` serves both. A control acts on channels — attackers and payroll
use the same channels. That is why the breakage model is real, not a string comparison.

Why `exceptions` are selectors and not flow ids — scoped segmentation of `prod-db`:

```
deny:       FlowSelector(dst_assets={prod-db})
exceptions: FlowSelector(src_assets={payroll-api}, dst_assets={prod-db}, protocols={tcp}, ports={5432}, identity_ids={svc.payroll})
            FlowSelector(src_assets={backup-01},   dst_assets={prod-db}, protocols={tcp}, ports={5432}, identity_ids={svc.backup})
```
`ws-hr → prod-db` holding stolen `creds:svc.payroll` fails `src_assets` → **denied**.
`backup-01 → prod-db` as `svc.backup` → **allowed** (flow F2 keeps working; so does attack
route B/D through backup-01 — the model shows the hole, which is the point). An allowed
payroll workload is not an attacker on an HR workstation holding payroll credentials.

Techniques live in **YAML, not code** — this is what lets a rule be edited live on stage
and what grounds the model in MITRE ATT&CK. **Ten techniques, each with a real ATT&CK ID.**
More entries do not improve the demo. No `blocked_by` — controls match channels.

```yaml
- id: rdp_lateral
  attck: T1021.001
  channel: {protocol: rdp, port: 3389}   # omitted for host-local techniques
  requires: [session:src, creds:who]     # who = each identity with login|admin grant on dst
  grants:   [session:dst]                # + admin:dst automatically when who's grant is admin
  base_success: 0.9
  cost: 2
  noise: 0.3
- id: cred_dump
  attck: T1003
  requires: [admin:src]
  grants:   [creds:sessions@src]         # every identity with a session grant on src
  base_success: 0.8
  cost: 1
  noise: 0.4
```
Placeholders allowed: `session:src|dst`, `admin:src|dst`, `creds:who`, `creds:sessions@src`,
`data:dst`. The ten: phish T1566 · exploit_public_app T1190 · cred_dump T1003 ·
priv_esc_local T1068 · creds_in_files T1552.001 · rdp_lateral T1021.001 · ssh_lateral
T1021.004 · smb_lateral T1021.002 · db_login T1078 · exfil_c2 T1041.

---

## 6. Compiler and two algorithms — NON-NEGOTIABLE

**`rules/compile.py` never invents a transition.** For each `Edge`, look up its one declared
technique, then expand only over candidate identities from `grants` on `dst`
(`creds:who` → one `CompiledEdge` per grant; `creds:sessions@src` → grants for every session
on `src`). Then apply controls: a channel matched by an impact's `deny` and by none of its
`exceptions` is dropped (`naive=True`) or has `p_success *= (1 - efficacy)` (`naive=False`).
`tests/test_rules.py` asserts `{(src, dst, technique)} of compiled ⊆ twin.edges` always, and
`==` with no controls.

**(a) Complete path search** — `engine/search.py`. Runs ONCE per compiled twin, cached.
State is `(node, frozenset(capabilities_held))`; dedupe on the full state, not the node.
Capabilities only accumulate. **An edge is admissible from any state whose caps ⊇
`edge.requires`** — `session:src` in `requires` is what ties it to a foothold, so an
attacker holding sessions on two hosts may act from either; `node` is the last `dst`, kept
for route rendering and the target check. DFS simple paths to `agent.target`. Hard caps
`max_depth=8`, `max_paths=5000`, raise `SearchBudgetExceeded` rather than hang. Produces
the **path inventory** and, compiled with `naive=True`, the headline "N critical paths"
number.

**(b) Plan-then-execute agent** — `engine/walk.py`. Used for ALL Monte Carlo statistics.

```
route_policy(inventory, agent) -> tuple[(route, p_select, p_route)]   # DETERMINISTIC, no RNG
    per route: p_edge_eff = 1 - (1 - p)^3               (up to 3 attempts per edge)
               p_route      = Π p_edge_eff
               effort_score = Σ cost_i / p_i             ("modelled attacker-effort score")
               noise        = Σ noise_i
    drop routes with noise > agent.noise_budget
    keep top K=5 by u = p_route / effort_score
    p_select_i ∝ u_i ** (1 + 4·skill)

trial(rng):  pick a route by p_select → execute edge by edge (≤3 attempts, each attempt adds
             cost and noise; noise over budget = detected) → record success, realised effort,
             edges traversed, route id
```

`route_policy` is shared: the walk samples from it, the optimiser scores with it. **Never
run the state-space search inside the Monte Carlo loop.** The honest sentence for the pitch:
*"the agent selects among feasible routes of the twin it faces; after the control the
feasible set changes and it selects a different route — that is `substituted_paths`."*

---

## 7. Core functions

```python
def compile(twin, techniques, *, naive=False) -> tuple[CompiledEdge, ...]      # rules/compile.py  (B)
def clone(twin, *, add_controls=(), add_edges=(), remove_edges=(), add_grants=()) -> Twin   # engine/twin.py (A)
def search(edges, agent) -> Inventory                                           # engine/search.py   (A)
def route_policy(inventory, agent) -> tuple[RouteChoice, ...]                   # engine/walk.py     (A)
def simulate(twin, agent, n: int, seed: int) -> Result                          # engine/walk.py     (A)
def diff(before: Result, after: Result) -> Delta                                # engine/results.py  (A)
def evaluate_change(scenario, control_ids, agent_ids, *, twin=None, seed, n) -> ChangeVerdict   # rules/evaluate.py (B)  THE centrepiece
def optimize(scenario, budget, agent_ids, *, twin=None) -> Portfolio            # rules/optimize.py (B)
def blast_radius(twin, edges, asset_id) -> Blast                                # engine/blast.py  (A)
def load_scenario(name) -> Scenario(twin, agents, catalogue)                    # engine/scenario.py
```

`Result`: `p_success`, `p_success_ci` (Wilson 95%), `effort_distribution`, `mean_effort`
(over successful trials), `p90_effort`, `edge_frequency` (choke points, free), `routes`
(top-K with `p_select` and observed frequency), `weighted_risk = target_crit × Σ p_select × p_route`.

`Delta`: `naive_path_reduction_pct`, `effort_increase_pct: float | None`,
`route_eliminated: bool` (after has < 20 successes → pct is `None`, flag is true),
`p_success_delta`, **`substituted_paths`** — routes selected in `after` never selected in
`before`. The single most compelling output in the system. Render it animated.

`ChangeVerdict`: `delta`, `broken_flows: tuple[ServiceFlow, ...]`, `cost`,
`confidence: {level, score, unknowns, undetermined}`, `recommendation`, `reasons`,
`alternatives` (best two safe portfolios with cost ≤ 1.25× the proposal).

**Confidence is computed, not decorated.** Decisive elements = every grant, flow and edge in
`broken_flows` or on any top-K route before or after. `score = mean(weight(evidence))`.
High ≥ 0.85, Medium ≥ 0.6, else Low. Any `assumed` element → `undetermined = True` (Azure's
"cannot be determined" posture) and the verdict is at best REVIEW. `unknowns` names each
non-verified element in words: *"svc.backup admin on prod-db — inferred"*.

**Verdict rules:**
```
BLOCK  → any broken flow with criticality >= 4
REVIEW → any broken flow (criticality < 4)  OR  confidence Low  OR  undetermined
         OR (effort_increase_pct is not None AND effort_increase_pct < 5 AND p_success_delta > -0.02)
DEPLOY → otherwise            # route_eliminated is a strong gain; it never triggers REVIEW
```

**Portfolio optimiser is exhaustive and constrained.** Catalogue ≤ 10 controls → ≤ 1024
subsets. For each subset within budget: clone → compile → search → `risk = Σ_agents
target_crit × Σ p_select × p_route` via `route_policy` (deterministic, no Monte Carlo) →
broken flows. Discard any subset breaking a flow with `criticality >= 4`. Best = maximum risk
reduction. No pruning tricks — 1024 is small and the code stays obviously correct. Monte Carlo
runs only on the winner for display. The deterministic score ignores detection during
retries, so it is an **upper bound** on simulated `p_success × crit`; `test_scenario.py` pins
it within 15%. Say "upper bound" on stage, never "the same number". Also return the naive "top-N by paths eliminated"
portfolio so the demo can contrast it. Only then is "optimal portfolio" a true sentence.

**Blast radius** = `search` seeded with `{session:X, admin:X} ∪ creds of every session on X`.
`nx.descendants` is shown separately, labelled "upper bound ignoring credentials".

**MFA wording, everywhere:** *"this interactive MFA policy is incompatible with these
non-interactive service identities."* Never "service accounts cannot MFA".

---

## 8. Stack

- Backend: Python 3.11+, FastAPI, Pydantic v2, NetworkX, pytest.
  NetworkX for authoring and the blast-radius upper bound only — flatten to `CompiledEdge`
  tuples before any simulation loop.
- **No database.** JSON files + in-memory dict keyed by twin hash.
- Frontend: React 18, TypeScript, Vite, Tailwind, React Flow (graph), Recharts (the
  overlaid attacker-effort histograms — the thesis made visible).
- **Run on localhost. Do not deploy.** Two terminals, `uvicorn` + `vite` (`scripts/demo.ps1`
  starts both). If Vite dies, `uvicorn` alone serves the built dashboard at `:8000`. Second
  laptop as hot backup.
- **Determinism is mandatory.** Seeded RNG; seed is part of the cache key. Rehearsed
  numbers must equal stage numbers.
- **Windows:** `curl` in PowerShell is `Invoke-WebRequest`. Every command in every doc says
  `curl.exe`.

## 9. API

```
GET  /twin/{id}                POST /twin/{id}/clone
POST /simulate                 POST /evaluate-change      <- centrepiece
POST /optimize                 GET  /matrix/{twin_id}     <- controls x agents
GET  /blast-radius/{asset_id}  GET  /lineage/{twin_id}
```

---

## 10. Tests — mandatory, not optional

1. `tests/test_fixture.py` (A) — hand-built 6-node graph of `CompiledEdge`s with known
   answers, including one path reachable **only** after collecting a credential two hops
   earlier. **Written BEFORE the pathfinder exists.** The pathfinder fails silently when
   wrong: it returns plausible output and every downstream number is then confidently false.
2. `tests/test_invariants.py` (A) — a control never raises any route's `p_route`, never
   raises the best route's `p_route`, never adds a naive path (checked for every catalogue
   control on golden); `clone` never mutates its input; same seed produces identical output.
   **The selected-route mix `p_success` CAN rise** when a control degrades a decoy route and
   the agent picks the easy one more often — modelled behaviour, surfaced as weak gain →
   REVIEW, never hidden.
3. `tests/test_rules.py` (B) — compile never invents a transition; the scoped-segmentation
   case (ws-hr denied, backup-01 allowed); every technique has an ATT&CK ID.
4. `tests/test_evaluate.py` (B) — verdict rules, confidence levels, `undetermined`,
   `route_eliminated` handling.
5. `tests/test_scenario.py` (D) — asserts the golden demo produces the exact numbers in the
   run sheet, and that optimiser risk and simulated `p_success × crit` agree within 0.05.
   Pinned at hour 20. Turns the demo into a regression test.

CI runs all five on every PR. A red test blocks merge.

---

## 11. Do NOT build

Real scanning, real exploits, enterprise auto-discovery. CRUD forms for building
environments by hand (ship a pre-built JSON + "load scenario" dropdown + ONE mutation
action for the sync demo). Auth, user accounts, login pages. An LLM-driven adversary —
rule-driven Monte Carlo is faster AND more defensible because it is reproducible. Live
LLM calls during the demo — pre-generate narration and cache it. A 200-node synthetic
environment — the demo runs on the ~10-asset FinBank twin; a generator is a Phase 4 stretch
only if everything else is merged, and never more than 60–80 nodes with sparse grants.

If behind, cut in this order: continuous sync (fake via JSON re-import) → extra adversary
profiles (ship one) → matrix view → lineage view.
**Never cut:** the fixture tests, `compile.py`'s no-invented-transition test,
`evaluate_change`, the decision card, the graph visualisation.

---

## 12. Rehearsed answers

1. *"How is this different from BloodHound / XM Cyber?"* → the approved claim, verbatim.
2. *"How does your pathfinder handle cycles / state explosion?"* → A answers from memory:
   state dedupe on `(node, caps)`, simple paths, `max_depth`/`max_paths`, raise not hang.
3. *"Your model could be wrong — so what?"* → **"This is decision support, not a guarantee.
   Every grant, flow and edge carries evidence; we compute confidence from the elements that
   decided the verdict and lower it — or say 'cannot be determined' — when crucial data is
   missing."** Never "accuracy is an ingestion problem".
4. *"Why does effort go down for some controls?"* → "Degrade the hard route and the agent stops
   wasting attempts on it, so the surviving successes are cheaper. That is why *harden the jump
   host alone* is REVIEW, not DEPLOY — path count would have called it a 62% win."
5. *"Isn't a random walk just noise, not adaptation?"* → "It is not a random walk. The agent
   scores the feasible routes of the twin it faces and selects among the best five. After a
   control, the feasible set changes and it selects a different route. We show you which."

---

## 13. Open question

Confirm whether the event is 24 or 36 hours. The PDF cover says 36. If 36, the extra time
goes into (a) replaying a publicly documented breach as a twin to show the engine
rediscovers the real attacker's path — validation, which nobody does at hackathons — and
(b) deeper rehearsal. Not more features.
