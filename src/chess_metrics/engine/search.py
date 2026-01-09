from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, Dict
from functools import lru_cache
from .types import GameState, Move, WHITE, BLACK, opposite
from .movegen import generate_legal_moves
from .metrics import compute_metrics, compute_metrics_fast, deltas, Metrics
from .rules import is_in_check
from .apply import apply_move, undo_move
from .fen import to_fen, parse_fen
from .zobrist import zobrist_hash
from .material_safety import evaluate_material_safety, has_adequate_compensation

# Import profiling utilities
try:
    from chess_metrics.web.profiling import profile_function, profile_section
except ImportError:
    # Fallback if profiling module not available
    def profile_function(func):
        return func
    def profile_section(name):
        class DummyContext:
            def __enter__(self): return self
            def __exit__(self, *args): pass
        return DummyContext()

MATE = 10**9

# Transposition table entry with bound types and best move
@dataclass
class TTEntry:
    score: float
    depth: int
    bound_type: str  # 'exact', 'lower', 'upper'
    best_move: Optional[Tuple[int, int]]  # (from_sq, to_sq)
    leaf_metrics: Metrics

# Global transposition table (now using Zobrist hash keys with improved entries)
_transposition_table: Dict[int, TTEntry] = {}
MAX_TT_SIZE = 1_000_000  # Limit cache size to prevent memory issues

# Metrics cache using Zobrist hashing
_metrics_cache: Dict[int, Metrics] = {}

# Killer moves: store 2 killer moves per ply (depth level)
# Killer moves are non-capture moves that caused beta cutoffs
_killer_moves: Dict[int, list[Tuple[int, int]]] = {}  # ply -> [(from_sq, to_sq), ...]
MAX_KILLERS_PER_PLY = 2

# History heuristic: track moves that cause cutoffs across the entire search tree
# Maps (from_sq, to_sq) -> score. Higher score = move caused more cutoffs
_history_scores: Dict[Tuple[int, int], int] = {}

@dataclass(frozen=True)
class Profile:
    name: str
    wPV: float = 1.0
    wMV: float = 1.0
    wOV: float = 1.0
    wDV: float = 1.0

@dataclass
class SearchResult:
    scoreS: float
    leaf_metrics: Metrics

def clear_transposition_table():
    """Clear the transposition table between games."""
    global _transposition_table, _metrics_cache, _killer_moves, _history_scores
    _transposition_table.clear()
    _metrics_cache.clear()
    _killer_moves.clear()
    _history_scores.clear()

def store_tt(hash_key: int, score: float, depth: int, bound_type: str,
             best_move: Optional[Tuple[int, int]], metrics: Metrics):
    """
    Store position in transposition table with depth-preferred replacement.

    Args:
        hash_key: Zobrist hash of the position
        score: Evaluation score
        depth: Search depth
        bound_type: 'exact', 'lower', or 'upper'
        best_move: Best move found (from_sq, to_sq)
        metrics: Leaf metrics
    """
    global _transposition_table

    if hash_key in _transposition_table:
        old_entry = _transposition_table[hash_key]
        # Keep deeper searches (they're more accurate)
        if old_entry.depth > depth:
            return

    # Limit table size to prevent memory issues
    if len(_transposition_table) >= MAX_TT_SIZE:
        # Simple replacement: remove first entry (could be improved with LRU)
        _transposition_table.pop(next(iter(_transposition_table)))

    _transposition_table[hash_key] = TTEntry(score, depth, bound_type, best_move, metrics)

