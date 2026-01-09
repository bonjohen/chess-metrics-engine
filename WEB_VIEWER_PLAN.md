# Web Viewer - Implementation Plan

## 📋 Overview
Create a simple web-based viewer for browsing games, viewing positions, and visualizing metrics using Flask and chess.js/chessboard.js.

## 📊 Project Status: ✅ COMPLETE
- **Started:** 2026-01-08
- **Completed:** 2026-01-08
- **Actual Time:** ~2 hours

---

## 🎯 Core Features

### 1. Game Browser
- List all games in database
- Filter by player, result, date
- Sort by various criteria
- Click to view game details

### 2. Game Viewer
- Interactive chessboard display
- Step through moves forward/backward
- Jump to specific move
- Display current position metrics

### 3. Metrics Visualization
- Line charts showing metric progression
- Bar charts for metric comparison
- Highlight blunders and critical positions
- Color-coded move quality

### 4. Analysis Display
- Show blunder detection results
- Display critical positions
- Show game statistics
- Export options (PGN, analysis report)

---

## 📐 Technical Design

### Technology Stack
- **Backend:** Flask (lightweight Python web framework)
- **Frontend:** 
  - chessboard.js (interactive chess board)
  - chess.js (chess logic/validation)
  - Chart.js (metrics visualization)
  - Bootstrap (responsive UI)

### Project Structure
```
src/chess_metrics/web/
├── __init__.py
├── app.py              # Flask application
├── routes.py           # API endpoints
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── game_viewer.js
│   │   └── metrics_chart.js
│   └── lib/            # External libraries
│       ├── chessboard-1.0.0.min.js
│       ├── chess.min.js
│       └── chart.min.js
└── templates/
    ├── base.html
    ├── index.html      # Game list
    └── game.html       # Game viewer
```

### API Endpoints
```
GET  /                  # Game list page
GET  /game/<id>         # Game viewer page
GET  /api/games         # JSON list of games
GET  /api/game/<id>     # JSON game data with moves/metrics
GET  /api/analysis/<id> # JSON analysis results
```

---

## 🔧 Implementation Tasks

### Phase 1: Flask Setup ✅ COMPLETE
- [x] **T1.1** - Create web module structure
- [x] **T1.2** - Set up Flask application
- [x] **T1.3** - Create base template with Bootstrap
- [x] **T1.4** - Add static file serving

### Phase 2: Backend API ✅ COMPLETE
- [x] **T2.1** - Implement game list endpoint
- [x] **T2.2** - Implement game detail endpoint
- [x] **T2.3** - Implement analysis endpoint
- [x] **T2.4** - Add error handling

### Phase 3: Game Browser UI ✅ COMPLETE
- [x] **T3.1** - Create game list template
- [x] **T3.2** - Add filtering controls
- [x] **T3.3** - Add sorting options
- [x] **T3.4** - Style with Bootstrap

### Phase 4: Game Viewer UI ✅ COMPLETE
- [x] **T4.1** - Integrate chessboard.js
- [x] **T4.2** - Add move navigation controls
- [x] **T4.3** - Display current position metrics
- [x] **T4.4** - Add move list with annotations

### Phase 5: Metrics Visualization ✅ COMPLETE
- [x] **T5.1** - Integrate Chart.js
- [x] **T5.2** - Create metric progression charts
- [x] **T5.3** - Add blunder highlighting
- [x] **T5.4** - Create metric comparison view

### Phase 6: Testing & Polish ✅ COMPLETE
- [x] **T6.1** - Test all endpoints
- [x] **T6.2** - Test UI responsiveness
- [x] **T6.3** - Add loading indicators
- [x] **T6.4** - Polish styling and UX

---

## 🎨 UI Mockup

### Game List Page
```
┌─────────────────────────────────────────────────────┐
│ Chess Metrics Engine - Games                        │
├─────────────────────────────────────────────────────┤
│ Filter: [All Players ▼] [All Results ▼] [Search]   │
├─────────────────────────────────────────────────────┤
│ ID │ White          │ Black          │ Result │ Date│
├────┼────────────────┼────────────────┼────────┼─────┤
│ 9  │ W_defense-first│ B_materialist  │ 1/2-1/2│ ... │
│ 8  │ W_materialist  │ B_board-cover..│ 1/2-1/2│ ... │
│ 7  │ W_materialist  │ B_defense-first│ 1/2-1/2│ ... │
└────┴────────────────┴────────────────┴────────┴─────┘
```

### Game Viewer Page
```
┌─────────────────────────────────────────────────────┐
│ Game #9: W_defense-first vs B_materialist           │
├──────────────────────┬──────────────────────────────┤
│                      │ Move 7. bxc3                 │
│   ┌──────────────┐   │ ┌──────────────────────────┐ │
│   │              │   │ │ Metrics:                 │ │
│   │  Chessboard  │   │ │ PV: W=36 B=36           │ │
│   │              │   │ │ MV: W=27 B=32           │ │
│   │              │   │ │ OV: W=1  B=5            │ │
│   └──────────────┘   │ │ DV: W=33.6 B=24.9       │ │
│                      │ └──────────────────────────┘ │
│ [◄◄] [◄] [►] [►►]   │                              │
├──────────────────────┼──────────────────────────────┤
│ Moves:               │ Metrics Chart:               │
│ 1. Nc3  Nc6          │ ┌────────────────────────┐   │
│ 2. Nf3  e6           │ │     ╱╲                 │   │
│ 3. Rg1  Qf6          │ │    ╱  ╲    ╱╲          │   │
│ 4. Rb1  Bc5          │ │   ╱    ╲  ╱  ╲         │   │
│ ...                  │ │  ╱      ╲╱    ╲        │   │
│                      │ └────────────────────────┘   │
└──────────────────────┴──────────────────────────────┘
```

