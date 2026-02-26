# Security Rules

- API kulcsokat SOHA ne commitolj — csak `.env`-ben
- `.env` mindig `.gitignore`-ban van
- `*.env*` pattern a `.gitignore`-ban ellenorizendo minden commit elott
- Secrets logba SOHA nem kerulnek — log uzeneteknl maszkold az API key-eket
- Paper trading: IBKR paper account (DUH118657) — nem live account
