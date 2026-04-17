"""
app.py — Flask Backend for Minesweeper AI Agent
=================================================
REST API serving the game engine and agent over HTTP.
Uses session-based state management to support multiple concurrent clients.
"""

import os
import uuid
from flask import Flask, jsonify, render_template, request

# Import existing core modules
from game_engine import MinesweeperGame, GameStatus, CellState
from agent import MinesweeperAgent, ACTION_REVEAL, ACTION_FLAG
from reasoning_log import ReasoningLog
from stats_tracker import StatsTracker

app = Flask(__name__)
app.secret_key = os.urandom(32)


# ─── Session Management ──────────────────────────────────────────────────────

class AppState:
    def __init__(self):
        self.game = MinesweeperGame(9, 9, 10)
        self.log = ReasoningLog()
        self.agent = MinesweeperAgent(self.game, self.log)
        self.stats = StatsTracker()
        self.move_number = 0
        self.last_move_cell = None      # (r, c) of most recent action
        self.last_move_algo = None       # algorithm used in most recent action


# Session store: session_id → AppState
_sessions: dict[str, AppState] = {}
MAX_SESSIONS = 50


def _get_session(session_id: str) -> AppState | None:
    """Retrieve a game session by ID, or None if not found."""
    return _sessions.get(session_id)


def _create_session() -> tuple[str, AppState]:
    """Create a new game session with a unique ID."""
    # Evict oldest session if at capacity to prevent memory exhaustion
    if len(_sessions) >= MAX_SESSIONS:
        oldest_key = next(iter(_sessions))
        del _sessions[oldest_key]
    sid = uuid.uuid4().hex
    state = AppState()
    _sessions[sid] = state
    return sid, state


def _require_session() -> tuple[AppState | None, str]:
    """Extract session from request. Returns (state_or_None, session_id)."""
    if request.is_json:
        session_id = (request.json or {}).get("session_id", "")
    else:
        session_id = request.args.get("session_id", "")
    return _get_session(session_id), session_id


