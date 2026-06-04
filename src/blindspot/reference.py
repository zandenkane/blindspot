"""Load, validate, and manage reference concept graphs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import networkx as nx


REFERENCES_DIR = Path(__file__).parent / "references"


class ReferenceError(Exception):


def _validate_schema(data: dict[str, Any]) -> list[str]:
    """Check that a reference graph dict has the expected structure.

    Returns a list of validation error messages (empty if valid).
    """
    errors: list[str] = []

    if "nodes" not in data:
        errors.append("Missing 'nodes' key")
    elif not isinstance(data["nodes"], list):
        errors.append("'nodes' must be a list")
    else:
        for i, node in enumerate(data["nodes"]):
            if not isinstance(node, dict):
                errors.append(f"nodes[{i}] must be a dict")
                continue
            if "id" not in node:
                errors.append(f"nodes[{i}] missing 'id' key")

    if "edges" not in data:
        errors.append("Missing 'edges' key")
    elif not isinstance(data["edges"], list):
        errors.append("'edges' must be a list")
    else:
        for i, edge in enumerate(data["edges"]):
            if not isinstance(edge, dict):
                errors.append(f"edges[{i}] must be a dict")
                continue
            if "from" not in edge:
                errors.append(f"edges[{i}] missing 'from' key")
            if "to" not in edge:
                errors.append(f"edges[{i}] missing 'to' key")

    return errors


def load_reference(name: str, search_dir: Path | None = None) -> nx.DiGraph:
    """Load a reference graph from a JSON file.

    Args:
        name: Topic name (filename without .json extension).
        search_dir: Directory to search for reference files.
            Defaults to the bundled references/ directory.

    Returns:
        A networkx DiGraph with concept nodes and relationship edges.

    Raises:
        ReferenceError: If the file is not found or has an invalid schema.
    """
    directory = search_dir or REFERENCES_DIR
    filepath = directory / f"{name}.json"

    if not filepath.exists():
        available = list_references(directory)
        raise ReferenceError(
            f"Reference '{name}' not found. "
            f"Available references: {', '.join(available) if available else '(none)'}"
        )

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    errors = _validate_schema(data)
    if errors:
        raise ReferenceError(
            f"Invalid reference graph '{name}': {'; '.join(errors)}"
        )

    graph = nx.DiGraph()

    for node in data["nodes"]:
        attrs = {k: v for k, v in node.items() if k != "id"}
        graph.add_node(node["id"].lower(), **attrs)

    for edge in data["edges"]:
        attrs = {k: v for k, v in edge.items() if k not in ("from", "to")}
        graph.add_edge(edge["from"].lower(), edge["to"].lower(), **attrs)

    return graph


def list_references(search_dir: Path | None = None) -> list[str]:
    """List available reference graph names.

    Args:
        search_dir: Directory to search. Defaults to bundled references/.

    Returns:
        Sorted list of reference names (without .json extension).
    directory = search_dir or REFERENCES_DIR
    if not directory.exists():
        return []
    return sorted(p.stem for p in directory.glob("*.json"))


def validate_reference(name: str, search_dir: Path | None = None) -> list[str]:
    """Check a reference graph for structural issues beyond schema validity.

    Looks for:
      - Duplicate node IDs
      - Edges referencing nodes that do not exist
      - Orphan nodes (no edges in or out)
      - Cycles that would block topological sorting

    Args:
        name: Topic name (filename without .json extension).
        search_dir: Directory to search for the reference file.

    Returns:
        List of issue descriptions. Empty list means the graph is clean.

    Raises:
        ReferenceError: If the file cannot be loaded at all.
    """
    directory = search_dir or REFERENCES_DIR
    filepath = directory / f"{name}.json"

    if not filepath.exists():
        raise ReferenceError(f"Reference '{name}' not found.")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    errors = _validate_schema(data)
    if errors:
        raise ReferenceError(f"Schema errors: {'; '.join(errors)}")

    issues: list[str] = []

    # Check for duplicate IDs
    node_ids = [n["id"].lower() for n in data["nodes"]]
    seen: set[str] = set()
    for nid in node_ids:
        if nid in seen:
            issues.append(f"Duplicate node ID: '{nid}'")
        seen.add(nid)

    node_set = set(node_ids)

    # Check edges reference existing nodes
    for i, edge in enumerate(data["edges"]):
        src = edge["from"].lower()
        dst = edge["to"].lower()
        if src not in node_set:
            issues.append(f"Edge {i} references unknown source node: '{src}'")
        if dst not in node_set:
            issues.append(f"Edge {i} references unknown target node: '{dst}'")

    # Build graph and check for orphans
    graph = nx.DiGraph()
    for nid in node_ids:
        graph.add_node(nid)
    for edge in data["edges"]:
        graph.add_edge(edge["from"].lower(), edge["to"].lower())

    for node in graph.nodes():
        if graph.in_degree(node) == 0 and graph.out_degree(node) == 0:
            issues.append(f"Orphan node (no connections): '{node}'")

    # Check for cycles
    if not nx.is_directed_acyclic_graph(graph):
        cycles = list(nx.simple_cycles(graph))
        for cycle in cycles[:5]:  # Limit output
            cycle_str = " -> ".join(cycle + [cycle[0]])
            issues.append(f"Cycle detected: {cycle_str}")

    return issues


def save_reference(
    name: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    search_dir: Path | None = None,
) -> Path:
    """Save a reference graph to a JSON file.

    Args:
        name: Topic name (becomes the filename).
        nodes: List of node dicts, each with at least an 'id' key.
        edges: List of edge dicts, each with 'from' and 'to' keys.
        search_dir: Directory to write to. Defaults to bundled references/.

    Returns:
        Path to the written file.

    Raises:
        ReferenceError: If the data fails validation.
    """
    data = {"nodes": nodes, "edges": edges}
    errors = _validate_schema(data)
    if errors:
        raise ReferenceError(f"Invalid reference data: {'; '.join(errors)}")

    directory = search_dir or REFERENCES_DIR
    directory.mkdir(parents=True, exist_ok=True)
    filepath = directory / f"{name}.json"

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath
