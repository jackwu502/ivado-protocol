"""FA Entity factories used by Demo 3.

Two analyst entities, each with a Claude loop inside:

  * `make_macro_analyst(host)` — answers a sector / macro question.
  * `make_equity_analyst(host)` — answers an equity question, with the
    option to delegate sector questions to the macro analyst it discovers
    through the FA network.

Each handler distinguishes incoming messages by sender:
  * Reply from the macro analyst → routed to a delegate queue.
  * Anything else from someone we know → treated as a fresh user query.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

# Allow `from shared.X import Y` when this module is imported from a notebook
# whose cwd is demo3_fa/.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fp import Message, MessageKind
from fp.core.base import EntityKind
from fp.core.wellknown import FPAddress
from fp.message import FriendRequestPayload

from shared.agent_runner import run_agent

STOCK_MCP_SERVER = str(_PROJECT_ROOT / "shared" / "stock_mcp_server.py")

FRIEND_KINDS = {MessageKind.FRIEND_REQUEST, MessageKind.FRIEND_ACCEPT, MessageKind.FRIEND_REJECT}

MACRO_SYSTEM_PROMPT = (
    "You are a macro / sector analyst. Given a sector or thematic question, "
    "answer concisely (2-3 sentences) using the available stock-data tools "
    "if helpful. Do not produce long reports."
)

EQUITY_SYSTEM_PROMPT = (
    "You are an equity analyst writing a brief on a single stock. Use the "
    "stock-data tools to fetch price action, company info, and news. If "
    "sector or macro context would inform your brief, call "
    "`ask_macro_analyst` ONCE for it. Then write a concise brief."
)

DELEGATE_TOOL = {
    "name": "ask_macro_analyst",
    "description": (
        "Ask the macro/sector analyst on the network for sector or thematic "
        "context. Use at most once per brief."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "Plain-English question about the sector or macro context.",
            }
        },
        "required": ["question"],
    },
}


def _payload_text(msg: Message) -> str:
    p = msg.payload
    if isinstance(p, dict):
        return p.get("text") or p.get("question") or ""
    return getattr(p, "text", "") or ""


def make_macro_analyst(host: Any, name: str = "MacroAnalyst") -> Any:
    """Register a macro analyst entity on `host` and return it."""
    state: dict[str, Any] = {}

    async def _handle_query(sender_addr: str, msg: Message) -> None:
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

    async def handler(msg: Message) -> None:
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
    return entity


def make_equity_analyst(host: Any, name: str = "EquityAnalyst") -> Any:
    """Register an equity analyst entity on `host` and return it.

    The entity discovers and calls `MacroAnalyst` lazily: at the time of
    the first query, it walks the network with
    `host.get_discoverable_entities(include_parent=True)`.
    """
    state: dict[str, Any] = {"macro_card": None, "pending_macro_queue": None}

    def _find_macro() -> Any:
        if state["macro_card"] is not None:
            return state["macro_card"]
        for card in host.get_discoverable_entities(include_parent=True):
            if card.name == "MacroAnalyst":
                state["macro_card"] = card
                return card
        return None

    async def _delegate(name_: str, args: dict[str, Any]) -> str:
        if name_ != "ask_macro_analyst":
            return f"(unknown tool: {name_})"
        macro_card = _find_macro()
        if macro_card is None:
            return "(macro analyst not found on the network)"

        # Friend handshake on first contact (auto-accepted by default)
        if macro_card.address.entity_uid not in state["entity"].friends:
            await state["entity"].send_message(
                to=macro_card,
                message=Message(
                    kind=MessageKind.FRIEND_REQUEST,
                    payload=FriendRequestPayload(sender_card=state["entity"].entity_card),
                ),
            )
            await asyncio.sleep(0.5)

        queue: asyncio.Queue[Message] = asyncio.Queue()
        state["pending_macro_queue"] = queue
        await state["entity"].send_message(
            to=macro_card,
            message=Message(kind=MessageKind.INVOKE, payload={"text": args["question"]}),
        )
        try:
            reply = await asyncio.wait_for(queue.get(), timeout=120)
            return _payload_text(reply) or "(empty reply)"
        finally:
            state["pending_macro_queue"] = None

    async def _handle_query(sender_addr: str, msg: Message) -> None:
        question = _payload_text(msg)
        try:
            answer = await run_agent(
                question=question,
                mcp_servers=[STOCK_MCP_SERVER],
                system_prompt=EQUITY_SYSTEM_PROMPT,
                extra_tools=[DELEGATE_TOOL],
                extra_tool_executor=_delegate,
            )
        except Exception as exc:
            answer = f"(equity analyst error: {exc})"
        await state["entity"].send_message(
            to=FPAddress(address=sender_addr),
            message=Message(kind=MessageKind.INVOKE, payload={"text": answer}),
        )

    async def handler(msg: Message) -> None:
        if msg.kind in FRIEND_KINDS:
            return
        sender_addr = msg.metadata.get("sender_address", "")
        if not sender_addr:
            return
        # Reply from macro → push to the delegate queue
        macro_card = state["macro_card"]
        if (
            macro_card is not None
            and sender_addr == macro_card.address.address
            and state["pending_macro_queue"] is not None
        ):
            await state["pending_macro_queue"].put(msg)
            return
        # Anything else: a fresh user query
        asyncio.create_task(_handle_query(sender_addr, msg))

    entity = host.register_entity(
        name=name,
        kind=EntityKind.AGENT,
        is_public=True,
        description="Equity analyst that delegates sector questions to a macro analyst on the network.",
        handler=handler,
    )
    state["entity"] = entity
    return entity
