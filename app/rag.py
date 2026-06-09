"""Retrieval-Augmented Generation utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Iterable

from .config import AssistantConfig
from .embeddings import HashingEmbeddingModel, cosine_similarity
from .ocr import OCRDocument, extract_documents


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    """Single knowledge-base document."""

    id: str
    title: str
    text: str
    tags: list[str] = field(default_factory=list)
    source_path: str | None = None
    source_type: str = "manual"

    def as_search_text(self) -> str:
        return " ".join([self.title, self.text, " ".join(self.tags)]).strip()

    def to_record(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "tags": self.tags,
            "source_path": self.source_path,
            "source_type": self.source_type,
        }

    @classmethod
    def from_record(cls, record: dict) -> "KnowledgeDocument":
        return cls(
            id=record["id"],
            title=record["title"],
            text=record["text"],
            tags=list(record.get("tags", [])),
            source_path=record.get("source_path"),
            source_type=record.get("source_type", "manual"),
        )


@dataclass(frozen=True, slots=True)
class RetrievedDocument:
    document: KnowledgeDocument
    score: float


class KnowledgeBase:
    """Vector-search index over healthcare knowledge snippets."""

    def __init__(
        self,
        documents: Iterable[KnowledgeDocument] | None = None,
        config: AssistantConfig | None = None,
        embedder: HashingEmbeddingModel | None = None,
    ) -> None:
        self.config = config or AssistantConfig()
        self.embedder = embedder or HashingEmbeddingModel(self.config.embedding_dimension)
        self.documents = list(documents) if documents is not None else self._load_documents()
        self._vectors = self.embedder.encode([document.as_search_text() for document in self.documents])
        self._persist_index()

    def _load_documents(self) -> list[KnowledgeDocument]:
        path = self.config.knowledge_base_path
        if not path.exists():
            return []

        raw = json.loads(path.read_text(encoding="utf-8"))
        records = raw.get("documents", raw) if isinstance(raw, dict) else raw
        return [KnowledgeDocument.from_record(item) for item in records]

    def _document_key(self, document: KnowledgeDocument) -> tuple[str, str | None, str]:
        return (document.id, document.source_path, document.source_type)

    def ingest_documents(self, new_documents: Iterable[KnowledgeDocument]) -> list[KnowledgeDocument]:
        merged = {self._document_key(document): document for document in self.documents}
        ingested: list[KnowledgeDocument] = []

        for document in new_documents:
            merged[self._document_key(document)] = document
            ingested.append(document)

        self.documents = list(merged.values())
        self._vectors = self.embedder.encode([document.as_search_text() for document in self.documents])
        self._persist_index()
        self._persist_documents()
        return ingested

    def ingest_paths(self, paths: Iterable[Path]) -> list[KnowledgeDocument]:
        extracted = extract_documents(paths)
        documents = [self._from_ocr_document(item) for item in extracted]
        return self.ingest_documents(documents)

    def _from_ocr_document(self, document: OCRDocument) -> KnowledgeDocument:
        suffix = Path(document.source_path).suffix.lower().lstrip(".")
        return KnowledgeDocument(
            id=document.id,
            title=document.title,
            text=document.text,
            tags=list(document.tags),
            source_path=document.source_path,
            source_type=suffix or "ocr",
        )

    def _persist_index(self) -> None:
        self.config.vector_store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "embedding_dimension": self.embedder.dimension,
            "documents": [
                {
                    "id": document.id,
                    "title": document.title,
                    "text": document.text,
                    "tags": document.tags,
                    "source_path": document.source_path,
                    "source_type": document.source_type,
                    "vector": vector,
                }
                for document, vector in zip(self.documents, self._vectors)
            ],
        }
        self.config.vector_store_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _persist_documents(self) -> None:
        self.config.knowledge_base_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "documents": [document.to_record() for document in self.documents],
        }
        self.config.knowledge_base_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def search(self, query: str, top_k: int | None = None) -> list[RetrievedDocument]:
        if not query.strip():
            return []

        query_vector = self.embedder.encode([query])[0]
        scored_documents = [
            RetrievedDocument(document=document, score=cosine_similarity(query_vector, vector))
            for document, vector in zip(self.documents, self._vectors)
        ]
        scored_documents.sort(key=lambda item: item.score, reverse=True)

        limit = top_k or self.config.top_k
        return [item for item in scored_documents[:limit] if item.score >= self.config.min_score]

    def build_context(self, query: str, top_k: int | None = None) -> tuple[str, list[RetrievedDocument]]:
        matches = self.search(query, top_k=top_k)
        if not matches:
            if not self.documents:
                return (
                    "No documents are indexed yet. Upload PDFs, images, or text files through the API to start retrieval.",
                    [],
                )
            return ("No relevant knowledge-base passages were retrieved.", [])

        lines = ["Retrieved context:"]
        for index, match in enumerate(matches, start=1):
            lines.append(
                f"{index}. {match.document.title} (score={match.score:.2f})\n{match.document.text}"
            )
        return ("\n\n".join(lines), matches)