def get_game_state_payload(state: AppState, session_id: str) -> dict:
    """Builds the JSON response containing the full current state."""
    board_view = state.game.get_board_view()
    status_str = state.game.status.name
    
    # Include the true mine map if the game is lost (for revealing)
    mine_map = None
    if state.game.status == GameStatus.LOST:
        mine_map = state.game.get_mine_map()

    # Build structured last_log entry (dict, not string)
    last_log_entry = state.log.get_last()
    last_log_structured = None
    if last_log_entry:
        r_l, c_l = last_log_entry["move"]
        last_log_structured = {
            "row": r_l,
            "col": c_l,
            "action": last_log_entry["action"],
            "algorithm": last_log_entry["algorithm"],
            "explanation": last_log_entry["explanation"],
            "formatted": state.log.format_entry(last_log_entry),
        }

    return {
        "session_id": session_id,
        "board": board_view,
        "rows": state.game.rows,
        "cols": state.game.cols,
        "mines": state.game.num_mines,
        "status": status_str,
        "flags": state.game.count_flags(),
        "mine_map": mine_map,
        "move_number": state.move_number,
        "last_move_cell": state.last_move_cell,
        "last_move_algo": state.last_move_algo,
        "last_log": last_log_structured,
        "stats": {
            "games_played": state.stats.games_played,
            "wins": state.stats.wins,
            "losses": state.stats.losses,
            "win_rate": round(state.stats.win_rate() * 100, 1),
            "total_moves": state.stats.total_moves,
            "avg_moves": round(state.stats.avg_moves(), 1),
            "algo_counts": dict(state.stats.algo_counts),
        },
    }


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main Web UI."""
    return render_template("index.html")

@app.route("/api/new_game", methods=["POST"])
def new_game():
    """Initialize a new game with posted settings."""
    data = request.json or {}

    # Input validation: clamp to safe ranges
    try:
        rows = max(5, min(int(data.get("rows", 9)), 30))
        cols = max(5, min(int(data.get("cols", 9)), 30))
        mines = max(1, min(int(data.get("mines", 10)), rows * cols - 10))
    except (TypeError, ValueError):
        rows, cols, mines = 9, 9, 10

    # Reuse existing session (preserves stats across games), or create new
    session_id = data.get("session_id")
    state = _get_session(session_id) if session_id else None
    if state is None:
        session_id, state = _create_session()

    state.game = MinesweeperGame(rows, cols, mines)
    state.log = ReasoningLog()
    state.agent = MinesweeperAgent(state.game, state.log)
    state.move_number = 0
    state.last_move_cell = None
    state.last_move_algo = None
    
    return jsonify(get_game_state_payload(state, session_id))

@app.route("/api/state", methods=["GET"])
def get_state():
    """Return the current board state."""
    state, session_id = _require_session()
    if state is None:
        return jsonify({"error": "Invalid or missing session_id"}), 404
    return jsonify(get_game_state_payload(state, session_id))

@app.route("/api/human_action", methods=["POST"])
def human_action():
    """Handle a human click (Reveal or Flag)."""
    state, session_id = _require_session()
    if state is None:
        return jsonify({"error": "Invalid or missing session_id"}), 404

    if state.game.status != GameStatus.ONGOING:
        return jsonify(get_game_state_payload(state, session_id))

    data = request.json or {}
    action = data.get("action")
    r = int(data.get("r", -1))
    c = int(data.get("c", -1))

    if r >= 0 and c >= 0:
        if action == "REVEAL":
            state.game.reveal(r, c)
            state.log.log_move(r, c, "REVEAL", "Human", "Player clicked Reveal")
        elif action == "FLAG":
            # Toggle logic — uses public accessor instead of private _cell_states
            current_cs = state.game.get_cell_state(r, c)
            if current_cs == CellState.HIDDEN:
                state.game.flag(r, c)
                state.log.log_move(r, c, "FLAG", "Human", "Player clicked Flag")
            elif current_cs == CellState.FLAGGED:
                state.game.unflag(r, c)
                state.log.log_move(r, c, "UNFLAG", "Human", "Player unflagged cell")

        state.move_number += 1
        state.last_move_cell = [r, c]
        state.last_move_algo = "Human"

    # If the game just finished on this move, record stats
    if state.game.status != GameStatus.ONGOING:
        state.stats.record_game(state.game.status == GameStatus.WON)

    return jsonify(get_game_state_payload(state, session_id))

@app.route("/api/agent_move", methods=["POST"])
def agent_move():
    """Ask the AI agent for its next move and apply it."""
    state, session_id = _require_session()
    if state is None:
        return jsonify({"error": "Invalid or missing session_id"}), 404

    if state.game.status != GameStatus.ONGOING:
        return jsonify(get_game_state_payload(state, session_id))

    r, c, action, algo = state.agent.next_move()
    state.stats.record_move(algo)
    state.move_number += 1
    state.last_move_cell = [r, c]
    state.last_move_algo = algo

    if action == ACTION_FLAG:
        state.game.flag(r, c)
    elif action == ACTION_REVEAL:
        state.game.reveal(r, c)

    # If the game just finished on this move, record stats
    if state.game.status != GameStatus.ONGOING:
        state.stats.record_game(state.game.status == GameStatus.WON)

    return jsonify(get_game_state_payload(state, session_id))

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Return cumulative statistics for a session."""
    state, session_id = _require_session()
    if state is None:
        return jsonify({"error": "Invalid or missing session_id"}), 404
    return jsonify({
        "games_played": state.stats.games_played,
        "wins": state.stats.wins,
        "losses": state.stats.losses,
        "win_rate": round(state.stats.win_rate() * 100, 1),
        "total_moves": state.stats.total_moves,
        "avg_moves": round(state.stats.avg_moves(), 1),
        "algo_counts": dict(state.stats.algo_counts),
    })


if __name__ == "__main__":
    # Ensure template and static directories exist
    os.makedirs(os.path.join(os.path.dirname(__file__), "templates"), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), "static"), exist_ok=True)
    
    app.run(port=5000, host="127.0.0.1")
