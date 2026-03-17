"""
ui.py — Terminal User Interface
================================
Renders the Minesweeper board in the terminal using colorama for colored output.
Displays:
  • Board grid with color-coded numbers, flags (🚩), hidden cells (■), mines (💣)
  • Current move information and reasoning log entry
  • Running game statistics
  • Human-mode input handling
"""

from __future__ import annotations

import os
import sys

# Force UTF-8 output on Windows to avoid encoding errors
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from colorama import init as colorama_init, Fore, Back, Style

from game_engine import MinesweeperGame, GameStatus
from reasoning_log import ReasoningLog
from stats_tracker import StatsTracker

# Initialize colorama (needed on Windows)
colorama_init(autoreset=True)


# ─── Color mapping for numbers 1–8 ───────────────────────────────────────────

NUMBER_COLORS = {
    0: Fore.WHITE + Style.DIM,
    1: Fore.BLUE + Style.BRIGHT,
    2: Fore.GREEN + Style.BRIGHT,
    3: Fore.RED + Style.BRIGHT,
    4: Fore.MAGENTA + Style.BRIGHT,
    5: Fore.YELLOW + Style.BRIGHT,
    6: Fore.CYAN + Style.BRIGHT,
    7: Fore.WHITE + Style.BRIGHT,
    8: Fore.WHITE + Style.DIM,
}


# ─── Board Renderer ──────────────────────────────────────────────────────────

class TerminalUI:
    """
    Renders the Minesweeper game state in the terminal with colors.
    """

    def __init__(self, game: MinesweeperGame):
        self.game = game

    # ── Full board display ───────────────────────────────────────────────────

    def render_board(
        self,
        board_view: list[list] | None = None,
        show_mines_on_loss: bool = True,
    ) -> str:
        """
        Render the board as a colored string.

        Parameters
        ----------
        board_view : list[list], optional
            Pre-computed board view. If None, fetches from self.game.
        show_mines_on_loss : bool
            If True and the game is lost, reveal all mines.

        Returns
        -------
        str
            Multi-line colored board string.
        """
        if board_view is None:
            board_view = self.game.get_board_view()

        rows = self.game.rows
        cols = self.game.cols
        mine_map = self.game.get_mine_map() if show_mines_on_loss else None
        game_lost = self.game.status == GameStatus.LOST

        lines: list[str] = []

        # Column headers
        header = "    " + " ".join(f"{c:>2}" for c in range(cols))
        lines.append(Fore.YELLOW + header + Style.RESET_ALL)
        lines.append("    " + "---" * cols)

        for r in range(rows):
            row_str = Fore.YELLOW + f"{r:>2} | " + Style.RESET_ALL
            for c in range(cols):
                cell = board_view[r][c]

                if cell == 'H':
                    # Show mines on loss
                    if game_lost and mine_map and mine_map[r][c]:
                        row_str += Fore.RED + Style.BRIGHT + " * " + Style.RESET_ALL
                    else:
                        row_str += Fore.WHITE + Style.DIM + " # " + Style.RESET_ALL
                elif cell == 'F':
                    row_str += Fore.RED + " F " + Style.RESET_ALL
                elif cell == 'M':
                    row_str += Fore.RED + Style.BRIGHT + " 💣" + Style.RESET_ALL
                elif isinstance(cell, int):
                    if cell == 0:
                        row_str += Style.DIM + " · " + Style.RESET_ALL
                    else:
                        color = NUMBER_COLORS.get(cell, Fore.WHITE)
                        row_str += color + f" {cell} " + Style.RESET_ALL
                else:
                    row_str += " ? "

            lines.append(row_str)

        return "\n".join(lines)

    # ── Status bar ───────────────────────────────────────────────────────────

    def render_status(self, move_number: int = 0) -> str:
        """Render game status bar."""
        g = self.game
        flags = g.count_flags()
        remaining = g.num_mines - flags
        status_str = g.status.name

        color = Fore.GREEN if g.status == GameStatus.ONGOING else (
            Fore.CYAN if g.status == GameStatus.WON else Fore.RED
        )

        return (
            f"{color}Status: {status_str}  |  "
            f"Mines: {g.num_mines}  |  Flags: {flags}  |  "
            f"Remaining: {remaining}  |  Move #{move_number}"
            f"{Style.RESET_ALL}"
        )

    # ── Move info ────────────────────────────────────────────────────────────

    @staticmethod
    def render_move_info(log: ReasoningLog) -> str:
        """Render the latest move reasoning."""
        last = log.get_last()
        if last is None:
            return ""
        return (
            Fore.CYAN + "  ▸ " + ReasoningLog.format_entry(last) + Style.RESET_ALL
        )

    # ── Full frame (board + status + reasoning) ──────────────────────────────

    def render_frame(
        self,
        log: ReasoningLog,
        move_number: int = 0,
        stats: StatsTracker | None = None,
    ) -> str:
        """Render a complete UI frame."""
        parts = [
            "",
            self.render_status(move_number),
            self.render_board(),
        ]

        move_info = self.render_move_info(log)
        if move_info:
            parts.append(move_info)

        if stats and stats.games_played > 0:
            parts.append(
                Fore.YELLOW + Style.DIM +
                f"  [Running: {stats.wins}W / {stats.losses}L "
                f"of {stats.games_played} games]" + Style.RESET_ALL
            )

        parts.append("")
        return "\n".join(parts)

    # ── Clear screen ─────────────────────────────────────────────────────────

    @staticmethod
    def clear_screen() -> None:
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    # ── Human input ──────────────────────────────────────────────────────────

    @staticmethod
    def get_human_input() -> tuple[str, int, int] | None:
        """
        Get a move from the human player.

        Expected input format:
            r <row> <col>    → reveal
            f <row> <col>    → flag
            u <row> <col>    → unflag
            q                → quit

        Returns (action, row, col) or None to quit.
        """
        try:
            raw = input(
                Fore.GREEN + "  Enter move (r/f/u row col, or q to quit): "
                + Style.RESET_ALL
            ).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return None

        if raw == 'q':
            return None

        parts = raw.split()
        if len(parts) != 3:
            print(Fore.RED + "  Invalid input. Use: r <row> <col>" + Style.RESET_ALL)
            return ("invalid", -1, -1)  # sentinel for retry

        action = parts[0]
        if action not in ('r', 'f', 'u'):
            print(Fore.RED + "  Action must be r, f, or u." + Style.RESET_ALL)
            return ("invalid", -1, -1)

        try:
            row, col = int(parts[1]), int(parts[2])
        except ValueError:
            print(Fore.RED + "  Row and col must be integers." + Style.RESET_ALL)
            return ("invalid", -1, -1)

        action_map = {'r': 'REVEAL', 'f': 'FLAG', 'u': 'UNFLAG'}
        return (action_map[action], row, col)
