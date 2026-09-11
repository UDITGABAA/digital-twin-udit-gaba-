# Security Change Sandbox — MUJ HackX 4.0

**Every session, every teammate, reads this file first.** It is the shared brain.
Detail lives in `docs/`. This file holds only what must never drift.

- Full build plan → `docs/IMPLEMENTATION_PLAN.md`
- Branching, ownership, PR rules → `docs/GOVERNANCE.md`
- Demo run sheet → `docs/DEMO_SCRIPT.md`

---

## 0. Working agreement for AI sessions

You are one of four parallel workstreams. Others are editing this repo right now.

1. **Read `docs/GOVERNANCE.md` before writing any file.** You may only create or edit
   files inside the directory your track owns. If a task needs a file outside it, stop
   and say so — do not edit it.
2. **`backend/core/models.py` and `backend/rules/techniques.yaml` are frozen contracts.**
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

---

## 3. Prior art — NON-NEGOTIABLE, do not overclaim

| Prior art | Does | Does not |
|---|---|---|
| BloodHound Enterprise, XM Cyber, MS Security Exposure Management, Wiz, Picus | Path discovery, choke points, prioritisation | No business-breakage model. Needs live estate telemetry. |
| MAL / securiCAD, MAL Simulator (open source, KTH) | Probabilistic simulation, time-to-compromise, **intelligent attacker AND defender agents**, RL | No business-flow model. Research tooling, not procurement decision support. |
| CAGE Challenges, CybORG, CyberBattleSim | Multi-agent RL gyms, adaptive red and blue | Training environments, not decision aids. |
| Azure VNM rule impact analyzer | Simulates a rule's traffic impact pre-deployment | Its own docs: **no security benefit analysis, no attack path assessment, no risk scoring.** One cloud, one control type. |
| MS Conditional Access report-only, AWS IAM Policy Simulator | Per-policy impact preview | Impact only, no security quantification. |
| IriusRisk, MS TMT, Threat Dragon | Design-time threat modelling | Qualitative checklists. No simulation. |

**BANNED CLAIMS** — each is falsifiable by one informed judge:
- "Nobody models attacker adaptation" — MAL Simulator and the CAGE gyms do.
- "First to simulate control impact before deployment" — Azure does.
- "We invented attack paths / choke points / blast radius" — all commodity.

**APPROVED CLAIM**, use this wording:
> "Adaptive attacker modelling exists in research — MAL Simulator, the CAGE challenges.
> Control impact simulation exists in cloud platforms — Azure's rule impact analyzer.
> To our knowledge no product joins security benefit and business breakage on one model
> for a single proposed change, which is the decision a change board actually makes."

Attacker re-planning is a **mechanism we use**, not the novelty we claim.

---

## 4. Metrics — ship BOTH, labelled

1. `naive_path_reduction_pct` — path-count reduction. **Required by the brief.** Display
   it, label it the industry-standard metric.
2. `honest_cost_increase_pct` — attacker-cost increase. Our argued improvement, because
   path count assumes a passive attacker while ours re-plans.

Pitch: *"The brief asks us to rank by paths eliminated. We do — and here's why that number
is misleading, and what we propose instead."* Shipping only the second fails a requirement.

---

## 5. Frozen contract — `backend/core/models.py`

**All collection fields are `tuple[...]` or `frozenset[...]`. Never `list` or `set`.**
Pydantic's `frozen=True` blocks attribute reassignment only; a `list` inside a frozen
model is still mutable and will silently corrupt snapshots and break content-addressed
caching. Everything in the twin must be hashable.

```python
class Asset(BaseModel, frozen=True):
    id: str; name: str
    kind: Literal["server","workstation","database","cloud_role","share"]
    zone: str                       # dmz | corp | prod | mgmt
    criticality: int                # 1-5
    crown_jewel: bool = False

class Identity(BaseModel, frozen=True):
    id: str; name: str
    kind: Literal["user","admin","service_account","cloud_role"]
    tier: int                       # 0 = most privileged

class Edge(BaseModel, frozen=True):
    src: str; dst: str
    technique: str

class ServiceFlow(BaseModel, frozen=True):
    """A LEGITIMATE dependency that must keep working. This type is the differentiator."""
    id: str; name: str
    src: str; dst: str
    technique: str
    criticality: int                # 1-5; >=4 must never be broken

class Control(BaseModel, frozen=True):
    id: str; name: str
    cost: int
    blocks: tuple[str, ...]
    scope: tuple[str, ...]
    efficacy: float                 # 0-1, controls are imperfect

class Agent(BaseModel, frozen=True):
    id: str; name: str
    start_zones: tuple[str, ...]
    capabilities: frozenset[str]
    objective: Literal["specific_target","max_breadth","exfil"]
    noise_budget: float
    skill: float

class Twin(BaseModel, frozen=True):
    id: str
    assets: tuple[Asset, ...]
    identities: tuple[Identity, ...]
    edges: tuple[Edge, ...]
    flows: tuple[ServiceFlow, ...]
    controls: tuple[Control, ...]
    parent_id: str | None = None    # lineage
```

