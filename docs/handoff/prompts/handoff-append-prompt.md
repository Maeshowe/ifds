# Chat Handoff (Append) — Instruction Prompt

> **Usage**: invoke this prompt when ending a "IFDS — Log Review & Ops" or
> "IFDS — Swing Pivot Dev" chat session. The next chat instance needs to
> pick up seamlessly.

---

You are concluding the current IFDS project chat session. The next chat
instance needs to pick up seamlessly.

## When to use this

Triggered by one of:
1. Context budget approaching ~75% (Claude self-aware signal — flag this proactively
   to the user)
2. Tamás requests explicitly ("fejezzük be ezt a chat-et" or "/handoff")
3. Friday 22:00 weekly summary (for Log Review chat)
4. Major milestone reached (e.g. Phase 1 cleanup complete)

## Your task

Create or append to a handoff document at:
- Log Review chat: `docs/handoff/YYYY-MM-DD-log-review-handoff.md`
- Swing Pivot Dev chat: `docs/handoff/YYYY-MM-DD-swing-dev-handoff.md`

If the same day already has a handoff file, **append a new dated section** rather
than overwriting. Format: `## Append — HH:MM CET — {reason}`.

## Handoff structure

```markdown
# {Chat name} Handoff — YYYY-MM-DD

## TL;DR (30-second pickup)
[1-2 sentences: where we left off, what the next chat should do first]

## What this chat session covered
- Days reviewed: [list of YYYY-MM-DD review files created]    ← Log Review only
- Tasks drafted: [list of docs/tasks/* files]                  ← Dev only
- Design docs: [list of docs/design/* files]                   ← Dev only
- Patterns observed: [bullet list]
- Backlog candidates surfaced: [reference to 04-risks-and-open-questions.md
  item numbers, or NEW items]

## Current state snapshot
- Paper trading day: [N/63 of new run, OR "pre-Phase 3 transition"]
- Cumulative P&L: $X (week / since reset)
- VIX: X, BMI: X, MID regime: X
- Active P0/P1/P2 incidents: [bullet list — P0 means URGENT]

## Open items for next chat
[Numbered list. Each item: what, why, where to look]

## Cross-chat sync notes
What the OTHER chat should be aware of (filesystem updates that occurred):
- `docs/master-reference/04-risks-and-open-questions.md` — added/modified item #X
- `docs/planning/backlog-ideas.md` — new idea
- `docs/STATUS.md` — milestone update

## Files modified this session
[List of full paths written/edited]

## Next action (one line recommendation)
[E.g. "Next chat should start by reading the new 04-risks #P0 item about ..."]
```

## Important behaviors

- **Respond in Hungarian**.
- Keep it **terse but complete** — the next instance reads this first.
- **Do not repeat** content already in the daily reviews or task files — link instead.
- If structural patterns matured into backlog candidates, **explicitly state**
  whether they were written to `04-risks-and-open-questions.md` or are
  pending (open item for next chat).
- End with a single-line "next action" recommendation.

## Proactive 75% trigger

When context usage approaches ~75%, **proactively** inform the user:

> ⚠️ A chat kontextus ~75%-on jár. Javaslom a handoff doc elkészítését,
> mielőtt elfogy a maradék token. Folytatjuk?

Do not wait for the user to ask. The earlier the handoff, the better the quality.

## Multiple handoffs per day

If the same chat day requires multiple handoffs (e.g. context reset mid-day),
use the append format with timestamps:

```markdown
## Append — 14:30 CET — context reset
[content]

## Append — 19:45 CET — chat-end summary
[content]
```

The most recent append represents the current state.
