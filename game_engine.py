"""
game_engine.py — Minesweeper Board Engine
==========================================
Implements the full Minesweeper game logic:
  • Configurable grid size and mine count
  • Cell states: HIDDEN, REVEALED, FLAGGED
  • Reveal with auto-flood-fill on zero-cells
  • First-click safety (mines placed after first reveal)
  • Game status tracking: ONGOING, WON, LOST
"""

from enum import Enum, auto
import random


# ─── Enums ────────────────────────────────────────────────────────────────────

class CellState(Enum):
    """Visible state of a cell from the player's perspective."""
    HIDDEN = auto()
    REVEALED = auto()
    FLAGGED = auto()


class GameStatus(Enum):
    """Overall game status."""
    ONGOING = auto()
    WON = auto()
    LOST = auto()


# ─── Game Engine ──────────────────────────────────────────────────────────────

class MinesweeperGame:
    """
    Full Minesweeper game state.

    Attributes
    ----------
    rows, cols : int
        Grid dimensions.
    num_mines : int
        Total number of mines on the board.
    status : GameStatus
        Current game status (ONGOING / WON / LOST).
    """

    def __init__(self, rows: int = 9, cols: int = 9, num_mines: int = 10):
        if num_mines >= rows * cols:
            raise ValueError("Number of mines must be less than total cells.")
        self.rows = rows
        self.cols = cols
        self.num_mines = num_mines
        self.status = GameStatus.ONGOING

        # Internal grids
        self._mines: list[list[bool]] = [[False] * cols for _ in range(rows)]
        self._numbers: list[list[int]] = [[0] * cols for _ in range(rows)]
        self._cell_states: list[list[CellState]] = [
            [CellState.HIDDEN] * cols for _ in range(rows)
        ]

        self._mines_placed = False  # first-click safety flag
        self._revealed_count = 0

    # ── Mine placement (deferred to first click) ────────────────────────────

    def _place_mines(self, safe_row: int, safe_col: int) -> None:
        """
        Randomly place mines on the board, guaranteeing that the cell
        (safe_row, safe_col) and its immediate neighbors are mine-free
        (first-click safety).
        """
        safe_zone = set()
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = safe_row + dr, safe_col + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    safe_zone.add((nr, nc))

        candidates = [
            (r, c)
            for r in range(self.rows)
            for c in range(self.cols)
            if (r, c) not in safe_zone
        ]

        # If board is too small for the safe-zone constraint, relax it
        if len(candidates) < self.num_mines:
            candidates = [
                (r, c)
                for r in range(self.rows)
                for c in range(self.cols)
                if (r, c) != (safe_row, safe_col)
            ]

        chosen = random.sample(candidates, self.num_mines)
        for r, c in chosen:
            self._mines[r][c] = True

        self._compute_numbers()
        self._mines_placed = True

    def _compute_numbers(self) -> None:
        """Compute the adjacency numbers for every cell."""
        for r in range(self.rows):
            for c in range(self.cols):
                if self._mines[r][c]:
                    self._numbers[r][c] = -1  # mine marker
                else:
                    self._numbers[r][c] = sum(
                        1 for nr, nc in self._neighbors(r, c)
                        if self._mines[nr][nc]
                    )

    # ── Neighbor helper ──────────────────────────────────────────────────────

    def _neighbors(self, r: int, c: int) -> list[tuple[int, int]]:
        """Return list of valid neighbor coordinates for (r, c)."""
        result = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    result.append((nr, nc))
        return result

    # ── Core actions ─────────────────────────────────────────────────────────

    def reveal(self, r: int, c: int) -> bool:
        """
        Reveal cell (r, c).

        Returns True if the game is still ongoing after this action,
        False if the game ended (win or loss).
        """
        if self.status != GameStatus.ONGOING:
            return False
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return True  # out of bounds — ignore
        if self._cell_states[r][c] != CellState.HIDDEN:
            return True  # already revealed or flagged — ignore

        # First-click safety: place mines now
        if not self._mines_placed:
            self._place_mines(r, c)

        # Hit a mine → game over
        if self._mines[r][c]:
            self._cell_states[r][c] = CellState.REVEALED
            self.status = GameStatus.LOST
            return False

        # Flood-fill reveal (BFS) for zero-cells
        self._flood_reveal(r, c)

        # Check win condition
        if self._check_win():
            self.status = GameStatus.WON
            return False

        return True

    def _flood_reveal(self, r: int, c: int) -> None:
        """BFS flood-fill: reveal cell and expand through zero-cells."""
        queue = [(r, c)]
        while queue:
            cr, cc = queue.pop(0)
            if self._cell_states[cr][cc] == CellState.REVEALED:
                continue
            if self._cell_states[cr][cc] == CellState.FLAGGED:
                continue
            self._cell_states[cr][cc] = CellState.REVEALED
            self._revealed_count += 1
            # If this cell is a zero, expand to neighbors
            if self._numbers[cr][cc] == 0:
                for nr, nc in self._neighbors(cr, cc):
                    if self._cell_states[nr][nc] == CellState.HIDDEN:
                        queue.append((nr, nc))

    def flag(self, r: int, c: int) -> None:
        """Flag a hidden cell as a suspected mine."""
        if self.status != GameStatus.ONGOING:
            return
        if 0 <= r < self.rows and 0 <= c < self.cols:
            if self._cell_states[r][c] == CellState.HIDDEN:
                self._cell_states[r][c] = CellState.FLAGGED

    def unflag(self, r: int, c: int) -> None:
        """Remove a flag from a cell."""
        if self.status != GameStatus.ONGOING:
            return
        if 0 <= r < self.rows and 0 <= c < self.cols:
            if self._cell_states[r][c] == CellState.FLAGGED:
                self._cell_states[r][c] = CellState.HIDDEN

    # ── Win condition ────────────────────────────────────────────────────────

    def _check_win(self) -> bool:
        """
        The player wins when every non-mine cell has been revealed.
        """
        total_safe = self.rows * self.cols - self.num_mines
        return self._revealed_count >= total_safe

    # ── Board view (for the agent / UI) ──────────────────────────────────────

    def get_board_view(self) -> list[list]:
        """
        Return the board as the player sees it.

        Each cell is one of:
          - 'H'   → hidden
          - 'F'   → flagged
          - int   → revealed number (0-8)
          - 'M'   → revealed mine (only visible after losing)
        """
        view = []
        for r in range(self.rows):
            row = []
            for c in range(self.cols):
                state = self._cell_states[r][c]
                if state == CellState.HIDDEN:
                    row.append('H')
                elif state == CellState.FLAGGED:
                    row.append('F')
                elif state == CellState.REVEALED:
                    if self._mines[r][c]:
                        row.append('M')
                    else:
                        row.append(self._numbers[r][c])
                else:
                    row.append('H')
            view.append(row)
        return view

    def get_mine_map(self) -> list[list[bool]]:
        """Return the full mine map (for debugging / post-game analysis)."""
        return [row[:] for row in self._mines]

    # ── Utility ──────────────────────────────────────────────────────────────

    def count_flags(self) -> int:
        """Return the number of currently flagged cells."""
        return sum(
            1
            for r in range(self.rows)
            for c in range(self.cols)
            if self._cell_states[r][c] == CellState.FLAGGED
        )

    def get_cell_state(self, r: int, c: int) -> CellState:
        """Return the CellState of the cell at (r, c)."""
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return self._cell_states[r][c]
        return CellState.HIDDEN

    def reset(self) -> None:
        """Reset the game to a fresh state (new game, mines not yet placed)."""
        self.status = GameStatus.ONGOING
        self._mines = [[False] * self.cols for _ in range(self.rows)]
        self._numbers = [[0] * self.cols for _ in range(self.rows)]
        self._cell_states = [
            [CellState.HIDDEN] * self.cols for _ in range(self.rows)
        ]
        self._mines_placed = False
        self._revealed_count = 0

    def __repr__(self) -> str:
        return (
            f"MinesweeperGame({self.rows}x{self.cols}, "
            f"mines={self.num_mines}, status={self.status.name})"
        )
