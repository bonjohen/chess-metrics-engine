# Performance Optimization Plan

**Date:** 2026-01-09  
**Current Performance:** Depth 3 search = 6.6 seconds  
**Target:** 2-3 seconds (2-3x speedup)

---

## 📊 Current Bottleneck Analysis

From benchmark results:

| Component | Time (ms) | % of Total | Calls | Avg (ms) |
|-----------|-----------|------------|-------|----------|
| **cached_compute_metrics** | 10,960 | 65% | 11,529 | 0.95 |
| - unified_mv_ov | 3,684 | 22% | 6,445 | 0.57 |
| - unified_dv | 2,255 | 13% | 6,445 | 0.35 |
| **choose_best_move:evaluate_moves** | 6,621 | 40% | 1 | - |
| **generate_legal_moves** | 347 | 2% | 1,360 | 0.26 |
| **material_safety** | 5.6 | <1% | 37 | 0.15 |

**Key Findings:**
1. **Metrics computation is 65% of total time** (10.96s out of 16.6s)
2. **MV/OV computation is the biggest bottleneck** (3.68s = 22%)
3. **DV computation is second** (2.26s = 13%)
4. **Caching is working well** - 11,529 calls but only 6,445 actual computations
5. **Material safety is negligible** (<1%) - our recent addition is efficient!

---

## 🎯 Optimization Opportunities (Ranked by Impact)

### **Priority 1: Optimize MV/OV Computation** (Expected: 1.5-2x speedup)

**Current Issue:**
- `unified_mv_ov` takes 0.57ms per call
- Generates full legal moves for both sides
- Legal move generation requires king safety checks

**Solutions:**
1. **Use pseudo-legal moves for MV estimation** (faster, less accurate)
2. **Cache move generation separately** from full metrics
3. **Lazy evaluation** - don't compute MV/OV if position is pruned

**Implementation:**
- Add `compute_metrics_fast()` that uses pseudo-legal moves
- Use for non-leaf nodes (depth > 0)
- Use full legal moves only at leaf nodes

---

### **Priority 2: Optimize DV Computation** (Expected: 1.3-1.5x speedup)

**Current Issue:**
- `unified_dv` takes 0.35ms per call
- Nested loop over all friendly pieces
- Simulates capture-like moves with apply/undo

**Solutions:**
1. **Approximate DV** - count defenders without full legality check
2. **Cache piece attack patterns** - precompute which pieces can attack which squares
3. **Skip DV for pruned positions** - lazy evaluation

**Implementation:**
- Add `compute_dv_fast()` that counts pseudo-attackers
- Use for non-leaf nodes
- Use accurate DV only at leaf nodes

---

### **Priority 3: Improve Transposition Table** (Expected: 1.2-1.3x speedup)

**Current Status:**
- Already using Zobrist hashing ✅
- Cache hit rate: ~47% (11,529 calls, 6,445 computations)

**Solutions:**
1. **Increase cache size** - allow more positions to be cached
2. **Better replacement strategy** - keep more valuable positions
3. **Separate caches** for different metric types

**Implementation:**
- Add cache size limit with LRU eviction
- Track cache hit/miss statistics
- Tune cache size based on memory constraints

---

### **Priority 4: Better Move Ordering** (Expected: 1.2-1.4x speedup)

**Current Status:**
- Basic MVV-LVA ordering
- Takes only 0.01ms per call (very fast)

**Solutions:**
1. **Add killer move heuristic** - remember good moves from sibling nodes
2. **Add history heuristic** - track which moves cause cutoffs
3. **Principal variation tracking** - try PV moves first

**Implementation:**
- Add killer move table (2 killers per ply)
- Add history table (indexed by from_sq, to_sq)
- Update move_priority() to use these heuristics

---

## 🚀 Implementation Plan

### **Phase 1: Quick Wins (1-2 hours)**
1. ✅ Add lazy evaluation for metrics
   - Don't compute full metrics if alpha-beta cutoff likely
   - Compute PV first, then MV/OV, then DV
   - Early exit if position is clearly bad

2. ✅ Add fast metrics mode
   - `compute_metrics_fast()` using pseudo-legal moves
   - Use for non-leaf nodes (depth > 0)
   - Expected: 1.5x speedup

### **Phase 2: Medium Effort (2-4 hours)**
3. ✅ Optimize DV computation
   - Add `compute_dv_fast()` approximation
   - Use for non-leaf nodes
   - Expected: 1.3x speedup

4. ✅ Improve move ordering
   - Add killer moves (simple)
   - Add history heuristic (medium)
   - Expected: 1.2x speedup

### **Phase 3: Advanced (4-8 hours)**
5. ⏳ Better transposition table
   - Add cache size limits
   - Better replacement strategy
   - Expected: 1.2x speedup

6. ⏳ Parallel search (if needed)
   - Multi-threaded root move evaluation
   - Requires careful synchronization
   - Expected: 2-3x speedup (on multi-core)

---

## 📈 Expected Results

| Optimization | Speedup | Cumulative | Depth 3 Time |
|--------------|---------|------------|--------------|
| **Baseline** | 1.0x | 1.0x | 6.6s |
| Fast metrics | 1.5x | 1.5x | 4.4s |
| Fast DV | 1.3x | 2.0x | 3.3s |
| Better ordering | 1.2x | 2.4x | 2.8s |
| Better cache | 1.2x | 2.9x | 2.3s |

**Target achieved:** 2.3s (2.9x speedup) ✅

---

## 🔧 Testing Strategy

1. **Correctness tests** - ensure optimizations don't break functionality
2. **Performance benchmarks** - measure actual speedup
3. **Quality tests** - ensure AI still plays well
4. **Regression tests** - ensure no blunders introduced

---

## 📝 Notes

- Material safety optimization was successful - only 5.6ms total!
- Zobrist hashing is working well - no need to optimize further
- Move generation is already fast (0.26ms) - not a bottleneck
- Focus on metrics computation (65% of time)

