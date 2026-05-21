Status: OPEN
Updated: 2026-04-02
Note: TV-SYNC Layer 3 — MCP interaktív (extra, ~4h CC)

# TV-SYNC Layer 3 — Claude Code + TradingView MCP interaktív

## Cél

A `tradingview-mcp` (https://github.com/tradesdontlie/tradingview-mcp) telepítése
Claude Code MCP szerverként a MacBook-on. Ad-hoc interaktív használat:
"mutasd a mai pozíciókat", "mi az EMN trail állapota?", "rajzold ki az utolsó
hét trade-jeit", "hasonlítsd össze a pipeline TP1-et a tényleges exit-tel".

**Ez kényelmi feature** — Layer 1-2 adja az üzleti értéket, Layer 3 az extra.

## Háttér

A `tradingview-mcp` 68 MCP toolt ad Claude Code-nak a TradingView vezérlésére.
CDP-n (Chrome DevTools Protocol, port 9222) kommunikál. Stdio transport.

Fő toolok az IFDS use case-hez:
- `chart_set_symbol` — ticker váltás
- `draw_shape` — horizontal_line, trend_line, rectangle, text
- `draw_clear` — IFDS rajzok törlése
- `watchlist_add` — watchlist frissítés
- `pine_set_source` + `pine_smart_compile` — AVWAP indikátor injection
- `capture_screenshot` — screenshot a chartról
- `batch_run` — több ticker egyszerre
- `data_get_ohlcv` — OHLCV adat lekérés

## Scope

### 1. MCP config — `~/.claude/.mcp.json` (MacBook)

```json
{
  "mcpServers": {
    "tradingview": {
      "command": "node",
      "args": ["/Users/safrtam/tools/tradingview-mcp/src/server.js"]
    }
  }
}
```

### 2. IFDS projekt MCP config — `.mcp.json` (MacBook, IFDS repo)

```json
{
  "mcpServers": {
    "tradingview": {
      "command": "node",
      "args": ["/Users/safrtam/tools/tradingview-mcp/src/server.js"]
    }
  }
}
```

### 3. CC Custom Command — `/tv-sync`

`.claude/commands/tv-sync.md`:
```markdown
# TradingView Position Sync

Read today's monitor_state.json and visualize on TradingView:

1. Read `scripts/paper_trading/logs/monitor_state_{today}.json`
2. For each ticker:
   a. Use `chart_set_symbol` to switch chart
   b. Use `draw_clear` to remove old IFDS drawings
   c. Draw entry, TP1, TP2, SL with `draw_shape` (horizontal_line)
   d. If trail_active: draw trail SL
   e. If avwap_converted: draw original limit vs AVWAP entry
   f. Use `capture_screenshot` for visual confirmation
3. Use `watchlist_add` to add all tickers to IFDS watchlist

Color scheme:
- Entry (limit): blue solid
- Entry (AVWAP): orange dashed
- TP1: green dashed
- TP2: green dotted
- SL: red solid
- Trail SL: orange dashed
- Original limit (if AVWAP): gray dotted
```

### 4. CC Custom Command — `/tv-review`

`.claude/commands/tv-review.md`:
```markdown
# TradingView Daily Review

Compare pipeline plan vs actual execution:

1. Read `output/execution_plan_run_{today}_*.csv` (planned)
2. Read `scripts/paper_trading/logs/monitor_state_{today}.json` (actual)
3. Read `scripts/paper_trading/logs/trades_{today}.csv` (result)

For each ticker, report:
- Plan entry vs actual fill (AVWAP slippage)
- Plan SL vs VIX-capped SL
- TP1/TP2 hit or MOC exit
- Scenario A or B activation
- Trail SL high watermark

Then for each interesting case, use TradingView to:
- Switch to that ticker's chart
- Draw the planned vs actual levels
- Screenshot for visual comparison
```

### 5. AVWAP Pine Script injection command

`.claude/commands/tv-avwap.md`:
```markdown
# Inject IFDS AVWAP Indicator

Read `scripts/tradingview/pine/ifds_avwap.pine` and inject it into TradingView:

1. Use `pine_new` to create a blank indicator
2. Use `pine_set_source` with the Pine Script content
3. Use `pine_smart_compile` to compile
4. Use `pine_get_errors` to check for issues
5. Confirm the AVWAP line appears on the chart
```

## Fontos megjegyzések

- Layer 3 a **MacBook-on** fut (Claude Code + TradingView Desktop)
- A **Mac Mini-n** Layer 1-2 fut (cron + CDP)
- Ha mindkét gépen fut TV debug módban, a port nem ütközik (külön gépek)
- A MCP server stdio transport — nem igényel hálózati konfigurációt
- A TradingView-nak MINDKÉT gépen debug módban kell futnia

## Előfeltétel

- Layer 1 kész (CDP client, tv_sync.py)
- Layer 2 kész (AVWAP Pine Script)
- Node.js 18+ a MacBook-on
- `tradingview-mcp` klónozva és npm install lefuttatva
- TradingView Desktop debug módban a MacBook-on
- Claude Code MCP config beállítva

## Tesztelés

- `tv_health_check` tool hívás Claude Code-ból → connection OK
- `/tv-sync` command → vizuálisan ellenőrizni
- `/tv-review` command → összehasonlítás konzisztens
- `pine_set_source` → AVWAP indikátor megjelenik

## Fájlok

| Fájl | Leírás |
|------|--------|
| `.mcp.json` | MCP config az IFDS projektben |
| `.claude/commands/tv-sync.md` | ÚJ — CC command a szinkronhoz |
| `.claude/commands/tv-review.md` | ÚJ — CC command a napi review-hoz |
| `.claude/commands/tv-avwap.md` | ÚJ — CC command AVWAP injection-höz |

## Commit

```
feat(tradingview): add Claude Code MCP integration and TV commands

Layer 3: tradingview-mcp configured as Claude Code MCP server.
Custom commands for position sync (/tv-sync), daily review
(/tv-review), and AVWAP Pine Script injection (/tv-avwap).
```
