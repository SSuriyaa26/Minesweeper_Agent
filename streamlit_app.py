"""
streamlit_app.py — Streamlit Deployment for Minesweeper AI Agent
================================================================
Premium dark-themed Streamlit UI. The interactive board is rendered as
an HTML component; human moves use sidebar inputs; AI controls drive
the agent step-by-step or in auto-run mode.

Deploy on Streamlit Community Cloud by pushing to GitHub.
"""

import streamlit as st
import streamlit.components.v1 as components
import time

from game_engine import MinesweeperGame, GameStatus, CellState
from agent import MinesweeperAgent, ACTION_REVEAL, ACTION_FLAG
from reasoning_log import ReasoningLog
from stats_tracker import StatsTracker

# ─── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Minesweeper AI Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
.stApp {
    background: #080c14;
    background-image:
        radial-gradient(ellipse at 20% 0%, rgba(88,166,255,0.06) 0%, transparent 60%),
        radial-gradient(ellipse at 80% 100%, rgba(188,140,255,0.05) 0%, transparent 60%);
}
[data-testid="stSidebar"] {
    background: rgba(22, 27, 34, 0.95) !important;
    border-right: 1px solid rgba(48,54,61,0.6) !important;
}
h1, h2, h3, h4, p, span, label, .stMarkdown { color: #f0f6fc !important; }
[data-testid="stMetricValue"] { font-family: 'JetBrains Mono', monospace !important; }
#MainMenu, footer, header { visibility: hidden; }

/* Glass panels */
.glass-panel {
    background: rgba(22, 27, 34, 0.8);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(48,54,61,0.6);
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}

/* Pipeline badges */
.pipe-badge {
    display: inline-block;
    padding: 6px 14px;
    border-radius: 8px;
    font-weight: 700;
    font-size: 0.82rem;
    font-family: 'JetBrains Mono', monospace;
    border: 2px solid transparent;
    opacity: 0.45;
    transition: all 0.3s;
    margin-right: 6px;
}
.pipe-badge.active { opacity: 1; transform: translateY(-2px); }
.pipe-badge.csp       { background: rgba(88,166,255,0.12); color: #58a6ff; }
.pipe-badge.csp.active { border-color: #58a6ff; box-shadow: 0 0 16px rgba(88,166,255,0.25); }
.pipe-badge.fc        { background: rgba(210,153,34,0.12); color: #d29922; }
.pipe-badge.fc.active  { border-color: #d29922; box-shadow: 0 0 16px rgba(210,153,34,0.25); }
.pipe-badge.bt        { background: rgba(188,140,255,0.12); color: #bc8cff; }
.pipe-badge.bt.active  { border-color: #bc8cff; box-shadow: 0 0 16px rgba(188,140,255,0.25); }
.pipe-badge.prob      { background: rgba(63,185,80,0.12); color: #3fb950; }
.pipe-badge.prob.active { border-color: #3fb950; box-shadow: 0 0 16px rgba(63,185,80,0.25); }

/* Algo bar */
.algo-row { display: flex; align-items: center; gap: 8px; margin: 6px 0; }
.algo-tag { font-size: 0.7rem; font-weight: 700; font-family: 'JetBrains Mono',monospace; min-width: 42px; text-align: center; padding: 2px 8px; border-radius: 4px; }
.algo-tag.csp  { background: rgba(88,166,255,0.15); color: #58a6ff; }
.algo-tag.fc   { background: rgba(210,153,34,0.15); color: #d29922; }
.algo-tag.bt   { background: rgba(188,140,255,0.15); color: #bc8cff; }
.algo-tag.prob { background: rgba(63,185,80,0.15); color: #3fb950; }
.bar-track { flex: 1; height: 8px; background: rgba(255,255,255,0.04); border-radius: 4px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
.bar-fill.csp  { background: linear-gradient(90deg, #58a6ff, rgba(88,166,255,0.4)); }
.bar-fill.fc   { background: linear-gradient(90deg, #d29922, rgba(210,153,34,0.4)); }
.bar-fill.bt   { background: linear-gradient(90deg, #bc8cff, rgba(188,140,255,0.4)); }
.bar-fill.prob { background: linear-gradient(90deg, #3fb950, rgba(63,185,80,0.4)); }
.algo-cnt { font-size: 0.8rem; font-weight: 700; font-family: 'JetBrains Mono',monospace; color: #8b949e; min-width: 28px; text-align: right; }

/* Log entry */
.log-entry {
    font-size: 0.8rem; line-height: 1.5; padding: 0.6rem 0.75rem;
    background: rgba(255,255,255,0.02); border-radius: 6px;
    border-left: 3px solid rgba(48,54,61,0.6);
    margin-bottom: 6px; color: #f0f6fc;
}
.log-entry.algo-csp  { border-left-color: #58a6ff; }
.log-entry.algo-fc   { border-left-color: #d29922; }
.log-entry.algo-bt   { border-left-color: #bc8cff; }
.log-entry.algo-prob { border-left-color: #3fb950; }
.log-entry.algo-human { border-left-color: #484f58; }
.log-head { display: flex; justify-content: space-between; margin-bottom: 3px; }
.log-act  { font-weight: 700; }
.log-body { color: #8b949e; font-size: 0.75rem; }

/* Game over banner */
.game-banner {
    text-align: center; padding: 1.5rem; border-radius: 12px; margin: 1rem 0;
    font-family: 'Inter', sans-serif;
}
.game-banner.won  { background: rgba(63,185,80,0.12); border: 1px solid rgba(63,185,80,0.3); }
.game-banner.lost { background: rgba(248,81,73,0.12); border: 1px solid rgba(248,81,73,0.3); }
.game-banner h2 { margin: 0 0 0.3rem 0; font-size: 1.8rem; }
.game-banner p  { margin: 0; color: #8b949e; }
</style>
""", unsafe_allow_html=True)

# ─── Difficulty Presets ───────────────────────────────────────────────────────

DIFFICULTIES = {
    "Beginner (9×9, 10 mines)": (9, 9, 10),
    "Intermediate (16×16, 40 mines)": (16, 16, 40),
    "Expert (16×30, 99 mines)": (16, 30, 99),
}

# ─── Session State ────────────────────────────────────────────────────────────

def init_game(rows=9, cols=9, mines=10):
    st.session_state.game = MinesweeperGame(rows, cols, mines)
    st.session_state.log = ReasoningLog()
    st.session_state.agent = MinesweeperAgent(
        st.session_state.game, st.session_state.log
    )
    st.session_state.move_number = 0
    st.session_state.last_move_cell = None
    st.session_state.last_move_algo = None
    st.session_state.auto_running = False
    st.session_state.log_entries = []

if "game" not in st.session_state:
    st.session_state.stats = StatsTracker()
    st.session_state.auto_speed = 0.2
    init_game()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def do_agent_step():
    game = st.session_state.game
    if game.status != GameStatus.ONGOING:
        st.session_state.auto_running = False
        return False
    r, c, action, algo = st.session_state.agent.next_move()
    st.session_state.stats.record_move(algo)
    st.session_state.move_number += 1
    st.session_state.last_move_cell = (r, c)
    st.session_state.last_move_algo = algo
    if action == ACTION_FLAG:
        game.flag(r, c)
    elif action == ACTION_REVEAL:
        game.reveal(r, c)
    last = st.session_state.log.get_last()
    if last:
        st.session_state.log_entries.append(
            {**last, "move_num": st.session_state.move_number}
        )
    if game.status != GameStatus.ONGOING:
        st.session_state.stats.record_game(game.status == GameStatus.WON)
        st.session_state.auto_running = False
        return False
    return True


def do_human_action(r, c, action_type):
    game = st.session_state.game
    if game.status != GameStatus.ONGOING:
        return
    if action_type == "REVEAL":
        game.reveal(r, c)
        st.session_state.log.log_move(r, c, "REVEAL", "Human", "Player clicked Reveal")
    elif action_type == "FLAG":
        cs = game._cell_states[r][c]
        if cs == CellState.HIDDEN:
            game.flag(r, c)
            st.session_state.log.log_move(r, c, "FLAG", "Human", "Player flagged cell")
        elif cs == CellState.FLAGGED:
            game.unflag(r, c)
            st.session_state.log.log_move(r, c, "UNFLAG", "Human", "Player unflagged cell")
    st.session_state.move_number += 1
    st.session_state.last_move_cell = (r, c)
    st.session_state.last_move_algo = "Human"
    last = st.session_state.log.get_last()
    if last:
        st.session_state.log_entries.append(
            {**last, "move_num": st.session_state.move_number}
        )
    if game.status != GameStatus.ONGOING:
        st.session_state.stats.record_game(game.status == GameStatus.WON)

# ─── Board HTML Renderer ─────────────────────────────────────────────────────

NUMBER_COLORS = {
    1: "#58a6ff", 2: "#3fb950", 3: "#f85149", 4: "#bc8cff",
    5: "#db6d28", 6: "#39d2c0", 7: "#f778ba", 8: "#d29922",
}

def render_board_html():
    game = st.session_state.game
    board = game.get_board_view()
    mine_map = game.get_mine_map() if game.status == GameStatus.LOST else None
    last = st.session_state.last_move_cell
    rows, cols = game.rows, game.cols
    sz = 38 if cols <= 16 else 28
    gap = 2

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');
    body {{ margin:0; background: transparent; }}
    .board {{
        display: grid;
        grid-template-columns: repeat({cols}, {sz}px);
        gap: {gap}px;
        background: rgba(48,54,61,0.6);
        border: 3px solid rgba(48,54,61,0.8);
        border-radius: 8px;
        padding: 3px;
        width: fit-content;
    }}
    .c {{
        width: {sz}px; height: {sz}px;
        display: flex; align-items: center; justify-content: center;
        font-weight: 700; font-size: {int(sz*0.48)}px;
        font-family: 'JetBrains Mono', monospace;
        border-radius: 3px; box-sizing: border-box;
    }}
    .hid {{ background: #21262d; }}
    .rev {{ background: #0d1117; }}
    .flg {{ background: #21262d; }}
    .mne {{ background: rgba(248,81,73,0.12); }}
    .hit {{ background: #f85149; }}
    .lm  {{ box-shadow: 0 0 0 2px rgba(88,166,255,0.7); z-index: 2; }}
    .lf  {{ box-shadow: 0 0 0 2px rgba(248,81,73,0.7); z-index: 2; }}
    @keyframes pulse {{ 0% {{ opacity:1; }} 50% {{ opacity:0.7; }} 100% {{ opacity:1; }} }}
    .lm, .lf {{ animation: pulse 0.8s ease-out; }}
    </style>
    """
    cells_html = []
    for r in range(rows):
        for c in range(cols):
            val = board[r][c]
            cls = ["c"]
            content = ""
            is_last = last and last[0] == r and last[1] == c

            if val == "H":
                if game.status == GameStatus.LOST and mine_map and mine_map[r][c]:
                    cls.append("rev mne")
                    content = "💣"
                elif game.status == GameStatus.WON:
                    cls.append("hid flg")
                    content = "🚩"
                else:
                    cls.append("hid")
            elif val == "F":
                cls.append("hid flg")
                content = "🚩"
            elif val == "M":
                cls.append("rev hit" if is_last else "rev mne")
                content = "💣"
            else:
                cls.append("rev")
                if val > 0:
                    color = NUMBER_COLORS.get(val, "#f0f6fc")
                    content = f'<span style="color:{color}">{val}</span>'

            if is_last and val != "M":
                last_algo = st.session_state.last_move_algo or ""
                last_log = st.session_state.log.get_last()
                is_flag = last_log and last_log["action"] in ("FLAG", "UNFLAG")
                cls.append("lf" if is_flag else "lm")

            cells_html.append(f'<div class="{" ".join(cls)}">{content}</div>')

    html = css + '<div class="board">' + "\n".join(cells_html) + "</div>"
    total_h = rows * (sz + gap) + 12
    components.html(html, height=total_h, scrolling=False)

# ─── Pipeline HTML ────────────────────────────────────────────────────────────

ALGO_MAP = {
    "CSP": "csp",
    "Forward Checking": "fc",
    "Backtracking": "bt",
    "Probabilistic": "prob",
}

def render_pipeline():
    algo = st.session_state.last_move_algo
    badges = []
    labels = {"csp": "① CSP", "fc": "② Forward Check", "bt": "③ Backtrack", "prob": "④ Probabilistic"}
    for name, key in ALGO_MAP.items():
        active = "active" if algo == name else ""
        badges.append(f'<span class="pipe-badge {key} {active}">{labels[key]}</span>')
    arrow = ' <span style="color:#484f58;font-size:1.2rem;">→</span> '
    st.markdown(
        '<div class="glass-panel" style="display:flex;align-items:center;gap:4px;flex-wrap:wrap;">'
        + '<span style="font-size:1rem;margin-right:8px;">🧠</span>'
        + arrow.join(badges)
        + "</div>",
        unsafe_allow_html=True,
    )

# ─── Stats HTML ───────────────────────────────────────────────────────────────

def render_stats():
    stats = st.session_state.stats
    ac = stats.algo_counts
    total = max(sum(ac.values()), 1)
    rows_html = ""
    for name, key in ALGO_MAP.items():
        cnt = ac.get(name, 0)
        pct = cnt / total * 100
        rows_html += f"""
        <div class="algo-row">
            <span class="algo-tag {key}">{key.upper()}</span>
            <div class="bar-track"><div class="bar-fill {key}" style="width:{pct}%"></div></div>
            <span class="algo-cnt">{cnt}</span>
        </div>"""
    summary = f"""
    <div style="display:flex;gap:8px;border-top:1px solid rgba(48,54,61,0.6);padding-top:10px;margin-top:10px;">
        <div style="flex:1;text-align:center;">
            <div style="font-size:0.65rem;color:#484f58;text-transform:uppercase;font-weight:600;">Games</div>
            <div style="font-size:1.15rem;font-weight:800;font-family:'JetBrains Mono',monospace;">{stats.games_played}</div>
        </div>
        <div style="flex:1;text-align:center;">
            <div style="font-size:0.65rem;color:#484f58;text-transform:uppercase;font-weight:600;">Win Rate</div>
            <div style="font-size:1.15rem;font-weight:800;font-family:'JetBrains Mono',monospace;">{stats.win_rate()*100:.1f}%</div>
        </div>
        <div style="flex:1;text-align:center;">
            <div style="font-size:0.65rem;color:#484f58;text-transform:uppercase;font-weight:600;">Moves</div>
            <div style="font-size:1.15rem;font-weight:800;font-family:'JetBrains Mono',monospace;">{stats.total_moves}</div>
        </div>
    </div>"""
    st.markdown(
        f'<div class="glass-panel"><h4 style="margin:0 0 10px 0;">📊 Algorithm Statistics</h4>{rows_html}{summary}</div>',
        unsafe_allow_html=True,
    )

# ─── Log HTML ─────────────────────────────────────────────────────────────────

def render_log():
    entries = st.session_state.log_entries
    if not entries:
        inner = '<div style="color:#484f58;text-align:center;padding:2rem 0;font-size:0.85rem;">Click <b style="color:#bc8cff;">▶ Step</b> to watch the AI think…</div>'
    else:
        items = []
        for e in reversed(entries[-30:]):
            r_e, c_e = e["move"]
            algo = e["algorithm"]
            key = ALGO_MAP.get(algo, "human")
            items.append(
                f'<div class="log-entry algo-{key}">'
                f'<div class="log-head"><span class="log-act">#{e["move_num"]} {e["action"]} → ({r_e},{c_e})</span>'
                f'<span class="algo-tag {key}">{algo}</span></div>'
                f'<div class="log-body">{e["explanation"]}</div></div>'
            )
        inner = "\n".join(items)
    st.markdown(
        f'<div class="glass-panel"><h4 style="margin:0 0 10px 0;">📝 Reasoning Log</h4>'
        f'<div style="max-height:320px;overflow-y:auto;">{inner}</div></div>',
        unsafe_allow_html=True,
    )

# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '## 🤖 Minesweeper<span style="background:linear-gradient(135deg,#58a6ff,#bc8cff);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent;">AI</span>',
        unsafe_allow_html=True,
    )
    st.caption("Intelligent Agent Demo")
    st.divider()

    st.markdown("#### 🎮 Game Controls")
    diff = st.selectbox("Difficulty", list(DIFFICULTIES.keys()), label_visibility="collapsed")
    if st.button("🔄 New Game", use_container_width=True, type="primary"):
        init_game(*DIFFICULTIES[diff])
        st.rerun()

    st.divider()
    st.markdown("#### 🤖 AI Controls")
    ac1, ac2 = st.columns(2)
    game = st.session_state.game
    ongoing = game.status == GameStatus.ONGOING
    with ac1:
        step_btn = st.button("▶ Step", use_container_width=True, disabled=not ongoing)
    with ac2:
        auto_lbl = "⏸ Stop" if st.session_state.auto_running else "⏩ Auto"
        auto_btn = st.button(auto_lbl, use_container_width=True, disabled=not ongoing and not st.session_state.auto_running)

    if step_btn:
        do_agent_step()
        st.rerun()
    if auto_btn:
        st.session_state.auto_running = not st.session_state.auto_running
        if st.session_state.auto_running:
            do_agent_step()
        st.rerun()

    if st.session_state.auto_running:
        speed_ms = st.slider("Speed (ms/move)", 50, 800, 200, 50)
        st.session_state.auto_speed = speed_ms / 1000

    st.divider()
    st.markdown("#### 👆 Human Play")
    hc1, hc2 = st.columns(2)
    with hc1:
        h_row = st.number_input("Row", 0, max(game.rows - 1, 0), 0)
    with hc2:
        h_col = st.number_input("Col", 0, max(game.cols - 1, 0), 0)
    hb1, hb2 = st.columns(2)
    with hb1:
        if st.button("👆 Reveal", use_container_width=True, disabled=not ongoing):
            do_human_action(h_row, h_col, "REVEAL")
            st.rerun()
    with hb2:
        if st.button("🚩 Flag", use_container_width=True, disabled=not ongoing):
            do_human_action(h_row, h_col, "FLAG")
            st.rerun()

# ─── Main Content ─────────────────────────────────────────────────────────────

# Header metrics
hc1, hc2, hc3, hc4 = st.columns([3, 1, 1, 1])
with hc1:
    st.markdown(
        '<h1 style="margin:0;font-size:2rem;font-weight:800;">🤖 Minesweeper'
        '<span style="background:linear-gradient(135deg,#58a6ff,#bc8cff);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent;">AI</span></h1>',
        unsafe_allow_html=True,
    )
status_name = game.status.name
with hc2:
    emoji = {"ONGOING": "🟢", "WON": "🏆", "LOST": "💥"}.get(status_name, "⚪")
    st.metric("Status", f"{emoji} {status_name}")
with hc3:
    remaining = game.num_mines - game.count_flags()
    st.metric("Mines", f"💣 {remaining}/{game.num_mines}")
with hc4:
    st.metric("Move", f"#{st.session_state.move_number}")

# Pipeline
render_pipeline()

# Game over banner
if game.status == GameStatus.WON:
    st.markdown(
        f'<div class="game-banner won"><h2>🎉 Victory!</h2>'
        f'<p>AI cleared the board in {st.session_state.move_number} moves</p></div>',
        unsafe_allow_html=True,
    )
elif game.status == GameStatus.LOST:
    st.markdown(
        f'<div class="game-banner lost"><h2>💥 Game Over</h2>'
        f'<p>Hit a mine after {st.session_state.move_number} moves</p></div>',
        unsafe_allow_html=True,
    )

# Board + Sidebar panels
board_col, info_col = st.columns([3, 2])

with board_col:
    render_board_html()

with info_col:
    render_stats()
    render_log()

# ─── Auto-Run Loop ────────────────────────────────────────────────────────────

if st.session_state.auto_running and game.status == GameStatus.ONGOING:
    time.sleep(st.session_state.auto_speed)
    do_agent_step()
    st.rerun()
