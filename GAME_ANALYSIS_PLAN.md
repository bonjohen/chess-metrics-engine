# Game Analysis Tools - Implementation Plan

## 📋 Overview
Add comprehensive game analysis tools to identify blunders, critical positions, and generate game statistics from the metrics data.

## 📊 Project Status: ✅ COMPLETE
- **Started:** 2026-01-08
- **Completed:** 2026-01-08
- **Actual Time:** ~1.5 hours

---

## 🎯 Core Features

### 1. Blunder Detection
- Identify moves with large negative metric swings
- Configurable threshold (e.g., -10 points in any metric)
- Track both sides' blunders separately

### 2. Critical Position Analysis
- Find positions with highest metric values
- Identify turning points (largest swings)
- Detect decisive moments

### 3. Game Statistics
- Total blunders per side
- Average metric values over time
- Material balance progression
- Metric trends (improving/declining)

### 4. Move Quality Assessment
- Categorize moves: Excellent, Good, Inaccuracy, Mistake, Blunder
- Based on metric delta thresholds

---

## 📐 Technical Design

### Analysis Module Structure
```
src/chess_metrics/analysis.py
├── detect_blunders()      # Find moves with large negative swings
├── find_critical_positions()  # Identify key moments
├── calculate_statistics()     # Aggregate game stats
├── assess_move_quality()      # Categorize individual moves
└── generate_game_report()     # Create comprehensive analysis
```

### Data Structures
```python
@dataclass
class Blunder:
    ply: int
    side: str  # 'white' or 'black'
    san: str
    metric: str  # 'PV', 'MV', 'OV', 'DV'
    delta: float
    before: float
    after: float

@dataclass
class CriticalPosition:
    ply: int
    fen: str
    reason: str  # 'peak_value', 'turning_point', etc.
    metrics: Dict[str, float]

@dataclass
class GameStatistics:
    white_blunders: int
    black_blunders: int
    avg_pv_white: float
    avg_pv_black: float
    # ... more stats
    turning_points: List[int]  # ply numbers
```

---

## 🔧 Implementation Tasks

### Phase 1: Core Analysis Functions ✅ COMPLETE
- [x] **T1.1** - Create analysis.py module
- [x] **T1.2** - Implement blunder detection algorithm
- [x] **T1.3** - Implement critical position finder
- [x] **T1.4** - Implement statistics calculator
- [x] **T1.5** - Implement move quality assessment

### Phase 2: Report Generation ✅ COMPLETE
- [x] **T2.1** - Design text report format
- [x] **T2.2** - Implement report generator
- [x] **T2.3** - Add summary section
- [x] **T2.4** - Add detailed move-by-move section

### Phase 3: CLI Integration ✅ COMPLETE
- [x] **T3.1** - Add analyze-game CLI command
- [x] **T3.2** - Support output to file or stdout
- [x] **T3.3** - Add configurable thresholds
- [x] **T3.4** - Add verbosity levels

### Phase 4: Testing & Validation ✅ COMPLETE
- [x] **T4.1** - Test with various game types
- [x] **T4.2** - Validate blunder detection accuracy
- [x] **T4.3** - Test report formatting
- [x] **T4.4** - Test edge cases (short games, draws)

---

## 📊 Blunder Detection Thresholds

### Metric Delta Thresholds
- **Blunder:** < -15 points in any metric
- **Mistake:** -10 to -15 points
- **Inaccuracy:** -5 to -10 points
- **Good:** -5 to +5 points
- **Excellent:** > +5 points

### Critical Position Criteria
- **Peak Value:** Metric > 40 points
- **Turning Point:** Absolute delta > 20 points
- **Decisive Moment:** Material change + large metric swing

---

## 🎨 Report Format Example

```
=== GAME ANALYSIS: Game #9 ===
White: W_defense-first (ai)
Black: B_materialist (ai)
Result: 1/2-1/2 (max_moves)

--- SUMMARY ---
Total Moves: 30 (15 full moves)
White Blunders: 2
Black Blunders: 3
Turning Points: 3 (ply 6, 14, 15)

--- BLUNDERS ---
[Ply 6] Black: Bxc3 - Material blunder (PV: -3)
[Ply 8] White: Qxg5 - Material blunder (PV: -3)
[Ply 14] White: Bxd3 - Severe material loss (PV: -9)

--- CRITICAL POSITIONS ---
[Ply 6] Peak Defense - White DV: 43.3
[Ply 14] Turning Point - Material swing of 9 points

--- STATISTICS ---
Average Material (PV):
  White: 28.5 | Black: 29.2
Average Mobility (MV):
  White: 25.3 | Black: 31.7
...
```

