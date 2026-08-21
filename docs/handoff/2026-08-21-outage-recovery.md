Status: ACTIVE
Updated: 2026-08-21
Note: 3. FileVault-osztályú outage (07-22, 08-07 után) — DE ÚJ HIBAALAK: a gép teljesen felbootolt és SSH-n egész nap elérhető volt, miközben a `cron` csak a 17:35-ös konzol-loginkor indult el. Időkritikus teendő: IB Gateway indítása a 21:40-es exit-ablak előtt.

# Outage-helyreállítás — 2026-08-21 (péntek)

## 0. Egy mondatban
Áramszünet után a Mini **09:07-kor teljesen felbootolt** és **SSH-n végig elérhető volt**, de a
**`cron` csak 17:35:43-kor, a konzol-login pillanatában indult el** — így **8,5 órán át egyetlen
ütemezett job sem futott**, miközben a gép kívülről egészségesnek látszott.

## 1. Bizonyítékok (mind verifikálva 2026-08-21 17:38–17:55 CEST)

| Tény | Bizonyíték |
|---|---|
| Teljes boot 09:07:02 | `kern.boottime`, `launchd` (pid 1) `STARTED Fri Aug 21 09:07:03` |
| **`cron` csak 17:35:43-kor indult** | `ps -p $(pgrep cron) -o lstart` → `Fri Aug 21 17:35:43` |
| Konzol-login 17:35 | `who` → `safrtam console Aug 21 17:35` |
| **Ma 0 log keletkezett** | a `logs/` legfrissebb fájlja: `pt_events_2026-08-20.jsonl`, **08-20 22:15** |
| **Ma 0 trade, 0 order** | IBKR `get_account_trades(TODAY)` = `[]`, `get_account_orders` = `[]` |
| Mind a 9 pozíció nyitva | IBKR `get_account_positions` — a 4 flagelt tétel is |
| **Nem fut IB Gateway** | nincs java/gateway process; app: `~/Applications/IB Gateway 10.43/` |
| A gép nem alszik | `pmset`: `sleep 0`, `autorestart 1` — az áram-visszatérés útja rendben |

## 2. ⚠️ ÚJ HIBAALAK — a dokumentált FileVault-modell PONTOSÍTÁSA

Az eddigi leírás (04-risks, [[mac-mini-connectivity]]): *„a Mini a feloldó-képernyőn ragad,
`launchd`/`sshd`/`cron` nem indul"*. **Ma nem ez történt.**

- A gép **teljesen felbootolt** (kernel + `launchd` + `sshd` mind fut 09:07 óta).
- **Az SSH egész nap működött** — bármilyen SSH-alapú health-check **ZÖLDET** mutatott volna.
- **A `cron` viszont csak a konzol-loginkor indult el.** macOS-en a `/usr/sbin/cron` launchd
  on-demand job; a login-ablakban **nem indult el**.

> 🔴 **Következmény, amit rögzíteni kell: az SSH-elérhetőség NEM egészség-jelzés a cron-láncra.**
> A gép „fent van és válaszol" állapotban **teljes némasággal** kihagyhat egy egész kereskedési napot.

**Másodlagos rés:** a `monitor_submit_heartbeat.py` (15:45) **maga is cron-job** — vagyis
**nem tudja detektálni, hogy a cron nem fut**. Az őrkutya a megfigyelt rendszeren belül van.
Egy valódi detektáláshoz **külső** (nem a Minin futó) heartbeat kell.

## 3. Mi maradt el ma

| Idő (CEST) | Job | Státusz | Következmény |
|---|---|---|---|
| 10:10 | `monitor_positions.py` | ❌ | — |
| **14:30** | `deploy_intraday.sh` (Phase 4-6) | ❌ | **nincs mai trade-terv** |
| 15:25 | `check_gateway.py` | ❌ | a Gateway-hiány nem lett jelezve |
| **15:30** | `close_positions.py --mode=eod_flags` | ❌ | **EQH MENTAL_SL + DLB TP1 NEM futott** |
| **15:31** | `submit_orders.py` | ❌ | **nincs mai belépő** |
| 15:45 | `monitor_submit_heartbeat.py` | ❌ | az őrkutya sem futott (§2) |
| **21:40** | `close_positions.py --mode=time_stop` | ⏳ **MÉG MEGMENTHETŐ** | SN + FBIN TIME_STOP |
| 22:00–22:45 | eod_eval → metrics → eod → reconcile → review_data | ⏳ várhatóan lefut | a `cron` 17:35 óta él |

