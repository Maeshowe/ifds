# IFDS — Fejlesztési Backlog
<!-- Frissíti: Chat/CC, in-place — nincs dátum a névben -->
<!-- Utolsó frissítés: 2026-04-02 -->

## Ami KÉSZ van (BC1-19 + quick wins)

| BC | Tartalom | Státusz |
|---|---|---|
| BC1-16 | Pipeline (Phase 0-6), API-k, async, SIM-L1, factor vol framework | ✅ |
| BC17 | Preflight, monitor_positions, Trail Stop A+B | ✅ |
| BC18 | EWMA, MMS activation (min_periods 10), Crowdedness shadow, T5, Factor Vol | ✅ |
| BC19 | SIM-L2 Mód 1 parameter sweep + Phase 4 snapshot | ✅ |
| Quick wins | TP1 0.75×ATR, VIX SL cap, 2s10s shadow, EWMA log, contradiction penalty, BMI guard, skip day shadow | ✅ |

---

## Parkolt / Backlog (nem ütemezett)

### GEX Call Wall TP1 Override + AVWAP TP1 Újraszámítás
**Mikor:** Ha VIX ~15 körül lesz (normál piac)
**Prioritás:** P2 parkolt

**Két összefüggő probléma:**

**1. Phase 6 — call_wall felülírja a 0.75×ATR TP1-et**

Jelenlegi logika (`phase6_sizing.py` ~540. sor):
```python
if gex.call_wall > 0 and gex.call_wall > entry:
    tp1 = gex.call_wall           # ← felülírja a 0.75×ATR-t
else:
    tp1 = entry + tp1_atr         # ← 0.75×ATR
```

Példák ahol ez ártott:
- CNX (03-31): entry $40.12, call_wall $45.00 → TP1 $45.00 (+12.2%). Ha 0.75×ATR lett volna (~$41.75), talán TP1 hit. Ehelyett SL+LOSS_EXIT+MOC, -$311.
- CF (04-02): entry $127.98, call_wall $145.00 → TP1 $145.00 (+13.3%).

Példa ahol segített:
- CENX (04-01): entry $61.01, call_wall $60.00 → TP1 $60.00 (közelebb mint 0.75×ATR ~$63.80). TP1 hit + trail +$61.30.

**Javasolt megoldás:** `tp1 = min(call_wall, entry + 0.75×ATR)` — a kettő közül a közelebbit választja. Így a call_wall felső korlátként működik (ha közelebb van, használja), de nem húzza el a TP1-et irreálisan messzire.

**2. pt_avwap.py — TP1 távolság relatív újraszámítás call_wall esetén hibás**

Jelenlegi logika (`pt_avwap.py` ~268. sor):
```python
tp1_distance = s["tp1_price"] - s["entry_price"]  # eredeti távolság
new_tp1 = round(fill_price + tp1_distance, 2)      # új fill + régi távolság
```

Ez **relatív távolságot** őriz meg, ami ATR-alapú TP1 esetén helyes: ha a TP1 0.75×ATR volt, az új fill-hez is 0.75×ATR-t ad.

DE ha a TP1 call_wall-ból jött, a call_wall **abszolút árszint** (opciós piaci szint), nem relatív. Az AVWAP-nak ilyenkor nem kellene eltolnia.

Konkrét példa (2026-04-02 CF):
- Pipeline: entry $127.98, TP1 $145.00 (call_wall) → tp1_distance = $17.02
- AVWAP fill: $134.46 (magasabb entry, MKT)
- new_tp1 = $134.46 + $17.02 = **$151.48** ← ez már messze a call_wall $145.00 fölött!
- A valós TP1 maradhatna $145.00 (call_wall) vagy lehetne $134.46 + 0.75×ATR

**Javasolt megoldás:** A monitor state-ben jelölni, hogy a TP1 call_wall-ból jött-e (`tp1_source: "call_wall" | "atr"`). Az AVWAP TP1 újraszámítás:
```python
if s.get("tp1_source") == "call_wall":
    new_tp1 = s["tp1_price"]  # abszolút szint, nem toljuk el
else:
    new_tp1 = fill_price + tp1_distance  # relatív, ATR-alapú
```

