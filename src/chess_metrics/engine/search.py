from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
from .types import GameState, Move, WHITE, BLACK, opposite
from .movegen import generate_legal_moves
from .metrics import compute_metrics, deltas, Metrics
from .rules import is_in_check
from .apply import apply_move, undo_move

MATE = 10**9

@dataclass(frozen=True)
class Profile:
    name: str
    wPV: float = 1.0
    wMV: float = 1.0
    wOV: float = 1.0
    wDV: float = 1.0

def score(metrics: Metrics, profile: Profile) -> float:
    dPV, dMV, dOV, dDV = deltas(metrics)
    return profile.wPV*dPV + profile.wMV*dMV + profile.wOV*dOV + profile.wDV*dDV

def score_s(metrics: Metrics, profile: Profile, root_side: int) -> float:
    s = score(metrics, profile)
    return s if root_side == WHITE else -s

@dataclass
class SearchResult:
    scoreS: float
    leaf_metrics: Metrics

def minimax_scoreS(state: GameState, profile: Profile, root_side: int, depth: int, alpha: float, beta: float) -> SearchResult:
    if depth == 0:
        m = compute_metrics(state)
        return SearchResult(score_s(m, profile, root_side), m)

    side = state.side_to_move
    legal = generate_legal_moves(state, side)

    if not legal:
        # terminal
        if is_in_check(state, side):
            # side to move is mated
            v = -MATE if side == root_side else +MATE
            m = compute_metrics(state)
            return SearchResult(v, m)
        else:
            m = compute_metrics(state)
            return SearchResult(0.0, m)

    maximizing = (side == root_side)

    if maximizing:
        best = -1e30
        best_leaf = None
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
        return SearchResult(best, best_leaf)
    else:
        best = +1e30
        best_leaf = None
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
        return SearchResult(best, best_leaf)

def choose_best_move(state: GameState, profile: Profile, depthN: int = 3) -> Optional[Move]:
    root_side = state.side_to_move
    legal = generate_legal_moves(state, root_side)
    if not legal:
        return None

    root_metrics = compute_metrics(state)
    root_dPV, _, root_dOV, _ = deltas(root_metrics)

    best_mv = None
    best_key = None  # tuple(scoreS, dPV_swing, dOV_swing, uciNeg)

    for mv in legal:
        u = apply_move(state, mv)
        res = minimax_scoreS(state, profile, root_side, depthN-1, -1e30, +1e30)
        undo_move(state, u)

        leaf_dPV, _, leaf_dOV, _ = deltas(res.leaf_metrics)
        dPV_swing = leaf_dPV - root_dPV
        dOV_swing = leaf_dOV - root_dOV

        # deterministic: UCI ascending, but tie-breaker wants stable order after other keys
        uci = mv.uci()

        key = (res.scoreS, dPV_swing, dOV_swing, -hash(uci))  # hash stable within run; used only last
        # better deterministic: compare UCI lex directly as last stage
        if best_key is None:
            best_mv = mv
            best_key = (res.scoreS, dPV_swing, dOV_swing, uci)
        else:
            cand = (res.scoreS, dPV_swing, dOV_swing, uci)
            if cand > best_key:
                best_mv = mv
                best_key = cand

    return best_mv
