## Módosítások az ifds-log-review-prompt-v3.md fájlhoz

### 1. Elemzés Válasz Struktúra — fill rate hozzáadása

A "Paper Trading Eredmény" ELÖTT add hozzá:

```
### Fill Rate
- Execution plan: X ticker | Filled: X | Unfilled: X | Fill rate: XX%
- Unfilled: [tickerek listája + ok]
```

### 2. Review Checklist Sablon — fill rate szekció hozzáadása

A "## Paper Trading P&L" szekció ELÖTT add hozzá:

```markdown
## Fill Rate & Execution
- Execution plan: ___ ticker | Filled: ___ | Unfilled: ___ | Fill rate: ___%
- Unfilled tickerek: _______________
- Unfill oka: [limit nem teljesült / AVWAP nem triggerelt / IBKR hiba]
```

### 3. Mit keresünk — Submit Log bővítés

A "### 3. Submit Log" szekcióba add hozzá:
```
- Fill rate: hány ticker-ből hány teljesült (limit + AVWAP MKT fallback összesen)
```

### Teljes szöveg a cserékhez:

RÉGI (Elemzés Válasz Struktúra):
```
### Paper Trading Eredmény
```

ÚJ:
```
### Fill Rate
- Execution plan: X ticker | Filled: X | Unfilled: X | Fill rate: XX%
- Unfilled: [tickerek + ok]

### Paper Trading Eredmény
```

---

RÉGI (Checklist Sablon):
```
## Paper Trading P&L
- Napi P&L: $_________
```

ÚJ:
```
## Fill Rate & Execution
- Execution plan: ___ ticker | Filled: ___ | Unfilled: ___ | Fill rate: ___%
- Unfilled tickerek: _______________
- Unfill oka: [limit nem teljesült / AVWAP nem triggerelt / IBKR hiba]

## Paper Trading P&L
- Napi P&L: $_________
```
