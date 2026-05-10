import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest


class TestQueryEndpoint:
    def test_returns_200_with_valid_query(self, client):
        response = client.post("/api/query", json={"query": "What is Python?"})
        assert response.status_code == 200

    def test_response_has_required_fields(self, client):
        body = client.post("/api/query", json={"query": "What is Python?"}).json()
        assert "answer" in body
        assert "sources" in body
        assert "session_id" in body

    def test_creates_session_when_none_provided(self, client, mock_rag):
        client.post("/api/query", json={"query": "Hello"})
        mock_rag.session_manager.create_session.assert_called_once()

    def test_uses_provided_session_id(self, client, mock_rag):
        client.post("/api/query", json={"query": "Hello", "session_id": "my-session"})
        mock_rag.query.assert_called_once_with("Hello", "my-session")

    def test_session_id_echoed_in_response(self, client):
        body = client.post(
            "/api/query", json={"query": "q", "session_id": "abc-123"}
        ).json()
        assert body["session_id"] == "abc-123"

    def test_auto_session_id_in_response(self, client):
        body = client.post("/api/query", json={"query": "q"}).json()
        assert body["session_id"] == "test-session-id"

    def test_answer_matches_rag_response(self, client, mock_rag):
        mock_rag.query.return_value = ("Custom answer.", [])
        body = client.post("/api/query", json={"query": "anything"}).json()
        assert body["answer"] == "Custom answer."

    def test_sources_propagated_to_response(self, client, mock_rag):
        mock_rag.query.return_value = (
            "Answer",
            [{"label": "Python 101 - Lesson 1", "url": "https://example.com"}],
        )
        body = client.post("/api/query", json={"query": "q"}).json()
        assert body["sources"][0]["label"] == "Python 101 - Lesson 1"
        assert body["sources"][0]["url"] == "https://example.com"

    def test_empty_sources_list_is_valid(self, client, mock_rag):
        mock_rag.query.return_value = ("Answer with no sources.", [])
        body = client.post("/api/query", json={"query": "q"}).json()
        assert body["sources"] == []

    def test_returns_500_when_rag_raises(self, client, mock_rag):
        mock_rag.query.side_effect = RuntimeError("DB offline")
        response = client.post("/api/query", json={"query": "q"})
        assert response.status_code == 500

    def test_error_detail_present_in_500(self, client, mock_rag):
        mock_rag.query.side_effect = RuntimeError("DB offline")
        body = client.post("/api/query", json={"query": "q"}).json()
        assert "DB offline" in body["detail"]

    def test_returns_422_when_query_missing(self, client):
        response = client.post("/api/query", json={})
        assert response.status_code == 422

    def test_query_passed_to_rag(self, client, mock_rag):
        client.post("/api/query", json={"query": "What is ML?"})
        called_query = mock_rag.query.call_args[0][0]
        assert called_query == "What is ML?"


class TestCoursesEndpoint:
    def test_returns_200(self, client):
        response = client.get("/api/courses")
        assert response.status_code == 200

    def test_response_has_required_fields(self, client):
        body = client.get("/api/courses").json()
        assert "total_courses" in body
        assert "course_titles" in body

    def test_course_count_matches_analytics(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 3,
            "course_titles": ["A", "B", "C"],
        }
        body = client.get("/api/courses").json()
        assert body["total_courses"] == 3
        assert body["course_titles"] == ["A", "B", "C"]

    def test_course_titles_list(self, client):
        body = client.get("/api/courses").json()
        assert isinstance(body["course_titles"], list)

    def test_empty_catalog_returns_zero(self, client, mock_rag):
        mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }
        body = client.get("/api/courses").json()
        assert body["total_courses"] == 0
        assert body["course_titles"] == []

    def test_returns_500_when_analytics_raises(self, client, mock_rag):
        mock_rag.get_course_analytics.side_effect = RuntimeError("Store unavailable")
        response = client.get("/api/courses")
        assert response.status_code == 500

    def test_error_detail_present_in_500(self, client, mock_rag):
        mock_rag.get_course_analytics.side_effect = RuntimeError("Store unavailable")
        body = client.get("/api/courses").json()
        assert "Store unavailable" in body["detail"]

    def test_analytics_called_once_per_request(self, client, mock_rag):
        client.get("/api/courses")
        mock_rag.get_course_analytics.assert_called_once()
