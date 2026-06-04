# Changelog

## 0.1.0 (2026-05-28)

- Concept extraction from plain text using spaCy noun chunks and dependency parsing
- Gap analysis comparing user concepts against reference graphs with fuzzy matching
- Three bundled reference graphs: python-basics (40 concepts), cell-biology (30 concepts), linear-algebra (35 concepts)
- CLI with `analyze`, `export`, `reference list`, `reference create`, `reference validate`, `reference info`, and `web` subcommands
- JSON export for piping results into other tools
- Reference graph validation for catching structural issues (orphans, dangling edges, duplicates, cycles)
- Flask web UI with interactive pyvis graph visualization
- Severity scoring based on concept out-degree, tier, and foundation status
- Topological sort for suggested study order
