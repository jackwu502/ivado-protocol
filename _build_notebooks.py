"""Generate the three lab notebooks.

Default:  python _build_notebooks.py            # build all three
Single:   python _build_notebooks.py 2          # build only demo 2
          python _build_notebooks.py 1 3        # build demos 1 and 3

Notebooks are demo-only. Conceptual material lives in slides.pptx.

Layout produced:
    demo1_mcp/01_mcp_demo.ipynb
    demo2_a2a/02_a2a_demo.ipynb
    demo3_fa/03_fa_demo.ipynb
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
DEMO1_DIR = HERE / "demo1_mcp"
DEMO2_DIR = HERE / "demo2_a2a"
DEMO3_DIR = HERE / "demo3_fa"

# CLI: which demos to build. Empty / no args means all three.
_args = {a for a in sys.argv[1:] if a in {"1", "2", "3"}}
BUILD = _args or {"1", "2", "3"}

BOOTSTRAP_COMMON = """\
# ── Bootstrap: resolve paths to shared/ and sibling helpers ──
import sys
from pathlib import Path
HERE = Path.cwd()
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))   # so `from shared.X import Y` works
sys.path.insert(0, str(HERE))   # so sibling helpers import directly
STOCK_MCP_SERVER = str(ROOT / "shared" / "stock_mcp_server.py")
"""


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "execution_count": None,
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def notebook(cells: list[dict]) -> dict:
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "ivado-lab (3.12)", "language": "python", "name": "ivado-lab"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


SETUP_COMMON = """\
## First-time setup

Run this once in a terminal, from the directory where you want the repo:

```bash
git clone https://github.com/jackwu502/ivado-protocol.git
cd ivado-protocol

python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m ipykernel install --user --name ivado-lab --display-name "ivado-lab (3.12)"
```

Create your local `.env` file:

```bash
cp .env.example .env
```

Then edit `.env` and fill in one credential route:

```bash
# Option 1: Anthropic direct
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6

# Option 2: OpenRouter-compatible Anthropic endpoint
# ANTHROPIC_BASE_URL=https://openrouter.ai/api
# ANTHROPIC_API_KEY=sk-or-v1-...
# ANTHROPIC_MODEL=anthropic/claude-sonnet-4.5
```

Do not commit `.env`; it is intentionally gitignored.

Start Jupyter from the repo root and select the `ivado-lab (3.12)` kernel:

```bash
python -m jupyter lab
```
"""


# ============================================================================
# 01 — MCP demo
# ============================================================================
mcp_cells = [
    md("""# Demo 1 — MCP

**Scenario:** ask an LLM about a stock. The LLM has two tool servers.

```
   you (this notebook)
        │
        ▼
   Claude (LLM)  ◄── MCP client (mcp_helpers.py)
        │
        ├──► stock_mcp_server.py    (subprocess via stdio)
        │      get_quote, get_history, get_company_info, get_news_headlines
        │
        └──► viz_mcp_server.py      (subprocess via stdio)
               line_chart, compare_lines
```

| File | Tools |
|------|-------|
| [`../shared/stock_mcp_server.py`](../shared/stock_mcp_server.py) | `get_quote`, `get_history`, `get_company_info`, `get_news_headlines` |
| [`viz_mcp_server.py`](viz_mcp_server.py) | `line_chart`, `compare_lines` |

Data backend: `yfinance` (no API key required). For production, swap to a company-maintained MCP server such as [Alpha Vantage's official one](https://mcp.alphavantage.co/).

""" + SETUP_COMMON),
    code(BOOTSTRAP_COMMON + 'VIZ_MCP_SERVER = str(HERE / "viz_mcp_server.py")\n'),
    code("""%pip install -q mcp anthropic yfinance matplotlib python-dotenv

import os
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

if not os.getenv("ANTHROPIC_API_KEY"):
    print("Note: ANTHROPIC_API_KEY not set in .env — the final 'hand to Claude' cell will skip.")
else:
    print(f"ready  (model={os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-6')})")"""),
    md("""## What an MCP server actually looks like

Below is the full source of `shared/stock_mcp_server.py`. Notice three things:

1. `FastMCP("stock-server")` — one line creates the server.
2. Each `@mcp.tool()` decorator turns a Python function into an MCP tool.
3. The function's **type hints + docstring** become the schema the LLM sees — no separate JSON schema written by hand."""),
    code("""from IPython.display import Code
Code(filename=str(ROOT / "shared" / "stock_mcp_server.py"), language="python")"""),
    md("""## List tools

Each server *advertises* its tools. **The servers themselves are passive — they cannot initiate anything; they only respond when called.** That is the MCP contract."""),
    code("""from mcp_helpers import list_tools

await list_tools(STOCK_MCP_SERVER)"""),
    code("""await list_tools(VIZ_MCP_SERVER)"""),
    md("""## Call one tool directly"""),
    code("""from mcp_helpers import call_tool

await call_tool(STOCK_MCP_SERVER, "get_quote", ticker="NVDA")"""),
    code("""await call_tool(STOCK_MCP_SERVER, "get_history", ticker="NVDA", days=10)"""),
    md("""## Hand both servers to Claude

The LLM gets all six tools. **The output below shows the contract live:**

1. **`══ TOOL MENU SENT TO CLAUDE ══`** — exactly the schemas Claude receives (auto-generated from each function's signature + docstring)
2. **`← tool_use  name=...  input=...`** — the raw decision Claude returned. No `if tool_name == "..."` in our code; Claude picked from the menu by reading the descriptions.
3. **`→ calling ...`** — our dispatcher executes whichever tool Claude named.

This whole loop is what makes MCP "the LLM is the only orchestrator" concrete."""),
    code("""from mcp_helpers import chat_with_claude

await chat_with_claude(
    message=(
        "How has NVDA traded over the last 10 days? "
        "Plot the closing prices and tell me what you see."
    ),
    servers=[STOCK_MCP_SERVER, VIZ_MCP_SERVER],
)"""),
    md("""### What just happened — the MCP architecture in action

Look at the trace above:

- Every tool call **originated from Claude**.
- Every tool result **returned to Claude**.
- The two servers **never talked to each other** — they don't even know the other exists.

Claude was the only orchestrator. All the data — stock prices, the PNG — flowed through Claude's context window. That is the MCP shape: one decision-maker, N passive tool catalogs."""),
]

