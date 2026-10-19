# Aukciós kilépés — ellenpróba a valódi könyvön

**Dátum:** 2026-10-19
**Script:** `scripts/analysis/auction_exit_counterfactual.py` (read-only, reprodukálható)
**Előzmény:** `docs/review/2026-10-19-execution-wall-by-horizon.md` §2.3 — a „C forgatókönyv"
ott **felső korlát** volt, nem terv. Ez a futás megméri.

---

## 0. A premissza — a production evaluátorból olvasva, nem feltételezve

A `swing_positions.evaluate_position_eod` szerint a két kilépési család **nem egyforma**:

| akció | trigger | legkorábbi elérhető aukció | kitettség |
|---|---|---|---|
| **TP1 / TP2** | `today_high` → **intraday** | **ugyanaz a nap záróaukciója** | **−1 overnight** |
| **MENTAL_SL / HARD_SL / TRAIL_SL** | `today_close` | **a KÖVETKEZŐ nap zárója** | **+1 session** |
| TIME_STOP | `days_held ≥ 5` | már most MOC | változatlan |

Egy „tegyünk mindent aukcióba" szám ezért **értelmezhetetlen** lenne: az egyik család
időt nyer, a másik veszít. Külön mérve, és a két előjel mindig látszik.

---

## 1. Eredmény

Az aukciós fill a **mért** aukciós súrlódással terhelve (+1,35 bp, 68 MOC-kilépésen),
nap-klaszterezett bootstrap CI:

| | n | **nettó** | 95% CI | jobb lett |
|---|---:|---:|---|---:|
| **TP1/TP2 → ugyanaznapi záró** | 29 | **+783 $** | **[+244, +1 460]** | **23/29** |
| SL-család → következő napi záró | 11 | +381 $ | [−395, +1 104] | 7/11 |
| *együtt (csak referenciaként)* | 40 | *+1 164 $* | *[+181, +2 190]* | *30/40* |

Típusonként: TP1 **+544 $** [+171, +891] · TP2 **+239 $** [+21, +597] ·
MENTAL_SL +335 $ [−434, +1 055] · TRAIL_SL +46 $ (n=1).

> ✅ **A TP1/TP2 csere szignifikáns.** A CI nem tartalmazza a nullát, és a lábak
> 79%-a javult.
> ⚠️ **Az SL-család nem szignifikáns** (n=11, a CI átlépi a nullát) — irányban
> pozitív, de önmagában nem állítás.

---

## 2. Háromfelé bontás — csak az első hasáb él

| család | **súrlódás-megszűnés** | óramozgás | aukciós költség | nettó | notional |
|---|---:|---:|---:|---:|---:|
| TP1/TP2 | **+536 $** | +259 $ | −13 $ | +783 $ | 93 396 $ |
| SL-család | **+366 $** | +22 $ | −7 $ | +381 $ | 54 475 $ |

- **Súrlódás-megszűnés = +902 $, a nettó 78%-a.** Ez a mechanikus, **ismétlődő** rész:
  egy csengő utáni market ~60 bp-t ad fel, egy aukció ~1,4 bp-t, **minden alkalommal**.
- **Óramozgás = +281 $, a nettó 24%-a.** Ez **hozam, nem súrlódás**: a TP1-nél az
  elkerült overnight rés, az SL-nél egy plusz session kitettsége. **Ez nem él** — a minta
  saját árútja. Az SL-családnál ez ~nulla (+22 $ / 54 475 $ = +4 bp), vagyis a plusz
  session ebben a mintában nem fájt, de n=11.

---

## 3. Tape-kontroll — nem egy emelkedő piacot mérünk?

| | n | átlag | medián | 95% CI |
|---|---:|---:|---:|---|
| `open→close` a kereskedett neveken, **az egész érán** | 6 506 név-nap | **+2,0 bp** | −1,4 bp | **[−2,7; +6,6]** |
| ugyanez a **40 használt aukciós napon** | 40 | **+142,9 bp** | +119,6 bp | — |

Az éra-szintű szám **átlépi a nullát** → nincs emelkedő-tape artefakt a populációban.

A kiválasztott napok erősen pozitívak — de ez **szelekció a triggerre** (a TP1 akkor
tüzel, amikor a `high` felszaladt), és **más szakaszon** van, mint az ellenpróba: az
ellenpróba csak az **overnightot** lépi át, nem a trigger-nap intradayét. **Ellenőriztem;
nem kerül bele a becslésbe.** A trigger-szelekció viszont indokolja, miért lehet az
overnight utána szisztematikusan más (poszt-felszaladás reverzió) — ezért az óramozgást
nem számolom edge-nek.

---

## 4. Mit mond ez a falról

A §2.3-ban a „C forgatókönyv" (minden aukciós, round trip **2,7 / 7,9 bp**) **felső
korlát** volt. Most pontosítható:

| | állapot |
|---|---|
| **TIME_STOP** (a kilépések 63%-a) | **már aukciós** |
| **TP1/TP2** (29 láb) | aukcióba tehető, **nettó +783 $ szignifikánsan** → a C ezen a részen **valódi** |
| **SL-család** (11 láb) | aukcióba tehető, nettó +381 $ **nem szignifikáns** → a C ezen a részen **nem bizonyított** |

Vagyis a C-fal **nagyobbik része megalapozott**: a drága 40 lábból 29 bizonyítottan
nyer az aukciós úton. A maradék 11-re a mérés irányban pozitív, de n=11.

---

## 5. Nagyságrend — hova illeszkedik

A könyv 88 nap alatt **−6 460,95 $**-t vesztett. Ez a javítás **+1 164 $**, azaz a
veszteség **~18%-a** — és az eddig mért legnagyobb egyedi mechanikai javítás
(SIM-1 exit-geometria: **−8 $**; SIM-EXEC limit-belépő: +2 442 $, de az
stratégia-változás volt). **Nem menti meg a stratégiát**, de a végrehajtási oldal
az egyetlen hely, ahol eddig ismételhető, mechanikus pénzt találtunk.
