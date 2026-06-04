"""Tests for reference graph loading and validation."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import networkx as nx

from blindspot.reference import (
    load_reference,
    list_references,
    save_reference,
    validate_reference,
    ReferenceError,
    _validate_schema,
)


class TestValidateSchema:
    def test_valid_schema(self):
        data = {
            "nodes": [{"id": "a"}, {"id": "b"}],
            "edges": [{"from": "a", "to": "b"}],
        }
        assert _validate_schema(data) == []

    def test_missing_nodes(self):
        errors = _validate_schema({"edges": []})
        assert any("nodes" in e for e in errors)

    def test_missing_edges(self):
        errors = _validate_schema({"nodes": []})
        assert any("edges" in e for e in errors)

    def test_node_missing_id(self):
        data = {"nodes": [{"name": "a"}], "edges": []}
        errors = _validate_schema(data)
        assert any("id" in e for e in errors)

    def test_edge_missing_from(self):
        data = {"nodes": [{"id": "a"}], "edges": [{"to": "b"}]}
        errors = _validate_schema(data)
        assert any("from" in e for e in errors)

    def test_edge_missing_to(self):
        data = {"nodes": [{"id": "a"}], "edges": [{"from": "a"}]}
        errors = _validate_schema(data)
        assert any("to" in e for e in errors)

    def test_nodes_not_list(self):
        errors = _validate_schema({"nodes": "bad", "edges": []})
        assert any("list" in e for e in errors)


class TestLoadReference:
    def test_load_bundled_python_basics(self):
        graph = load_reference("python-basics")
        assert isinstance(graph, nx.DiGraph)
        assert len(graph.nodes()) > 20

    def test_load_bundled_cell_biology(self):
        graph = load_reference("cell-biology")
        assert isinstance(graph, nx.DiGraph)
        assert len(graph.nodes()) > 15

    def test_missing_reference_raises(self):
        with pytest.raises(ReferenceError, match="not found"):
            load_reference("nonexistent-topic-xyz")

    def test_nodes_are_lowercase(self):
        graph = load_reference("python-basics")
        for node in graph.nodes():
            assert node == node.lower()

    def test_load_from_custom_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {
                "nodes": [{"id": "alpha"}, {"id": "beta"}],
                "edges": [{"from": "alpha", "to": "beta", "relation": "prerequisite"}],
            }
            path = Path(tmpdir) / "test-topic.json"
            path.write_text(json.dumps(data))

            graph = load_reference("test-topic", search_dir=Path(tmpdir))
            assert "alpha" in graph.nodes()
            assert "beta" in graph.nodes()
            assert graph.has_edge("alpha", "beta")


class TestListReferences:
    def test_lists_bundled_references(self):
        refs = list_references()
        assert "python-basics" in refs
        assert "cell-biology" in refs

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            refs = list_references(search_dir=Path(tmpdir))
            assert refs == []

    def test_returns_sorted(self):
        refs = list_references()
        assert refs == sorted(refs)


class TestSaveReference:
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nodes = [{"id": "x"}, {"id": "y"}]
            edges = [{"from": "x", "to": "y"}]
            path = save_reference("roundtrip", nodes, edges, search_dir=Path(tmpdir))

            assert path.exists()

            graph = load_reference("roundtrip", search_dir=Path(tmpdir))
            assert "x" in graph.nodes()
            assert graph.has_edge("x", "y")

    def test_save_invalid_data_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ReferenceError):
                save_reference("bad", [{"no_id": "x"}], [], search_dir=Path(tmpdir))

    def test_save_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "sub" / "dir"
            save_reference("nested", [{"id": "a"}], [], search_dir=nested)
            assert (nested / "nested.json").exists()


class TestValidateReference:
    def test_bundled_graphs_are_valid(self):
        for name in ["python-basics", "cell-biology", "linear-algebra"]:
            issues = validate_reference(name)
            assert issues == [], f"{name} has issues: {issues}"

    def test_detects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {
                "nodes": [{"id": "alpha"}, {"id": "alpha"}],
                "edges": [{"from": "alpha", "to": "alpha"}],
            }
            path = Path(tmpdir) / "dup.json"
            path.write_text(json.dumps(data))
            issues = validate_reference("dup", search_dir=Path(tmpdir))
            assert any("Duplicate" in i for i in issues)

    def test_detects_dangling_edge(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {
                "nodes": [{"id": "alpha"}],
                "edges": [{"from": "alpha", "to": "missing"}],
            }
            path = Path(tmpdir) / "dangle.json"
            path.write_text(json.dumps(data))
            issues = validate_reference("dangle", search_dir=Path(tmpdir))
            assert any("unknown" in i.lower() for i in issues)

    def test_detects_orphan_node(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {
                "nodes": [{"id": "alpha"}, {"id": "beta"}, {"id": "orphan"}],
                "edges": [{"from": "alpha", "to": "beta"}],
            }
            path = Path(tmpdir) / "orphan.json"
            path.write_text(json.dumps(data))
            issues = validate_reference("orphan", search_dir=Path(tmpdir))
            assert any("orphan" in i.lower() for i in issues)

    def test_detects_cycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {
                "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
                "edges": [
                    {"from": "a", "to": "b"},
                    {"from": "b", "to": "c"},
                    {"from": "c", "to": "a"},
                ],
            }
            path = Path(tmpdir) / "cycle.json"
            path.write_text(json.dumps(data))
            issues = validate_reference("cycle", search_dir=Path(tmpdir))
            assert any("Cycle" in i for i in issues)

    def test_missing_reference_raises(self):
        with pytest.raises(ReferenceError, match="not found"):
            validate_reference("does-not-exist-xyz")

    def test_clean_graph_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {
                "nodes": [{"id": "a"}, {"id": "b"}],
                "edges": [{"from": "a", "to": "b"}],
            }
            path = Path(tmpdir) / "clean.json"
            path.write_text(json.dumps(data))
            issues = validate_reference("clean", search_dir=Path(tmpdir))
            assert issues == []
