"""Route definitions for CONDUCTOR orchestration."""

from dataclasses import dataclass, field
from enum import Enum


class Route(Enum):
    MEMORY = "memory"
    BA_BRIDGE = "ba_bridge"
    TECHNICAL = "technical"
    STRATEGY = "strategy"


ROUTE_AVAILABILITY = {
    Route.MEMORY: True,
    Route.BA_BRIDGE: True,
    Route.TECHNICAL: True,
    Route.STRATEGY: True,
}

ROUTE_COMMANDS = {
    Route.MEMORY: ["/where-am-i", "/continue", "/wrap-up", "/pause", "/learn"],
    Route.BA_BRIDGE: ["/analyze-idea"],
    Route.TECHNICAL: ["/build", "/review", "/test", "/setup-env"],
    Route.STRATEGY: ["/red-team", "/scenarios", "/decide", "/compliance"],
}

ROUTE_DESCRIPTIONS = {
    Route.MEMORY: "Context & session management",
    Route.BA_BRIDGE: "Idea analysis & requirement structuring",
    Route.TECHNICAL: "Code implementation & review",
    Route.STRATEGY: "Strategic analysis & decision support",
}

# Keyword patterns for rule-based routing (case-insensitive)
ROUTE_KEYWORDS: dict[Route, list[str]] = {
    Route.BA_BRIDGE: [
        "idea", "ötlet", "feature", "kellene egy", "mi lenne ha",
        "csináljuk meg", "új funkció", "requirement", "követelmény",
        "new feature", "build this", "szeretnék egy", "jó lenne",
    ],
    Route.TECHNICAL: [
        "code", "kód", "bug", "fix", "test", "review", "refactor",
        "implement", "build", "fejleszt", "javít", "programoz",
        "error", "hiba", "debug",
        "tech debt", "technikai adósság", "code smell", "kódszag",
        "cleanup", "takarítás", "átszervezés",
        "dokumentáció", "docs", "environment", "környezet",
        "setup", "dependency", "függőség",
    ],
    Route.STRATEGY: [
        "strategy", "stratégia", "döntés", "decide", "risk", "kockázat",
        "red team", "compliance", "scenario", "forgatókönyv",
        "szabályozás", "regulation", "kockázatelemzés",
    ],
    Route.MEMORY: [
        "hol tartok", "where am i", "continue", "folytat", "wrap up",
        "lezár", "pause", "szünet", "learn", "tanul", "search", "keres",
    ],
}


@dataclass
class RoutingResult:
    route: Route
    available: bool
    suggested_command: str
    confidence: str  # "high", "medium", "low"
    reasoning: str
    all_matches: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "route": self.route.value,
            "available": self.available,
            "suggested_command": self.suggested_command,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "description": ROUTE_DESCRIPTIONS.get(self.route, ""),
            "commands": ROUTE_COMMANDS.get(self.route, []),
            "all_matches": self.all_matches,
        }
