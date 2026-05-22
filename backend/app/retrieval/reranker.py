from app.config import Settings, get_settings
from app.retrieval.hybrid_retriever import RetrievedChunk


class Reranker:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._model = None
        self._model_failed = False

    def rerank(self, question: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return []
        model = self._get_model()
        if model is None:
            return sorted(chunks, key=lambda chunk: chunk.combined_score, reverse=True)

        pairs = [(question, chunk.text) for chunk in chunks]
        try:
            scores = model.predict(pairs)
        except Exception:
            return sorted(chunks, key=lambda chunk: chunk.combined_score, reverse=True)

        for chunk, score in zip(chunks, scores):
            chunk.rerank_score = float(score)
        return sorted(chunks, key=lambda chunk: chunk.rerank_score, reverse=True)

    def _get_model(self):
        if not self.settings.enable_cross_encoder or self._model_failed:
            return None
        if self._model is not None:
            return self._model
        try:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            return self._model
        except Exception:
            self._model_failed = True
            return None

