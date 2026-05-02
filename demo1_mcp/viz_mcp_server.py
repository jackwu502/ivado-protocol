"""A minimal MCP server exposing visualization tools.

Run directly:  python viz_mcp_server.py
Returns rendered plots as PNG images via MCP's image content type.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from datetime import datetime
from io import BytesIO

from mcp.server.fastmcp import FastMCP, Image

mcp = FastMCP("viz-server")


def _render(fig) -> Image:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    return Image(data=buf.getvalue(), format="png")


@mcp.tool()
def line_chart(
    dates: list[str],
    values: list[float],
    title: str = "Time series",
    ylabel: str = "value",
) -> Image:
    """Line chart of `values` indexed by `dates` (YYYY-MM-DD strings).

    Use for stock price history, trends, or any single-series time-series plot.
    """
    parsed = [datetime.fromisoformat(d) for d in dates]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(parsed, values, marker="o", linewidth=1.5)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate()
    return _render(fig)


@mcp.tool()
def compare_lines(
    dates: list[str],
    series: dict[str, list[float]],
    title: str = "Comparison",
    ylabel: str = "value",
) -> Image:
    """Compare multiple series on the same axes.

    `series` maps a label to a list of numbers, all aligned with `dates`.
    Useful for comparing two tickers' prices over time.
    """
    parsed = [datetime.fromisoformat(d) for d in dates]
    fig, ax = plt.subplots(figsize=(7, 4))
    for label, values in series.items():
        ax.plot(parsed, values, marker="o", linewidth=1.5, label=label)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate()
    return _render(fig)


if __name__ == "__main__":
    mcp.run(transport="stdio")
