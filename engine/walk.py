"""Plan-then-execute agent route selection and Monte Carlo simulation (Algorithm B).

Implements:
- route_policy(): Deterministic ranking and probability assignment over path inventory
- simulate(): n-trial Monte Carlo simulation executing routes with retries and noise tracking
"""

import math
import random
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel

from engine.models import Agent, CompiledEdge, Twin, twin_hash
from engine.search import Inventory, Route, search
from engine.results import Result, RouteStat


class RouteChoice(BaseModel, frozen=True):
    """Deterministic route policy choice with selection probability and metrics."""
    route: Route
    p_select: float
    p_route: float
    effort_score: float
    noise: float


# Cache for path searches: (twin_hash, edges signature, agent.id) -> Inventory
_SEARCH_CACHE: Dict[Tuple[str, tuple, str], Inventory] = {}


def clear_search_cache() -> None:
    """Clear internal search cache."""
    _SEARCH_CACHE.clear()


def route_policy(
    inventory: Inventory,
    agent: Agent,
    *,
    k: int = 5
) -> tuple[RouteChoice, ...]:
    """Deterministically score, filter, and rank attack paths from the inventory.
    
    Equations (CLAUDE.md §6b):
        p_edge_eff = 1 - (1 - p)^3             (up to 3 attempts per edge)
        p_route = Prod(p_edge_eff)
        effort_score = Sum(cost_i / p_i)       (modelled attacker-effort score)
        noise = Sum(noise_i)
        Drop routes with noise > agent.noise_budget
        Keep top K=5 by u = p_route / effort_score
        p_select_i proportional to u_i ** (1 + 4 * skill)
        Sum(p_select) == 1.0
    """
    if not inventory.routes:
        return ()

    scored_routes: list[tuple[float, float, float, float, Route]] = []

    for r in inventory.routes:
        p_route = 1.0
        effort_score = 0.0
        total_noise = 0.0

        for e in r:
            p = max(0.0, min(1.0, e.p_success))
            p_edge_eff = 1.0 - (1.0 - p) ** 3
            p_route *= p_edge_eff
            # Avoid division by zero: minimum denominator 1e-6
            effort_score += e.cost / max(p, 1e-6)
            total_noise += e.noise

        # Noise budget filter
        if total_noise > agent.noise_budget:
            continue

        u = p_route / max(effort_score, 1e-6)
        scored_routes.append((u, p_route, effort_score, total_noise, r))

    if not scored_routes:
        return ()

    # Sort deterministically:
    # 1. Utility u descending
    # 2. p_route descending
    # 3. effort_score ascending
    # 4. Canonical route signature for deterministic tie-breaking
    scored_routes.sort(
        key=lambda item: (
            -item[0],
            -item[1],
            item[2],
            tuple((e.src, e.dst, e.technique) for e in item[4])
        )
    )

    # Keep top-k
    top_k = scored_routes[:k]

    # Calculate p_select proportional to u ** (1 + 4 * skill)
    exponent = 1.0 + 4.0 * agent.skill
    weights = [item[0] ** exponent for item in top_k]
    sum_w = sum(weights)

    choices: list[RouteChoice] = []
    for idx, (u, p_route, effort_score, total_noise, route) in enumerate(top_k):
        if sum_w > 0:
            p_sel = weights[idx] / sum_w
        else:
            p_sel = 1.0 / len(top_k)

        choices.append(
            RouteChoice(
                route=route,
                p_select=p_sel,
                p_route=p_route,
                effort_score=effort_score,
                noise=total_noise,
            )
        )

    return tuple(choices)


class Step(BaseModel, frozen=True):
    """One attempt on one edge, as the replay shows it."""
    src: str
    dst: str
    technique: str
    identity_id: Optional[str]
    attempt: int                 # 1..3
    roll: Optional[float]        # None when detected before rolling
    p_success: float
    succeeded: bool
    detected: bool
    effort_so_far: float
    noise_so_far: float


class Trial(BaseModel, frozen=True):
    index: int
    route_index: int
    success: bool
    detected: bool
    effort: float
    noise: float
    steps: tuple[Step, ...]


def _run_trial(rng: random.Random, choices: tuple[RouteChoice, ...], weights: list[float], agent: Agent, index: int = 0) -> Trial:
    """The ONE trial loop. simulate() aggregates it n times; trace() returns it verbatim.
    RNG call order: one rng.choices() for the route, then one rng.random() per attempt."""
    chosen_idx = rng.choices(range(len(choices)), weights=weights, k=1)[0]
    route = choices[chosen_idx].route
    effort = 0.0
    noise = 0.0
    steps: list[Step] = []
    success = True
    detected = False
    for edge in route:
        edge_ok = False
        for attempt in range(1, 4):
            effort += edge.cost
            noise += edge.noise
            if noise > agent.noise_budget:
                detected = True
                steps.append(Step(src=edge.src, dst=edge.dst, technique=edge.technique, identity_id=edge.identity_id,
                                  attempt=attempt, roll=None, p_success=edge.p_success, succeeded=False, detected=True,
                                  effort_so_far=effort, noise_so_far=noise))
                break
            roll = rng.random()
            edge_ok = roll < edge.p_success
            steps.append(Step(src=edge.src, dst=edge.dst, technique=edge.technique, identity_id=edge.identity_id,
                              attempt=attempt, roll=round(roll, 4), p_success=edge.p_success, succeeded=edge_ok, detected=False,
                              effort_so_far=effort, noise_so_far=noise))
            if edge_ok:
                break
        if not edge_ok:
            success = False
            break
    return Trial(index=index, route_index=chosen_idx, success=success, detected=detected,
                 effort=effort, noise=round(noise, 4), steps=tuple(steps))


