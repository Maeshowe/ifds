Emergency save — immediately pause the current CONDUCTOR session. No questions, no delays.

```bash
python -m conductor pause --project-dir $ARGUMENTS
```

If $ARGUMENTS is empty, use the current working directory.

Parse the JSON output and confirm:
- **Session paused** — ID and timestamp
- **State saved** — confirmation
- **Resume with** `/continue` when ready

Keep the response short — this is an emergency command.
