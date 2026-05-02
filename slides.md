---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  section {
    font-size: 26px;
    padding: 50px 70px;
  }
  h1 { color: #1a4d8f; }
  h2 { color: #1a4d8f; border-bottom: 2px solid #1a4d8f; padding-bottom: 6px; }
  code { background: #f0f4f8; padding: 2px 6px; border-radius: 3px; }
  table { font-size: 22px; }
  .small { font-size: 20px; color: #555; }
  .center { text-align: center; }
---

<!-- _class: lead -->

# Agent Protocols Hands-on Lab

<br>

**MCP · A2A · FA**

<br>

<span class="small">IVADO · Statistics Lab Session · 2026</span>

<!--
Welcome. We have ~40 minutes. About 10 minutes of concepts up front, then three short hands-on demos in Jupyter — roughly 10 minutes each. The whole lab is built around one running example: asking an agent about a stock. We use the same input under three different protocols so the differences are visible.

If you have questions, interrupt at any time. The notebooks and slides will be on the shared drive after the session.
-->

---

## What is an LLM agent?

```
              ┌────────────────────┐
   user ───►  │   LLM (reason/plan) │  ───► answer
              └─────────┬──────────┘
                        │  tool_use
                        ▼
              ┌────────────────────┐
              │  Tools / Data /     │
              │  Other Agents       │
              └────────────────────┘
```

**LLM + tools + state + an autonomous decision loop.**

<!--
An LLM agent is not just a chatbot. The model decides what to do next: it can call a function, query a database, ask another agent. That decision loop is the difference between "chat" and "agent."

For our purposes today, "agent" means: an LLM that calls external tools to get its job done. Once you accept that, the question becomes: what's the standard way for the LLM to talk to those tools, and what's the standard way for tools (or other agents) to be discovered and called?
-->

---

## Why protocols?

Without standards: **M × N glue layers.** Every framework × every tool, rewritten.

| Problem | Consequence |
|---------|-------------|
| No common interface | Switch frameworks → rewrite every tool |
| No standard schema | Tool descriptions hard-coded into prompts |
| No agent-to-agent calling | Multi-agent systems stuck in one process |

> A standard interface lets any client talk to any server, with no per-pair glue.

<!--
Anyone who has built integrations recognizes this pattern. You write a connector for tool A in framework X. Then framework Y comes out and you rewrite. Then tool B is added and you rewrite for both frameworks. M × N.

Protocols solve M × N by introducing a common bus. Tool authors write once. Framework authors write once. Everyone else benefits. The classic analogy is the international electrical socket — any appliance plugs in.

The three protocols today each address a different scope of this problem.
-->

---

## The three protocols today

| Protocol | Author | Connects |
|----------|--------|----------|
| **MCP** (Model Context Protocol) | Anthropic | Agent ↔ **tools / data** |
| **A2A** (Agent-to-Agent) | Google | Agent ↔ **Agent** |
| **FA** (Foundation Agents Protocol) | DeepWisdom (collaborator) | **Humans / Agents / Tools / Services** |

<br>

The scope grows from left to right.

<!--
MCP is the narrowest and most established — it standardizes how a single LLM reaches external tools. Anthropic released it in late 2024 and the ecosystem has roughly 100 million installs by early 2026.

A2A came from Google in 2025. It standardizes the protocol when the callee is itself an agent — meaning, it has its own LLM and decides things on its own — rather than a stateless tool.

FA is the broadest. It's developed by DeepWisdom, with our group as a research collaborator. It treats humans, agents, tools, and services as members of a single network with persistent identity and discovery built in.

We will see what each one can do that the previous one cannot — that's the through-line of the lab.
-->

---

## MCP — concept

```
┌──────────┐   JSON-RPC over stdio/HTTP    ┌──────────────┐
│  Host    │ ◄────────────────────────► │  MCP Server   │
│ (Claude) │                              │ (your tools)  │
└──────────┘                              └──────────────┘
```

- **Tools** — functions the LLM can call
- **Resources** — data the LLM can read
- **Prompts** — server-side prompt templates

<!--
MCP is a protocol between an LLM host (Claude Desktop, Cursor, your own Jupyter notebook running the Anthropic SDK) and a tool server. The wire format is JSON-RPC 2.0 over either stdio (a subprocess) or HTTP.

A tool server exposes three kinds of things: tools (functions the LLM can call), resources (data the LLM can read passively), and prompts (server-side templates). For this lab we focus on tools.

The key benefit: write a tool server once and any MCP-aware client can use it. Today that includes Claude Desktop, Cursor, Continue, the Anthropic and OpenAI SDKs, and dozens of community hosts.
-->

---

## MCP — when to use it

- You want an LLM to reach a database, an R script, or an internal API
- You want one tool to be reusable across Claude Desktop, Cursor, your own Jupyter
- You want type-safe tool schemas auto-generated from your code

> Mental model: **the LLM is the calculator's user; MCP is the calculator's keypad.**

<!--
The use case is wherever you want an LLM to call into a system you control. Your lab has a SAS pipeline? Wrap it with MCP. Your team uses an internal API? Wrap it with MCP. The LLM doesn't care what's behind the protocol — it sees a list of tools.

The mental model: think of the LLM as the user of a calculator. MCP is the keypad. The keys are buttons the LLM can press. The protocol defines what each button does and how to label it.
-->

---

## A2A — concept

```
   Agent A   ◄── HTTP + JSON-RPC ──►   Agent B
   (caller)                            (analyst)

   Each agent serves /.well-known/agent-card.json
   describing skills, modalities, endpoint.
```

- **Agent Card** — self-description published at a well-known URL
- **Task** — work unit with a lifecycle (`submitted → working → completed`)
- **Message / Artifact** — input / output

<!--
A2A is the protocol when the entity you are calling is itself an agent — meaning it runs its own LLM, has its own memory, and decides for itself how to respond.

Each A2A agent serves a small JSON file at a well-known URL — that's its agent card. The card lists the agent's skills, what input modalities it accepts, and how to call it. Any A2A-aware client reads the card, then sends messages.

A2A also models tasks as first-class. Every call has a task ID and a status. The status walks through submitted, working, then completed or failed. That makes long-running async calls natural — useful when the agent might take minutes to research something.
-->

---

## A2A — when to use it

- The callee should plan and reason on its own (not just expose fixed tools)
- The work is async / long-running — you want a task ID, not a blocking call
- Different teams or organizations own caller and callee

> Mental model: **MCP is a calculator. A2A is a phone call to a colleague.**

<!--
Use A2A when "give the LLM tools" is not enough — when you want to delegate the entire problem to another smart agent. The caller doesn't know what tools the callee uses internally. It says "analyze this stock" and gets back a brief.

Compare to a calculator versus a phone call. With a calculator, you press the buttons. With a phone call, you say "what do you think?" and trust the person on the other end.

A2A is also the right fit when the agent runs in someone else's deployment. You don't have to install their environment; you talk to their HTTP endpoint.
-->

---

## FA — concept

```
              ┌───────────────┐
              │  CloudHost    │   relay
              └──────┬────────┘
            parent   │   parent
        ┌────────────┴────────────┐
   ┌────┴─────┐              ┌────┴─────┐
   │  HostA   │              │  HostB   │
   │  alice,  │              │  Macro   │
   │  Equity  │              │ Analyst  │
   └──────────┘              └──────────┘
```

A network of hosts; entities live on hosts; messages route through the tree.

<!--
FA, formally Foundation Protocol, treats every participant as an entity living on a host. Hosts can connect to a parent host, forming a tree. Messages route through the tree, just like email between mail servers.

The reference implementation is called AI Link Net, distributed as the `aln` CLI. The protocol itself, fp/, is the minimal core. The application layer, aln/, adds CLI tools, a web UI, and integration with MCP and A2A.

The diagram shows three hosts. CloudHost is a pure routing node — it hosts no entities itself, just relays mail. HostA holds alice (a human) and an equity-analyst agent. HostB holds a macro-analyst agent. We will see this exact topology in Demo 3.
-->

---

## FA — additional abstractions

- **Entity** — a network member: HUMAN / AGENT / TOOL / ORG / ARBITER
- **Host** — a node; can be a **pure routing node** with no entities
- **Friend** — persistent relationship between entities (handshake required)
- **Federation** — addressing by **Entity ID** (decoupled from IP / deployment)
- **Trade** — built-in contracts, payments, ratings, arbitration

<br>

> Mental model: **FA is the email / postal system for agents.**

<!--
What FA adds beyond A2A:

Entity types are first class. An entity is HUMAN, AGENT, TOOL, ORG, or ARBITER. Each carries its own identity and keys.

Host is a routing concept. A host can host zero entities — its job is just to route. That gives you natural places to put audit, rate-limiting, or compliance checks.

Friend is a persistent relationship. Two entities have to handshake before they can exchange application messages. That handshake survives across deployments.

Federation means you address by Entity ID, not URL. The underlying machine can change without breaking the address.

Trade primitives — contracts, payments, ratings, arbitration — are part of the protocol, not bolted on per application.

The mental model is the postal system. You have a stable address. Mail queues if you're offline. Mail servers route between organizations. Privacy and audit happen at the relay layer.
-->

---

## Why federate, instead of pure P2P?

**Scenario:** Dr. Lee (McGill) and Dr. Wright (U of T) — their AI assistants need to collaborate.

| | A2A (P2P) | FA (federated) |
|---|---|---|
| Reachability | laptop behind campus firewall: unreachable | host maintains outbound link; agents register on it |
| Identity | URL = identity; new laptop → new URL | **stable Entity ID** |
| Audit / compliance | each agent implements its own | one enforcement point at the campus host |
| Offline | call to offline agent fails | **mailbox queues**; delivered later |
| Privacy | TLS terminates at relays | per-entity keys; relays cannot read content |

<!--
Pure P2P assumes endpoints are equal, reachable, and self-sufficient. The real internet is not P2P — it has DNS, ISPs, mail servers. FA brings that "infrastructure layer" into the agent protocol itself.

Take Dr. Lee at McGill and Dr. Wright at U of T. With A2A, Dr. Lee's agent has to expose an HTTP URL. McGill's firewall blocks inbound — broken. With FA, McGill runs a host that maintains an outbound connection to a hub. Dr. Lee's agent registers on it. Anyone on the network can reach Dr. Lee through that host, no inbound port needed.

Same logic applies to identity, audit, offline delivery, and end-to-end privacy. Each is a real friction point that FA's federation layer addresses.

This isn't a new pattern. It's how we evolved from direct dial-up to email, from ARPANET to the routed Internet. The federation layer is what lets a network scale across organizations and across years.
-->

---

## The three, side by side

| Dimension | MCP | A2A | FA |
|-----------|-----|-----|-----|
| Connects | LLM ↔ tools | Agent ↔ Agent | Humans / Agents / Tools / Services |
| Addressing | tool name | URL (DNS-bound) | **Entity ID** (location-independent) |
| Topology | single host | flat (every agent a leaf) | tree (hosts can be relays) |
| Discovery | client config | Agent Card (URL must be known) | **in-protocol** |
| State | none | task lifecycle | **persistent friend graph + offline mailbox** |
| Encryption | typically TLS | typically TLS | per-entity keys, end-to-end |
| Economy | none | none | **contracts / payments / ratings** |

<!--
Reading across the columns, you can see the scope grow. Some properties — like end-to-end encryption across relays, or in-protocol discovery — are only meaningful once you have a federated topology.

This is also a chooser's table. If you only need an LLM to reach a database, MCP is enough. If you want to delegate a whole task to a remote agent, A2A. If you want a network where agents find each other across organizations, FA.
-->

---

## Each demo adds what the previous protocol cannot do

- **Demo 1 (MCP)** — give an LLM tools to call.
- **Demo 2 (A2A)** — let the *callee* be a smart agent the caller delegates to.
- **Demo 3 (FA)** — let agents on the network **find and call each other** without pre-configured URLs.

<br>

The three are **complementary**, not competing — FA can wrap MCP servers and A2A agents as entity types.

<!--
This is the through-line. Each demo shows one capability that the previous protocol does not have natively.

Demo 1: ask Claude a question, Claude orchestrates the tool calls. The LLM is in charge.

Demo 2: ask one sentence to a smart agent. The agent itself decides which tools to use, in what order, and writes the final answer. Caller does not orchestrate.

Demo 3: ask the equity analyst about NVDA. The equity analyst decides it wants sector context, discovers the macro analyst on the network — without ever being told a URL — and delegates that part. Combines and answers.

The point is not that A2A "cannot" cross networks. The point is that FA's federation layer makes "agent finds agent" a one-line API call instead of an external registry problem.
-->

---

## Lab agenda

| # | Topic | Time | Notebook |
|---|-------|------|----------|
| 1 | **MCP** — Claude with stock-data + plotting tools | ~10 min | `demo1_mcp/01_mcp_demo.ipynb` |
| 2 | **A2A** — delegate "Analyze NVDA" to an analyst agent | ~10 min | `demo2_a2a/02_a2a_demo.ipynb` |
| 3 | **FA** — equity analyst discovers + calls a macro analyst on another host | ~10 min | `demo3_fa/03_fa_demo.ipynb` |

<br>

**Same input across all three: a question about a single stock.**

<!--
We use the same data — questions about NVDA — across all three demos. That makes the protocol differences visible without changing the problem.

Stock data comes from yfinance, which needs no API key. For production you'd swap to a company-maintained MCP server like Alpha Vantage's official one. The mechanics are identical.

LLM calls go through OpenRouter to Claude Sonnet 4.5 — set in the project's .env file. You can also point it directly at the Anthropic API.
-->

---

## Demo 1 — what we're about to do

```
   you (notebook)
        │
        ▼
   Claude (LLM)
        ├──► stock_mcp_server.py      (yfinance: quote / history / news)
        └──► viz_mcp_server.py        (matplotlib: line_chart / compare_lines)
```

You ask one sentence. Claude picks tools and orchestrates.

<!--
In Demo 1, you are the orchestrator. You write the natural-language question. Claude has six tools across two MCP servers — three from the stock server, three from the viz server — and decides which to call.

Watch for: Claude calls get_history first, then line_chart, then writes a plain-English summary. We did not tell it the order. The schemas plus the question are enough.

The notebook prints every tool call as Claude makes it, so you can see the loop unfold.
-->

---

## Demo 2 — what we're about to do

```
   you (notebook)
        │ HTTP / JSON-RPC, one sentence
        ▼
   analyst_agent.py  (A2A server, port 9999)
        │  internal Claude loop
        ▼
   stock_mcp_server.py  (same MCP tools)
        │
        ▼  (returns a written brief to you)
```

You delegate one sentence. The agent runs its own loop.

<!--
In Demo 2, the orchestrator moves into the agent. You send one sentence — Analyze NVDA — to the agent's HTTP endpoint. The agent has its own internal Claude loop. It picks tools, fetches data, writes a brief, sends back the brief.

You did not specify tools. You did not specify the plan. You just said what you wanted. That is the A2A pattern.

Watch for: in the notebook, the cell sends the message and prints the brief. There is no tool-use loop visible from the caller's side — that lives entirely in the agent.
-->

---

## Demo 3 — what we're about to do

```
   alice (HUMAN, EquityHost)
        │
        ▼
   EquityAnalyst (AGENT, EquityHost)  ──discovers via FA──►  MacroAnalyst (AGENT, MacroHost)
        │   (writes brief, weaving in macro reply)
        ▼
   alice (receives reply)
```

The equity analyst **finds** the macro analyst it has never been told about.

<!--
In Demo 3, we put the agents in a federation. Alice sends a query to the equity analyst. The equity analyst's internal LLM decides sector context would help. It calls FA's discovery API — host.get_discoverable_entities — and finds the macro analyst on a separate host. It does a friend handshake, sends a delegated question, waits for the reply, weaves it in.

Alice never knew the macro analyst existed. The equity analyst was never told its URL.

Watch for: the brief at the end has a "Sector Context" section. That section's content came back from the macro analyst, across hosts, through the relay, end-to-end. The discovery + delegation is what makes this an FA-only demo.
-->

---

<!-- _class: lead -->

# Let's begin →
## `demo1_mcp/01_mcp_demo.ipynb`

<br>

<span class="small">Interrupt with questions at any time.</span>

<!--
Questions before we start? If not, open the demo1 folder in Jupyter Lab and we'll go cell by cell.
-->