def probe_tt(hash_key: int, depth: int, alpha: float, beta: float) -> Optional[SearchResult]:
    """
    Probe transposition table with bound checking.

    Args:
        hash_key: Zobrist hash of the position
        depth: Current search depth
        alpha: Alpha bound
        beta: Beta bound

    Returns:
        SearchResult if we can use the cached value, None otherwise
    """
    if hash_key not in _transposition_table:
        return None

    entry = _transposition_table[hash_key]

    # Only use entries from searches at least as deep as current
    if entry.depth < depth:
        return None

    # Check if we can use this entry based on bound type
    if entry.bound_type == 'exact':
        return SearchResult(entry.score, entry.leaf_metrics)
    elif entry.bound_type == 'lower' and entry.score >= beta:
        return SearchResult(entry.score, entry.leaf_metrics)
    elif entry.bound_type == 'upper' and entry.score <= alpha:
        return SearchResult(entry.score, entry.leaf_metrics)

    return None

def get_pv_move(hash_key: int) -> Optional[Tuple[int, int]]:
    """Get the principal variation (best) move from transposition table."""
    if hash_key in _transposition_table:
        return _transposition_table[hash_key].best_move
    return None

@profile_function
def cached_compute_metrics(hash_key: int, state: GameState) -> Metrics:
    """
    Cache metrics computation using Zobrist hash.

    This is much faster than FEN-based caching:
    - No string allocation/comparison
    - O(1) hash lookup vs string comparison
    - Hash computation is ~10x faster than FEN generation

    Args:
        hash_key: Zobrist hash of the position
        state: Game state
    """
    if hash_key not in _metrics_cache:
        _metrics_cache[hash_key] = compute_metrics(state)
    return _metrics_cache[hash_key]

def score(metrics: Metrics, profile: Profile) -> float:
    dPV, dMV, dOV, dDV = deltas(metrics)
    return profile.wPV*dPV + profile.wMV*dMV + profile.wOV*dOV + profile.wDV*dDV

def score_s(metrics: Metrics, profile: Profile, root_side: int) -> float:
    s = score(metrics, profile)
    return s if root_side == WHITE else -s

def evaluate_move_with_safety(state: GameState, move: Move, metrics: Metrics,
                               profile: Profile, root_side: int) -> float:
    """
    Evaluate a move considering both positional metrics and material safety.

    This prevents the AI from making obvious blunders like:
    - Losing the queen for no compensation
    - Leaving pieces hanging
    - Moving into attacks without defense

    Args:
        state: Current game state (before move)
        move: Move to evaluate
        metrics: Metrics after the move
        profile: AI profile
        root_side: Side making the root move

    Returns:
        Combined score (positional + safety)
    """
    # Calculate base positional score
    positional_score = score_s(metrics, profile, root_side)

    # Evaluate material safety
    safety_score = evaluate_material_safety(state, move)

    # Material safety is CRITICAL - weight it heavily
    # A safety score of -9 (hanging queen) should override most positional gains
    SAFETY_WEIGHT = 10.0

    # Profile-specific safety adjustments
    if profile.name == "materialist":
        # Materialists are extra cautious about material
        SAFETY_WEIGHT = 15.0
    elif profile.name == "offense-first":
        # Offense-first can take calculated risks
        # But still shouldn't sacrifice queen for nothing
        SAFETY_WEIGHT = 7.0
    elif profile.name == "defense-first":
        # Defense-first is very cautious
        SAFETY_WEIGHT = 12.0

    # Combined score
    total_score = positional_score + (safety_score * SAFETY_WEIGHT)

    # Hard veto: Never lose 5+ points without compensation
    if safety_score < -5.0:
        # Check if there's adequate compensation
        if not has_adequate_compensation(state, move, abs(safety_score)):
            # Massive penalty - effectively veto this move
            total_score = -MATE / 2

    return total_score

