import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass


@dataclass
class _Config:
    ANTHROPIC_API_KEY: str = "test-key"
    ANTHROPIC_MODEL: str = "claude-test"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100
    MAX_RESULTS: int = 5
    MAX_HISTORY: int = 2
    CHROMA_PATH: str = "/tmp/test_chroma_rag"


def _make_rag(max_results=5):
    cfg = _Config(MAX_RESULTS=max_results)
    with patch("chromadb.PersistentClient"), patch(
        "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
    ), patch("anthropic.Anthropic"):
        from rag_system import RAGSystem
        return RAGSystem(cfg)


class TestConfigBug:
    def test_max_results_is_positive_in_production_config(self):
        """Regression guard: MAX_RESULTS must be > 0 or ChromaDB raises on every search."""
        from config import config
        assert config.MAX_RESULTS > 0, (
            "MAX_RESULTS must be a positive integer. "
            "Setting it to 0 causes ChromaDB to raise an exception (n_results=0) "
            "on every query, so all content searches silently fail."
        )


class TestVectorStoreWithZeroMaxResults:
    def test_search_returns_error_when_n_results_is_zero(self):
        """VectorStore.search() with max_results=0 propagates a Search error."""
        from vector_store import VectorStore

        mock_collection = MagicMock()
        mock_collection.query.side_effect = Exception(
            "Number of requested results 0 is less than number of elements in index"
        )

        with patch("chromadb.PersistentClient"), patch(
            "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
        ):
            store = VectorStore("/tmp/test_vs", "all-MiniLM-L6-v2", max_results=0)
            store.course_content = mock_collection
            store.course_catalog = MagicMock()

        result = store.search(query="test query")
        assert result.error is not None
        assert "Search error" in result.error

    def test_search_succeeds_with_positive_max_results(self):
        """VectorStore.search() with max_results=5 calls ChromaDB correctly."""
        from vector_store import VectorStore

        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["content about Python"]],
            "metadatas": [[{"course_title": "Python 101", "lesson_number": 1}]],
            "distances": [[0.1]],
        }

        with patch("chromadb.PersistentClient"), patch(
            "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
        ):
            store = VectorStore("/tmp/test_vs", "all-MiniLM-L6-v2", max_results=5)
            store.course_content = mock_collection
            store.course_catalog = MagicMock()

        result = store.search(query="test query")
        assert result.error is None
        assert len(result.documents) == 1
        mock_collection.query.assert_called_once_with(
            query_texts=["test query"], n_results=5, where=None
        )


class TestRAGSystemQuery:
    def test_query_returns_response_and_empty_sources_list(self):
        rag = _make_rag(max_results=5)
        rag.ai_generator.generate_response = MagicMock(return_value="A direct answer.")

        response, sources = rag.query("What is 2+2?")

        assert response == "A direct answer."
        assert isinstance(sources, list)

    def test_query_with_session_stores_history(self):
        rag = _make_rag(max_results=5)
        rag.ai_generator.generate_response = MagicMock(return_value="History answer.")

        session_id = rag.session_manager.create_session()
        rag.query("Hello", session_id=session_id)

        history = rag.session_manager.get_conversation_history(session_id)
        assert history is not None
        assert "Hello" in history

    def test_query_passes_tools_to_ai_generator(self):
        rag = _make_rag(max_results=5)
        rag.ai_generator.generate_response = MagicMock(return_value="answer")

        rag.query("What topics are in lesson 2?")

        call_kwargs = rag.ai_generator.generate_response.call_args[1]
        assert "tools" in call_kwargs
        tool_names = [t["name"] for t in call_kwargs["tools"]]
        assert "search_course_content" in tool_names

    def test_sources_reset_after_query(self):
        rag = _make_rag(max_results=5)
        rag.ai_generator.generate_response = MagicMock(return_value="answer")

        # Manually set a source to confirm reset happens
        rag.search_tool.last_sources = [{"label": "stale", "url": None}]

        rag.query("Any question")

        # After query, sources should be reset (reset_sources called in rag_system.query)
        assert rag.search_tool.last_sources == []

    def test_query_fails_gracefully_with_zero_max_results(self):
        """Reproduces the production bug: MAX_RESULTS=0 → search error → AI reports failure."""
        rag = _make_rag(max_results=0)

        # Simulate what actually happens in production: ChromaDB raises, VectorStore
        # returns a Search error string, CourseSearchTool returns it to Claude,
        # and Claude produces a failure response.
        from vector_store import SearchResults
        rag.search_tool.store.search = MagicMock(
            return_value=SearchResults(
                documents=[],
                metadata=[],
                distances=[],
                error="Search error: Number of requested results 0 is less than number of elements in index",
            )
        )
        rag.ai_generator.generate_response = MagicMock(
            return_value="I'm sorry, the query failed due to a search error."
        )

        response, _ = rag.query("What is covered in lesson 1?")

        assert "failed" in response.lower() or "error" in response.lower()
