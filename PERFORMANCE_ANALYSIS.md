# Performance Analysis - Chess Metrics Engine

**Date:** 2026-01-09  
**Benchmark Tool:** `benchmark_performance.py`

---

## 📊 Executive Summary

The Chess Metrics Engine has been profiled to identify performance bottlenecks. The primary bottleneck is **metrics computation**, specifically the `compute_mv_ov` and `compute_dv` functions, which account for ~86% of total execution time during AI search.

### Key Findings:
- **AI Search Depth 3:** ~5.5 seconds per move
- **Bottleneck:** Metrics computation (5.0s out of 5.5s = 91%)
  - `compute_mv_ov`: 2.98s (54%)
  - `compute_dv`: 1.82s (33%)
- **Move Generation:** Fast (~0.2ms per call)
- **Database Operations:** Very fast (~0.08ms per query)

---

## 🔍 Detailed Benchmark Results

### 1. Move Generation Performance
**Test:** 100 iterations per position

| Position Type | Moves | Avg Time | Performance |
|--------------|-------|----------|-------------|
| Starting     | 20    | 0.131ms  | ✅ Excellent |
| Italian Game | 33    | 0.223ms  | ✅ Excellent |
| Catalan      | 33    | 0.215ms  | ✅ Excellent |
| Middlegame   | 37    | 0.250ms  | ✅ Excellent |

**Average:** 0.204ms per generation  
**Verdict:** Move generation is highly optimized and not a bottleneck.

---

### 2. Metrics Computation Performance
**Test:** 50 iterations per position

| Position Type | Avg Time | Performance |
|--------------|----------|-------------|
| Starting     | 0.661ms  | ⚠️ Moderate |
| Italian Game | 0.834ms  | ⚠️ Moderate |
| Catalan      | 0.793ms  | ⚠️ Moderate |
| Middlegame   | 0.896ms  | ⚠️ Moderate |

**Average:** 0.796ms per computation  
**Verdict:** Metrics computation is 3-4x slower than move generation.

---

### 3. AI Search Performance
**Test:** Middlegame position with default profile

| Depth | Time    | Nodes/sec | Performance |
|-------|---------|-----------|-------------|
| 1     | 0.03s   | ~28,709   | ✅ Good     |
| 2     | 1.32s   | ~755      | ⚠️ Moderate |
| 3     | 5.55s   | ~180      | ❌ Slow     |

**Verdict:** Depth 3 search is too slow for interactive play. Depth 2 is acceptable.

---

### 4. Database Operations
**Test:** 10 iterations of `get_game_for_analysis`

| Operation | Avg Time | Performance |
|-----------|----------|-------------|
| Full Query | 0.085ms | ✅ Excellent |

**Verdict:** Database is not a bottleneck.

---

## 🎯 Profiling Breakdown (Depth 3 Search)

### Top Time Consumers

| Function/Section | Calls | Total (ms) | Avg (ms) | % of Total |
|-----------------|-------|------------|----------|------------|
| `cached_compute_metrics` | 5,302 | 5,005.11 | 0.94 | **90.1%** |
| ├─ `compute_mv_ov` | 5,302 | 2,980.03 | 0.56 | 53.7% |
| ├─ `compute_dv` | 5,302 | 1,820.54 | 0.34 | 32.8% |
| └─ `compute_pv` | 5,302 | 37.14 | 0.01 | 0.7% |
| `generate_legal_moves` | 1,360 | 335.51 | 0.25 | 6.0% |
| `to_fen` | 7,202 | 77.04 | 0.01 | 1.4% |
| `move_ordering` | 1,360 | 9.32 | 0.01 | 0.2% |

---

## 🚨 Critical Bottlenecks

### 1. **compute_mv_ov** (54% of time)
**What it does:** Calculates Mobility Value (MV) and Offensive Value (OV)
- Generates all legal moves for a side
- Counts non-capture moves (MV) and capture values (OV)

**Why it's slow:**
- Called 5,302 times during depth-3 search
- Each call generates legal moves (expensive)
- Legal move generation requires checking if king is in check after each move

**Optimization opportunities:**
- ✅ Already using transposition table for caching
- 🔄 Could cache MV/OV separately from full metrics
- 🔄 Could use pseudo-legal moves for MV/OV estimation (less accurate but faster)

### 2. **compute_dv** (33% of time)
**What it does:** Calculates Defensive Value (DV)
- For each friendly piece, checks how many other friendly pieces defend it
- Uses `pseudo_attacks_square` and `is_in_check` for validation

**Why it's slow:**
- Nested loops over all friendly pieces
- Multiple board state checks per piece pair
- Called 5,302 times during depth-3 search

**Optimization opportunities:**
- 🔄 Could use incremental updates instead of full recalculation
- 🔄 Could approximate DV with simpler heuristics
- 🔄 Could cache DV values more aggressively

---

## 💡 Optimization Recommendations

### High Priority (2-3x speedup potential)

1. **Incremental Metrics Updates**
   - Instead of recalculating all metrics from scratch, update them incrementally after each move
   - Complexity: High
   - Impact: Very High (2-3x speedup)

2. **Simplified DV Calculation**
   - Use a faster approximation for DV (e.g., count attackers without full legality checks)
   - Complexity: Medium
   - Impact: High (1.5-2x speedup)

3. **Better Transposition Table**
   - Increase cache size
   - Use Zobrist hashing instead of FEN strings
   - Complexity: Medium
   - Impact: Medium (1.3-1.5x speedup)

### Medium Priority (1.2-1.5x speedup potential)

4. **Move Ordering Improvements**
   - Better move ordering reduces nodes searched
   - Add killer moves and history heuristic
   - Complexity: Medium
   - Impact: Medium (1.2-1.5x speedup)

5. **Lazy Evaluation**
   - Don't compute all metrics if alpha-beta cutoff occurs
   - Complexity: Low
   - Impact: Low-Medium (1.1-1.3x speedup)

### Low Priority

6. **Parallel Search**
   - Use multiple threads for batch game generation
   - Complexity: High
   - Impact: High for batch, none for single games

---

## 📈 Performance Targets

| Metric | Current | Target | Improvement Needed |
|--------|---------|--------|-------------------|
| Depth 3 search | 5.5s | 2.0s | 2.75x speedup |
| Depth 2 search | 1.3s | 0.5s | 2.6x speedup |
| Metrics computation | 0.8ms | 0.3ms | 2.7x speedup |

**Achievable with:** Incremental metrics + simplified DV + better caching

---

## 🛠️ Tools Added

1. **`benchmark_performance.py`** - Comprehensive benchmarking script
2. **Profiling decorators** - Added to all critical functions
3. **`/api/profiling` endpoint** - View profiling stats in web app
4. **`print_timing_report()`** - Generate formatted profiling reports

---

## 📝 Next Steps

1. ✅ Profiling infrastructure complete
2. ⏭️ Implement incremental metrics updates
3. ⏭️ Simplify DV calculation
4. ⏭️ Improve transposition table
5. ⏭️ Re-benchmark and measure improvements

