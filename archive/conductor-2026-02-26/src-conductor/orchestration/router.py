"""Rule-based router for CONDUCTOR orchestration (v1)."""

import re

from conductor.orchestration.routes import (
    ROUTE_AVAILABILITY,
    ROUTE_COMMANDS,
    ROUTE_KEYWORDS,
    Route,
    RoutingResult,
)


class Router:
    """Simple rule-based router. Classifies user input to a Route."""

    def route(self, input_text: str) -> RoutingResult:
        """Classify input text and return a routing decision."""
        text_lower = input_text.lower().strip()

        # Priority 1: Explicit command reference
        explicit = self._check_explicit_command(text_lower)
        if explicit:
            return explicit

        # Priority 2: Keyword matching with scoring
        scores = self._score_routes(text_lower)

        if not scores:
            return RoutingResult(
                route=Route.MEMORY,
                available=True,
                suggested_command="/where-am-i",
                confidence="low",
                reasoning="No specific keywords matched. Defaulting to memory/context.",
            )

        # Best match
        best_route, best_score = scores[0]
        all_matches = [
            {"route": r.value, "score": s, "available": ROUTE_AVAILABILITY[r]}
            for r, s in scores
        ]

        confidence = "high" if best_score >= 3 else "medium" if best_score >= 2 else "low"
        suggested = ROUTE_COMMANDS.get(best_route, ["/where-am-i"])[0]

        available = ROUTE_AVAILABILITY[best_route]
        reasoning = f"Matched {best_score} keyword(s) for {best_route.value}."
        if not available:
            reasoning += f" Note: {best_route.value} is not yet available."

        return RoutingResult(
            route=best_route,
            available=available,
            suggested_command=suggested,
            confidence=confidence,
            reasoning=reasoning,
            all_matches=all_matches,
        )

    def _check_explicit_command(self, text: str) -> RoutingResult | None:
        """Check if input explicitly references a known command."""
        all_commands = {}
        for route, commands in ROUTE_COMMANDS.items():
            for cmd in commands:
                all_commands[cmd] = route

        for cmd, route in all_commands.items():
            if cmd in text:
                return RoutingResult(
                    route=route,
                    available=ROUTE_AVAILABILITY[route],
                    suggested_command=cmd,
                    confidence="high",
                    reasoning=f"Explicit command reference: {cmd}",
                )
        return None

    def _score_routes(self, text: str) -> list[tuple[Route, int]]:
        """Score each route by keyword match count. Returns sorted list (highest first)."""
        scores: list[tuple[Route, int]] = []

        for route, keywords in ROUTE_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            if score > 0:
                scores.append((route, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores
