"""Flask web UI for blindspot."""

from __future__ import annotations

from flask import Flask, render_template, request

from blindspot.extractor import extract_concepts, _load_model
from blindspot.analyzer import analyze
from blindspot.reference import list_references, load_reference
from blindspot.reporter import format_html_report, build_pyvis_html


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, template_folder="templates")

    @app.route("/", methods=["GET"])
    def index() -> str:
        refs = list_references()
        return render_template("index.html", references=refs)

    @app.route("/analyze", methods=["POST"])
    def analyze_route() -> str:
        text = request.form.get("text", "").strip()
        topic = request.form.get("topic", "").strip()
        threshold = float(request.form.get("threshold", "0.75"))

        if not text or not topic:
            refs = list_references()
            return render_template(
                "index.html",
                references=refs,
                error="Please provide both text and a topic.",
            )

        try:
            ref_graph = load_reference(topic)
        except Exception as e:
            refs = list_references()
            return render_template(
                "index.html",
                references=refs,
                error=str(e),
            )

        nlp = _load_model()
        user_graph = extract_concepts(text, nlp=nlp)
        result = analyze(
            user_graph, ref_graph, nlp=nlp,
            similarity_threshold=threshold,
        )

        report_html = format_html_report(result, topic)
        graph_html = build_pyvis_html(
            user_graph, ref_graph, result.matched_concepts, topic,
        )

        return render_template(
            "results.html",
            topic=topic,
            report_html=report_html,
            graph_html=graph_html,
            coverage=result.coverage,
        )

    return app
