// ═══════════════════════════════════════════════════════════════════════════════
//  Minesweeper AI — Interactive Frontend
// ═══════════════════════════════════════════════════════════════════════════════

// State
let isAutoRunning = false;
let autoTimer = null;
let currentSettings = { rows: 9, cols: 9, mines: 10 };
let lastLogId = 0; // Simple counter to track unique log entries
let moveCount = 0;

// DOM Elements
const boardContainer = document.getElementById('board-container');
const statusEl = document.getElementById('game-status');
const minesEl = document.getElementById('game-mines');
const moveNumberEl = document.getElementById('move-number');
const logContainer = document.getElementById('log-container');
const gameOverlay = document.getElementById('game-overlay');
const overlayIcon = document.getElementById('overlay-icon');
const overlayTitle = document.getElementById('overlay-title');
const overlaySubtitle = document.getElementById('overlay-subtitle');

const btnNewGame = document.getElementById('btn-new-game');
const btnOverlayNew = document.getElementById('btn-overlay-new');
const btnAgentStep = document.getElementById('btn-agent-step');
const btnAgentAuto = document.getElementById('btn-agent-auto');
const difficultySelect = document.getElementById('board-size');
const speedSlider = document.getElementById('speed-slider');
const speedValueMs = document.getElementById('speed-value-ms');
const speedControl = document.getElementById('speed-control');
const chipStatus = document.getElementById('chip-status');

// Pipeline step elements
const pipeSteps = {
    'CSP': document.getElementById('pipe-csp'),
    'Forward Checking': document.getElementById('pipe-forward'),
    'Backtracking': document.getElementById('pipe-backtrack'),
    'Probabilistic': document.getElementById('pipe-prob'),
};

// Stats elements
const barCsp = document.getElementById('bar-csp');
const barFc = document.getElementById('bar-fc');
const barBt = document.getElementById('bar-bt');
const barProb = document.getElementById('bar-prob');
const countCsp = document.getElementById('count-csp');
const countFc = document.getElementById('count-fc');
const countBt = document.getElementById('count-bt');
const countProb = document.getElementById('count-prob');
const statGames = document.getElementById('stat-games');
const statWinrate = document.getElementById('stat-winrate');
const statTotalMoves = document.getElementById('stat-total-moves');

// ─── INIT ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    fetchState();
    setupEventListeners();
});

function setupEventListeners() {
    btnNewGame.addEventListener('click', startNewGame);
    btnOverlayNew.addEventListener('click', startNewGame);
    btnAgentStep.addEventListener('click', agentNextMove);
    btnAgentAuto.addEventListener('click', toggleAutoRun);
    boardContainer.addEventListener('contextmenu', e => e.preventDefault());

    speedSlider.addEventListener('input', () => {
        const val = 830 - parseInt(speedSlider.value); // Invert: slider right = fast = low ms
        speedValueMs.textContent = val;
        if (isAutoRunning) {
            clearInterval(autoTimer);
            autoTimer = setInterval(agentNextMove, val);
        }
    });
}

// ─── API CALLS ─────────────────────────────────────────────────────────────

async function fetchState() {
    try {
        const res = await fetch('/api/state');
        const data = await res.json();
        renderState(data);
    } catch (err) {
        console.error('Failed to fetch state:', err);
    }
}

async function startNewGame() {
    const val = difficultySelect.value.split(',');
    currentSettings = {
        rows: parseInt(val[0]),
        cols: parseInt(val[1]),
        mines: parseInt(val[2])
    };

    if (isAutoRunning) toggleAutoRun();
    gameOverlay.classList.remove('visible');
    moveCount = 0;
    lastLogId = 0;

    try {
        const res = await fetch('/api/new_game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentSettings)
        });
        const data = await res.json();
        logContainer.innerHTML = '<div class="log-empty">Click <strong>"Agent: Next Move"</strong> to watch the AI think…</div>';
        clearPipeline();
        renderState(data);
    } catch (err) {
        console.error('Failed to start new game:', err);
    }
}