if "1" in BUILD:
    DEMO1_DIR.mkdir(exist_ok=True)
    (DEMO1_DIR / "01_mcp_demo.ipynb").write_text(json.dumps(notebook(mcp_cells), indent=1, ensure_ascii=False))
    print("wrote demo1_mcp/01_mcp_demo.ipynb")


# ============================================================================
# 02 — A2A demo
# ============================================================================
a2a_cells = [
    md("""# Demo 2 — A2A

Two A2A agents in a chain: you → **equity** → **macro**. Each agent has its own LLM and its own MCP tools.

```
   you (notebook on localhost)
        │
        │  A2A
        ▼
   equity  (127.0.0.3:9999) ──A2A──► macro  (127.0.0.2:9998)
        │                   ◄─reply──
        ▼
   combined brief back to you
```

The notebook hosts no agents — both agents live on different loopback IPs to make their separateness visually obvious. Equity is independent of macro; it just *also* acts as an A2A client when it needs to delegate.

""" + SETUP_COMMON + """

Use the same `.env` from Demo 1."""),
    code(BOOTSTRAP_COMMON),
    code("""%pip install -q "a2a-sdk<1.0" uvicorn httpx anthropic mcp yfinance python-dotenv

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
print("ready")"""),

    md("""## 1. Imports

The user only knows one address — equity's. Macro's URL is hidden inside equity's own source."""),
    code("""import asyncio
import json
import uuid
import httpx
import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message
from shared.agent_runner import run_agent

# The only address the *user* (this notebook) ever needs.
# Notebook runs on localhost; both agents live on different loopback IPs
# (equity on 127.0.0.3, macro on 127.0.0.2) so they look like remote services.
EQUITY_URL = "http://127.0.0.3:9999"
print("ready — user only knows:", EQUITY_URL)"""),

    md("""## 2. Macro analyst

The leaf agent. Its own Claude + MCP tools, wrapped as an A2A server so equity can call it."""),
    code('''# Macro picks its own bind address + port. Using 127.0.0.2 (a
# distinct loopback IP) so visually it looks like a separate service.
MACRO_HOST = "127.0.0.2"
MACRO_PORT = 9998

MACRO_SYSTEM_PROMPT = """You are a macro / sector analyst. Given a sector
or thematic question, answer concisely (2-3 sentences) using the available
stock-data tools if helpful. Do not produce long reports."""


class MacroAnalystExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        question = context.get_user_input() or "Give a brief market outlook."
        macro_trace: list[str] = []
        try:
            answer = await run_agent(
                question=question,
                mcp_servers=[STOCK_MCP_SERVER],
                system_prompt=MACRO_SYSTEM_PROMPT,
                trace=macro_trace,
                agent_label="macro",
            )
        except Exception as exc:
            answer = f"(macro analyst error: {exc})"
        # Bundle macro's trace lines into the reply so equity can interleave
        # them into its own trace at the right point in time.
        if macro_trace:
            payload = (
                "\\u27ea\\u27eaTRACE\\u27eb\\u27eb\\n"
                + "\\n".join(macro_trace)
                + "\\n\\u27ea\\u27ea/TRACE\\u27eb\\u27eb\\n"
                + answer
            )
        else:
            payload = answer
        await event_queue.enqueue_event(new_agent_text_message(payload))

    async def cancel(self, context, event_queue):
        raise NotImplementedError


def build_macro_card() -> AgentCard:
    return AgentCard(
        name="MacroAnalystAgent",
        description="Sector / macro outlook analyst.",
        url=f"http://{MACRO_HOST}:{MACRO_PORT}/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[AgentSkill(
            id="sector_outlook",
            name="Sector outlook",
            description="Quick view of a sector or macro theme.",
            tags=["finance", "macro", "sector"],
            examples=["semiconductor sector outlook", "energy in 2025"],
        )],
    )'''),

    md("""## 3. Equity analyst (chain caller)

Same as macro, plus one extra tool: `ask_macro_analyst`. When Claude calls it, equity makes an A2A request to macro — that's the chain edge."""),
    code('''# Equity's own bind address + port. Using 127.0.0.3 (a distinct
# loopback IP from macro's 127.0.0.2) so neither agent shares an address
# with the notebook, and the trace makes it visible they're separate services.
EQUITY_HOST = "127.0.0.3"
EQUITY_PORT = 9999

EQUITY_SYSTEM_PROMPT = """You are an equity analyst writing a brief on a
single stock. Use the stock-data tools to fetch price action, company info,
and news. If sector or macro context would inform your brief, call
`ask_macro_analyst` ONCE for it. Then write a concise brief."""


ASK_MACRO_TOOL = {
    "name": "ask_macro_analyst",
    "description": (
        "Ask the macro/sector analyst for sector or thematic context. "
        "Use at most once per brief."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Plain-English question for the macro analyst.",
            }
        },
        "required": ["question"],
    },
}


import re


def _extract_macro_trace(reply_text: str):
    """If reply was wrapped with ⟪⟪TRACE⟫⟫...⟪⟪/TRACE⟫⟫, pull the trace
    lines out and return (trace_lines, cleaned_text)."""
    m = re.search(
        r"\\u27ea\\u27eaTRACE\\u27eb\\u27eb\\n(.*?)\\n\\u27ea\\u27ea/TRACE\\u27eb\\u27eb\\n",
        reply_text, flags=re.S,
    )
    if not m:
        return [], reply_text
    return m.group(1).splitlines(), reply_text[:m.start()] + reply_text[m.end():]


def _make_call_macro_a2a(equity_trace: list[str]):
    """Build an A2A-client closure that appends macro's trace lines into
    equity's trace at the moment the macro call returns — so the audience
    sees [equity] -> [macro] tool calls -> [equity] in temporal order."""
    MACRO_URL = "http://127.0.0.2:9998"

    async def call_macro_a2a(name_, args):
        if name_ != "ask_macro_analyst":
            return f"(unknown tool: {name_})"
        question = args.get("question", "")
        print(f"  [equity → A2A] calling MacroAnalystAgent at {MACRO_URL}: \\"{question[:60]}\\"")
        request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "messageId": str(uuid.uuid4()),
                    "parts": [{"kind": "text", "text": question}],
                }
            },
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{MACRO_URL}/", json=request)
            resp = r.json()
        result = resp.get("result", {}) or {}
        if result.get("kind") == "message":
            for part in result.get("parts", []):
                if part.get("kind") == "text":
                    raw = part["text"]
                    macro_lines, clean = _extract_macro_trace(raw)
                    # Splice macro's trace into equity's trace right here,
                    # between equity's [tool] line and equity's [result] line.
                    if macro_lines:
                        equity_trace.extend(macro_lines)
                    print(f"  [equity ← A2A] reply ({len(clean)} chars, "
                          f"+{len(macro_lines)} trace lines from macro)")
                    return clean
        return "(no text reply from macro)"

    return call_macro_a2a


class EquityAnalystExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        question = context.get_user_input() or "Analyze the market."
        trace: list[str] = []
        call_macro_a2a = _make_call_macro_a2a(trace)
        try:
            answer = await run_agent(
                question=question,
                mcp_servers=[STOCK_MCP_SERVER],            # MCP layer
                system_prompt=EQUITY_SYSTEM_PROMPT,
                extra_tools=[ASK_MACRO_TOOL],              # A2A chain edge
                extra_tool_executor=call_macro_a2a,
                trace=trace,
                agent_label="equity",
            )
        except Exception as exc:
            answer = f"(equity analyst error: {exc})"
        if trace:
            full = (
                "── Internal trace (each line shows which agent called the tool) ──\\n"
                + "\\n".join(trace)
                + "\\n── End trace ──\\n\\n"
                + answer
            )
        else:
            full = answer
        await event_queue.enqueue_event(new_agent_text_message(full))

    async def cancel(self, context, event_queue):
        raise NotImplementedError


def build_equity_card() -> AgentCard:
    return AgentCard(
        name="EquityAnalystAgent",
        description="Equity analyst — produces stock briefs; may chain to a macro analyst.",
        url=f"http://{EQUITY_HOST}:{EQUITY_PORT}/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[AgentSkill(
            id="stock_brief",
            name="Stock brief",
            description="Brief on a single stock; may include sector context.",
            tags=["finance", "equities", "research"],
            examples=["Analyze NVDA briefly. Include sector context."],
        )],
    )'''),

    md("""## 4. Boot both agents

Two `uvicorn` tasks. **Notebook is on localhost; both agents live on different loopback IPs** — equity on `127.0.0.3`, macro on `127.0.0.2` — so the trace makes it obvious the two agents are remote services from the user's perspective.

> **macOS first-run only:** if you see *"Can't assign requested address"*, alias both loopbacks once (sticks until reboot):
> ```bash
> sudo ifconfig lo0 alias 127.0.0.2 up
> sudo ifconfig lo0 alias 127.0.0.3 up
> ```"""),
    code("""def _build_app(card, executor):
    handler = DefaultRequestHandler(
        agent_executor=executor, task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(agent_card=card, http_handler=handler).build()


async def _start(app, host, port):
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None
    asyncio.create_task(server.serve())
    for _ in range(40):
        await asyncio.sleep(0.1)
        if server.started: break
    return server

macro_server  = await _start(_build_app(build_macro_card(),  MacroAnalystExecutor()),
                             MACRO_HOST, MACRO_PORT)
equity_server = await _start(_build_app(build_equity_card(), EquityAnalystExecutor()),
                             EQUITY_HOST, EQUITY_PORT)
print(f"MacroAnalystAgent  on http://{MACRO_HOST}:{MACRO_PORT}")
print(f"EquityAnalystAgent on http://{EQUITY_HOST}:{EQUITY_PORT}")"""),

    md("""## 5. The user role

Quick sanity-check: from the user's perspective, the only address in scope is `EQUITY_URL`. Macro exists, but it's hidden behind equity — exactly the encapsulation A2A is designed for. The user never has to learn that there's even a chain happening."""),
    code("""from a2a_helpers import send_message, show_response

print("Where each thing lives:")
print(f"  localhost          ← notebook (the user). NO agent here.")
print(f"  127.0.0.3:9999     ← EquityAnalystAgent. Notebook calls this.")
print(f"  127.0.0.2:9998     ← MacroAnalystAgent. ONLY equity calls this; notebook never touches it.")"""),

    md("""## 6. Send one sentence — watch the chain

We send **one** sentence to equity and wait for one final brief. While the call is in flight, watch the printed trace: you'll see equity's own tool calls, then `[equity → A2A]` when its Claude decides to delegate, then macro's tool calls interleaved live, then `[equity ← A2A]` when macro replies, then equity weaves it all into the brief."""),
    code("""response = await send_message(
    "Analyze NVDA briefly. Include sector context.",
    url=EQUITY_URL,
    timeout=180.0,
)
show_response(response)"""),

    md("""### Recap

Two architectural points worth pausing on:

1. **Equity is both server (to you) and client (to macro).** That's the whole A2A chain pattern in one sentence — every agent is a peer that can also call other agents.
2. **Look at the duplicate `get_quote(NVDA)` lines** — equity called it, then macro called it again. Why? Because each A2A call is a fresh Claude conversation; macro's context is empty when it starts and has no idea equity already fetched that data. Compare with Demo 1's MCP, where everything sits in one `messages[]` array and Claude never re-asks. **This is the price of A2A's encapsulation: callee = separate brain.**

And the limitation: `MACRO_URL` is still hardcoded in equity's source. A2A spec doesn't standardize a registry, so every chain edge gets wired by hand. Demo 3 replaces that hardcode with a runtime lookup."""),

    md("""## 7. Raw JSON-RPC envelope (optional)"""),
    code("""show_response(response, raw=True)"""),

    md("""## 8. Stop both agents"""),
    code("""for srv in (equity_server, macro_server):
    srv.should_exit = True
await asyncio.sleep(1)
print("both agents stopped")"""),
]

if "2" in BUILD:
    DEMO2_DIR.mkdir(exist_ok=True)
    (DEMO2_DIR / "02_a2a_demo.ipynb").write_text(json.dumps(notebook(a2a_cells), indent=1, ensure_ascii=False))
    print("wrote demo2_a2a/02_a2a_demo.ipynb")


# ============================================================================
# 03 — FA demo
# ============================================================================
ALN_GIT_URL = "git+https://github.com/FoundationAgents/ai-link-net.git"

fa_cells = [
    md("""# Demo 3 — FA (Foundation Agents Protocol)

Source: [github.com/FoundationAgents/ai-link-net](https://github.com/FoundationAgents/ai-link-net)

Same scenario as Demo 2 (alice asks for a stock brief → analyst delegates to a sector specialist), but the cross-agent layer is **FA** instead of A2A. Equity **discovers** macro at runtime — no URL hardcoded anywhere.

![](../figures/fa_topology.png)

Three independent hosts under one relay; one entity per host. **Two protocols stack:** FA routes between entities (cross-host); MCP supplies each agent's tools (stock data).

""" + SETUP_COMMON + """

Needs the FA reference implementation [`ai-link-net`](https://github.com/FoundationAgents/ai-link-net). The install cell below uses a local clone if present, otherwise GitHub."""),
    code(BOOTSTRAP_COMMON),
    code(f"""assert sys.version_info >= (3, 12), "ai-link-net needs Python 3.12+"

# Dependencies for the wrapped MCP server and the analyst loop
%pip install -q mcp anthropic yfinance python-dotenv

import importlib.util
import subprocess

def _have_ai_link_net():
    return importlib.util.find_spec("fp") is not None and importlib.util.find_spec("aln") is not None

def _pip_install(*args):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *args])

if _have_ai_link_net():
    print("ai-link-net already importable")
else:
    candidates = []
    candidates.append(ROOT / "ai-link-net")
    candidates.append(ROOT.parent / "ai-link-net")

    local_clone = next((p for p in candidates if p and p.exists()), None)
    if local_clone:
        print(f"installing ai-link-net from local clone: {{local_clone}}")
        _pip_install("-e", str(local_clone))
    else:
        print("installing ai-link-net from GitHub")
        _pip_install({ALN_GIT_URL!r})

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
print("Python:", sys.version.split()[0])"""),
    md("""## Setup

Imports plus three small patches for a clean in-notebook demo: silence FA's chatty info-level logs, skip its on-disk persistence, and teach `Host` to resolve `TOOL` entities through `MCPHandler` (the bridge from FA's tool concept to MCP)."""),
    code("""import asyncio, json
from unittest.mock import patch
from loguru import logger

logger.remove()
logger.add(sys.stderr, level="WARNING", format="<level>{level}</level> | {message}")
patch("fp.host.Host.save").start()

from fp import Host
from aln.app.handlers import create_entity_handler

_orig = Host._resolve_entity_handler
def _resolve(self, entity, handler, provider, system_prompt, handler_config):
    return _orig(self, entity, handler, provider, system_prompt, handler_config) \\
        or create_entity_handler(entity=entity, kind=entity.kind, provider=provider,
                                 system_prompt=system_prompt, handler_config=handler_config)
Host._resolve_entity_handler = _resolve
print("ready")"""),
    md("""## 1. System prompts + tool schemas

Two system prompts (one per agent) plus two extra tools that equity will use to discover and delegate: `list_network_specialists` and `delegate_to_specialist`.

Notice the tool definitions are **completely generic** — no mention of "macro" anywhere. The equity prompt tells Claude to *first* list what's on the network, *read each entity's description*, and pick whichever one fits the question. That's the FA discovery story in code form."""),
    code("""from fp import Host, Message, MessageKind
from fp.core.base import EntityKind
from fp.core.wellknown import FPAddress
from fp.message import FriendRequestPayload
from shared.agent_runner import run_agent

FRIEND_KINDS = {MessageKind.FRIEND_REQUEST, MessageKind.FRIEND_ACCEPT, MessageKind.FRIEND_REJECT}

MACRO_SYSTEM_PROMPT = (
    "You are a macro / sector analyst. Given a sector or thematic question, "
    "answer concisely (2-3 sentences) using the available stock-data tools "
    "if helpful. Do not produce long reports."
)

EQUITY_SYSTEM_PROMPT = (
    "You are an equity analyst writing a brief on a single stock. Use the "
    "stock-data tools to fetch price action, company info, and news.\\n\\n"
    "If sector or macro context would inform your brief, you may delegate "
    "that question to another agent on the federated network. The procedure:\\n"
    "  1) Call `list_network_specialists` to see what other public agents "
    "     are reachable. Each entry has an entity_id and a description.\\n"
    "  2) Read the descriptions and pick the one whose stated expertise "
    "     best matches what you need.\\n"
    "  3) Call `delegate_to_specialist(entity_id=..., question=...)` with "
    "     the chosen entity_id.\\n\\n"
    "Use at most one delegation per brief. Then write a concise brief that "
    "weaves in the delegated answer if you obtained one."
)

LIST_SPECIALISTS_TOOL = {
    "name": "list_network_specialists",
    "description": (
        "List public AGENT entities reachable on the federated network "
        "(excluding yourself). Returns a JSON array of objects with "
        "entity_id, name, and description."
    ),
    "input_schema": {"type": "object", "properties": {}},
}

DELEGATE_TO_SPECIALIST_TOOL = {
    "name": "delegate_to_specialist",
    "description": (
        "Send a plain-English question to another agent on the network "
        "and return its answer. You must first call "
        "list_network_specialists to obtain a valid entity_id."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "entity_id": {"type": "string"},
            "question": {"type": "string"},
        },
        "required": ["entity_id", "question"],
    },
}

def _payload_text(msg):
    p = msg.payload
    if isinstance(p, dict):
        return p.get("text") or p.get("question") or ""
    return getattr(p, "text", "") or ""

def _is_agent(card):
    return "agent" in str(card.kind).lower()"""),

    md("""## 2. Macro analyst

A simple FA entity: when it receives an INVOKE mail, it runs a Claude loop with the stock MCP server and sends the answer back as another mail. No A2A involved — the cross-agent layer here is FA itself."""),
    code("""def make_macro_analyst(host, name="MacroAnalyst"):
    state = {}

    async def _handle_query(sender_addr, msg):
        question = _payload_text(msg)
        try:
            answer = await run_agent(
                question=question,
                mcp_servers=[STOCK_MCP_SERVER],
                system_prompt=MACRO_SYSTEM_PROMPT,
            )
        except Exception as exc:
            answer = f"(macro analyst error: {exc})"
        await state["entity"].send_message(
            to=FPAddress(address=sender_addr),
            message=Message(kind=MessageKind.INVOKE, payload={"text": answer}),
        )

    async def handler(msg):
        if msg.kind in FRIEND_KINDS:
            return
        sender_addr = msg.metadata.get("sender_address", "")
        if not sender_addr:
            return
        asyncio.create_task(_handle_query(sender_addr, msg))

    entity = host.register_entity(
        name=name,
        kind=EntityKind.AGENT,
        is_public=True,
        description="Sector / macro outlook analyst.",
        handler=handler,
    )
    state["entity"] = entity
    return entity"""),

    md("""## 3. Equity analyst (discovery + delegation)

Three pieces to look at:

- **`_list_specialists`** — calls `host.get_discoverable_entities(include_parent=True)`, returns the list with descriptions, and prints each one so you can watch the discovery happen.
- **`_ask(entity_id, question)`** — sends an INVOKE to whichever entity Claude picked, then awaits the reply on a queue.
- **`handler`** — when something arrives, route it: a reply from a specialist we're waiting on goes into the queue; anything else is treated as a new user query.

Crucially, equity's source has **zero hardcoded knowledge** about macro — no name, no URL, no entity_id."""),
    code("""def make_equity_analyst(host, name="EquityAnalyst"):
    state = {"entity": None, "pending_target_id": None, "pending_queue": None}

    def _list_specialists():
        me_id = state["entity"].address.entity_uid
        items = []
        for card in host.get_discoverable_entities(include_parent=True):
            if not _is_agent(card): continue
            if card.address.entity_uid == me_id: continue
            items.append({
                "entity_id": card.address.address,
                "name": card.name,
                "description": (card.description or "").strip(),
            })
        # Visible trace
        print(f"  [equity → discovery] list_network_specialists "
              f"returned {len(items)} agents:")
        for it in items:
            desc = it["description"][:60]
            print(f"    • {it['name']:<14}  ({it['entity_id']})  — {desc}")
        return json.dumps(items, indent=2)

    def _find_card_by_id(entity_id):
        for card in host.get_discoverable_entities(include_parent=True):
            if card.address.address == entity_id:
                return card
        return None

    async def _ask(entity_id, question):
        target = _find_card_by_id(entity_id)
        if target is None:
            return f"(no entity with id {entity_id} on the network)"
        print(f"  [equity → delegation] delegate_to_specialist "
              f"to {target.name}: \\"{question[:80]}\\"")
        # Lazy friend handshake
        if target.address.entity_uid not in state["entity"].friends:
            await state["entity"].send_message(
                to=target,
                message=Message(
                    kind=MessageKind.FRIEND_REQUEST,
                    payload=FriendRequestPayload(sender_card=state["entity"].entity_card),
                ),
            )
            await asyncio.sleep(0.5)
        # Route INVOKE, wait for reply via inbox queue
        queue = asyncio.Queue()
        state["pending_target_id"] = target.address.address
        state["pending_queue"] = queue
        await state["entity"].send_message(
            to=target,
            message=Message(kind=MessageKind.INVOKE, payload={"text": question}),
        )
        try:
            reply = await asyncio.wait_for(queue.get(), timeout=120)
            text = _payload_text(reply) or "(empty reply)"
            print(f"  [equity ← reply] from {target.name}: {len(text)} chars")
            return text
        finally:
            state["pending_target_id"] = None
            state["pending_queue"] = None

    async def _delegate(name_, args):
        if name_ == "list_network_specialists":
            return _list_specialists()
        if name_ == "delegate_to_specialist":
            return await _ask(args.get("entity_id", ""), args.get("question", ""))
        return f"(unknown tool: {name_})"

    async def _handle_query(sender_addr, msg):
        question = _payload_text(msg)
        try:
            answer = await run_agent(
                question=question,
                mcp_servers=[STOCK_MCP_SERVER],
                system_prompt=EQUITY_SYSTEM_PROMPT,
                extra_tools=[LIST_SPECIALISTS_TOOL, DELEGATE_TO_SPECIALIST_TOOL],
                extra_tool_executor=_delegate,
            )
        except Exception as exc:
            answer = f"(equity analyst error: {exc})"
        await state["entity"].send_message(
            to=FPAddress(address=sender_addr),
            message=Message(kind=MessageKind.INVOKE, payload={"text": answer}),
        )

    async def handler(msg):
        if msg.kind in FRIEND_KINDS: return
        sender_addr = msg.metadata.get("sender_address", "")
        if not sender_addr: return
        # Reply from a specialist we are currently waiting on → queue
        if (state["pending_target_id"] == sender_addr
                and state["pending_queue"] is not None):
            await state["pending_queue"].put(msg)
            return
        # Anything else: new user query
        asyncio.create_task(_handle_query(sender_addr, msg))

    entity = host.register_entity(
        name=name,
        kind=EntityKind.AGENT,
        is_public=True,
        description=(
            "Equity analyst — writes briefs on individual stocks. May "
            "delegate sector/macro questions to other agents on the network."
        ),
        handler=handler,
    )
    state["entity"] = entity
    return entity"""),

    md("""## 4. Build the network

Four hosts under one relay: `CloudHost` (root), `AliceHost` (alice), `EquityHost` (equity), `MacroHost` (macro). Each host has exactly one entity — they're truly independent.

**Alice has no idea macro exists** — she only knows her own host. Equity will discover macro at query time through the federation tree."""),
    code("""cloud      = Host(name="CloudHost")
host_alice = Host(name="AliceHost",  port=18100)
host_equity = Host(name="EquityHost", port=18101)
host_macro  = Host(name="MacroHost",  port=18102)
for h in (host_alice, host_equity, host_macro):
    h.set_parent_host(cloud)

# Each agent on its own host
macro  = make_macro_analyst(host_macro)
equity = make_equity_analyst(host_equity)

# Alice (the user) on her own host — separate from any agent
alice_inbox: asyncio.Queue[Message] = asyncio.Queue()
async def alice_handler(msg):
    if msg.kind not in FRIEND_KINDS:
        await alice_inbox.put(msg)
alice = host_alice.register_entity("alice", kind=EntityKind.HUMAN, handler=alice_handler)

print(f"{'Entity':<14}  {'Address':<70}  Lives on")
for ent, hname in [(alice, 'AliceHost'), (equity, 'EquityHost'), (macro, 'MacroHost')]:
    print(f"{ent.name:<14}  {ent.address.address:<70}  {hname}")"""),
    md("""## 5. Discovery (the FA-only primitive)

Easiest place to inspect the federation is **on the relay** (`cloud`) — it sees all its children directly. **No URL was configured anywhere**; the host network IS the directory.

You'll only see **public** entities. Alice is registered without `is_public=True` (default is private), so she doesn't appear — humans typically aren't broadcast as callable services. Only the two AGENT entities show up, which is exactly what equity will pick from at runtime.

> **At runtime equity doesn't have access to `cloud`** — it only knows its own host. So it calls `host_equity.get_discoverable_entities(include_parent=True)`, which walks up through `parent_host` to cloud and gets the same list back. Same result, different POV."""),
    code("""print("From the relay's POV — all public entities reachable in the federation:\\n")
for card in cloud.get_discoverable_entities(include_parent=False):
    print(f"  {card.name:<14}  {card.address.address}  (kind={card.kind})")
    print(f"    description: {card.description}")
print("\\n(alice is hidden — not is_public)")"""),
    md("""## 6. Friend handshake (alice ↔ equity)

FA requires a one-time friend handshake before two entities exchange real messages — it's how each side captures the other's signing key. Alice ↔ equity we do explicitly here; the equity ↔ macro handshake will happen lazily inside `_ask` the first time equity delegates."""),
    code("""await alice.send_message(
    to=equity.entity_card,
    message=Message(kind=MessageKind.FRIEND_REQUEST,
                    payload=FriendRequestPayload(sender_card=alice.entity_card)),
)
await asyncio.sleep(0.5)
print("alice friends:", list(alice.friends.keys()))"""),
    md("""## 7. Alice asks one question

This is the moment of truth. Alice sends one INVOKE to equity. Watch the printed trace:

- `[equity → discovery]` — equity asks the network "who's reachable?" and the host returns a list of EntityCards
- equity's Claude reads each `description` and **picks** the right specialist (it's never told the name "macro")
- `[equity → delegation]` — equity sends the question, routed `EquityHost → CloudHost → MacroHost`
- macro's reply travels back the same path
- equity weaves it all into a final brief"""),
    code("""await alice.send_message(
    to=equity.entity_card,
    message=Message(
        kind=MessageKind.INVOKE,
        payload={"text": "Analyze NVDA briefly. Include sector context."},
    ),
)
reply = await asyncio.wait_for(alice_inbox.get(), timeout=300)
print(reply.payload["text"])"""),
    md("""### Recap

Look for the "Sector Context" paragraph in the brief above — that text was written by macro on MacroHost and travelled `MacroHost → CloudHost → EquityHost`, end-to-end. And the discovery line proves equity picked macro purely from the description string — re-run with a "geopolitics analyst" instead and it would just work, no code change.

Three FA primitives all fired in sequence: **discovery** (`get_discoverable_entities`), **Entity-ID addressing** (`delegate_to_specialist` takes an entity_id, not a URL), and **cross-host routing** (cloud relayed without either child knowing the other's IP). In A2A all three would be the application's problem; in FA they're protocol-native."""),

    md("""## 8. Bonus — offline delivery (something A2A cannot do)

**The story:** alice2 keeps sending messages to a worker. Halfway through, the worker's machine drops off the network. In **A2A** the call would just fail. In **FA** the relay quietly **queues** the messages and delivers them when the worker comes back — alice2 never knows anything went wrong.

We'll run a tiny 3-host federation (real WebSockets, real disconnect) and watch this happen.

> **macOS first-run only:** alias the extra loopbacks once (sticks until reboot):
> ```bash
> sudo ifconfig lo0 alias 127.0.0.2 up
> sudo ifconfig lo0 alias 127.0.0.3 up
> ```"""),

    md("""### Setup

Plumbing — `HostServer` imports + a small helper to start each host on its own loopback IP. Skim it; the interesting code is in the next cells."""),
    code("""import uvicorn
from fastapi import FastAPI
from fp import EntityStatus
from aln.app.service.host_server import HostServer
from aln.app.api.ws import router as ws_router
from aln.app.api.well_known import router as well_known_router

# Skip disk persistence for the in-notebook demo
patch("aln.app.service.host_server.HostServer._save_offline_mail_queues").start()
patch("aln.app.service.host_server.HostServer._load_offline_mail_queues").start()

def _make_host_app(host_runtime: HostServer) -> FastAPI:
    app = FastAPI()
    app.include_router(well_known_router)
    app.include_router(ws_router)
    app.state.host_runtime = host_runtime
    return app

async def start_host(host_runtime: HostServer, host: str, port: int):
    config = uvicorn.Config(_make_host_app(host_runtime), host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    server.install_signal_handlers = lambda: None
    asyncio.create_task(server.serve())
    for _ in range(50):
        await asyncio.sleep(0.1)
        if server.started: break
    return server

async def _no_reconnect():  # disable auto-retry so we control online/offline manually
    pass

print("helpers ready")"""),

    md("""### Build the federation

Three machines:

| Where | What lives there |
|---|---|
| **127.0.0.1**  (relay)  | nothing — just routes mail |
| **127.0.0.2**  (host_x) | `alice2` (the user) |
| **127.0.0.3**  (host_y) | `worker` (an echo agent) |

host_x and host_y open outbound WebSockets to the relay. That handshake is what marks them ONLINE."""),
    code("""# Build the three hosts
relay  = HostServer(name="Relay",  port=20001)
host_x = HostServer(name="HostX",  port=20002)  # alice2 lives here
host_y = HostServer(name="HostY",  port=20003)  # worker lives here

# alice2 — collects replies in an inbox queue
inbox2: asyncio.Queue = asyncio.Queue()
async def alice2_handler(msg):
    if msg.kind not in FRIEND_KINDS:
        await inbox2.put(msg)
alice2 = host_x.register_entity("alice2", kind=EntityKind.HUMAN, handler=alice2_handler)

# worker — echoes whatever it receives
async def worker_handler(msg):
    if msg.kind in FRIEND_KINDS: return
    sender = msg.metadata.get("sender_address", "")
    text = msg.payload.get("text", "")
    await worker.send_message(
        to=FPAddress(address=sender),
        message=Message(kind=MessageKind.INVOKE, payload={"text": f"echo: {text}"}),
    )
worker = host_y.register_entity(
    "worker", kind=EntityKind.AGENT, is_public=True,
    description="echo worker", handler=worker_handler,
)
host_y._reconnect_to_parent = _no_reconnect  # we control reconnects manually

# Boot uvicorn for each host on its own loopback IP
relay_srv  = await start_host(relay,  "127.0.0.1", 20001)
host_x_srv = await start_host(host_x, "127.0.0.2", 20002)
host_y_srv = await start_host(host_y, "127.0.0.3", 20003)

# Children connect outbound to the relay
await host_x.connect_to_parent("http://127.0.0.1:20001")
await host_y.connect_to_parent("http://127.0.0.1:20001")
await asyncio.sleep(1.0)


# Helper: print a clean snapshot of "what relay sees" + alice2's inbox
def show_state(label: str):
    worker_status = relay.entity_status.get(worker.address.entity_uid)
    queued = sum(len(q) for q in relay.offline_mail_queues.values())
    inbox = inbox2.qsize()
    status_str = worker_status.value.upper() if worker_status else "?"
    print(f"\\n─── State: {label} ───")
    print(f"   worker (relay's view):    {status_str}")
    print(f"   messages queued at relay: {queued}")
    print(f"   alice2's inbox:           {inbox} reply/replies waiting")
    print(f"───────────────────────────────────────────")

show_state("after everyone connects")"""),

    md("""### Baseline — round-trip while everyone is online

One quick exchange to confirm the network actually routes."""),
    code("""# Friend handshake (silent — required before sending real mail)
await alice2.send_message(
    to=worker.entity_card,
    message=Message(kind=MessageKind.FRIEND_REQUEST,
                    payload=FriendRequestPayload(sender_card=alice2.entity_card)),
)
await asyncio.sleep(0.8)

# Send and receive
await alice2.send_message(
    to=worker.entity_card,
    message=Message(kind=MessageKind.INVOKE, payload={"text": "baseline"}),
)
reply = await asyncio.wait_for(inbox2.get(), timeout=5.0)
print(f"alice2 sent 'baseline' → got back '{reply.payload['text']}'")
show_state("after baseline round-trip")"""),

    md("""### Worker drops off the network

We close host_y's WebSocket — same effect as worker's machine being shut down or losing wifi. **The relay notices on its own** (no manual flag flipping) and marks worker OFFLINE."""),
    code("""print("[host_y disconnects from the relay…]")
await host_y.disconnect_from_parent()
await asyncio.sleep(1.5)  # let the relay notice the dropped connection

show_state("after worker goes offline")"""),

    md("""### alice2 sends 3 messages anyway

alice2's code didn't change — she has no idea worker is down. The relay catches the OFFLINE status and **queues each message** instead of failing. Watch the queue grow."""),
    code("""print("alice2 sends 3 messages to the (offline) worker…")
for i in range(3):
    await alice2.send_message(
        to=worker.entity_card,
        message=Message(kind=MessageKind.INVOKE, payload={"text": f"queued-{i+1}"}),
    )
await asyncio.sleep(1.0)

show_state("3 messages later (worker still offline)")"""),

    md("""### Worker comes back

host_y reopens its WebSocket. The relay's handshake handler fires `_mark_child_entities_online` AND `_flush_offline_queues_for_child` automatically — the 3 queued messages stream out, worker echoes them, replies route back to alice2."""),
    code("""print("[host_y reconnects to the relay…]")
await host_y.connect_to_parent("http://127.0.0.1:20001")
await asyncio.sleep(2.0)  # handshake + auto-flush + worker replies + routing

show_state("after worker reconnects (relay auto-flushed)")

print("\\nalice2 finally received:")
while not inbox2.empty():
    reply = inbox2.get_nowait()
    print(f"   ← {reply.payload['text']}")"""),

    md("""### Recap

Look back at the four `─── State ───` blocks:

1. Everyone online → worker ONLINE, queue 0
2. Worker disconnects → worker OFFLINE, queue 0
3. alice2 sends 3 → worker OFFLINE, **queue 3**
4. Worker reconnects → worker ONLINE, **queue 0** + 3 replies in alice2's inbox

alice2's code is identical the whole time. **No retry loop. No "is recipient online?" check. No timeout handling.** The relay handled everything because addressing is by stable Entity ID and queueing is a protocol primitive.

(In production the relay also writes the queue to disk — survives restarts. Turned off here for the in-notebook demo.)"""),

    md("""### Cleanup"""),
    code("""for srv in (relay_srv, host_x_srv, host_y_srv):
    srv.should_exit = True
await asyncio.sleep(0.5)
print("offline-demo subnet stopped")"""),

    md("""## CLI entry point

The non-coding workflow uses the `aln` CLI and a WebUI (`aln init`, `aln ui`, `bash demo/quickstart.sh`). Below is just the help text."""),
    code("""import shutil, subprocess
from pathlib import Path
aln = shutil.which("aln") or str(Path(sys.executable).parent / "aln")
if Path(aln).exists():
    print(subprocess.run([aln, "-h"], capture_output=True, text=True).stdout[:1200])
else:
    print("`aln` not on PATH (does not affect the demo above)")"""),
]

if "3" in BUILD:
    DEMO3_DIR.mkdir(exist_ok=True)
    (DEMO3_DIR / "03_fa_demo.ipynb").write_text(json.dumps(notebook(fa_cells), indent=1, ensure_ascii=False))
    print("wrote demo3_fa/03_fa_demo.ipynb")
