"""Tests for the concept extractor."""

from __future__ import annotations

import pytest
import networkx as nx

from blindspot.extractor import extract_concepts, _normalize, _SPACY_AVAILABLE


class TestNormalize:
    def test_lowercase(self):
        assert _normalize("Hello World") == "hello world"

    def test_strip_whitespace(self):
        assert _normalize("  spaced  ") == "spaced"

    def test_empty_string(self):
        assert _normalize("") == ""


class TestExtractConceptsFallback:
    """Tests for the regex/keyword fallback (no spaCy needed)."""

    def test_returns_digraph(self):
        graph = extract_concepts("Python uses variables to store data.", nlp=None)
        assert isinstance(graph, nx.DiGraph)

    def test_finds_concepts_in_text(self):
        text = "Variables store values. Functions accept parameters and return results."
        graph = extract_concepts(text, nlp=None)
        nodes = set(graph.nodes())
        assert len(nodes) > 0
        assert "variables" in nodes
        assert "functions" in nodes

    def test_empty_text_returns_empty_graph(self):
        graph = extract_concepts("", nlp=None)
        assert len(graph.nodes()) == 0

    def test_concepts_are_lowercase(self):
        text = "Python Variables and Data Types are fundamental concepts."
        graph = extract_concepts(text, nlp=None)
        for node in graph.nodes():
            assert node == node.lower(), f"Node not lowercase: {node}"

    def test_bigrams_extracted(self):
        text = "for loops and while loops are important"
        graph = extract_concepts(text, nlp=None)
        nodes = set(graph.nodes())
        assert "for loops" in nodes
        assert "while loops" in nodes


@pytest.mark.skipif(
    not _SPACY_AVAILABLE,
    reason="spaCy not installed"
)
class TestExtractConceptsSpacy:
    """Tests that run against a real spaCy model."""

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
        assert len(nodes) > 0

    def test_empty_text_returns_empty_graph(self, nlp):
        graph = extract_concepts("", nlp=nlp)
        assert len(graph.nodes()) == 0

    def test_finds_relationships(self, nlp):
        text = "Python uses variables to store integers and strings."
        graph = extract_concepts(text, nlp=nlp)
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