**Érintett fájlok:**
- `src/ifds/phases/phase6_sizing.py` — TP1 call_wall logika
- `scripts/paper_trading/pt_avwap.py` — AVWAP TP1 újraszámítás
- `scripts/paper_trading/submit_orders.py` — monitor state `tp1_source` mező

**Miért parkolt:** A jelenlegi bearish piac (VIX 24-30) nem a legjobb tesztkörnyezet ehhez. Ha a VIX ~15-re csökken és a piac normalizálódik, a TP1 hit rate-en jobban mérhető a call_wall hatás.

---

## Q2 — Április-Június (~3 hónap)

### BC20 — SIM-L2 Mód 2 + A/B Teszt + Trail SIM (~ápr 7-18)
**Prioritás:** P2 | **Becsült:** ~12 óra CC
**SORREND: BC20 ELŐBB mint BC20A** — az M_target és BMI guard hatását csak
szimulációval lehet visszamenőleg mérni. Ha a Swing Exit jön előbb,
elveszítjük a baseline-t az összehasonlításhoz.

| Phase | Tartalom | Előfeltétel |
|---|---|---|
| 20A | Re-Score Engine — Phase 4 snapshot-okból újraszámolás más config-gal | BC18 DONE ✅ |
| 20B | T10 A/B Teszt — Freshness Alpha (lineáris) vs WOW Signals (U-alakú) | 20A kész |
| 20C | Trail SIM — broker_sim.py multi-day + partial exit szimulálás | 20A kész |

**Miért fontos:** Amíg nincs Mód 2, nem tudjuk tudományosan mérni, hogy az EWMA,
MMS, contradiction penalty ténylegesen javít-e a scoring-on. Jelenleg "érzésre"
nézzük a review-kban.

---

### BC20A — Swing Hybrid Exit (~ápr 21 — máj 9)
**Prioritás:** P2 | **Becsült:** ~25-30 óra CC | **Design:** `swing-hybrid-exit-design.md`

Ez az **igazi game changer** — az 1-napos MOC exit rendszerből swing trading-re váltás.
A Position Tracker teljesen új state management komponens, és az async path frissítése
Phase 4/6-ban további effort.

| Phase | Tartalom | Effort |
|---|---|---|
| 20A_1 | VWAP Modul — Polygon 5-min bars, entry quality filter | 2h |
| 20A_2 | Position Tracker — `state/open_positions.json`, hold day, TP1 status | 3h |
| 20A_3 | Pipeline Split + MKT Entry — Phase 1-3 (22:00) / Phase 4-6 (15:45) + MKT entry | 3h |
| 20A_4 | close_positions.py Swing — hold tracking, breakeven SL, TRAIL, max D+5 | 3h |
| 20A_5 | SimEngine Swing — broker_sim multi-day, partial exit, trail szimulálás | 4h |
| — | Async path frissítés — Phase 4 VWAP fetch + Phase 6 swing sizing integráció | 3h |
| — | Tesztelés — unit + integration (Position Tracker, SimEngine Swing, pipeline split) | 5h |
| — | Puffer — review, debug, edge cases (D+5 rollover, partial fill, breakeven edge) | 5h |
| **Összesen** | | **~28h** |

**Amit megold:**
- MOC exit dominancia (30 napból 22-ben minden trade MOC-on zárt)
- AVWAP slippage (limit→MKT váltás, garantált fill)
- TP2 soha nem érhető el (trail stop helyettesíti)
- Pozíciók 5 napig nyitva maradhatnak (swing hold)

---

### BC21 — Risk Layer + Cross-Asset Regime (~máj 11-22)
**Prioritás:** P2 | **Becsült:** ~10 óra CC

| Phase | Tartalom |
|---|---|
| 21A | Korrelációs Guard + Portfolio VaR — ne legyen 5 utility egyszerre |
| 21B | Cross-Asset Regime — HYG/IEF, RSP/SPY, IWM/SPY szavazás + 2s10s (4. szavazó) |

