"""Tests for the CLI interface."""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from blindspot.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestMainGroup:
    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "blindspot" in result.output

    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0


class TestReferenceList:
    def test_list_shows_references(self, runner):
        result = runner.invoke(main, ["reference", "list"])
        assert result.exit_code == 0
        assert "python-basics" in result.output
        assert "cell-biology" in result.output
        assert "linear-algebra" in result.output


class TestReferenceValidate:
    def test_validate_bundled_graph(self, runner):
        result = runner.invoke(main, ["reference", "validate", "python-basics"])
        assert result.exit_code == 0
        assert "valid" in result.output.lower()

    def test_validate_missing_graph(self, runner):
        result = runner.invoke(main, ["reference", "validate", "nonexistent-xyz"])
        assert result.exit_code != 0

    def test_validate_help(self, runner):
        result = runner.invoke(main, ["reference", "validate", "--help"])
        assert result.exit_code == 0


class TestReferenceInfo:
    def test_info_shows_counts(self, runner):
        result = runner.invoke(main, ["reference", "info", "python-basics"])
        assert result.exit_code == 0
        assert "Nodes:" in result.output
        assert "Edges:" in result.output
        assert "Tiers:" in result.output

    def test_info_missing_graph(self, runner):
        result = runner.invoke(main, ["reference", "info", "nonexistent-xyz"])
        assert result.exit_code != 0

    def test_info_help(self, runner):
        result = runner.invoke(main, ["reference", "info", "--help"])
        assert result.exit_code == 0


class TestAnalyzeCommand:
    def test_analyze_empty_input(self, runner):
        result = runner.invoke(main, ["analyze", "python-basics"], input="")
        # Should fail with empty input
        assert result.exit_code != 0

    def test_analyze_missing_topic(self, runner):
        result = runner.invoke(
            main,
            ["analyze", "nonexistent-topic-xyz"],
            input="Variables store data.",
        )
        assert result.exit_code != 0

    def test_analyze_help(self, runner):
        result = runner.invoke(main, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "TOPIC" in result.output


class TestExportCommand:
    def test_export_empty_input(self, runner):
        result = runner.invoke(main, ["export", "python-basics"], input="")
        assert result.exit_code != 0

    def test_export_missing_topic(self, runner):
        result = runner.invoke(
            main,
            ["export", "nonexistent-topic-xyz"],
            input="Variables store data.",
        )
        assert result.exit_code != 0

    def test_export_help(self, runner):
        result = runner.invoke(main, ["export", "--help"])
        assert result.exit_code == 0
        assert "JSON" in result.output


class TestReferenceCreate:
    def test_create_help(self, runner):
        result = runner.invoke(main, ["reference", "create", "--help"])
        assert result.exit_code == 0


class TestWebCommand:
    def test_web_help(self, runner):
        result = runner.invoke(main, ["web", "--help"])
        assert result.exit_code == 0
        assert "--port" in result.output
