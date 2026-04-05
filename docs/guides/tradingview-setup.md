# TradingView + IFDS — Infrastruktúra telepítés

Lépésről-lépésre útmutató a TradingView Desktop + CDP + MCP beállításához
az IFDS paper trading vizualizációjához.

## Két gép, két szerep

| Gép | TradingView mód | Mi fut rajta |
|-----|-----------------|-------------|
| **Mac Mini** | CDP auto (cron) | Layer 1-2: tv_sync.py rajzolja a szinteket |
| **MacBook** | CDP interaktív | Layer 3: Claude Code + MCP ad-hoc parancsok |

Mindkét gépen szükséges a TradingView Desktop és a debug mód.

---

## 1. lépés — TradingView Desktop telepítése

### Mac Mini + MacBook (mindkettőn)

1. Töltsd le: https://www.tradingview.com/desktop/
2. Telepítsd a `.dmg` fájlból
3. Jelentkezz be a TradingView fiókodba (fizetős előfizetés kell a real-time adathoz)
4. Állíts be egy alap layoutot:
   - Daily timeframe
   - Candles chart type
   - Volume indikátor alul

---

## 2. lépés — TradingView indítása debug módban (CDP)

A CDP (Chrome DevTools Protocol) lehetővé teszi, hogy programozottan
vezéreljük a TradingView Electron appot a `localhost:9222` porton.

### Mac Mini — automatikus indítás

Hozz létre egy launch scriptet:

```bash
# ~/scripts/launch_tv_debug.sh
#!/bin/bash
# Kill any existing TradingView
pkill -f TradingView 2>/dev/null
sleep 1

# Launch with CDP
/Applications/TradingView.app/Contents/MacOS/TradingView \
    --remote-debugging-port=9222 &

echo "TradingView launched with CDP on port 9222"
```

```bash
chmod +x ~/scripts/launch_tv_debug.sh
```

**Reggeli rutin:** A TradingView-t debug módban kell indítani MINDEN NAP
a cron scriptek előtt. Két lehetőség:

**A) Kézi indítás:** Reggel SSH-val vagy fizikailag: `~/scripts/launch_tv_debug.sh`

**B) Login item (automatikus):**
1. System Settings → General → Login Items
2. Add: `~/scripts/launch_tv_debug.sh`
   VAGY: Automator app ami futtatja a scriptet

**C) Launchd (legmegbízhatóbb):**
```bash
# ~/Library/LaunchAgents/com.ifds.tradingview.plist
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ifds.tradingview</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/TradingView.app/Contents/MacOS/TradingView</string>
        <string>--remote-debugging-port=9222</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.ifds.tradingview.plist
```

### MacBook — kézi indítás

```bash
# Terminal
/Applications/TradingView.app/Contents/MacOS/TradingView --remote-debugging-port=9222 &
```

Vagy hozz létre egy Automator appot (Optional):
1. Automator → New → Application
2. Add: Run Shell Script
3. Paste: `/Applications/TradingView.app/Contents/MacOS/TradingView --remote-debugging-port=9222`
4. Save as: "TradingView Debug.app" a Dock-ba

### Ellenőrzés (mindkét gépen)

```bash
# CDP health check — JSON választ kell kapni
curl -s http://localhost:9222/json/version | python3 -m json.tool
```

Várható kimenet:
```json
{
    "Browser": "Chrome/XXX",
    "Protocol-Version": "1.3",
    "webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/..."
}
```

---

## 3. lépés — Python CDP függőségek (Mac Mini)

```bash
cd /Users/safrtam/SSH-Services/ifds
source .venv/bin/activate

# Websocket kliens a CDP kommunikációhoz
pip install websocket-client --break-system-packages
```

---

## 4. lépés — tradingview-mcp telepítése (MacBook, Layer 3)

```bash
# Klónozás
cd /Users/safrtam/tools   # vagy ahol a toolokat tartod
git clone https://github.com/tradesdontlie/tradingview-mcp.git
cd tradingview-mcp
npm install

# Teszt (TradingView-nak futnia kell debug módban)
node src/server.js  # Ctrl+C-vel kilépés — ha nincs hiba, jó
```

### Claude Code MCP config

**Globális config** (minden projekthez):
```bash
# ~/.claude/.mcp.json
{
  "mcpServers": {
    "tradingview": {
      "command": "node",
      "args": ["/Users/safrtam/tools/tradingview-mcp/src/server.js"]
    }
  }
}
```

**IFDS projekt-szintű config** (csak IFDS-hez):
```bash
# /Users/safrtam/SSH-Services/ifds/.mcp.json
{
  "mcpServers": {
    "tradingview": {
      "command": "node",
      "args": ["/Users/safrtam/tools/tradingview-mcp/src/server.js"]
    }
  }
}
```

Válaszd az egyiket — a projekt-szintű config prioritást élvez.

### Ellenőrzés Claude Code-ban

Indítsd újra Claude Code-ot (ha fut), majd:
```
> Use tv_health_check to verify TradingView is connected
```

Várható válasz: connection OK, TradingView verzió, CDP port.

---

## 5. lépés — TradingView layout beállítása

### Ajánlott layout az IFDS-hez

