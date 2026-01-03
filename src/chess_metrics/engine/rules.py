from __future__ import annotations
from .types import (
    WHITE, BLACK,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    piece_color, piece_kind, opposite
)

KNIGHT_OFFS = [+17, +15, +10, +6, -6, -10, -15, -17]
KING_OFFS   = [+1, -1, +8, -8, +9, +7, -7, -9]

def on_board(sq: int) -> bool:
    return 0 <= sq < 64

def same_file(a: int, b: int) -> bool:
    return (a % 8) == (b % 8)

def same_rank(a: int, b: int) -> bool:
    return (a // 8) == (b // 8)

def file_of(sq: int) -> int:
    return sq % 8

def rank_of(sq: int) -> int:
    return sq // 8

def is_square_attacked(state, sq: int, by_side: int) -> bool:
    b = state.board

    # Pawn attacks
    if by_side == WHITE:
        for d in (-7, -9):
            s = sq + d
            if 0 <= s < 64:
                # ensure file delta matches diagonal
                if abs(file_of(s) - file_of(sq)) == 1 and b[s] == WHITE * PAWN:
                    return True
    else:
        for d in (+7, +9):
            s = sq + d
            if 0 <= s < 64:
                if abs(file_of(s) - file_of(sq)) == 1 and b[s] == BLACK * PAWN:
                    return True

    # Knight attacks
    for d in KNIGHT_OFFS:
        s = sq + d
        if 0 <= s < 64 and abs(file_of(s) - file_of(sq)) in (1,2):
            p = b[s]
            if p != 0 and piece_color(p) == by_side and piece_kind(p) == KNIGHT:
                return True

    # King attacks
    for d in KING_OFFS:
        s = sq + d
        if 0 <= s < 64 and abs(file_of(s) - file_of(sq)) <= 1:
            p = b[s]
            if p != 0 and piece_color(p) == by_side and piece_kind(p) == KING:
                return True

    # Sliding attacks (rook/queen)
    for d in (+1, -1, +8, -8):
        s = sq + d
        while 0 <= s < 64 and (d in (+8,-8) or same_rank(s, s-d)):
            p = b[s]
            if p != 0:
                if piece_color(p) == by_side:
                    k = piece_kind(p)
                    if k == ROOK or k == QUEEN:
                        return True
                break
            s += d

    # Sliding attacks (bishop/queen)
    for d in (+9, +7, -7, -9):
        s = sq + d
        while 0 <= s < 64 and abs(file_of(s) - file_of(s-d)) == 1:
            p = b[s]
            if p != 0:
                if piece_color(p) == by_side:
                    k = piece_kind(p)
                    if k == BISHOP or k == QUEEN:
                        return True
                break
            s += d

    return False

def find_king_sq(state, side: int) -> int:
    target = side * KING
    for sq, p in enumerate(state.board):
        if p == target:
            return sq
    raise ValueError("King not found")

def is_in_check(state, side: int) -> bool:
    ksq = find_king_sq(state, side)
    return is_square_attacked(state, ksq, opposite(side))

def pseudo_attacks_square(state, from_sq: int, to_sq: int) -> bool:
    b = state.board
    p = b[from_sq]
    if p == 0:
        return False
    side = piece_color(p)
    k = piece_kind(p)

    ff = from_sq % 8
    tf = to_sq % 8

    df = tf - ff
    dr = (to_sq // 8) - (from_sq // 8)

    if k == PAWN:
        if side == WHITE:
            return dr == 1 and abs(df) == 1
        else:
            return dr == -1 and abs(df) == 1

    if k == KNIGHT:
        return (abs(df), abs(dr)) in ((1,2),(2,1))

    if k == KING:
        return max(abs(df), abs(dr)) == 1

    if k in (BISHOP, ROOK, QUEEN):
        # check ray alignment
        step = 0
        if df == 0 and dr != 0:
            step = 8 if dr > 0 else -8
        elif dr == 0 and df != 0:
            step = 1 if df > 0 else -1
        elif abs(df) == abs(dr) and df != 0:
            if df > 0 and dr > 0: step = 9
            if df < 0 and dr > 0: step = 7
            if df > 0 and dr < 0: step = -7
            if df < 0 and dr < 0: step = -9
        else:
            return False

        if k == BISHOP and abs(df) != abs(dr):
            return False
        if k == ROOK and not (df == 0 or dr == 0):
            return False

        s = from_sq + step
        while s != to_sq:
            if s < 0 or s >= 64:
                return False
            # ensure we didn't wrap on ranks/files
            if step in (1,-1) and (s // 8) != ((s-step)//8):
                return False
            if step in (7,9,-7,-9) and abs((s%8) - ((s-step)%8)) != 1:
                return False
            if b[s] != 0:
                return False
            s += step
        return True

    return False
