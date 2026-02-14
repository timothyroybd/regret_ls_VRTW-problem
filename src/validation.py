# src/validation.py
"""
Solution validation module to verify VRPTW constraints.
"""
from typing import List, Tuple, Optional
from dataclasses import dataclass

from instance import VRPTWInstance
from solution import Solution, Route


@dataclass
class RouteValidation:
    """Results of validating a single route."""
    route_idx: int
    is_valid: bool
    violations: List[str]
    total_demand: int
    capacity_limit: int
    arrival_times: List[Tuple[int, int]]
    

@dataclass
class SolutionValidation:
    """Results of validating an entire solution."""
    is_valid: bool
    total_violations: int
    route_validations: List[RouteValidation]
    unrouted_customers: List[int]
    duplicate_customers: List[int]
    

def validate_route_capacity(inst: VRPTWInstance, route: Route) -> Tuple[bool, int, str]:
    """Validate that route respects vehicle capacity."""
    total_demand = sum(inst.demand[c] for c in route)
    is_valid = total_demand <= inst.capacity
    
    if is_valid:
        msg = f"OK: Capacity {total_demand}/{inst.capacity}"
    else:
        msg = f"VIOLATION: Capacity {total_demand} > {inst.capacity} (excess: {total_demand - inst.capacity})"
    
    return is_valid, total_demand, msg


def validate_route_time_windows(inst: VRPTWInstance, route: Route) -> Tuple[bool, List[Tuple[int, int]], List[str]]:
    """Validate that route respects all time windows."""
    c = inst.travel_time
    ready = inst.ready_time
    due = inst.due_time
    service = inst.service_time
    depot = inst.depot
    
    violations = []
    arrival_times = []
    
    current_time = 0
    prev_node = depot
    
    for idx, customer in enumerate(route):
        current_time += c[prev_node][customer]
        arrival_time = current_time
        
        if current_time > due[customer]:
            violations.append(
                f"Customer {customer} (pos {idx}): Arrived at {current_time}, "
                f"due time is {due[customer]} (LATE by {current_time - due[customer]})"
            )
        
        if current_time < ready[customer]:
            current_time = ready[customer]
        
        arrival_times.append((customer, arrival_time))
        current_time += service[customer]
        prev_node = customer
    
    current_time += c[prev_node][depot]
    
    if current_time > due[depot]:
        violations.append(
            f"Depot return: Arrived at {current_time}, "
            f"due time is {due[depot]} (LATE by {current_time - due[depot]})"
        )
    
    is_valid = len(violations) == 0
    return is_valid, arrival_times, violations


def validate_route(inst: VRPTWInstance, route: Route, route_idx: int) -> RouteValidation:
    """Comprehensively validate a single route."""
    violations = []
    
    capacity_ok, total_demand, capacity_msg = validate_route_capacity(inst, route)
    if not capacity_ok:
        violations.append(capacity_msg)
    
    time_ok, arrival_times, time_msgs = validate_route_time_windows(inst, route)
    violations.extend(time_msgs)
    
    is_valid = capacity_ok and time_ok
    
    return RouteValidation(
        route_idx=route_idx,
        is_valid=is_valid,
        violations=violations,
        total_demand=total_demand,
        capacity_limit=inst.capacity,
        arrival_times=arrival_times,
    )


