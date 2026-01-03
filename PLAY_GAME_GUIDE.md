# Play Game Guide

## Overview
The `play-game` command allows you to play interactive chess games that are automatically saved to the database with full move history and metrics.

## Usage

### Basic Command
```powershell
$env:PYTHONPATH="src"
python -m chess_metrics.cli play-game
```

This starts a game with default settings:
- White: Human player named "White"
- Black: AI player named "Black"
- AI uses default profile with depth 3

### Options

```powershell
python -m chess_metrics.cli play-game [OPTIONS]
```

**Available Options:**
- `--white NAME` - Name for white player (default: "White")
- `--black NAME` - Name for black player (default: "Black")
- `--white-type {human,ai}` - White player type (default: human)
- `--black-type {human,ai}` - Black player type (default: ai)
- `--ai-depth N` - AI search depth (default: 3)
- `--ai-profile PROFILE` - AI playing style (default: "default")
- `--start-fen FEN` - Starting position (default: standard starting position)
- `--db PATH` - Database file path (default: chess.sqlite)

### AI Profiles

Available AI profiles:
- `default` - Balanced play (equal weights)
- `offense-first` - Aggressive, prioritizes offensive value
- `defense-first` - Defensive, prioritizes defensive value
- `board-coverage` - Emphasizes mobility
- `materialist` - Prioritizes piece value

## Examples

### 1. Human vs AI (default)
```powershell
$env:PYTHONPATH="src"
python -m chess_metrics.cli play-game
```

### 2. Human vs Human
```powershell
$env:PYTHONPATH="src"
python -m chess_metrics.cli play-game --white-type human --black-type human
```

### 3. AI vs AI
```powershell
$env:PYTHONPATH="src"
python -m chess_metrics.cli play-game --white-type ai --black-type ai
```

### 4. Custom Players with Different AI Styles
```powershell
$env:PYTHONPATH="src"
python -m chess_metrics.cli play-game `
  --white "Aggressive AI" --white-type ai --ai-profile offense-first `
  --black "Defensive AI" --black-type ai --ai-profile defense-first
```

### 5. Stronger AI (deeper search)
```powershell
$env:PYTHONPATH="src"
python -m chess_metrics.cli play-game --ai-depth 5
```

## Playing the Game

### For Human Players
When it's your turn:
1. The board is displayed (White pieces: UPPERCASE, Black pieces: lowercase)
2. **All legal moves are shown with detailed metrics:**
   - Move number and UCI notation
   - SAN (Standard Algebraic Notation)
   - Delta metrics (dPV, dMV, dOV, dDV) - advantage after the move
   - Absolute metrics for both White and Black
3. Moves are sorted by material advantage (dPV) to help you choose
4. Enter your move in UCI format (e.g., `e2e4`, `g1f3`, `e7e8q` for promotion)
5. Type `quit`, `exit`, or `resign` to resign the game

### Move Format (UCI)
- Normal move: `e2e4` (from square to square)
- Castling: `e1g1` (king-side) or `e1c1` (queen-side)
- Promotion: `e7e8q` (pawn to e8, promote to queen)

### Game Display
Each turn shows:
- Current board position (8x8 grid)
- Current position metrics (PV, MV, OV, DV deltas)
- **Complete move analysis table** showing:
  - All legal moves with UCI and SAN notation
  - Delta metrics for each move (how the position changes)
  - Absolute metrics for White and Black after each move
  - Moves sorted by advantage (best moves first)
- Whose turn it is

### Game End
The game ends when:
- Checkmate occurs
- Stalemate occurs
- 50-move rule is reached
- A player resigns

## Database Storage

All games are saved to the database with:
- Player information
- Complete move history (UCI and SAN notation)
- Position after each move (FEN)
- Metrics for each position (PV, MV, OV, DV)
- Game result and termination reason

### Viewing Saved Games

You can query the database to see game history:

```powershell
sqlite3 chess.sqlite "SELECT * FROM games;"
sqlite3 chess.sqlite "SELECT ply, san, uci FROM moves WHERE game_id=1;"
```

## Tips

1. **Start Simple**: Begin with human vs AI to learn the interface
2. **Watch AI vs AI**: Great for testing and seeing different strategies
3. **Experiment with Profiles**: Try different AI profiles to see varied play styles
4. **Adjust Depth**: Higher depth = stronger AI but slower moves
5. **Save Your Database**: The `chess.sqlite` file contains all your games

## Troubleshooting

**"Invalid move" error**: Make sure you're using UCI format (e.g., `e2e4` not `e4`)

**AI takes too long**: Reduce `--ai-depth` (try 2 or 3)

**Can't find module**: Make sure to set `$env:PYTHONPATH="src"` before running

## Example Session

```
Game created with ID: 1
White (White): human
Black (Black): ai

r n b q k b n r
p p p p p p p p
. . . . . . . .
. . . . . . . .
. . . . . . . .
. . . . . . . .
P P P P P P P P
R N B Q K B N R

Metrics: PV=+0 MV=+0 OV=+0 DV=+0

White (White) - Legal Moves with Metrics:
================================================================================
#    Move     SAN        dPV   dMV   dOV   dDV |  PVw  MVw  OVw  DVw  PVb  MVb  OVb  DVb
--------------------------------------------------------------------------------
1    b1c3     Nc3         +0    +2    +0   +16 |   39   22    0   51   39   20    0   35
2    g1f3     Nf3         +0    +2    +0    +7 |   39   22    0   42   39   20    0   35
3    d2d3     d3          +0    +7    +0    -1 |   39   27    0   34   39   20    0   35
4    e2e4     e4          +0   +10    +0    -4 |   39   30    0   31   39   20    0   35
...
================================================================================
Total: 20 legal moves

Metrics Legend:
  dPV/dMV/dOV/dDV = Delta (White - Black) for Piece Value / Mobility / Offensive / Defensive
  PVw/MVw/OVw/DVw = White's absolute metrics
  PVb/MVb/OVb/DVb = Black's absolute metrics

White, enter your move (UCI format, e.g., e2e4) or 'quit': e2e4
Move 1: e4

...
```

