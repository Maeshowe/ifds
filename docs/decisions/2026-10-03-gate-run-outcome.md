Status: DONE (a kritérium-olvasat); OPEN (a Tamás-döntés)
Updated: 2026-10-03
Note: A KAPU-FUTÁS EREDMÉNYE. A §3 olvasat determinált: az ÉLESÍTÉS nem teljesül, a LEÁLLÍTÁS kritérium TELJESÜL (cum_30d). A tényleges döntés human-in-the-loop, Tamásé. A `signal_attribution` eredménye LEÍRÓ és G1 szerint NEM input a leállítási kérdéshez.

# Kapu-futás — eredmény és a §3 kritériumok olvasata

## 0. A futás metaadatai (§6 protokoll-megfelelés)

| Tétel | Érték |
|---|---|
| **Pre-reg kapu-dátum** | **2026-09-22** (D2, fixálva 2026-07-28) |
| **Tényleges futás** | **2026-10-03** — **8 kereskedési nap késés**, a futás ELŐTT dokumentálva (§D8 / dátum-eltérés) |
| **Eszköz-pin (§6/1)** | `signal_attribution.py` **`c5e9ed0`** — verifikálva, **0 soros diff** |
| **Wrapper-pin** | `gate_sample.py` **`68fc00e`** — verifikálva, **0 soros diff** |
| **Minta (§6/2)** | betöltve **83** → adat-kizárás **10** → §5-kizárás **4** → **n=79** |
| **Minta-fixálás (§6/3)** | ✅ a §5.1/§5.2 feloldás a futás ELŐTT rögzült (commit `708fb12`) |
| **Kettős futás (§6/5)** | ✅ **egyetlen futás** |
| **Output (§6/4)** | `docs/analysis/gate-sample-attribution-2026-10-03-GATE-{full,clean,clean_exit}.md` *(gitignore-olt + sync-halmazban → a számok ITT, trackelve)* |
| `full` / `clean` / `clean_exit` | mind **n=79** (a Day 9 clean cut változatlanul hatástalan, §5.4) |

---

## 1. 🔴 A §3 KRITÉRIUMOK OLVASATA

### ÉLESÍTÉS — mind a három EGYIDEJŰLEG kell
| # | Kritérium | Küszöb | **Kapu-dátum (09-22)** | Teljesül? |
|---|---|---|---|---|
| 1 | Kumulatív paper P&L | > **+$2 000** | **−$5 193,86** *(távolság $7 193,86)* | ❌ |
| 2 | Sharpe (60 napi, annualizált) | > **0,5** | **−7,174** | ❌ |
| 3 | Pozitív excess vs SPY napok | **≥ 25** (D5, megfigyelt napokra) | **36 / 79 (45,6%)** | ✅ |

➡️ **ÉLESÍTÉS: NEM TELJESÜL** (2/3 kritérium elbukik, nagy távolsággal).

> ⚠️ **A [2] Sharpe magnitúdójához** — a §D3/M korlát miatt a realized-only mező a 0-exites
> napokon 0,00%-ot ad, ami a szórást lenyomja és az annualizált Sharpe-ot felnagyítja.
> **Az előjel és a küszöbtől mért távolság viszont egyértelmű**, a magnitúdó bizonytalansága
> a verdikten nem változtat.
> ⚠️ **A [3] kritériumhoz** — a 36 pozitív napból **8 nap 0-exites**, ahol `excess ≡ −SPY`,
> tehát ott a számláló **piaci irányt mér, nem stratégiai teljesítményt** (§D3/M). Exites
> napokra szűkítve: **28 / 57**.

### LEÁLLÍTÁS — bármelyik elég
| Kritérium | Küszöb | **Kapu-dátum (09-22)** | Sérül? |
|---|---|---|---|
| **30 napi kumulatív** | < **−3,0%** | 🔴 **−5,22%** | **✅ SÉRÜL** |
| 10 napi excess átlag | < −1,0% | −0,45% | nem |
| 15 napi excess átlag | < −1,0% | −0,28% | nem |

➡️ 🔴 **LEÁLLÍTÁS: A KRITÉRIUM TELJESÜL** (a `cum_30d` révén).

