# Square Root Defense Value Feature

## Overview
The defense value (DV) calculation now uses the **square root of piece values** instead of raw piece values. This provides a more realistic and balanced evaluation of defensive strength.

## What Changed

### Old Calculation
```python
dv += piece_value  # e.g., Queen = 9, Rook = 5, Pawn = 1
```

### New Calculation
```python
dv += math.sqrt(piece_value)  # e.g., Queen = 3.0, Rook = 2.24, Pawn = 1.0
```

## Impact on Piece Values

| Piece  | Value | Old DV | New DV (sqrt) | Reduction |
|--------|-------|--------|---------------|-----------|
| Pawn   | 1     | 1      | 1.000         | 0.0%      |
| Knight | 3     | 3      | 1.732         | 42.3%     |
| Bishop | 3     | 3      | 1.732         | 42.3%     |
| Rook   | 5     | 5      | 2.236         | 55.3%     |
| Queen  | 9     | 9      | 3.000         | 66.7%     |

**Key Observation:** Higher value pieces contribute proportionally less to defense.

## Why Square Root?

### 1. Diminishing Returns
In chess, defending a queen is important, but not **9 times** more important than defending a pawn. The square root provides a more realistic scaling:
- Queen: 9 → 3.0 (3x more valuable than pawn)
- Rook: 5 → 2.24 (2.24x more valuable than pawn)

### 2. Balance with Other Metrics
The old DV calculation could dominate the Sum column because piece values are relatively large (1, 3, 5, 9). With square root:
- DV values are smaller and more comparable to MV and OV
- Sum is more balanced across all four metrics
- No single metric dominates the evaluation

### 3. Strategic Realism
The square root encourages **distributed defense**:

**Example:**
- **Old system:**
  - Defending 1 queen (9) + 1 pawn (1) = **10 DV**
  - Defending 2 rooks (5 + 5) = **10 DV**
  - Equal value (but 2 rooks are more valuable!)

- **New system:**
  - Defending 1 queen + 1 pawn = sqrt(9) + sqrt(1) = 3.0 + 1.0 = **4.0 DV**
  - Defending 2 rooks = sqrt(5) + sqrt(5) = 2.24 + 2.24 = **4.48 DV**
  - 2 rooks valued higher (more realistic!)

### 4. Prevents DV Domination
In the starting position:
- **Old DV:** ~35 per side (very high)
- **New DV:** ~24 per side (more balanced)
- **MV:** ~20 per side
- **OV:** ~0 per side

With the new calculation, DV doesn't overwhelm the other metrics.

## Examples

### Starting Position
```
Old DV_white: 35, DV_black: 35
New DV_white: 23.93, DV_black: 23.93
```

### Test Position
```
FEN: 3r2k1/8/8/2p5/3P4/8/3R4/3Q2K1 w - - 0 1
White pieces: Queen(9), Rook(5), Pawn(1)

Old DV_white: 9 + 5 + 1 = 15
New DV_white: sqrt(9) + sqrt(5) + sqrt(1) = 3.0 + 2.24 + 1.0 = 6.24
```

### Move Evaluation Impact
```
Top moves in starting position:

Old system (sorted by Sum):
Move: Nc3, dPV=+0, dMV=+2, dOV=+0, dDV=+16, Sum=+18

New system (sorted by Sum):
Move: Nc3, dPV=+0.0, dMV=+2.0, dOV=+0.0, dDV=+7.46, Sum=+9.46
```

**Notice:** dDV is now smaller, making the Sum more balanced.

## Technical Details

### Code Changes

**File:** `src/chess_metrics/engine/metrics.py`

```python
def compute_dv(state: GameState, side: int) -> float:
    import math
    from .types import KING
    b = state.board
    dv = 0.0  # Changed from int to float

    friendly_squares = [sq for sq, p in enumerate(b) if p != 0 and piece_color(p) == side]
    for t in friendly_squares:
        X = b[t]
        valueX = PIECE_VALUE[piece_kind(X)]

        if piece_kind(X) == KING:
            continue

        for f in friendly_squares:
            if f == t:
                continue
            A = b[f]
            if not pseudo_attacks_square(state, f, t):
                continue

            moved, captured, _ = _apply_capture_like(state, f, t)
            ok = not is_in_check(state, side)
            _undo_capture_like(state, f, t, moved, captured)

            if ok:
                dv += math.sqrt(valueX)  # Changed from valueX

    return dv
```

### Dataclass Update

```python
@dataclass(frozen=True)
class Metrics:
    pv_w: int
    mv_w: int
    ov_w: int
    dv_w: float  # Changed from int
    pv_b: int
    mv_b: int
    ov_b: int
    dv_b: float  # Changed from int
```

## Benefits

### 1. More Realistic Evaluation
- Defending a queen is 3x more valuable than a pawn (not 9x)
- Reflects the diminishing marginal value of higher-value pieces

### 2. Better Metric Balance
- DV no longer dominates the Sum
- All four metrics (PV, MV, OV, DV) contribute more equally
- More nuanced position evaluation

### 3. Encourages Distributed Defense
- Defending multiple pieces is valued appropriately
- Prevents over-valuation of single high-value piece defense

### 4. Improved Move Rankings
- Moves are ranked more holistically
- Less bias toward defensive moves
- Better balance between offense and defense

## Comparison Table

| Scenario | Old DV | New DV | Difference |
|----------|--------|--------|------------|
| Defend 1 pawn | 1 | 1.00 | 0% |
| Defend 1 knight | 3 | 1.73 | -42% |
| Defend 1 rook | 5 | 2.24 | -55% |
| Defend 1 queen | 9 | 3.00 | -67% |
| Defend 3 pawns | 3 | 3.00 | 0% |
| Defend 1 queen + 1 pawn | 10 | 4.00 | -60% |
| Defend 2 rooks | 10 | 4.48 | -55% |

## Testing

All tests updated and passing:
- ✅ Unit tests updated for new DV values
- ✅ Square root calculation verified
- ✅ Metric balance confirmed
- ✅ Move analysis works correctly

See `test_sqrt_dv.py` for comprehensive tests.

## Migration

**No database migration needed** - DV is calculated on-the-fly from board state.

Existing games in the database will automatically use the new calculation when positions are re-evaluated.

---

## See Also

- [METRICS_EXPLAINED.md](METRICS_EXPLAINED.md) - Understanding all metrics
- [DATABASE_GUIDE.md](DATABASE_GUIDE.md) - Query defense values from database
- [VARIANCE_FEATURE.md](VARIANCE_FEATURE.md) - Variance system

## Summary

The square root DV calculation provides:
- ✅ More realistic piece defense valuation
- ✅ Better balance between metrics
- ✅ Encourages distributed defense
- ✅ Prevents DV from dominating evaluations
- ✅ More nuanced and strategic move rankings

This change makes the chess engine's evaluation more sophisticated and realistic!

