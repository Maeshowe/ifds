# IFDS Backlog — Ötletek, nem ütemezett

## VectorBT CC Skill (BC20+ scope)

**Forrás:** marketcalls/vectorbt-backtesting-skills repo elemzése (2026-02-24)

**Ötlet:** IFDS-specifikus CC skill(ek) VectorBT parameter sweep-hez, a Phase 4 snapshot adatokon alapulva. Lehetséges fókuszok:
- `/sim-sweep` — min_score, weight_flow/funda/tech, ATR multiplier, hold napok sweep → heatmap + CSV
- `/sim-validate` — SimEngine vs VectorBT párhuzamos futtatás, eredmény összevetés
- `/sim-score` — scoring weight optimalizálás Sharpe alapján

**Miért érdemes:** munkamenet-gyorsítás — egy paranccsal CC végigcsinálja a teljes sweep → heatmap → CSV pipeline-t.

**Előfeltétel:** ~30-40 nap Phase 4 snapshot adat (legkorábban április, BC20 scope).

**Implementáció típusa (még nem döntött):** prompt template + tudásbázis, vagy prompt + kész `ifds_sim_vbt.py` modul.

**Státusz:** PARKOLT — BC20 előtt nem aktuális.

---

## MCP Server — IFDS + MID (BC23+ scope)

**Forrás:** financial-datasets/mcp-server repo elemzése (2026-02-28)

**Ötlet:** Saját MCP server a meglévő API-k (FRED, FMP, Polygon, Unusual Whales) fölé, két céllal:

**A) Template alapú saját MCP server:**
- A `financial-datasets/mcp-server` repo struktúráját követve
- Csak a már meglévő IFDS/MID API integrációk exponálása MCP toolként
- Claude Desktop-ból közvetlenül lekérdezhető: pipeline státusz, logok, paper trading P&L
- Nem új adatforrás — kizárólag meglévő wrapper-ek (FMPClient, stb.)

**C) IFDS/MID pipeline introspekció:**
- `get_pipeline_status` — legutóbbi cron futás eredménye
- `get_paper_trading_pnl` — kumulatív P&L, napi trades
- `get_positions` — aktuális nyitott pozíciók
- `get_regime` — aktuális BMI/GIP rezsim
- `query_logs` — log keresés dátum/ticker alapján

**Előfeltétel:** BC23 után — MID produkciós állapot, IFDS stabil.

**Státusz:** PARKOLT — BC23 előtt nem aktuális.

---

## Company Intel v2 — MCP-alapú adatgazdagítás (BC23+ scope)

**Forrás:** NXST GAAP vs adjusted EPS eset elemzése (2026-02-28)

**Ötlet:** A `company_intel.py` jelenleg FMP + Anthropic API kombinációt használ. BC23 után érdemes lehet:
- MCP server toolként exponálni (Claude Desktop direkt hívhatja)
- Adjusted EPS adatforrás integrálása (FMP `/stable/income-statement` vagy külső)
- Richer context: short interest, options flow summary, insider sentiment score
- Esetleg: napi automatikus futás Telegram push helyett MCP pull modellben

**Előfeltétel:** MCP server megléte (fenti item), BC23 után.

**Státusz:** PARKOLT — BC23 előtt nem aktuális.
