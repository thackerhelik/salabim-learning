
from collections import deque


class EventLogger:
    """Collects simulation events and controls console verbosity."""

    LOG_LEVELS = {
        "quiet",
        "summary",
        "info",
        "debug",
    }

    # Events worth displaying at the info level.
    # Routine decisions, movements, claims and periodic updates
    # are reserved for debug mode.
    INFO_EVENTS = {
        "DISCOVERY",
        "RESOURCE_DEPLETED",
        "GATHER",
        "EAT",
        "LOOT",
        "DEPOSIT",
        "WITHDRAW",
        "CLAIM_DENIED",
        "MOVEMENT_BLOCKED",
        "ACTION_FAILED",
        "INVALID_ACTION",
        "LEADER_FED",
        "LEADER_DEATH",
        "TEAM_ELIMINATED",
        "DEATH",
    }

    def __init__(
        self,
        debug=False,
        max_events=1000,
        level=None,
    ):
        # Backward compatibility:
        # EventLogger(debug=True)  -> debug
        # EventLogger(debug=False) -> info
        if level is None:
            level = "debug" if debug else "info"

        if level not in self.LOG_LEVELS:
            raise ValueError(
                f"Invalid logging level: {level}. "
                f"Choose from {sorted(self.LOG_LEVELS)}."
            )

        if not isinstance(max_events, int) or max_events <= 0:
            raise ValueError("max_events must be a positive integer.")

        self.level = level

        # Preserve the old attribute for compatibility.
        self.debug = level == "debug"

        # Keep a bounded history for the dashboard and metrics.
        self.events = deque(maxlen=max_events)

    def should_print(self, event, debug_only=False):
        """Determine whether an event should appear in the console."""

        if self.level in {"quiet", "summary"}:
            return False

        if self.level == "debug":
            return True

        # Info level: only important events.
        return (
            not debug_only
            and event in self.INFO_EVENTS
        )

    def log(
        self,
        sim_time,
        team_id,
        explorer_name,
        event,
        message,
        details=None,
        debug_only=False,
    ):
        """Record an event and optionally print it."""

        entry = {
            "time": sim_time,
            "team_id": team_id,
            "explorer": explorer_name,
            "event": event,
            "message": message,
            "details": list(details or []),
            "debug_only": debug_only,
        }

        # Always record the event, regardless of logging level.
        self.events.append(entry)

        # Console output is controlled independently.
        if not self.should_print(event, debug_only):
            return entry

        print(
            f"[T={sim_time:6.1f}] "
            f"[TEAM {team_id}] "
            f"[{explorer_name}] "
            f"{event}"
        )

        print(f"    {message}")

        for detail in entry["details"]:
            print(f"    {detail}")

        return entry

    def get_recent_events(
        self,
        limit=20,
        team_id=None,
        explorer_name=None,
        include_debug=False,
    ):
        """Return recent events, optionally filtered."""

        filtered = [
            event
            for event in self.events
            if (
                include_debug or not event.get("debug_only", False)
            )
            and (
                team_id is None
                or event["team_id"] == team_id
            )
            and (
                explorer_name is None
                or event["explorer"] == explorer_name
            )
        ]

        if limit is None:
            return filtered

        if limit <= 0:
            return []

        return filtered[-limit:]
