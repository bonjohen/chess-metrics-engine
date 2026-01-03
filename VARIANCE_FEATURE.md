# Variance Feature

## Overview

The chess metrics engine now includes a **variance feature** that introduces a small amount of randomness to move evaluations. This makes the game more interesting and less deterministic, while still maintaining strategic coherence.

## How It Works

### Variance Factor
- Each move is assigned a random **variance factor** between **0.75 and 1.25**
- This factor is multiplied by the delta metrics (dPV, dMV, dOV, dDV)
- The variance factor is saved in the database for each move

### Application
When a move is made:
1. A random variance factor is generated (e.g., 0.95)
2. The delta metrics are multiplied by this factor
3. The variance factor is stored in the `moves` table

### Example
```
Original deltas: dPV=+10, dMV=+5, dOV=+3, dDV=-2
Variance factor: 0.90
Adjusted deltas: dPV=+9.0, dMV=+4.5, dOV=+2.7, dDV=-1.8
```

## Why Variance?

### 1. Reduces Determinism
Without variance, the AI would always make the same move in the same position. Variance introduces variety while keeping moves strategically sound.

### 2. Simulates Uncertainty
In real chess, players don't have perfect evaluation. Variance simulates the uncertainty and imperfect calculation that humans experience.

### 3. More Interesting Games
Games between the same AI profiles become more varied and interesting to watch.

### 4. Realistic Play
Small variations in evaluation are realistic - even strong players might evaluate the same position slightly differently on different days.

## Database Schema Changes

### Positions Table
Metrics are now stored as **REAL** (floating-point) instead of INTEGER:
```sql
pv_w REAL NOT NULL,
mv_w REAL NOT NULL,
ov_w REAL NOT NULL,
dv_w REAL NOT NULL,
pv_b REAL NOT NULL,
mv_b REAL NOT NULL,
ov_b REAL NOT NULL,
dv_b REAL NOT NULL
```

### Moves Table
Added `variance_factor` column:
```sql
variance_factor REAL NULL
```

This stores the variance factor (0.75-1.25) that was applied to the move's evaluation.

## Display Changes

### Move Analysis Table
The variance factor and sum of deltas are now displayed in the move options:

```
#    Move     SAN        dPV   dMV   dOV   dDV   Var    Sum |  PVw  MVw  OVw  DVw  PVb  MVb  OVb  DVb
1    e2e4     e4        +0.0  +9.5  +0.0  -3.8  0.95   +5.7 |   39   30    0   31   39   20    0   35
```

**New columns:**
- **Var**: Variance factor (0.75-1.25) applied to this move's deltas
- **Sum**: Total of all deltas (dPV + dMV + dOV + dDV) - used for sorting

### Decimal Precision
- Delta metrics (dPV, dMV, dOV, dDV) shown with 1 decimal place
- Variance factor shown with 2 decimal places
- Sum shown with 1 decimal place
- Absolute metrics (PVw, MVw, etc.) shown as whole numbers

### Move Sorting
- Moves are now **sorted by Sum** (descending order)
- Sum = dPV + dMV + dOV + dDV
- Higher Sum = better overall move
- This replaces the previous sorting by dPV only

## Impact on Gameplay

### Human Players
- See variance factor for each move option
- Can understand that evaluations have some "noise"
- Makes choosing between similar moves more interesting

### AI Players
- AI still uses the same search algorithm
- Variance is applied after move selection
- Creates variety in AI play without changing core strategy

### Game Records
- Every move's variance is recorded
- Can analyze how variance affected game outcomes
- Useful for post-game analysis

## Technical Details

### Variance Generation
```python
def generate_variance() -> float:
    """Generate a random variance factor between 0.75 and 1.25."""
    return random.uniform(0.75, 1.25)
```

### Application to Metrics
```python
variance_factor = generate_variance()  # e.g., 0.95

# Apply to deltas
dPV_varied = dPV * variance_factor
dMV_varied = dMV * variance_factor
dOV_varied = dOV * variance_factor
dDV_varied = dDV * variance_factor
```

### Storage
```python
repo.insert_move(
    game_id, ply, uci, san, from_sq, to_sq,
    is_capture, is_ep, is_castle, is_promotion, promotion_piece,
    variance_factor  # Saved to database
)
```

## Querying Variance

### Get variance for all moves in a game
```sql
SELECT ply, uci, san, variance_factor 
FROM moves 
WHERE game_id = 1 
ORDER BY ply;
```

### Average variance in a game
```sql
SELECT AVG(variance_factor) as avg_variance 
FROM moves 
WHERE game_id = 1;
```

### Moves with high variance
```sql
SELECT ply, uci, san, variance_factor 
FROM moves 
WHERE game_id = 1 AND variance_factor > 1.15
ORDER BY variance_factor DESC;
```

## Configuration

### Disabling Variance
To disable variance (for testing or analysis), modify the game loop:
```python
# In play_interactive_game function
display_move_options(state, legal, current_name, current_side, apply_variance=False)
variance_factor = 1.0  # No variance
```

### Adjusting Variance Range
To change the variance range, modify the `generate_variance()` function:
```python
def generate_variance() -> float:
    # Tighter range (0.90 to 1.10)
    return random.uniform(0.90, 1.10)
    
    # Wider range (0.50 to 1.50)
    return random.uniform(0.50, 1.50)
```

## Examples

### Low Variance (0.76)
```
Move: Nf3
Original: dPV=+0, dMV=+2, dOV=+0, dDV=+7
With variance: dPV=+0.0, dMV=+1.5, dOV=+0.0, dDV=+5.3
Effect: Move appears slightly weaker
```

### High Variance (1.23)
```
Move: e4
Original: dPV=+0, dMV=+10, dOV=+0, dDV=-4
With variance: dPV=+0.0, dMV=+12.3, dOV=+0.0, dDV=-4.9
Effect: Move appears slightly stronger
```

### Neutral Variance (1.00)
```
Move: d4
Original: dPV=+0, dMV=+8, dOV=+0, dDV=-3
With variance: dPV=+0.0, dMV=+8.0, dOV=+0.0, dDV=-3.0
Effect: No change
```

## Benefits

1. **Variety**: Same position can lead to different moves
2. **Realism**: Simulates human evaluation uncertainty
3. **Analysis**: Can study how variance affects outcomes
4. **Fun**: Makes games less predictable
5. **Learning**: Shows that small evaluation differences matter less

## Limitations

1. **Not Perfect**: Variance is uniform, real uncertainty might be different
2. **No Context**: Variance doesn't consider position type (opening vs endgame)
3. **Same Range**: All metrics get same variance range (could be different)
4. **Random**: Not based on position complexity or player strength

## Future Enhancements

Potential improvements:
1. **Adaptive Variance**: Higher variance in complex positions
2. **Metric-Specific**: Different variance ranges for PV, MV, OV, DV
3. **Player-Based**: Different variance for different AI profiles
4. **Time-Based**: Variance could change based on time pressure
5. **Learning**: Variance could be tuned based on game outcomes

---

## See Also

- [METRICS_EXPLAINED.md](METRICS_EXPLAINED.md) - Understanding metrics
- [DATABASE_GUIDE.md](DATABASE_GUIDE.md) - Query variance data
- [SQRT_DV_FEATURE.md](SQRT_DV_FEATURE.md) - Defense value calculation
- [SUM_COLUMN_FEATURE.md](SUM_COLUMN_FEATURE.md) - Sum column and sorting
