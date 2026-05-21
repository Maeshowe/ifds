Status: DONE
Updated: 2026-03-07
Note: BC17-preflight COMPLETE — kód ellenőrizve 2026-03-07

# Task: BC17 előtt — F-23 validator + F5 silent except + F-16/17 atomic writes + C6/C7 API retry tesztek

**Dátum:** 2026-02-27  
**Prioritás:** 🟡 BC17 előtt  
**QA forrás:** `docs/qa/2026-02-27-verification.md`

---

## Item 1 — F-23: MMS regime multiplier keys validálás (`validator.py`)

### Probléma

A `config/validator.py` nem validálja az MMS rezsim multiplier kulcsokat.
Ha BC17-ben élesítjük az MMS multipliereket (`mms_regime_multipliers` config kulcs),
és egy kulcs elgépelődik (pl. `gamma_positiv` `gamma_positive` helyett),
a pipeline csendben futna rossz multiplierekkel.

### Fix

**`src/ifds/config/validator.py`** — új validáció a `validate_config()` végére:

```python
# --- MMS regime multiplier keys ---
VALID_MMS_REGIMES = {
    "gamma_positive", "gamma_negative", "dark_dominant",
    "absorption", "distribution", "volatile", "neutral", "undetermined",
}
mms_multipliers = config.tuning.get("mms_regime_multipliers", {})
if mms_multipliers:
    unknown = set(mms_multipliers.keys()) - VALID_MMS_REGIMES
    if unknown:
        errors.append(
            f"Unknown MMS regime multiplier keys: {sorted(unknown)}. "
            f"Valid keys: {sorted(VALID_MMS_REGIMES)}"
        )
    for regime, val in mms_multipliers.items():
        if not isinstance(val, (int, float)) or val <= 0:
            errors.append(
                f"MMS regime multiplier '{regime}' must be a positive number, got {val!r}"
            )
```

### Tesztelés

```python
# tests/test_validator_mms.py — új fájl

def test_valid_mms_multipliers_pass():
    config = make_config(mms_regime_multipliers={
        "gamma_positive": 1.0,
        "gamma_negative": 0.65,
        "dark_dominant": 1.1,
    })
    validate_config(config)  # nem dob exception-t

def test_unknown_mms_regime_key_raises():
    config = make_config(mms_regime_multipliers={
        "gamma_positiv": 1.0,  # elgépelés
    })
    with pytest.raises(ConfigValidationError, match="Unknown MMS regime"):
        validate_config(config)

def test_negative_mms_multiplier_raises():
    config = make_config(mms_regime_multipliers={
        "gamma_positive": -0.5,
    })
    with pytest.raises(ConfigValidationError, match="must be a positive number"):
        validate_config(config)

def test_empty_mms_multipliers_pass():
    """Ha nincs mms_regime_multipliers a config-ban, nem validál (BC17 előtt optional)."""
    config = make_config()  # nincs mms_regime_multipliers
    validate_config(config)  # nem dob exception-t
```

---

## Item 2 — F5: Silent `except Exception: pass` logolása (`phase5_gex.py`)

### Probléma

4 helyen van `except Exception: pass` logolás nélkül — ha az MMS analízis
csendben failel, nem látjuk a logban:

**sync path (~sor 118):**
```python
except Exception:
    pass
```

**sync path MMS (~sor ~162 körül, a GEX nélküli ágban):**
```python
except Exception:
    pass
```

**async path (~sor 469):**
```python
except Exception:
    pass
```

**async path MMS (~sor ~520 körül, GEX nélküli ágban):**
```python
except Exception:
    pass
```

### Fix

Mind a 4 `except Exception: pass` blokk cseréje — a MMS-hez tartozó blokkokban
már van `except Exception as mms_err:` logolással, ezt a mintát kell követni
a `pass`-os blokkoknál is:

```python
# ELŐTTE:
except Exception:
    pass

# UTÁNA:
except Exception as e:
    logger.log(
        EventType.PHASE_DIAGNOSTIC, Severity.DEBUG, phase=5,
        ticker=ticker,
        message=f"[MMS] {ticker} collection skipped: {e}",
    )
```

**Fontos:** `Severity.DEBUG` — ezek nem hibák, csak informatív jelzések.
Ne `WARNING`, mert egy-egy ticker MMS adathiánya normális lehet.

### Tesztelés

```bash
python -m pytest tests/ -k "phase5 or gex" -v
# Meglévő tesztek mind pass-oljanak
```

Manuális ellenőrzés: a logban ne legyen `except Exception: pass` a phase5_gex.py-ban:
```bash
grep -n "except Exception:" src/ifds/phases/phase5_gex.py
# Csak az `as e:` formák maradjanak
```

---

## Item 3 — F-16/17: Atomic file write-ok (Phase 2, Phase 4, Phase 6)

### Probléma

