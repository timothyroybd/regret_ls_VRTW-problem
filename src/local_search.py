# src/local_search.py
"""
Local search improvement for VRPTW solutions.
"""
from typing import Tuple
import time

from instance import VRPTWInstance
from solution import Solution, Route
from regret_constructor import is_time_feasible_route, route_load


def route_cost(inst: VRPTWInstance, route: Route) -> int:
    """Calculate travel cost for a route."""
    d = inst.depot
    c = inst.travel_time
    if not route:
        return 0
    cost = c[d][route[0]]
    for i in range(len(route) - 1):
        cost += c[route[i]][route[i + 1]]
    cost += c[route[-1]][d]
    return cost


def solution_cost(inst: VRPTWInstance, sol: Solution) -> int:
    """Calculate total solution cost."""
    return sum(route_cost(inst, r) for r in sol.routes)


def _feasible_route(inst: VRPTWInstance, route: Route) -> bool:
    """Check if route is feasible (capacity + time windows)."""
    if route_load(inst, route) > inst.capacity:
        return False
    return is_time_feasible_route(inst, route)


def _try_relocate(inst: VRPTWInstance, sol: Solution) -> Tuple[bool, int]:
    """Try relocating customers between routes (best-improving)."""
    base = solution_cost(inst, sol)
    best_sol = None
    best = base

    for ra_idx, ra in enumerate(sol.routes):
        for i, cust in enumerate(ra):
            ra2 = ra[:i] + ra[i+1:]
            if ra2 and not _feasible_route(inst, ra2):
                continue

            for rb_idx, rb in enumerate(sol.routes):
                if rb_idx == ra_idx:
                    continue
                for pos in range(len(rb) + 1):
                    rb2 = rb[:pos] + [cust] + rb[pos:]
                    if not _feasible_route(inst, rb2):
                        continue

                    cand = sol.copy()
                    cand.routes[ra_idx] = ra2
                    cand.routes[rb_idx] = rb2
                    cand.routes = [r for r in cand.routes if len(r) > 0]

                    val = solution_cost(inst, cand)
                    if val < best:
                        best = val
                        best_sol = cand

    if best_sol is None:
        return False, 0

    sol.routes = best_sol.routes
    return True, best - base


def _try_swap(inst: VRPTWInstance, sol: Solution) -> Tuple[bool, int]:
    """Try swapping customers between routes."""
    base = solution_cost(inst, sol)
    best_sol = None
    best = base

    for ra_idx in range(len(sol.routes)):
        ra = sol.routes[ra_idx]
        for rb_idx in range(ra_idx + 1, len(sol.routes)):
            rb = sol.routes[rb_idx]

            for i, a in enumerate(ra):
                for j, b in enumerate(rb):
                    ra2 = ra[:]
                    rb2 = rb[:]
                    ra2[i] = b
                    rb2[j] = a

                    if not _feasible_route(inst, ra2):
                        continue
                    if not _feasible_route(inst, rb2):
                        continue

                    cand = sol.copy()
                    cand.routes[ra_idx] = ra2
                    cand.routes[rb_idx] = rb2
                    val = solution_cost(inst, cand)
                    if val < best:
                        best = val
                        best_sol = cand

    if best_sol is None:
        return False, 0

    sol.routes = best_sol.routes
    return True, best - base


def local_search(
    inst: VRPTWInstance,
    sol: Solution,
    deadline: float = None,
    verbose: bool = False,
) -> Solution:
    """
    Local search using relocate and swap operators.
    
    Args:
        inst: VRPTW instance
        sol: Initial solution (modified in-place)
        deadline: Optional time deadline (perf_counter)
        verbose: Print progress
        
    Returns:
        Improved solution
    """
    while True:
        if deadline is not None and time.perf_counter() >= deadline:
            if verbose:
                print("[INFO] Deadline reached during local search")
            break

        improved, _ = _try_relocate(inst, sol)
        if improved:
            continue

        improved, _ = _try_swap(inst, sol)
        if improved:
            continue

        break

    return sol
