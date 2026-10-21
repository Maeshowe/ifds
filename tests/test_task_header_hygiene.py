"""Task-file header hygiene — the gap behind the open-task query, not one instance.

Why this exists. `CLAUDE.md` publishes one way to ask "what is still open":

    grep -lE "^Status:[[:space:]]*(OPEN|WIP)" docs/tasks/*.md

That query is anchored on purpose (a body quoting "Status: OPEN" must not count), and
it is non-recursive on purpose (`archive/` is closed work). Both choices mean the query
is only as honest as the headers. A file whose status is written `**Status**: WIP`, or
that carries no status line at all, is INVISIBLE to it — and invisible reads as closed.

This has now happened twice. `docs/tasks/archive/README.md` records the 2026-10-04
correction: twelve files sat in the root with bold status headers, and the README's own
reasoning ("they do not pollute the query") covered for them. On 2026-10-21 the same
class turned up again in five more files — one genuinely WIP (`2026-05-28`, the review
pipeline) and one with no status line whatsoever (`2026-05-23`, state reconciliation),
both of which the query had been silently omitting for five months.

So the fix is not another round of normalisation. It is this test: the format the query
depends on is now enforced where it is depended upon, and the allowlist below is the
only way to opt out — by name, with the reason written down.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

TASKS_DIR = Path(__file__).resolve().parent.parent / "docs" / "tasks"

#: The states a task header may declare. `REJECTED` is here because the archive
#: convention names it (`archive/README.md`): work that was closed without being done.
OPEN_STATES = ("OPEN", "WIP", "BLOCKED")
CLOSED_STATES = ("DONE", "REJECTED")
ALL_STATES = OPEN_STATES + CLOSED_STATES

STATUS_RE = re.compile(rf"^Status:[ \t]+({'|'.join(ALL_STATES)})\b")
UPDATED_RE = re.compile(r"^Updated:[ \t]+(\d{4})-(\d{2})-(\d{2})\s*$")

#: Files under `docs/tasks/` that are NOT tasks and so carry no task header.
#: Each entry needs a reason, and the reason has to survive review — "it is old" does not.
EXEMPT: dict[str, str] = {
    "2026-05-25-operator-emergency-procedure.md": (
        "A living operator runbook, not a unit of work: it is referenced from "
        "scripts/crontab.md, docs/master-reference/04-risks-and-open-questions.md, "
        "docs/handoff/operating-environment.md and tests/test_runner_skip_path.py. "
        "Moving or archiving it would break those paths for no gain, so it stays in "
        "place and stays out of the query."
    ),
}


def _task_files() -> list[Path]:
    """Exactly the files the documented query globs — non-recursive, archive excluded."""
    return sorted(p for p in TASKS_DIR.glob("*.md") if p.name != "README.md")


def _candidates() -> list[Path]:
    return [p for p in _task_files() if p.name not in EXEMPT]


class TestTheHeaderTheQueryDependsOn:
    @pytest.mark.parametrize("path", _candidates(), ids=lambda p: p.name)
    def test_line_one_declares_a_status_the_query_can_see(self, path: Path) -> None:
        first = path.read_text().splitlines()[0] if path.read_text() else ""
        assert STATUS_RE.match(first), (
            f"{path.name}: line 1 must be `Status: <{'|'.join(ALL_STATES)}>`, got {first!r}. "
            "A bold `**Status**:` or a missing line is invisible to the open-task query "
            "in CLAUDE.md, which makes unfinished work read as finished."
        )

    @pytest.mark.parametrize("path", _candidates(), ids=lambda p: p.name)
    def test_line_two_dates_the_status(self, path: Path) -> None:
        lines = path.read_text().splitlines()
        assert len(lines) > 1 and UPDATED_RE.match(lines[1]), (
            f"{path.name}: line 2 must be `Updated: YYYY-MM-DD`, got "
            f"{(lines[1] if len(lines) > 1 else '')!r}. Without it a stale OPEN is "
            "indistinguishable from a live one."
        )

    @pytest.mark.parametrize("path", _candidates(), ids=lambda p: p.name)
    def test_the_date_is_not_in_the_future(self, path: Path) -> None:
        """A typo'd year is how a header stops being evidence of anything."""
        match = UPDATED_RE.match(path.read_text().splitlines()[1])
        assert match, f"{path.name}: no parseable Updated line"
        stamped = date(*(int(g) for g in match.groups()))
        assert stamped <= date.today(), f"{path.name}: Updated: {stamped} is in the future"


class TestTheRootHoldsOnlyLiveWork:
    @pytest.mark.parametrize("path", _candidates(), ids=lambda p: p.name)
    def test_a_closed_task_has_been_archived(self, path: Path) -> None:
        """`archive/README.md`: the root keeps active tasks, closed ones are git mv'd.

        Enforced because the 2026-10-04 correction found twelve closed files sitting in
        the root, and "it does not pollute the query" was accepted as a reason to leave
        them. A query that cannot see a file is not evidence that the file is in its
        right place.
        """
        status = STATUS_RE.match(path.read_text().splitlines()[0])
        assert status, f"{path.name}: no parseable Status line"
        assert status.group(1) not in CLOSED_STATES, (
            f"{path.name} is {status.group(1)} but still in docs/tasks/ — "
            "`git mv` it to docs/tasks/archive/."
        )


class TestTheGuardCannotQuietlyStopGuarding:
    def test_every_exemption_names_a_file_that_exists(self) -> None:
        """A renamed or deleted exemption must break the test, not widen it."""
        for name, reason in EXEMPT.items():
            assert (TASKS_DIR / name).exists(), (
                f"EXEMPT names {name}, which no longer exists. Drop the entry rather "
                "than leaving a hole that matches nothing."
            )
            assert len(reason) > 80, f"{name}: the exemption needs a real reason"

    def test_there_is_something_to_check(self) -> None:
        assert len(_candidates()) >= 3, (
            "No task files found — the glob broke, and a guard over an empty set "
            "passes while guarding nothing."
        )

    def test_the_documented_query_and_this_test_agree(self) -> None:
        """The grep in CLAUDE.md and the regex here must mean the same thing."""
        import subprocess

        proc = subprocess.run(
            ["grep", "-lE", r"^Status:[[:space:]]*(OPEN|WIP)", *[str(p) for p in _task_files()]],
            capture_output=True,
            text=True,
        )
        by_grep = {Path(line).name for line in proc.stdout.splitlines() if line}
        by_regex = {
            p.name
            for p in _task_files()
            if (m := STATUS_RE.match(p.read_text().splitlines()[0] or ""))
            and m.group(1) in ("OPEN", "WIP")
        }
        assert by_grep == by_regex, (
            "The CLAUDE.md query and this guard disagree about what is open: "
            f"grep={sorted(by_grep)} vs guard={sorted(by_regex)}"
        )
