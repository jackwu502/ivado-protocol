# Agent Protocols Hands-on Lab

A ~40-minute hands-on session introducing three agent protocols: **MCP**, **A2A**, and **FA**.
Audience: statistics faculty and students.

## Agenda

| # | Topic | Time | File |
|---|-------|------|------|
| 0 | Concepts | 10 min | [`slides.pptx`](slides.pptx) |
| 1 | MCP — Claude with stock-data + plotting tools | ~10 min | [`demo1_mcp/01_mcp_demo.ipynb`](demo1_mcp/01_mcp_demo.ipynb) |
| 2 | A2A — delegate "Analyze NVDA" to an analyst agent | ~10 min | [`demo2_a2a/02_a2a_demo.ipynb`](demo2_a2a/02_a2a_demo.ipynb) |
| 3 | FA — equity analyst discovers and calls a macro analyst on another host | ~10 min | [`demo3_fa/03_fa_demo.ipynb`](demo3_fa/03_fa_demo.ipynb) |

Each demo does something the previous protocol cannot do well: MCP gives the LLM tools, A2A delegates to a smart agent, and FA adds cross-host discovery.

FA is developed by **DeepWisdom**, with our group as a research collaborator.

## Setup

Requires **Python 3.12+** (FA / `ai-link-net` constraint).

Clone the repo and create a local virtual environment:

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

Demo 3 also needs the FA reference implementation, [`ai-link-net`](https://github.com/FoundationAgents/ai-link-net). It will be released soon. Once it is available, clone it next to this repo:

```bash
cd ..
git clone https://github.com/FoundationAgents/ai-link-net.git
cd ivado-protocol
```

The Demo 3 install cell will use that local clone, or install from GitHub if it is already public.

## Slides

Use [`slides.pptx`](slides.pptx) for the concept section. The notebook demos are self-contained and can be run directly after setup.

`slides.md` is an older Marp markdown version, kept for quick textual reference.

## Files

Each demo lives in its own folder so it is obvious which file belongs where. Code shared by multiple demos lives under `shared/`.

```
ivado-protocol/
├── slides.pptx                            # 10-slide deck
├── slides.md                              # older Marp reference version
├── README.md
├── requirements.txt
├── .env / .gitignore                      # .env holds API keys (gitignored)
├── _build_notebooks.py                    # regenerates the notebooks below
│
├── shared/                                # used by 2 or more demos
│   ├── stock_mcp_server.py                # yfinance-backed MCP tools (all demos)
│   └── agent_runner.py                    # reusable Claude + MCP agentic loop (demos 2, 3)
│
├── demo1_mcp/
│   ├── 01_mcp_demo.ipynb                  # the notebook
│   ├── viz_mcp_server.py                  # plotting MCP tools
│   └── mcp_helpers.py                     # MCP client plumbing for the notebook
│
├── demo2_a2a/
│   ├── 02_a2a_demo.ipynb
│   ├── analyst_agent.py                   # A2A smart-analyst server
│   └── a2a_helpers.py                     # A2A client plumbing
│
└── demo3_fa/
    ├── 03_fa_demo.ipynb
    └── fa_analysts.py                     # equity + macro FA entity factories
```

Each notebook starts with a small bootstrap cell that adds the project root to `sys.path` (so `from shared.X import Y` works) and sets `STOCK_MCP_SERVER` to the absolute path of the shared MCP server. Run Jupyter from the project root.

## Running example

All three demos work on the same input — a single stock (`NVDA`) — to make the protocol differences visible:

- **Demo 1 (MCP):** the user gives Claude a question and Claude orchestrates tool calls (`get_history`, `line_chart`).
- **Demo 2 (A2A):** the user sends *one sentence* to a standalone analyst agent that internally runs the loop and returns a brief.
- **Demo 3 (FA):** the equity analyst entity discovers a macro analyst on another host and delegates the sector question to it, producing a brief that combines both.

The stock data comes from [`yfinance`](https://github.com/ranaroussi/yfinance) (no API key required). For production, swap to a company-maintained MCP server such as [Alpha Vantage's official one](https://mcp.alphavantage.co/).