def validate_solution(inst: VRPTWInstance, sol: Solution, verbose: bool = True) -> SolutionValidation:
    """Comprehensively validate an entire solution."""
    route_validations = []
    
    for idx, route in enumerate(sol.routes):
        route_val = validate_route(inst, route, idx)
        route_validations.append(route_val)
    
    all_customers = set(range(inst.n_nodes)) - {inst.depot}
    routed_customers = []
    for route in sol.routes:
        routed_customers.extend(route)
    
    routed_set = set(routed_customers)
    unrouted = sorted(all_customers - routed_set)
    
    duplicate_customers = []
    seen = set()
    for c in routed_customers:
        if c in seen:
            duplicate_customers.append(c)
        seen.add(c)
    
    fleet_violations = []
    if len(sol.routes) > inst.n_vehicles:
        fleet_violations.append(
            f"FLEET SIZE VIOLATION: Using {len(sol.routes)} routes, "
            f"only {inst.n_vehicles} vehicles available"
        )
    
    route_validity = all(rv.is_valid for rv in route_validations)
    coverage_validity = len(unrouted) == 0 and len(duplicate_customers) == 0
    fleet_validity = len(sol.routes) <= inst.n_vehicles
    
    is_valid = route_validity and coverage_validity and fleet_validity
    
    total_violations = sum(len(rv.violations) for rv in route_validations)
    total_violations += len(fleet_violations)
    
    if verbose:
        print("=" * 80)
        print("SOLUTION VALIDATION REPORT")
        print("=" * 80)
        
        print(f"\nOVERALL: {'VALID' if is_valid else 'INVALID'}")
        print(f"Total routes: {len(sol.routes)} (limit: {inst.n_vehicles})")
        print(f"Total violations: {total_violations}")
        
        if fleet_violations:
            print("\nFLEET SIZE:")
            for v in fleet_violations:
                print(f"  {v}")
        else:
            print(f"\nFleet size OK: {len(sol.routes)}/{inst.n_vehicles} vehicles used")
        
        print(f"\nCUSTOMER COVERAGE:")
        total_customers = len(all_customers)
        routed_count = len(routed_set)
        print(f"  Total customers: {total_customers}")
        print(f"  Routed customers: {routed_count}")
        
        if unrouted:
            print(f"  Unrouted customers ({len(unrouted)}): {unrouted[:10]}")
        else:
            print(f"  All customers routed: OK")
        
        if duplicate_customers:
            print(f"  Duplicate customers ({len(duplicate_customers)}): {sorted(set(duplicate_customers))}")
        else:
            print(f"  No duplicate customers: OK")
        
        print(f"\nROUTE VALIDATION:")
        for rv in route_validations:
            status = "VALID" if rv.is_valid else "INVALID"
            print(f"\n  Route {rv.route_idx}: {status}")
            print(f"    Customers: {len(sol.routes[rv.route_idx])}")
            print(f"    Demand: {rv.total_demand}/{rv.capacity_limit}")
            
            if rv.violations:
                print(f"    Violations ({len(rv.violations)}):")
                for v in rv.violations[:3]:
                    print(f"      {v}")
                if len(rv.violations) > 3:
                    print(f"      ... and {len(rv.violations) - 3} more")
        
        print("\n" + "=" * 80)
    
    return SolutionValidation(
        is_valid=is_valid,
        total_violations=total_violations,
        route_validations=route_validations,
        unrouted_customers=unrouted,
        duplicate_customers=duplicate_customers,
    )


def sample_route_validation(inst: VRPTWInstance, sol: Solution, sample_size: int = 3) -> None:
    """Validate a sample of routes with detailed output."""
    import random
    
    print("=" * 80)
    print(f"SAMPLE ROUTE VALIDATION ({sample_size} routes)")
    print("=" * 80)
    
    if not sol.routes:
        print("\nSolution has no routes!")
        return
    
    sample_indices = random.sample(
        range(len(sol.routes)), 
        min(sample_size, len(sol.routes))
    )
    
    for idx in sorted(sample_indices):
        route = sol.routes[idx]
        print(f"\n{'-' * 80}")
        print(f"ROUTE {idx} (Customers: {len(route)})")
        print(f"{'-' * 80}")
        print(f"Route: Depot -> {' -> '.join(map(str, route))} -> Depot")
        
        capacity_ok, total_demand, capacity_msg = validate_route_capacity(inst, route)
        print(f"\nCAPACITY CHECK:")
        print(f"  {capacity_msg}")
        
        time_ok, arrival_times, time_msgs = validate_route_time_windows(inst, route)
        print(f"\nTIME WINDOW CHECK:")
        
        if arrival_times:
            print(f"  Arrival schedule:")
            for customer, arrival_time in arrival_times[:5]:
                ready = inst.ready_time[customer]
                due = inst.due_time[customer]
                status = "OK" if ready <= arrival_time <= due else "LATE"
                wait = max(0, ready - arrival_time)
                print(f"    {status}: Customer {customer} arrive at {arrival_time} "
                      f"[{ready}, {due}]" + (f" (wait {wait})" if wait > 0 else ""))
            if len(arrival_times) > 5:
                print(f"    ... and {len(arrival_times) - 5} more customers")
        
        if time_msgs:
            print(f"\n  Violations:")
            for msg in time_msgs[:3]:
                print(f"    {msg}")
        else:
            print(f"  All time windows satisfied: OK")
    
    print("\n" + "=" * 80)
