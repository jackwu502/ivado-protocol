"""A2A 'Stock Analyst' agent.

Used by Demo 2 (`demo2_a2a/02_a2a_demo.ipynb`).

Run directly:  python analyst_agent.py
The agent listens on http://localhost:9999 and exposes:
  - GET  /.well-known/agent-card.json  (self-description)
  - POST /                              (JSON-RPC: message/send)

Internally it uses Claude plus the shared/stock_mcp_server.py to
answer high-level questions like "Analyze NVDA". The caller does not
need to know which tools to invoke — the agent plans, fetches, and
writes a brief.
"""

import sys
from pathlib import Path

# Allow `from shared.X import Y` when this file runs as a standalone script.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message

from shared.agent_runner import run_agent

STOCK_MCP_SERVER = str(_PROJECT_ROOT / "shared" / "stock_mcp_server.py")


SYSTEM_PROMPT = """You are an equity analyst.
When given a ticker or a high-level question, plan and fetch the data you
need (recent quote, price history, company info, news), then write a
concise brief: where the stock is, how it has moved, what the company does,
and what notable news may explain the move. Use the tools available."""


class StockAnalystExecutor(AgentExecutor):
    """The brain of the agent: receives a task and produces a written brief."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        question = context.get_user_input() or "Analyze the market."
        try:
            answer = await run_agent(
                question=question,
                mcp_servers=[STOCK_MCP_SERVER],
                system_prompt=SYSTEM_PROMPT,
            )
        except Exception as exc:
            answer = f"(analyst error: {exc})"
        await event_queue.enqueue_event(new_agent_text_message(answer))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError("cancel not supported in this demo")


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


if __name__ == "__main__":
    import uvicorn

    handler = DefaultRequestHandler(
        agent_executor=StockAnalystExecutor(),
        task_store=InMemoryTaskStore(),
    )
    app = A2AStarletteApplication(agent_card=build_agent_card(), http_handler=handler)
    uvicorn.run(app.build(), host="0.0.0.0", port=9999, log_level="warning")