def trace(edges: tuple[CompiledEdge, ...], agent: Agent, twin: Twin, seed: int, k: int = 12) -> tuple[Trial, ...]:
    """The first k trials of simulate(edges, agent, twin, n, seed), step by step, for the replay.
    Same seed, same RNG stream: trial i here is trial i of the simulation."""
    inventory = search(edges, agent, twin)
    choices = route_policy(inventory, agent)
    if not choices:
        return ()
    rng = random.Random(seed)
    weights = [c.p_select for c in choices]
    return tuple(_run_trial(rng, choices, weights, agent, i) for i in range(k))


def simulate(
    edges: tuple[CompiledEdge, ...],
    agent: Agent,
    twin: Twin,
    n: int,
    seed: int
) -> Result:
    """Execute n Monte Carlo trials of adversary attack simulation.
    
    Calls search (cached by (twin_hash, edge signature, agent.id)) once,
    route_policy once, then runs n trials with seeded PRNG.
    """
    edge_sig = tuple((e.src, e.dst, e.technique, e.identity_id, round(e.p_success, 6)) for e in edges)
    cache_key = (twin_hash(twin), edge_sig, agent.id)
    if cache_key in _SEARCH_CACHE:
        inventory = _SEARCH_CACHE[cache_key]
    else:
        inventory = search(edges, agent, twin)
        _SEARCH_CACHE[cache_key] = inventory

    choices = route_policy(inventory, agent)

    if not choices or n <= 0:
        return Result(
            p_success=0.0,
            p_success_ci=(0.0, 0.0),
            effort_distribution=(),
            mean_effort=None,
            p90_effort=None,
            edge_frequency=(),
            routes=(),
            weighted_risk=0.0,
            n=n,
            seed=seed,
        )

    rng = random.Random(seed)
    p_select_weights = [c.p_select for c in choices]

    route_attempts = [0] * len(choices)
    route_successes = [0] * len(choices)
    edge_traversal_counts: dict[tuple[str, str, str], int] = {}
    successful_efforts: list[float] = []

    for _ in range(n):
        t = _run_trial(rng, choices, p_select_weights, agent)
        route_attempts[t.route_index] += 1
        for ek in {(st.src, st.dst, st.technique) for st in t.steps}:
            edge_traversal_counts[ek] = edge_traversal_counts.get(ek, 0) + 1
        if t.success:
            route_successes[t.route_index] += 1
            successful_efforts.append(t.effort)

    # Statistics
    succ_count = len(successful_efforts)
    p_succ = succ_count / n

    # Wilson score 95% confidence interval
    z = 1.95996
    denom = 1.0 + (z * z) / n
    center = (p_succ + (z * z) / (2.0 * n)) / denom
    spread = (z / denom) * math.sqrt(
        (p_succ * (1.0 - p_succ) / n) + (z * z) / (4.0 * n * n)
    )
    p_success_ci = (
        round(max(0.0, center - spread), 4),
        round(min(1.0, center + spread), 4),
    )

    # Effort distribution
    sorted_efforts = tuple(sorted(successful_efforts))
    if succ_count > 0:
        mean_eff = sum(sorted_efforts) / succ_count
        p90_idx = int(0.9 * (succ_count - 1))
        p90_eff = sorted_efforts[p90_idx]
    else:
        mean_eff = None
        p90_eff = None

    # Edge frequency (choke points)
    edge_freq_list = [
        (src, dst, tech, round(count / n, 4))
        for (src, dst, tech), count in edge_traversal_counts.items()
    ]
    edge_freq_list.sort(key=lambda item: (-item[3], item[0], item[1], item[2]))

    # Route stats
    route_stats = []
    for idx, c in enumerate(choices):
        attempts = route_attempts[idx]
        succ = route_successes[idx]
        obs_freq = round(attempts / n, 4)
        obs_succ = round(succ / attempts, 4) if attempts > 0 else 0.0
        route_stats.append(
            RouteStat(
                route=c.route,
                p_select=round(c.p_select, 6),
                p_route=round(c.p_route, 6),
                effort_score=round(c.effort_score, 4),
                noise=round(c.noise, 4),
                observed_freq=obs_freq,
                observed_success=obs_succ,
            )
        )

    # Weighted risk = target_crit * sum(p_select * p_route)
    target_asset = next((a for a in twin.assets if a.id == agent.target), None)
    target_crit = target_asset.criticality if target_asset else 1
    weighted_risk = float(target_crit) * sum(c.p_select * c.p_route for c in choices)

    return Result(
        p_success=round(p_succ, 4),
        p_success_ci=p_success_ci,
        effort_distribution=sorted_efforts,
        mean_effort=round(mean_eff, 4) if mean_eff is not None else None,
        p90_effort=round(p90_eff, 4) if p90_eff is not None else None,
        edge_frequency=tuple(edge_freq_list),
        routes=tuple(route_stats),
        weighted_risk=round(weighted_risk, 4),
        n=n,
        seed=seed,
    )


__all__ = [
    "RouteChoice",
    "Step",
    "Trial",
    "route_policy",
    "simulate",
    "trace",
    "clear_search_cache",
]
