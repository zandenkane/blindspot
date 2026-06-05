"""Extract concepts and relationships from plain text using spaCy NLP."""

from __future__ import annotations

import spacy
import networkx as nx
from spacy.tokens import Doc


def _load_model() -> spacy.language.Language:
    try:
        return spacy.load("en_core_web_md")
    except OSError:
        raise RuntimeError(
            "spaCy model 'en_core_web_md' is not installed. "
            "Run: python -m spacy download en_core_web_md"
        )


def _normalize(text: str) -> str:
    return text.lower().strip()


def _extract_noun_chunks(doc: Doc) -> list[str]:
    seen: set[str] = set()
    chunks: list[str] = []
    for chunk in doc.noun_chunks:
        # Remove determiners and leading stopwords
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
            # Find direct objects of the same verb
            for child in token.head.children:
                if child.dep_ in ("dobj", "attr", "prep"):
                    if child.dep_ == "prep":
                        # Follow preposition to its object
                        for pobj in child.children:
                            if pobj.dep_ == "pobj":
                                obj = pobj.lemma_.lower()
                                triples.append((subject, verb, obj))
                    else:
                        obj = child.lemma_.lower()
                        triples.append((subject, verb, obj))
    return triples


def extract_concepts(text: str, nlp: spacy.language.Language | None = None) -> nx.DiGraph:
    """Parse text and build a concept graph. Nodes are normalized concepts extracted from noun chunks. Edges represent relationships found via dependency parsing (SVO triples). Args: text: Plain text describing what the user knows about a topic. nlp: Optional pre-loaded spaCy model. Loads en_core_web_md if not provided. Returns: A networkx DiGraph with concept nodes and relationship edges. if nlp is None: nlp = _load_model() doc = nlp(text) graph = nx.DiGraph() # Add noun chunks as nodes concepts = _extract_noun_chunks(doc) for concept in concepts: graph.add_node(concept, source="noun_chunk") # Add SVO triples as edges (and ensure nodes exist) triples = _extract_svo_triples(doc) for subj, verb, obj in triples: if subj != obj:  # Skip self-loops graph.add_node(subj, source="svo") graph.add_node(obj, source="svo") graph.add_edge(subj, obj, relation=verb) return graph"""