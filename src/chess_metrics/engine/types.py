from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Tuple

WHITE = 1
BLACK = -1

# Board encoding: 0 empty; >0 white piece; <0 black piece; abs(piece) is piece kind.
PAWN   = 1
KNIGHT = 2
BISHOP = 3
ROOK   = 4
QUEEN  = 5
KING   = 6

PIECE_TO_CHAR = {
    PAWN: "P", KNIGHT: "N", BISHOP: "B", ROOK: "R", QUEEN: "Q", KING: "K"
}
CHAR_TO_PIECE = {v: k for k, v in PIECE_TO_CHAR.items()}
CHAR_TO_PIECE.update({v.lower(): -k for k, v in PIECE_TO_CHAR.items()})  # for FEN parsing

# Castling rights bitmask
CR_WK = 1
CR_WQ = 2
CR_BK = 4
CR_BQ = 8

PIECE_VALUE = {
    PAWN: 1,
    KNIGHT: 3,
    BISHOP: 3,
    ROOK: 5,
    QUEEN: 9,
    KING: 0,
}

def piece_color(p: int) -> int:
    if p > 0: return WHITE
    if p < 0: return BLACK
    return 0

def piece_kind(p: int) -> int:
    return abs(p)

def value_of_piece(p: int) -> int:
    return PIECE_VALUE[abs(p)] if p != 0 else 0

def opposite(side: int) -> int:
    return WHITE if side == BLACK else BLACK

def sq_to_alg(sq: int) -> str:
    f = sq % 8
    r = sq // 8
    return chr(ord('a') + f) + chr(ord('1') + r)

def alg_to_sq(a: str) -> int:
    f = ord(a[0]) - ord('a')
    r = ord(a[1]) - ord('1')
    return r * 8 + f

@dataclass(frozen=True)
class Move:
    from_sq: int
    to_sq: int
    moving_kind: int
    captured_kind: int = 0
    is_capture: bool = False
    is_ep: bool = False
    is_castle: bool = False
    is_promotion: bool = False
    promotion_kind: int = QUEEN

    def uci(self) -> str:
        s = sq_to_alg(self.from_sq) + sq_to_alg(self.to_sq)
        if self.is_promotion:
            s += "q"  # locked
        return s

@dataclass
class Undo:
    move: Move
    captured_piece: int
    captured_sq: int
    prev_castling_rights: int
    prev_ep_sq: int
    prev_halfmove: int
    prev_fullmove: int
    prev_side_to_move: int
    rook_piece: int
    rook_from: int
    rook_to: int
    moved_piece_before: int
    to_piece_before: int

@dataclass
class GameState:
    board: List[int]               # len 64
    side_to_move: int              # WHITE or BLACK
    castling_rights: int           # bitmask CR_*
    ep_sq: int                     # -1 if none
    halfmove_clock: int
    fullmove_number: int
    undo_stack: List[Undo]

    @staticmethod
    def empty() -> "GameState":
        return GameState([0]*64, WHITE, 0, -1, 0, 1, [])
