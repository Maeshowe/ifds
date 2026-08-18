Status: DONE
Updated: 2026-08-18
Note: Tamás-döntés — az Unusual Whales adatforrás KIVEZETVE, nincs használatban. A döntés a Day 90 UW dark-pool Bayesian rekalibrációt is ejti, és adat-proveniencia tényként a kapu-riportba kerül.

# Döntési rekord — Unusual Whales (UW) kivezetés

## A döntés

**Tamás, 2026-08-18: az Unusual Whales adatforrást KIVEZETTÜK. Nincs használatban.**

Ez a 2026-07-17-i review óta nyitott P1 ügy (`docs/handoff/2026-08-18-review-session-handoff.md` §2/4)
lezárása. A két felkínált út közül — *(a) pótoljuk a kulcsot*, *(b) tudatosan a Polygon-úton maradunk
és a tervet módosítjuk* — a **(b)** született meg, azzal, hogy a UW nem csak fallbackre szorul,
hanem **kivezetésre kerül**.

## A tényállás a döntés pillanatában

| Tétel | Állapot |
|---|---|
| UW API-kulcs a Mini `.env`-jében | **2026-06-24 óta hiányzik** (`API_HEALTH_CHECK: unusual_whales → skipped`) |
| UW API-kulcs a fejlesztői `.env`-ben | kikommentelve (`# IFDS_UW_API_KEY=…`) |
| Pipeline-hatás | **nincs** — dokumentált fallback aktív (`API_FALLBACK: primary=unusual_whales, fallback=polygon`) |
| Phase 5 egészség (08-17) | 79 analyzed / 73 passed / 6 GEX-exclusion / mms_count 79 — **normál** |
| GEX-forrás | **Polygon-only**, log-igazolt a 2026-06-24-i flip post-verify óta (04-risks §11.7) |
| `uw_gex_fetch_enabled` | `True` (dormant default), de a Mini `prod_overrides.json` `false`-ra állítja |

Vagyis a rendszer **~2 hónapja de facto UW nélkül fut**, bizonyítottan stabilan. A döntés ezt az
állapotot teszi **de jure** véglegessé.

## Miért ez a helyes döntés (a döntés indoklása, nem utólagos igazolása)

1. **A UW-jel életképessége már korábban megdőlt.** A 2026-06-18-i de-scope elemzés
   (`docs/analysis/uw-feed-descope-2026-06-18.md`) a dark-pool shadow-mintát **n=69**-nél találta —
   ez **nem elég** a Day 90-re tervezett Bayesian rekalibrációhoz. A minta azóta sem nőtt
   (a shadow-írás a kulcs hiányával elhalt), és a 2026-05-19-i test-env-hygiene incidens
   (04-risks, `write_shadow_snapshot` patch-eletlen) egy teljes napot ireverzibilisen elvitt belőle.
2. **A flip output-invariáns volt.** A `uw_gex_fetch_enabled=False` átállás
   bizonyítottan nem változtatta a kimenetet (`source=uw` == 0/92 nap + live on/off diff PASS,
   commit `cd0841a`). A UW eltávolítása tehát **nem viselkedés-változás**.
3. **Költség/haszon.** A közös MID+IFDS előfizetés amúgy is megszűnt (2026-07-04); a UW
   újraaktiválása fizetős, miközben az egyetlen tervezett felhasználója (a Day 90 rekalibráció)
   input-hiány miatt már nem kivitelezhető.

## Következmények — mit von maga után

### 1. A Day 90 UW dark-pool Bayesian rekalibráció **TÖRÖLVE**
Nem elhalasztva — **ejtve**. Input nélkül nem kivitelezhető, és a bemenő minta (n=69, hiányos)
a döntés pillanatában sem volt elégséges. A roadmap érintett tétele ennek megfelelően zárul.

### 2. Adat-proveniencia tény a kapu-riportba (KÖTELEZŐ)
> A 2026-09-22-i kapu-minta **GEX/dark-pool jele Polygon-forrásból** származik, nem UW-ből.
> Ez a **teljes swing-érára** igaz (a flip 2026-06-24-én zárult le, a kulcs ugyanekkor tűnt el),
> tehát a minta ebből a szempontból **homogén** — nem éra-keveredés (nincs G5-sértés).

Ez a mondat a kapu-riportban **szó szerint idézendő**, ahogy a §D3/M korlát is.

### 3. Amit NEM változtatunk most (freeze-fegyelem a kapuig)
A UW-hez kötődő **kódutak a helyükön maradnak** 2026-09-22-ig:
`uw_gex_fetch_enabled` flag, `unusual_whales_api_key` config-kulcs, `uw_shadow.py`,
`scripts/analysis/uw_quick_wins_verification.py`, `gex_live_onoff_diff.py`.

**Indok:** ezek jelenleg **dormant** ágak (a flag `false`, a kulcs `None`), tehát a kereskedési
viselkedést nem érintik. A takarításuk **output-invariáns cleanup** lenne — de a kapu-ablak
40%-a (25/63 trading nap) a freeze-feloldás UTÁNRA esik (lásd az összefoglaló-dokumentumot),
és a felesleges prod-churn ott kockázat haszon nélkül. **A dead-code takarítás a kapu UTÁNI
tétel**, saját taskkal.

### 4. `.env` higiénia
A kikommentelt `# IFDS_UW_API_KEY=…` sor **kulcsot tartalmaz** a fejlesztői `.env`-ben.
Mivel a szolgáltatást kivezettük, ez a kulcs **rotálandó/visszavonandó a UW oldalán**,
és a sor törlendő mindkét gépen. *(Tamás futtatja; a `.env` nincs verziókövetve.)*

## Kereszthivatkozások
- Gate-protokoll: `docs/planning/2026-07-25-gate-protocol-preregistration.md` (§D3/M mellett a
  proveniencia-mondat)
- Kockázati regiszter: `docs/master-reference/04-risks-and-open-questions.md` **§11.14**
- Előzmény: `docs/analysis/uw-feed-descope-2026-06-18.md` (n=69 de-scope),
  04-risks §11.6 (flag), §11.7 (flip post-verify)
