let isAutoRunning = false;
let autoTimer = null;
let sessionId = null;
let currentSettings = { rows: 9, cols: 9, mines: 10 };
let moveCount = 0;

const boardContainer = document.getElementById('board-container');
const statusDot = document.getElementById('status-dot');
const statusChip = document.getElementById('chip-status');
const minesEl = document.getElementById('game-mines');
const moveNumberEl = document.getElementById('move-number');
const logContainer = document.getElementById('log-container');
const gameOverlay = document.getElementById('game-overlay');

const btnNewGame = document.getElementById('btn-new-game');
const btnOverlayNew = document.getElementById('btn-overlay-new');
const btnAgentStep = document.getElementById('btn-agent-step');
const btnAgentAuto = document.getElementById('btn-agent-auto');
const difficultySelect = document.getElementById('board-size');
const speedSlider = document.getElementById('speed-slider');
const speedValueMs = document.getElementById('speed-value-ms');
const speedControl = document.getElementById('speed-control');

const pipeSteps = {
    'CSP': document.getElementById('pipe-csp'),
    'Forward Checking': document.getElementById('pipe-forward'),
    'Backtracking': document.getElementById('pipe-backtrack'),
    'Probabilistic': document.getElementById('pipe-prob'),
};

document.addEventListener('DOMContentLoaded', () => {
    btnNewGame.addEventListener('click', startNewGame);
    btnOverlayNew.addEventListener('click', startNewGame);
    btnAgentStep.addEventListener('click', agentNextMove);
    btnAgentAuto.addEventListener('click', toggleAutoRun);
    boardContainer.addEventListener('contextmenu', e => e.preventDefault());

    speedSlider.addEventListener('input', () => {
        const val = 830 - parseInt(speedSlider.value);
        speedValueMs.textContent = `${val}ms`;
        if (isAutoRunning) {
            clearInterval(autoTimer);
            autoTimer = setInterval(agentNextMove, val);
        }
    });

    startNewGame();
});

async function startNewGame() {
    const val = difficultySelect.value.split(',');
    currentSettings = {
        rows: parseInt(val[0]),
        cols: parseInt(val[1]),
        mines: parseInt(val[2])
    };

    if (isAutoRunning) toggleAutoRun();
    gameOverlay.classList.add('hidden');
    moveCount = 0;
    
    statusDot.className = 'pulse-dot active';
    statusChip.textContent = 'Initializing';

    try {
        const res = await fetch('/api/new_game', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ...currentSettings, session_id: sessionId })
        });
        const data = await res.json();
        sessionId = data.session_id;
        logContainer.innerHTML = '<div class="trace-empty">Awaiting execution...</div>';
        clearPipeline();
        renderState(data);
    } catch (err) {
        console.error('Failed to init game:', err);
    }
}

async function humanAction(r, c, action) {
    if (isAutoRunning) toggleAutoRun();
    try {
        const res = await fetch('/api/human_action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ r, c, action, session_id: sessionId })
        });
        const data = await res.json();
        renderState(data);
    } catch (err) {
        console.error('Action payload rejected:', err);
    }
}