Ha a pipeline a JSON/Parquet írás közben leáll (crash, SIGKILL, disk full),
a fájl félkész állapotban marad. A következő futás korrupt adatot olvas be.

**Érintett helyek:**
- Phase 2: universe output JSON (ha van ilyen mentés)
- Phase 4: `phase4_snapshot.py` — snapshot Parquet/JSON írás
- Phase 6: `state/daily_trades.json`, `state/daily_notional.json`, `signal_history.parquet`

### Atomic write minta

```python
import os
import tempfile
from pathlib import Path

def atomic_write_json(path: str | Path, data: dict | list) -> None:
    """Write JSON atomically using temp file + rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to temp file in same directory (same filesystem → rename is atomic)
    with tempfile.NamedTemporaryFile(
        mode='w', dir=path.parent, suffix='.tmp',
        delete=False, encoding='utf-8'
    ) as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        tmp_path = f.name
    os.replace(tmp_path, path)  # atomic on POSIX

def atomic_write_parquet(path: str | Path, df) -> None:
    """Write Parquet atomically using temp file + rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, suffix='.tmp', delete=False
    ) as f:
        tmp_path = f.name
    df.to_parquet(tmp_path, index=False)
    os.replace(tmp_path, path)
```

**Implementáció:** Hozz létre egy `src/ifds/utils/io.py` helper modult
`atomic_write_json()` és `atomic_write_parquet()` függvényekkel,
majd cseréld ki az érintett `open(..., 'w')` + `json.dump()` hívásokat.

**Érintett fájlok pontosan:**
- `src/ifds/data/phase4_snapshot.py` — snapshot mentés
- `src/ifds/phases/phase6_sizing.py` — `_save_daily_counter()`
- `src/ifds/phases/phase6_sizing.py` — `_apply_freshness_alpha()` parquet írás

### Tesztelés

```python
# tests/test_atomic_write.py

def test_atomic_write_json_creates_file(tmp_path):
    path = tmp_path / "test.json"
    atomic_write_json(path, {"key": "value"})
    assert path.exists()
    assert json.loads(path.read_text()) == {"key": "value"}

def test_atomic_write_json_no_partial_on_error(tmp_path):
    """Eredeti fájl érintetlen marad ha az írás failel."""
    path = tmp_path / "existing.json"
    path.write_text('{"original": true}')
    # Szimulálj írási hibát — nehéz, de legalább ellenőrizd hogy
    # tmp fájl nem marad a könyvtárban normál esetben
    atomic_write_json(path, {"new": "data"})
    assert json.loads(path.read_text()) == {"new": "data"}
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0  # nincs maradék .tmp

def test_atomic_write_parquet(tmp_path):
    import pandas as pd
    df = pd.DataFrame({"ticker": ["AAPL"], "date": ["2026-01-01"]})
    path = tmp_path / "test.parquet"
    atomic_write_parquet(path, df)
    result = pd.read_parquet(path)
    assert list(result["ticker"]) == ["AAPL"]
```

---

## Item 4 — C6/C7: API retry tesztek (`test_base_client.py` + `test_async_base_client.py`)

### Probléma

A `BaseAPIClient` és `AsyncBaseAPIClient` retry logikájához nincs teszt.
Ha a retry viselkedés megváltozik (pl. backoff módosítás), nem detektáljuk.

### Fix — `tests/test_base_client.py` (új fájl)

```python
"""Tests for BaseAPIClient retry logic."""
import pytest
from unittest.mock import MagicMock, patch
import requests

from ifds.data.base import BaseAPIClient


class ConcreteClient(BaseAPIClient):
    def __init__(self, **kwargs):
        super().__init__(base_url="https://api.example.com", **kwargs)


class TestBaseClientRetry:

    def test_retry_on_500_then_success(self):
        """Retry on 5xx, succeed on 2nd attempt."""
        client = ConcreteClient(max_retries=3, timeout=5)
        mock_resp_500 = MagicMock()
        mock_resp_500.status_code = 500
        mock_resp_500.raise_for_status.side_effect = requests.HTTPError(
            response=mock_resp_500
        )
        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.raise_for_status.return_value = None
        mock_resp_200.json.return_value = {"ok": True}

        with patch.object(client._session, 'get',
                          side_effect=[mock_resp_500, mock_resp_200]):
            result = client._get("/test")
        assert result == {"ok": True}

    def test_no_retry_on_404(self):
        """4xx (except 429) — no retry, immediate return None."""
        client = ConcreteClient(max_retries=3, timeout=5)
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = requests.HTTPError(
            response=mock_resp
        )

        with patch.object(client._session, 'get', return_value=mock_resp) as mock_get:
            result = client._get("/test")
        assert result is None
        assert mock_get.call_count == 1  # no retry

    def test_retry_on_429_rate_limit(self):
        """429 rate limit triggers retry."""
        client = ConcreteClient(max_retries=3, timeout=5)
        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429
        mock_resp_429.raise_for_status.side_effect = requests.HTTPError(
            response=mock_resp_429
        )
        mock_resp_200 = MagicMock()
        mock_resp_200.status_code = 200
        mock_resp_200.raise_for_status.return_value = None
        mock_resp_200.json.return_value = {"ok": True}

        with patch.object(client._session, 'get',
                          side_effect=[mock_resp_429, mock_resp_200]), \
             patch('time.sleep'):
            result = client._get("/test")
        assert result == {"ok": True}

    def test_all_retries_exhausted_returns_none(self):
        """All retries fail → return None, no exception raised."""
        client = ConcreteClient(max_retries=3, timeout=5)
        with patch.object(client._session, 'get',
                          side_effect=requests.exceptions.ConnectionError("refused")), \
             patch('time.sleep'):
            result = client._get("/test")
        assert result is None

    def test_timeout_triggers_retry(self):
        """Timeout triggers retry up to max_retries."""
        client = ConcreteClient(max_retries=2, timeout=5)
        with patch.object(client._session, 'get',
                          side_effect=requests.exceptions.Timeout()), \
             patch('time.sleep') as mock_sleep:
            result = client._get("/test")
        assert result is None
        assert mock_sleep.call_count == 1  # sleep between attempt 1 and 2
```

