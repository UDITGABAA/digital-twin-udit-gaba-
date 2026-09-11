"""Exhaustive, constrained portfolio selection (CLAUDE.md §7).

Scores every subset of the catalogue within budget with the SAME deterministic policy the
agent uses (route_policy), never Monte Carlo, and discards any subset that breaks a flow
with criticality >= 4. No pruning tricks: <= 1024 subsets on a ~10-asset twin is seconds.
"""

from itertools import combinations

from pydantic import BaseModel

from engine.models import Agent, Control, Twin
from engine.scenario import Scenario
from engine.search import search
from engine.twin import clone
from engine.walk import route_policy
from rules.compile import broken_flows, compile
from rules.loader import TechniqueTable, load_techniques


class Portfolio(BaseModel, frozen=True):
    budget: int
    baseline_risk: float
    constrained: tuple[str, ...]
    constrained_risk_reduction: float
    constrained_cost: int
    constrained_broken_flows: tuple[str, ...]
    naive: tuple[str, ...]                      # top-N by paths eliminated, within budget
    naive_risk_reduction: float
    naive_cost: int
    naive_broken_flows: tuple[str, ...]
    evaluated: int


def risk(twin: Twin, agents: tuple[Agent, ...], techniques: TechniqueTable) -> float:
    """Sum over agents of target_crit x sum(p_select x p_route) -- what simulate() converges to."""
    edges = compile(twin, techniques)
    crit = {a.id: a.criticality for a in twin.assets}
    total = 0.0
    for agent in agents:
        choices = route_policy(search(edges, agent, twin), agent)
        total += crit.get(agent.target, 1) * sum(c.p_select * c.p_route for c in choices)
    return total


def naive_paths(twin: Twin, agents: tuple[Agent, ...], techniques: TechniqueTable) -> int:
    edges = compile(twin, techniques, naive=True)
    return sum(len(search(edges, a, twin).routes) for a in agents)


def optimize(scenario: Scenario, budget: int, agent_ids: tuple[str, ...] | None = None,
             *, twin: Twin | None = None, techniques: TechniqueTable | None = None) -> Portfolio:
    techniques = techniques or load_techniques()
    twin = twin or scenario.twin
    agents = tuple(a for a in scenario.agents if agent_ids is None or a.id in agent_ids)
    catalogue = tuple(c for c in scenario.catalogue if c.id not in {x.id for x in twin.controls})
    base_risk = risk(twin, agents, techniques)

    best: tuple[float, int, tuple[str, ...], tuple[str, ...]] | None = None   # (reduction, cost, ids, broken)
    evaluated = 0
    for k in range(0, len(catalogue) + 1):
        for subset in combinations(catalogue, k):
            cost = sum(c.cost for c in subset)
            if cost > budget:
                continue
            evaluated += 1
            candidate = clone(twin, add_controls=subset)
            broken = broken_flows(candidate)
            if any(f.criticality >= 4 for f in broken):
                continue
            reduction = base_risk - risk(candidate, agents, techniques)
            key = (round(reduction, 6), -cost)
            if best is None or key > (round(best[0], 6), -best[1]):
                best = (reduction, cost, tuple(c.id for c in subset), tuple(f.id for f in broken))

    # the brief's ranking: paths eliminated per control, greedy within budget, breakage ignored
    base_paths = naive_paths(twin, agents, techniques)
    ranked = sorted(catalogue, key=lambda c: (-(base_paths - naive_paths(clone(twin, add_controls=(c,)), agents, techniques)), c.cost))
    naive_pick: list[Control] = []
    spent = 0
    for c in ranked:
        if spent + c.cost <= budget:
            naive_pick.append(c)
            spent += c.cost
    naive_twin = clone(twin, add_controls=tuple(naive_pick))

    assert best is not None
    return Portfolio(
        budget=budget, baseline_risk=round(base_risk, 4),
        constrained=best[2], constrained_risk_reduction=round(best[0], 4), constrained_cost=best[1],
        constrained_broken_flows=best[3],
        naive=tuple(c.id for c in naive_pick), naive_risk_reduction=round(base_risk - risk(naive_twin, agents, techniques), 4),
        naive_cost=spent, naive_broken_flows=tuple(f.id for f in broken_flows(naive_twin)),
        evaluated=evaluated,
    )


__all__ = ["Portfolio", "risk", "naive_paths", "optimize"]
