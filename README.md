# 🤖 Minesweeper AI Agent

A robust, interactive web application featuring an intelligent agent that autonomously plays Minesweeper. Watch the AI solve boards in real-time while it explains every decision it makes. 

Built natively in Python from scratch—without external ML libraries—using classic Artificial Intelligence techniques (CSP, Backtracking, Minimax).

---

## ✨ Features

- **🎮 Interactive Game Board:** A custom-built, premium glassmorphism dark theme UI.
- **🧠 4-Stage AI Pipeline:** The agent employs a cascading decision process to solve the board reliably.
- **📝 Live Reasoning Log:** The AI transparently explains *why* it chose a specific cell (e.g., "Constraint propagation proves this cell is safe").
- **📊 Real-time Statistics:** Tracks win rates, total moves, and the exact count of each algorithm used.
- **⚙️ Auto-Run Mode:** Sit back and watch the AI clear the board automatically with an adjustable speed slider.
- **👆 Human Play:** Step in at any time to reveal or flag cells yourself.

---

## 🔬 How the AI Works

The AI Agent acts in a Perception → Decision → Action loop. At every step, it applies four algorithms in strict order of priority:

1. **CSP & Constraint Propagation** 🎯
   Examines the "frontier" (revealed numbers adjacent to hidden cells) and infers deterministic safe cells and mines based on trivial local constraints.
2. **Forward Checking** ✂️
   When simple constraints stall, it assigns tentative MINE or SAFE labels to the frontier, immediately checking if any adjacency rules are violated to prune dead-end branches early.
3. **Backtracking Search** 🔍
   Conducts an exhaustive search over all valid remaining constraint assignments. If a cell is SAFE in 100% of the valid solutions, the AI clicks it confidently.
4. **Probabilistic Minimax Fallback** 🎲
   If forced to guess, the agent estimates the exact probability of a mine for every unknown cell (using solutions from the Backtracking phase + global mine densities) and picks the historically safest mathematical choice.

---

## 🚀 Running the App Locally

The project includes both a **Streamlit** (recommended) and a legacy **Flask** frontend.

### Prerequisites
Make sure you have Python 3.9+ installed.

```bash
git clone https://github.com/taneesh-8/minesweeper-ai-agent.git
cd minesweeper-ai-agent
pip install -r requirements.txt
```

### Launching with Streamlit (Modern UI)
This is the recommended deployment method. It uses an embedded HTML component for a lightning-fast grid while leveraging Streamlit's native sidebar for controls.

```bash
streamlit run streamlit_app.py
```
*The app will open automatically in your browser at `http://localhost:8501`.*

### Launching with Flask (Legacy UI)
If you prefer the vanilla JS/HTML/CSS implementation served locally:

```bash
python app.py
```
*Open `http://127.0.0.1:5000` in your browser.*

---

## 📂 Project Structure

- `streamlit_app.py` — The main Streamlit entry point.
- `game_engine.py` — Core board logic (cell states, flood-fill reveal, win conditions).
- `agent.py` — The 4-stage intelligent decision logic.
- `reasoning_log.py` — Formatter for tracking the AI's step-by-step thoughts.
- `stats_tracker.py` — Aggregates win/loss rates and algorithm usage metrics.
- `/templates` & `/static` — Frontend assets for the Flask version.

---

## 🌐 Deploying to Streamlit Community Cloud

This project is perfectly structured for free deployment on Streamlit Cloud.
1. Push this code to a public GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Connect your repository.
4. Set the **Main file path** to `streamlit_app.py`.
5. Click **Deploy!**
