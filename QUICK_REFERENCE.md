# Quick Reference Card

## Setup
```powershell
# Set Python path (required for all commands)
$env:PYTHONPATH="src"
```

## Common Commands

### Play a Game
```powershell
# Human vs AI (default)
python -m chess_metrics.cli play-game

# Human vs Human
python -m chess_metrics.cli play-game --white-type human --black-type human

# AI vs AI
python -m chess_metrics.cli play-game --white-type ai --black-type ai

# Custom players
python -m chess_metrics.cli play-game --white "Alice" --black "Bob"

# Stronger AI
python -m chess_metrics.cli play-game --ai-depth 5

# Different AI style
python -m chess_metrics.cli play-game --ai-profile offense-first
```

### Other Commands
```powershell
# Initialize database
python -m chess_metrics.cli migrate

# Show position
python -m chess_metrics.cli show --fen "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# Get legal moves
python -m chess_metrics.cli legal-moves

# Get AI move suggestion
python -m chess_metrics.cli ai-move --depth 4
```

### Run Tests
```powershell
# All tests
python -m unittest discover -s tests -v

# Specific test
cd tests
$env:PYTHONPATH="../src"
python -m unittest test_fen -v

# Demo test
python test_play_game.py
```

## Move Format (UCI)
- Normal: `e2e4`, `g1f3`, `d7d5`
- Castling: `e1g1` (O-O), `e1c1` (O-O-O)
- Promotion: `e7e8q` (=Q), `a7a8n` (=N)

## AI Profiles
- `default` - Balanced
- `offense-first` - Aggressive
- `defense-first` - Defensive
- `board-coverage` - Mobility-focused
- `materialist` - Material-focused

## In-Game Commands
- Enter move: `e2e4`
- Resign: `quit`, `exit`, or `resign`

## Database Queries
```powershell
# View all games
sqlite3 chess.sqlite "SELECT * FROM games;"

# View moves from game 1
sqlite3 chess.sqlite "SELECT ply, san, uci FROM moves WHERE game_id=1;"

# View positions from game 1
sqlite3 chess.sqlite "SELECT ply, fen FROM positions WHERE game_id=1;"

# View players
sqlite3 chess.sqlite "SELECT * FROM players;"
```

## File Structure
```
chess-metrics-engine/
├── src/chess_metrics/     # Main source code
│   ├── engine/            # Chess engine
│   ├── db/                # Database layer
│   └── cli.py             # Command-line interface
├── tests/                 # Unit tests
├── chess.sqlite           # Default database (created on first run)
├── README.md              # Main documentation
├── PLAY_GAME_GUIDE.md     # Detailed play guide
└── QUICK_REFERENCE.md     # This file
```

## Troubleshooting

**Problem**: `ModuleNotFoundError: No module named 'chess_metrics'`  
**Solution**: Set `$env:PYTHONPATH="src"` before running commands

**Problem**: "Invalid move" error  
**Solution**: Use UCI format (e.g., `e2e4` not `e4`)

**Problem**: AI too slow  
**Solution**: Reduce depth with `--ai-depth 2`

**Problem**: Can't see legal moves  
**Solution**: They're displayed when it's your turn (first 10 shown)

## Tips
1. Start with depth 2-3 for faster games
2. Try AI vs AI to watch different strategies
3. All games are saved - check the database!
4. Use `--help` on any command for more options
5. The board shows: UPPERCASE=White, lowercase=Black

