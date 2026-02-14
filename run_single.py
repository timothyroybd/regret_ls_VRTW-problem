#!/usr/bin/env python3
"""
Run solver on a single instance.

Usage:
    python run_single.py instances/ORTEC-VRPTW-ASYM-0dc59ef2-d1-n213-k25.txt --budget 300
"""
import argparse
import sys
from pathlib import Path
import time

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from instance import load_ortec_vrptw
from solver import solve_instance


def main():
    parser = argparse.ArgumentParser(description='Run solver on single instance')
    parser.add_argument('instance', type=str, help='Path to instance file')
    parser.add_argument('--budget', type=int, required=True, help='Time budget in seconds')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-validate', action='store_true', help='Skip validation')
    
    args = parser.parse_args()
    
    inst_path = Path(args.instance)
    if not inst_path.exists():
        print(f"Error: Instance file not found: {inst_path}")
        return 1
    
    print(f"{'='*80}")
    print(f"Instance: {inst_path.name}")
    print(f"Budget: {args.budget}s")
    print(f"{'='*80}\n")
    
    # Load instance
    print("Loading instance...")
    inst = load_ortec_vrptw(inst_path)
    print(f"  Nodes: {inst.n_nodes}")
    print(f"  Vehicles: {inst.n_vehicles}")
    print(f"  Capacity: {inst.capacity}\n")
    
    # Solve
    print("Solving...")
    t0 = time.perf_counter()
    sol, init_cost, final_cost, is_valid = solve_instance(
        inst,
        budget_s=args.budget,
        validate=not args.no_validate,
        verbose=args.verbose,
    )
    wall_time = time.perf_counter() - t0
    
    # Results
    improvement_pct = ((init_cost - final_cost) / init_cost * 100) if init_cost > 0 else 0
    
    print(f"\n{'='*80}")
    print("RESULTS")
    print(f"{'='*80}")
    print(f"Initial cost: {init_cost}")
    print(f"Final cost: {final_cost}")
    print(f"Improvement: {improvement_pct:.2f}%")
    print(f"Routes used: {sol.num_routes()}/{inst.n_vehicles}")
    print(f"Wall time: {wall_time:.2f}s")
    print(f"Valid: {'✓ YES' if is_valid else '✗ NO'}")
    print(f"{'='*80}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
