# Session Commit — 2026-02-24 earnings-date-telegram

## CC feladatok

### 1. Commit (ha még nem tette meg)
```bash
cd /Users/safrtam/SSH-Services/ifds
git add src/ifds/data/fmp.py src/ifds/output/telegram.py src/ifds/pipeline/runner.py tests/test_earnings_telegram.py
git commit -m "feat: earnings date column in Telegram exec table (BC17-prep)

- FMPClient.get_next_earnings_date(): /stable/earnings?symbol= endpoint
- _format_exec_table(): opcionális earnings_map paraméter, EARN oszlop
- send_daily_report(): fmp paraméter átadás a format chain-en át
- Pipeline runner: FMPTelegram client, fmp átadása send_daily_report-nak
- 16 új teszt, 833 passed total

Trigger: KEP position kiment 2026-02-23-án, valós earnings 2026-02-26
FMP bulk calendar rossz dátumot tárolt (2026-03-10). Az új oszlop
láthatóvá teszi az FMP adatot → manuális ellenőrzés lehetséges."
```

### 2. Journal commit
```bash
git add docs/journal/2026-02-24-earnings-date-telegram.md docs/tasks/2026-02-24-earnings-date-in-telegram.md
git commit -m "docs: journal 2026-02-24 earnings date telegram"
```

### 3. Push
```bash
git push
```