def move_priority(state: GameState, move: Move, ply: int = 0, pv_move: Optional[Tuple[int, int]] = None) -> int:
    """
    Calculate move priority for move ordering.
    Higher priority moves are searched first for better alpha-beta pruning.

    Priority order:
    1. PV move from transposition table (10000)
    2. Promotions (500+)
    3. Captures (MVV-LVA: 100-900)
    4. Killer moves (50)
    5. Castling (40)
    6. History heuristic (0-49)
    7. Other moves (0)
    """
    priority = 0

    # PV move gets highest priority (from transposition table)
    if pv_move and (move.from_sq, move.to_sq) == pv_move:
        priority += 10000

    # Promotions get highest priority
    if move.is_promotion:
        priority += 500

    # Captures get high priority (MVV-LVA)
    elif state.board[move.to_sq] != 0:
        captured_piece = abs(state.board[move.to_sq])
        moving_piece = abs(state.board[move.from_sq])
        # MVV-LVA: Most Valuable Victim - Least Valuable Attacker
        priority += captured_piece * 100 - moving_piece

    # Killer moves (non-captures that caused cutoffs)
    elif ply in _killer_moves:
        move_key = (move.from_sq, move.to_sq)
        if move_key in _killer_moves[ply]:
            priority += 50

    # History heuristic: add score based on how often this move caused cutoffs
    move_key = (move.from_sq, move.to_sq)
    if move_key in _history_scores:
        # Scale history score to fit in priority range (0-49 to not overlap with killers)
        # Cap at 49 to keep below killer move priority
        history_bonus = min(_history_scores[move_key] // 100, 49)
        priority += history_bonus

    # Castling moves
    if abs(move.from_sq - move.to_sq) == 2 and abs(state.board[move.from_sq]) == 6:  # King moves 2 squares
        priority += 40

    return -priority  # Negative because we sort ascending

def quiescence_search(state: GameState, profile: Profile, root_side: int, alpha: float, beta: float, ply: int, max_depth: int = 6) -> SearchResult:
    """
    Quiescence search: continue searching captures until position is "quiet".

    This avoids the horizon effect where we stop searching right before
    a capture that would drastically change the evaluation.

    Args:
        state: Current game state
        profile: Evaluation profile
        root_side: The side we're maximizing for
        alpha: Alpha bound
        beta: Beta bound
        ply: Current ply depth (for limiting search)
        max_depth: Maximum additional plies to search in quiescence (default: 6)

    Returns:
        SearchResult with evaluation and leaf metrics
    """
    hash_key = zobrist_hash(state)

    # Stand pat: evaluate the current position
    # This gives us a baseline - we can always choose not to capture
    with profile_section("cached_compute_metrics"):
        m = cached_compute_metrics(hash_key, state)
    stand_pat_score = score_s(m, profile, root_side)

    side = state.side_to_move
    maximizing = (side == root_side)

    if maximizing:
        if stand_pat_score >= beta:
            # Position is already too good - beta cutoff
            return SearchResult(beta, m)
        if stand_pat_score > alpha:
            alpha = stand_pat_score
    else:
        if stand_pat_score <= alpha:
            # Position is already too bad - alpha cutoff
            return SearchResult(alpha, m)
        if stand_pat_score < beta:
            beta = stand_pat_score

    # Stop if we've searched too deep in quiescence
    if ply >= max_depth:
        return SearchResult(stand_pat_score, m)

    # Generate only capture moves for quiescence
    legal = generate_legal_moves(state, side)
    captures = [mv for mv in legal if mv.is_capture]

    # If no captures, position is quiet - return stand pat score
    if not captures:
        return SearchResult(stand_pat_score, m)

    # Sort captures by MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
    # This ensures we search the most promising captures first
    captures.sort(key=lambda mv: move_priority(state, mv, ply))

    # Delta pruning: don't search captures that can't possibly improve alpha
    # If even capturing a queen can't improve our position, skip quiescence
    DELTA_MARGIN = 9.0  # Queen value
    if maximizing and stand_pat_score + DELTA_MARGIN < alpha:
        return SearchResult(stand_pat_score, m)
    if not maximizing and stand_pat_score - DELTA_MARGIN > beta:
        return SearchResult(stand_pat_score, m)

    best_score = stand_pat_score
    best_metrics = m

    if maximizing:
        for mv in captures:
            # SEE (Static Exchange Evaluation) pruning: skip obviously bad captures
            # If we're capturing a pawn with a queen, it's probably bad
            if mv.captured_kind > 0 and mv.moving_kind > mv.captured_kind + 2:
                # Skip if we're using a much more valuable piece to capture
                # (e.g., Queen captures Pawn is usually bad unless there's a tactic)
                continue

            u = apply_move(state, mv)
            res = quiescence_search(state, profile, root_side, alpha, beta, ply + 1, max_depth)
            undo_move(state, u)

            if res.scoreS > best_score:
                best_score = res.scoreS
                best_metrics = res.leaf_metrics

            alpha = max(alpha, best_score)
            if beta <= alpha:
                break  # Beta cutoff

        return SearchResult(best_score, best_metrics)
    else:
        for mv in captures:
            # SEE pruning for minimizing side
            if mv.captured_kind > 0 and mv.moving_kind > mv.captured_kind + 2:
                continue

            u = apply_move(state, mv)
            res = quiescence_search(state, profile, root_side, alpha, beta, ply + 1, max_depth)
            undo_move(state, u)

            if res.scoreS < best_score:
                best_score = res.scoreS
                best_metrics = res.leaf_metrics

            beta = min(beta, best_score)
            if beta <= alpha:
                break  # Alpha cutoff

        return SearchResult(best_score, best_metrics)


def minimax_scoreS(state: GameState, profile: Profile, root_side: int, depth: int, alpha: float, beta: float, ply: int = 0, allow_null: bool = True) -> SearchResult:
    """
    Alpha-beta minimax search with optimizations:
    - Transposition table with bound types
    - Null move pruning
    - PV move ordering
    - Late move reduction
    - Futility pruning
    """
    # Use Zobrist hash as position key (much faster than FEN)
    hash_key = zobrist_hash(state)

    # Probe transposition table with improved bound checking
    tt_result = probe_tt(hash_key, depth, alpha, beta)
    if tt_result is not None:
        return tt_result

    if depth == 0:
        # At depth 0, enter quiescence search to avoid horizon effect
        result = quiescence_search(state, profile, root_side, alpha, beta, ply=0, max_depth=6)
        store_tt(hash_key, result.scoreS, depth, 'exact', None, result.leaf_metrics)
        return result

    side = state.side_to_move
    maximizing = (side == root_side)

    # Initialize current metrics for evaluation
    current_metrics = cached_compute_metrics(hash_key, state)

    # Null Move Pruning: if doing nothing is already too good, skip this position
    if allow_null and depth >= 3 and not is_in_check(state, side):
        # Try doing nothing (null move)
        state.side_to_move = opposite(side)
        null_result = minimax_scoreS(state, profile, root_side, depth - 3, -beta, -beta + 1, ply + 1, allow_null=False)
        state.side_to_move = side

        if maximizing and -null_result.scoreS >= beta:
            # Null move caused beta cutoff
            store_tt(hash_key, beta, depth, 'lower', None, current_metrics)
            return SearchResult(beta, current_metrics)
        elif not maximizing and -null_result.scoreS <= alpha:
            # Null move caused alpha cutoff
            store_tt(hash_key, alpha, depth, 'upper', None, current_metrics)
            return SearchResult(alpha, current_metrics)

    # Futility Pruning: at low depths, skip if position is hopeless
    if depth <= 2 and not is_in_check(state, side):
        static_eval = score_s(current_metrics, profile, root_side)
        futility_margin = 3.0 * depth  # Adjust based on testing

        if maximizing and static_eval + futility_margin < alpha:
            # Even with optimistic bonus, can't reach alpha
            store_tt(hash_key, static_eval, depth, 'upper', None, current_metrics)
            return SearchResult(static_eval, current_metrics)
        elif not maximizing and static_eval - futility_margin > beta:
            store_tt(hash_key, static_eval, depth, 'lower', None, current_metrics)
            return SearchResult(static_eval, current_metrics)

    with profile_section("generate_legal_moves"):
        legal = generate_legal_moves(state, side)

    if not legal:
        # Terminal position
        if is_in_check(state, side):
            # Checkmate
            v = -MATE if side == root_side else +MATE
            result = SearchResult(v, current_metrics)
        else:
            # Stalemate
            result = SearchResult(0.0, current_metrics)
        store_tt(hash_key, result.scoreS, depth, 'exact', None, result.leaf_metrics)
        return result

    # PV Move Ordering: get best move from transposition table
    pv_move = get_pv_move(hash_key)

    # Move ordering for better alpha-beta pruning
    with profile_section("move_ordering"):
        legal.sort(key=lambda mv: move_priority(state, mv, ply, pv_move))

    # Search all moves
    best_score = -1e30 if maximizing else +1e30
    best_leaf = current_metrics
    best_move = None
    original_alpha = alpha

    if maximizing:
        for move_idx, mv in enumerate(legal):
            u = apply_move(state, mv)

            # Late Move Reduction: search later moves at reduced depth
            # Skip LMR for: first few moves, captures, promotions, checks
            if (move_idx >= 4 and depth >= 3 and
                not mv.is_capture and not mv.is_promotion and
                not is_in_check(state, opposite(side))):
                # Search with reduced depth first
                res = minimax_scoreS(state, profile, root_side, depth - 2, alpha, beta, ply + 1)

                # If it looks promising, re-search at full depth
                if res.scoreS > alpha:
                    res = minimax_scoreS(state, profile, root_side, depth - 1, alpha, beta, ply + 1)
            else:
                # Search first few moves and tactical moves at full depth
                res = minimax_scoreS(state, profile, root_side, depth - 1, alpha, beta, ply + 1)

            undo_move(state, u)

            if res.scoreS > best_score:
                best_score = res.scoreS
                best_leaf = res.leaf_metrics
                best_move = (mv.from_sq, mv.to_sq)

            alpha = max(alpha, best_score)
            if beta <= alpha:
                # Beta cutoff - store killer move and history
                if not mv.is_capture and not mv.is_promotion:
                    move_key = (mv.from_sq, mv.to_sq)
                    if ply not in _killer_moves:
                        _killer_moves[ply] = []
                    if move_key not in _killer_moves[ply]:
                        _killer_moves[ply].insert(0, move_key)
                        if len(_killer_moves[ply]) > MAX_KILLERS_PER_PLY:
                            _killer_moves[ply].pop()

                    history_bonus = depth * depth
                    if move_key in _history_scores:
                        _history_scores[move_key] += history_bonus
                    else:
                        _history_scores[move_key] = history_bonus

                # Store as lower bound (beta cutoff)
                store_tt(hash_key, best_score, depth, 'lower', best_move, best_leaf)
                return SearchResult(best_score, best_leaf)

        # Determine bound type
        if best_score <= original_alpha:
            bound_type = 'upper'  # All moves failed low
        else:
            bound_type = 'exact'  # Found exact score

        store_tt(hash_key, best_score, depth, bound_type, best_move, best_leaf)
        return SearchResult(best_score, best_leaf)
    else:
        original_beta = beta

        for move_idx, mv in enumerate(legal):
            u = apply_move(state, mv)

            # Late Move Reduction for minimizing player
            if (move_idx >= 4 and depth >= 3 and
                not mv.is_capture and not mv.is_promotion and
                not is_in_check(state, opposite(side))):
                # Search with reduced depth first
                res = minimax_scoreS(state, profile, root_side, depth - 2, alpha, beta, ply + 1)

                # If it looks promising, re-search at full depth
                if res.scoreS < beta:
                    res = minimax_scoreS(state, profile, root_side, depth - 1, alpha, beta, ply + 1)
            else:
                # Search first few moves and tactical moves at full depth
                res = minimax_scoreS(state, profile, root_side, depth - 1, alpha, beta, ply + 1)

            undo_move(state, u)

            if res.scoreS < best_score:
                best_score = res.scoreS
                best_leaf = res.leaf_metrics
                best_move = (mv.from_sq, mv.to_sq)

            beta = min(beta, best_score)
            if beta <= alpha:
                # Alpha cutoff - store killer move and history
                if not mv.is_capture and not mv.is_promotion:
                    move_key = (mv.from_sq, mv.to_sq)
                    if ply not in _killer_moves:
                        _killer_moves[ply] = []
                    if move_key not in _killer_moves[ply]:
                        _killer_moves[ply].insert(0, move_key)
                        if len(_killer_moves[ply]) > MAX_KILLERS_PER_PLY:
                            _killer_moves[ply].pop()

                    history_bonus = depth * depth
                    if move_key in _history_scores:
                        _history_scores[move_key] += history_bonus
                    else:
                        _history_scores[move_key] = history_bonus

                # Store as upper bound (alpha cutoff)
                store_tt(hash_key, best_score, depth, 'upper', best_move, best_leaf)
                return SearchResult(best_score, best_leaf)

        # Determine bound type
        if best_score >= original_beta:
            bound_type = 'lower'  # All moves failed high
        else:
            bound_type = 'exact'  # Found exact score

        store_tt(hash_key, best_score, depth, bound_type, best_move, best_leaf)
        return SearchResult(best_score, best_leaf)

def choose_best_move_at_depth(state: GameState, profile: Profile, depthN: int, move_order: Optional[list[Move]] = None) -> tuple[Optional[Move], list[Move]]:
    """
    Choose best move at a specific depth.

    Returns:
        (best_move, ordered_moves) - best move and moves ordered by score for next iteration
    """
    root_side = state.side_to_move

    legal = generate_legal_moves(state, root_side)
    if not legal:
        return None, []

    # Use provided move ordering from previous iteration, or default ordering
    if move_order:
        # Reorder legal moves to match the provided order
        move_set = set((m.from_sq, m.to_sq) for m in legal)
        ordered = []
        for m in move_order:
            if (m.from_sq, m.to_sq) in move_set:
                ordered.append(m)
        # Add any new moves not in the previous order
        ordered_set = set((m.from_sq, m.to_sq) for m in ordered)
        for m in legal:
            if (m.from_sq, m.to_sq) not in ordered_set:
                ordered.append(m)
        legal = ordered

    root_hash = zobrist_hash(state)
    root_metrics = cached_compute_metrics(root_hash, state)
    root_dPV, _, root_dOV, _ = deltas(root_metrics)

    best_mv = None
    best_key = None
    move_scores = []  # (score, move) for ordering next iteration

    for mv in legal:
        safety_score = evaluate_material_safety(state, mv)

        u = apply_move(state, mv)
        res = minimax_scoreS(state, profile, root_side, depthN-1, -1e30, +1e30, ply=1)
        undo_move(state, u)

        leaf_dPV, _, leaf_dOV, _ = deltas(res.leaf_metrics)
        dPV_swing = leaf_dPV - root_dPV
        dOV_swing = leaf_dOV - root_dOV

        SAFETY_WEIGHT = 10.0
        if profile.name == "materialist":
            SAFETY_WEIGHT = 15.0
        elif profile.name == "offense-first":
            SAFETY_WEIGHT = 7.0
        elif profile.name == "defense-first":
            SAFETY_WEIGHT = 12.0

        safety_adjusted_score = res.scoreS + (safety_score * SAFETY_WEIGHT)

        if safety_score < -5.0:
            if not has_adequate_compensation(state, mv, abs(safety_score)):
                safety_adjusted_score = -MATE / 2

        uci = mv.uci()
        cand = (safety_adjusted_score, res.scoreS, dPV_swing, dOV_swing, uci)

        move_scores.append((safety_adjusted_score, mv))

        if best_key is None or cand > best_key:
            best_mv = mv
            best_key = cand

    # Sort moves by score for next iteration (best first)
    move_scores.sort(reverse=True, key=lambda x: x[0])
    ordered_moves = [mv for _, mv in move_scores]

    return best_mv, ordered_moves

def choose_best_move_at_depth_windowed(state: GameState, profile: Profile, depth: int,
                                       move_order: Optional[list[Move]],
                                       alpha: float, beta: float) -> tuple[Optional[Move], list[Move], float]:
    """
    Choose best move at a specific depth with aspiration window.

    Returns:
        (best_move, ordered_moves, score) - best move, moves ordered by score, and best score
    """
    root_side = state.side_to_move
    legal = generate_legal_moves(state, root_side)

    if not legal:
        return None, [], 0.0

    if move_order:
        legal = move_order + [mv for mv in legal if mv not in move_order]
    else:
        hash_key = zobrist_hash(state)
        pv_move = get_pv_move(hash_key)
        legal.sort(key=lambda mv: move_priority(state, mv, 0, pv_move))

    best_mv = None
    best_score = -1e30
    move_scores = []

    for mv in legal:
        u = apply_move(state, mv)
        res = minimax_scoreS(state, profile, root_side, depth - 1, alpha, beta, ply=1)
        undo_move(state, u)

        move_scores.append((res.scoreS, mv))

        if res.scoreS > best_score:
            best_score = res.scoreS
            best_mv = mv
            alpha = max(alpha, best_score)

    move_scores.sort(reverse=True, key=lambda x: x[0])
    ordered_moves = [mv for _, mv in move_scores]

    return best_mv, ordered_moves, best_score

@profile_function
def choose_best_move(state: GameState, profile: Profile, depthN: int = 3, use_iterative_deepening: bool = True) -> Optional[Move]:
    """
    Choose the best move using iterative deepening with aspiration windows.

    Iterative deepening searches depth 1, 2, 3, ... up to depthN.
    Benefits:
    - Better move ordering from shallow searches improves pruning
    - Aspiration windows narrow the search window for faster cutoffs
    - Can return best move found so far if interrupted
    - Minimal overhead due to exponential growth of search tree

    Args:
        state: Current game state
        profile: Evaluation profile
        depthN: Maximum depth to search
        use_iterative_deepening: If False, search only at depthN (for testing)
    """
    if not use_iterative_deepening:
        # Direct search at target depth (old behavior)
        best_mv, _ = choose_best_move_at_depth(state, profile, depthN)
        return best_mv

    # Iterative deepening with aspiration windows
    best_move = None
    move_order = None
    prev_score = 0.0

    for depth in range(1, depthN + 1):
        if depth == 1:
            # First iteration: use full window
            best_move, move_order, prev_score = choose_best_move_at_depth_windowed(
                state, profile, depth, move_order, -1e30, 1e30)
        else:
            # Use aspiration window based on previous score
            window = 0.5  # Narrow window
            alpha, beta = prev_score - window, prev_score + window

            # Try narrow window first
            best_move, move_order, score = choose_best_move_at_depth_windowed(
                state, profile, depth, move_order, alpha, beta)

            # If search failed (score outside window), re-search with full window
            if score <= alpha or score >= beta:
                # Failed low or high - re-search with wider window
                window = 2.0
                alpha, beta = prev_score - window, prev_score + window
                best_move, move_order, score = choose_best_move_at_depth_windowed(
                    state, profile, depth, move_order, alpha, beta)

                # If still failed, use full window
                if score <= alpha or score >= beta:
                    best_move, move_order, score = choose_best_move_at_depth_windowed(
                        state, profile, depth, move_order, -1e30, 1e30)

            prev_score = score

        if best_move is None:
            break

    return best_move
