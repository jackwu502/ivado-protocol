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
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


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

## First-time setup

Run once in a terminal:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install jupyterlab
jupyter lab
```

Set the LLM credentials in `.env` (project root). Two options:
- **Anthropic direct:** `ANTHROPIC_API_KEY=sk-ant-...`, `ANTHROPIC_MODEL=claude-sonnet-4-6`
- **OpenRouter (cheaper):** `ANTHROPIC_BASE_URL=https://openrouter.ai/api`, `ANTHROPIC_API_KEY=sk-or-v1-...`, `ANTHROPIC_MODEL=anthropic/claude-sonnet-4.5`"""),
    code(BOOTSTRAP_COMMON + 'VIZ_MCP_SERVER = str(HERE / "viz_mcp_server.py")\n'),
    code("""%pip install -q mcp anthropic yfinance matplotlib python-dotenv

import os
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

if not os.getenv("ANTHROPIC_API_KEY"):
    print("Note: ANTHROPIC_API_KEY not set in .env — the final 'hand to Claude' cell will skip.")
else:
    print(f"ready  (model={os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-6')})")"""),
    md("""## List tools"""),
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
]

DEMO1_DIR.mkdir(exist_ok=True)
(DEMO1_DIR / "01_mcp_demo.ipynb").write_text(json.dumps(notebook(mcp_cells), indent=1, ensure_ascii=False))
print("wrote demo1_mcp/01_mcp_demo.ipynb")


# ============================================================================
# 02 — A2A demo
# ============================================================================
a2a_cells = [
    md("""# Demo 2 — A2A

**What changes from Demo 1:** the agentic loop moves *inside* an agent we can call over HTTP. The caller sends one sentence; the agent plans, fetches, writes a brief.

```
   you (this notebook)
        │  one sentence ("Analyze NVDA ...")
        │  HTTP + JSON-RPC
        ▼
   ┌─────────────────────────────────────┐
   │  analyst_agent.py  (A2A server)     │
   │  port 9999                          │
   │                                     │
   │   internal Claude loop ──┐          │
   │                          │          │
   │                          ▼          │
   │   stock_mcp_server.py (subprocess)  │
   └─────────────────────────────────────┘
        │
        ▼  written brief
   you (notebook prints it)
```

Agent: [`analyst_agent.py`](analyst_agent.py) — A2A server with an internal Claude + stock-MCP loop
Helpers: [`a2a_helpers.py`](a2a_helpers.py)

## First-time setup

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install jupyterlab
jupyter lab
```

Use the same `.env` from Demo 1 (the agent reads `ANTHROPIC_*` to call Claude internally)."""),
    code(BOOTSTRAP_COMMON),
    code("""%pip install -q "a2a-sdk<1.0" uvicorn httpx anthropic mcp yfinance python-dotenv

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")
print("ready")"""),
    md("""## Agent card

Self-description served at `/.well-known/agent-card.json`. Any A2A client can discover this agent through it."""),
    code("""from analyst_agent import build_agent_card
print(build_agent_card().model_dump_json(indent=2, exclude_none=True))"""),
    md("""## Start the agent (port 9999)"""),
    code("""from a2a_helpers import (
    start_agent, stop_agent, fetch_agent_card,
    print_agent_card, send_message, show_response,
)

agent = start_agent(str(HERE / "analyst_agent.py"))"""),
    md("""## Discover it over HTTP"""),
    code("""print_agent_card(fetch_agent_card())"""),
    md("""## Delegate a high-level task

We send **one sentence** — no tool list, no plan. The agent's internal Claude loop figures out which data to fetch and how to summarize."""),
    code("""response = send_message("Analyze NVDA — recent price action, what the company does, and any notable news.")
show_response(response)"""),
    md("""## Raw JSON-RPC envelope (optional)

Note `result.kind` and `result.status` — A2A models every call as a task with a lifecycle."""),
    code("""show_response(response, raw=True)"""),
    code("""stop_agent(agent)"""),
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

A2A would require alice (or the equity analyst) to know each callee's URL up front. Here the network has a directory of public entities, and `host.get_discoverable_entities(include_parent=True)` returns cards across hosts."""),
    md("""## First-time setup

If you have not done these once already, run them in a terminal (not in the notebook):

```bash
# 1. Create and activate a Python 3.12 environment (required for ai-link-net)
python3.12 -m venv .venv && source .venv/bin/activate

# 2. Install Jupyter and start it
pip install jupyterlab
jupyter lab

# 3. If ai-link-net is private for your account, clone it next to this repo
#    or set ALN_LOCAL_PATH to your local clone. If it is public, the install
#    cell below can fetch it from GitHub directly.
git clone https://github.com/FoundationAgents/ai-link-net.git
```

Then open this notebook and run the install cell below."""),
    code(BOOTSTRAP_COMMON),
    code(f"""assert sys.version_info >= (3, 12), "ai-link-net needs Python 3.12+"

# Dependencies for the wrapped MCP server and the analyst loop
%pip install -q mcp anthropic yfinance python-dotenv

import importlib.util
import os
import subprocess

def _have_ai_link_net():
    return importlib.util.find_spec("fp") is not None and importlib.util.find_spec("aln") is not None

def _pip_install(*args):
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *args])

if _have_ai_link_net():
    print("ai-link-net already importable")
else:
    candidates = []
    if os.getenv("ALN_LOCAL_PATH"):
        candidates.append(Path(os.environ["ALN_LOCAL_PATH"]).expanduser())
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
    md("""## Set up the network

Two hosts under a relay. The equity analyst lives with alice on `EquityHost`; the macro analyst lives on `MacroHost`. Alice does not know macro exists yet — equity will discover it at query time."""),
    code("""from fp import Host, Message, MessageKind
from fp.core.base import EntityKind
from fp.message import FriendRequestPayload
from fa_analysts import make_equity_analyst, make_macro_analyst, FRIEND_KINDS

cloud = Host(name="CloudHost")
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
    md("""## Discovery

The equity analyst's host walks the federation tree and lists every public entity it can see — including the macro analyst on the other host. **No URL was pre-configured.**"""),
    code("""for card in host_a.get_discoverable_entities(include_parent=True):
    print(f"{card.name:<14}  {card.address.address}  (kind={card.kind})")"""),
    md("""## Friend handshake (alice ↔ equity)

The equity ↔ macro handshake happens lazily on the first delegation call inside `make_equity_analyst`."""),
    code("""await alice.send_message(
    to=equity.entity_card,
    message=Message(kind=MessageKind.FRIEND_REQUEST,
                    payload=FriendRequestPayload(sender_card=alice.entity_card)),
)
await asyncio.sleep(0.5)
print("alice friends:", list(alice.friends.keys()))"""),
    md("""## Alice asks one question

The equity analyst plans, fetches NVDA data, decides sector context would help, and **delegates to the macro analyst it discovered** — across hosts, through the relay. The macro analyst replies; the equity analyst combines and returns its brief."""),
    code("""await alice.send_message(
    to=equity.entity_card,
    message=Message(
        kind=MessageKind.INVOKE,
        payload={"text": "Analyze NVDA briefly. Include sector context."},
    ),
)
reply = await asyncio.wait_for(alice_inbox.get(), timeout=300)
print(reply.payload["text"])"""),
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
