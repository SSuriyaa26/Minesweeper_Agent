"""
main.py — CLI Entry Point
===========================
Wires together the game engine, AI agent, terminal UI, reasoning log,
and statistics tracker.

Modes:
  agent_auto  — Agent plays N games autonomously, prints final stats
  agent_step  — Agent plays one game step-by-step with reasoning shown
  human       — Human plays interactively via keyboard input

Usage:
  python main.py --mode agent_auto --games 20
  python main.py --mode agent_step
  python main.py --mode human
  python main.py --mode agent_auto --games 20 --rows 16 --cols 16 --mines 40
"""

from __future__ import annotations

import argparse
import sys
import time

# Force UTF-8 output on Windows to avoid encoding errors
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from colorama import Fore, Style

from game_engine import MinesweeperGame, GameStatus
from agent import MinesweeperAgent, ACTION_REVEAL, ACTION_FLAG
from reasoning_log import ReasoningLog
from stats_tracker import StatsTracker
from ui import TerminalUI


# ─── Agent Auto Mode ─────────────────────────────────────────────────────────

def run_agent_auto(
    rows: int, cols: int, mines: int, num_games: int
) -> None:
    """
    Agent plays `num_games` games autonomously.
    Prints a progress line per game and a final summary table.
    """
    stats = StatsTracker()

    print(Fore.CYAN + Style.BRIGHT)
    print("╔══════════════════════════════════════════════╗")
    print("║   MINESWEEPER AI — AUTO MODE                ║")
    print(f"║   Board: {rows}×{cols}  Mines: {mines:<3d}  Games: {num_games:<5d}   ║")
    print("╚══════════════════════════════════════════════╝")
    print(Style.RESET_ALL)

    for game_num in range(1, num_games + 1):
        game = MinesweeperGame(rows, cols, mines)
        log = ReasoningLog()
        agent = MinesweeperAgent(game, log)
        move_count = 0

        while game.status == GameStatus.ONGOING:
            r, c, action, algo = agent.next_move()
            stats.record_move(algo)
            move_count += 1

            if action == ACTION_FLAG:
                game.flag(r, c)
            elif action == ACTION_REVEAL:
                game.reveal(r, c)

        won = game.status == GameStatus.WON
        stats.record_game(won)

        result_str = (Fore.GREEN + "WIN " if won else Fore.RED + "LOSS") + Style.RESET_ALL
        print(f"  Game {game_num:>3d}/{num_games}: {result_str}  "
              f"({move_count} moves)")

    print()
    print(stats.summary())
    print()


# ─── Agent Step Mode ─────────────────────────────────────────────────────────

def run_agent_step(rows: int, cols: int, mines: int) -> None:
    """
    Agent plays one game step-by-step.
    After each move, the board and reasoning are displayed.
    Press Enter to advance.
    """
    game = MinesweeperGame(rows, cols, mines)
    log = ReasoningLog()
    agent = MinesweeperAgent(game, log)
    ui = TerminalUI(game)
    stats = StatsTracker()
    move_count = 0

    print(Fore.CYAN + Style.BRIGHT)
    print("╔══════════════════════════════════════════════╗")
    print("║   MINESWEEPER AI — STEP MODE                ║")
    print(f"║   Board: {rows}×{cols}  Mines: {mines}                    ║")
    print("║   Press ENTER to advance, q to quit         ║")
    print("╚══════════════════════════════════════════════╝")
    print(Style.RESET_ALL)

    # Show initial empty board
    print(ui.render_frame(log, move_count, stats))

    while game.status == GameStatus.ONGOING:
        try:
            cmd = input(Fore.GREEN + "  [Enter=next move, q=quit] " + Style.RESET_ALL)
        except (EOFError, KeyboardInterrupt):
            break
        if cmd.strip().lower() == 'q':
            break

        r, c, action, algo = agent.next_move()
        stats.record_move(algo)
        move_count += 1

        if action == ACTION_FLAG:
            game.flag(r, c)
        elif action == ACTION_REVEAL:
            game.reveal(r, c)

        ui.clear_screen()
        print(ui.render_frame(log, move_count, stats))

    # Final board
    won = game.status == GameStatus.WON
    stats.record_game(won)
    ui.clear_screen()
    print(ui.render_frame(log, move_count, stats))

    if game.status == GameStatus.WON:
        print(Fore.GREEN + Style.BRIGHT + "  >>> AGENT WINS! <<<" + Style.RESET_ALL)
    elif game.status == GameStatus.LOST:
        print(Fore.RED + Style.BRIGHT + "  >>> AGENT HIT A MINE! <<<" + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + "  Game interrupted." + Style.RESET_ALL)

    print()
    print(Fore.CYAN + "  ── Full Reasoning Log ──" + Style.RESET_ALL)
    print(log.dump())
    print()
    print(stats.summary())
    print()


