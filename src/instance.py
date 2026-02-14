# src/instance.py
"""
VRPTW instance loader for ORTEC instances.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional, Dict
import math
import re


@dataclass
class VRPTWInstance:
    """
    VRPTW instance representation.
    
    Attributes:
        n_vehicles: Number of available vehicles
        capacity: Vehicle capacity
        depot: Depot node index (typically 0)
        travel_time: Distance/time matrix [n x n]
        demand: Demand for each node
        ready_time: Earliest service time for each node
        due_time: Latest service time for each node
        service_time: Service duration for each node
    """
    n_vehicles: int
    capacity: int
    depot: int
    travel_time: List[List[int]]
    demand: List[int]
    ready_time: List[int]
    due_time: List[int]
    service_time: List[int]

    @property
    def n_nodes(self) -> int:
        """Total number of nodes (including depot)."""
        return len(self.demand)


def _euclid_rounded(x1: float, y1: float, x2: float, y2: float) -> int:
    """Euclidean distance rounded to nearest integer."""
    return int(round(math.hypot(x1 - x2, y1 - y2)))


def _parse_header_value(lines: List[str], key: str) -> Optional[int]:
    """Parse header value like 'VEHICLES : 42'."""
    pattern = rf'\b{re.escape(key)}\s*:\s*(\d+)'
    for line in lines:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _find_section(lines: List[str], section_name: str) -> Optional[int]:
    """Find line index where section starts."""
    for idx, line in enumerate(lines):
        if section_name.upper() in line.upper():
            return idx + 1
    return None


def _parse_id_value_section(lines: List[str], start_idx: int) -> Dict[int, int]:
    """Parse section with format: id value"""
    data = {}
    for line in lines[start_idx:]:
        if "SECTION" in line.upper() or "EOF" in line.upper():
            break
        tokens = line.replace("\t", " ").split()
        if len(tokens) >= 2:
            try:
                node_id = int(tokens[0])
                value = int(tokens[1])
                data[node_id] = value
            except ValueError:
                pass
    return data


def _parse_id_two_values_section(lines: List[str], start_idx: int) -> Dict[int, Tuple[int, int]]:
    """Parse section with format: id value1 value2"""
    data = {}
    for line in lines[start_idx:]:
        if "SECTION" in line.upper() or "EOF" in line.upper():
            break
        tokens = line.replace("\t", " ").split()
        if len(tokens) >= 3:
            try:
                node_id = int(tokens[0])
                val1 = int(tokens[1])
                val2 = int(tokens[2])
                data[node_id] = (val1, val2)
            except ValueError:
                pass
    return data


def load_ortec_vrptw(path: Path) -> VRPTWInstance:
    """
    Load ORTEC VRPTW instance from file.
    
    Args:
        path: Path to instance file
        
    Returns:
        VRPTWInstance object
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Instance not found: {path}")

    raw_lines = [ln.strip() for ln in path.read_text(encoding="utf-8", errors="ignore").splitlines()]
    lines = [ln for ln in raw_lines if ln and not ln.startswith("#")]

    # Parse header
    n_vehicles = _parse_header_value(lines, "VEHICLES")
    capacity = _parse_header_value(lines, "CAPACITY")
    dimension = _parse_header_value(lines, "DIMENSION")
    
    if n_vehicles is None or capacity is None:
        raise RuntimeError(f"Failed to parse VEHICLES and/or CAPACITY from {path.name}")
    
    # Parse sections
    travel_time = None
    matrix_idx = _find_section(lines, "EDGE_WEIGHT_SECTION")
    if matrix_idx and dimension:
        all_numbers = []
        for line in lines[matrix_idx:]:
            if "SECTION" in line.upper():
                break
            tokens = line.replace("\t", " ").split()
            for tok in tokens:
                try:
                    all_numbers.append(int(tok))
                except ValueError:
                    pass
        
        if len(all_numbers) >= dimension * dimension:
            travel_time = []
            for i in range(dimension):
                row = all_numbers[i * dimension:(i + 1) * dimension]
                travel_time.append(row)
    
    # Node coordinates
    coords = {}
    coord_idx = _find_section(lines, "NODE_COORD_SECTION")
    if coord_idx:
        for line in lines[coord_idx:]:
            if "SECTION" in line.upper():
                break
            tokens = line.replace("\t", " ").split()
            if len(tokens) >= 3:
                try:
                    node_id = int(tokens[0])
                    x = float(tokens[1])
                    y = float(tokens[2])
                    coords[node_id] = (x, y)
                except ValueError:
                    pass
    
    # Demands
    demand_idx = _find_section(lines, "DEMAND_SECTION")
    demands = _parse_id_value_section(lines, demand_idx) if demand_idx else {}
    
    # Service times
    service_idx = _find_section(lines, "SERVICE_TIME_SECTION")
    services = _parse_id_value_section(lines, service_idx) if service_idx else {}
    
    # Time windows
    tw_idx = _find_section(lines, "TIME_WINDOW_SECTION")
    time_windows = _parse_id_two_values_section(lines, tw_idx) if tw_idx else {}
    
    # Build instance
    all_ids = sorted(set(coords.keys()) | set(demands.keys()) | set(time_windows.keys()))
    n = len(all_ids)
    
    if n == 0:
        raise RuntimeError(f"No customer data found in {path.name}")
    
    depot_id = 1 if 1 in all_ids else all_ids[0]
    id_to_idx = {node_id: i for i, node_id in enumerate(all_ids)}
    depot = id_to_idx[depot_id]
    
    xs = [coords.get(nid, (0.0, 0.0))[0] for nid in all_ids]
    ys = [coords.get(nid, (0.0, 0.0))[1] for nid in all_ids]
    demand = [demands.get(nid, 0) for nid in all_ids]
    service_time = [services.get(nid, 0) for nid in all_ids]
    ready_time = [time_windows.get(nid, (0, 99999))[0] for nid in all_ids]
    due_time = [time_windows.get(nid, (0, 99999))[1] for nid in all_ids]
    
    # Build or compute travel time matrix
    if travel_time and len(travel_time) == n:
        pass  # Use provided matrix
    else:
        travel_time = [[0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i != j:
                    travel_time[i][j] = _euclid_rounded(xs[i], ys[i], xs[j], ys[j])
    
    return VRPTWInstance(
        n_vehicles=n_vehicles,
        capacity=capacity,
        depot=depot,
        travel_time=travel_time,
        demand=demand,
        ready_time=ready_time,
        due_time=due_time,
        service_time=service_time,
    )
