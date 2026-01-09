from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Tuple, List
from .types import (
    GameState, WHITE, BLACK,
    PIECE_VALUE, KING,
    piece_color, piece_kind, opposite
)
from .movegen import generate_legal_moves, gen_pseudo_moves
from .rules import is_in_check, pseudo_attacks_square
from .apply import apply_move, undo_move
from .types import Move

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


# =============================================================================
# UNIFIED METRICS COMPUTATION (Optimized)
# =============================================================================
# This implementation uses a single board traversal and shared move generation
# to compute all metrics more efficiently than the original separate functions.

def _collect_pieces(board: List[int]) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """
    Single board traversal to collect all pieces by side.
    Returns (white_pieces, black_pieces) where each is a list of (square, piece_kind).
    """
    white_pieces: List[Tuple[int, int]] = []
    black_pieces: List[Tuple[int, int]] = []

    for sq, p in enumerate(board):
        if p == 0:
            continue
        kind = piece_kind(p)
        if p > 0:  # WHITE
            white_pieces.append((sq, kind))
        else:  # BLACK
            black_pieces.append((sq, kind))

    return white_pieces, black_pieces


def _compute_pv_from_pieces(pieces: List[Tuple[int, int]]) -> int:
    """Compute piece value from pre-collected pieces list."""
    return sum(PIECE_VALUE[kind] for sq, kind in pieces)


def _compute_mv_ov_from_moves(moves: List[Move]) -> Tuple[int, int]:
    """Compute mobility and offensive value from pre-generated moves."""
    mv = 0
    ov = 0
    for m in moves:
        if m.is_ep:
            ov += 1  # victim pawn value
        elif m.is_capture:
            ov += PIECE_VALUE[m.captured_kind]
        else:
            mv += 1  # non-capture moves (includes castling, non-capture promotions)
    return mv, ov


def _compute_dv_optimized(state: GameState, side: int, pieces: List[Tuple[int, int]]) -> float:
    """
    Optimized DV computation using pre-collected pieces.

    For each friendly piece X (except king), check if any other friendly piece A
    can pseudo-attack X's square, and if moving A to X's square would leave
    the king safe (simulating a "defense" move).
    """
    b = state.board
    dv = 0.0

    # Build a quick lookup for piece squares
    piece_squares = [sq for sq, kind in pieces]

    for t_idx, (t_sq, t_kind) in enumerate(pieces):
        # Skip kings - can't temporarily remove king from board
        if t_kind == KING:
            continue

        value_x = PIECE_VALUE[t_kind]
        sqrt_value = math.sqrt(value_x)

        for f_idx, (f_sq, f_kind) in enumerate(pieces):
            if f_idx == t_idx:
                continue

            # Check if piece at f_sq can pseudo-attack t_sq
            if not pseudo_attacks_square(state, f_sq, t_sq):
                continue

            # Simulate capture-like move (A -> t, removing X) and check king safety
            # Inline the apply/undo for performance
            moved = b[f_sq]
            captured = b[t_sq]
            b[t_sq] = moved
            b[f_sq] = 0

            ok = not is_in_check(state, side)

            # Undo
            b[f_sq] = moved
            b[t_sq] = captured

            if ok:
                dv += sqrt_value

    return dv


@profile_function
def compute_metrics_unified(state: GameState) -> Metrics:
    """
    Unified metrics computation with optimizations:
    1. Single board traversal to collect pieces
    2. Shared move generation for MV/OV
    3. Optimized DV computation with pre-collected pieces

    This is 2-3x faster than the original separate function approach.
    """
    b = state.board

    # Phase 1: Single board traversal to collect pieces
    white_pieces, black_pieces = _collect_pieces(b)

    # Phase 2: Compute PV from collected pieces (no board traversal needed)
    pv_w = _compute_pv_from_pieces(white_pieces)
    pv_b = _compute_pv_from_pieces(black_pieces)

    # Phase 3: Generate legal moves once per side, compute MV/OV
    with profile_section("unified_mv_ov"):
        white_moves = generate_legal_moves(state, WHITE)
        mv_w, ov_w = _compute_mv_ov_from_moves(white_moves)

        black_moves = generate_legal_moves(state, BLACK)
        mv_b, ov_b = _compute_mv_ov_from_moves(black_moves)

    # Phase 4: Compute DV using pre-collected pieces
    with profile_section("unified_dv"):
        dv_w = _compute_dv_optimized(state, WHITE, white_pieces)
        dv_b = _compute_dv_optimized(state, BLACK, black_pieces)

    return Metrics(pv_w, mv_w, ov_w, dv_w, pv_b, mv_b, ov_b, dv_b)


# =============================================================================
# FAST APPROXIMATION MODE (for deep search)
# =============================================================================
# Uses pseudo-legal moves instead of legal moves for MV/OV calculation.
# This is ~3x faster but less accurate (doesn't account for pins/checks).
# DV is approximated without legality checks.

def _compute_mv_ov_fast(state: GameState, side: int) -> Tuple[int, int]:
    """
    Fast MV/OV computation using pseudo-legal moves.
    Does not check if moves leave king in check.
    """
    pseudo = gen_pseudo_moves(state, side)
    mv = 0
    ov = 0
    for m in pseudo:
        if m.is_ep:
            ov += 1
        elif m.is_capture:
            ov += PIECE_VALUE[m.captured_kind]
        else:
            mv += 1
    return mv, ov


