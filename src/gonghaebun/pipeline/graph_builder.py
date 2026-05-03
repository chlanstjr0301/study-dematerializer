"""
Stage 2: Prerequisite Graph Builder.

Builds the prerequisite DAG for a concept from the knowledge base.
In MVP 1 this is a pure lookup — no LLM.

Validates: no cycles, max depth 3.
"""
from __future__ import annotations

from datetime import datetime, timezone

from gonghaebun.knowledge.real_analysis import CONCEPTS, PREREQUISITE_EDGES
from gonghaebun.models.graph import PrerequisiteEdge, PrerequisiteGraph, PrerequisiteNode

MAX_DEPTH = 3


class GraphCycleError(ValueError):
    """Raised if the prerequisite graph contains a cycle."""


def build_prerequisite_graph(concept_id: str) -> PrerequisiteGraph:
    """
    Build and return the PrerequisiteGraph rooted at concept_id.
    Performs BFS up to MAX_DEPTH levels of prerequisites.
    """
    nodes: dict[str, PrerequisiteNode] = {}
    edges: list[PrerequisiteEdge] = []

    visited: set[str] = set()
    queue: list[tuple[str, int]] = [(concept_id, 0)]

    while queue:
        cid, depth = queue.pop(0)
        if cid in visited:
            continue
        visited.add(cid)

        concept = CONCEPTS.get(cid)
        canonical_name = concept.canonical_name if concept else cid
        nodes[cid] = PrerequisiteNode(
            concept_id=cid,
            canonical_name=canonical_name,
            depth=depth,
        )

        if depth >= MAX_DEPTH:
            continue

        for prereq_id in PREREQUISITE_EDGES.get(cid, []):
            edges.append(PrerequisiteEdge(from_concept=cid, to_concept=prereq_id))
            if prereq_id not in visited:
                queue.append((prereq_id, depth + 1))

    graph = PrerequisiteGraph(
        root_concept_id=concept_id,
        nodes=list(nodes.values()),
        edges=edges,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    if graph.has_cycle():
        raise GraphCycleError(
            f"Prerequisite graph for {concept_id!r} contains a cycle."
        )

    return graph