### A „DEFAULT: PAPER FOLYTATÁS" itt NEM alkalmazandó
A §3 szerint a default *„a két fenti egyike sem"* esetre szól. **Itt a LEÁLLÍTÁS kritérium
kifejezetten teljesül**, tehát a default nem hívható.

### Érzékenység a dátumválasztásra — a verdikt NEM változik
| | 09-22 (pre-reg) | 10-02 (adat-frontier) |
|---|---|---|
| Kumulatív | −$5 193,86 | −$6 460,95 |
| Sharpe (60d) | −7,174 | −7,105 |
| Pozitív excess nap | 36/79 ✅ | 39/86 ✅ |
| `cum_30d` | **−5,22% SÉRÜL** | **−5,72% SÉRÜL** |

📌 **Mindkét dátumon ugyanaz az olvasat.** A 8 napos késés **nem** befolyásolja a verdiktet.

---

## 2. 🔴 §8/F — KÖTELEZŐ RÖGZÍTÉS: a leállítási feltétel ÉLT a kapu előtt és alatt

> **2026-09-11 óta folyamatosan fennáll egy pre-regisztrált leállítási feltétel.**
> A `cum_30d` ezen a napon sértette először a −3,0%-os küszöböt (**−3,38%**), és a
> **kapu napján (2026-09-22) −5,22%**-on állt. A breach **11 egymást követő kereskedési
> napon** állt fenn a kapu-dátumig, **monoton romló** tendenciával
> (−3,38% → −3,45% → −4,26% → −4,62% → −5,15% → −4,86% → **−5,22%**).

**A D7-döntés (2026-09-12)** rögzítette, hogy a breach után *„elmegyünk a kapuig, ott döntés"* —
és hogy **a trigger nem resetelődik**. Ez megtörtént: a feltétel a kapun fennállt.
**A D8/F (2026-10-03)** befagyasztotta az olvasatot a kapu-napi **−5,22%**-on, mert az
adatgyűjtési módban a mutató **a tétlenségtől mechanikusan 0 felé csúszik** — ami **nem felépülés**.

---

## 3. §8/E — KÖTELEZŐ IDÉZETEK

### §D3/M — módszertani korlát (szó szerint idézve)
> A `daily_metrics::excess_return` `portfolio_return_pct` mezője **realized-only**. Egy **0 exites**
> napon ez **definíció szerint 0,00%**, tehát `excess = −SPY`. Eső tapén ez **automatikusan
> „felülteljesítést" mér**, emelkedőn lemaradást. A mező ilyen napokon **indexirányt mér, nem
> stratégiai teljesítményt.** A swing-érában a napok **~34%-a** 0-realizált; a realized és az MTM
> olvasat **12/45 napon (26,7%) ellentétes előjelű**, és ebből **csak 3** volt 0-exites — a
> szétválás tehát **nem** a 0-exit napokhoz kötött, hanem abból ered, hogy a realized-olvasat
> **nem látja a nyitott könyv mozgását**.
> **Következmény erre a kapu-riportra:** a [3] kritérium számlálójában **8 nap 0-exites**
> (ott `excess ≡ −SPY`), és a [2] Sharpe magnitúdója a lenyomott szórás miatt felnagyított.

### §D3/P — adat-proveniencia (szó szerint idézve)
> A kapu-minta **GEX/dark-pool jele Polygon-forrásból** származik, nem Unusual Whales-ből.
> A UW **kivezetve** (`docs/decisions/2026-08-18-uw-decommission.md`); a kulcs 2026-06-24 óta
> hiányzik, a flip (04-risks §11.7) **output-invariánsnak bizonyult**. Ez a **teljes swing-érára**
> igaz, tehát a minta ebből a szempontból **homogén** — **nem éra-keveredés, nem G5-sértés**.

---

## 4. A `signal_attribution` eredménye — ⚠️ LEÍRÓ, G1 SZERINT NEM KAPU-INPUT A LEÁLLÍTÁSHOZ

> **G1**: a kapu egyetlen jel-érvényességi inputja a pinelt eszköz — és **az eredménye sem
> mellette, sem ellene nem idézhető a LEÁLLÍTÁSI deliberációban**. A §3 kritériumok
> P&L/Sharpe/excess-alapúak; az attribúció **külön, leíró** mérés.
> **G3**: jel-érvényességi nyelv **tilos**; az alábbi kizárólag tényszerű.

