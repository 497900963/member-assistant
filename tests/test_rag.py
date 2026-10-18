"""Tests for RAG retrieval (needs the built index)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.rag import RAGIndex, chunk_text  # noqa: E402


def test_chunk_overlap():
    chunks = chunk_text("0123456789", chunk_size=6, overlap=2)
    assert chunks[0] == "012345"
    assert chunks[1].startswith("45")


def test_query_returns_relevant_doc():
    rag = RAGIndex().load()
    results = rag.query("停车场收费标准是什么", top_k=2)
    assert results, "no results returned"
    assert results[0].doc_name == "parking"
    assert results[0].score > 0.3