1. Nyisd meg a TradingView Desktop-ot
2. Állíts be:
   - **Timeframe:** 5 min (AVWAP legjobban itt látszik)
   - **Chart type:** Candles
   - **Indikátorok:** Volume (alul)
3. Hozz létre egy "IFDS" watchlistet (üres, a tv_sync.py majd feltölti)
4. Mentsd el mint "IFDS Trading" layout:
   - Jobb felső sarok → Layout → Save Layout As → "IFDS Trading"

### AVWAP Pine Script kézi hozzáadása (ha Layer 3 nincs még)

1. Pine Editor megnyitása (alul)
2. New → Indicator
3. Töröld az alapértelmezett kódot
4. Másold be a `scripts/tradingview/pine/ifds_avwap.pine` tartalmát
5. "Add to Chart" gomb
6. Az AVWAP vonal megjelenik a charton (lila, market open-től)

---

## 6. lépés — Cron beállítás (Mac Mini)

A Layer 1-2 script a meglévő paper trading cron-okhoz illeszkedik:

```bash
crontab -e
```

Meglévő cron sorok (referencia):
```
# Pipeline
00 08 * * 1-5  cd /Users/safrtam/SSH-Services/ifds && ...

# Paper Trading
35 15 * * 1-5  ... submit_orders.py ...
*/1 15-17 * * 1-5  ... pt_avwap.py ...
*/5 10-21 * * 1-5  ... pt_monitor.py ...
45 21 * * 1-5  ... close_positions.py ...
05 22 * * 1-5  ... eod_report.py ...
```

Új sorok:
```
# TradingView Sync (Layer 1-2)
# A script belül kezeli a napi log rotációt (logs/pt_tv_sync_YYYY-MM-DD.log)
# és a pt_events JSONL-be is ír (logs/pt_events_YYYY-MM-DD.jsonl)

# 15:40 CET — submit_orders (15:35) után, monitor_state kész
40 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/tradingview/tv_sync.py 2>> logs/cron_errors.log

# 19:10 CET — Scenario B (19:00) után, frissített szintek
10 19 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/tradingview/tv_sync.py --update 2>> logs/cron_errors.log
```

---

## Hibaelhárítás

### "Connection refused" a CDP-nél

```bash
# Ellenőrizd, hogy a TV fut-e debug módban
curl -s http://localhost:9222/json/version

# Ha nincs válasz:
# 1. TradingView normálisan fut (debug nélkül)?
pkill -f TradingView
sleep 2
/Applications/TradingView.app/Contents/MacOS/TradingView --remote-debugging-port=9222 &

# 2. Port foglalt?
lsof -i :9222
```

### "TradingView not found" az MCP-nél

```bash
# Ellenőrizd az elérési utat
ls -la /Applications/TradingView.app/Contents/MacOS/TradingView

# Ha máshol van:
which tradingview
find /Applications -name "TradingView" 2>/dev/null
```

### "WebSocket disconnected" szinkron közben

A TradingView frissítheti magát vagy a websocket timeout-olhat:

```bash
# tv_sync.py-ban automatikus reconnect van, de ha nem segít:
pkill -f TradingView
sleep 3
~/scripts/launch_tv_debug.sh
```

### Pine Script compilation error

```bash
# Ellenőrizd a Pine Script verziót (v5 kell)
# A TradingView frissítéseknél változhatnak a belső API-k

# MCP-vel:
# Claude Code → "Use pine_get_errors to check compilation"

# Kézzel:
# Pine Editor → hiba jelezve a kódban
```

### Rajzok nem jelennek meg

```bash
# 1. Van-e monitor_state a mai naphoz?
ls -la scripts/paper_trading/logs/monitor_state_$(date +%Y-%m-%d).json

# 2. Dry-run mód — kiírja a tervezett rajzokat
python scripts/tradingview/tv_sync.py --dry-run

# 3. A TradingView-ban a megfelelő szimbólumon vagy?
# A tv_sync.py automatikusan vált, de ellenőrizd a watchlistet
```

---

## Biztonsági megjegyzések

- A CDP csak `localhost`-on elérhető (9222 port) — nem tár ki semmit a hálózatra
- A TradingView fiókod hitelesítő adatai a TradingView Electron app-ban maradnak
- A `tradingview-mcp` nem küld adatot sehova — csak a lokális CDP-vel kommunikál
- A TradingView ToS szürke zóna az automatizálásra — személyes használatra OK,
  de ne oszd meg és ne használd kereskedelmi célra
- A CDP nem ad hozzáférést a TradingView szerverekhez, csak a helyi app-hoz

---

## Összefoglaló — mi hol fut

```
Mac Mini (Production)
├── TradingView Desktop (CDP :9222) — launch_tv_debug.sh (reggel)
├── IBKR Gateway (paper account)
├── Pipeline cron (10:00 CET)
├── Paper Trading scriptek (15:35 - 22:05 CET)
└── tv_sync.py cron (15:40 + 19:10 CET) ← Layer 1-2

MacBook (Development)
├── TradingView Desktop (CDP :9222) — kézi indítás
├── Claude Code + tradingview-mcp MCP
├── VSCode + IFDS repo
└── Interaktív TV parancsok ← Layer 3
```
