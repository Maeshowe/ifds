Run the CONDUCTOR orientation command to show where we are:

```bash
python -m conductor where-am-i --project-dir $ARGUMENTS
```

If $ARGUMENTS is empty, use the current working directory.

Parse the JSON output and present it in a clear, structured format:
- **Project** name and current phase
- **Active session** (when started, how long ago)
- **Open tasks** (list with status)
- **Active decisions** (list)
- **Recent learnings** (last 5)

If there's no active session, suggest running `/continue` to start one.
If CONDUCTOR is not initialized, tell the user to run `python -m conductor init`.
