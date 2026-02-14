# src/solver.py
"""
Main VRPTW solver combining regret construction + local search + validation.
"""
from typing import Tuple
import time

from instance import VRPTWInstance
from solution import Solution
from regret_constructor import regret_insertion_construct
from local_search import local_search, solution_cost
from validation import validate_solution


def solve_instance(
    inst: VRPTWInstance,
    budget_s: float,
    validate: bool = True,
    verbose: bool = False,
) -> Tuple[Solution, int, int, bool]:
    """
    Solve VRPTW instance with regret+LS.
    
    Args:
        inst: VRPTW instance
        budget_s: Wall-clock time budget in seconds
        validate: Perform validation
        verbose: Print progress
        
    Returns:
        (solution, init_cost, final_cost, is_valid)
    """
    t0 = time.perf_counter()
    deadline = t0 + float(budget_s)

    # Construction
    if verbose:
        print("[PHASE] Regret construction...")
    sol = regret_insertion_construct(inst, deadline=deadline, verbose=verbose)
    init_cost = solution_cost(inst, sol)

    # Local search
    if verbose:
        print("[PHASE] Local search...")
    sol = local_search(inst, sol, deadline=deadline, verbose=verbose)
    final_cost = solution_cost(inst, sol)

    # Validation
    is_valid = True
    if validate:
        if verbose:
            print("\n[VALIDATION]")
        result = validate_solution(inst, sol, verbose=verbose)
        is_valid = result.is_valid
        
        if not verbose and not is_valid:
            print(f"⚠️  VALIDATION FAILED: {result.total_violations} violations")

    return sol, init_cost, final_cost, is_valid
