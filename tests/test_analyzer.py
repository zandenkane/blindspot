"""Tests for the gap analyzer."""

from __future__ import annotations

import pytest
import networkx as nx

from blindspot.analyzer import analyze, AnalysisResult, Gap


def _make_ref_graph() -> nx.DiGraph:
    """Build a small reference graph for testing."""
    g = nx.DiGraph()
    g.add_node("variables", tier=1)
    g.add_node("data types", tier=1)
    g.add_node("functions", tier=1)
    g.add_node("loops", tier=1)
    g.add_node("classes", tier=2)
    g.add_edge("variables", "data types", relation="prerequisite")
    g.add_edge("variables", "loops", relation="prerequisite")
    g.add_edge("variables", "functions", relation="prerequisite")
    g.add_edge("functions", "classes", relation="prerequisite")
    return g


def _make_user_graph(concepts: list[str], edges: list[tuple[str, str]] | None = None) -> nx.DiGraph:
    """Build a user concept graph from a list of concepts."""
    g = nx.DiGraph()
    for c in concepts:
        g.add_node(c)
    if edges:
        for src, dst in edges:
            g.add_edge(src, dst)
    return g


class TestAnalyze:
    @pytest.fixture(scope="module")
    def nlp(self):
        import spacy
        try:
            return spacy.load("en_core_web_md")
        except OSError:
            pytest.skip("en_core_web_md model not installed")

    def test_full_coverage(self, nlp):
        ref = _make_ref_graph()
        user = _make_user_graph(["variables", "data types", "functions", "loops", "classes"])
        result = analyze(user, ref, nlp=nlp)
        assert result.coverage == 1.0
        assert len(result.matched_concepts) == 5

    def test_partial_coverage(self, nlp):
        ref = _make_ref_graph()
        user = _make_user_graph(["variables", "functions"])
        result = analyze(user, ref, nlp=nlp)
        assert 0.0 < result.coverage < 1.0
        assert "variables" in result.matched_concepts
        assert "functions" in result.matched_concepts

    def test_zero_coverage(self, nlp):
        ref = _make_ref_graph()
        user = _make_user_graph(["quantum physics", "relativity"])
        result = analyze(user, ref, nlp=nlp)
        # Coverage should be very low (possibly not exactly 0 due to fuzzy matching)
        assert result.coverage < 0.5

    def test_empty_reference_graph(self, nlp):
        ref = nx.DiGraph()
        user = _make_user_graph(["variables"])
        result = analyze(user, ref, nlp=nlp)
        assert result.coverage == 1.0

    def test_empty_user_graph(self, nlp):
        ref = _make_ref_graph()
        user = nx.DiGraph()
        result = analyze(user, ref, nlp=nlp)
        assert result.coverage == 0.0
        assert len(result.gaps) == 5

    def test_gaps_sorted_by_severity(self, nlp):
        ref = _make_ref_graph()
        user = nx.DiGraph()
        result = analyze(user, ref, nlp=nlp)
        missing_nodes = [g for g in result.gaps if g.gap_type == "missing_node"]
        severities = [g.severity for g in missing_nodes]
        assert severities == sorted(severities, reverse=True)

    def test_study_order_is_list(self, nlp):
        ref = _make_ref_graph()
        user = _make_user_graph(["variables"])
        result = analyze(user, ref, nlp=nlp)
        assert isinstance(result.study_order, list)

    def test_result_has_correct_counts(self, nlp):
        ref = _make_ref_graph()
        user = _make_user_graph(["variables", "loops", "extra concept"])
        result = analyze(user, ref, nlp=nlp)
        assert result.reference_node_count == 5
        assert result.user_node_count == 3


class TestAnalysisResult:
    def test_dataclass_fields(self):
        result = AnalysisResult(coverage=0.5)
        assert result.coverage == 0.5
        assert result.matched_concepts == []
        assert result.gaps == []
        assert result.study_order == []

    def test_to_dict_structure(self):
        result = AnalysisResult(
            coverage=0.75,
            matched_concepts=["a", "b"],
            gaps=[Gap(concept="c", gap_type="missing_node", severity=0.6, details="info")],
            study_order=["c"],
            user_node_count=3,
            reference_node_count=4,
        )
        d = result.to_dict()
        assert d["coverage"] == 0.75
        assert d["matched_concepts"] == ["a", "b"]
        assert len(d["gaps"]) == 1
        assert d["gaps"][0]["concept"] == "c"
        assert d["gaps"][0]["type"] == "missing_node"
        assert d["gaps"][0]["severity"] == 0.6
        assert d["study_order"] == ["c"]

    def test_to_dict_empty(self):
        result = AnalysisResult(coverage=1.0)
        d = result.to_dict()
        assert d["coverage"] == 1.0
        assert d["gaps"] == []
        assert d["matched_concepts"] == []

    def test_missing_count(self):
        result = AnalysisResult(
            coverage=0.5,
            gaps=[
                Gap(concept="a", gap_type="missing_node", severity=0.5),
                Gap(concept="b", gap_type="missing_node", severity=0.3),
                Gap(concept="x -> y", gap_type="missing_edge", severity=0.2),
            ],
        )
        assert result.missing_count == 2

    def test_missing_count_zero(self):
        result = AnalysisResult(coverage=1.0)
        assert result.missing_count == 0

    def test_average_gap_severity(self):
        result = AnalysisResult(
            coverage=0.5,
            gaps=[
                Gap(concept="a", gap_type="missing_node", severity=0.4),
                Gap(concept="b", gap_type="missing_node", severity=0.6),
            ],
        )
        assert result.average_gap_severity == pytest.approx(0.5)

    def test_average_gap_severity_no_gaps(self):
        result = AnalysisResult(coverage=1.0)
        assert result.average_gap_severity == 0.0

    def test_average_gap_severity_ignores_edges(self):
        result = AnalysisResult(
            coverage=0.5,
            gaps=[
                Gap(concept="a", gap_type="missing_node", severity=0.8),
                Gap(concept="x -> y", gap_type="missing_edge", severity=0.2),
            ],
        )
        assert result.average_gap_severity == pytest.approx(0.8)


class TestGap:
    def test_gap_creation(self):
        gap = Gap(concept="loops", gap_type="missing_node", severity=0.8)
        assert gap.concept == "loops"
        assert gap.gap_type == "missing_node"
        assert gap.severity == 0.8
        assert gap.details == ""

    def test_gap_with_details(self):
        gap = Gap(
            concept="loops",
            gap_type="missing_node",
            severity=0.65,
            details="Not found in your description (reference has 3 dependents)",
        )
        assert "3 dependents" in gap.details
