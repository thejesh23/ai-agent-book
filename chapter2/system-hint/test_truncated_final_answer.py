"""Regression: a text reply cut off by max_tokens (finish_reason="length")
must not be accepted as the final answer."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from agent import SystemHintAgent, SystemHintConfig


def make_agent():
    config = SystemHintConfig(
        enable_timestamps=False,
        enable_tool_counter=False,
        enable_todo_list=False,
        enable_detailed_errors=False,
        enable_system_state=False,
        save_trajectory=False,
    )
    return SystemHintAgent(api_key="test-key", provider="kimi", config=config, verbose=False)


def reply(content, finish_reason):
    message = SimpleNamespace(
        content=content,
        tool_calls=None,
        model_dump=lambda: {"role": "assistant", "content": content},
    )
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish_reason)])


def test_truncated_reply_is_continued_not_returned():
    agent = make_agent()
    agent.client = MagicMock()
    agent.client.chat.completions.create = MagicMock(
        side_effect=[
            reply("Step 1: I will first create the director", "length"),
            reply("FINAL ANSWER: done", "stop"),
        ]
    )

    result = agent.execute_task("make a plan", max_iterations=5)

    assert result["final_answer"] == "done"
    assert result["iterations"] == 2


def test_only_truncated_replies_do_not_succeed():
    agent = make_agent()
    agent.client = MagicMock()
    agent.client.chat.completions.create = MagicMock(
        side_effect=[reply("Step 1: I will", "length"), reply("Step 1: I will", "length")]
    )

    result = agent.execute_task("make a plan", max_iterations=2)

    assert result["success"] is False
    assert result["final_answer"] is None
