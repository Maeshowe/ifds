#!/bin/bash
# IFDS session start — betolti a legutolso journal kontextust + STATUS
JOURNAL_DIR="docs/journal"
if [ -d "$JOURNAL_DIR" ]; then
  ls -t "$JOURNAL_DIR" | head -2 | while read f; do
    echo "=== Journal: $f ==="
    cat "$JOURNAL_DIR/$f"
  done
fi

if [ -f "docs/STATUS.md" ]; then
  echo "=== STATUS.md ==="
  cat "docs/STATUS.md"
fi
