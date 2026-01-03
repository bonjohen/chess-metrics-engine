# Database Guide

Complete guide to querying and analyzing chess game data stored in `chess.sqlite`.

---

## 🚀 Quick Start

### Using the Query Script (Easiest!)

```powershell
# Show all games and latest game details
python query_database.py

# Show specific game details
python query_database.py 1
```

### Using sqlite3 Command Line

```powershell
# List all games
sqlite3 -column -header chess.sqlite "SELECT * FROM games;"

# Show moves from game 1
sqlite3 -column -header chess.sqlite "SELECT ply, san, uci FROM moves WHERE game_id=1;"

# Show metrics from game 1
sqlite3 -column -header chess.sqlite "SELECT ply, last_move_san, dPV, dMV, dOV, dDV FROM v_position_deltas WHERE game_id=1;"
```

---

## 📊 Database Schema

### Tables

**`games`** - Game records
- `game_id` - Unique identifier
- `created_utc` - Timestamp
- `white_player_id`, `black_player_id` - Player IDs (FK to players)
- `result` - Game result ("1-0", "0-1", "1/2-1/2", NULL)
- `termination` - How game ended ("checkmate", "resignation", "stalemate", etc.)
- `start_fen` - Starting position

**`players`** - Player information
- `player_id` - Unique identifier
- `name` - Player name
- `type` - 'human' or 'ai'
- `profile_id` - AI profile (FK to profiles, NULL for humans)

**`profiles`** - AI playing styles
- `profile_id` - Unique identifier
- `name` - Profile name ("default", "offense-first", etc.)
- `wPV`, `wMV`, `wOV`, `wDV` - Metric weights
- `notes` - Description

**`positions`** - Board positions after each move
- `position_id` - Unique identifier
- `game_id` - Game ID (FK to games)
- `ply` - Move number (half-move, starts at 0)
- `side_to_move` - 'W' or 'B'
- `fen` - Position in FEN notation
- `last_move_uci`, `last_move_san` - Last move
- `pv_w`, `mv_w`, `ov_w`, `dv_w` - White's metrics
- `pv_b`, `mv_b`, `ov_b`, `dv_b` - Black's metrics

**`moves`** - Move details
- `move_id` - Unique identifier
- `game_id` - Game ID (FK to games)
- `ply` - Move number
- `uci` - UCI format (e.g., "e2e4")
- `san` - SAN format (e.g., "e4")
- `from_sq`, `to_sq` - Squares
- `is_capture`, `is_ep`, `is_castle`, `is_promotion` - Boolean flags
- `promotion_piece` - Piece if promoted
- `variance_factor` - Variance applied (0.75-1.25)

### Views

**`v_position_deltas`** - Positions with auto-calculated deltas
- All position columns plus:
- `dPV`, `dMV`, `dOV`, `dDV` - Calculated as (White - Black)

**`v_position_deltas_with_prev`** - Includes previous position deltas
- All v_position_deltas columns plus:
- `prev_dPV`, `prev_dMV`, `prev_dOV`, `prev_dDV`

---

## 📋 Common Queries

### Game Information

```sql
-- List all games with players
SELECT 
  g.game_id,
  g.created_utc,
  wp.name AS white,
  bp.name AS black,
  g.result,
  g.termination
FROM games g
JOIN players wp ON g.white_player_id = wp.player_id
JOIN players bp ON g.black_player_id = bp.player_id
ORDER BY g.created_utc DESC;

-- Count total games
SELECT COUNT(*) FROM games;

-- Find games by player
SELECT g.game_id, g.result
FROM games g
JOIN players p ON p.player_id IN (g.white_player_id, g.black_player_id)
WHERE p.name = 'White';
```

### Move History

```sql
-- All moves in a game
SELECT ply, san, uci, variance_factor
FROM moves
WHERE game_id = 1
ORDER BY ply;

-- Find captures
SELECT ply, san, uci
FROM moves
WHERE game_id = 1 AND is_capture = 1;

-- Find castling moves
SELECT ply, san, uci
FROM moves
WHERE game_id = 1 AND is_castle = 1;

-- Count moves by type
SELECT 
  COUNT(*) AS total,
  SUM(is_capture) AS captures,
  SUM(is_castle) AS castles,
  SUM(is_promotion) AS promotions
FROM moves
WHERE game_id = 1;
```

### Metrics Analysis

```sql
-- Game metrics with deltas (using view - easiest!)
SELECT ply, last_move_san, dPV, dMV, dOV, dDV
FROM v_position_deltas
WHERE game_id = 1
ORDER BY ply;

-- Full metrics
SELECT 
  ply, last_move_san,
  pv_w, mv_w, ov_w, dv_w,
  pv_b, mv_b, ov_b, dv_b,
  dPV, dMV, dOV, dDV
FROM v_position_deltas
WHERE game_id = 1
ORDER BY ply;

-- Find positions where material changed
SELECT ply, last_move_san, dPV
FROM v_position_deltas
WHERE game_id = 1 AND dPV != 0;

-- Average metrics
SELECT 
  AVG(dPV) AS avg_material,
  AVG(dMV) AS avg_mobility,
  AVG(dOV) AS avg_offensive,
  AVG(dDV) AS avg_defensive
FROM v_position_deltas
WHERE game_id = 1;
```

---

## 🔍 Advanced Queries

### Defense Value Analysis (sqrt DV)

```sql
-- Track defense values over time
SELECT ply, last_move_san, dv_w, dv_b, (dv_w - dv_b) AS dDV
FROM positions
WHERE game_id = 1
ORDER BY ply;

-- Find positions with highest defense
SELECT ply, last_move_san, dv_w, dv_b
FROM positions
WHERE game_id = 1
ORDER BY (dv_w + dv_b) DESC
LIMIT 5;
```

### Critical Moments (Large Metric Swings)

```sql
SELECT
  cur.ply,
  cur.last_move_san,
  cur.dPV,
  prev.dPV AS prev_dPV,
  (cur.dPV - prev.dPV) AS dPV_change
FROM v_position_deltas cur
LEFT JOIN v_position_deltas prev
  ON cur.game_id = prev.game_id AND cur.ply = prev.ply + 1
WHERE cur.game_id = 1
  AND ABS(cur.dPV - COALESCE(prev.dPV, 0)) > 2
ORDER BY cur.ply;
```

### Variance Analysis

```sql
SELECT
  AVG(variance_factor) AS avg_variance,
  MIN(variance_factor) AS min_variance,
  MAX(variance_factor) AS max_variance,
  COUNT(*) AS total_moves
FROM moves
WHERE game_id = 1 AND variance_factor IS NOT NULL;
```

### Player Statistics

```sql
SELECT
  p.name,
  p.type,
  COUNT(DISTINCT g.game_id) AS games_played,
  SUM(CASE WHEN g.result = '1-0' AND g.white_player_id = p.player_id THEN 1
           WHEN g.result = '0-1' AND g.black_player_id = p.player_id THEN 1
           ELSE 0 END) AS wins,
  SUM(CASE WHEN g.result = '1/2-1/2' THEN 1 ELSE 0 END) AS draws
FROM players p
LEFT JOIN games g ON p.player_id = g.white_player_id OR p.player_id = g.black_player_id
GROUP BY p.player_id;
```

### Most Common Opening Moves

```sql
SELECT
  san,
  COUNT(*) AS frequency
FROM moves
WHERE ply = 1
GROUP BY san
ORDER BY frequency DESC;
```

---

## 🐍 Python Examples

### Basic Query

```python
import sqlite3

conn = sqlite3.connect('chess.sqlite')
cursor = conn.cursor()

# Get all games
cursor.execute("""
    SELECT g.game_id, wp.name AS white, bp.name AS black, g.result
    FROM games g
    JOIN players wp ON g.white_player_id = wp.player_id
    JOIN players bp ON g.black_player_id = bp.player_id
""")

for row in cursor.fetchall():
    print(f"Game {row[0]}: {row[1]} vs {row[2]} - Result: {row[3]}")

conn.close()
```

### Using Pandas

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('chess.sqlite')

# Load game metrics
df = pd.read_sql_query("""
    SELECT ply, last_move_san, dPV, dMV, dOV, dDV
    FROM v_position_deltas
    WHERE game_id = 1
    ORDER BY ply
""", conn)

print(df)

# Calculate statistics
print(f"\nAverage dPV: {df['dPV'].mean():.2f}")
print(f"Max dMV: {df['dMV'].max():.2f}")
print(f"Min dDV: {df['dDV'].min():.2f}")

