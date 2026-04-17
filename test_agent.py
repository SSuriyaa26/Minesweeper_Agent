"""
test_agent.py — Smoke Tests for Minesweeper AI Engine & Agent
===============================================================
Covers critical edge cases identified during the technical audit.
Run with:  python -m pytest test_agent.py -v   (or)   python test_agent.py
"""

import unittest

from game_engine import MinesweeperGame, GameStatus, CellState
from agent import MinesweeperAgent, ACTION_REVEAL, ACTION_FLAG, ALGO_PROBABILISTIC
from reasoning_log import ReasoningLog
from stats_tracker import StatsTracker


class TestGameEngine(unittest.TestCase):
    """Game engine edge cases."""

    def test_get_cell_state_valid(self):
        """Revealed cell returns CellState.REVEALED."""
        game = MinesweeperGame(9, 9, 10)
        game.reveal(0, 0)
        self.assertEqual(game.get_cell_state(0, 0), CellState.REVEALED)

    def test_get_cell_state_out_of_bounds(self):
        """Out-of-bounds access returns HIDDEN (safe default), not an exception."""
        game = MinesweeperGame(9, 9, 10)
        self.assertEqual(game.get_cell_state(99, 99), CellState.HIDDEN)
        self.assertEqual(game.get_cell_state(-1, 0), CellState.HIDDEN)

    def test_first_click_safety(self):
        """First reveal should never hit a mine (first-click safety)."""
        for _ in range(50):
            game = MinesweeperGame(9, 9, 10)
            game.reveal(4, 4)
            self.assertNotEqual(game.status, GameStatus.LOST,
                                "First click hit a mine — first-click safety violated!")

    def test_win_condition(self):
        """Revealing all non-mine cells should trigger a win."""
        game = MinesweeperGame(5, 5, 1)
        game.reveal(0, 0)  # place mines
        # Reveal every non-mine cell
        for r in range(5):
            for c in range(5):
                if not game._mines[r][c]:
                    game.reveal(r, c)
        self.assertEqual(game.status, GameStatus.WON)

    def test_flag_unflag_cycle(self):
        """Flag → unflag should return cell to HIDDEN."""
        game = MinesweeperGame(9, 9, 10)
        game.flag(0, 0)
        self.assertEqual(game.get_cell_state(0, 0), CellState.FLAGGED)
        game.unflag(0, 0)
        self.assertEqual(game.get_cell_state(0, 0), CellState.HIDDEN)

    def test_count_flags(self):
        """count_flags() should accurately track flagged cells."""
        game = MinesweeperGame(9, 9, 10)
        game.flag(0, 0)
        game.flag(1, 1)
        self.assertEqual(game.count_flags(), 2)
        game.unflag(0, 0)
        self.assertEqual(game.count_flags(), 1)


class TestAgent(unittest.TestCase):
    """Agent-level tests."""

    def test_opening_move_is_corner(self):
        """First move should always be a corner cell."""
        for _ in range(20):
            game = MinesweeperGame(9, 9, 10)
            log = ReasoningLog()
            agent = MinesweeperAgent(game, log)
            r, c, action, algo = agent.next_move()
            corners = {(0, 0), (0, 8), (8, 0), (8, 8)}
            self.assertIn((r, c), corners,
                          f"Opening move ({r},{c}) is not a corner")
            self.assertEqual(action, ACTION_REVEAL)

    def test_enumerate_solutions_empty_variables(self):
        """Empty variable list should return a single empty-assignment solution."""
        game = MinesweeperGame(9, 9, 10)
        log = ReasoningLog()
        agent = MinesweeperAgent(game, log)
        solutions = agent._enumerate_solutions([], [])
        self.assertEqual(solutions, [{}])

    def test_enumerate_solutions_single_mine(self):
        """One variable with a constraint forcing it to be MINE."""
        game = MinesweeperGame(9, 9, 10)
        log = ReasoningLog()
        agent = MinesweeperAgent(game, log)
        variables = [(0, 0)]
        constraints = [{'hidden': {(0, 0)}, 'count': 1}]
        solutions = agent._enumerate_solutions(variables, constraints)
        self.assertEqual(len(solutions), 1)
        self.assertEqual(solutions[0][(0, 0)], 'MINE')

    def test_enumerate_solutions_single_safe(self):
        """One variable with a constraint forcing it to be SAFE."""
        game = MinesweeperGame(9, 9, 10)
        log = ReasoningLog()
        agent = MinesweeperAgent(game, log)
        variables = [(0, 0)]
        constraints = [{'hidden': {(0, 0)}, 'count': 0}]
        solutions = agent._enumerate_solutions(variables, constraints)
        self.assertEqual(len(solutions), 1)
        self.assertEqual(solutions[0][(0, 0)], 'SAFE')

    def test_full_game_no_crash(self):
        """Agent should complete a full game without exceptions."""
        game = MinesweeperGame(9, 9, 10)
        log = ReasoningLog()
        agent = MinesweeperAgent(game, log)
        moves = 0
        while game.status == GameStatus.ONGOING and moves < 200:
            r, c, action, algo = agent.next_move()
            if action == ACTION_FLAG:
                game.flag(r, c)
            else:
                game.reveal(r, c)
            moves += 1
        self.assertIn(game.status, (GameStatus.WON, GameStatus.LOST))


class TestStatsTracker(unittest.TestCase):
    """Stats tracker tests."""

    def test_win_rate(self):
        """Win rate calculation should be correct."""
        stats = StatsTracker()
        stats.record_game(True)
        stats.record_game(True)
        stats.record_game(False)
        self.assertAlmostEqual(stats.win_rate(), 2 / 3)

    def test_empty_stats(self):
        """Empty tracker should return 0 for all rates."""
        stats = StatsTracker()
        self.assertEqual(stats.win_rate(), 0.0)
        self.assertEqual(stats.avg_moves(), 0.0)


class TestRebuildConstraints(unittest.TestCase):
    """Tests for the extracted _rebuild_constraints helper."""

    def test_filters_known_cells(self):
        """Known cells should be removed from constraint hidden sets."""
        constraints = [
            {'hidden': {(0, 0), (0, 1), (0, 2)}, 'count': 2},
        ]
        known = {(0, 0): 'MINE'}
        clean, frontier = MinesweeperAgent._rebuild_constraints(constraints, known)
        self.assertEqual(len(clean), 1)
        self.assertNotIn((0, 0), clean[0]['hidden'])
        self.assertEqual(clean[0]['count'], 1)  # adjusted for known mine
        self.assertEqual(frontier, {(0, 1), (0, 2)})

    def test_empty_constraint_dropped(self):
        """A constraint with no remaining hidden cells should be dropped."""
        constraints = [
            {'hidden': {(0, 0)}, 'count': 1},
        ]
        known = {(0, 0): 'MINE'}
        clean, frontier = MinesweeperAgent._rebuild_constraints(constraints, known)
        self.assertEqual(len(clean), 0)
        self.assertEqual(frontier, set())


if __name__ == "__main__":
    unittest.main()
