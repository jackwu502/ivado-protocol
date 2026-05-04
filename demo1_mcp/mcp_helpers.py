"""Beginner-friendly wrappers around the MCP client.

The notebook calls these like normal functions; all the async / protocol /
subprocess machinery stays hidden in here. Curious readers can open this file.
"""

import base64
import os
import sys
from contextlib import AsyncExitStack

from anthropic import Anthropic
from IPython.display import Image as IPImage, display
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load .env if present so notebooks can pick up ANTHROPIC_API_KEY,
# ANTHROPIC_BASE_URL, ANTHROPIC_MODEL without manual exports.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def _params(server_path: str) -> StdioServerParameters:
    # Use the same Python interpreter as the notebook so the server can find
    # the same packages (mcp, scipy, matplotlib) that were installed here.
    return StdioServerParameters(command=sys.executable, args=[server_path])


async def list_tools(server_path: str) -> None:
    """Print the tools that one MCP server provides."""
    async with stdio_client(_params(server_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            resp = await session.list_tools()
            print(f"[{server_path}]")
            for t in resp.tools:
                params = list(t.inputSchema.get("properties", {}).keys())
                first_line = t.description.strip().splitlines()[0] if t.description else ""
                print(f"  • {t.name}({', '.join(params)})")
                print(f"      {first_line}")


async def call_tool(server_path: str, tool_name: str, **arguments) -> None:
    """Call one tool by name. Prints text results; displays images inline."""
    async with stdio_client(_params(server_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            for c in result.content:
                if getattr(c, "type", None) == "text":
                    print(c.text)
                elif getattr(c, "type", None) == "image":
                    display(IPImage(data=base64.b64decode(c.data)))


async def chat_with_claude(
    message: str,
    servers: list[str],
    model: str | None = None,
    max_rounds: int = 10,
) -> None:
    """Let Claude answer `message`, with access to all tools from `servers`.

    Prints every step so you can see Claude pick tools and use the results.
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY not set — fill it into .env and restart the kernel.")
        return

    model = model or DEFAULT_MODEL
    base_url = os.getenv("ANTHROPIC_BASE_URL")
    print(f"(model={model}{', via OpenRouter' if base_url and 'openrouter' in base_url else ''})\n")

    async with AsyncExitStack() as stack:
        # Open one session per server
        sessions: list[tuple[str, ClientSession]] = []
        for path in servers:
            read, write = await stack.enter_async_context(stdio_client(_params(path)))
            sess = await stack.enter_async_context(ClientSession(read, write))
            await sess.initialize()
            sessions.append((path, sess))

        # Combine tool list, build routing table (tool name → which server)
        tool_to_server: dict[str, tuple[str, ClientSession]] = {}
        tools_for_claude: list[dict] = []
        for path, sess in sessions:
            resp = await sess.list_tools()
            for t in resp.tools:
                tool_to_server[t.name] = (path, sess)
                tools_for_claude.append({
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema,
                })

        client = Anthropic()
        messages = [{"role": "user", "content": message}]

        # ── Show what Claude actually receives as the "menu" ────────────
        print("══ TOOL MENU SENT TO CLAUDE ══")
        print(f"  (these schemas are auto-generated from each tool's signature + docstring)")
        for t in tools_for_claude:
            schema = t["input_schema"]
            params = schema.get("properties", {})
            param_str = ", ".join(
                f'{k}:{v.get("type", "?")}' for k, v in params.items()
            )
            req = schema.get("required", [])
            req_str = f" (required: {req})" if req else ""
            print(f"  • {t['name']}({param_str}){req_str}")
            desc = (t["description"] or "").strip().split("\n")[0]
            print(f"      \"{desc}\"")
        print("══ END MENU ══\n")

        print(f"YOU say:\n  {message}\n")

        for round_no in range(1, max_rounds + 1):
            resp = client.messages.create(
                model=model, max_tokens=2048,
                tools=tools_for_claude, messages=messages,
            )

            if resp.stop_reason != "tool_use":
                final_text = "".join(b.text for b in resp.content if b.type == "text")
                print(f"\nCLAUDE final answer:\n  {final_text}")
                return

            # ── Show the raw tool_use blocks Claude returned ───────────
            print(f"[round {round_no}] CLAUDE returned (stop_reason={resp.stop_reason!r}):")
            for block in resp.content:
                if block.type == "tool_use":
                    print(f"  ← tool_use  name={block.name!r}  input={dict(block.input)!r}")
                elif block.type == "text" and block.text.strip():
                    print(f"  ← text      {block.text.strip()[:120]!r}")
            print(f"  (Claude picked these from the menu above — based on tool name + description)")

            messages.append({"role": "assistant", "content": resp.content})
            tool_results = []
            for block in resp.content:
                if block.type != "tool_use":
                    continue
                path, sess = tool_to_server[block.name]
                print(f"  → calling {block.name} from {path}")
                out = await sess.call_tool(block.name, block.input)

                result_blocks = []
                for c in out.content:
                    if getattr(c, "type", None) == "text":
                        result_blocks.append({"type": "text", "text": c.text})
                        snippet = c.text[:160].replace("\n", " ")
                        print(f"     result (text): {snippet}")
                    elif getattr(c, "type", None) == "image":
                        result_blocks.append({
                            "type": "image",
                            "source": {"type": "base64", "media_type": c.mimeType, "data": c.data},
                        })
                        print(f"     result (image): a {c.mimeType} (shown below)")
                        display(IPImage(data=base64.b64decode(c.data)))

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_blocks if result_blocks else "ok",
                })
            print()
            messages.append({"role": "user", "content": tool_results})

        print("(stopped: hit max rounds)")
