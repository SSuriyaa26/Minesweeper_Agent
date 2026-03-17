"""
stats_tracker.py — Multi-Game Statistics Tracker
=================================================
Tracks performance over N games:
  • Win rate, total games, average moves per game
  • Per-algorithm usage counters (CSP / Forward Checking / Backtracking /
    Probabilistic)
  • Prints a formatted summary table
"""

from __future__ import annotations


class StatsTracker:
    """
    Accumulates statistics across multiple Minesweeper games.
    """

    ALGORITHMS = ["CSP", "Forward Checking", "Backtracking", "Probabilistic"]

    def __init__(self):
        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.total_moves = 0
        self._moves_this_game = 0

        # Per-algorithm counters (across all games)
        self.algo_counts: dict[str, int] = {a: 0 for a in self.ALGORITHMS}

    # ── Per-move recording ───────────────────────────────────────────────────

    def record_move(self, algorithm: str) -> None:
        """Record that one move was made using the given algorithm."""
        self.total_moves += 1
        self._moves_this_game += 1
        if algorithm in self.algo_counts:
            self.algo_counts[algorithm] += 1

    # ── Per-game recording ───────────────────────────────────────────────────

    def record_game(self, won: bool) -> None:
        """Record the outcome of a completed game."""
        self.games_played += 1
        if won:
            self.wins += 1
        else:
            self.losses += 1
        self._moves_this_game = 0

    # ── Summary ──────────────────────────────────────────────────────────────

    def win_rate(self) -> float:
        """Return win rate as a fraction (0.0 – 1.0)."""
        return self.wins / self.games_played if self.games_played else 0.0

    def avg_moves(self) -> float:
        """Return average moves per game."""
        return self.total_moves / self.games_played if self.games_played else 0.0

    def summary(self) -> str:
        """Return a formatted summary table string."""
        w = 42
        lines = [
            "╔" + "═" * w + "╗",
            "║" + "  MINESWEEPER AI — STATISTICS SUMMARY  ".center(w) + "║",
            "╠" + "═" * w + "╣",
            "║" + f"  Games Played:  {self.games_played}".ljust(w) + "║",
            "║" + f"  Wins:          {self.wins}".ljust(w) + "║",
            "║" + f"  Losses:        {self.losses}".ljust(w) + "║",
            "║" + f"  Win Rate:      {self.win_rate():.1%}".ljust(w) + "║",
            "║" + f"  Total Moves:   {self.total_moves}".ljust(w) + "║",
            "║" + f"  Avg Moves/Game:{self.avg_moves():.1f}".ljust(w) + "║",
            "╠" + "═" * w + "╣",
            "║" + "  Algorithm Usage:".ljust(w) + "║",
        ]
        for algo, count in self.algo_counts.items():
            lines.append("║" + f"    {algo:<20s} {count:>5d} moves".ljust(w) + "║")
        lines.append("╚" + "═" * w + "╝")
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (
            f"StatsTracker(games={self.games_played}, "
            f"wins={self.wins}, losses={self.losses})"
        )
