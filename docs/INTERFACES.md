# Interfaces — the contract between AI sessions

Four Claude Code sessions run in parallel and cannot see each other. This file is the only
thing they share about each other's code. **A session that changes a signature edits its
own section here in the same PR.** A session that needs a signature not in this file stops
and says so (CLAUDE.md §0.7).

Types are from `engine/models.py` (frozen) and `engine/results.py` (A).

---

## B → A · `rules/compile.py` (owner: B)

```python
def compile(twin: Twin, techniques: TechniqueTable, *, naive: bool = False) -> tuple[CompiledEdge, ...]
    # Each Edge -> its ONE declared technique -> one CompiledEdge per candidate grant on dst.
    # naive=True: channels matched by a control impact (deny and no exception) are DROPPED.
    # naive=False: their p_success *= (1 - efficacy).
    # Guarantee: {(e.src, e.dst, e.technique) for e in result} ⊆ {(e.src, e.dst, e.technique) for e in twin.edges}

def matches(selector: FlowSelector, channel: Channel) -> bool
    # Channel = (technique|None, src, src_zone, dst, dst_zone, protocol|None, port|None, identity_id|None, identity_kind|None)
    # every non-empty selector field must contain the channel's value.

def flow_channel(flow: ServiceFlow, twin: Twin) -> Channel
def edge_channel(edge: CompiledEdge, twin: Twin, techniques: TechniqueTable) -> Channel
```

`TechniqueTable = dict[str, Technique]` from `rules/loader.py`:
`load_techniques(path) -> TechniqueTable`; `Technique(id, attck, channel | None, requires, grants, base_success, cost, noise)`.

---

## A → B · `engine/search.py`, `walk.py`, `results.py`, `twin.py` (owner: A)

```python
# twin.py
def clone(twin: Twin, *, add_controls: tuple[Control, ...] = (), add_edges: tuple[Edge, ...] = (),
          remove_edges: tuple[Edge, ...] = (), add_grants: tuple[PrivilegeGrant, ...] = ()) -> Twin
    # never mutates input; new id = twin_hash(new twin); parent_id = twin.id
def twin_hash(twin: Twin) -> str          # sha256 of canonical model_dump (sort_keys, sorted frozensets)

# search.py
class SearchBudgetExceeded(Exception): ...
class Inventory(BaseModel, frozen=True):
    routes: tuple[Route, ...]            # Route = tuple[CompiledEdge, ...], start -> target
    naive_count: int                     # len(routes) when compiled with naive=True
def search(edges: tuple[CompiledEdge, ...], agent: Agent, twin: Twin,
           *, max_depth: int = 8, max_paths: int = 5000, max_states: int = 20000) -> Inventory
    # raises SearchBudgetExceeded on any cap; max_states bounds wall time on dense twins
    # starts: every asset in agent.start_zones with caps = agent.capabilities | {session:<start>}
    # success: reaching agent.target with session: or admin: on it (objective specific_target)
    #          or holding data:<target> after an exfil edge (objective exfil)

# walk.py
class RouteChoice(BaseModel, frozen=True):
    route: Route; p_select: float; p_route: float; effort_score: float; noise: float
def route_policy(inventory: Inventory, agent: Agent, *, k: int = 5) -> tuple[RouteChoice, ...]
    # DETERMINISTIC. p_edge_eff = 1-(1-p)^3; p_route = Π p_edge_eff; effort_score = Σ cost/p;
    # drop noise > agent.noise_budget; top-k by p_route/effort_score; p_select ∝ u**(1+4*skill); Σ p_select = 1
def simulate(edges: tuple[CompiledEdge, ...], agent: Agent, twin: Twin, n: int, seed: int) -> Result
    # calls search (cached by (twin_hash, edge signature, agent.id)) once, route_policy once, then n trials.
class Step(BaseModel, frozen=True):   # one attempt on one edge: attempt, roll, p_success, succeeded, detected, effort_so_far, noise_so_far
class Trial(BaseModel, frozen=True):  # index, route_index, success, detected, effort, noise, steps
def trace(edges, agent, twin, seed, k=12) -> tuple[Trial, ...]
    # the first k trials of simulate(..., seed) step by step - SAME RNG stream, so trial i is trial i of the statistics

# results.py
class Result(BaseModel, frozen=True):
    p_success: float; p_success_ci: tuple[float, float]
    effort_distribution: tuple[float, ...]; mean_effort: float | None; p90_effort: float | None
    edge_frequency: tuple[tuple[str, str, str, float], ...]     # (src, dst, technique, freq)
    routes: tuple[RouteStat, ...]                               # RouteChoice + observed_freq + observed_success
    weighted_risk: float                                        # target_crit × Σ p_select × p_route
    n: int; seed: int
class Delta(BaseModel, frozen=True):
    naive_path_reduction_pct: float
    effort_increase_pct: float | None; route_eliminated: bool   # None/True when after has < 20 successes
    p_success_delta: float
    substituted_paths: tuple[Route, ...]                        # in after.routes, not in before.routes
def diff(before: Result, after: Result, *, naive_before: int, naive_after: int) -> Delta

# blast.py
class Blast(BaseModel, frozen=True):
    asset_id: str; reachable: tuple[str, ...]; crown_jewels_hit: tuple[str, ...]
    upper_bound: tuple[str, ...]                                # nx.descendants, ignores credentials
def blast_radius(twin: Twin, edges: tuple[CompiledEdge, ...], asset_id: str) -> Blast
    # reachable: credential-expanding closure from asset_id (internet is a sink, never a launchpad)

# scenario.py
class Scenario(BaseModel, frozen=True):
    twin: Twin; agents: tuple[Agent, ...]; catalogue: tuple[Control, ...]   # catalogue = proposable controls
def load_scenario(name_or_path) -> Scenario      # "golden" -> scenarios/golden.json
```

