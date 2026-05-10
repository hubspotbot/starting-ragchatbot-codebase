import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import MagicMock
from search_tools import CourseSearchTool
from vector_store import SearchResults


def make_results(docs, metas):
    return SearchResults(documents=docs, metadata=metas, distances=[0.1] * len(docs))


def make_error(msg):
    return SearchResults(documents=[], metadata=[], distances=[], error=msg)


@pytest.fixture
def mock_store():
    store = MagicMock()
    store.get_lesson_link.return_value = None
    return store


@pytest.fixture
def tool(mock_store):
    return CourseSearchTool(mock_store)


class TestCourseSearchToolExecute:
    def test_returns_formatted_results(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            ["Lesson content about Python"],
            [{"course_title": "Python Course", "lesson_number": 1}],
        )
        result = tool.execute(query="What is Python?")
        assert "[Python Course - Lesson 1]" in result
        assert "Lesson content about Python" in result

    def test_returns_no_results_message_when_empty(self, tool, mock_store):
        mock_store.search.return_value = make_results([], [])
        result = tool.execute(query="something obscure")
        assert "No relevant content found" in result

    def test_no_results_message_includes_course_filter(self, tool, mock_store):
        mock_store.search.return_value = make_results([], [])
        result = tool.execute(query="topic", course_name="ML Course")
        assert "No relevant content found" in result
        assert "ML Course" in result

    def test_no_results_message_includes_lesson_filter(self, tool, mock_store):
        mock_store.search.return_value = make_results([], [])
        result = tool.execute(query="topic", lesson_number=3)
        assert "lesson 3" in result

    def test_returns_error_string_on_search_error(self, tool, mock_store):
        # This is the bug path: n_results=0 causes a Search error
        mock_store.search.return_value = make_error(
            "Search error: Number of requested results 0 is less than number of elements in index"
        )
        result = tool.execute(query="anything")
        assert "Search error" in result

    def test_populates_last_sources_after_search(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            ["content"],
            [{"course_title": "Test Course", "lesson_number": 2}],
        )
        mock_store.get_lesson_link.return_value = "https://example.com/lesson2"

        tool.execute(query="test")

        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["label"] == "Test Course - Lesson 2"
        assert tool.last_sources[0]["url"] == "https://example.com/lesson2"

    def test_last_sources_empty_on_no_results(self, tool, mock_store):
        mock_store.search.return_value = make_results([], [])
        tool.execute(query="nothing")
        assert tool.last_sources == []

    def test_passes_course_name_and_lesson_to_store(self, tool, mock_store):
        mock_store.search.return_value = make_results([], [])
        tool.execute(query="content", course_name="ML Course", lesson_number=3)
        mock_store.search.assert_called_once_with(
            query="content", course_name="ML Course", lesson_number=3
        )

    def test_formats_multiple_results(self, tool, mock_store):
        mock_store.search.return_value = make_results(
            ["Doc A", "Doc B"],
            [
                {"course_title": "Course 1", "lesson_number": 1},
                {"course_title": "Course 2", "lesson_number": 2},
            ],
        )
        result = tool.execute(query="query")
        assert "[Course 1 - Lesson 1]" in result
        assert "[Course 2 - Lesson 2]" in result
        assert "Doc A" in result
        assert "Doc B" in result
