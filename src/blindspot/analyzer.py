"""Compare a user's concept graph against a reference graph to find knowledge gaps."""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
import spacy


@dataclass
class Gap:

    concept: str
    gap_type: str  # "missing_node", "missing_edge", "isolated"
    severity: float  # 0.0 to 1.0
    details: str = ""


@dataclass
class AnalysisResult:
    """Full gap analysis output."""

    coverage: float  # 0.0 to 1.0
    matched_concepts: list[str] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)
    study_order: list[str] = field(default_factory=list)
    user_node_count: int = 0
    reference_node_count: int = 0

    def to_dict(self) -> dict:
        """Serialize the result to a plain dictionary (JSON-safe)."""
        return {
            "coverage": round(self.coverage, 4),
            "matched_concepts": self.matched_concepts,
            "gaps": [
                {
                    "concept": g.concept,
                    "type": g.gap_type,
                    "severity": round(g.severity, 4),
                    "details": g.details,
                }
                for g in self.gaps
            ],
            "study_order": self.study_order,
            "user_node_count": self.user_node_count,
            "reference_node_count": self.reference_node_count,
        }

    @property
    def missing_count(self) -> int:
        """Number of reference concepts not found in user text."""
        return sum(1 for g in self.gaps if g.gap_type == "missing_node")

    @property
    def average_gap_severity(self) -> float:
        missing = [g for g in self.gaps if g.gap_type == "missing_node"]
        if not missing:
            return 0.0
        return sum(g.severity for g in missing) / len(missing)


def _best_match_score(
    concept: str,
    user_concepts: list[str],
    nlp: spacy.language.Language,
) -> float:
    """Find the highest similarity score between a concept and user concepts.

    Uses spaCy word vectors for fuzzy matching.
    if not user_concepts:
        return 0.0

    concept_doc = nlp(concept)
    best = 0.0
    for uc in user_concepts:
        uc_doc = nlp(uc)
        sim = concept_doc.similarity(uc_doc)
        if sim > best:
            best = sim
    return best


def _compute_severity(
    concept: str,
    ref_graph: nx.DiGraph,
    max_out_degree: int,
) -> float:
    """Score severity based on how many concepts depend on this one.

    Concepts with higher out-degree (more dependents) get higher severity.
    Prerequisite-tier concepts also get a boost.
    """
    out_deg = ref_graph.out_degree(concept)
    in_deg = ref_graph.in_degree(concept)

    # Normalize out-degree to 0-1 range
    degree_score = out_deg / max(max_out_degree, 1)

    # Concepts with low in-degree are foundational (fewer prerequisites)
    foundation_bonus = 0.2 if in_deg == 0 else 0.0

    # Check tier attribute if present
    tier = ref_graph.nodes[concept].get("tier", 3)
    tier_bonus = max(0, (4 - tier)) * 0.1  # tier 1 = +0.3, tier 2 = +0.2, tier 3 = +0.1

    raw = degree_score * 0.5 + tier_bonus + foundation_bonus
    return min(1.0, max(0.0, raw))


def analyze(
    user_graph: nx.DiGraph,
    ref_graph: nx.DiGraph,
    nlp: spacy.language.Language | None = None,
    similarity_threshold: float = 0.75,
) -> AnalysisResult:
    """Compare a user's extracted concept graph against a reference graph.

    Args:
        user_graph: Graph of concepts extracted from user's text.
        ref_graph: Reference graph defining the complete topic.
        nlp: Pre-loaded spaCy model for similarity. Loads en_core_web_md if None.
        similarity_threshold: Minimum similarity score to count as a match (0-1).

    Returns:
        AnalysisResult with coverage, gaps, and suggested study order.
    if nlp is None:
        import spacy as sp
        nlp = sp.load("en_core_web_md")

    user_concepts = list(user_graph.nodes())
    ref_concepts = list(ref_graph.nodes())

    if not ref_concepts:
        return AnalysisResult(
            coverage=1.0,
            matched_concepts=[],
            gaps=[],
            study_order=[],
            user_node_count=len(user_concepts),
            reference_node_count=0,
        )

    # Phase 1: Find which reference concepts the user covered
    matched: list[str] = []
    missing: list[str] = []
    max_out = max((ref_graph.out_degree(n) for n in ref_concepts), default=0)

    for concept in ref_concepts:
        # Exact match first
        if concept in user_concepts:
            matched.append(concept)
            continue

        # Fuzzy match via word vectors
        score = _best_match_score(concept, user_concepts, nlp)
        if score >= similarity_threshold:
            matched.append(concept)
        else:
            missing.append(concept)

    coverage = len(matched) / len(ref_concepts) if ref_concepts else 1.0

    # Phase 2: Build gap list
    gaps: list[Gap] = []

    for concept in missing:
        severity = _compute_severity(concept, ref_graph, max_out)
        gaps.append(Gap(
            concept=concept,
            gap_type="missing_node",
            severity=severity,
            details=f"Not found in your description (reference has {ref_graph.out_degree(concept)} dependents)",
        ))

    # Phase 3: Missing edges (relationships between concepts the user mentioned
    # but did not connect)
    for src, dst, data in ref_graph.edges(data=True):
        if src in matched and dst in matched:
            # Both concepts present; check if user connected them
            has_connection = False
            if user_graph.has_edge(src, dst) or user_graph.has_edge(dst, src):
                has_connection = True
            else:
                # Check fuzzy matches in user edges
                for u_src, u_dst in user_graph.edges():
                    src_doc = nlp(src)
                    dst_doc = nlp(dst)
                    u_src_doc = nlp(u_src)
                    u_dst_doc = nlp(u_dst)
                    if (src_doc.similarity(u_src_doc) >= similarity_threshold and
                            dst_doc.similarity(u_dst_doc) >= similarity_threshold):
                        has_connection = True
                        break
            if not has_connection:
                relation = data.get("relation", "related-to")
                gaps.append(Gap(
                    concept=f"{src} -> {dst}",
                    gap_type="missing_edge",
                    severity=0.3,
                    details=f"You mentioned both concepts but did not connect them ({relation})",
                ))

    # Phase 4: Isolated clusters in user graph
    undirected = user_graph.to_undirected()
    components = list(nx.connected_components(undirected))
    if len(components) > 1:
        for comp in components:
            if len(comp) == 1:
                concept = list(comp)[0]
                gaps.append(Gap(
                    concept=concept,
                    gap_type="isolated",
                    severity=0.4,
                    details="Mentioned but not connected to any other concept",
                ))

    # Sort gaps by severity (highest first)
    gaps.sort(key=lambda g: g.severity, reverse=True)

    # Phase 5: Suggested study order (topological sort of missing concepts)
    missing_subgraph = ref_graph.subgraph(missing).copy()
    try:
        study_order = list(nx.topological_sort(missing_subgraph))
    except nx.NetworkXUnfeasible:
        # Graph has cycles; fall back to sorting by severity
        study_order = [g.concept for g in gaps if g.gap_type == "missing_node"]

    return AnalysisResult(
        coverage=coverage,
        matched_concepts=matched,
        gaps=gaps,
        study_order=study_order,
        user_node_count=len(user_concepts),
        reference_node_count=len(ref_concepts),
    )