| Metrika | **Kapu-futás (n=79)** | *08-18 leíró (n=39)* |
|---|---|---|
| **L2 sector-relative Spearman, h=5** (elsődleges) | **ρ = +0,073**, CI **[−0,150, +0,289]** | *−0,008, CI [−0,323, +0,308]* |
| L2 Spearman h=1 | +0,046, CI [−0,177, +0,264] | *+0,016* |
| L2 Spearman h=3 | −0,008, CI [−0,229, +0,213] | *−0,074* |
| L1 (exit-izolált) Spearman h=5 | −0,172, CI [−0,379, +0,051] | *−0,292* |
| L0 realizált Spearman | −0,163, CI [−0,370, +0,061] | *−0,185* |
| L0 realizált Pearson | −0,150, CI [−0,359, +0,074] | *−0,181* |

**Tényszerű megállapítások (következtetés nélkül):**
- **Mind a hat CI tartalmazza a 0-t.** A 08-18-i futásnál egy CI (L1 h=5, nem-szűrt minta)
  kizárta — **a kapu-futásnál egyetlen sem**.
- Az elsődleges metrika pontbecslése **+0,073**; a minta a 39 → **79**-re **duplázódott**.
- A pre-reg power-küszöb (|ρ|≈0,36–0,38 detektálható) **továbbra is a pontbecslés fölött** van.
- **Ebből semmilyen jel-érvényességi állítás nem vonható le (G3).**

---

## 5. 🔴 AMIT EZ A DOKUMENTUM NEM DÖNT EL

**A §3 kritérium-olvasat determinált** (§1): az ÉLESÍTÉS nem teljesül, a LEÁLLÍTÁS kritérium
teljesül. **A tényleges döntés — leállítás, folytatás más feltételekkel, vagy keret-revízió —
HUMAN-IN-THE-LOOP, Tamásé.** A monitor tervezési elve változatlan: *„kizárólag jelez, nem
cselekszik."*

**Amit a döntéshez érdemes mellé olvasni (mind leíró, egyik sem kapu-input):**
1. **Négy mért mechanikai defekt nyitva** — §11.20 (a TP1/stop/**breakeven** szintek a
   **tervezett** árhoz kötöttek, nem a fillhez: +2,91%-os adverz fillnél a R:R **0,75 → 0,23**;
   élesben igazolva a MANH veszteséggel zárt „nyereségcélján"), a visszalépési mintázat
   (6 lezárt ciklus, **4 negatív / 2 pozitív**), a `max_hold` ↔ belépő-jel ütközés, és az
   exit-eloszlás (a pozíciók **~80%-a `max_hold`-on** zárul, és ez a tömb hordozza a veszteséget).
2. **A D8 adatgyűjtési mód él** — a kereskedés felfüggesztve, a kutatási adatfolyam (Phase 1-3,
   Phase 4-6, `phase4_snapshots`) **változatlanul fut**.
3. **A D6 SIM-sáv kész** — a „mit tett volna a stratégia a javításokkal" kérdés **nulla
   kockázattal** megválaszolható ugyanazon a piaci adaton.
4. **A keret-revízió helye**: ha a §3 küszöbök strukturálisan rosszak (ahogy a 2026-05-14-i
   dokumentum §7 az ELŐZŐ keretről kimondta), annak **ITT, a kapu UTÁN, az eredmény ismeretében,
   ÚJ pre-regisztrációval** van a helye — **a §3 küszöbök utólagos módosítása kizárt.**

## 6. Kereszthivatkozások
- Gate-protokoll: **§D8**, **§D8/F**, **§5.1–§5.2 feloldás**, **dátum-eltérés**, §8 tábla (C, D8, G)
- 04-risks: **§11.19** (befagyasztva), **§11.20** (geometria), **§11.21** (lezárva), **§11.22** (D8)
- Döntési rekordok: `2026-08-18-uw-decommission.md`
- A periódus összefoglalója: `docs/planning/2026-08-18-day63-period-summary-and-proposal.md`