**Amit megold:**
- BMI momentum guard jelenleg "gyors fix" → a Cross-Asset Regime az igazi megoldás
- 2s10s yield curve shadow → Szint 2 küszöbök + Szint 3 integráció
- Portfolio VaR → nem csak ticker-szintű risk, hanem portfólió-szintű

---

### BC22 — HRP Allokáció (~máj 25 — jún 6)
**Prioritás:** P2 | **Becsült:** ~8 óra CC

| Phase | Tartalom |
|---|---|
| 22A | Hierarchical Risk Parity — Riskfolio-Lib, score-alapú allokáció |
| 22B | Pozíciószám bővítés 8→15 — exposure limit recalibráció |

---

### BC23 — ETF Flow Intelligence (~jún 8-27)
**Prioritás:** P2 | **Becsült:** ~12 óra CC

| Phase | Tartalom |
|---|---|
| 23A | ETF Flow Intelligence — UW ETF in/outflow, szektor rotáció megerősítés |
| 23B | L2 Szektoros Finomítás — 42 ETF, szektor-szintű momentum rangsor |
| 23C | MCP Server Alap — IFDS pipeline introspekció API |

---

## Q3 — Július-Szeptember

### BC24 — Black-Litterman + Company Intel v2
**Prioritás:** P3

| Phase | Tartalom |
|---|---|
| 24A | Score→Expected Return mapping, Black-Litterman modell, HRP→BL transition |
| 24B | MCP-alapú Company Intel v2, adjusted EPS, short interest, napi auto futás |

### BC25 — Auto Execution
**Prioritás:** P3

| Phase | Tartalom |
|---|---|
| 25A | Polygon WebSocket + IBKR auto submit + Telegram human approval loop |
| 25B | IBGatewayManager long-running — heartbeat, reconnect, watchdog |

### BC26 — Multi-Strategy Framework
**Prioritás:** P3

| Phase | Tartalom |
|---|---|
| 26A | Mean Reversion stratégia — Laggard + OVERSOLD szektorok |
| 26B | ETF-szintű kereskedés — momentum stratégia |

---

## Q4 — Október-December

### BC27-30 — Dashboard + Alpha Decay + Retail Packaging
**Prioritás:** P3 | Még nincs részletes scope

- Dashboard (web UI a pipeline eredményekhez)
- Alpha Decay monitoring (a stratégia hatékonysága idővel)
- Retail Packaging (ha éles kereskedésre váltunk)

---

## SimEngine Roadmap

| Level | Státusz | BC |
|---|---|---|
| L1 Forward Validation | ✅ Kész | BC16 |
| L2 Mód 1 Parameter Sweep | ✅ Kész | BC19 |
| L2 Mód 2 Re-Score | Következő | BC20 |
| L2 Trail Szimuláció | Következő | BC20 |
| L3 Full Backtest (VectorBT) | Q3 | BC24+ |

---

## Összesített becsült effort

| Időszak | BC-k | Becsült CC effort |
|---|---|---|
| Április (ápr 7 — ápr 30) | BC20 + BC20A eleje | ~35-40 óra |
| Május (máj 1 — máj 31) | BC20A vége + BC21 + BC22 | ~25-30 óra |
| Június (jún 1 — jún 30) | BC23 | ~12 óra |
| Júl-Szept | BC24-26 | ~30 óra |
| Okt-Dec | BC27-30 | TBD |
| **Összesen Q2-Q3** | | **~100-110 óra** |

---

## Legfontosabb kérdés (Day ~50/63 kiértékelés)

Az április végi review megmutatja:
- Javult-e a TP1 hit rate (0.75×ATR vs korábbi 2×ATR)?
- Az M_target penalty csökkentette-e a contradiction veszteségeket?
- A BMI guard működött-e csökkenő BMI trend esetén?
- Az MMS multiplierek (51 ticker aktív) javult-e a méretezés?
- A piac recovery fázisában hogyan teljesít a rendszer?
- A Skip Day Shadow Guard hány napot mentett volna?

Ezeket a BC20 SIM-L2 Mód 2 fogja tudományosan mérni a baseline-nal összehasonlítva.
