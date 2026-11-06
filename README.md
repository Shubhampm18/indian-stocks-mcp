# stock-analyst-mcp

MCP server for India-only (NSE/BSE) stock analysis. Six tools over historical
price data — OHLC, returns, technical indicators, risk metrics, index history,
peer comparison — where every tool takes an `as_of` cutoff and the server
physically cannot return data after it.

```bash
uvx stock-analyst-mcp        # from PyPI (no API key)
# or from a local build:
uvx --from ./dist/stock_analyst_mcp-0.1.0-py3-none-any.whl stock-analyst-mcp
```

## Install

```bash
uv sync
uv run pytest -q            # leak suite
uv build
uvx --from ./dist/stock_analyst_mcp-0.1.0-py3-none-any.whl stock-analyst-mcp
```

## MCP client config

```json
{
  "mcpServers": {
    "stock-analyst": {
      "command": "uvx",
      "args": ["stock-analyst-mcp"]
    }
  }
}
```

Claude Desktop (config: `claude_desktop_config.json`), Cursor (`.cursor/mcp.json`), etc. accept the same block. No API key; data comes from yfinance (research/personal use, cached locally in Parquet).

## The `as_of` guarantee

- Every tool accepts `as_of` (YYYY-MM-DD). All rows are filtered to `date <= as_of` in a single helper (`enforce_as_of` in `src/stock_analyst_mcp/data.py`), and the response echoes `data_through`.
- Adjusted prices are **rebuilt from corporate actions with ex-date ≤ as_of only** — a split announced later cannot change an earlier price. Dividends use the standard factor method: `factor = 1 - div / close_on_day_before_ex_date`, multiplied into all pre-ex prices (not flat cash subtraction). (This is the adjustment-vintage test in `tests/test_leak.py`.)
- A future `as_of` raises `isError: true`; an unknown symbol raises `isError: true` with "Did you mean …?" suggestions.
- Nothing is printed to stdout (stdio JSON-RPC would corrupt); all logging goes to stderr.

## Tools

| Tool | What it returns |
|---|---|
| `get_ohlcv(symbol, as_of?, lookback_days=90)` | Daily OHLC + rebuilt adjusted close + `adjustment_history` |
| `get_returns(symbol, as_of?, windows=[1,5,20,60])` | Simple/log returns per window (pandas) |
| `get_technical_indicators(symbol, as_of?, indicators=[…])` | SMA/EMA/RSI/MACD/Bollinger/ATR/VWAP computed in Python, never LLM math; `trend` field |
| `get_risk_metrics(symbol, as_of?, benchmark="^NSEI", lookback_days=252)` | Sharpe, Sortino, max drawdown (start/end), volatility, beta, alpha |
| `get_index_history(index, as_of?, lookback_days=90)` | `^NSEI` / `^BSESN` / `^NSEBANK` close series |
| `get_peer_comparison(symbols, as_of?, metric="return_20d")` | Side-by-side values + ranks on one metric |

Every output carries `source` (`"yfinance"`), `as_of` (echoed), and `currency` (`"INR"`).

## Demo

> Did Reliance beat TCS over the last 20 sessions as of 31 Dec 2025?

```
get_peer_comparison(symbols=["RELIANCE.NS", "TCS.NS"], as_of="2025-12-31", metric="return_20d")
```

→ ranked results for the two symbols, `data_through` on or before 2025-12-31, plus the peer `current_price` for each. Re-checkable in one yfinance call: `yf.Ticker("RELIANCE.NS").history(...)`.

## How this differs from existing NSE MCP servers (measured, Nov 2026)

- **FinMCP** ([Finance-LLMs/FinMCP](https://github.com/Finance-LLMs/FinMCP), MIT) fetches live NSE/BSE quotes via `nsepython`/`bse` (see `MCP_tools/indian_markets.py`) — **no `as_of` parameter, no test directory**; the comparison script `scripts/compare_finmcp.py` runs the same 3 queries against both servers.
- **Tapetide** (48 tools) advertises point-in-time tools but runs on a closed remote (`mcp.tapetide.com`); the public repo is only a stdio→HTTPS bridge with zero date logic.
- This server's value is the last two columns: mandatory `as_of` with server-side enforcement, and a runnable leak suite (`tests/test_leak.py`: cutoff shrink, canary spike, future-date error, vintage rebuild, pandas recomputation match).

## Data notes

- Suffixes: `.NS` = NSE, `.BO` = BSE. Bare tickers default to `.NS`. Use `.BO` explicitly for BSE — bare tickers are always treated as NSE, and an unknown bare ticker will error with "Did you mean...?" suggestions rather than guessing an exchange.
- Cache: `~/.cache/stock-analyst-mcp/` — Parquet cache with a **24-hour TTL**; older caches are refetched, and a network failure falls back to the stale cache with a stderr warning. Pass `force_refresh=True` internally to bypass the TTL.
- Market hours: 09:15–15:30 IST, Mon–Fri. Weekends/holidays roll back to the last trading day (`data_through` reports it).
- yfinance is research/personal use only; do not redistribute raw data commercially. Cache: `~/.cache/stock-analyst-mcp/`.

## Tests

```bash
uv run pytest -q
```

Leak suite (8 passing, 6 network-dependent tests skipped when the network is unavailable — the pure-logic cutoff/vintage tests never skip).

## Credits

Built with the official `mcp` Python SDK. yfinance usage follows https://ranaroussi.github.io/yfinance/advanced/price_adjustment.html (`auto_adjust=False` + local adjustment-vintage rebuild is why this server can answer "as of" honestly).
