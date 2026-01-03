from __future__ import annotations
from typing import List
from .types import (
    GameState, Move,
    WHITE, BLACK,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    PIECE_TO_CHAR, piece_color, piece_kind, opposite, sq_to_alg
)
from .movegen import generate_legal_moves
from .apply import apply_move, undo_move
from .rules import is_in_check

def move_to_san(state: GameState, m: Move) -> str:
    # Castling
    if m.is_castle:
        if m.to_sq % 8 == 6:
            san = "O-O"
        else:
            san = "O-O-O"
        # suffix check/mate
        u = apply_move(state, m)
        suffix = _check_suffix(state)
        undo_move(state, u)
        return san + suffix

    b = state.board
    mover_piece = b[m.from_sq]
    mover_kind = piece_kind(mover_piece)

    dest = sq_to_alg(m.to_sq)
    capture = m.is_capture or m.is_ep

    # Piece letter (none for pawn)
    if mover_kind == PAWN:
        prefix = ""
        if capture:
            prefix = chr(ord('a') + (m.from_sq % 8))  # pawn file
    else:
        prefix = PIECE_TO_CHAR[mover_kind]
        prefix += _disambiguation(state, m)

    san = prefix
    if capture:
        san += "x"
    san += dest

    if m.is_promotion:
        san += "=Q"

    u = apply_move(state, m)
    suffix = _check_suffix(state)
    undo_move(state, u)

    return san + suffix

def _disambiguation(state: GameState, m: Move) -> str:
    # Minimal SAN disambiguation: if another legal piece of same kind can also reach to_sq, include file/rank as needed.
    b = state.board
    mover_piece = b[m.from_sq]
    mover_kind = piece_kind(mover_piece)
    side = piece_color(mover_piece)

    if mover_kind in (PAWN, KING):
        return ""

    legal = generate_legal_moves(state, side)
    rivals = []
    for mv in legal:
        if mv.to_sq == m.to_sq and mv.from_sq != m.from_sq:
            p = b[mv.from_sq]
            if p != 0 and piece_color(p) == side and piece_kind(p) == mover_kind:
                rivals.append(mv)

    if not rivals:
        return ""

    from_file = m.from_sq % 8
    from_rank = m.from_sq // 8

    need_file = any((rv.from_sq % 8) == from_file for rv in rivals)
    need_rank = any((rv.from_sq // 8) == from_rank for rv in rivals)

    # SAN rule: if files differ among candidates, use file; else use rank; else use both.
    file_unique = all((rv.from_sq % 8) != from_file for rv in rivals)
    rank_unique = all((rv.from_sq // 8) != from_rank for rv in rivals)

    if file_unique:
        return chr(ord('a') + from_file)
    if rank_unique:
        return chr(ord('1') + from_rank)
    return chr(ord('a') + from_file) + chr(ord('1') + from_rank)

def _check_suffix(state_after_move: GameState) -> str:
    # state_after_move.side_to_move is opponent now
    opp = state_after_move.side_to_move
    in_check = is_in_check(state_after_move, opp)
    if not in_check:
        return ""
    # checkmate if no legal moves
    if not generate_legal_moves(state_after_move, opp):
        return "#"
    return "+"