### Fix — `tests/test_async_base_client.py` (új fájl)

```python
"""Tests for AsyncBaseAPIClient retry logic."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from ifds.data.async_base import AsyncBaseAPIClient


class ConcreteAsyncClient(AsyncBaseAPIClient):
    def __init__(self, **kwargs):
        super().__init__(base_url="https://api.example.com", **kwargs)


class TestAsyncBaseClientRetry:

    @pytest.mark.asyncio
    async def test_retry_on_500_then_success(self):
        """Retry on 5xx, succeed on 2nd attempt."""
        client = ConcreteAsyncClient(max_retries=3, timeout=5)
        mock_session = AsyncMock()

        resp_500 = AsyncMock()
        resp_500.status = 500
        resp_500.__aenter__ = AsyncMock(return_value=resp_500)
        resp_500.__aexit__ = AsyncMock(return_value=False)

        resp_200 = AsyncMock()
        resp_200.status = 200
        resp_200.json = AsyncMock(return_value={"ok": True})
        resp_200.__aenter__ = AsyncMock(return_value=resp_200)
        resp_200.__aexit__ = AsyncMock(return_value=False)

        mock_session.get = MagicMock(side_effect=[resp_500, resp_200])
        client._session = mock_session

        with patch('asyncio.sleep'):
            result = await client._get("/test")
        assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_no_retry_on_404(self):
        """4xx (except 429) — no retry."""
        client = ConcreteAsyncClient(max_retries=3, timeout=5)
        mock_session = AsyncMock()

        resp_404 = AsyncMock()
        resp_404.status = 404
        resp_404.__aenter__ = AsyncMock(return_value=resp_404)
        resp_404.__aexit__ = AsyncMock(return_value=False)

        mock_session.get = MagicMock(return_value=resp_404)
        client._session = mock_session

        result = await client._get("/test")
        assert result is None
        assert mock_session.get.call_count == 1

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_returns_none(self):
        """All retries fail → None, no exception."""
        import aiohttp
        client = ConcreteAsyncClient(max_retries=2, timeout=5)
        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            side_effect=aiohttp.ClientConnectionError("refused")
        )
        client._session = mock_session

        with patch('asyncio.sleep'):
            result = await client._get("/test")
        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_triggers_retry(self):
        """asyncio.TimeoutError triggers retry."""
        client = ConcreteAsyncClient(max_retries=2, timeout=5)
        mock_session = AsyncMock()
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())
        client._session = mock_session

        with patch('asyncio.sleep') as mock_sleep:
            result = await client._get("/test")
        assert result is None
        assert mock_sleep.call_count == 1
```

### Tesztelés

```bash
python -m pytest tests/test_base_client.py tests/test_async_base_client.py -v
# Elvárt: mind pass
python -m pytest --tb=short -q
# Elvárt: 882 + új tesztek passing, 0 failed
```

---

## Git commit javaslat

```
feat(validator,phase5,io,tests): BC17 pre-flight hardening

- validator.py: MMS regime multiplier key validation (F-23)
- phase5_gex.py: replace silent except pass with DEBUG logging (F5)
- utils/io.py: atomic_write_json + atomic_write_parquet helpers (F-16/17)
- phase4_snapshot, phase6_sizing: use atomic writes
- tests/test_validator_mms.py: 3 new tests
- tests/test_atomic_write.py: 3 new tests
- tests/test_base_client.py: 5 new tests (C6)
- tests/test_async_base_client.py: 4 new tests (C7)

Fixes: QA findings F-23, F5, F-16, F-17, C6, C7
```