conn.close()
```

### Visualization

```python
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

conn = sqlite3.connect('chess.sqlite')

# Get metrics over time
df = pd.read_sql_query("""
    SELECT ply, dPV, dMV, dOV, dDV
    FROM v_position_deltas
    WHERE game_id = 1
    ORDER BY ply
""", conn)

# Plot
fig, axes = plt.subplots(2, 2, figsize=(12, 8))
fig.suptitle('Game Metrics Over Time')

df.plot(x='ply', y='dPV', ax=axes[0, 0], title='Material (dPV)', legend=False)
df.plot(x='ply', y='dMV', ax=axes[0, 1], title='Mobility (dMV)', legend=False)
df.plot(x='ply', y='dOV', ax=axes[1, 0], title='Offensive (dOV)', legend=False)
df.plot(x='ply', y='dDV', ax=axes[1, 1], title='Defensive (dDV)', legend=False)

plt.tight_layout()
plt.show()

conn.close()
```

---

## 💾 Export Data

### Export to CSV

```powershell
# Export all games
sqlite3 -header -csv chess.sqlite "SELECT * FROM games;" > games.csv

# Export game 1 with metrics
sqlite3 -header -csv chess.sqlite "SELECT * FROM v_position_deltas WHERE game_id=1;" > game1.csv

# Export all moves
sqlite3 -header -csv chess.sqlite "SELECT * FROM moves;" > moves.csv
```

### Export to JSON (Python)

```python
import sqlite3
import json

conn = sqlite3.connect('chess.sqlite')
cursor = conn.cursor()

cursor.execute("SELECT * FROM v_position_deltas WHERE game_id = 1")
columns = [desc[0] for desc in cursor.description]
rows = cursor.fetchall()

data = [dict(zip(columns, row)) for row in rows]

with open('game1.json', 'w') as f:
    json.dump(data, f, indent=2)

conn.close()
```

### Export to Markdown

```powershell
sqlite3 -markdown chess.sqlite "SELECT ply, san, dPV, dMV, dOV, dDV FROM v_position_deltas WHERE game_id=1 LIMIT 10;"
```

---

## 🎯 Interactive Mode

```powershell
# Open database
sqlite3 chess.sqlite
```

Inside sqlite3:
```sql
-- Enable nice formatting
.headers on
.mode column

-- List all tables
.tables

-- Show table schema
.schema games
.schema moves
.schema positions

-- Run queries
SELECT * FROM games;

-- Exit
.quit
```

---

## 📊 Quick Reference

| Task | Command |
|------|---------|
| View all games | `python query_database.py` |
| View specific game | `python query_database.py 1` |
| List games (SQL) | `sqlite3 -column -header chess.sqlite "SELECT * FROM games;"` |
| Show moves | `sqlite3 -column -header chess.sqlite "SELECT ply, san FROM moves WHERE game_id=1;"` |
| Show metrics | `sqlite3 -column -header chess.sqlite "SELECT * FROM v_position_deltas WHERE game_id=1;"` |
| Export to CSV | `sqlite3 -csv chess.sqlite "SELECT * FROM games;" > out.csv` |
| Interactive mode | `sqlite3 chess.sqlite` |
| Count games | `sqlite3 chess.sqlite "SELECT COUNT(*) FROM games;"` |

---

## 💡 Tips

1. **Use Views**: `v_position_deltas` automatically calculates deltas - much easier!
2. **Pretty Output**: Use `-column -header` flags for readable tables
3. **Pandas**: For analysis, load data into pandas DataFrames
4. **Backup**: Copy `chess.sqlite` before experimenting with UPDATE/DELETE
5. **Python Script**: Run `python query_database.py` for formatted output
6. **Export**: Use `-csv` or `-markdown` for easy data export

---

## 📚 See Also

- [PLAY_GAME_GUIDE.md](PLAY_GAME_GUIDE.md) - How to play games
- [METRICS_EXPLAINED.md](METRICS_EXPLAINED.md) - Understanding metrics
- [SQRT_DV_FEATURE.md](SQRT_DV_FEATURE.md) - Defense value calculation
- [VARIANCE_FEATURE.md](VARIANCE_FEATURE.md) - Variance system