# ─── Human Mode ──────────────────────────────────────────────────────────────

def run_human(rows: int, cols: int, mines: int) -> None:
    """
    Human plays Minesweeper interactively.
    Input: r <row> <col> to reveal, f <row> <col> to flag, q to quit.
    """
    game = MinesweeperGame(rows, cols, mines)
    log = ReasoningLog()
    ui = TerminalUI(game)
    move_count = 0

    print(Fore.CYAN + Style.BRIGHT)
    print("╔══════════════════════════════════════════════╗")
    print("║   MINESWEEPER — HUMAN MODE                  ║")
    print(f"║   Board: {rows}×{cols}  Mines: {mines}                    ║")
    print("║   r <row> <col> = reveal                    ║")
    print("║   f <row> <col> = flag                      ║")
    print("║   u <row> <col> = unflag                    ║")
    print("║   q = quit                                  ║")
    print("╚══════════════════════════════════════════════╝")
    print(Style.RESET_ALL)

    while game.status == GameStatus.ONGOING:
        print(ui.render_frame(log, move_count))
        result = ui.get_human_input()

        if result is None:
            print(Fore.YELLOW + "  Goodbye!" + Style.RESET_ALL)
            return

        action, row, col = result
        if action == "invalid":
            continue

        move_count += 1

        if action == "REVEAL":
            game.reveal(row, col)
            log.log_move(row, col, "REVEAL", "Human", "Player chose to reveal")
        elif action == "FLAG":
            game.flag(row, col)
            log.log_move(row, col, "FLAG", "Human", "Player flagged cell")
        elif action == "UNFLAG":
            game.unflag(row, col)
            log.log_move(row, col, "UNFLAG", "Human", "Player removed flag")

        ui.clear_screen()

    # Final board
    ui.clear_screen()
    print(ui.render_frame(log, move_count))

    if game.status == GameStatus.WON:
        print(Fore.GREEN + Style.BRIGHT + "  >>> YOU WIN! <<<" + Style.RESET_ALL)
    else:
        print(Fore.RED + Style.BRIGHT + "  >>> BOOM! You hit a mine! <<<" + Style.RESET_ALL)
    print()


# ─── CLI Argument Parser ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Minesweeper Intelligent Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py --mode agent_auto --games 20\n"
            "  python main.py --mode agent_step\n"
            "  python main.py --mode human\n"
            "  python main.py --mode agent_auto --games 50 "
            "--rows 16 --cols 16 --mines 40\n"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["agent_auto", "agent_step", "human"],
        default="agent_auto",
        help="Play mode (default: agent_auto)",
    )
    parser.add_argument("--games", type=int, default=20, help="Number of games for auto mode")
    parser.add_argument("--rows", type=int, default=9, help="Board rows (default: 9)")
    parser.add_argument("--cols", type=int, default=9, help="Board columns (default: 9)")
    parser.add_argument("--mines", type=int, default=10, help="Number of mines (default: 10)")

    args = parser.parse_args()

    if args.mode == "agent_auto":
        run_agent_auto(args.rows, args.cols, args.mines, args.games)
    elif args.mode == "agent_step":
        run_agent_step(args.rows, args.cols, args.mines)
    elif args.mode == "human":
        run_human(args.rows, args.cols, args.mines)


if __name__ == "__main__":
    main()
