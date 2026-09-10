"""Read-only aggregate queries over ai_requests (see db.py's SCHEMA and
enricher.py's _record_ai_request) — the source for AI.md's speed and
reliability numbers. Run as a script (`python -m app.ai_stats`) to print
a fresh summary; re-run and re-paste into AI.md whenever those numbers
need refreshing, rather than trusting stale hand-typed figures.

Deliberately does not compute a single blended "quality score" — success
rate and latency are mechanical (every real call contributes a data
point automatically); factual accuracy is not and can't be inferred from
this table at all (see findings.md's manual fact-checks instead). Mixing
them into one number would let a fast, reliable, confidently-wrong
provider look good."""

import asyncio
import statistics
from typing import TypedDict

import aiosqlite

from .db import DB_PATH


class LatencyStats(TypedDict):
    count: int
    median_ms: float
    p90_ms: float
    min_ms: int
    max_ms: int


async def success_rate(conn: aiosqlite.Connection, provider: str,
                        since: str | None = None) -> float | None:
    """Fraction (0.0-1.0) of ai_requests rows for this provider with
    outcome='success'. None if there are no rows at all (distinct from
    0.0, which means real data showing total failure)."""
    query = "SELECT outcome FROM ai_requests WHERE provider = ?"
    params: list = [provider]
    if since:
        query += " AND started_at >= ?"
        params.append(since)
    cur = await conn.execute(query, params)
    rows = await cur.fetchall()
    if not rows:
        return None
    successes = sum(1 for r in rows if r["outcome"] == "success")
    return successes / len(rows)


async def latency_percentiles(conn: aiosqlite.Connection, provider: str,
                              since: str | None = None,
                              successful_only: bool = True) -> LatencyStats | None:
    """Median/p90 latency in ms. successful_only=True (default) excludes
    no_output rows, since a fast failure isn't meaningfully "fast" for
    the purpose of judging how long a real answer takes to arrive."""
    query = "SELECT elapsed_ms FROM ai_requests WHERE provider = ?"
    params: list = [provider]
    if successful_only:
        query += " AND outcome = 'success'"
    if since:
        query += " AND started_at >= ?"
        params.append(since)
    cur = await conn.execute(query, params)
    values = sorted(r["elapsed_ms"] for r in await cur.fetchall())
    if not values:
        return None
    return {
        "count": len(values),
        "median_ms": statistics.median(values),
        # SQLite has no native percentile function; nearest-rank on the
        # sorted list is precise enough for a handful of dashboard
        # numbers and avoids pulling in numpy for this one call.
        "p90_ms": values[min(len(values) - 1, round(0.9 * (len(values) - 1)))],
        "min_ms": values[0],
        "max_ms": values[-1],
    }


async def recent_summary(since: str | None = None) -> dict[str, dict]:
    """Full per-provider dump: success rate + latency stats, one entry
    per provider that has at least one logged request."""
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        cur = await conn.execute("SELECT DISTINCT provider FROM ai_requests")
        providers_seen = [r["provider"] for r in await cur.fetchall()]
        out: dict[str, dict] = {}
        for provider in sorted(providers_seen):
            out[provider] = {
                "success_rate": await success_rate(conn, provider, since),
                "latency": await latency_percentiles(conn, provider, since),
            }
        return out


def _print_summary(summary: dict[str, dict]) -> None:
    if not summary:
        print("No ai_requests rows yet — nothing to summarize.")
        return
    for provider, stats in summary.items():
        rate = stats["success_rate"]
        latency = stats["latency"]
        rate_str = f"{rate:.0%}" if rate is not None else "n/a"
        if latency:
            lat_str = (f"median {latency['median_ms']:.0f}ms, "
                       f"p90 {latency['p90_ms']:.0f}ms, n={latency['count']}")
        else:
            lat_str = "no successful calls yet"
        print(f"{provider}: success_rate={rate_str}, {lat_str}")


if __name__ == "__main__":
    _print_summary(asyncio.run(recent_summary()))
