# Chess Metrics Engine (PV/MV/OV/DV) + SQLite

Implementation:
- Legal move generation (pins/check/castling/ep/promotion)
- Metrics PV/MV/OV/DV (no deduping; multiplicity counts; true-legal required)
- **Square root DV** - Defense values use sqrt(piece_value) for realistic scaling
- Minimax search depth N plies (default 3) using Score_S convention
- SQLite persistence (games/players/profiles/positions/moves)
- Interactive game play with database storage
- **Variance system** (0.75-1.25 random factor on move evaluations)
- Decimal metrics support for precise evaluation
- Minimal CLI

## Quick start (Windows PowerShell)

### Run Tests
```powershell
$env:PYTHONPATH="src"
python -m unittest discover -s tests -v
```

### Play a Game
```powershell
$env:PYTHONPATH="src"
python -m chess_metrics.cli play-game
```

This starts an interactive game (Human vs AI by default) that saves all moves to the database.

**Features:**
- Real-time board display
- Complete move analysis with metrics for every legal move
- Shows PV (material), MV (mobility), OV (offense), DV (defense) for both players
- **Sum column** displays total of all deltas (dPV + dMV + dOV + dDV)
- **Moves sorted by Sum** (descending) for better overall evaluation
- **Variance system** adds randomness (0.75-1.25x) to move evaluations
- Decimal precision for metrics (e.g., dPV=+9.5 instead of +10)

**Documentation:**
- [PLAY_GAME_GUIDE.md](PLAY_GAME_GUIDE.md) - How to play games
- [METRICS_EXPLAINED.md](METRICS_EXPLAINED.md) - Understanding metrics
- [DATABASE_GUIDE.md](DATABASE_GUIDE.md) - Database queries and analysis
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Command reference

**Features:**
- [SQRT_DV_FEATURE.md](SQRT_DV_FEATURE.md) - Square root defense values
- [VARIANCE_FEATURE.md](VARIANCE_FEATURE.md) - Variance system
- [SUM_COLUMN_FEATURE.md](SUM_COLUMN_FEATURE.md) - Sum column and sorting

### Other Commands
```powershell
$env:PYTHONPATH="src"
python -m chess_metrics.cli --help
python -m chess_metrics.cli migrate          # Initialize database
python -m chess_metrics.cli show --fen "..."  # Display position
python -m chess_metrics.cli legal-moves       # Show legal moves
python -m chess_metrics.cli ai-move           # Get AI move suggestion
```

## Layout
- `src/chess_metrics/` - engine, metrics, search, db, cli
- `tests/` - unittest suite
