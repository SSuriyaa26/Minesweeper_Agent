"""
reasoning_log.py — Move Explanation Logger
==========================================
After every agent move, this module stores and formats a human-readable
explanation of WHY the agent chose that move, including which algorithm
(CSP, Forward Checking, Backtracking, or Probabilistic) was responsible.
"""


class ReasoningLog:
    """
    Collects and formats reasoning entries for every move the agent makes.

    Each entry is a dict with keys:
        move       : (row, col)
        action     : 'REVEAL' or 'FLAG'
        algorithm  : str  — which AI algorithm produced the decision
        explanation: str  — human-readable reason
    """

    def __init__(self):
        self._entries: list[dict] = []

    # ── Recording ────────────────────────────────────────────────────────────

    def log_move(
        self,
        row: int,
        col: int,
        action: str,
        algorithm: str,
        explanation: str,
    ) -> None:
        """
        Record a single move with its reasoning.

        Parameters
        ----------
        row, col : int
            Cell coordinates.
        action : str
            'REVEAL' or 'FLAG'.
        algorithm : str
            One of 'CSP', 'Forward Checking', 'Backtracking', 'Probabilistic'.
        explanation : str
            Human-readable justification for the move.
        """
        self._entries.append({
            "move": (row, col),
            "action": action,
            "algorithm": algorithm,
            "explanation": explanation,
        })

    # ── Retrieval ────────────────────────────────────────────────────────────

    def get_last(self) -> dict | None:
        """Return the most recent log entry, or None if empty."""
        return self._entries[-1] if self._entries else None

    def get_all(self) -> list[dict]:
        """Return all log entries."""
        return list(self._entries)

    def count(self) -> int:
        """Return the number of logged moves."""
        return len(self._entries)

    # ── Formatting ───────────────────────────────────────────────────────────

    @staticmethod
    def format_entry(entry: dict) -> str:
        """Format a single entry as a human-readable string."""
        r, c = entry["move"]
        action = entry["action"]
        algo = entry["algorithm"]
        expl = entry["explanation"]
        return f"Cell ({r},{c}): {action} — {algo}: {expl}"

    def format_last(self) -> str:
        """Format the most recent entry."""
        last = self.get_last()
        if last is None:
            return "(no moves yet)"
        return self.format_entry(last)

    def dump(self) -> str:
        """Return the full log as a multi-line formatted string."""
        if not self._entries:
            return "(empty log)"
        lines = []
        for i, entry in enumerate(self._entries, start=1):
            lines.append(f"  Move {i:>3}: {self.format_entry(entry)}")
        return "\n".join(lines)

    # ── Lifecycle ────────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Clear all log entries (used between games)."""
        self._entries.clear()

    def __repr__(self) -> str:
        return f"ReasoningLog({len(self._entries)} entries)"
