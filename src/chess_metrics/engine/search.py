from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple, Dict
from functools import lru_cache
from .types import GameState, Move, WHITE, BLACK, opposite
from .movegen import generate_legal_moves
from .metrics import compute_metrics, deltas, Metrics
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

# Global transposition table (now using Zobrist hash keys)
_transposition_table: Dict[int, Tuple['SearchResult', int]] = {}

# Metrics cache using Zobrist hashing
_metrics_cache: Dict[int, Metrics] = {}

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
    global _transposition_table, _metrics_cache
    _transposition_table.clear()
    _metrics_cache.clear()

@profile_function
def cached_compute_metrics(hash_key: int, state: GameState) -> Metrics:
    """
    Cache metrics computation using Zobrist hash.

    This is much faster than FEN-based caching:
    - No string allocation/comparison
    - O(1) hash lookup vs string comparison
    - Hash computation is ~10x faster than FEN generation
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

def move_priority(state: GameState, move: Move) -> int:
    priority = 0
    
    # Captures get higher priority
    if state.board[move.to_sq] != 0:
        captured_piece = abs(state.board[move.to_sq])
        moving_piece = abs(state.board[move.from_sq])
        # MVV-LVA: Most Valuable Victim - Least Valuable Attacker
        priority += captured_piece * 100 - moving_piece
    
    # Castling moves
    if abs(move.from_sq - move.to_sq) == 2 and abs(state.board[move.from_sq]) == 6:  # King moves 2 squares
        priority += 100

    # Promotions
    if move.is_promotion:
        priority += 500

    # Checks get medium priority (if you have check detection)
    # if gives_check(state, move):
    #     priority += 50
    
    return -priority

def minimax_scoreS(state: GameState, profile: Profile, root_side: int, depth: int, alpha: float, beta: float) -> SearchResult:
    # Use Zobrist hash as position key (much faster than FEN)
    hash_key = zobrist_hash(state)

    # Check transposition table
    if hash_key in _transposition_table:
        cached_result, cached_depth = _transposition_table[hash_key]
        if cached_depth >= depth:
            return cached_result

    if depth == 0:
        with profile_section("cached_compute_metrics"):
            m = cached_compute_metrics(hash_key, state)
        result = SearchResult(score_s(m, profile, root_side), m)
        _transposition_table[hash_key] = (result, depth)
        return result

    side = state.side_to_move
    with profile_section("generate_legal_moves"):
        legal = generate_legal_moves(state, side)

    if not legal:
        # terminal
        if is_in_check(state, side):
            # side to move is mated
            v = -MATE if side == root_side else +MATE
            with profile_section("cached_compute_metrics"):
                m = cached_compute_metrics(hash_key, state)
            result = SearchResult(v, m)
        else:
            with profile_section("cached_compute_metrics"):
                m = cached_compute_metrics(hash_key, state)
            result = SearchResult(0.0, m)
        _transposition_table[hash_key] = (result, depth)
        return result

    # Move ordering for better alpha-beta pruning
    with profile_section("move_ordering"):
        legal.sort(key=lambda mv: move_priority(state, mv))

    maximizing = (side == root_side)

    # Initialize best_leaf with current position metrics as fallback
    current_metrics = cached_compute_metrics(hash_key, state)

    if maximizing:
        best = -1e30
        best_leaf = current_metrics
        for mv in legal:
            u = apply_move(state, mv)
            res = minimax_scoreS(state, profile, root_side, depth-1, alpha, beta)
            undo_move(state, u)

            if res.scoreS > best:
                best = res.scoreS
                best_leaf = res.leaf_metrics

            alpha = max(alpha, best)
            if beta <= alpha:
                break

        result = SearchResult(best, best_leaf)
        _transposition_table[hash_key] = (result, depth)
        return result
    else:
        best = +1e30
        best_leaf = current_metrics
        for mv in legal:
            u = apply_move(state, mv)
            res = minimax_scoreS(state, profile, root_side, depth-1, alpha, beta)
            undo_move(state, u)

            if res.scoreS < best:
                best = res.scoreS
                best_leaf = res.leaf_metrics

            beta = min(beta, best)
            if beta <= alpha:
                break

        result = SearchResult(best, best_leaf)
        _transposition_table[hash_key] = (result, depth)
        return result

@profile_function
def choose_best_move(state: GameState, profile: Profile, depthN: int = 3) -> Optional[Move]:
    root_side = state.side_to_move

    with profile_section("choose_best_move:generate_legal_moves"):
        legal = generate_legal_moves(state, root_side)

    if not legal:
        return None

    with profile_section("choose_best_move:compute_root_metrics"):
        root_hash = zobrist_hash(state)
        root_metrics = cached_compute_metrics(root_hash, state)
        root_dPV, _, root_dOV, _ = deltas(root_metrics)

    best_mv = None
    best_key = None  # tuple(safety_adjusted_score, scoreS, dPV_swing, dOV_swing, uci)

    with profile_section("choose_best_move:evaluate_moves"):
        for mv in legal:
            # Evaluate material safety BEFORE applying the move
            with profile_section("choose_best_move:material_safety"):
                safety_score = evaluate_material_safety(state, mv)

            u = apply_move(state, mv)
            res = minimax_scoreS(state, profile, root_side, depthN-1, -1e30, +1e30)
            undo_move(state, u)

            leaf_dPV, _, leaf_dOV, _ = deltas(res.leaf_metrics)
            dPV_swing = leaf_dPV - root_dPV
            dOV_swing = leaf_dOV - root_dOV

            # Apply material safety adjustment to the score
            # Material safety is CRITICAL - weight it heavily
            SAFETY_WEIGHT = 10.0

            # Profile-specific safety adjustments
            if profile.name == "materialist":
                SAFETY_WEIGHT = 15.0
            elif profile.name == "offense-first":
                SAFETY_WEIGHT = 7.0
            elif profile.name == "defense-first":
                SAFETY_WEIGHT = 12.0

            # Calculate safety-adjusted score
            safety_adjusted_score = res.scoreS + (safety_score * SAFETY_WEIGHT)

            # Hard veto: Never lose 5+ points without compensation
            if safety_score < -5.0:
                if not has_adequate_compensation(state, mv, abs(safety_score)):
                    # Massive penalty - effectively veto this move
                    safety_adjusted_score = -MATE / 2

            # deterministic: UCI ascending, but tie-breaker wants stable order after other keys
            uci = mv.uci()

            if best_key is None:
                best_mv = mv
                best_key = (safety_adjusted_score, res.scoreS, dPV_swing, dOV_swing, uci)
            else:
                cand = (safety_adjusted_score, res.scoreS, dPV_swing, dOV_swing, uci)
                if cand > best_key:
                    best_mv = mv
                    best_key = cand

    return best_mv