Techniques live in **YAML, not code** — this is what lets a rule be edited live on stage
and what grounds the model in MITRE ATT&CK. Tag every technique with a real ATT&CK ID; it
is the answer to "where did your model come from."

```yaml
- id: rdp_lateral
  attck: T1021.001
  requires: [creds_for_dst]
  grants:   [session_on_dst]
  base_success: 0.9
  cost: 2
  noise: 0.3
  blocked_by: [network_segmentation, mfa]
```

---

## 6. Two algorithms — NON-NEGOTIABLE, never merge them

Different jobs. Conflating them causes a correctness bug *and* a performance blowup.

**(a) Complete path search** — `core/search.py`. Runs ONCE per twin, cached.
State is `(node, frozenset(capabilities_held))`, because an edge may only be traversable
once credentials collected earlier are held. Capabilities only accumulate. Hard caps
`max_depth=8`, `max_states=5000`, raise loudly rather than hang. Produces the path
inventory and the headline "N critical paths" number.

**(b) Sampled agent walk** — `core/walk.py`. Used for ALL Monte Carlo statistics.
At each step the agent enumerates only edges admissible *from where it stands with what it
holds*, scores them, picks probabilistically, moves. No global search. ~depth × branching
ops per trial, so 1000 trials is milliseconds.

(b) is also the more honest attacker model — real attackers have local, not omniscient,
knowledge — and it makes adaptation emergent: block an edge and the agent never
enumerates it. **Never run the state-space search inside the Monte Carlo loop.**

---

## 7. Core functions

```python
def clone(twin, *, add_controls=(), add_edges=(), remove_edges=()) -> Twin
def simulate(twin, agent, n: int, seed: int) -> Result
def diff(before: Result, after: Result) -> Delta
def evaluate_change(twin, controls, agents) -> ChangeVerdict   # THE centrepiece
```

`Result`: `p_success`, `cost_distribution`, `mean_cost`, `p90`, `edge_frequency`
(choke points, free), `exemplar_paths`, `weighted_risk`.

`Delta`: `naive_path_reduction_pct`, `honest_cost_increase_pct`, `p_success_delta`,
**`substituted_paths`** — paths present in `after` but not `before`. The single most
compelling output in the system: the attacker's specific new route. Render it animated.

`ChangeVerdict`: `security_delta`, `broken_flows: tuple[ServiceFlow, ...]`, `cost`,
`confidence`, `recommendation: Literal["deploy","blocked","review"]`.

**Portfolio optimiser is constrained**: maximise risk reduction subject to budget AND
never breaking a ServiceFlow with `criticality >= 4`.

---

## 8. Stack

- Backend: Python 3.11, FastAPI, Pydantic v2, NetworkX, pytest.
  NetworkX for authoring and blast radius (`nx.descendants`) only — flatten to plain dicts
  before any simulation loop.
- **No database.** JSON files + in-memory dict keyed by twin hash.
- Frontend: React 18, TypeScript, Vite, Tailwind, React Flow (graph), Recharts (the
  overlaid attacker-cost histograms — the thesis made visible).
- **Run on localhost. Do not deploy.** Two terminals, `uvicorn` + `vite`. Second laptop
  as hot backup.
- **Determinism is mandatory.** Seeded RNG; seed is part of the cache key. Rehearsed
  numbers must equal stage numbers.

## 9. API

```
GET  /twin/{id}                POST /twin/{id}/clone
POST /simulate                 POST /evaluate-change      <- centrepiece
POST /optimize                 GET  /matrix/{twin_id}     <- controls x agents
GET  /blast-radius/{asset_id}  GET  /lineage/{twin_id}
```

---

## 10. Tests — mandatory, not optional

1. `tests/test_fixture.py` — hand-built 6-node graph with known answers, including one
   path reachable **only** after collecting a credential two hops earlier.
   **Written BEFORE the pathfinder exists.** The pathfinder fails silently when wrong: it
   returns plausible output and every downstream number is then confidently false.
2. `tests/test_invariants.py` — adding a control never increases attacker success;
   `clone` never mutates its input; same seed produces identical output.
3. `tests/test_scenario.py` — asserts the golden demo produces the exact numbers in the
   run sheet. Run at hour 23. Turns the demo into a regression test.

CI runs all three on every PR. A red test blocks merge.

---

## 11. Do NOT build

Real scanning, real exploits, enterprise auto-discovery. CRUD forms for building
environments by hand (ship a pre-built JSON + "load scenario" dropdown + ONE mutation
action for the sync demo). Auth, user accounts, login pages. An LLM-driven adversary —
rule-driven Monte Carlo is faster AND more defensible because it is reproducible. Live
LLM calls during the demo — pre-generate narration and cache it.

If behind, cut in this order: continuous sync (fake via JSON re-import) → extra adversary
profiles (ship one) → technique breadth (10 instead of 15).
**Never cut:** the fixture tests, `evaluate_change`, the graph visualisation.

---

## 12. Open question

Confirm whether the event is 24 or 36 hours. The PDF cover says 36. If 36, the extra time
goes into (a) replaying a publicly documented breach as a twin to show the engine
rediscovers the real attacker's path — validation, which nobody does at hackathons — and
(b) deeper rehearsal. Not more features.