async function humanAction(r, c, action) {
    if (isAutoRunning) toggleAutoRun();
    try {
        const res = await fetch('/api/human_action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ r, c, action })
        });
        const data = await res.json();
        renderState(data);
    } catch (err) {
        console.error('Human action failed:', err);
    }
}

async function agentNextMove() {
    try {
        const res = await fetch('/api/agent_move', { method: 'POST' });
        const data = await res.json();
        renderState(data);
        if (data.status !== 'ONGOING' && isAutoRunning) {
            toggleAutoRun();
        }
    } catch (err) {
        console.error('Agent move failed:', err);
        if (isAutoRunning) toggleAutoRun();
    }
}

// ─── AUTO RUN ──────────────────────────────────────────────────────────────

function toggleAutoRun() {
    isAutoRunning = !isAutoRunning;

    if (isAutoRunning) {
        btnAgentAuto.classList.add('active');
        btnAgentAuto.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
            Stop Auto Run
        `;
        btnAgentStep.disabled = true;
        speedControl.style.display = 'block';

        const interval = 830 - parseInt(speedSlider.value);
        autoTimer = setInterval(agentNextMove, interval);
    } else {
        btnAgentAuto.classList.remove('active');
        btnAgentAuto.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon><line x1="19" y1="3" x2="19" y2="21"></line></svg>
            Auto Run
        `;
        clearInterval(autoTimer);
        btnAgentStep.disabled = false;
        speedControl.style.display = 'none';
    }
}

// ─── RENDER STATE ──────────────────────────────────────────────────────────

function renderState(data) {
    const { board, rows, cols, mines, status, flags, mine_map,
            move_number, last_move_cell, last_move_algo, last_log, stats } = data;

    moveCount = move_number || 0;

    // 1. Header chips
    statusEl.textContent = status;
    const dot = chipStatus.querySelector('.chip-dot');
    dot.className = 'chip-dot ' + status.toLowerCase();

    const remaining = mines - flags;
    minesEl.textContent = `${remaining} / ${mines}`;
    moveNumberEl.textContent = moveCount;

    // 2. Disable/enable controls
    if (status !== 'ONGOING') {
        btnAgentStep.disabled = true;
        btnAgentAuto.disabled = true;
        if (isAutoRunning) toggleAutoRun();
    } else {
        if (!isAutoRunning) btnAgentStep.disabled = false;
        btnAgentAuto.disabled = false;
    }

    // 3. Pipeline highlight
    updatePipeline(last_move_algo);

    // 4. Render Board
    boardContainer.innerHTML = '';
    boardContainer.style.gridTemplateColumns = `repeat(${cols}, 1fr)`;
    if (cols > 16) {
        boardContainer.classList.add('expert');
    } else {
        boardContainer.classList.remove('expert');
    }

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const cellVal = board[r][c];
            const cellDiv = document.createElement('div');
            cellDiv.className = 'cell';

            if (status === 'ONGOING') {
                cellDiv.addEventListener('mousedown', (e) => {
                    if (e.button === 0) humanAction(r, c, 'REVEAL');
                    else if (e.button === 2) humanAction(r, c, 'FLAG');
                });
            }

            if (cellVal === 'H') {
                cellDiv.classList.add('hidden');
            } else if (cellVal === 'F') {
                cellDiv.classList.add('hidden', 'flag');
            } else if (cellVal === 'M') {
                cellDiv.classList.add('revealed', 'mine', 'mine-hit');
            } else {
                cellDiv.classList.add('revealed');
                if (cellVal > 0) {
                    cellDiv.setAttribute('data-val', cellVal);
                    cellDiv.textContent = cellVal;
                }
            }

            // Lost: show all mines
            if (status === 'LOST' && mine_map && mine_map[r][c]) {
                if (!cellDiv.classList.contains('flag') && !cellDiv.classList.contains('mine-hit')) {
                    cellDiv.classList.add('revealed', 'mine');
                }
            }

            // Won: auto-flag remaining
            if (status === 'WON' && cellVal === 'H') {
                cellDiv.classList.add('flag');
            }

            // Highlight last move
            if (last_move_cell && last_move_cell[0] === r && last_move_cell[1] === c) {
                if (last_log && last_log.action === 'FLAG') {
                    cellDiv.classList.add('last-move-flag');
                } else {
                    cellDiv.classList.add('last-move');
                }
            }

            boardContainer.appendChild(cellDiv);
        }
    }

    // 5. Game Over Overlay
    if (status === 'WON') {
        overlayIcon.textContent = '🎉';
        overlayTitle.textContent = 'Victory!';
        overlayTitle.style.color = 'var(--accent-green)';
        overlaySubtitle.textContent = `AI cleared the board in ${moveCount} moves`;
        gameOverlay.classList.add('visible');
    } else if (status === 'LOST') {
        overlayIcon.textContent = '💥';
        overlayTitle.textContent = 'Game Over';
        overlayTitle.style.color = 'var(--accent-red)';
        overlaySubtitle.textContent = `Hit a mine after ${moveCount} moves`;
        gameOverlay.classList.add('visible');
    }

    // 6. Stats Dashboard
    if (stats) {
        updateStats(stats);
    }

    // 7. Reasoning Log
    if (last_log) {
        appendLogEntry(last_log);
    }
}

