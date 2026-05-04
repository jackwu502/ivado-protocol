"""HTTP/JSON-RPC client helpers for the A2A demo notebook.

The agent itself is defined inline in the notebook and runs as an asyncio
task in the same kernel. These helpers therefore use the *async* httpx
client — calling sync httpx from the same kernel would deadlock the event
loop the server needs to handle requests.
"""

import json
import uuid

import httpx


async def fetch_agent_card(port: int = 9999) -> dict:
    """Get the agent's self-description (the 'agent card')."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        r = await client.get(f"http://localhost:{port}/.well-known/agent-card.json")
        return r.json()


def print_agent_card(card: dict) -> None:
    """Pretty-print the highlights of an agent card."""
    print(f"name: {card.get('name')}")
    print(f"description: {card.get('description')}")
    print(f"url: {card.get('url')}")
    print("skills:")
    for s in card.get("skills", []):
        print(f"  • {s.get('name')}  (id={s.get('id')})")
        print(f"      {s.get('description')}")
        for ex in s.get("examples", []) or []:
            print(f"      example: {ex!r}")


async def send_message(text: str, port: int = 9999, timeout: float = 120.0) -> dict:
    """Send one text message to an A2A agent and return the raw JSON-RPC response."""
    request = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "messageId": str(uuid.uuid4()),
                "parts": [{"kind": "text", "text": text}],
            }
        },
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"http://localhost:{port}/", json=request)
        return r.json()


def show_response(response: dict, raw: bool = False) -> None:
    """Print the agent's text replies from a `message/send` response."""
    if raw:
        print(json.dumps(response, indent=2, ensure_ascii=False)[:2000])
        print("...\n")
        return

    result = response.get("result", {}) or {}

    # Two shapes exist depending on SDK version:
    #   1) result is a single message: {"kind": "message", "parts": [...]}
    #   2) result is a task with history: {"kind": "task", "history": [...]}
    if result.get("kind") == "message":
        entries = [result]
    else:
        entries = result.get("history", []) or []

    for entry in entries:
        if entry.get("role") != "agent":
            continue
        for part in entry.get("parts", []):
            if part.get("kind") == "text":
                print("AGENT:")
                for line in part["text"].splitlines():
                    print(f"  {line}")
