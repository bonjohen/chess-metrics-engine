# Architecture Issues Analysis

**Date:** 2026-01-09  
**Context:** Performance optimization attempt revealed fundamental architectural problems

---

## 🚨 Critical Issues Identified

### **Issue #1: Cache Pollution with Mixed Metrics**

**Problem:**
```python
# Current code (BROKEN):
if hash_key not in _metrics_cache:
    if use_fast:
        _metrics_cache[hash_key] = compute_metrics_fast(state)  # Pseudo-legal moves
    else:
        _metrics_cache[hash_key] = compute_metrics(state)       # Legal moves
return _metrics_cache[hash_key]
```

**Why it's broken:**
1. **Same cache for different metric types** - Fast metrics (pseudo-legal) and accurate metrics (legal) are stored in the same cache
2. **First-write wins** - If a position is first evaluated with `use_fast=True`, it stores inaccurate metrics
3. **Later accurate requests get wrong data** - When we later need accurate metrics for the same position, we get the cached fast (inaccurate) metrics
4. **Evaluation quality degrades** - Leaf nodes (which need accurate metrics) may get pseudo-legal move counts

**Impact:**
- **Correctness issue** - AI makes decisions based on wrong metrics
- **Performance degradation** - 6.6s → 8.76s (33% slower!)
- **Unpredictable behavior** - Results depend on cache hit order

**Fix:**
Use separate caches:
```python
_metrics_cache_fast: Dict[int, Metrics] = {}
_metrics_cache_accurate: Dict[int, Metrics] = {}
```

---

### **Issue #2: Transposition Table Doesn't Respect Metric Quality**

**Problem:**
```python
# Transposition table stores SearchResult with leaf_metrics
_transposition_table[hash_key] = (SearchResult(score, leaf_metrics), depth)
```

**Why it's broken:**
1. **Leaf metrics may be from fast computation** - If we computed a position with fast metrics, the leaf_metrics are inaccurate
2. **Transposition table returns wrong metrics** - Later lookups return inaccurate leaf metrics
3. **No way to distinguish** - We can't tell if cached result used fast or accurate metrics

**Impact:**
- **Correctness issue** - Returned metrics may be pseudo-legal counts
- **Cascading errors** - Wrong metrics propagate through the search tree

**Fix:**
Either:
- Store metric quality flag in transposition table
- Only cache positions evaluated with accurate metrics
- Separate transposition tables for fast/accurate

---

### **Issue #3: Fundamental Design Flaw - Mixing Approximation Levels**

**The Core Problem:**

The current architecture tries to use **two different evaluation functions** (fast vs accurate) in the **same search tree**:

```
Root (accurate)
├─ Move 1 (fast) ← Pseudo-legal metrics
│  ├─ Move 1.1 (fast) ← Pseudo-legal metrics
│  └─ Move 1.2 (accurate) ← Legal metrics ✓
└─ Move 2 (fast) ← Pseudo-legal metrics
   └─ Move 2.1 (accurate) ← Legal metrics ✓
```

**Why this is fundamentally broken:**

1. **Inconsistent evaluation** - Comparing scores from different evaluation functions
2. **Alpha-beta assumes consistency** - Alpha-beta pruning requires monotonic evaluation
3. **Pruning becomes incorrect** - We might prune good moves because fast metrics underestimated them
4. **No theoretical guarantee** - Can't prove correctness of the search

**Example of failure:**
```
Position A: Fast metrics say score = 5.0 (overestimate)
Position B: Accurate metrics say score = 6.0 (correct)

Alpha-beta might prune B because A's fast score was higher!
```

---

## 🎯 Architectural Solutions

### **Option 1: Separate Fast/Accurate Paths (Current Attempt - FLAWED)**

❌ **Don't do this** - Mixing evaluation functions breaks alpha-beta

### **Option 2: Use Fast Metrics Everywhere (Consistent but Inaccurate)**

✅ **Pros:**
- Consistent evaluation function
- Alpha-beta works correctly
- Faster search

❌ **Cons:**
- Lower quality evaluation
- May miss tactical nuances
- Pseudo-legal moves can be misleading

### **Option 3: Use Accurate Metrics Everywhere (Current - SLOW)**

✅ **Pros:**
- Highest quality evaluation
- Correct alpha-beta pruning
- No approximation errors

❌ **Cons:**
- Slower (current: 6.6s for depth 3)
- Can't reach deeper depths

