"""Extract concepts and relationships from plain text.

Uses spaCy NLP when available for better extraction quality.
Falls back to simple regex/keyword matching when spaCy is not installed.
"""

from __future__ import annotations

import re

import networkx as nx

try:
    import spacy
    from spacy.tokens import Doc

    _SPACY_AVAILABLE = True
except ImportError:
    spacy = None  # type: ignore[assignment]
    Doc = None  # type: ignore[assignment,misc]
    _SPACY_AVAILABLE = False


def _load_model() -> object | None:
    """Load the spaCy model if available. Returns None when spaCy is missing."""
    if not _SPACY_AVAILABLE:
        return None
    try:
        return spacy.load("en_core_web_md")
    except OSError:
        return None


def _normalize(text: str) -> str:
    return text.lower().strip()


# ---------------------------------------------------------------------------
# spaCy-based extraction (used when nlp is not None)
# ---------------------------------------------------------------------------

def _extract_noun_chunks(doc: Doc) -> list[str]:
    seen: set[str] = set()
    chunks: list[str] = []
    for chunk in doc.noun_chunks:
        tokens = [t for t in chunk if not t.is_stop and not t.is_punct]
        if not tokens:
            continue
        lemmatized = " ".join(t.lemma_.lower() for t in tokens)
        if lemmatized and lemmatized not in seen:
            seen.add(lemmatized)
            chunks.append(lemmatized)
    return chunks


def _extract_svo_triples(doc: Doc) -> list[tuple[str, str, str]]:
    triples: list[tuple[str, str, str]] = []
    for token in doc:
        if token.dep_ in ("nsubj", "nsubjpass"):
            subject = token.lemma_.lower()
            verb = token.head.lemma_.lower()
            for child in token.head.children:
                if child.dep_ in ("dobj", "attr", "prep"):
                    if child.dep_ == "prep":
                        for pobj in child.children:
                            if pobj.dep_ == "pobj":
                                obj = pobj.lemma_.lower()
                                triples.append((subject, verb, obj))
                    else:
                        obj = child.lemma_.lower()
                        triples.append((subject, verb, obj))
    return triples


def _extract_with_spacy(text: str, nlp: object) -> nx.DiGraph:
    """Extract concepts using spaCy NLP pipeline."""
    doc = nlp(text)
    graph = nx.DiGraph()

    concepts = _extract_noun_chunks(doc)
    for concept in concepts:
        graph.add_node(concept, source="noun_chunk")

    triples = _extract_svo_triples(doc)
    for subj, verb, obj in triples:
        if subj != obj:
            graph.add_node(subj, source="svo")
            graph.add_node(obj, source="svo")
            graph.add_edge(subj, obj, relation=verb)

    return graph


# ---------------------------------------------------------------------------
# Regex/keyword fallback (used when spaCy is not available)
# ---------------------------------------------------------------------------

def _tokenize_simple(text: str) -> list[str]:
    """Split text into lowercase tokens, stripping punctuation."""
    text = text.lower()
    # Replace punctuation with spaces (keep hyphens inside words)
    cleaned = re.sub(r"[^\w\s-]", " ", text)
    # Collapse whitespace
    return cleaned.split()


def _extract_without_spacy(text: str) -> nx.DiGraph:
    """Extract concepts using simple unigram + bigram matching.

    This fallback does not use any NLP model. It tokenizes the text and
    builds unigrams and bigrams, which are later matched against the
    reference graph by exact string comparison in the analyzer.
    """
    graph = nx.DiGraph()
    tokens = _tokenize_simple(text)

    if not tokens:
        return graph

    seen: set[str] = set()

    # Add unigrams
    for token in tokens:
        if token and token not in seen:
            seen.add(token)
            graph.add_node(token, source="unigram")

    # Add bigrams
    for i in range(len(tokens) - 1):
        bigram = f"{tokens[i]} {tokens[i + 1]}"
        if bigram not in seen:
            seen.add(bigram)
            graph.add_node(bigram, source="bigram")

    return graph


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_concepts(text: str, nlp: object | None = None) -> nx.DiGraph:
    """Parse text and build a concept graph.

    When a spaCy model is provided via *nlp*, uses noun-chunk and SVO
    extraction for higher quality results.  When *nlp* is None, falls
    back to simple unigram/bigram tokenisation so the tool works without
    any NLP model installed.

    Args:
        text: Plain text describing what the user knows about a topic.
        nlp: Optional pre-loaded spaCy model. Falls back to regex if None.

    Returns:
        A networkx DiGraph with concept nodes and relationship edges.
    """
    if nlp is not None:
        return _extract_with_spacy(text, nlp)
    return _extract_without_spacy(text)
