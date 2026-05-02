"""Beginner-friendly helpers for the A2A demo.

Keeps subprocess / HTTP / JSON-RPC details out of the notebook.
"""

import json
import subprocess
import sys
import time
import uuid

import httpx


def start_agent(script_path: str, port: int = 9999, startup_timeout: float = 10.0):
    """Start an A2A agent as a background process. Returns a handle for stop_agent()."""
    proc = subprocess.Popen(
        [sys.executable, script_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    url = f"http://localhost:{port}/.well-known/agent-card.json"
    deadline = time.time() + startup_timeout
    while time.time() < deadline:
        try:
            httpx.get(url, timeout=0.5)
            print(f"agent started (pid={proc.pid}, port={port})")
            return proc
        except Exception:
            time.sleep(0.3)
    proc.terminate()
    raise RuntimeError(f"agent at {script_path} failed to start within {startup_timeout}s")


def stop_agent(proc) -> None:
    """Stop an agent started by start_agent()."""
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("agent stopped")


def fetch_agent_card(port: int = 9999) -> dict:
    """Get the agent's self-description (the 'agent card')."""
    return httpx.get(f"http://localhost:{port}/.well-known/agent-card.json", timeout=5).json()


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


def send_message(text: str, port: int = 9999, timeout: float = 120.0) -> dict:
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
    return httpx.post(f"http://localhost:{port}/", json=request, timeout=timeout).json()


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
