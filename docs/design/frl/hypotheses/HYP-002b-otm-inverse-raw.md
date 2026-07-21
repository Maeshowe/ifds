Status: DRAFT
Updated: 2026-07-21
Data-lane: v2
Attempt-family: —

# HYP-002B — OTM-inverse — nyers decay-profil (h=1..7)

> **a/b aszimmetria-szabály (spec §8.2):** a transzform-szintű (a) változat az
> ÉLŐ pipeline-transzformot minősíti (EWMA, küszöbök, sign-flip együtt), NEM a
> mögöttes nyers jelet. Az a-eredmény a b-hipotézisre nézve **sem megerősítés,
> sem cáfolat** — külön attempt-családok, külön fájl.

## Mechanizmus (MIÉRT létezne — kötelező, teszt ELŐTT írva)

<VÁZ — a tartalmat Chat (Dev) tölti. Irány: A nyers OTM-call-ratio jel lecsengési profilja a swing-horizonton.>

> Párja: `HYP-002a-otm-inverse-transform.md` — az a/b aszimmetria-szabály miatt KÜLÖN attempt-család.
>
> **v2 sáv:** nem tesztelhető, amíg az enrichment forward-mintája < 40 nap (D_A).

## Várt előjel és horizont

<+1 vagy −1, és melyik h-nál várjuk a maximumot. Ez a `Factor.expected_sign`,
amivel a sanity-kapu fut.>

## Ki a vesztes oldal / milyen frikció tartja fenn

<Ki fizeti a jelet, és miért nem arbitrálódik el.>

## Költségprofil (várt turnover)

<Várt half-life és turnover; a cost-kapu a `research/cost_model.json` aktuális
empirikus bp/oldal értékén fut, NEM feltevésen.>

## Pre-reg metrika és kill-kritérium

<Melyik metrika dönt, milyen küszöbnél. A kill-kritériumot a teszt ELŐTT
rögzítjük — utólagos lazítás protokollsértés.>

## Eredmény (a batch tölti)

—

## KILL/PARK indoklás (ha releváns)

—