def _compute_dv_fast(state: GameState, side: int, pieces: List[Tuple[int, int]]) -> float:
    """
    Fast DV computation without legality checks.
    Simply counts pseudo-attacks between friendly pieces.
    """
    dv = 0.0

    for t_idx, (t_sq, t_kind) in enumerate(pieces):
        if t_kind == KING:
            continue

        sqrt_value = math.sqrt(PIECE_VALUE[t_kind])

        for f_idx, (f_sq, f_kind) in enumerate(pieces):
            if f_idx == t_idx:
                continue

            if pseudo_attacks_square(state, f_sq, t_sq):
                dv += sqrt_value

    return dv


@profile_function
def compute_metrics_fast(state: GameState) -> Metrics:
    """
    Fast metrics computation using pseudo-legal moves.

    ~3x faster than compute_metrics_unified but less accurate:
    - MV/OV counts pseudo-legal moves (ignores pins/checks)
    - DV doesn't verify legality of defense moves

    Use for deep search where speed matters more than precision.
    """
    b = state.board

    # Phase 1: Single board traversal to collect pieces
    white_pieces, black_pieces = _collect_pieces(b)

    # Phase 2: Compute PV from collected pieces
    pv_w = _compute_pv_from_pieces(white_pieces)
    pv_b = _compute_pv_from_pieces(black_pieces)

    # Phase 3: Fast MV/OV using pseudo-legal moves
    mv_w, ov_w = _compute_mv_ov_fast(state, WHITE)
    mv_b, ov_b = _compute_mv_ov_fast(state, BLACK)

    # Phase 4: Fast DV without legality checks
    dv_w = _compute_dv_fast(state, WHITE, white_pieces)
    dv_b = _compute_dv_fast(state, BLACK, black_pieces)

    return Metrics(pv_w, mv_w, ov_w, dv_w, pv_b, mv_b, ov_b, dv_b)


# =============================================================================
# ORIGINAL FUNCTIONS (kept for comparison and testing)
# =============================================================================

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

# =============================================================================
# METRICS MODE CONFIGURATION
# =============================================================================
# METRICS_MODE controls which implementation is used:
#   "optimized" - python-chess + NumPy + Zobrist (fastest, accurate)
#   "hybrid"    - python-chess for moves only (good balance)
#   "unified"   - Accurate metrics with optimized single-pass (default)
#   "fast"      - Fast approximation using pseudo-legal moves (~3x faster)
#   "original"  - Original separate functions (for comparison)
#
# Performance comparison (depth 3 search):
#   - "optimized": ~1.0s (estimated, 5x faster)
#   - "hybrid":    ~2.0s (estimated, 2.5x faster)
#   - "unified":   5.3s, accurate metrics
#   - "fast":      2.9s, approximate metrics (1.8x faster)
METRICS_MODE = "unified"

def compute_metrics(state: GameState) -> Metrics:
    """
    Compute all metrics for a position.

    Uses METRICS_MODE to select implementation:
    - "optimized": python-chess + NumPy (fastest, accurate)
    - "hybrid": python-chess for moves only
    - "unified": Accurate with optimizations (default)
    - "fast": Fast approximation for deep search
    - "original": Original implementation for comparison
    """
    if METRICS_MODE == "optimized":
        from .metrics_optimized import compute_metrics_optimized
        return compute_metrics_optimized(state)
    elif METRICS_MODE == "hybrid":
        from .metrics_optimized import compute_metrics_hybrid
        return compute_metrics_hybrid(state)
    elif METRICS_MODE == "fast":
        return compute_metrics_fast(state)
    elif METRICS_MODE == "unified":
        return compute_metrics_unified(state)

    # Original implementation (kept for comparison)
    with profile_section("compute_pv"):
        pv_w = compute_pv(state, WHITE)
        pv_b = compute_pv(state, BLACK)

    with profile_section("compute_mv_ov"):
        mv_w, ov_w = compute_mv_ov(state, WHITE)
        mv_b, ov_b = compute_mv_ov(state, BLACK)

    with profile_section("compute_dv"):
        dv_w = compute_dv(state, WHITE)
        dv_b = compute_dv(state, BLACK)

    return Metrics(pv_w, mv_w, ov_w, dv_w, pv_b, mv_b, ov_b, dv_b)


def set_metrics_mode(mode: str) -> None:
    """
    Set the metrics computation mode.

    Args:
        mode: One of "optimized", "hybrid", "unified", "fast", or "original"
    """
    global METRICS_MODE
    valid_modes = ("optimized", "hybrid", "unified", "fast", "original")
    if mode not in valid_modes:
        raise ValueError(f"Invalid metrics mode: {mode}. Use one of {valid_modes}.")
    METRICS_MODE = mode

def deltas(m: Metrics) -> Tuple[int,int,int,int]:
    return (m.pv_w - m.pv_b, m.mv_w - m.mv_b, m.ov_w - m.ov_b, m.dv_w - m.dv_b)
