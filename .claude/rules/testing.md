# Testing Rules

- Minden commit elott KOTELEZO: `python -m pytest tests/ -q`
- 0 failure, 0 warning a minimum — ne commitolj piros tesztekkel
- Uj feature → uj tesztek (legalabb happy path + 1 edge case)
- Mock: AsyncMock csak valoban async kodutnl, kulonben MagicMock
- Jelenlegi baseline: 861 passing (2026-02-26) — ez csak nohet
