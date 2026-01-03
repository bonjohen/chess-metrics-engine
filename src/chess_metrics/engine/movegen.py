from __future__ import annotations
from typing import List
from .types import (
    GameState, Move,
    WHITE, BLACK,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    CR_WK, CR_WQ, CR_BK, CR_BQ,
    piece_color, piece_kind, opposite
)
from .rules import is_in_check, is_square_attacked, file_of, rank_of
from .apply import apply_move, undo_move

def on_board(sq: int) -> bool:
    return 0 <= sq < 64

def same_rank(a: int, b: int) -> bool:
    return (a // 8) == (b // 8)

def gen_pseudo_moves(state: GameState, side: int) -> List[Move]:
    b = state.board
    moves: List[Move] = []

    for from_sq, p in enumerate(b):
        if p == 0 or piece_color(p) != side:
            continue
        k = piece_kind(p)

        if k == PAWN:
            moves.extend(_pawn_moves(state, side, from_sq))
        elif k == KNIGHT:
            moves.extend(_knight_moves(state, side, from_sq))
        elif k == BISHOP:
            moves.extend(_slider_moves(state, side, from_sq, deltas=[+9,+7,-7,-9], kinds=(BISHOP,)))
        elif k == ROOK:
            moves.extend(_slider_moves(state, side, from_sq, deltas=[+1,-1,+8,-8], kinds=(ROOK,)))
        elif k == QUEEN:
            moves.extend(_slider_moves(state, side, from_sq, deltas=[+1,-1,+8,-8,+9,+7,-7,-9], kinds=(QUEEN,)))
        elif k == KING:
            moves.extend(_king_moves(state, side, from_sq))

    # Castling pseudo (with legality admission per spec)
    moves.extend(_castle_moves(state, side))

    return moves

def generate_legal_moves(state: GameState, side: int) -> List[Move]:
    pseudo = gen_pseudo_moves(state, side)
    legal: List[Move] = []
    for m in pseudo:
        u = apply_move(state, m)
        if not is_in_check(state, side):
            legal.append(m)
        undo_move(state, u)
    # stable deterministic order (UCI)
    legal.sort(key=lambda m: m.uci())
    return legal

def _pawn_moves(state: GameState, side: int, from_sq: int) -> List[Move]:
    b = state.board
    moves: List[Move] = []
    r = rank_of(from_sq)
    f = file_of(from_sq)

    forward = 8 if side == WHITE else -8
    start_rank = 1 if side == WHITE else 6
    promo_rank = 7 if side == WHITE else 0

    one = from_sq + forward
    if on_board(one) and b[one] == 0:
        # promotion?
        if rank_of(one) == promo_rank:
            moves.append(Move(from_sq, one, PAWN, is_promotion=True))
        else:
            moves.append(Move(from_sq, one, PAWN))
            # double
            two = from_sq + 2*forward
            if r == start_rank and on_board(two) and b[two] == 0:
                moves.append(Move(from_sq, two, PAWN))

    # captures
    for df in (-1, +1):
        if 0 <= f+df <= 7:
            to = from_sq + forward + df
            if on_board(to):
                target = b[to]
                if target != 0 and piece_color(target) == opposite(side):
                    cap_kind = piece_kind(target)
                    if rank_of(to) == promo_rank:
                        moves.append(Move(from_sq, to, PAWN, captured_kind=cap_kind, is_capture=True, is_promotion=True))
                    else:
                        moves.append(Move(from_sq, to, PAWN, captured_kind=cap_kind, is_capture=True))

    # en-passant
    if state.ep_sq != -1:
        ep = state.ep_sq
        ep_r = rank_of(ep)
        ep_f = file_of(ep)
        # ep target must be diagonally forward from pawn
        if abs(ep_f - f) == 1 and ((side == WHITE and ep_r == r+1) or (side == BLACK and ep_r == r-1)):
            # victim pawn is behind ep square
            victim_sq = ep - 8 if side == WHITE else ep + 8
            if on_board(victim_sq) and b[victim_sq] == opposite(side) * PAWN and b[ep] == 0:
                moves.append(Move(from_sq, ep, PAWN, captured_kind=PAWN, is_capture=True, is_ep=True, ep_victim_sq=victim_sq))

    return moves

def _knight_moves(state: GameState, side: int, from_sq: int) -> List[Move]:
    b = state.board
    moves: List[Move] = []
    ff = file_of(from_sq)

    for d in (+17,+15,+10,+6,-6,-10,-15,-17):
        to = from_sq + d
        if not on_board(to):
            continue
        tf = file_of(to)
        if abs(tf - ff) not in (1,2):
            continue
        target = b[to]
        if target == 0:
            moves.append(Move(from_sq, to, KNIGHT))
        elif piece_color(target) == opposite(side):
            moves.append(Move(from_sq, to, KNIGHT, captured_kind=piece_kind(target), is_capture=True))
    return moves

def _king_moves(state: GameState, side: int, from_sq: int) -> List[Move]:
    b = state.board
    moves: List[Move] = []
    ff = file_of(from_sq)
    for d in (+1,-1,+8,-8,+9,+7,-7,-9):
        to = from_sq + d
        if not on_board(to):
            continue
        if abs(file_of(to) - ff) > 1:
            continue
        target = b[to]
        if target == 0:
            moves.append(Move(from_sq, to, KING))
        elif piece_color(target) == opposite(side):
            moves.append(Move(from_sq, to, KING, captured_kind=piece_kind(target), is_capture=True))
    return moves

def _slider_moves(state: GameState, side: int, from_sq: int, deltas: List[int], kinds) -> List[Move]:
    b = state.board
    moves: List[Move] = []
    k = piece_kind(b[from_sq])
    for d in deltas:
        to = from_sq + d
        while on_board(to):
            # rank wrap for horizontal
            if d in (+1,-1) and not same_rank(to, to-d):
                break
            # diagonal wrap
            if d in (+7,+9,-7,-9) and abs(file_of(to) - file_of(to-d)) != 1:
                break
            target = b[to]
            if target == 0:
                moves.append(Move(from_sq, to, k))
            else:
                if piece_color(target) == opposite(side):
                    moves.append(Move(from_sq, to, k, captured_kind=piece_kind(target), is_capture=True))
                break
            to += d
    return moves

def _castle_moves(state: GameState, side: int) -> List[Move]:
    b = state.board
    moves: List[Move] = []

    # King must be on e-file home rank
    if side == WHITE:
        king_sq = 4   # e1
        home_rank = 0
        if b[king_sq] != WHITE * KING:
            return moves
        if is_in_check(state, WHITE):
            return moves

        # King side: e1->g1, rook h1->f1
        if state.castling_rights & CR_WK:
            if b[5] == 0 and b[6] == 0 and b[7] == WHITE * ROOK:
                if (not is_square_attacked(state, 5, BLACK)) and (not is_square_attacked(state, 6, BLACK)):
                    moves.append(Move(4, 6, KING, is_castle=True, castle_rook_from=7, castle_rook_to=5))

        # Queen side: e1->c1, rook a1->d1
        if state.castling_rights & CR_WQ:
            if b[3] == 0 and b[2] == 0 and b[1] == 0 and b[0] == WHITE * ROOK:
                if (not is_square_attacked(state, 3, BLACK)) and (not is_square_attacked(state, 2, BLACK)):
                    moves.append(Move(4, 2, KING, is_castle=True, castle_rook_from=0, castle_rook_to=3))

    else:
        king_sq = 60  # e8
        if b[king_sq] != BLACK * KING:
            return moves
        if is_in_check(state, BLACK):
            return moves

        # King side: e8->g8, rook h8->f8
        if state.castling_rights & CR_BK:
            if b[61] == 0 and b[62] == 0 and b[63] == BLACK * ROOK:
                if (not is_square_attacked(state, 61, WHITE)) and (not is_square_attacked(state, 62, WHITE)):
                    moves.append(Move(60, 62, KING, is_castle=True, castle_rook_from=63, castle_rook_to=61))

        # Queen side: e8->c8, rook a8->d8
        if state.castling_rights & CR_BQ:
            if b[59] == 0 and b[58] == 0 and b[57] == 0 and b[56] == BLACK * ROOK:
                if (not is_square_attacked(state, 59, WHITE)) and (not is_square_attacked(state, 58, WHITE)):
                    moves.append(Move(60, 58, KING, is_castle=True, castle_rook_from=56, castle_rook_to=59))

    return moves