async function agentNextMove() {
    try {
        const res = await fetch('/api/agent_move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        const data = await res.json();
        renderState(data);
        if (data.status !== 'ONGOING' && isAutoRunning) {
            toggleAutoRun();
        }
    } catch (err) {
        console.error('Agent invocation failed:', err);
        if (isAutoRunning) toggleAutoRun();
    }
}

function toggleAutoRun() {
    isAutoRunning = !isAutoRunning;

    if (isAutoRunning) {
        btnAgentAuto.classList.add('active');
        btnAgentAuto.textContent = 'Halt';
        btnAgentStep.disabled = true;
        speedControl.classList.remove('hidden');

        const interval = 830 - parseInt(speedSlider.value);
        autoTimer = setInterval(agentNextMove, interval);
        
        statusDot.className = 'pulse-dot active';
        statusChip.textContent = 'Executing';
    } else {
        btnAgentAuto.classList.remove('active');
        btnAgentAuto.textContent = 'Auto-Run';
        clearInterval(autoTimer);
        btnAgentStep.disabled = false;
        speedControl.classList.add('hidden');
        
        statusDot.className = 'pulse-dot';
        statusChip.textContent = 'Standby';
    }
}

function renderState(data) {
    const { board, rows, cols, mines, status, flags, mine_map,
            move_number, last_move_cell, last_move_algo, last_log, stats } = data;

    moveCount = move_number || 0;

    minesEl.textContent = `${mines - flags}`;
    moveNumberEl.textContent = moveCount;

    if (status !== 'ONGOING') {
        btnAgentStep.disabled = true;
        btnAgentAuto.disabled = true;
        statusDot.className = status === 'WON' ? 'pulse-dot active' : 'pulse-dot error';
        statusChip.textContent = status === 'WON' ? 'Success' : 'Failed';
        if (isAutoRunning) toggleAutoRun();
    } else if (!isAutoRunning) {
        btnAgentStep.disabled = false;
        btnAgentAuto.disabled = false;
        statusDot.className = 'pulse-dot';
        statusChip.textContent = 'Standby';
    }

    updatePipeline(last_move_algo);

    boardContainer.innerHTML = '';

    // Calculate maximum available space in the middle panel dynamically
    const availableWidth = window.innerWidth > 960 ? window.innerWidth - 660 : window.innerWidth - 60;
    const availableHeight = window.innerHeight - 280;
    
    // Calculate the perfect cell size to fit the viewport (-1 to account for grid gap)
    let size = Math.floor(Math.min(availableWidth / cols, availableHeight / rows)) - 1;
    // Base bounds for safety
    size = Math.max(14, Math.min(size, 46));
    
    boardContainer.style.gridTemplateColumns = `repeat(${cols}, ${size}px)`;
    boardContainer.style.gridTemplateRows = `repeat(${rows}, ${size}px)`;
    boardContainer.style.setProperty('--cell-size', `${size}px`);

    // Use a DocumentFragment so the 900 cells load instantly at the same time
    const fragment = document.createDocumentFragment();

    for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
            const cellVal = board[r][c];
            const cell = document.createElement('div');
            cell.className = 'cell';

            if (status === 'ONGOING') {
                cell.addEventListener('click', (e) => {
                    humanAction(r, c, 'REVEAL');
                });
                cell.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    humanAction(r, c, 'FLAG');
                });
            }

            if (cellVal === 'H') cell.classList.add('covered');
            else if (cellVal === 'F') cell.classList.add('covered', 'flag');
            else if (cellVal === 'M') cell.classList.add('revealed', 'mine', 'mine-hit');
            else {
                cell.classList.add('revealed');
                if (cellVal > 0) {
                    cell.setAttribute('data-val', cellVal);
                    cell.textContent = cellVal;
                }
            }

            if (status === 'LOST' && mine_map && mine_map[r][c]) {
                if (!cell.classList.contains('flag') && !cell.classList.contains('mine-hit')) {
                    cell.classList.add('revealed', 'mine');
                }
            }
            
            if (status === 'WON' && cellVal === 'H') cell.classList.add('flag');

            if (last_move_cell && last_move_cell[0] === r && last_move_cell[1] === c) {
                cell.classList.add('last-move');
            }

            fragment.appendChild(cell);
        }
    }
    
    boardContainer.appendChild(fragment);

    if (status === 'WON') {
        document.getElementById('overlay-title').textContent = 'Task Completed';
        document.getElementById('overlay-subtitle').textContent = `Target achieved in ${moveCount} cycles.`;
        gameOverlay.classList.remove('hidden');
    } else if (status === 'LOST') {
        document.getElementById('overlay-title').textContent = 'Execution Failed';
        document.getElementById('overlay-subtitle').textContent = `Constraint violated at cycle ${moveCount}.`;
        gameOverlay.classList.remove('hidden');
    }

    if (stats) {
        document.getElementById('count-csp').textContent = stats.algo_counts['CSP'] || 0;
        document.getElementById('count-fc').textContent = stats.algo_counts['Forward Checking'] || 0;
        document.getElementById('count-bt').textContent = stats.algo_counts['Backtracking'] || 0;
        document.getElementById('count-prob').textContent = stats.algo_counts['Probabilistic'] || 0;
        
        const totalAlgos = (stats.algo_counts['CSP'] || 0) + (stats.algo_counts['Forward Checking'] || 0) + (stats.algo_counts['Backtracking'] || 0) + (stats.algo_counts['Probabilistic'] || 0) || 1;
        document.getElementById('bar-csp').style.width = ((stats.algo_counts['CSP'] || 0)/totalAlgos*100) + '%';
        document.getElementById('bar-fc').style.width = ((stats.algo_counts['Forward Checking'] || 0)/totalAlgos*100) + '%';
        document.getElementById('bar-bt').style.width = ((stats.algo_counts['Backtracking'] || 0)/totalAlgos*100) + '%';
        document.getElementById('bar-prob').style.width = ((stats.algo_counts['Probabilistic'] || 0)/totalAlgos*100) + '%';

        document.getElementById('stat-games').textContent = stats.games_played;
        // Backend returns e.g. 50.0 natively, do not multiply by 100 again!
        document.getElementById('stat-winrate').textContent = `${stats.win_rate}%`;
        document.getElementById('stat-total-moves').textContent = stats.total_moves;
    }

    if (last_log) appendLogEntry(last_log);
}

function updatePipeline(algo) {
    clearPipeline();
    if (algo && pipeSteps[algo]) pipeSteps[algo].classList.add('active');
}

function clearPipeline() {
    Object.values(pipeSteps).forEach(el => el.classList.remove('active'));
}

function appendLogEntry(entry) {
    const emptyMsg = logContainer.querySelector('.trace-empty');
    if (emptyMsg) emptyMsg.remove();

    const key = `${entry.row},${entry.col},${entry.action},${moveCount}`;
    if (logContainer.querySelector(`[data-key="${key}"]`)) return;

    const div = document.createElement('div');
    div.className = 'trace-entry';
    div.setAttribute('data-key', key);
    
    div.innerHTML = `
        <div class="trace-header">
            <span>Cycle ${moveCount} &mdash; ${entry.action} [${entry.row}, ${entry.col}]</span>
            <span class="trace-algo">${entry.algorithm || 'Manual'}</span>
        </div>
        <div class="trace-msg">${entry.explanation}</div>
    `;
    logContainer.appendChild(div);
    logContainer.scrollTop = logContainer.scrollHeight;
}

// ---------------------------------------------------------------------- //
// Theme Toggle Logic
// ---------------------------------------------------------------------- //
const themeToggle = document.getElementById('theme-toggle');
const iconSun = document.getElementById('icon-sun');
const iconMoon = document.getElementById('icon-moon');

const currentTheme = localStorage.getItem('theme') || 'dark';
if (currentTheme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
    iconMoon.classList.add('hidden-icon'); 
    iconSun.classList.remove('hidden-icon');
}

themeToggle.addEventListener('click', () => {
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    if (isLight) {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('theme', 'dark');
        iconSun.classList.add('hidden-icon');
        iconMoon.classList.remove('hidden-icon');
    } else {
        document.documentElement.setAttribute('data-theme', 'light');
        localStorage.setItem('theme', 'light');
        iconMoon.classList.add('hidden-icon');
        iconSun.classList.remove('hidden-icon');
    }
});
