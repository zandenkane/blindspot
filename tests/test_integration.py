"""Integration test: prove blindspot finds real knowledge gaps without spaCy."""

from __future__ import annotations

from blindspot.extractor import extract_concepts
from blindspot.analyzer import analyze
from blindspot.reference import load_reference


class TestKnowledgeGapDetection:
    """End-to-end test using the python-basics reference graph.

    A student writes about variables, functions, loops, conditionals,
    data types, and operators -- but says nothing about decorators,
    generators, or closures.  Blindspot should correctly identify the
    covered material AND the gaps.
    """

    def test_finds_covered_and_missing_concepts(self):
        # --- arrange --------------------------------------------------------
        ref_graph = load_reference("python-basics")

        # Text deliberately covers basics but omits advanced concepts
        text = """
        Variables are used to store data in Python. You can assign integers,
        floats, strings, and booleans to variables. Python has several data
        types including lists, tuples, and dictionaries.

        Functions let you organize code into reusable blocks. Functions take
        parameters and return values. You can set default arguments for
        function parameters.

        Loops let you repeat code. For loops iterate over sequences. While
        loops run until a condition is false. You can use break to exit a
        loop and continue to skip iterations. List comprehensions provide a
        concise way to create lists from loops.

        Conditionals control program flow. If statements check conditions.
        You use elif for additional checks and else for the default case.
        Comparison operators and logical operators are used in conditions.

        Operators let you perform calculations and comparisons on variables.
        """

        # --- act ------------------------------------------------------------
        # Explicitly pass nlp=None to use the regex fallback (no spaCy needed)
        user_graph = extract_concepts(text, nlp=None)
        result = analyze(user_graph, ref_graph, nlp=None)

        # --- assert: covered concepts --------------------------------------
        covered = set(result.matched_concepts)

        for expected in ("variables", "functions", "loops"):
            assert expected in covered, (
                f"Expected '{expected}' to be identified as covered, "
                f"but it was not. Matched: {sorted(covered)}"
            )

        # --- assert: missing concepts (gaps) --------------------------------
        missing_concepts = {
            g.concept for g in result.gaps if g.gap_type == "missing_node"
        }

        for expected_gap in ("decorators", "generators", "closures"):
            assert expected_gap in missing_concepts, (
                f"Expected '{expected_gap}' to be flagged as a gap, "
                f"but it was not. Missing: {sorted(missing_concepts)}"
            )

        # --- assert: coverage percentage is roughly 50-70% ------------------
        assert 0.50 <= result.coverage <= 0.70, (
            f"Expected coverage between 50% and 70%, got {result.coverage:.1%}. "
            f"Matched {len(result.matched_concepts)}/{result.reference_node_count} concepts."
        )
