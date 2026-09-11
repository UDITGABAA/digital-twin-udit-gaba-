"""Result analysis and diffing models for simulation outcomes (Track A).

Frozen contract models defined in docs/INTERFACES.md:
- RouteStat: Route choice combined with observed simulation performance
- Result: Monte Carlo run aggregates (p_success, Wilson CI, effort distribution, choke points)
- Delta: Comparison between baseline and post-control simulation outcomes
- diff(): Computes naive path reduction %, effort increase %, and substituted paths
"""

from typing import Optional, Tuple
from pydantic import BaseModel
from engine.models import CompiledEdge

Route = tuple[CompiledEdge, ...]


class RouteStat(BaseModel, frozen=True):
    """Execution statistics for a route evaluated during simulation."""
    route: Route
    p_select: float
    p_route: float
    effort_score: float
    noise: float
    observed_freq: float
    observed_success: float


class Result(BaseModel, frozen=True):
    """Aggregate outcomes of an n-trial Monte Carlo simulation."""
    p_success: float
    p_success_ci: tuple[float, float]
    effort_distribution: tuple[float, ...]
    mean_effort: Optional[float]
    p90_effort: Optional[float]
    edge_frequency: tuple[tuple[str, str, str, float], ...]     # (src, dst, technique, freq)
    routes: tuple[RouteStat, ...]                               # RouteChoice + observed_freq + observed_success
    weighted_risk: float                                        # target_crit x Sigma p_select x p_route
    n: int
    seed: int


class Delta(BaseModel, frozen=True):
    """Delta comparison between two simulation states (before vs. after a security change)."""
    naive_path_reduction_pct: float
    effort_increase_pct: Optional[float]
    route_eliminated: bool                                      # None/True when after has < 20 successes
    p_success_delta: float
    substituted_paths: tuple[Route, ...]                        # in after.routes, not in before.routes


def diff(
    before: Result,
    after: Result,
    *,
    naive_before: int,
    naive_after: int
) -> Delta:
    """Compare baseline (before) and post-control (after) simulation results.
    
    Parameters
    ----------
    before : Result
        Baseline simulation result.
    after : Result
        Post-control simulation result.
    naive_before : int
        Number of attack paths before control under naive compile.
    naive_after : int
        Number of attack paths after control under naive compile.
    """
    # 1. Naive path reduction percentage
    if naive_before > 0:
        naive_reduction = ((naive_before - naive_after) / naive_before) * 100.0
    else:
        naive_reduction = 0.0

    # 2. Success delta
    p_delta = after.p_success - before.p_success

    # 3. Effort increase % & Route elimination:
    # If after has < 20 successful trials, pct is None and route_eliminated is True
    success_count_after = len(after.effort_distribution)
    if success_count_after < 20:
        effort_increase_pct = None
        route_eliminated = True
    else:
        route_eliminated = False
        if before.mean_effort is not None and before.mean_effort > 0 and after.mean_effort is not None:
            effort_increase_pct = ((after.mean_effort - before.mean_effort) / before.mean_effort) * 100.0
        else:
            effort_increase_pct = 0.0

    # 4. Substituted paths: routes selected in after that were not in before
    before_route_signatures = {
        tuple((e.src, e.dst, e.technique) for e in r.route)
        for r in before.routes
        if r.observed_freq > 0 or r.p_select > 0
    }
    
    substituted: list[Route] = []
    seen_sub_signatures = set()
    for r in after.routes:
        if r.observed_freq > 0 or r.p_select > 0:
            sig = tuple((e.src, e.dst, e.technique) for e in r.route)
            if sig not in before_route_signatures and sig not in seen_sub_signatures:
                seen_sub_signatures.add(sig)
                substituted.append(r.route)

    return Delta(
        naive_path_reduction_pct=round(naive_reduction, 2),
        effort_increase_pct=round(effort_increase_pct, 2) if effort_increase_pct is not None else None,
        route_eliminated=route_eliminated,
        p_success_delta=round(p_delta, 4),
        substituted_paths=tuple(substituted),
    )


__all__ = [
    "Route",
    "RouteStat",
    "Result",
    "Delta",
    "diff",
]