// ─── PIPELINE ──────────────────────────────────────────────────────────────

function updatePipeline(algo) {
    // Clear all active
    Object.values(pipeSteps).forEach(el => el.classList.remove('active'));

    if (algo && pipeSteps[algo]) {
        pipeSteps[algo].classList.add('active');
    }
}

function clearPipeline() {
    Object.values(pipeSteps).forEach(el => el.classList.remove('active'));
}

// ─── STATS ─────────────────────────────────────────────────────────────────

function updateStats(stats) {
    const ac = stats.algo_counts || {};
    const csp = ac['CSP'] || 0;
    const fc = ac['Forward Checking'] || 0;
    const bt = ac['Backtracking'] || 0;
    const prob = ac['Probabilistic'] || 0;
    const total = csp + fc + bt + prob || 1;

    countCsp.textContent = csp;
    countFc.textContent = fc;
    countBt.textContent = bt;
    countProb.textContent = prob;

    barCsp.style.width = (csp / total * 100) + '%';
    barFc.style.width = (fc / total * 100) + '%';
    barBt.style.width = (bt / total * 100) + '%';
    barProb.style.width = (prob / total * 100) + '%';

    statGames.textContent = stats.games_played;
    statWinrate.textContent = stats.win_rate + '%';
    statTotalMoves.textContent = stats.total_moves;
}

// ─── LOG ───────────────────────────────────────────────────────────────────

function appendLogEntry(entry) {
    const emptyMsg = logContainer.querySelector('.log-empty');
    if (emptyMsg) emptyMsg.remove();

    // Deduplicate
    const key = `${entry.row},${entry.col},${entry.action},${moveCount}`;
    if (logContainer.querySelector(`[data-key="${key}"]`)) return;

    const algo = entry.algorithm || 'Human';
    const algoClass = getAlgoClass(algo);
    const algoTag = getAlgoTagClass(algo);

    const div = document.createElement('div');
    div.className = `log-entry algo-${algoClass}`;
    div.setAttribute('data-key', key);
    div.innerHTML = `
        <div class="log-header">
            <span class="log-action">#${moveCount} ${entry.action} → (${entry.row}, ${entry.col})</span>
            <span class="log-algo-tag ${algoTag}">${algo}</span>
        </div>
        <div class="log-body">${entry.explanation}</div>
    `;
    logContainer.appendChild(div);
    logContainer.scrollTop = logContainer.scrollHeight;
}

function getAlgoClass(algo) {
    const map = {
        'CSP': 'csp',
        'Forward Checking': 'fc',
        'Backtracking': 'bt',
        'Probabilistic': 'prob',
        'Human': 'human'
    };
    return map[algo] || 'human';
}

function getAlgoTagClass(algo) {
    return getAlgoClass(algo); // Same mapping
}
