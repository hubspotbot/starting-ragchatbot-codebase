import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to a comprehensive search tool for course information.

Search Tool Usage:
- Use the search tool **only** for questions about specific course content or detailed educational materials
- **Course outline/syllabus questions**: Use the get_course_outline tool; always include the course title, course link, and the complete numbered lesson list (lesson number + lesson title) in your response
- **You may perform up to two sequential searches per query.** Only perform a second search when the first result reveals a gap — for example, when you need a lesson title from one course to then search for matching content in another. Do not search twice for the same thing.
- Synthesize search results into accurate, fact-based responses
- If search yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Search first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }

    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Delegate to tool loop when tools are available
        if tools and tool_manager:
            return self._run_tool_loop(
                messages=[{"role": "user", "content": query}],
                system_content=system_content,
                tools=tools,
                tool_manager=tool_manager,
            )

        # No-tools fast path: single API call
        response = self.client.messages.create(
            **self.base_params,
            messages=[{"role": "user", "content": query}],
            system=system_content,
        )
        return response.content[0].text

    def _run_tool_loop(
        self,
        messages: List[Dict],
        system_content: str,
        tools: List,
        tool_manager,
        max_rounds: int = 2,
    ) -> str:
        """
        Run up to max_rounds of tool-calling, accumulating conversation context.

        Terminates early when:
          (a) Claude returns end_turn (answer already in the response — return immediately)
          (b) A tool execution raises an exception (break, then issue final synthesis call)
        Terminates normally when max_rounds are exhausted (issue final synthesis call).
        """
        for _ in range(max_rounds):
            response = self.client.messages.create(
                **self.base_params,
                messages=messages,
                system=system_content,
                tools=tools,
                tool_choice={"type": "auto"},
            )

            # Claude finished naturally — its current response is the answer
            if response.stop_reason != "tool_use":
                return response.content[0].text

            # Append Claude's assistant turn (includes tool_use blocks)
            messages.append({"role": "assistant", "content": response.content})

            # Execute all tool calls in this round
            tool_results = []
            tool_error = False
            for block in response.content:
                if block.type == "tool_use":
                    try:
                        # Tool returning an error string is valid — pass it through to Claude
                        result = tool_manager.execute_tool(block.name, **block.input)
                    except Exception as e:
                        result = f"Error: {e}"
                        tool_error = True
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})

            if tool_error:
                break  # Don't attempt another round after an exception

        # Tool results are pending in messages — ask Claude to synthesize without tools
        final_response = self.client.messages.create(
            **self.base_params,
            messages=messages,
            system=system_content,
        )
        return final_response.content[0].text
