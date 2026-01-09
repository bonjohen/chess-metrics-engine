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

MATE = 10**9

# Global transposition table
_transposition_table: Dict[str, Tuple['SearchResult', int]] = {}

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
    global _transposition_table
    _transposition_table.clear()

@lru_cache(maxsize=10000)
def cached_compute_metrics(fen: str) -> Metrics:
    """Cache metrics computation by FEN string."""
    from .fen import parse_fen
    state = parse_fen(fen)
    return compute_metrics(state)

def score(metrics: Metrics, profile: Profile) -> float:
    dPV, dMV, dOV, dDV = deltas(metrics)
    return profile.wPV*dPV + profile.wMV*dMV + profile.wOV*dOV + profile.wDV*dDV

def score_s(metrics: Metrics, profile: Profile, root_side: int) -> float:
    s = score(metrics, profile)
    return s if root_side == WHITE else -s

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
    # Use FEN as position key for transposition table
    fen_key = to_fen(state)
    
    # Check transposition table
    if fen_key in _transposition_table:
        cached_result, cached_depth = _transposition_table[fen_key]
        if cached_depth >= depth:
            return cached_result
    
    if depth == 0:
        m = cached_compute_metrics(fen_key)
        result = SearchResult(score_s(m, profile, root_side), m)
        _transposition_table[fen_key] = (result, depth)
        return result

    side = state.side_to_move
    legal = generate_legal_moves(state, side)

    if not legal:
        # terminal
        if is_in_check(state, side):
            # side to move is mated
            v = -MATE if side == root_side else +MATE
            m = cached_compute_metrics(fen_key)
            result = SearchResult(v, m)
        else:
            m = cached_compute_metrics(fen_key)
            result = SearchResult(0.0, m)
        _transposition_table[fen_key] = (result, depth)
        return result

    # Move ordering for better alpha-beta pruning
    legal.sort(key=lambda mv: move_priority(state, mv))

    maximizing = (side == root_side)

    # Initialize best_leaf with current position metrics as fallback
    current_metrics = cached_compute_metrics(fen_key)

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
        _transposition_table[fen_key] = (result, depth)
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
        _transposition_table[fen_key] = (result, depth)
        return result

def choose_best_move(state: GameState, profile: Profile, depthN: int = 3) -> Optional[Move]:
    root_side = state.side_to_move
    legal = generate_legal_moves(state, root_side)
    if not legal:
        return None

    root_fen = to_fen(state)
    root_metrics = cached_compute_metrics(root_fen)
    root_dPV, _, root_dOV, _ = deltas(root_metrics)

    best_mv = None
    best_key = None  # tuple(scoreS, dPV_swing, dOV_swing, uci)

    for mv in legal:
        u = apply_move(state, mv)
        res = minimax_scoreS(state, profile, root_side, depthN-1, -1e30, +1e30)
        undo_move(state, u)

        leaf_dPV, _, leaf_dOV, _ = deltas(res.leaf_metrics)
        dPV_swing = leaf_dPV - root_dPV
        dOV_swing = leaf_dOV - root_dOV

        # deterministic: UCI ascending, but tie-breaker wants stable order after other keys
        uci = mv.uci()

        if best_key is None:
            best_mv = mv
            best_key = (res.scoreS, dPV_swing, dOV_swing, uci)
        else:
            cand = (res.scoreS, dPV_swing, dOV_swing, uci)
            if cand > best_key:
                best_mv = mv
                best_key = cand

    return best_mv
