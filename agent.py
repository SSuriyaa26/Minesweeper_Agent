"""
agent.py — Minesweeper Intelligent Agent
=========================================
Implements the perception → decision → action loop using four AI algorithms
applied in strict priority order:

  1. CSP + Constraint Propagation
  2. Forward Checking
  3. Backtracking Search
  4. Probabilistic Fallback (Minimax under uncertainty)

No ML libraries — all logic is hand-coded CSP / search / probability.
"""

from __future__ import annotations

import itertools
import random
from typing import Optional

from game_engine import MinesweeperGame, GameStatus
from reasoning_log import ReasoningLog


# ─── Constants ────────────────────────────────────────────────────────────────

ACTION_REVEAL = "REVEAL"
ACTION_FLAG = "FLAG"

ALGO_CSP = "CSP"
ALGO_FORWARD_CHECK = "Forward Checking"
ALGO_BACKTRACK = "Backtracking"
ALGO_PROBABILISTIC = "Probabilistic"


# ─── Agent ────────────────────────────────────────────────────────────────────

class MinesweeperAgent:
    """
    AI agent that autonomously plays Minesweeper.

    At each turn the agent follows:
        PERCEPTION  → read the board view
        DECISION    → apply CSP → Forward Checking → Backtracking → Probabilistic
        ACTION      → return (row, col, action_type)
    """

    def __init__(self, game: MinesweeperGame, log: ReasoningLog):
        self.game = game
        self.log = log

    # ══════════════════════════════════════════════════════════════════════════
    #  PUBLIC INTERFACE
    # ══════════════════════════════════════════════════════════════════════════

    def next_move(self) -> tuple[int, int, str, str]:
        """
        Compute the next move.

        Returns
        -------
        (row, col, action, algorithm)
            action ∈ {REVEAL, FLAG}
            algorithm ∈ {CSP, Forward Checking, Backtracking, Probabilistic}
        """
        # ── PERCEPTION ───────────────────────────────────────────────────────
        board = self.game.get_board_view()

        # Opening move — no information yet, pick a corner
        if not self._has_revealed_cells(board):
            return self._opening_move(board)

        # Build frontier constraints from the current board
        constraints, hidden_set, flagged_set = self._build_constraints(board)

        # Known assignments: cells already determined as MINE or SAFE
        known: dict[tuple[int, int], str] = {}  # cell → 'MINE' | 'SAFE'

        # ── DECISION (a): CSP + Constraint Propagation ───────────────────────
        safe_cells, mine_cells = self._csp_propagate(constraints, known)

        if safe_cells or mine_cells:
            return self._pick_from_csp(safe_cells, mine_cells)

        # ── DECISION (b + c): Forward Checking + Backtracking ────────────────
        safe_cells, mine_cells = self._backtrack_solve(constraints, known)

        if safe_cells or mine_cells:
            return self._pick_from_backtrack(safe_cells, mine_cells)

        # ── DECISION (d): Probabilistic Fallback ─────────────────────────────
        return self._probabilistic_fallback(board, constraints, known)

    # ══════════════════════════════════════════════════════════════════════════
    #  PERCEPTION HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _has_revealed_cells(board: list[list]) -> bool:
        """Check if any cell has been revealed yet."""
        for row in board:
            for cell in row:
                if isinstance(cell, int):
                    return True
        return False

    def _build_constraints(
        self, board: list[list]
    ) -> tuple[list[dict], set[tuple[int, int]], set[tuple[int, int]]]:
        """
        Build CSP constraints from the current board view.

        For each revealed number cell that has at least one hidden neighbor,
        create a constraint:
            { 'cell': (r,c), 'hidden': set of hidden neighbors,
              'count': remaining mines around this cell }

        Returns (constraints, all_hidden_frontier, all_flagged)
        """
        rows, cols = self.game.rows, self.game.cols
        constraints: list[dict] = []
        hidden_set: set[tuple[int, int]] = set()
        flagged_set: set[tuple[int, int]] = set()

        for r in range(rows):
            for c in range(cols):
                if board[r][c] == 'F':
                    flagged_set.add((r, c))

        for r in range(rows):
            for c in range(cols):
                val = board[r][c]
                if not isinstance(val, int):
                    continue  # skip non-revealed cells

                # Gather hidden & flagged neighbors
                hidden_neighbors: set[tuple[int, int]] = set()
                flagged_count = 0
                for nr, nc in self._neighbors(r, c, rows, cols):
                    if board[nr][nc] == 'H':
                        hidden_neighbors.add((nr, nc))
                    elif board[nr][nc] == 'F':
                        flagged_count += 1

                if not hidden_neighbors:
                    continue  # fully satisfied, skip

                remaining = val - flagged_count  # mines still to find
                constraints.append({
                    'cell': (r, c),
                    'hidden': hidden_neighbors,
                    'count': remaining,
                })
                hidden_set.update(hidden_neighbors)

        return constraints, hidden_set, flagged_set

    @staticmethod
    def _neighbors(r: int, c: int, rows: int, cols: int) -> list[tuple[int, int]]:
        """Return valid neighbor coordinates."""
        result = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    result.append((nr, nc))
        return result

    # ══════════════════════════════════════════════════════════════════════════
    #  DECISION (a): CSP + CONSTRAINT PROPAGATION
    # ══════════════════════════════════════════════════════════════════════════

    def _csp_propagate(
        self,
        constraints: list[dict],
        known: dict[tuple[int, int], str],
    ) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
        """
        CSP Constraint Propagation
        --------------------------
        Iteratively apply two simple rules until convergence:
          • If remaining count == number of hidden neighbors → ALL are mines
          • If remaining count == 0                          → ALL are safe

        After each inference, update all constraints that share the determined
        cells (this is essentially arc-consistency / unit propagation).
        """
        safe_cells: set[tuple[int, int]] = set()
        mine_cells: set[tuple[int, int]] = set()

        changed = True
        while changed:
            changed = False
            for con in constraints:
                # Remove cells already known from this constraint
                con['hidden'] -= safe_cells
                con['count'] -= len(con['hidden'] & mine_cells)
                con['hidden'] -= mine_cells

                if not con['hidden']:
                    continue

                # Rule 1: all hidden neighbors must be mines
                if con['count'] == len(con['hidden']):
                    for cell in con['hidden']:
                        if cell not in mine_cells:
                            mine_cells.add(cell)
                            known[cell] = 'MINE'
                            changed = True
                    con['hidden'] = set()

                # Rule 2: no remaining mines → all are safe
                elif con['count'] == 0:
                    for cell in con['hidden']:
                        if cell not in safe_cells:
                            safe_cells.add(cell)
                            known[cell] = 'SAFE'
                            changed = True
                    con['hidden'] = set()

        return safe_cells, mine_cells

    # ══════════════════════════════════════════════════════════════════════════
    #  DECISION (b + c): FORWARD CHECKING + BACKTRACKING
    # ══════════════════════════════════════════════════════════════════════════

    def _backtrack_solve(
        self,
        constraints: list[dict],
        known: dict[tuple[int, int], str],
    ) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
        """
        Backtracking Search with Forward Checking
        ------------------------------------------
        When CSP propagation stalls, enumerate all consistent MINE/SAFE
        assignments over the unknown frontier variables.

        Forward Checking:
            After each assignment, immediately check all constraints that
            include the assigned cell. If any constraint becomes inconsistent
            (remaining count < 0, or count > remaining hidden cells), prune
            this branch.

        After collecting all valid solutions:
          • Cells that are MINE in ALL solutions → deterministic mines
          • Cells that are SAFE in ALL solutions → deterministic safe
        """
        # Rebuild constraints fresh (deep copy) to avoid mutation issues
        cons = []
        frontier_vars: set[tuple[int, int]] = set()
        for c in constraints:
            remaining_hidden = c['hidden'] - set(known.keys())
            remaining_count = c['count']
            # Adjust count for cells we already know are mines in known
            for cell in c['hidden'] & set(known.keys()):
                if known[cell] == 'MINE':
                    remaining_count -= 1
            if remaining_hidden:
                cons.append({
                    'hidden': set(remaining_hidden),
                    'count': remaining_count,
                })
                frontier_vars.update(remaining_hidden)

        if not frontier_vars:
            return set(), set()

        # Limit backtracking to connected groups to keep it tractable
        groups = self._find_connected_groups(cons, frontier_vars)

        all_safe: set[tuple[int, int]] = set()
        all_mine: set[tuple[int, int]] = set()

        for group_vars, group_cons in groups:
            safe, mine = self._backtrack_group(list(group_vars), group_cons)
            all_safe.update(safe)
            all_mine.update(mine)

        return all_safe, all_mine

    def _find_connected_groups(
        self,
        constraints: list[dict],
        frontier_vars: set[tuple[int, int]],
    ) -> list[tuple[set[tuple[int, int]], list[dict]]]:
        """
        Split the frontier into independent connected groups.
        Two variables are connected if they share a constraint.
        Solving smaller groups independently is much faster.
        """
        # Build adjacency: variable → set of variables sharing a constraint
        var_to_cons: dict[tuple[int, int], list[int]] = {v: [] for v in frontier_vars}
        for i, c in enumerate(constraints):
            for v in c['hidden']:
                if v in var_to_cons:
                    var_to_cons[v].append(i)

        visited: set[tuple[int, int]] = set()
        groups: list[tuple[set[tuple[int, int]], list[dict]]] = []

        for start in frontier_vars:
            if start in visited:
                continue
            # BFS to find connected component
            group_vars: set[tuple[int, int]] = set()
            group_con_ids: set[int] = set()
            queue = [start]
            while queue:
                v = queue.pop()
                if v in visited:
                    continue
                visited.add(v)
                group_vars.add(v)
                for ci in var_to_cons.get(v, []):
                    group_con_ids.add(ci)
                    for neighbor in constraints[ci]['hidden']:
                        if neighbor not in visited and neighbor in frontier_vars:
                            queue.append(neighbor)

            group_cons = [
                {'hidden': set(constraints[ci]['hidden']), 'count': constraints[ci]['count']}
                for ci in group_con_ids
            ]
            groups.append((group_vars, group_cons))

        return groups

    def _backtrack_group(
        self,
        variables: list[tuple[int, int]],
        constraints: list[dict],
    ) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
        """
        Backtracking over one connected group of frontier variables.

        Collects all valid complete assignments.  Returns cells that are
        the same value across ALL solutions (deterministic).

        Caps enumeration at 1000 solutions to stay tractable on large groups.
        """
        MAX_SOLUTIONS = 1000

        # If the group is too large, skip backtracking (probabilistic will handle it)
        if len(variables) > 25:
            return set(), set()

        solutions: list[dict[tuple[int, int], str]] = []
        assignment: dict[tuple[int, int], str] = {}

        def is_consistent() -> bool:
            """
            Forward Checking
            ----------------
            After each assignment, check every constraint.
            A constraint is inconsistent if:
              - assigned mines already exceed the count
              - remaining count exceeds remaining unassigned hidden cells
            """
            for con in constraints:
                assigned_mines = sum(
                    1 for v in con['hidden']
                    if assignment.get(v) == 'MINE'
                )
                unassigned = [
                    v for v in con['hidden']
                    if v not in assignment
                ]
                assigned_safe = sum(
                    1 for v in con['hidden']
                    if assignment.get(v) == 'SAFE'
                )

                remaining = con['count'] - assigned_mines
                if remaining < 0:
                    return False
                if remaining > len(unassigned):
                    return False
                # If all assigned, count must be exactly zero remaining
                if not unassigned and remaining != 0:
                    return False
            return True

        def backtrack(idx: int) -> None:
            """Depth-first search with forward checking pruning."""
            if len(solutions) >= MAX_SOLUTIONS:
                return

            if idx == len(variables):
                # Complete assignment — record it
                solutions.append(dict(assignment))
                return

            cell = variables[idx]
            for value in ('SAFE', 'MINE'):
                assignment[cell] = value
                # Forward Checking: prune immediately if inconsistent
                if is_consistent():
                    backtrack(idx + 1)
                del assignment[cell]

        backtrack(0)

        if not solutions:
            return set(), set()

        # Deterministic cells: same value across ALL solutions
        safe_cells: set[tuple[int, int]] = set()
        mine_cells: set[tuple[int, int]] = set()

        for var in variables:
            values = {sol[var] for sol in solutions}
            if len(values) == 1:
                if 'SAFE' in values:
                    safe_cells.add(var)
                else:
                    mine_cells.add(var)

        return safe_cells, mine_cells

    # ══════════════════════════════════════════════════════════════════════════
    #  DECISION (d): PROBABILISTIC FALLBACK (MINIMAX UNDER UNCERTAINTY)
    # ══════════════════════════════════════════════════════════════════════════

    def _probabilistic_fallback(
        self,
        board: list[list],
        constraints: list[dict],
        known: dict[tuple[int, int], str],
    ) -> tuple[int, int, str, str]:
        """
        Probabilistic Fallback — Minimax under Uncertainty
        ---------------------------------------------------
        When no deterministic move is available, estimate the mine probability
        for each unknown cell and choose the safest one (lowest P(mine)).

        Probability estimation:
          1. For frontier cells: run constrained backtracking (already done),
             compute fraction of solutions where each cell is a mine.
          2. For non-frontier hidden cells: use global probability =
             (remaining mines - frontier mines) / (total hidden - frontier size).
          3. If no constraints apply at all (e.g. first move after a big clear),
             prefer corners > edges > interior (fewer neighbors = more info).

        This is analogous to Minimax: the "opponent" (mine placement) picks the
        worst case, and we pick the move that minimizes our maximum risk.
        """
        rows, cols = self.game.rows, self.game.cols

        # Collect all hidden cells and frontier cells
        all_hidden: set[tuple[int, int]] = set()
        for r in range(rows):
            for c in range(cols):
                if board[r][c] == 'H':
                    all_hidden.add((r, c))

        if not all_hidden:
            # Should not happen, but be safe
            return (0, 0, ACTION_REVEAL, ALGO_PROBABILISTIC)

        # Rebuild constraints and solve again for probability
        cons = []
        frontier_vars: set[tuple[int, int]] = set()
        for c in constraints:
            remaining_hidden = c['hidden'] - set(known.keys())
            remaining_count = c['count']
            for cell in c['hidden'] & set(known.keys()):
                if known[cell] == 'MINE':
                    remaining_count -= 1
            if remaining_hidden:
                cons.append({
                    'hidden': set(remaining_hidden),
                    'count': remaining_count,
                })
                frontier_vars.update(remaining_hidden)

        # Remove cells already determined
        frontier_vars -= set(known.keys())
        all_hidden -= set(k for k, v in known.items() if v == 'SAFE')
        all_hidden -= set(k for k, v in known.items() if v == 'MINE')

        # Compute frontier probabilities via backtracking
        mine_probs: dict[tuple[int, int], float] = {}

        if frontier_vars:
            groups = self._find_connected_groups(cons, frontier_vars)
            for group_vars, group_cons in groups:
                probs = self._compute_group_probabilities(
                    list(group_vars), group_cons
                )
                mine_probs.update(probs)

        # Non-frontier cells: use global probability
        total_mines = self.game.num_mines
        flags_count = self.game.count_flags()
        known_mines = sum(1 for v in known.values() if v == 'MINE')
        remaining_mines = total_mines - flags_count - known_mines

        frontier_expected_mines = sum(mine_probs.values()) if mine_probs else 0
        non_frontier = all_hidden - frontier_vars
        non_frontier_count = len(non_frontier)
        non_frontier_mines = max(0, remaining_mines - frontier_expected_mines)

        if non_frontier_count > 0:
            global_prob = non_frontier_mines / non_frontier_count
        else:
            global_prob = 1.0

        for cell in non_frontier:
            mine_probs[cell] = global_prob

        if not mine_probs:
            # Absolute fallback: random hidden cell
            cell = random.choice(list(all_hidden))
            return (*cell, ACTION_REVEAL, ALGO_PROBABILISTIC)

        # ── Minimax decision: pick the cell with lowest mine probability ─────
        # Tie-break: prefer corners > edges > interior (more informative)
        def cell_priority(cell: tuple[int, int]) -> tuple[float, int]:
            r, c = cell
            prob = mine_probs.get(cell, 1.0)
            edge_r = (r == 0 or r == rows - 1)
            edge_c = (c == 0 or c == cols - 1)
            if edge_r and edge_c:
                tier = 0  # corner
            elif edge_r or edge_c:
                tier = 1  # edge
            else:
                tier = 2  # interior
            return (prob, tier)

        best_cell = min(mine_probs.keys(), key=cell_priority)
        prob = mine_probs[best_cell]

        r, c = best_cell
        explanation = f"mine probability = {prob:.1%}"
        if best_cell in non_frontier:
            explanation += " (non-frontier, global estimate)"

        self.log.log_move(r, c, ACTION_REVEAL, ALGO_PROBABILISTIC, explanation)
        return (r, c, ACTION_REVEAL, ALGO_PROBABILISTIC)

    def _compute_group_probabilities(
        self,
        variables: list[tuple[int, int]],
        constraints: list[dict],
    ) -> dict[tuple[int, int], float]:
        """
        Run backtracking over a group and compute P(mine) for each variable
        as: (# solutions where cell=MINE) / (total # solutions).
        """
        MAX_SOLUTIONS = 1000

        if len(variables) > 25:
            # Too large — use uniform estimate
            total_count = sum(c['count'] for c in constraints)
            avg = total_count / max(len(variables), 1)
            return {v: min(max(avg, 0.0), 1.0) for v in variables}

        solutions: list[dict[tuple[int, int], str]] = []
        assignment: dict[tuple[int, int], str] = {}

        def is_consistent() -> bool:
            for con in constraints:
                assigned_mines = sum(
                    1 for v in con['hidden'] if assignment.get(v) == 'MINE'
                )
                unassigned = [v for v in con['hidden'] if v not in assignment]
                remaining = con['count'] - assigned_mines
                if remaining < 0:
                    return False
                if remaining > len(unassigned):
                    return False
                if not unassigned and remaining != 0:
                    return False
            return True

        def backtrack(idx: int) -> None:
            if len(solutions) >= MAX_SOLUTIONS:
                return
            if idx == len(variables):
                solutions.append(dict(assignment))
                return
            cell = variables[idx]
            for value in ('SAFE', 'MINE'):
                assignment[cell] = value
                if is_consistent():
                    backtrack(idx + 1)
                del assignment[cell]

        backtrack(0)

        if not solutions:
            return {v: 0.5 for v in variables}

        probs: dict[tuple[int, int], float] = {}
        total = len(solutions)
        for v in variables:
            mine_count = sum(1 for sol in solutions if sol[v] == 'MINE')
            probs[v] = mine_count / total

        return probs

    # ══════════════════════════════════════════════════════════════════════════
    #  MOVE SELECTION HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _opening_move(
        self, board: list[list]
    ) -> tuple[int, int, str, str]:
        """
        Opening Move Strategy
        ---------------------
        With no information, prefer corners (fewest neighbors → most
        informative first reveal).
        """
        rows, cols = self.game.rows, self.game.cols
        corners = [(0, 0), (0, cols - 1), (rows - 1, 0), (rows - 1, cols - 1)]
        r, c = random.choice(corners)

        self.log.log_move(
            r, c, ACTION_REVEAL, ALGO_PROBABILISTIC,
            "Opening move — no information available, picking corner "
            "(fewest neighbors, most informative)"
        )
        return (r, c, ACTION_REVEAL, ALGO_PROBABILISTIC)

    def _pick_from_csp(
        self,
        safe_cells: set[tuple[int, int]],
        mine_cells: set[tuple[int, int]],
    ) -> tuple[int, int, str, str]:
        """Pick one move from CSP-determined cells, logging the reason."""
        # Prefer flagging mines first (gives more info to future constraints)
        if mine_cells:
            cell = min(mine_cells)  # deterministic pick
            r, c = cell
            explanation = (
                f"Constraint propagation forces this cell to be a mine "
                f"(all {len(mine_cells)} mine(s) determined this round)"
            )
            self.log.log_move(r, c, ACTION_FLAG, ALGO_CSP, explanation)
            return (r, c, ACTION_FLAG, ALGO_CSP)

        cell = min(safe_cells)
        r, c = cell
        explanation = (
            f"Constraint propagation proves this cell is safe "
            f"(all {len(safe_cells)} safe cell(s) determined this round)"
        )
        self.log.log_move(r, c, ACTION_REVEAL, ALGO_CSP, explanation)
        return (r, c, ACTION_REVEAL, ALGO_CSP)

    def _pick_from_backtrack(
        self,
        safe_cells: set[tuple[int, int]],
        mine_cells: set[tuple[int, int]],
    ) -> tuple[int, int, str, str]:
        """Pick one move from Backtracking-determined cells."""
        # Log under Forward Checking for the first mine, Backtracking for safe
        if mine_cells:
            cell = min(mine_cells)
            r, c = cell
            explanation = (
                f"Forward Checking eliminated SAFE from domain — "
                f"cell is MINE in all {len(mine_cells)} consistent assignment(s)"
            )
            self.log.log_move(r, c, ACTION_FLAG, ALGO_FORWARD_CHECK, explanation)
            return (r, c, ACTION_FLAG, ALGO_FORWARD_CHECK)

        cell = min(safe_cells)
        r, c = cell
        explanation = (
            f"Backtracking search: cell is SAFE in all consistent assignments"
        )
        self.log.log_move(r, c, ACTION_REVEAL, ALGO_BACKTRACK, explanation)
        return (r, c, ACTION_REVEAL, ALGO_BACKTRACK)
