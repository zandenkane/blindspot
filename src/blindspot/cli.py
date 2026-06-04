"""CLI interface for blindspot. Uses click for subcommands."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from blindspot.extractor import extract_concepts, _load_model
from blindspot.analyzer import analyze
from blindspot.reference import list_references, load_reference, save_reference, validate_reference
from blindspot.reporter import format_cli_report


@click.group()
@click.version_option(package_name="blindspot")
def main() -> None:
    """blindspot: find the gaps in what you know."""


@main.command("analyze")
@click.argument("topic")
@click.option(
    "--input", "-i", "input_path",
    type=click.Path(exists=True),
    help="Path to a text file. Reads from stdin if omitted.",
)
@click.option(
    "--threshold", "-t",
    type=float,
    default=0.75,
    show_default=True,
    help="Similarity threshold for fuzzy concept matching (0-1).",
)
def analyze_cmd(topic: str, input_path: str | None, threshold: float) -> None:
    """Analyze your knowledge of TOPIC.

    Write what you know about the topic in a text file or pipe it via stdin.
    blindspot will compare your concepts against the reference graph and report gaps.
    """
    # Read input text
    if input_path:
        text = Path(input_path).read_text(encoding="utf-8")
    else:
        if sys.stdin.isatty():
            click.echo("Paste your text below (Ctrl+D / Ctrl+Z to finish):")
        text = sys.stdin.read()

    if not text.strip():
        click.echo("Error: empty input. Write what you know about the topic.", err=True)
        raise SystemExit(1)

    # Load model and reference
    click.echo("Loading NLP model...")
    nlp = _load_model()

    click.echo(f"Loading reference graph for '{topic}'...")
    try:
        ref_graph = load_reference(topic)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    # Extract concepts from user text
    click.echo("Extracting concepts from your text...")
    user_graph = extract_concepts(text, nlp=nlp)

    # Run analysis
    click.echo("Analyzing gaps...")
    result = analyze(user_graph, ref_graph, nlp=nlp, similarity_threshold=threshold)

    # Print report
    click.echo()
    click.echo(format_cli_report(result, topic))


@main.command("export")
@click.argument("topic")
@click.option(
    "--input", "-i", "input_path",
    type=click.Path(exists=True),
    help="Path to a text file. Reads from stdin if omitted.",
)
@click.option(
    "--output", "-o", "output_path",
    type=click.Path(),
    help="Path for the JSON output file. Writes to stdout if omitted.",
)
@click.option(
    "--threshold", "-t",
    type=float,
    default=0.75,
    show_default=True,
    help="Similarity threshold for fuzzy concept matching (0 to 1).",
)
def export_cmd(topic: str, input_path: str | None, output_path: str | None, threshold: float) -> None:
    """Export analysis results as JSON.

    Same analysis as 'analyze' but outputs structured JSON instead of a
    formatted report. Useful for piping into other tools or dashboards.
    if input_path:
        text = Path(input_path).read_text(encoding="utf-8")
    else:
        if sys.stdin.isatty():
            click.echo("Paste your text below (Ctrl+D / Ctrl+Z to finish):", err=True)
        text = sys.stdin.read()

    if not text.strip():
        click.echo("Error: empty input.", err=True)
        raise SystemExit(1)

    nlp = _load_model()

    try:
        ref_graph = load_reference(topic)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    user_graph = extract_concepts(text, nlp=nlp)
    result = analyze(user_graph, ref_graph, nlp=nlp, similarity_threshold=threshold)

    payload = result.to_dict()
    payload["topic"] = topic

    json_str = json.dumps(payload, indent=2)

    if output_path:
        Path(output_path).write_text(json_str, encoding="utf-8")
        click.echo(f"Results written to {output_path}", err=True)
    else:
        click.echo(json_str)


@main.group()
def reference() -> None:
    """Manage reference concept graphs."""


@reference.command("list")
def reference_list() -> None:
    refs = list_references()
    if not refs:
        click.echo("No reference graphs found.")
        return
    click.echo("Available reference graphs:")
    for name in refs:
        click.echo(f"  - {name}")


@reference.command("validate")
@click.argument("name")
def reference_validate(name: str) -> None:
    """Validate a reference graph for structural issues.

    Checks for orphaned nodes, missing edge targets, duplicate IDs,
    and cycles that would prevent topological sorting.
    """
    try:
        issues = validate_reference(name)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    if not issues:
        click.echo(f"Reference '{name}' is valid. No issues found.")
    else:
        click.echo(f"Reference '{name}' has {len(issues)} issue(s):")
        for issue in issues:
            click.echo(f"  ! {issue}")
        raise SystemExit(1)


@reference.command("info")
@click.argument("name")
def reference_info(name: str) -> None:
    """Show summary statistics for a reference graph.

    Displays node count, edge count, tier breakdown, and connectivity info.
    try:
        graph = load_reference(name)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)

    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()

    tiers: dict[int, int] = {}
    for _, data in graph.nodes(data=True):
        t = data.get("tier", 0)
        tiers[t] = tiers.get(t, 0) + 1

    click.echo(f"Reference: {name}")
    click.echo(f"  Nodes: {node_count}")
    click.echo(f"  Edges: {edge_count}")
    click.echo("  Tiers:")
    for tier_num in sorted(tiers):
        label = {1: "foundational", 2: "intermediate", 3: "advanced"}.get(tier_num, f"tier {tier_num}")
        click.echo(f"    {tier_num} ({label}): {tiers[tier_num]}")

    # Find root nodes (no incoming edges)
    roots = [n for n in graph.nodes() if graph.in_degree(n) == 0]
    if roots:
        click.echo(f"  Root concepts: {', '.join(sorted(roots))}")

    # Find leaf nodes (no outgoing edges)
    leaves = [n for n in graph.nodes() if graph.out_degree(n) == 0]
    if leaves:
        click.echo(f"  Leaf concepts: {', '.join(sorted(leaves))}")


@reference.command("create")
@click.argument("name")
def reference_create(name: str) -> None:
    """Create a new reference graph interactively.

    Prompts for concepts and relationships, then writes a JSON file.
    """
    click.echo(f"Creating reference graph: {name}")
    click.echo("Enter concepts one per line (empty line to finish):")

    nodes: list[dict] = []
    tier = 1
    while True:
        concept = click.prompt("  Concept", default="", show_default=False)
        if not concept:
            break
        t = click.prompt("    Tier (1=foundational, 2=intermediate, 3=advanced)", type=int, default=tier)
        nodes.append({"id": concept.lower().strip(), "tier": t})

    if not nodes:
        click.echo("No concepts entered. Aborting.")
        return

    click.echo("\nEnter relationships (empty 'from' to finish):")
    edges: list[dict] = []
    while True:
        src = click.prompt("  From concept", default="", show_default=False)
        if not src:
            break
        dst = click.prompt("  To concept", default="", show_default=False)
        if not dst:
            break
        rel = click.prompt("  Relation", default="prerequisite")
        edges.append({
            "from": src.lower().strip(),
            "to": dst.lower().strip(),
            "relation": rel,
        })

    filepath = save_reference(name, nodes, edges)
    click.echo(f"\nReference graph saved to {filepath}")


@main.command("web")
@click.option("--port", "-p", type=int, default=5000, show_default=True)
@click.option("--debug", is_flag=True, default=False)
def web_cmd(port: int, debug: bool) -> None:
    from blindspot.web import create_app

    app = create_app()
    click.echo(f"Starting blindspot web UI on http://localhost:{port}")
    app.run(port=port, debug=debug)


if __name__ == "__main__":
    main()
