# Task: pyproject.toml — pytest PYTHONPATH fix

**Date:** 2026-02-25
**Priority:** LOW — developer experience, azonnali
**Scope:** `pyproject.toml`
**Effort:** 1 sor

---

## A probléma

A tesztek jelenleg csak `PYTHONPATH=src pytest` paranccsal futnak.
`pytest` önmagában ImportError-t dob, mert a `src/` layout nem szerepel a Python path-ban.

## Fix

A `pyproject.toml` `[tool.pytest.ini_options]` szekciójába add hozzá:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

## Ellenőrzés

```bash
# Ezután mindkét formának működnie kell:
pytest
PYTHONPATH=src pytest  # visszafelé kompatibilis marad
```

## Git

```bash
git add pyproject.toml
git commit -m "chore: pytest pythonpath fix — src layout (pyproject.toml)"
git push
```
