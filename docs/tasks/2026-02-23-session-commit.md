# Task: Session zárás — commit (2026-02-23)

Futtasd az IFDS repo gyökeréből:

```bash
cd /Users/safrtam/SSH-Services/ifds
git add scripts/paper_trading/logs/trades_2026-02-20.csv
git add scripts/paper_trading/logs/cumulative_pnl.json
git add docs/tasks/2026-02-23-obsidian-remove-feb16.md
git add docs/journal/2026-02-23-session-pnl-reconstruction.md
git add CLAUDE.md
git commit -m "fix: reconstruct feb20 trades, restore cumulative PnL, clean OBSIDIAN store

- trades_2026-02-20.csv: reconstructed from Telegram+IBKR screenshot
  (CMI/GLPI bracket split, CDP unfilled, 7x NUKE + 2x TP1)
- cumulative_pnl.json: remove stale overnight carry (+267.46),
  trading_days 5->4, cum PnL +205.83 -> -61.63 (-0.062%)
- OBSIDIAN store: removed 100 Feb 16 (Presidents Day) stale entries
- CLAUDE.md: aktualis kontextus frissitve
- docs: journal + task fajlok"
git push
```
