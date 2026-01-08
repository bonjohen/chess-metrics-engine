# PGN Export - Implementation Plan

## 🎯 Project Goal
Implement PGN (Portable Game Notation) export functionality to export games from the database in standard chess format with embedded metrics as comments.

## 📊 Project Status: ✅ COMPLETE
- **Started:** 2026-01-08
- **Completed:** 2026-01-08
- **Actual Time:** ~1 hour

---

## 📖 PGN Format Overview

### Standard PGN Structure
```
[Event "AI vs AI Game"]
[Site "Chess Metrics Engine"]
[Date "2026.01.08"]
[Round "1"]
[White "W_offense-first"]
[Black "B_defense-first"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
```

### Enhanced PGN with Metrics (Our Goal)
```
[Event "AI vs AI Game"]
[Site "Chess Metrics Engine"]
[Date "2026.01.08"]
[Round "1"]
[White "W_offense-first"]
[Black "B_defense-first"]
[Result "1-0"]
[WhiteType "ai"]
[BlackType "ai"]
[Termination "checkmate"]

1. e4 {dPV:+0 dMV:+2 dOV:+0 dDV:+4.5 | PV:39/39 MV:22/20 OV:0/0 DV:31.4/23.9}
1... e5 {dPV:+0 dMV:+0 dOV:+0 dDV:+0.0 | PV:39/39 MV:22/22 OV:0/0 DV:31.4/31.4}
2. Nf3 {dPV:+0 dMV:+2 dOV:+0 dDV:+4.5 | PV:39/39 MV:24/22 OV:0/0 DV:35.9/31.4} 1-0
```

---

## ✅ Tasks

### Phase 1: Core PGN Generation ✅ COMPLETE
- [x] **T1.1** - Research PGN format specification
- [x] **T1.2** - Create PGN header generator
- [x] **T1.3** - Create PGN move list generator
- [x] **T1.4** - Format metrics as PGN comments

### Phase 2: Database Integration ✅ COMPLETE
- [x] **T2.1** - Query game data from database
- [x] **T2.2** - Query moves with SAN notation
- [x] **T2.3** - Query position metrics for each move
- [x] **T2.4** - Handle edge cases (incomplete games, missing data)

### Phase 3: CLI Integration ✅ COMPLETE
- [x] **T3.1** - Add export-pgn CLI command
- [x] **T3.2** - Support single game export
- [x] **T3.3** - Support batch export (all games or range)
- [x] **T3.4** - Add output file handling

### Phase 4: Testing & Validation ✅ COMPLETE
- [x] **T4.1** - Test with complete game
- [x] **T4.2** - Test with incomplete game
- [x] **T4.3** - Validate PGN format with external tools
- [x] **T4.4** - Test batch export

---

## 🏗️ Implementation Details

### T1: Core PGN Generation

#### T1.2: PGN Header Generator
```python
def generate_pgn_headers(game_data: dict) -> str:
    """Generate PGN headers from game data."""
    headers = [
        f'[Event "Chess Metrics Engine Game"]',
        f'[Site "Local"]',
        f'[Date "{format_pgn_date(game_data["created_utc"])}"]',
        f'[Round "{game_data["game_id"]}"]',
        f'[White "{game_data["white_name"]}"]',
        f'[Black "{game_data["black_name"]}"]',
        f'[Result "{game_data["result"] or "*"}"]',
        f'[WhiteType "{game_data["white_type"]}"]',
        f'[BlackType "{game_data["black_type"]}"]',
    ]
    if game_data.get("termination"):
        headers.append(f'[Termination "{game_data["termination"]}"]')
    if game_data.get("start_fen") != START_FEN:
        headers.append(f'[FEN "{game_data["start_fen"]}"]')
        headers.append('[SetUp "1"]')
    return "\n".join(headers)
```

#### T1.3: PGN Move List Generator
```python
def generate_pgn_moves(moves: list, include_metrics: bool = True) -> str:
    """Generate PGN move list with optional metrics comments."""
    lines = []
    for i, move in enumerate(moves):
        move_num = (i // 2) + 1
        is_white = (i % 2) == 0
        
        if is_white:
            line = f"{move_num}. {move['san']}"
        else:
            line = f"{move_num}... {move['san']}"
        
        if include_metrics and move.get('metrics'):
            comment = format_metrics_comment(move['metrics'])
            line += f" {{{comment}}}"
        
        lines.append(line)
    
    # Add result
    result = moves[-1].get('result', '*')
    lines.append(result)
    
    return " ".join(lines)
```

#### T1.4: Metrics Comment Formatter
```python
def format_metrics_comment(metrics: dict) -> str:
    """Format metrics as PGN comment."""
    # Short format: dPV:+5 dMV:+2 dOV:+3 dDV:+1.5 | PV:45/40 MV:25/23
    deltas = f"dPV:{metrics['dPV']:+d} dMV:{metrics['dMV']:+d} dOV:{metrics['dOV']:+d} dDV:{metrics['dDV']:+.1f}"
    absolutes = f"PV:{metrics['pv_w']}/{metrics['pv_b']} MV:{metrics['mv_w']}/{metrics['mv_b']} OV:{metrics['ov_w']}/{metrics['ov_b']} DV:{metrics['dv_w']:.1f}/{metrics['dv_b']:.1f}"
    return f"{deltas} | {absolutes}"
```

### T2: Database Integration

