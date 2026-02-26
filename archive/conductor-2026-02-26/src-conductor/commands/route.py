"""CONDUCTOR /route — Classify input and suggest routing."""

import json
from pathlib import Path

from conductor.orchestration.router import Router


def run(input_text: str) -> str:
    """Execute /route and return JSON routing decision."""
    if not input_text.strip():
        return json.dumps({"error": "No input text provided for routing."})

    router = Router()
    result = router.route(input_text)
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False)
