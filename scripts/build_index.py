"""Build the FAISS vector index from data/kb/*.md.

Usage: python scripts/build_index.py
Reads: MEMBER_ASSISTANT_KB_DIR, MEMBER_ASSISTANT_INDEX_DIR,
       MEMBER_ASSISTANT_EMBEDDING_MODEL, MEMBER_ASSISTANT_CHUNK_SIZE,
       MEMBER_ASSISTANT_CHUNK_OVERLAP
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.log import get_logger, log_with
from app.rag import chunk_text

logger = get_logger("build_index")


def main() -> None:
    kb_files = sorted(glob.glob(os.path.join(settings.kb_dir, "*.md")))
    if not kb_files:
        raise SystemExit(f"no markdown docs found in {settings.kb_dir}")

    texts, metas = [], []
    for path in kb_files:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        doc_name = os.path.splitext(os.path.basename(path))[0]
        for chunk in chunk_text(content, settings.chunk_size, settings.chunk_overlap):
            texts.append(chunk)
            metas.append({"doc_name": doc_name, "text": chunk})
    log_with(logger, 20, "chunked docs", docs=len(kb_files), chunks=len(texts))

    log_with(logger, 20, "loading embedding model", model=settings.embedding_model)
    model = SentenceTransformer(settings.embedding_model)
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
    embeddings = np.asarray(embeddings, dtype=np.float32)

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    os.makedirs(settings.index_dir, exist_ok=True)
    faiss.write_index(index, os.path.join(settings.index_dir, "faiss.index"))
    with open(os.path.join(settings.index_dir, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(metas, f, ensure_ascii=False, indent=2)
    log_with(logger, 20, "index written", dir=settings.index_dir, chunks=len(texts))


if __name__ == "__main__":
    main()
