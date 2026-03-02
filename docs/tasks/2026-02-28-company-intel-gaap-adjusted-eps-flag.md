# Task: Company Intel — GAAP vs Adjusted EPS distinction in CONTRADICTION section

**Date:** 2026-02-28  
**Priority:** 🟡 Quality improvement  
**File:** `scripts/company_intel.py`

---

## Problem

The `CONTRADICTION` section in company intel briefs can produce false positives.

**Root cause:** `fetch_earnings_surprises()` fetches GAAP EPS only. When a company has
large one-time items (merger costs, write-offs, restructuring), GAAP EPS can show a
catastrophic miss while adjusted (non-GAAP) EPS is positive — and the market prices
the adjusted figure.

**Real example (2026-02-27):**
- NXST Q4 2025: GAAP EPS = -$5.63 → GAAP miss = -236.5%
- NXST adjusted EPS = positive → market priced this correctly
- Intel brief flagged "CONTRADICTION" correctly in form, but the LLM lacked adjusted
  EPS context to explain it — the flag was technically accurate but misleading without
  the full picture

---

## Fix

### 1. Add `fetch_earnings_surprises_adjusted()` — new function

Use FMP `/stable/income-statement` to fetch the last 4 quarters and extract
`epsdiluted` (GAAP) alongside `eps` or derived adjusted figure.

A simpler approach: FMP `/stable/analyst-estimates` contains both GAAP and adjusted
EPS estimates. Alternatively, flag when GAAP surprise is extreme (< -50%) and note
that adjusted figures may differ.

**Recommended approach — minimal change, maximum signal:**

In `fetch_earnings_surprises()`, add a `large_miss_flag` field when
`surprisePct < -50`:

```python
results.append({
    "date": item.get("date", "?"),
    "actualEarningResult": actual,
    "estimatedEarning": estimated,
    "surprisePct": surprise_pct,
    "large_miss_flag": surprise_pct is not None and surprise_pct < -50,
})
```

### 2. Update the prompt — CONTRADICTION section

In `generate_brief()`, add a note to the earnings section when large GAAP misses exist:

```python
# Build earnings text — flag large misses
lines = []
has_large_gaap_miss = False
for s in surprises:
    ...
    if s.get("large_miss_flag"):
        has_large_gaap_miss = True
        lines.append(f"  {dt}: Actual={actual}, Est={est} → MISS{pct_str} ⚠ LARGE GAAP MISS — adjusted EPS may differ")
    else:
        lines.append(f"  {dt}: Actual={actual}, Est={est} → {beat}{pct_str}")
```

And update the CONTRADICTION instruction in the prompt:

```python
# BEFORE:
CONTRADICTION: [Does anything in the data contradict the high IFDS score ({score})?
E.g. serial earnings misses + high score, price above analyst target, analyst downgrades.
If none: "No contradiction identified." 1 sentence.]

# AFTER:
CONTRADICTION: [Does anything in the data contradict the high IFDS score ({score})?
E.g. serial earnings misses + high score, price above analyst target, analyst downgrades.
IMPORTANT: If a large GAAP miss (< -50%) is flagged, note that GAAP figures may include
one-time items (merger costs, write-offs) and adjusted EPS may differ significantly —
do NOT treat a single large GAAP miss as a definitive contradiction without context.
If none: "No contradiction identified." 1 sentence.]
```

### 3. Update beat count logic

The `beats` counter in `format_cli_ticker()` and `format_telegram_ticker()` currently
counts GAAP beats only. Add a note in the earnings summary line when large misses exist:

```python
# BEFORE:
earnings_line = f"{beats}/{n} beat (last {n}Q)" if n > 0 else "N/A"

# AFTER:
gaap_note = " *GAAP" if any(s.get("large_miss_flag") for s in surprises) else ""
earnings_line = f"{beats}/{n} beat (last {n}Q){gaap_note}" if n > 0 else "N/A"
```

---

## Testing

```bash
# Run company intel manually on yesterday's execution plan
python scripts/company_intel.py

# Verify:
# 1. Large GAAP misses (< -50%) get ⚠ LARGE GAAP MISS flag in earnings section
# 2. CONTRADICTION section notes adjusted EPS caveat for flagged tickers
# 3. Earnings summary line shows "*GAAP" note when applicable
# 4. Normal misses (e.g. -5%) are unaffected
```

**Edge cases to verify:**
- `surprisePct = None` (no estimate available) → no flag, no crash
- All beats → no flag, no change in output
- Multiple large misses in same ticker → flag shown for each

---

## Git commit

```
feat(company_intel): flag large GAAP misses in CONTRADICTION section

Add large_miss_flag when GAAP EPS surprise < -50%. Update LLM prompt
to distinguish GAAP vs adjusted EPS context. Add *GAAP note to beat
count summary. Prevents false-positive CONTRADICTION flags from
one-time accounting items (merger costs, write-offs).

Triggered by: NXST Q4 2025 GAAP miss -236.5% vs positive adjusted EPS
```
