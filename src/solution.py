# src/solution.py
"""
Solution representation for VRPTW.
"""
from dataclasses import dataclass, field
from typing import List, Iterator

Route = List[int]  # List of customer node indices


@dataclass
class Solution:
    """
    VRPTW solution containing multiple routes.
    
    Attributes:
        routes: List of routes, where each route is a list of customer indices
    """
    routes: List[Route] = field(default_factory=list)

    def __iter__(self) -> Iterator[Route]:
        """Iterate over routes."""
        return iter(self.routes)

    def copy(self) -> "Solution":
        """Create deep copy of solution."""
        return Solution(routes=[r[:] for r in self.routes])
    
    def num_routes(self) -> int:
        """Number of routes in solution."""
        return len(self.routes)
    
    def num_customers(self) -> int:
        """Total number of customers served."""
        return sum(len(r) for r in self.routes)
