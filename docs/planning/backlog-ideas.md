# IFDS Backlog — Ötletek, nem ütemezett

## VectorBT CC Skill (BC20+ scope)

**Forrás:** marketcalls/vectorbt-backtesting-skills repo elemzése (2026-02-24)

**Ötlet:** IFDS-specifikus CC skill(ek) VectorBT parameter sweep-hez, a Phase 4 snapshot adatokon alapulva. Lehetséges fókuszok:
- `/sim-sweep` — min_score, weight_flow/funda/tech, ATR multiplier, hold napok sweep → heatmap + CSV
- `/sim-validate` — SimEngine vs VectorBT párhuzamos futtatás, eredmény összevetés
- `/sim-score` — scoring weight optimalizálás Sharpe alapján

**Miért érdemes:** munkamenet-gyorsítás — egy paranccsal CC végigcsinálja a teljes sweep → heatmap → CSV pipeline-t.

**Előfeltétel:** ~30-40 nap Phase 4 snapshot adat (legkorábban április, BC20 scope).

**Implementáció típusa (még nem döntött):** prompt template + tudásbázis, vagy prompt + kész `ifds_sim_vbt.py` modul.

**Státusz:** PARKOLT — BC20 előtt nem aktuális.
