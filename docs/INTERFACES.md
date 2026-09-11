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
           *, max_depth: int = 8, max_paths: int = 5000) -> Inventory
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
    # calls search (cached by (hash(edges), agent.id)) once, route_policy once, then n trials.

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
    route_eliminated: bool; broken_flows: tuple[str, ...]; recommendation: str
class ChangeVerdict(BaseModel, frozen=True):
    twin_id: str; after_twin_id: str; control_ids: tuple[str, ...]
    delta: Delta; before: Result; after: Result
    broken_flows: tuple[ServiceFlow, ...]; cost: int
    confidence: Confidence
    recommendation: Literal["deploy", "blocked", "review"]; reasons: tuple[str, ...]
    alternatives: tuple[Alternative, ...]
def evaluate_change(twin: Twin, control_ids: tuple[str, ...], agent_ids: tuple[str, ...],
                    *, seed: int = 1, n: int = 1000) -> ChangeVerdict
    # controls and agents are looked up in the twin / agent catalogue by id

class Portfolio(BaseModel, frozen=True):
    budget: int
    constrained: tuple[str, ...]; constrained_risk_reduction: float; constrained_cost: int
    naive: tuple[str, ...]; naive_risk_reduction: float; naive_broken_flows: tuple[str, ...]
    evaluated: int                                              # subsets scored
def optimize(twin: Twin, budget: int, agents: tuple[Agent, ...]) -> Portfolio
    # exhaustive over every subset within budget; discard any breaking a flow with criticality >= 4;
    # risk via route_policy (deterministic), never Monte Carlo
```

---

## D → C · HTTP (owner: D) — responses are the Pydantic models' JSON; `types.ts` is generated from them

```
GET  /twin/{id}                          -> Twin
POST /twin/{id}/clone                    {add_controls?, add_edges?, remove_edges?, add_grants?} -> Twin
POST /simulate                           {twin_id, agent_id, n, seed} -> Result
POST /evaluate-change                    {twin_id, control_ids, agent_ids, seed?} -> ChangeVerdict
POST /optimize                           {twin_id, budget, agent_ids} -> Portfolio
GET  /matrix/{twin_id}?agent_ids=..      -> {controls: [...], agents: [...], cells: [[effort_increase_pct | null]], route_eliminated: [[bool]]}
GET  /blast-radius/{twin_id}/{asset_id}  -> Blast
GET  /lineage/{twin_id}                  -> {nodes: [{id, parent_id, label}], edges: [[parent, child]]}
GET  /scenarios                          -> ["golden", "golden_sync"]
POST /scenarios/{name}/load              -> Twin        (the ONE sync action)
GET  /agents                             -> [Agent]
GET  /controls/{twin_id}                 -> [Control]
```

Errors: `422` on unknown ids; `409 {"error": "SearchBudgetExceeded"}` if search caps trip.
CORS: `http://localhost:5173`.
