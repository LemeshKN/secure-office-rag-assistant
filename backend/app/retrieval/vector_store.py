import math
from dataclasses import dataclass
from typing import Any

from app.config import Settings, get_settings


@dataclass(frozen=True)
class VectorRecord:
    chroma_id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class VectorSearchResult:
    chroma_id: str
    text: str
    score: float
    metadata: dict[str, Any]


_MEMORY_COLLECTIONS: dict[str, list[VectorRecord]] = {}


class InMemoryVectorStore:
    """Small fallback used by tests and by local runs without Chroma installed."""

    def __init__(self, collection_name: str = "enterprise_rag_chunks") -> None:
        self.collection_name = collection_name
        _MEMORY_COLLECTIONS.setdefault(collection_name, [])

    @property
    def records(self) -> list[VectorRecord]:
        return _MEMORY_COLLECTIONS[self.collection_name]

    def upsert(self, records: list[VectorRecord]) -> None:
        by_id = {record.chroma_id: record for record in self.records}
        for record in records:
            by_id[record.chroma_id] = record
        _MEMORY_COLLECTIONS[self.collection_name] = list(by_id.values())

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[VectorSearchResult]:
        matches = [record for record in self.records if _matches_where(record.metadata, where)]
        scored = [
            VectorSearchResult(
                chroma_id=record.chroma_id,
                text=record.text,
                score=max(0.0, _cosine_similarity(query_embedding, record.embedding)),
                metadata=record.metadata,
            )
            for record in matches
        ]
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]

    def reset(self) -> None:
        _MEMORY_COLLECTIONS[self.collection_name] = []


class ChromaVectorStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._fallback: InMemoryVectorStore | None = None
        try:
            import chromadb

            self.client = chromadb.PersistentClient(path=str(self.settings.chroma_path))
            self.collection = self.client.get_or_create_collection(self.settings.chroma_collection)
        except Exception:
            self._fallback = InMemoryVectorStore(self.settings.chroma_collection)

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        if self._fallback is not None:
            self._fallback.upsert(records)
            return
        self.collection.upsert(
            ids=[record.chroma_id for record in records],
            documents=[record.text for record in records],
            embeddings=[record.embedding for record in records],
            metadatas=[record.metadata for record in records],
        )

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[VectorSearchResult]:
        if self._fallback is not None:
            return self._fallback.query(query_embedding, top_k, where)

        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        result = self.collection.query(**kwargs)
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        output: list[VectorSearchResult] = []
        for index, chroma_id in enumerate(ids):
            distance = distances[index] if index < len(distances) else 1.0
            output.append(
                VectorSearchResult(
                    chroma_id=chroma_id,
                    text=documents[index] if index < len(documents) else "",
                    score=1.0 / (1.0 + max(distance, 0.0)),
                    metadata=metadatas[index] if index < len(metadatas) else {},
                )
            )
        return output


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    length = min(len(left), len(right))
    numerator = sum(left[index] * right[index] for index in range(length))
    left_norm = math.sqrt(sum(value * value for value in left)) or 1.0
    right_norm = math.sqrt(sum(value * value for value in right)) or 1.0
    return numerator / (left_norm * right_norm)


def _matches_where(metadata: dict, where: dict | None) -> bool:
    if not where:
        return True
    if "$or" in where:
        return any(_matches_where(metadata, condition) for condition in where["$or"])
    if "$and" in where:
        return all(_matches_where(metadata, condition) for condition in where["$and"])
    for key, expected in where.items():
        if metadata.get(key) != expected:
            return False
    return True

