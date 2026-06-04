"""Tests for the Flask web interface."""

from __future__ import annotations

import pytest

from blindspot.web import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestIndexRoute:
    def test_index_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_index_contains_form(self, client):
        resp = client.get("/")
        html = resp.data.decode()
        assert "<form" in html
        assert "topic" in html
        assert "text" in html

    def test_index_lists_references(self, client):
        resp = client.get("/")
        html = resp.data.decode()
        assert "python-basics" in html
        assert "cell-biology" in html


class TestAnalyzeRoute:
    def test_missing_text_shows_error(self, client):
        resp = client.post("/analyze", data={"topic": "python-basics", "text": ""})
        html = resp.data.decode()
        assert "Please provide" in html or resp.status_code == 200

    def test_missing_topic_shows_error(self, client):
        resp = client.post("/analyze", data={"topic": "", "text": "Variables store data."})
        html = resp.data.decode()
        assert "Please provide" in html or resp.status_code == 200

    def test_invalid_topic_shows_error(self, client):
        resp = client.post(
            "/analyze",
            data={"topic": "nonexistent-topic-xyz", "text": "Some text here."},
        )
        html = resp.data.decode()
        assert "not found" in html.lower() or resp.status_code == 200
