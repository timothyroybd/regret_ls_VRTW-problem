# src/regret_constructor.py
"""
Regret-based construction heuristic for VRPTW.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple
import math
import time

from instance import VRPTWInstance
from solution import Route, Solution


def insertion_delta(inst: VRPTWInstance, route: Route, pos: int, customer: int) -> int:
    """Calculate cost delta of inserting customer at position pos in route."""
    c = inst.travel_time
    d = inst.depot

    if len(route) == 0:
        prev = d
        succ = d
    else:
        prev = d if pos == 0 else route[pos - 1]
        succ = d if pos == len(route) else route[pos]

    old_cost = c[prev][succ]
    new_cost = c[prev][customer] + c[customer][succ]
    return new_cost - old_cost


def route_load(inst: VRPTWInstance, route: Route) -> int:
    """Calculate total demand of a route."""
    return sum(inst.demand[c] for c in route)


def is_time_feasible_route(inst: VRPTWInstance, route: Route) -> bool:
    """Check if route satisfies all time windows."""
    c = inst.travel_time
    ready = inst.ready_time
    due = inst.due_time
    service = inst.service_time
    d = inst.depot

    t = 0
    prev = d

    for cust in route:
        t += c[prev][cust]
        if t < ready[cust]:
            t = ready[cust]
        if t > due[cust]:
            return False
        t += service[cust]
        prev = cust

    t += c[prev][d]
    if t > due[d]:
        return False
    return True


def is_time_feasible_insertion(inst: VRPTWInstance, route: Route, pos: int, customer: int) -> bool:
    """Check if inserting customer at pos maintains time feasibility."""
    new_route = route[:pos] + [customer] + route[pos:]
    return is_time_feasible_route(inst, new_route)


@dataclass
class RegretInfo:
    customer: int
    best_cost: int
    regret: float


def best_two_insertions(inst: VRPTWInstance, sol: Solution, customer: int) -> Tuple[Optional[int], Optional[int]]:
    """
    Find best and second-best insertion costs for a customer.
    Returns (best_cost, second_best_cost) or (None, None) if infeasible.
    """
    best = math.inf
    second = math.inf

    # Try inserting into existing routes
    for route in sol:
        if route_load(inst, route) + inst.demand[customer] > inst.capacity:
            continue
        for pos in range(len(route) + 1):
            if not is_time_feasible_insertion(inst, route, pos, customer):
                continue
            delta = insertion_delta(inst, route, pos, customer)
            if delta < best:
                second = best
                best = delta
            elif delta < second:
                second = delta

    # Try opening a new route
    can_open_new = len(sol.routes) < inst.n_vehicles
    if can_open_new and inst.demand[customer] <= inst.capacity:
        new_route = [customer]
        if is_time_feasible_route(inst, new_route):
            d = inst.depot
            c = inst.travel_time
            new_cost = c[d][customer] + c[customer][d]
            if new_cost < best:
                second = best
                best = new_cost
            elif new_cost < second:
                second = new_cost

    if best is math.inf:
        return None, None
    if second is math.inf:
        return best, None
    return best, second


def compute_regret_list(inst: VRPTWInstance, sol: Solution, unrouted: List[int]) -> List[RegretInfo]:
    """Compute regret values for all unrouted customers."""
    infos: List[RegretInfo] = []
    for cust in unrouted:
        c1, c2 = best_two_insertions(inst, sol, cust)
        if c1 is None:
            continue
        regret = 1e9 if c2 is None else (c2 - c1)
        infos.append(RegretInfo(customer=cust, best_cost=c1, regret=regret))
    return infos


def regret_insertion_construct(
    inst: VRPTWInstance,
    deadline: Optional[float] = None,
    verbose: bool = False,
) -> Solution:
    """
    Builds initial solution using regret insertion heuristic.
    
    Args:
        inst: VRPTW instance
        deadline: Optional time deadline (perf_counter)
        verbose: Print progress
        
    Returns:
        Solution (may be partial if deadline reached)
    """
    n_nodes = inst.n_nodes
    customers = [i for i in range(n_nodes) if i != inst.depot]
    unrouted = customers[:]
    sol = Solution()

    it = 0
    while unrouted:
        it += 1
        
        if deadline is not None and time.perf_counter() >= deadline:
            if verbose:
                print(f"[WARN] Deadline reached, {len(unrouted)} customers unrouted")
            break

        infos = compute_regret_list(inst, sol, unrouted)
        if not infos:
            if verbose:
                print(f"[WARN] No feasible insertions, {len(unrouted)} customers unrouted")
            break

        infos.sort(key=lambda x: (-x.regret, x.best_cost))
        chosen = infos[0].customer

        # Find best insertion position
        best_delta = math.inf
        best_r = None
        best_pos = None

        for r_idx, route in enumerate(sol.routes):
            if route_load(inst, route) + inst.demand[chosen] > inst.capacity:
                continue
            for pos in range(len(route) + 1):
                if not is_time_feasible_insertion(inst, route, pos, chosen):
                    continue
                delta = insertion_delta(inst, route, pos, chosen)
                if delta < best_delta:
                    best_delta = delta
                    best_r = r_idx
                    best_pos = pos

        # Try new route
        if len(sol.routes) < inst.n_vehicles and inst.demand[chosen] <= inst.capacity:
            if is_time_feasible_route(inst, [chosen]):
                d = inst.depot
                c = inst.travel_time
                new_cost = c[d][chosen] + c[chosen][d]
                if new_cost < best_delta:
                    best_delta = new_cost
                    best_r = "NEW"
                    best_pos = 0

        if best_r is None:
            if verbose:
                print(f"[WARN] Could not place customer {chosen}")
            break

        if best_r == "NEW":
            sol.routes.append([chosen])
        else:
            sol.routes[best_r].insert(best_pos, chosen)

        unrouted.remove(chosen)

    return sol
