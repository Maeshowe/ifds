Record a learning in CONDUCTOR memory.

Parse $ARGUMENTS to extract the content and category. Expected format:
- `/learn [category] [content]` — e.g., `/learn discovery A Python SQLite FTS5 triggers need special handling`
- If $ARGUMENTS contains a category keyword (rule, discovery, correction) at the start, use it
- If no category is specified, ask the user which category applies:
  - **rule** — permanent correction, always follow this
  - **discovery** — something new learned, useful context
  - **correction** — a mistake was made, this is the fix

Then run:
```bash
python -m conductor learn --content "<content>" --category "<category>" --project-dir .
```

Parse the JSON output and confirm:
- **Learning saved** — ID, category, content
- **Total learnings** — how many we have now

If category is "rule", note that it was also saved to the central rules (~/.conductor/rules.json).
