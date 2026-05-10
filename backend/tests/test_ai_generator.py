import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import MagicMock, patch, call
from ai_generator import AIGenerator


def _text_block(text):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _tool_use_block(name, tool_id, inputs):
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.id = tool_id
    block.input = inputs
    return block


def _tool_use_response(name, tool_id, inputs):
    """Build a mock API response that requests a tool call."""
    response = MagicMock()
    response.stop_reason = "tool_use"
    response.content = [_tool_use_block(name, tool_id, inputs)]
    return response


def _text_response(text):
    """Build a mock API response with a plain text answer."""
    response = MagicMock()
    response.stop_reason = "end_turn"
    response.content = [_text_block(text)]
    return response


@pytest.fixture
def generator():
    with patch("anthropic.Anthropic"):
        gen = AIGenerator(api_key="test-key", model="claude-test")
    return gen


# ---------------------------------------------------------------------------
# Kept from original suite — direct text path and no-tool-manager path
# ---------------------------------------------------------------------------

class TestAIGeneratorDirectResponse:
    def test_returns_text_when_no_tool_use(self, generator):
        generator.client.messages.create.return_value = _text_response("Direct answer")
        result = generator.generate_response(query="What is 2+2?")
        assert result == "Direct answer"

    def test_no_tool_execution_when_tool_manager_absent(self, generator):
        generator.client.messages.create.return_value = _text_response("Fallback")
        result = generator.generate_response(
            query="search something",
            tools=[{"name": "search_course_content"}],
            tool_manager=None,
        )
        assert result == "Fallback"
        generator.client.messages.create.assert_called_once()


# ---------------------------------------------------------------------------
# New behavioral tests — all exercised via generate_response, not internals
# ---------------------------------------------------------------------------

