from __future__ import annotations
from dataclasses import dataclass, field
from .concept import MasteryLevel


@dataclass
class PrerequisiteNode:
    concept_id: str
    canonical_name: str
    depth: int
    mastery_state: MasteryLevel = "unknown"


@dataclass
class PrerequisiteEdge:
    from_concept: str   # prerequisite
    to_concept: str     # depends on prerequisite


@dataclass
class PrerequisiteGraph:
    root_concept_id: str
    nodes: list[PrerequisiteNode] = field(default_factory=list)
    edges: list[PrerequisiteEdge] = field(default_factory=list)
    generated_at: str = ""

    def has_cycle(self) -> bool:
        """Return True if the graph contains a cycle."""
        adj: dict[str, list[str]] = {}
        for edge in self.edges:
            adj.setdefault(edge.from_concept, []).append(edge.to_concept)

        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            in_stack.add(node)
            for neighbour in adj.get(node, []):
                if neighbour not in visited:
                    if dfs(neighbour):
                        return True
                elif neighbour in in_stack:
                    return True
            in_stack.discard(node)
            return False

        all_nodes = {e.from_concept for e in self.edges} | {e.to_concept for e in self.edges}
        for n in all_nodes:
            if n not in visited:
                if dfs(n):
                    return True
        return False
