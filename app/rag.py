"""Real vector RAG: sentence-transformers embeddings + FAISS index.

The index is built offline by scripts/build_index.py and loaded read-only here.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from .config import settings
from .log import get_logger, log_with

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    doc_name: str
    text: str
    score: float  # cosine similarity, 0..1


class RAGIndex:
    def __init__(self, index_dir: str | None = None, embedding_model: str | None = None):
        self.index_dir = index_dir or settings.index_dir
        self.embedding_model_name = embedding_model or settings.embedding_model
        self._model: SentenceTransformer | None = None
        self._index: faiss.Index | None = None
        self._chunks: list[dict] = []

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            log_with(logger, 20, "loading embedding model", model=self.embedding_model_name)
            self._model = SentenceTransformer(self.embedding_model_name)
        return self._model

    def load(self) -> "RAGIndex":
        index_path = os.path.join(self.index_dir, "faiss.index")
        meta_path = os.path.join(self.index_dir, "chunks.json")
        if not (os.path.exists(index_path) and os.path.exists(meta_path)):
            raise FileNotFoundError(
                f"RAG index not found in {self.index_dir}. Run scripts/build_index.py first."
            )
        self._index = faiss.read_index(index_path)
        with open(meta_path, "r", encoding="utf-8") as f:
            self._chunks = json.load(f)
        log_with(logger, 20, "rag index loaded", chunks=len(self._chunks), dir=self.index_dir)
        return self

    def query(self, question: str, top_k: int | None = None) -> list[RetrievedChunk]:
        if self._index is None:
            raise RuntimeError("index not loaded, call load() first")
        k = top_k or settings.top_k
        vec = self.model.encode([question], normalize_embeddings=True).astype(np.float32)
        scores, ids = self._index.search(vec, k)
        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0:
                continue
            chunk = self._chunks[idx]
            results.append(
                RetrievedChunk(doc_name=chunk["doc_name"], text=chunk["text"], score=float(score))
            )
        log_with(
            logger, 20, "rag query",
            question=question[:80],
            top_score=results[0].score if results else 0.0,
            docs=[r.doc_name for r in results],
        )
        return results


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Simple character chunking with overlap; keeps code dependency-free."""
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks
