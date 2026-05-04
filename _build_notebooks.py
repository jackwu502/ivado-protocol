"""Generate the three lab notebooks. Run once: python _build_notebooks.py

Notebooks are demo-only. Conceptual material lives in slides.pptx.

Layout produced:
    demo1_mcp/01_mcp_demo.ipynb
    demo2_a2a/02_a2a_demo.ipynb
    demo3_fa/03_fa_demo.ipynb

Each notebook starts with a small bootstrap cell that resolves absolute paths
to the shared MCP server and adds the project root to `sys.path` so that
`from shared.X import Y` works regardless of where Jupyter is launched from.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
DEMO1_DIR = HERE / "demo1_mcp"
DEMO2_DIR = HERE / "demo2_a2a"
DEMO3_DIR = HERE / "demo3_fa"

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

The LLM gets all six tools. We ask one natural-language question; Claude decides which tools to call, in what order."""),
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

DEMO1_DIR.mkdir(exist_ok=True)
(DEMO1_DIR / "01_mcp_demo.ipynb").write_text(json.dumps(notebook(mcp_cells), indent=1, ensure_ascii=False))
print("wrote demo1_mcp/01_mcp_demo.ipynb")


# ============================================================================
# 02 — A2A demo
# ============================================================================
a2a_cells = [
    md("""# Demo 2 — A2A

**What changes from Demo 1:** the agentic loop moves *inside* an agent we call over HTTP. The caller sends one sentence; the agent plans, fetches, writes a brief.

**Protocol stack — A2A wraps MCP:**

```
   you (this notebook)
        │  A2A protocol  (HTTP + JSON-RPC)
        │  one sentence:  "Analyze NVDA ..."
        ▼
   ┌─────────────────────────────────────────────────────┐
   │  analyst_agent.py  —  A2A server, port 9999         │
   │                                                     │
   │   ┌─ internal Claude loop (Anthropic SDK) ─┐        │
   │   │                                        │        │
   │   │      MCP protocol  (stdio JSON-RPC)    │        │
   │   │              │                         │        │
   │   │              ▼                         │        │
   │   │   stock_mcp_server.py  (subprocess)    │        │
   │   │              │  yfinance               │        │
   │   └────────────────────────────────────────┘        │
   └─────────────────────────────────────────────────────┘
        │
        ▼  written brief
   you (notebook prints it)
```

**Two protocols stacked.** The agent speaks A2A to the outside, MCP to its tools — that's exactly what `slides 13` and the side-by-side table mean by "complementary, not competing".

Helpers: [`a2a_helpers.py`](a2a_helpers.py) — pure HTTP / JSON-RPC plumbing for the client side.

The agent itself is **defined inline below** — no separate `analyst_agent.py`.

""" + SETUP_COMMON + """

Use the same `.env` from Demo 1. The A2A agent reads `ANTHROPIC_*` to call Claude internally."""),
    code(BOOTSTRAP_COMMON),
    code("""%pip install -q "a2a-sdk<1.0" uvicorn httpx anthropic mcp yfinance python-dotenv

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
print("ready")"""),

    md("""## 1. The system prompt — the agent's role

This is plain English. The whole "intelligence" of the agent flows from this prompt + Claude's reasoning."""),
    code('''SYSTEM_PROMPT = """You are an equity analyst.
When given a ticker or a high-level question, plan and fetch the data you
need (recent quote, price history, company info, news), then write a
concise brief: where the stock is, how it has moved, what the company does,
and what notable news may explain the move. Use the tools available."""'''),

    md("""## 2. The agent's brain — `StockAnalystExecutor`

This class is the A2A `AgentExecutor` contract: `execute()` is called once per incoming task. Inside, we call `run_agent(...)` from `shared/agent_runner.py` — that's the Claude + MCP loop. **`mcp_servers=[STOCK_MCP_SERVER]` is the line where A2A nests MCP.**

We pass `trace=trace` so the agent's internal tool calls are captured and prepended to the response — useful for the demo."""),
    code("""from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.utils import new_agent_text_message
from shared.agent_runner import run_agent


class StockAnalystExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        question = context.get_user_input() or "Analyze the market."
        trace: list[str] = []
        try:
            answer = await run_agent(
                question=question,
                mcp_servers=[STOCK_MCP_SERVER],     # ← A2A wraps MCP here
                system_prompt=SYSTEM_PROMPT,
                trace=trace,
            )
        except Exception as exc:
            answer = f"(analyst error: {exc})"
        if trace:
            full = (
                "── Internal trace (agent's own tool calls) ──\\n"
                + "\\n".join(trace)
                + "\\n── End trace ──\\n\\n"
                + answer
            )
        else:
            full = answer
        await event_queue.enqueue_event(new_agent_text_message(full))

    async def cancel(self, context, event_queue):
        raise NotImplementedError("cancel not supported in this demo")"""),

    md("""## 3. The agent card — self-description served at `/.well-known/agent-card.json`

Any A2A-aware client reads this card and knows the agent's name, skills, endpoint."""),
    code("""from a2a.types import AgentCapabilities, AgentCard, AgentSkill


def build_agent_card() -> AgentCard:
    skill = AgentSkill(
        id="stock_brief",
        name="Stock brief",
        description=(
            "Given a ticker or a question about a stock, produce a brief "
            "covering recent price action, company profile, and notable news."
        ),
        tags=["finance", "equities", "research"],
        examples=[
            "Analyze NVDA.",
            "What's going on with TSLA this week?",
            "Brief me on MSFT — price, sector, recent news.",
        ],
    )
    return AgentCard(
        name="StockAnalystAgent",
        description="An equity analyst that produces written briefs from market data and news.",
        url="http://localhost:9999/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[skill],
    )

print(build_agent_card().model_dump_json(indent=2, exclude_none=True))"""),

    md("""## 4. Start the agent in-process

We run uvicorn as a background `asyncio` task **in this same kernel** — no subprocess, no external file. The HTTP server is live on `localhost:9999`."""),
    code("""import asyncio
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

handler = DefaultRequestHandler(
    agent_executor=StockAnalystExecutor(),
    task_store=InMemoryTaskStore(),
)
app = A2AStarletteApplication(agent_card=build_agent_card(), http_handler=handler)

config = uvicorn.Config(app.build(), host="0.0.0.0", port=9999, log_level="warning")
server = uvicorn.Server(config)
server.install_signal_handlers = lambda: None  # we are not in the main thread
agent_task = asyncio.create_task(server.serve())
await asyncio.sleep(2)  # let it bind
print("agent running on http://localhost:9999")"""),

    md("""## 5. Discover it over HTTP — fetch the agent card from outside

Note we `await` the helpers — the server runs in this kernel's event loop, so the client side has to be async too (sync httpx would deadlock the loop)."""),
    code("""from a2a_helpers import fetch_agent_card, print_agent_card, send_message, show_response

print_agent_card(await fetch_agent_card())"""),

    md("""## 6. Delegate the task — one sentence in, one brief out

No tool list, no plan, no orchestration on our side. The agent figures it out internally."""),
    code("""response = await send_message("Analyze NVDA — recent price action, what the company does, and any notable news.")
show_response(response)"""),

    md("""### What just happened — the A2A jump from MCP

You sent **one sentence**. From your side: no tool list, no plan, no loop.

The reply has two parts:

- An **"Internal trace"** block at the top — captured by `trace=trace` in `StockAnalystExecutor.execute()` (cell 2 above).
- The actual brief below.

Look at the trace: the analyst called `get_quote`, then `get_history`, then `get_company_info`, then `get_news_headlines` — all on the stock MCP server, all decided by the analyst's own LLM. **None of that orchestration lives in this notebook's client-side code.**

That is the architectural shift A2A unlocks: the *callee* is a smart agent in its own right. In MCP your notebook's LLM was the orchestrator; here the LLM lives inside the executor we just defined, behind one HTTP call.

(In principle, an A2A agent can also call other A2A agents internally. The protocol does not prevent loops — depth limits, timeouts, and budgets are application concerns.)"""),

    md("""## 7. Raw JSON-RPC envelope (optional)

Note `result.kind` and `result.status` — A2A models every call as a task with a lifecycle."""),
    code("""show_response(response, raw=True)"""),

    md("""## 8. Stop the agent"""),
    code("""server.should_exit = True
await asyncio.sleep(1)
agent_task.cancel()
print("agent stopped")"""),
]

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

**Scenario:** an equity analyst entity needs sector context. It **discovers** a macro analyst on the network — without being told its URL — sends a delegated question, and weaves the response into its brief.

```
                    ┌────────────────┐
                    │   CloudHost    │   relay (no entities of its own)
                    └────┬───────┬───┘
              parent     │       │     parent
                  ┌──────┘       └────────┐
            ┌─────┴────────┐         ┌────┴───────┐
            │  EquityHost  │         │  MacroHost │
            │              │         │            │
            │  alice ──┐   │         │  Macro     │
            │          ▼   │         │  Analyst   │
            │   Equity     │         │            │
            │   Analyst ───┼─────────┼──►  ◀──┐   │
            │              │         │        │   │
            │              │         │   reply│   │
            │   ◄──────────┼─────────┼────────┘   │
            └──────────────┘         └────────────┘

   1. alice → EquityAnalyst:      "Analyze NVDA, include sector context"
   2. EquityAnalyst (LLM loop) → fetches NVDA via stock MCP
   3. EquityAnalyst → host.get_discoverable_entities(include_parent=True)
                       finds MacroAnalyst on MacroHost
   4. EquityAnalyst → MacroAnalyst (cross-host INVOKE through CloudHost)
   5. MacroAnalyst (LLM loop) → returns sector outlook
   6. EquityAnalyst → weaves both into a brief → alice
```

**Protocol stack — three layers nested:**

```
   alice (FA HUMAN entity)
        │  FA protocol  (Entity-ID addressed, host-routed)
        ▼
   ┌─────────────────────────────────────────────────────────┐
   │  EquityAnalyst  (FA AGENT entity, EquityHost)           │
   │                                                         │
   │  internal Claude loop (Anthropic SDK)                   │
   │     │                                                   │
   │     │  MCP (stdio) ──► stock_mcp_server.py              │
   │     │                                                   │
   │     │  FA delegate tool ──► routes to MacroAnalyst:     │
   │     │  ┌────────────────────────────────────────────┐   │
   │     │  │ MacroAnalyst (FA AGENT entity, MacroHost)  │   │
   │     │  │   internal Claude loop                     │   │
   │     │  │      MCP (stdio) ──► stock_mcp_server.py   │   │
   │     │  │      sector outlook → reply via FA         │   │
   │     │  └────────────────────────────────────────────┘   │
   └─────────────────────────────────────────────────────────┘
        │
        ▼  combined brief
   alice (receives it)
```

**Three protocols are running together in this single demo:** FA routes between entities, each entity contains an A2A-style internal loop, and that loop calls MCP tools. *That's why FA / A2A / MCP are complementary, not competing.*

A2A would require alice (or the equity analyst) to know each callee's URL up front. Here the network has a directory of public entities, and `host.get_discoverable_entities(include_parent=True)` returns cards across hosts.

""" + SETUP_COMMON + """

Demo 3 also needs the FA reference implementation, [`ai-link-net`](https://github.com/FoundationAgents/ai-link-net). It will be released soon. Once it is available, clone it next to this repo:

```bash
cd ..
git clone https://github.com/FoundationAgents/ai-link-net.git
cd ivado-protocol
```

The install cell below will use that local clone, or install from GitHub if it is already public."""),
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

`fp/` is the protocol layer; `aln/` provides `MCPHandler`. Patch `fp/Host` so `TOOL` entities resolve to `MCPHandler`. Silence logs and skip disk persistence for the demo."""),
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
    md("""## 1. The system prompts and tool schemas

Both analysts have their behaviour set by a system prompt. The equity analyst gets two extra tools (`list_network_specialists`, `delegate_to_specialist`) that let it discover and call other agents on the network.

**Notice the tools are completely generic — no `"macro"` anywhere.** Discovery happens at runtime by reading entity descriptions."""),
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

    md("""## 2. The macro analyst — `make_macro_analyst(host)`

Just an LLM-loop entity on its own host. It receives an INVOKE, runs Claude with the stock MCP server, replies."""),
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

    md("""## 3. The equity analyst — `make_equity_analyst(host)`

This one has the discovery logic. **Read these three pieces:**

- `_list_specialists()` — calls `host.get_discoverable_entities(include_parent=True)` and returns the list with descriptions. **Prints what it returns** so the demo audience sees the discovery happening.
- `_ask(entity_id, question)` — sends an INVOKE to whichever entity_id Claude picked, awaits the reply via the queue.
- `handler()` — routes incoming messages: a reply from a specialist we are waiting on goes into the delegate queue; anything else is a new user query."""),
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

    md("""## 4. Build the network: 3 hosts, 3 entities

Two leaf hosts under a relay. Macro on `MacroHost`, equity + alice on `EquityHost`. **Alice has no idea macro exists** — equity will find it at query time."""),
    code("""cloud = Host(name="CloudHost")
host_a = Host(name="EquityHost", port=18101)
host_b = Host(name="MacroHost",  port=18102)
host_a.set_parent_host(cloud)
host_b.set_parent_host(cloud)

# Macro analyst on host_b (will be discovered, not pre-configured)
macro = make_macro_analyst(host_b)

# Equity analyst on host_a — looks up macro at query time
equity = make_equity_analyst(host_a)

# Alice (the user) on host_a
alice_inbox: asyncio.Queue[Message] = asyncio.Queue()
async def alice_handler(msg):
    if msg.kind not in FRIEND_KINDS:
        await alice_inbox.put(msg)
alice = host_a.register_entity("alice", kind=EntityKind.HUMAN, handler=alice_handler)

print(f"{alice.name:<14}  {alice.address.address}")
print(f"{equity.name:<14}  {equity.address.address}")
print(f"{macro.name:<14}  {macro.address.address}")"""),
    md("""## 5. Discovery — the FA-only primitive

`host.get_discoverable_entities(include_parent=True)` walks the federation tree (own host + parent + parent's other children) and returns every public entity's `EntityCard`. **No URL or hostname was pre-configured.**

This is the API that A2A doesn't have. In A2A, to call an agent you must already know its URL (or run an external registry yourself).

In a moment the equity analyst will use exactly this API (inside `_list_specialists` from cell 3) — but instead of looking for a hardcoded name, it gives the resulting list to its own Claude and lets Claude pick a specialist by description."""),
    code("""for card in host_a.get_discoverable_entities(include_parent=True):
    print(f"{card.name:<14}  {card.address.address}  (kind={card.kind})")
    print(f"    description: {card.description}")"""),
    md("""## 6. Friend handshake (alice ↔ equity)

The equity ↔ macro handshake happens lazily inside `_ask` (cell 3) on the first delegation call."""),
    code("""await alice.send_message(
    to=equity.entity_card,
    message=Message(kind=MessageKind.FRIEND_REQUEST,
                    payload=FriendRequestPayload(sender_card=alice.entity_card)),
)
await asyncio.sleep(0.5)
print("alice friends:", list(alice.friends.keys()))"""),
    md("""## 7. Alice asks one question

The equity analyst now does **real discovery**:

1. fetches NVDA data with the stock-MCP tools,
2. decides sector context would help,
3. calls `list_network_specialists` — the host returns the list of public agents,
4. **its own Claude reads each entity's `description`** and picks the one whose stated expertise matches (the macro analyst, here, but the equity analyst was never told that name),
5. calls `delegate_to_specialist(entity_id, question)` — message is routed `EquityHost → CloudHost → MacroHost`,
6. weaves the macro reply into a final brief.

Watch the printed trace below — you'll see the `[equity → discovery]` and `[equity → delegation]` lines as Claude makes the two calls."""),
    code("""await alice.send_message(
    to=equity.entity_card,
    message=Message(
        kind=MessageKind.INVOKE,
        payload={"text": "Analyze NVDA briefly. Include sector context."},
    ),
)
reply = await asyncio.wait_for(alice_inbox.get(), timeout=300)
print(reply.payload["text"])"""),
    md("""### What just happened — the FA jump from A2A

Look for a **"Sector Context"** section in the brief above. That section's content was written by the macro analyst on `MacroHost`, not by the equity analyst on `EquityHost`. It travelled `MacroHost → CloudHost → EquityHost`, end-to-end.

And look at the `[equity → discovery]` line above — the equity analyst's Claude saw a list of agents and **chose** the macro one based on the description string. **No agent name was hardcoded in the equity-side code.** Re-running with a different specialist (say, a "geopolitics analyst" with a different description) would just work.

Three FA primitives all came together here:

- **Discovery** — `host.get_discoverable_entities(include_parent=True)` returns EntityCards from across the network; the equity analyst's LLM picks one based on `description`.
- **Entity-ID addressing** — `delegate_to_specialist` takes an `entity_id`, not a URL. The recipient can move to a new host or machine; the call still resolves.
- **Cross-host routing** — `CloudHost` relayed the messages; neither host had the other's IP hardcoded.

In A2A, all three would have to be solved with external infrastructure. In FA, they are part of the protocol."""),

    md("""## 8. Bonus — offline delivery

A2A requires the recipient to be online when you call: send a request to a server that is down and the call **fails**. FA's design instead lets messages **queue** at the host (or at the entity) until the recipient comes back, then deliver them.

In our small in-process setup we don't get the full `HostServer` mailbox machinery, so we show the **same pattern at the entity layer**: a small worker entity with an `online` toggle. When offline, its handler buffers incoming messages locally; when toggled back online, the buffer is drained and processed normally.

In production with `HostServer` this happens automatically at the host boundary — same idea, just protocol-level instead of in our handler."""),
    code("""# A worker entity with a manual online/offline toggle.
# Pattern: when offline, the handler buffers messages; when online, it drains.

def make_offline_capable_worker(host, name="SlowWorker"):
    state = {"entity": None, "online": True, "pending": []}

    async def _process(sender_addr, msg):
        question = _payload_text(msg)
        # Pretend to do real work
        await asyncio.sleep(0.5)
        result = f"Processed: {question!r}"
        await state["entity"].send_message(
            to=FPAddress(address=sender_addr),
            message=Message(kind=MessageKind.INVOKE, payload={"text": result}),
        )

    async def handler(msg):
        if msg.kind in FRIEND_KINDS: return
        sender_addr = msg.metadata.get("sender_address", "")
        if not sender_addr: return
        if state["online"]:
            asyncio.create_task(_process(sender_addr, msg))
        else:
            state["pending"].append((sender_addr, msg))
            print(f"  [{name} OFFLINE] queued; pending = {len(state['pending'])}")

    async def go_offline():
        state["online"] = False
        print(f"  [{name}] now OFFLINE — incoming messages will be queued")

    async def come_back_online():
        state["online"] = True
        pending = state["pending"][:]
        state["pending"].clear()
        print(f"  [{name}] back ONLINE — draining {len(pending)} queued messages")
        for sender_addr, msg in pending:
            asyncio.create_task(_process(sender_addr, msg))

    entity = host.register_entity(
        name=name, kind=EntityKind.AGENT, is_public=True,
        description="Demo worker with offline toggle.",
        handler=handler,
    )
    state["entity"] = entity
    return entity, go_offline, come_back_online


worker, go_offline, come_back_online = make_offline_capable_worker(host_a)

# alice friends the worker
await alice.send_message(
    to=worker.entity_card,
    message=Message(kind=MessageKind.FRIEND_REQUEST,
                    payload=FriendRequestPayload(sender_card=alice.entity_card)),
)
await asyncio.sleep(0.4)
print(f"worker registered: {worker.address.address}")"""),

    md("""### Take the worker offline, then send 3 messages

Each message is buffered. Nothing is processed yet."""),
    code("""await go_offline()

for i in range(3):
    await alice.send_message(
        to=worker.entity_card,
        message=Message(kind=MessageKind.INVOKE, payload={"text": f"task #{i+1}"}),
    )

await asyncio.sleep(1.0)
print(f"alice received so far: {alice_inbox.qsize()} replies "
      f"(should be 0 — worker is offline)")"""),

    md("""### Bring the worker back online → buffer drains → replies arrive

The worker's queued messages are processed and the replies flow back to alice — even though alice never re-sent anything."""),
    code("""await come_back_online()

# Collect the 3 replies that the worker now produces
for _ in range(3):
    reply = await asyncio.wait_for(alice_inbox.get(), timeout=10)
    print(f"  alice ← {reply.payload['text']}")"""),

    md("""### What just happened

- alice sent 3 messages while the worker was offline → none failed; all queued.
- The worker came back online → drained the queue → produced replies → routed back to alice through the host network.
- alice's code did **not** know the worker was ever offline. From her side, the messages were sent, and after a delay, the replies came back.

This is FA's **offline-delivery pattern**: addressing by Entity ID + a queue that survives the recipient's downtime. In A2A you would have gotten a connection refused / timeout when the recipient was down, and your code would have to handle retry on its own.

(For a full implementation, FA's `HostServer` does this queueing at the host boundary — including across host restarts — without requiring per-entity code.)"""),

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

DEMO3_DIR.mkdir(exist_ok=True)
(DEMO3_DIR / "03_fa_demo.ipynb").write_text(json.dumps(notebook(fa_cells), indent=1, ensure_ascii=False))
print("wrote demo3_fa/03_fa_demo.ipynb")