---

## 🚀 CLI Usage Examples

```powershell
# Basic analysis
python -m chess_metrics.cli analyze-game --game-id 9

# Save to file
python -m chess_metrics.cli analyze-game --game-id 9 --output analysis.txt

# Adjust blunder threshold
python -m chess_metrics.cli analyze-game --game-id 9 --blunder-threshold 20

# Verbose output
python -m chess_metrics.cli analyze-game --game-id 9 --verbose
```

---

## ✅ Implementation Summary

### Files Created
1. **src/chess_metrics/analysis.py** - Game analysis module (450 lines)
   - `Blunder` dataclass - Represents poor moves
   - `CriticalPosition` dataclass - Represents key moments
   - `GameStatistics` dataclass - Aggregate stats
   - `assess_move_quality()` - Categorize move quality
   - `detect_blunders()` - Find blunders, mistakes, inaccuracies
   - `find_critical_positions()` - Identify peak values and turning points
   - `calculate_statistics()` - Compute game-wide statistics
   - `generate_game_report()` - Create formatted text report

### Files Modified
1. **src/chess_metrics/db/repo.py** - Added analysis query method
   - `get_game_for_analysis()` - Get game data with all positions and metrics

2. **src/chess_metrics/cli.py** - Added analyze-game command
   - Import analysis functions
   - Add CLI argument parser with configurable thresholds
   - Implement analysis handler with file/stdout output

### Testing Results
✅ Basic analysis (game 9, game 7)
✅ Verbose mode with inaccuracies
✅ File output
✅ Configurable thresholds
✅ Blunder detection accuracy
✅ Critical position identification
✅ Statistics calculation
✅ Report formatting

### Example Usage
```powershell
# Basic analysis
python -m chess_metrics.cli analyze-game --game-id 9

# Verbose with all details
python -m chess_metrics.cli analyze-game --game-id 9 --verbose

# Save to file
python -m chess_metrics.cli analyze-game --game-id 9 --output analysis.txt

# Adjust thresholds for stricter analysis
python -m chess_metrics.cli analyze-game --game-id 9 --blunder-threshold -8 --mistake-threshold -6
```

### Example Output
```
============================================================
GAME ANALYSIS: Game #9
============================================================
White: W_defense-first (ai)
Black: B_materialist (ai)
Result: 1/2-1/2 (max_moves)

────────────────────────────────────────────────────────────
SUMMARY
────────────────────────────────────────────────────────────
Total Moves: 31 (15 full moves)

White Performance:
  Blunders: 0
  Mistakes: 1
  Inaccuracies: 1

Black Performance:
  Blunders: 1
  Mistakes: 1
  Inaccuracies: 0

Turning Points: 1 (ply 28)

────────────────────────────────────────────────────────────
BLUNDERS & MISTAKES
────────────────────────────────────────────────────────────
Blunders:
  [14...] Black: Bxd3
      OV: 13.0 → 4.0 (Δ-9.0)

Mistakes:
  [8...] Black: Qxg5
      OV: 8.0 → 2.0 (Δ-6.0)
  [9.] White: Nxg5
      DV: 28.4 → 20.7 (Δ-7.7)

────────────────────────────────────────────────────────────
AVERAGE METRICS
────────────────────────────────────────────────────────────
Material Value (PV): White: 33.5 | Black: 33.0
Mobility Value (MV): White: 25.1 | Black: 31.9
Offensive Value (OV): White: 2.8 | Black: 4.7
Defensive Value (DV): White: 29.5 | Black: 22.8
```

---

## 🎯 Success Criteria

- ✅ Accurately detects blunders based on metric swings
- ✅ Identifies critical positions
- ✅ Generates comprehensive statistics
- ✅ Produces readable text reports
- ✅ Configurable thresholds
- ✅ Handles edge cases gracefully

---

## 🚀 Next Steps

Game Analysis Tools are complete! You can now:
- Analyze any game for blunders and mistakes
- Identify critical positions and turning points
- Get comprehensive statistics
- Adjust thresholds for different analysis levels

**Recommended next action:** Proceed with Option C (Performance Optimization) or Option D (Opening Book Analysis) from NEXT_STEPS_PLAN.md

