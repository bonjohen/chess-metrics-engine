from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple
from .types import (
    GameState, WHITE, BLACK,
    PIECE_VALUE,
    piece_color, piece_kind, opposite
)
from .movegen import generate_legal_moves
from .rules import is_in_check, pseudo_attacks_square
from .apply import apply_move, undo_move
from .types import Move

@dataclass(frozen=True)
class Metrics:
    pv_w: int
    mv_w: int
    ov_w: int
    dv_w: float
    pv_b: int
    mv_b: int
    ov_b: int
    dv_b: float

def compute_pv(state: GameState, side: int) -> int:
    s = 0
    for p in state.board:
        if p != 0 and piece_color(p) == side:
            s += PIECE_VALUE[piece_kind(p)]
    return s

def compute_mv_ov(state: GameState, side: int) -> Tuple[int,int]:
    legal = generate_legal_moves(state, side)
    mv = 0
    ov = 0
    for m in legal:
        if m.is_ep:
            ov += 1  # victim pawn value
            continue
        if m.is_capture:
            ov += PIECE_VALUE[m.captured_kind]
        else:
            mv += 1  # non-capture to empty (includes castling, non-capture promotions)
    return mv, ov

def _apply_capture_like(state: GameState, from_sq: int, to_sq: int) -> Tuple[int,int,int]:
    # temporary: move piece from->to and remove piece on to (friendly) as if capture
    b = state.board
    moved = b[from_sq]
    captured = b[to_sq]
    b[to_sq] = moved
    b[from_sq] = 0
    return moved, captured, from_sq

def _undo_capture_like(state: GameState, from_sq: int, to_sq: int, moved: int, captured: int) -> None:
    b = state.board
    b[from_sq] = moved
    b[to_sq] = captured

def compute_dv(state: GameState, side: int) -> float:
    import math
    from .types import KING
    b = state.board
    dv = 0.0

    friendly_squares = [sq for sq, p in enumerate(b) if p != 0 and piece_color(p) == side]
    for t in friendly_squares:
        X = b[t]
        valueX = PIECE_VALUE[piece_kind(X)]

        # Skip if target is a king - we can't temporarily remove the king from the board
        # because is_in_check needs to find it
        if piece_kind(X) == KING:
            continue

        for f in friendly_squares:
            if f == t:
                continue
            A = b[f]
            # EP does not apply to DV by definition; DV is only about onto occupied friendly squares.
            if not pseudo_attacks_square(state, f, t):
                continue

            # Simulate capture-like move (A -> t, removing X) and check king safety.
            moved, captured, _ = _apply_capture_like(state, f, t)
            ok = not is_in_check(state, side)
            _undo_capture_like(state, f, t, moved, captured)

            if ok:
                # Use square root of piece value for defense calculation
                dv += math.sqrt(valueX)  # multiplicity counts

    return dv

def compute_metrics(state: GameState) -> Metrics:
    pv_w = compute_pv(state, WHITE)
    pv_b = compute_pv(state, BLACK)

    mv_w, ov_w = compute_mv_ov(state, WHITE)
    mv_b, ov_b = compute_mv_ov(state, BLACK)

    dv_w = compute_dv(state, WHITE)
    dv_b = compute_dv(state, BLACK)

    return Metrics(pv_w, mv_w, ov_w, dv_w, pv_b, mv_b, ov_b, dv_b)

def deltas(m: Metrics) -> Tuple[int,int,int,int]:
    return (m.pv_w - m.pv_b, m.mv_w - m.mv_b, m.ov_w - m.ov_b, m.dv_w - m.dv_b)
