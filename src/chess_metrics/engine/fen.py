from __future__ import annotations
from typing import List
from .types import (
    GameState, WHITE, BLACK,
    CR_WK, CR_WQ, CR_BK, CR_BQ,
    CHAR_TO_PIECE, PIECE_TO_CHAR, sq_to_alg, alg_to_sq
)

def parse_fen(fen: str) -> GameState:
    parts = fen.strip().split()
    if len(parts) != 6:
        raise ValueError("FEN must have 6 fields")

    placement, stm, castling, ep, halfmove, fullmove = parts
    board: List[int] = [0]*64

    ranks = placement.split("/")
    if len(ranks) != 8:
        raise ValueError("FEN placement must have 8 ranks")

    # FEN rank 8 -> internal rank 7, ... rank 1 -> internal rank 0
    for fen_rank_index, rank_str in enumerate(ranks):
        r = 7 - fen_rank_index
        f = 0
        for ch in rank_str:
            if ch.isdigit():
                f += int(ch)
            else:
                if ch not in CHAR_TO_PIECE:
                    raise ValueError(f"Bad piece char: {ch}")
                p = CHAR_TO_PIECE[ch]
                sq = r * 8 + f
                board[sq] = p
                f += 1
        if f != 8:
            raise ValueError("Bad FEN rank width")

    side = WHITE if stm == "w" else BLACK if stm == "b" else None
    if side is None:
        raise ValueError("Bad side to move in FEN")

    cr = 0
    if castling != "-":
        if "K" in castling: cr |= CR_WK
        if "Q" in castling: cr |= CR_WQ
        if "k" in castling: cr |= CR_BK
        if "q" in castling: cr |= CR_BQ

    ep_sq = -1 if ep == "-" else alg_to_sq(ep)

    return GameState(
        board=board,
        side_to_move=side,
        castling_rights=cr,
        ep_sq=ep_sq,
        halfmove_clock=int(halfmove),
        fullmove_number=int(fullmove),
        undo_stack=[]
    )

def to_fen(state: GameState) -> str:
    rows = []
    for r in range(7, -1, -1):
        empties = 0
        row = ""
        for f in range(8):
            sq = r*8 + f
            p = state.board[sq]
            if p == 0:
                empties += 1
            else:
                if empties:
                    row += str(empties)
                    empties = 0
                kind = abs(p)
                ch = PIECE_TO_CHAR[kind]
                row += ch if p > 0 else ch.lower()
        if empties:
            row += str(empties)
        rows.append(row)
    placement = "/".join(rows)
    stm = "w" if state.side_to_move == WHITE else "b"

    cr = ""
    if state.castling_rights == 0:
        cr = "-"
    else:
        if state.castling_rights & 1: cr += "K"
        if state.castling_rights & 2: cr += "Q"
        if state.castling_rights & 4: cr += "k"
        if state.castling_rights & 8: cr += "q"

    ep = "-" if state.ep_sq == -1 else sq_to_alg(state.ep_sq)

    return f"{placement} {stm} {cr} {ep} {state.halfmove_clock} {state.fullmove_number}"
