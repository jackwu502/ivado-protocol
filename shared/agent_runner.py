"""Reusable Claude + MCP agentic loop.

Used by:
  - The A2A analyst agent in Demo 2.
  - The equity/macro analyst entities in Demo 3.

Both wrap this same loop and only differ in how they receive a question and
deliver the answer (HTTP/JSON-RPC for A2A, FA messages for FA).
"""

from __future__ import annotations

import os
import sys
from contextlib import AsyncExitStack
from typing import Any, Awaitable, Callable

from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _params(server_path: str) -> StdioServerParameters:
    return StdioServerParameters(command=sys.executable, args=[server_path])


async def run_agent(
    question: str,
    mcp_servers: list[str],
    *,
    system_prompt: str | None = None,
    extra_tools: list[dict[str, Any]] | None = None,
    extra_tool_executor: Callable[[str, dict[str, Any]], Awaitable[Any]] | None = None,
    model: str | None = None,
    max_rounds: int = 8,
) -> str:
    """Run an agentic Claude loop and return the final text answer.

    `extra_tools` and `extra_tool_executor` let the caller plug in tools that
    are not MCP-backed (e.g., a "delegate to another agent" tool used by the
    FA equity analyst to call the macro analyst).
    """
    client = Anthropic()
    model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    async with AsyncExitStack() as stack:
        sessions: list[tuple[str, ClientSession]] = []
        for path in mcp_servers:
            read, write = await stack.enter_async_context(stdio_client(_params(path)))
            sess = await stack.enter_async_context(ClientSession(read, write))
            await sess.initialize()
            sessions.append((path, sess))

        # Build combined tool list and routing table
        tool_to_session: dict[str, ClientSession] = {}
        tools_for_claude: list[dict[str, Any]] = []
        for _, sess in sessions:
            resp = await sess.list_tools()
            for t in resp.tools:
                tool_to_session[t.name] = sess
                tools_for_claude.append({
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema,
                })
        for t in extra_tools or []:
            tools_for_claude.append(t)

        messages: list[dict[str, Any]] = [{"role": "user", "content": question}]

        for _ in range(max_rounds):
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": 2048,
                "tools": tools_for_claude,
                "messages": messages,
            }
            if system_prompt:
                kwargs["system"] = system_prompt
            resp = client.messages.create(**kwargs)

            if resp.stop_reason != "tool_use":
                return "".join(b.text for b in resp.content if b.type == "text").strip()

            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue

                if block.name in tool_to_session:
                    out = await tool_to_session[block.name].call_tool(block.name, block.input)
                    parts = []
                    for c in out.content:
                        if getattr(c, "type", None) == "text":
                            parts.append({"type": "text", "text": c.text})
                        elif getattr(c, "type", None) == "image":
                            parts.append({
                                "type": "image",
                                "source": {"type": "base64", "media_type": c.mimeType, "data": c.data},
                            })
                    content = parts or "ok"
                elif extra_tool_executor is not None:
                    result = await extra_tool_executor(block.name, dict(block.input))
                    content = str(result)
                else:
                    content = f"(no executor for tool {block.name!r})"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                })

            messages.append({"role": "user", "content": tool_results})

        return "(stopped: hit max_rounds without final answer)"