### **Option 4: Iterative Deepening with Quality Tiers (RECOMMENDED)**

Use different metric quality at different depths:

```
Depth 1-2: Fast metrics (quick overview)
Depth 3-4: Accurate metrics (tactical search)
Depth 5+: Accurate metrics + extensions
```

**Key insight:** Use **consistent** metrics within each depth iteration

✅ **Pros:**
- Consistent evaluation at each depth
- Can search deeper with fast metrics first
- Time management - stop when time runs out
- Move ordering improves from shallow search

❌ **Cons:**
- More complex implementation
- Need to manage time budget

---

### **Option 5: Selective Search (ADVANCED)**

Use accurate metrics only for:
- Tactical positions (captures, checks)
- Principal variation
- Positions near leaf nodes

Use fast metrics for:
- Quiet positions
- Positions likely to be pruned
- Deep nodes far from PV

✅ **Pros:**
- Best of both worlds
- Adaptive to position complexity

❌ **Cons:**
- Very complex to implement correctly
- Hard to debug
- Still has consistency issues

---

## 📊 Performance Reality Check

**Current bottleneck breakdown:**
- Metrics computation: 65% (10.96s / 16.6s)
  - MV/OV: 22% (3.68s)
  - DV: 13% (2.26s)
- Search overhead: 35%

**Theoretical speedup limits:**

| Optimization | Best Case Speedup | Realistic Speedup |
|--------------|-------------------|-------------------|
| Fast metrics everywhere | 3x | 2x |
| Better move ordering | 2x | 1.3x |
| Transposition table improvements | 1.5x | 1.2x |
| Parallel search | 4x (4 cores) | 2.5x |

**Reality:** We can't get 10x speedup without fundamental changes

---

## 🔧 Recommended Action Plan

### **Immediate (Revert Bad Changes)**

1. ✅ **Revert the fast/accurate mixing** - Go back to consistent accurate metrics
2. ✅ **Keep killer moves** - This is a safe optimization
3. ✅ **Fix cache pollution** - Ensure cache consistency

### **Short-term (Safe Optimizations)**

4. ✅ **Improve move ordering** - Better ordering = more cutoffs
   - Killer moves (already added)
   - History heuristic
   - MVV-LVA for captures (already have)

5. ✅ **Optimize hot paths** - Profile-guided optimization
   - Inline small functions
   - Reduce allocations
   - Cache piece lists

6. ✅ **Iterative deepening** - Search depth 1, 2, 3 progressively
   - Better move ordering from shallow search
   - Time management
   - Can return best move so far if time runs out

### **Medium-term (Bigger Changes)**

7. ⏳ **Quiescence search** - Extend search for tactical positions
   - Search captures/checks deeper
   - Avoid horizon effect
   - Standard in chess engines

8. ⏳ **Null move pruning** - Skip a move to prove position is bad
   - Very effective pruning technique
   - 20-30% speedup typical

9. ⏳ **Late move reductions** - Search later moves at reduced depth
   - Assumes good move ordering
   - Can search deeper

### **Long-term (Major Refactoring)**

10. ⏳ **Bitboards** - Represent board as 64-bit integers
    - Much faster move generation
    - Standard in modern engines
    - Major rewrite required

11. ⏳ **Parallel search** - Multi-threaded search
    - 2-3x speedup on 4 cores
    - Complex synchronization

---

## 💡 Key Insights

1. **Consistency > Speed** - A slower consistent evaluation beats a faster inconsistent one
2. **Alpha-beta is fragile** - Requires monotonic, consistent evaluation
3. **Caching is critical** - But cache pollution is worse than no cache
4. **Move ordering is king** - Better ordering → more cutoffs → faster search
5. **Depth matters more than speed** - Searching depth 4 with fast metrics may beat depth 3 with slow metrics

---

## 🎓 Lessons Learned

1. **Don't mix evaluation functions** - Alpha-beta assumes consistency
2. **Cache keys must include all relevant state** - Including metric quality
3. **Profile before optimizing** - We optimized the wrong thing
4. **Correctness first, speed second** - A fast wrong answer is useless
5. **Understand the algorithm** - Alpha-beta has strict requirements

---

## Next Steps

**What should we do?**

1. **Revert to working state** - Remove fast/accurate mixing
2. **Keep killer moves** - Safe optimization
3. **Add iterative deepening** - Proper way to use fast metrics
4. **Improve move ordering** - History heuristic
5. **Profile again** - Find real bottlenecks

