"""Format analysis results for CLI output and web display."""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from blindspot.analyzer import AnalysisResult


def format_cli_report(result: AnalysisResult, topic: str) -> str:
    """Produce a plain-text report for terminal output.

    Args:
        result: The AnalysisResult from the analyzer.
        topic: Name of the reference topic.

    Returns:
        A formatted multi-line string.
    """
    lines: list[str] = []

    pct = result.coverage * 100
    lines.append(f"Knowledge Gap Report: {topic}")
    lines.append("=" * 50)
    lines.append(f"Coverage: {pct:.1f}% ({len(result.matched_concepts)}/{result.reference_node_count} concepts)")
    lines.append(f"Your text contained {result.user_node_count} identifiable concepts")
    lines.append("")

    # Matched concepts
    if result.matched_concepts:
        lines.append("Concepts you covered:")
        for c in sorted(result.matched_concepts):
            lines.append(f"  [+] {c}")
        lines.append("")

    # Gaps by type
    missing_nodes = [g for g in result.gaps if g.gap_type == "missing_node"]
    missing_edges = [g for g in result.gaps if g.gap_type == "missing_edge"]
    isolated = [g for g in result.gaps if g.gap_type == "isolated"]

    if missing_nodes:
        lines.append("Missing concepts (sorted by importance):")
        for g in missing_nodes:
            bar = "#" * int(g.severity * 10)
            lines.append(f"  [-] {g.concept} (severity: {g.severity:.2f} {bar})")
        lines.append("")

    if missing_edges:
        lines.append("Missing connections:")
        for g in missing_edges:
            lines.append(f"  [~] {g.concept}: {g.details}")
        lines.append("")

    if isolated:
        lines.append("Isolated concepts (mentioned but unconnected):")
        for g in isolated:
            lines.append(f"  [?] {g.concept}")
        lines.append("")

    if result.study_order:
        lines.append("Suggested study order:")
        for i, concept in enumerate(result.study_order, 1):
            lines.append(f"  {i}. {concept}")
        lines.append("")

    if not result.gaps:
        lines.append("No gaps found. You have strong coverage of this topic.")

    return "\n".join(lines)


def build_pyvis_html(
    user_graph: nx.DiGraph,
    ref_graph: nx.DiGraph,
    matched: list[str],
    topic: str,
) -> str:
    """Generate an interactive HTML graph using pyvis.

    Green nodes = concepts the user covered.
    Red nodes = missing concepts.
    Yellow nodes = partially matched (mentioned but isolated).

    Args:
        user_graph: The user's extracted concept graph.
        ref_graph: The reference concept graph.
        matched: List of concepts the user matched.
        topic: Topic name for the graph title.

    Returns:
        HTML string containing the interactive graph.
    """
    try:
        from pyvis.network import Network
    except ImportError:
        return (
            "<p>pyvis is not installed. "
            "Install it with: pip install pyvis</p>"
        )

    net = Network(
        height="600px",
        width="100%",
        directed=True,
        notebook=False,
        cdn_resources="remote",
    )

    matched_set = set(matched)
    user_nodes = set(user_graph.nodes())

    # Add all reference nodes with color coding
    for node in ref_graph.nodes():
        if node in matched_set:
            color = "#4CAF50"  # green
            title = f"{node}: covered"
        elif node in user_nodes:
            color = "#FFC107"  # yellow
            title = f"{node}: mentioned but not well connected"
        else:
            color = "#F44336"  # red
            title = f"{node}: missing from your description"

        label = node
        net.add_node(node, label=label, color=color, title=title)

    # Add reference edges
    for src, dst, data in ref_graph.edges(data=True):
        relation = data.get("relation", "related-to")
        net.add_edge(src, dst, title=relation, arrows="to")

    # Physics settings for readable layout
    net.set_options("""{
        "physics": {
            "forceAtlas2Based": {
                "gravitationalConstant": -50,
                "centralGravity": 0.01,
                "springLength": 100,
                "springConstant": 0.08
            },
            "solver": "forceAtlas2Based",
            "stabilization": {"iterations": 150}
        }
    }""")

    return net.generate_html()


def format_html_report(result: AnalysisResult, topic: str) -> str:
    """Produce an HTML report fragment (no full page, just content).

    Args:
        result: The AnalysisResult from the analyzer.
        topic: Name of the reference topic.

    Returns:
        HTML string with the report content.
    """
    pct = result.coverage * 100
    parts: list[str] = []

    parts.append(f"<h2>Knowledge Gap Report: {html.escape(topic)}</h2>")
    parts.append(f"<p><strong>Coverage:</strong> {pct:.1f}% "
                 f"({len(result.matched_concepts)}/{result.reference_node_count} concepts)</p>")
    parts.append(f"<p>Your text contained {result.user_node_count} identifiable concepts.</p>")

    if result.matched_concepts:
        parts.append("<h3>Concepts You Covered</h3><ul>")
        for c in sorted(result.matched_concepts):
            parts.append(f"<li style='color:#4CAF50'>{html.escape(c)}</li>")
        parts.append("</ul>")

    missing_nodes = [g for g in result.gaps if g.gap_type == "missing_node"]
    if missing_nodes:
        parts.append("<h3>Missing Concepts</h3><ul>")
        for g in missing_nodes:
            width = int(g.severity * 100)
            parts.append(
                f"<li>{html.escape(g.concept)} "
                f"<span style='display:inline-block;background:#F44336;"
                f"height:10px;width:{width}px'></span> "
                f"severity: {g.severity:.2f}</li>"
            )
        parts.append("</ul>")

    missing_edges = [g for g in result.gaps if g.gap_type == "missing_edge"]
    if missing_edges:
        parts.append("<h3>Missing Connections</h3><ul>")
        for g in missing_edges:
            parts.append(f"<li>{html.escape(g.concept)}: {html.escape(g.details)}</li>")
        parts.append("</ul>")

    if result.study_order:
        parts.append("<h3>Suggested Study Order</h3><ol>")
        for concept in result.study_order:
            parts.append(f"<li>{html.escape(concept)}</li>")
        parts.append("</ol>")

    if not result.gaps:
        parts.append("<p style='color:#4CAF50;font-weight:bold'>"
                     "No gaps found. You have strong coverage of this topic.</p>")

    return "\n".join(parts)
