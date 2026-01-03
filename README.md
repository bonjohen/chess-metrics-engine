# Chess Metrics Engine (PV/MV/OV/DV) + SQLite

Implementation:
- Legal move generation (pins/check/castling/ep/promotion)
- Metrics PV/MV/OV/DV (no deduping; multiplicity counts; true-legal required)
- Minimax search depth N plies (default 3) using Score_S convention
- SQLite persistence (games/players/profiles/positions/moves)
- Minimal CLI

## Quick start (Windows PowerShell)
\\\powershell
python -m unittest -v
python -m chess_metrics.cli --help
\\\

## Layout
- \src/chess_metrics/\ engine, metrics, search, db, cli
- \	ests/\ unittest suite
