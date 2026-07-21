Status: DRAFT
Updated: YYYY-MM-DD
Data-lane: v1
Attempt-family: —

# HYP-### — <cím>

> **a/b aszimmetria-szabály (spec §8.2):** a transzform-szintű (a) változat az
> ÉLŐ pipeline-transzformot minősíti (EWMA, küszöbök, sign-flip együtt), NEM a
> mögöttes nyers jelet. Az a-eredmény a b-hipotézisre nézve **sem megerősítés,
> sem cáfolat** — külön attempt-családok, külön fájl.

## Mechanizmus (MIÉRT létezne — kötelező, teszt ELŐTT írva)

<Közgazdasági/mikrostruktúrás indoklás. Ha ide nem írható le, hogy miért
létezne a jel, a hipotézis nem regisztrálható.>

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
