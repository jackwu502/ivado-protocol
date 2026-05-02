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

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# FA demo — clone and install ai-link-net
git clone https://github.com/FoundationAgents/ai-link-net.git
pip install -e ./ai-link-net
# (Once the repo is public, this works directly:
#   pip install git+https://github.com/FoundationAgents/ai-link-net.git )

# LLM credentials in .env (see .env.example for both Anthropic-direct and
# OpenRouter routes). The agentic loop uses ANTHROPIC_API_KEY plus the
# optional ANTHROPIC_BASE_URL and ANTHROPIC_MODEL.

jupyter lab
```

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