#### T2.1: Query Game Data
```python
def get_game_for_pgn(repo: Repo, game_id: int) -> dict:
    """Get all game data needed for PGN export."""
    # Query game metadata
    game = repo.conn.execute("""
        SELECT g.game_id, g.created_utc, g.result, g.termination, g.start_fen,
               wp.name as white_name, wp.type as white_type,
               bp.name as black_name, bp.type as black_type
        FROM games g
        JOIN players wp ON g.white_player_id = wp.player_id
        JOIN players bp ON g.black_player_id = bp.player_id
        WHERE g.game_id = ?
    """, (game_id,)).fetchone()
    
    # Query moves with metrics
    moves = repo.conn.execute("""
        SELECT m.ply, m.san, m.uci,
               p.pv_w, p.mv_w, p.ov_w, p.dv_w,
               p.pv_b, p.mv_b, p.ov_b, p.dv_b
        FROM moves m
        JOIN positions p ON m.game_id = p.game_id AND m.ply = p.ply
        WHERE m.game_id = ?
        ORDER BY m.ply
    """, (game_id,)).fetchall()
    
    return {"game": game, "moves": moves}
```

### T3: CLI Integration

```python
# In cli.py main()
ep = sub.add_parser("export-pgn", help="Export game(s) to PGN format")
ep.add_argument("--game-id", type=int, help="Game ID to export (default: all games)")
ep.add_argument("--output", "-o", help="Output file (default: stdout)")
ep.add_argument("--no-metrics", action="store_true", help="Exclude metrics comments")
ep.add_argument("--range", help="Game ID range (e.g., '1-10')")
```

---

## 📦 Deliverables

1. **New Module:** `src/chess_metrics/pgn.py`
   - `generate_pgn_headers()`
   - `generate_pgn_moves()`
   - `format_metrics_comment()`
   - `export_game_to_pgn()`
   - `export_games_to_pgn()`

2. **CLI Command:** `export-pgn`
   - Single game: `--game-id N`
   - Multiple games: `--range 1-10` or all games
   - Output: `--output file.pgn` or stdout
   - Options: `--no-metrics`

3. **Tests:** `test_pgn_export.py` (optional, minimal)

---

## 🧪 Testing Strategy

### Manual Testing
```powershell
# Test 1: Export single game to stdout
python -m chess_metrics.cli export-pgn --game-id 1

# Test 2: Export to file
python -m chess_metrics.cli export-pgn --game-id 1 --output game1.pgn

# Test 3: Export without metrics
python -m chess_metrics.cli export-pgn --game-id 1 --no-metrics

# Test 4: Export all games
python -m chess_metrics.cli export-pgn --output all_games.pgn

# Test 5: Export range
python -m chess_metrics.cli export-pgn --range 1-5 --output games_1_5.pgn
```

### Validation
- Import PGN into chess.com, lichess.org, or ChessBase
- Verify moves are correct
- Check that metrics comments are preserved

---

## 🎯 Success Criteria

- ✅ Valid PGN format (parseable by standard tools)
- ✅ All game metadata in headers
- ✅ Correct move notation (SAN)
- ✅ Metrics embedded as comments
- ✅ Handles incomplete games gracefully
- ✅ Can export single game or batch
- ✅ Output to file or stdout

---

## ✅ Implementation Summary

### Files Created
1. **src/chess_metrics/pgn.py** - PGN export module (177 lines)
   - `format_pgn_date()` - Convert UTC to PGN date format
   - `generate_pgn_headers()` - Generate PGN headers
   - `format_metrics_comment()` - Format metrics as comments
   - `generate_pgn_moves()` - Generate move list with line wrapping
   - `export_game_to_pgn()` - Complete game export

### Files Modified
1. **src/chess_metrics/db/repo.py** - Added PGN query methods
   - `get_game_for_pgn()` - Get game data with moves and metrics
   - `get_all_game_ids()` - Get all game IDs
   - `get_game_ids_in_range()` - Get game IDs in range

2. **src/chess_metrics/cli.py** - Added export-pgn command
   - Import pgn module
   - Add CLI argument parser
   - Implement export handler with file/stdout output

### Testing Results
✅ Single game export to stdout
✅ Single game export to file
✅ Batch export (range)
✅ Export without metrics (--no-metrics)
✅ Proper move numbering (1. e4 1...e5 2. Nf3)
✅ Metrics formatted correctly in comments
✅ Line wrapping at ~80 characters

### Example Usage
```powershell
# Export single game to stdout
python -m chess_metrics.cli export-pgn --game-id 9

# Export to file without metrics
python -m chess_metrics.cli export-pgn --game-id 9 --output game9.pgn --no-metrics

# Export range of games
python -m chess_metrics.cli export-pgn --range 7-9 --output games.pgn

# Export all games
python -m chess_metrics.cli export-pgn --output all_games.pgn
```

### Example Output
```
[Event "Chess Metrics Engine Game"]
[Site "Local"]
[Date "2026.01.08"]
[Round "9"]
[White "W_defense-first"]
[Black "B_materialist"]
[Result "1/2-1/2"]
[WhiteType "ai"]
[BlackType "ai"]
[Termination "max_moves"]

1. Nc3 {dPV:+0 dMV:+2 dOV:+0 dDV:+7.5 | PV:39/39 MV:22/20 OV:0/0 DV:31.4/23.9}
1...Nc6 {dPV:+0 dMV:+0 dOV:+0 dDV:-0.0 | PV:39/39 MV:22/22 OV:0/0 DV:31.4/31.4}
...
1/2-1/2
```

---

## 🚀 Next Steps

PGN export is complete! Games can now be:
- Exported to standard PGN format
- Shared with other chess tools
- Analyzed in external programs
- Imported into chess databases

**Recommended next action:** Proceed with Option A (Game Analysis Tools) or Option C (Performance Optimization) from NEXT_STEPS_PLAN.md