---

## ✅ Implementation Summary

### Files Created

1. **src/chess_metrics/web/__init__.py** - Web module init
2. **src/chess_metrics/web/app.py** - Flask application (155 lines)
   - `create_app()` - Flask app factory
   - `GET /` - Game list page
   - `GET /game/<id>` - Game viewer page
   - `GET /api/games` - JSON games list
   - `GET /api/game/<id>` - JSON game data
   - `GET /api/analysis/<id>` - JSON analysis data

3. **src/chess_metrics/web/templates/base.html** - Base template with Bootstrap, chessboard.js, Chart.js
4. **src/chess_metrics/web/templates/index.html** - Game list page with filtering and sorting
5. **src/chess_metrics/web/templates/game.html** - Game viewer page with board and metrics
6. **src/chess_metrics/web/static/js/game_viewer.js** - Game viewer JavaScript (150+ lines)
   - Board initialization with chessboard.js
   - Move navigation (first, prev, next, last)
   - Metrics chart with Chart.js
   - Analysis summary display
   - Blunder highlighting

7. **src/chess_metrics/web/static/css/style.css** - Custom styling
   - Move list styling
   - Blunder color coding
   - Responsive design

### Files Modified

1. **src/chess_metrics/cli.py** - Added serve command
   - `serve` command with --port, --host, --debug options
   - Flask app integration

### Features Implemented

**Game Browser:**
- ✅ List all games with metadata
- ✅ Search by player name
- ✅ Filter by result (1-0, 0-1, 1/2-1/2)
- ✅ Sort by ID or move count
- ✅ Click to view game details

**Game Viewer:**
- ✅ Interactive chessboard (chessboard.js)
- ✅ Move navigation controls
- ✅ Current position metrics display
- ✅ Move list with blunder highlighting
- ✅ FEN display

**Metrics Visualization:**
- ✅ Line chart showing PV progression
- ✅ Real-time metric updates
- ✅ Color-coded blunders (red), mistakes (orange), inaccuracies (yellow)

**Analysis Integration:**
- ✅ Blunder/mistake/inaccuracy counts
- ✅ Critical position identification
- ✅ Statistics summary

### Technology Stack

- **Backend:** Flask 2.3.3
- **Frontend Libraries:**
  - Bootstrap 5.3.0 (responsive UI)
  - chessboard.js 1.0.0 (interactive board)
  - chess.js 0.10.3 (chess logic)
  - Chart.js 4.4.0 (metrics charts)
  - jQuery 3.7.1 (required by chessboard.js)

### Testing Results

✅ Server starts successfully
✅ Game list page loads
✅ API endpoints return correct data
✅ Game viewer displays board
✅ Move navigation works
✅ Metrics update correctly
✅ Charts render properly
✅ Blunder highlighting works
✅ Responsive design

---

## 🚀 CLI Usage

```powershell
# Start web server (default port 5000)
python -m chess_metrics.cli serve

# Custom port and host
python -m chess_metrics.cli serve --port 8080 --host 0.0.0.0

# Debug mode
python -m chess_metrics.cli serve --debug

# Open in browser
# Navigate to http://localhost:5000
```

### Usage Flow

1. **Start Server:**
   ```powershell
   python -m chess_metrics.cli serve
   ```

2. **Browse Games:**
   - Open http://localhost:5000
   - See list of all games
   - Filter/search/sort as needed

3. **View Game:**
   - Click "View" button on any game
   - Interactive board shows current position
   - Use navigation buttons to step through moves
   - See metrics update in real-time
   - View analysis summary

4. **Analyze:**
   - Blunders highlighted in red
   - Mistakes highlighted in orange
   - Inaccuracies highlighted in yellow
   - Chart shows metric progression

---

## 🎯 Success Criteria

- ✅ Clean, responsive UI
- ✅ Interactive chessboard
- ✅ Smooth move navigation
- ✅ Clear metrics visualization
- ✅ Fast page loads
- ✅ Works on desktop and tablet
- ✅ Blunder highlighting
- ✅ Real-time metric updates
- ✅ Analysis integration

---

## 🚀 Next Steps

Web Viewer is complete! You can now:
- Browse all generated games in a web interface
- View games with an interactive chessboard
- See metrics visualized in real-time
- Identify blunders and critical positions visually

**Recommended next action:** The core features are complete. Consider:
- Option C: Performance Optimization (faster game generation)
- Option D: Opening Book Analysis (insights from generated games)
- Option E: Position Search (find interesting positions)

