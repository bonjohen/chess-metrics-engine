# Chess Engine Optimization Summary

**Date:** 2026-01-09  
**Status:** Reverted broken changes, ready for proper optimizations

---

## ✅ Completed

### 1. **Reverted Fast/Accurate Metrics Mixing**
- **Problem:** Mixing two evaluation functions in same alpha-beta search breaks correctness
- **Solution:** Removed `use_fast` parameter, using consistent accurate metrics everywhere
- **Result:** Back to working baseline (~9.1s for depth 3)

### 2. **Killer Moves Optimization (KEPT)**
- **Status:** Working correctly
- **Implementation:** Stores non-capture moves that caused beta cutoffs
- **Benefit:** Improves move ordering for better pruning

---

## 📊 Current Performance Baseline

**Test position:** `r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 6 7`  
**Depth:** 3  
**Time:** ~9.1 seconds  

**Bottleneck breakdown:**
- Metrics computation: ~65%
  - MV/OV calculation: ~22%
  - DV calculation: ~13%
- Search overhead: ~35%

---

## 🎯 Next Optimizations (In Order)

### **Phase 1: Iterative Deepening** (RECOMMENDED FIRST)
**Why:** Proper way to use time management and improve move ordering

**Benefits:**
- Better move ordering from shallow searches
- Can stop early if time runs out
- Returns best move found so far
- Standard in all chess engines

**Implementation:**
```python
def choose_best_move_iterative(state, profile, max_depth, time_limit=None):
    best_move = None
    for depth in range(1, max_depth + 1):
        result = search(state, depth, ...)
        best_move = result.best_move
        if time_limit and elapsed > time_limit:
            break
    return best_move
```

**Expected improvement:** 10-20% faster due to better move ordering

---

### **Phase 2: History Heuristic**
**Why:** Track which moves are good across the entire search tree

**Benefits:**
- Better move ordering than just killer moves
- Works for all positions, not just current ply
- Complements killer moves

**Implementation:**
```python
_history_scores: Dict[Tuple[int, int], int] = {}  # (from_sq, to_sq) -> score

def update_history(move, depth):
    key = (move.from_sq, move.to_sq)
    _history_scores[key] = _history_scores.get(key, 0) + depth * depth
```

**Expected improvement:** 5-15% faster

---

### **Phase 3: Quiescence Search**
**Why:** Avoid horizon effect - don't stop search in middle of tactical sequence

**Benefits:**
- More accurate evaluation
- Avoids missing tactics
- Standard in all chess engines

**Implementation:**
```python
def quiescence(state, alpha, beta):
    stand_pat = evaluate(state)
    if stand_pat >= beta:
        return beta
    alpha = max(alpha, stand_pat)
    
    # Only search captures and checks
    for move in generate_tactical_moves(state):
        score = -quiescence(make_move(state, move), -beta, -alpha)
        alpha = max(alpha, score)
        if alpha >= beta:
            break
    return alpha
```

**Expected improvement:** Better quality, similar speed

---

### **Phase 4: Null Move Pruning**
**Why:** Prove that position is so good we can skip a move and still be winning

**Benefits:**
- Very effective pruning
- 20-30% speedup typical
- Standard technique

**Implementation:**
```python
if depth >= 3 and not in_check:
    # Give opponent a free move
    null_state = make_null_move(state)
    score = -search(null_state, depth - 3, -beta, -beta + 1)
    if score >= beta:
        return beta  # Position is too good, prune
```

**Expected improvement:** 20-30% faster

---

### **Phase 5: Late Move Reductions (LMR)**
**Why:** Search later moves (likely bad) at reduced depth

**Benefits:**
- Can search much deeper
- Assumes good move ordering
- Standard in modern engines

**Implementation:**
```python
if move_number > 4 and depth >= 3 and not tactical:
    # Search at reduced depth first
    score = -search(new_state, depth - 2, -alpha - 1, -alpha)
    if score > alpha:
        # Re-search at full depth
        score = -search(new_state, depth - 1, -beta, -alpha)
```

**Expected improvement:** Can reach 1-2 ply deeper

---

## 🚫 What NOT to Do

1. **Don't mix evaluation functions** - Breaks alpha-beta
2. **Don't optimize without profiling** - Optimize the bottleneck
3. **Don't sacrifice correctness for speed** - Fast wrong answer is useless
4. **Don't skip testing** - Each optimization must be verified

---

## 📈 Expected Final Performance

With all optimizations:
- **Iterative deepening:** 1.2x faster (7.6s)
- **History heuristic:** 1.1x faster (6.9s)
- **Null move pruning:** 1.3x faster (5.3s)
- **Quiescence search:** Similar speed, better quality
- **LMR:** Can reach depth 4 in same time

**Target:** Depth 3 in ~5 seconds, or depth 4 in ~10 seconds

---

## 🔧 Implementation Order

1. ✅ **Revert broken changes** - DONE
2. ✅ **Keep killer moves** - DONE
3. ⏳ **Implement iterative deepening** - NEXT
4. ⏳ **Add history heuristic**
5. ⏳ **Implement quiescence search**
6. ⏳ **Add null move pruning**
7. ⏳ **Test and benchmark**

---

## 💡 Key Lessons

1. **Consistency is critical** - Alpha-beta requires monotonic evaluation
2. **Move ordering is king** - Better ordering = more cutoffs = faster search
3. **Standard techniques exist** - Use proven chess engine techniques
4. **Test incrementally** - Add one optimization at a time
5. **Profile first** - Know where the time is spent

---

## 📚 References

- **Chessprogramming Wiki:** https://www.chessprogramming.org/
- **Alpha-Beta Pruning:** https://www.chessprogramming.org/Alpha-Beta
- **Move Ordering:** https://www.chessprogramming.org/Move_Ordering
- **Iterative Deepening:** https://www.chessprogramming.org/Iterative_Deepening
- **Null Move Pruning:** https://www.chessprogramming.org/Null_Move_Pruning
- **Quiescence Search:** https://www.chessprogramming.org/Quiescence_Search