---

## B → D · `rules/evaluate.py`, `optimize.py` (owner: B)

```python
class Confidence(BaseModel, frozen=True):
    level: Literal["High", "Medium", "Low"]; score: float
    unknowns: tuple[str, ...]            # "svc.backup admin on prod-db — inferred"
    undetermined: bool                   # any decisive element is 'assumed'
class Alternative(BaseModel, frozen=True):
    control_ids: tuple[str, ...]; cost: int; effort_increase_pct: float | None
    route_eliminated: bool; p_success_delta: float; broken_flows: tuple[str, ...]; recommendation: str
class ChangeVerdict(BaseModel, frozen=True):
    twin_id: str; after_twin_id: str; control_ids: tuple[str, ...]
    delta: Delta; before: Result; after: Result; outcomes: tuple[AgentOutcome, ...]
    broken_flows: tuple[ServiceFlow, ...]; cost: int
    confidence: Confidence
    recommendation: Literal["deploy", "blocked", "review"]; reasons: tuple[str, ...]
    alternatives: tuple[Alternative, ...]
class AgentOutcome(BaseModel, frozen=True):
    agent_id: str; before: Result; after: Result; naive_before: int; naive_after: int; delta: Delta
def evaluate_change(scenario: Scenario, control_ids: tuple[str, ...], agent_ids: tuple[str, ...] = (),
                    *, twin: Twin | None = None, seed: int = 1, n: int = 1000,
                    techniques: TechniqueTable | None = None, with_alternatives: bool = True) -> ChangeVerdict
    # controls come from scenario.catalogue, agents from scenario.agents; twin defaults to scenario.twin
    # ChangeVerdict.delta/before/after are the first agent's; outcomes has every agent
def confidence_of(outcomes, broken_flows) -> Confidence
def verdict_of(broken_flows, confidence, deltas) -> (recommendation, reasons)

class Portfolio(BaseModel, frozen=True):
    budget: int
    constrained: tuple[str, ...]; constrained_risk_reduction: float; constrained_cost: int
    naive: tuple[str, ...]; naive_risk_reduction: float; naive_broken_flows: tuple[str, ...]
    evaluated: int                                              # subsets scored
    baseline_risk: float; constrained_broken_flows: tuple[str, ...]; naive_cost: int
def risk(twin, agents, techniques) -> float      # sum over agents of target_crit x sum(p_select x p_route)
                                                 # ignores detection on retries: an UPPER BOUND on simulated p_success x crit
def optimize(scenario: Scenario, budget: int, agent_ids: tuple[str, ...] | None = None,
             *, twin: Twin | None = None, techniques=None) -> Portfolio
    # exhaustive over every subset within budget; discard any breaking a flow with criticality >= 4
```

---

## D → C · HTTP (owner: D) — responses are the Pydantic models' JSON; `types.ts` is generated from them

```
GET  /twin/{id}                          -> Twin                       ("current" = the loaded scenario's twin)
POST /twin/{id}/clone                    {control_ids?, add_grants?, label?} -> Twin
GET  /graph/{id}                         -> {assets, identities, grants, attack_edges[{src,dst,technique,attck,identities,p_success,evidence}], flows, controls}
GET  /paths/{id}?agent_id=               -> {naive_count, count, routes}   (attack path discovery)
POST /simulate                           {twin_id, agent_id, n, seed} -> Result
POST /trace                              {twin_id, agent_id, control_ids?, k?, seed?} -> [Trial]   (attack replay; k <= 200)
POST /evaluate-change                    {twin_id, control_ids, agent_ids, seed?, n?} -> ChangeVerdict   (422 if control_ids empty)
POST /optimize                           {twin_id, budget, agent_ids} -> Portfolio
GET  /matrix/{id}?seed&n                 -> {agents, rows[{control_id, name, cost, broken_flows, cells[{agent_id, effort_increase_pct, route_eliminated, p_success_delta, recommendation}]}]}
GET  /blast-radius/{id}/{asset_id}       -> Blast
GET  /lineage/{id}                       -> {nodes: [{id, parent_id, label, controls}], edges: [[parent, child]]}
GET  /scenarios                          -> {scenarios: [...], current: twin_id}
POST /scenarios/{name}/load              -> Twin        (the ONE sync action)
GET  /agents                             -> [Agent]
GET  /controls/{id}                      -> {applied: [Control], catalogue: [Control]}
```

Errors: `404` unknown twin/scenario/asset, `422` unknown control/agent or empty proposal, `409` if search caps trip.
CORS: `http://localhost:5173`; the Vite dev server proxies `/api/*` to `:8000`.
