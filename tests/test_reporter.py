"""Tests for the report formatter."""

from __future__ import annotations

import networkx as nx

from blindspot.analyzer import AnalysisResult, Gap
from blindspot.reporter import format_cli_report, format_html_report, build_pyvis_html


def _sample_result() -> AnalysisResult:
    return AnalysisResult(
        coverage=0.6,
        matched_concepts=["variables", "functions", "loops"],
        gaps=[
            Gap(concept="classes", gap_type="missing_node", severity=0.7, details="Not found"),
            Gap(
                concept="variables -> classes",
                gap_type="missing_edge",
                severity=0.3,
                details="You mentioned both but did not connect them",
            ),
            Gap(concept="scope", gap_type="isolated", severity=0.4, details="Unconnected"),
        ],
        study_order=["classes", "inheritance"],
        user_node_count=5,
        reference_node_count=5,
    )


class TestFormatCliReport:
    def test_contains_topic_name(self):
        result = _sample_result()
        report = format_cli_report(result, "python-basics")
        assert "python-basics" in report

    def test_contains_coverage_percentage(self):
        result = _sample_result()
        report = format_cli_report(result, "test")
        assert "60.0%" in report

    def test_contains_matched_concepts(self):
        result = _sample_result()
        report = format_cli_report(result, "test")
        assert "[+] functions" in report
        assert "[+] loops" in report
        assert "[+] variables" in report

    def test_contains_missing_concepts(self):
        result = _sample_result()
        report = format_cli_report(result, "test")
        assert "[-] classes" in report

    def test_contains_missing_connections(self):
        result = _sample_result()
        report = format_cli_report(result, "test")
        assert "[~]" in report

    def test_contains_isolated_concepts(self):
        result = _sample_result()
        report = format_cli_report(result, "test")
        assert "[?] scope" in report

    def test_contains_study_order(self):
        result = _sample_result()
        report = format_cli_report(result, "test")
        assert "1. classes" in report
        assert "2. inheritance" in report

    def test_severity_bar_present(self):
        result = _sample_result()
        report = format_cli_report(result, "test")
        assert "#" in report

    def test_no_gaps_message(self):
        result = AnalysisResult(
            coverage=1.0,
            matched_concepts=["a", "b"],
            gaps=[],
            study_order=[],
            user_node_count=2,
            reference_node_count=2,
        )
        report = format_cli_report(result, "test")
        assert "No gaps found" in report

    def test_correct_concept_counts(self):
        result = _sample_result()
        report = format_cli_report(result, "test")
        assert "3/5 concepts" in report
        assert "5 identifiable concepts" in report

    def test_zero_coverage(self):
        result = AnalysisResult(
            coverage=0.0,
            matched_concepts=[],
            gaps=[Gap(concept="x", gap_type="missing_node", severity=0.5)],
            study_order=["x"],
            user_node_count=0,
            reference_node_count=1,
        )
        report = format_cli_report(result, "empty")
        assert "0.0%" in report


class TestFormatHtmlReport:
    def test_contains_html_heading(self):
        result = _sample_result()
        html = format_html_report(result, "python-basics")
        assert "<h2>" in html
        assert "python-basics" in html

    def test_contains_coverage_info(self):
        result = _sample_result()
        html = format_html_report(result, "test")
        assert "60.0%" in html

    def test_escapes_html_in_topic(self):
        result = _sample_result()
        html = format_html_report(result, "<script>alert(1)</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_missing_concepts_have_severity_bar(self):
        result = _sample_result()
        html = format_html_report(result, "test")
        assert "background:#F44336" in html

    def test_no_gaps_shows_success_message(self):
        result = AnalysisResult(
            coverage=1.0,
            matched_concepts=["a"],
            gaps=[],
            study_order=[],
            user_node_count=1,
            reference_node_count=1,
        )
        html = format_html_report(result, "test")
        assert "No gaps found" in html

    def test_study_order_as_ordered_list(self):
        result = _sample_result()
        html = format_html_report(result, "test")
        assert "<ol>" in html
        assert "<li>classes</li>" in html


class TestBuildPyvisHtml:
    def test_returns_html_string(self):
        user = nx.DiGraph()
        user.add_node("variables")
        ref = nx.DiGraph()
        ref.add_node("variables")
        ref.add_node("loops")
        ref.add_edge("variables", "loops", relation="prerequisite")

        html = build_pyvis_html(user, ref, ["variables"], "test")
        assert isinstance(html, str)
        # pyvis generates full HTML documents
        assert "html" in html.lower() or "pyvis" in html.lower() or "not installed" in html.lower()

    def test_missing_pyvis_returns_message(self, monkeypatch):
        """When pyvis is not importable, we get a helpful message."""
        import builtins

        real_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pyvis.network":
                raise ImportError("mocked")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)
        user = nx.DiGraph()
        ref = nx.DiGraph()
        ref.add_node("x")
        html = build_pyvis_html(user, ref, [], "test")
        assert "not installed" in html
