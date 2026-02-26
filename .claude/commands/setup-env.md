Te most a CONDUCTOR DevOps Agent vagy. Feladatod: runtime környezet vizsgálat és dokumentálás.

Olvasd el az agent definíciót:
```bash
cat .conductor/agents/devops.md
```

## Környezet vizsgálat

Futtasd a környezet ellenőrzést:
```bash
python -m conductor setup-env check
```

## Eredmény értelmezése

Az output JSON tartalmazza:
- **python:** Python verzió
- **platform:** operációs rendszer
- **venv:** virtuális környezet elérési útja (vagy null)
- **venv_active:** van-e aktív venv
- **dependencies:** pyproject.toml-ból olvasott függőségek

## Problémák jelzése

Ellenőrizd:
1. Van-e aktív venv? (macOS-en PEP 668 miatt kötelező)
2. A Python verzió megfelelő-e? (3.10+ ajánlott)
3. A függőségek telepítve vannak-e?
4. Van-e pyproject.toml?

Ha hiányosság van → adj konkrét javaslatot a javításra.

## Opcionális mentés

Kérdezd meg: „Mentsem a környezet snapshot-ot?"

Ha igen:
```bash
python -m conductor setup-env save --data '{"python": "...", "platform": "...", "venv": "...", "dependencies": [...]}'
```

Ez learning-ként mentődik (category: "environment"), így kereshető FTS5-tel.
