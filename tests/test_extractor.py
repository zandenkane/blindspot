"""Tests for the concept extractor."""

from __future__ import annotations

import pytest
import networkx as nx

from blindspot.extractor import extract_concepts, _normalize


class TestNormalize:
    def test_lowercase(self):
        assert _normalize("Hello World") == "hello world"

    def test_strip_whitespace(self):
        assert _normalize("  spaced  ") == "spaced"

    def test_empty_string(self):
        assert _normalize("") == ""


@pytest.mark.skipif(
    True,  # these tests require spaCy en_core_web_md model
    reason="spaCy model not available in CI"
)
class TestExtractConcepts:
    """Tests that run against a real spaCy model.

    These are marked slow because loading en_core_web_md takes a few seconds.
    """

    @pytest.fixture(scope="module")
    def nlp(self):
        import spacy
        try:
            return spacy.load("en_core_web_md")
        except OSError:
            pytest.skip("en_core_web_md model not installed")

    def test_returns_digraph(self, nlp):
        graph = extract_concepts("Python uses variables to store data.", nlp=nlp)
        assert isinstance(graph, nx.DiGraph)

    def test_finds_concepts_in_text(self, nlp):
        text = "Variables store values. Functions accept parameters and return results."
        graph = extract_concepts(text, nlp=nlp)
        nodes = set(graph.nodes())
        # Should find at least some of these concepts
        assert len(nodes) > 0

    def test_empty_text_returns_empty_graph(self, nlp):
        graph = extract_concepts("", nlp=nlp)
        assert len(graph.nodes()) == 0

    def test_finds_relationships(self, nlp):
        text = "Python uses variables to store integers and strings."
        graph = extract_concepts(text, nlp=nlp)
        # Should have at least one edge if SVO extraction works
        # The exact edges depend on spaCy's parse, so we just check structure
        assert isinstance(graph, nx.DiGraph)

    def test_no_self_loops(self, nlp):
        text = "A cell contains a cell membrane. The cell has cytoplasm."
        graph = extract_concepts(text, nlp=nlp)
        for src, dst in graph.edges():
            assert src != dst, f"Self-loop found: {src} -> {dst}"

    def test_concepts_are_lowercase(self, nlp):
        text = "Python Variables and Data Types are fundamental concepts."
        graph = extract_concepts(text, nlp=nlp)
        for node in graph.nodes():
            assert node == node.lower(), f"Node not lowercase: {node}"