class TestSingleRoundToolCalling:
    def test_single_round_returns_text(self, generator):
        """One tool call: 2 API calls total, execute_tool called once."""
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Search results for Python"

        generator.client.messages.create.side_effect = [
            _tool_use_response("search_course_content", "tu_1", {"query": "Python"}),
            _text_response("Python is a programming language."),
        ]

        result = generator.generate_response(
            query="What is Python?",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        assert result == "Python is a programming language."
        assert generator.client.messages.create.call_count == 2
        tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="Python"
        )

    def test_tool_result_structure_in_follow_up_call(self, generator):
        """The second API call receives a properly structured tool_result message."""
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "Found: Python basics"

        generator.client.messages.create.side_effect = [
            _tool_use_response("search_course_content", "tu_42", {"query": "Python"}),
            _text_response("Answer"),
        ]

        generator.generate_response(
            query="q",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        second_call_kwargs = generator.client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]
        user_with_tool_result = next(
            m for m in messages if m["role"] == "user" and isinstance(m["content"], list)
        )
        tr = user_with_tool_result["content"][0]
        assert tr["type"] == "tool_result"
        assert tr["tool_use_id"] == "tu_42"
        assert tr["content"] == "Found: Python basics"

    def test_single_round_no_extra_synthesis_call(self, generator):
        """When Claude returns end_turn inside the loop, no extra post-loop call is made."""
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "results"

        generator.client.messages.create.side_effect = [
            _tool_use_response("search_course_content", "tu_1", {"query": "q"}),
            _text_response("answer"),
        ]

        result = generator.generate_response(
            query="q",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        # Claude finished naturally in round 2 (still inside the loop) — exactly 2 calls, no extra
        assert generator.client.messages.create.call_count == 2
        assert result == "answer"
        # Both calls included tools (loop iterations always offer tools)
        for c in generator.client.messages.create.call_args_list:
            assert "tools" in c[1]


class TestTwoRoundToolCalling:
    def test_second_round_triggers_third_api_call(self, generator):
        """Two tool rounds produce 3 API calls; execute_tool is called twice."""
        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = ["Round 1 result", "Round 2 result"]

        generator.client.messages.create.side_effect = [
            _tool_use_response("search_course_content", "tu_1", {"query": "query 1"}),
            _tool_use_response("get_course_outline", "tu_2", {"course_title": "Course X"}),
            _text_response("Final synthesized answer."),
        ]

        result = generator.generate_response(
            query="Compare lesson 4 of course X with similar courses",
            tools=[{"name": "search_course_content"}, {"name": "get_course_outline"}],
            tool_manager=tool_manager,
        )

        assert result == "Final synthesized answer."
        assert generator.client.messages.create.call_count == 3
        assert tool_manager.execute_tool.call_count == 2

    def test_second_round_api_call_includes_tools(self, generator):
        """Both round-1 and round-2 API calls must include tools — this is the core fix."""
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "result"

        generator.client.messages.create.side_effect = [
            _tool_use_response("search_course_content", "tu_1", {"query": "q1"}),
            _tool_use_response("search_course_content", "tu_2", {"query": "q2"}),
            _text_response("Final answer"),
        ]

        generator.generate_response(
            query="q",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        calls = generator.client.messages.create.call_args_list
        assert "tools" in calls[0][1], "Round 1 call must include tools"
        assert "tools" in calls[1][1], "Round 2 call must include tools"

    def test_final_call_after_two_rounds_has_no_tools(self, generator):
        """The 3rd (synthesis) API call must not include tools."""
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "result"

        generator.client.messages.create.side_effect = [
            _tool_use_response("search_course_content", "tu_1", {"query": "q1"}),
            _tool_use_response("search_course_content", "tu_2", {"query": "q2"}),
            _text_response("Answer"),
        ]

        generator.generate_response(
            query="q",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        third_call_kwargs = generator.client.messages.create.call_args_list[2][1]
        assert "tools" not in third_call_kwargs
        assert "tool_choice" not in third_call_kwargs

    def test_full_message_history_in_final_call(self, generator):
        """The final call receives the complete 5-message history."""
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "result"

        r1 = _tool_use_response("search_course_content", "tu_1", {"query": "q1"})
        r2 = _tool_use_response("search_course_content", "tu_2", {"query": "q2"})

        generator.client.messages.create.side_effect = [r1, r2, _text_response("done")]

        generator.generate_response(
            query="original query",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        final_messages = generator.client.messages.create.call_args_list[2][1]["messages"]
        assert len(final_messages) == 5

        assert final_messages[0] == {"role": "user", "content": "original query"}
        assert final_messages[1]["role"] == "assistant"
        assert final_messages[1]["content"] == r1.content
        assert final_messages[2]["role"] == "user"
        assert final_messages[2]["content"][0]["type"] == "tool_result"
        assert final_messages[3]["role"] == "assistant"
        assert final_messages[3]["content"] == r2.content
        assert final_messages[4]["role"] == "user"
        assert final_messages[4]["content"][0]["type"] == "tool_result"

    def test_max_two_rounds_even_if_claude_keeps_requesting_tools(self, generator):
        """Claude requesting tools indefinitely must not produce more than 3 API calls."""
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "result"

        # All calls return tool_use — Claude would loop forever without the round cap
        generator.client.messages.create.side_effect = [
            _tool_use_response("search_course_content", "tu_1", {"query": "q1"}),
            _tool_use_response("search_course_content", "tu_2", {"query": "q2"}),
            _text_response("Forced final answer"),
        ]

        result = generator.generate_response(
            query="q",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        assert generator.client.messages.create.call_count == 3
        assert tool_manager.execute_tool.call_count == 2
        assert result == "Forced final answer"


class TestToolErrorHandling:
    def test_tool_exception_terminates_loop_gracefully(self, generator):
        """A Python exception from execute_tool stops the loop; Claude still synthesizes."""
        tool_manager = MagicMock()
        tool_manager.execute_tool.side_effect = RuntimeError("DB connection failed")

        generator.client.messages.create.side_effect = [
            _tool_use_response("search_course_content", "tu_1", {"query": "q"}),
            _text_response("Sorry, I couldn't complete the search."),
        ]

        result = generator.generate_response(
            query="q",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        assert generator.client.messages.create.call_count == 2
        assert result == "Sorry, I couldn't complete the search."

    def test_tool_error_string_is_not_treated_as_failure(self, generator):
        """An error *string* from execute_tool is a valid result — passed through to Claude."""
        tool_manager = MagicMock()
        tool_manager.execute_tool.return_value = "No course found matching 'X'"

        generator.client.messages.create.side_effect = [
            _tool_use_response("search_course_content", "tu_1", {"query": "X"}),
            _text_response("No matching course was found."),
        ]

        result = generator.generate_response(
            query="find course X",
            tools=[{"name": "search_course_content"}],
            tool_manager=tool_manager,
        )

        # Loop continued (2 calls), error string forwarded, no crash
        assert generator.client.messages.create.call_count == 2
        assert result == "No matching course was found."

        second_call_messages = generator.client.messages.create.call_args_list[1][1]["messages"]
        user_msg = next(
            m for m in second_call_messages
            if m["role"] == "user" and isinstance(m["content"], list)
        )
        assert user_msg["content"][0]["content"] == "No course found matching 'X'"