## 4. 🔴 IDŐKRITIKUS — Tamás teendője (Mini terminál)

> A tőzsde **22:00 CEST**-kor zár. A 21:40-es cron **le fog futni** (a `cron` él), **de csak akkor
> tud rendelést adni, ha fut az IB Gateway.** Jelenleg **nem fut**.

**(1) Gateway indítása — ez a 21:40-es ablak feltétele:**
```bash
open ~/Applications/"IB Gateway 10.43"/"IB Gateway 10.43.app"
# bejelentkezés a paper accountba (DUH118657), majd ellenőrzés:
cd ~/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/check_gateway.py
```

**(2) DÖNTÉS a 15:30-kor elmaradt két exitről** — `EQH` MENTAL_SL és `DLB` TP1.
A piac még **nyitva** (≈22:00-ig), tehát ma is végrehajthatók:
```bash
cd ~/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py --mode=eod_flags
```
| Ticker | Flag | Tegnapi záró | **Mai állás (17:50)** | Elmozdulás |
|---|---|---|---|---|
| EQH | MENTAL_SL | −$481,42 | **−$363,10** | **+$118,32** (javult) |
| DLB | TP1 (50%) | +$209,56 | **+$302,62** | **+$93,06** (javult) |

⚠️ **Mindkét késés jelenleg KEDVEZ** — de ez **nem** érv a halasztás mellett: a §5 kizárási elv
szerint a probléma a **végrehajtás időpontja**, nem a veszteség iránya (a korábbi 4 késett exit
mindegyike rosszabbul zárt, de a mechanizmus **elvben kétirányú**). **A döntés a tiéd.**

**(3) Amit NEM javaslok pótolni:** a 14:30 `deploy_intraday.sh` + 15:31 `submit_orders.py`.
A swing-architektúra **következő-napi MKT-open belépőre** épül; egy ~4 órával a nyitás utáni,
elavult terv alapján adott belépő **spec-en kívüli**. **Ma maradjunk belépő nélkül.**

## 5. Rendszerszintű javaslat (nem ma, de a következő outage előtt)

| # | Javaslat | Miért |
|---|---|---|
| 1 | **Külső heartbeat** (nem a Minin fut) — pl. a MacBookról napi ellenőrzés, hogy a mai `logs/` fájlok megvannak-e | A cron-on belüli őrkutya elvileg képtelen a „cron nem fut" esetet detektálni (§2) |
| 2 | **`cron` → launchd `RunAtLoad` agent**, vagy a job-ok átvitele `LaunchDaemon`-ba (rendszer-kontextus, login-független) | A user-cron a login-ablakban nem indul el; egy `LaunchDaemon` igen |
| 3 | **Auto-login** (FileVault-döntés csomagban) | A 09:07 → 17:35 közti 8,5 óra pontosan a hiányzó login |
| 4 | A `check_gateway.py` **indítsa is** a Gateway-t, ne csak jelezzen | Ma a Gateway-hiány önmagában is elvitte volna a napot |

## 6. Kapu-hatás (gate-protokoll)

- **Ma valószínűleg NEM lesz §5.1 „outage-nap"**: a 22:00-as eod-lánc a helyreállt cronnal
  várhatóan lefut → **lesz `daily_metrics/2026-08-21.json`**, tehát a `verify_outage_days()`
  nem fogja hiányzó napként látni. **Ezt ma este ellenőrizni kell.**
- **§5.2 hatás**: ha az EQH/DLB (és esetleg SN/FBIN) **hétfőre csúszik**, azok
  **outage-késleltetett exitek** lesznek → a §5.2 lista bővül → **`gate_sample.py` módosítás +
  ÚJ PIN**, a protokoll §5.6 szabálya szerint (a futás ELŐTT, indoklással).
- A jelenlegi pin: **`68fc00e`**. Változás esetén az új pin a §5.6-ba és a 04-risks-be kerül.
