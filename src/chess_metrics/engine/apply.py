from __future__ import annotations
from .types import (
    GameState, Move, Undo,
    WHITE, BLACK,
    PAWN, ROOK, KING, QUEEN,
    CR_WK, CR_WQ, CR_BK, CR_BQ,
    piece_color, piece_kind
)

def apply_move(state: GameState, m: Move) -> Undo:
    b = state.board

    prev_cr = state.castling_rights
    prev_ep = state.ep_sq
    prev_half = state.halfmove_clock
    prev_full = state.fullmove_number
    prev_stm = state.side_to_move

    moved_piece_before = b[m.from_sq]
    to_piece_before = b[m.to_sq]

    captured_piece = 0
    captured_sq = -1

    rook_piece = 0
    rook_from = -1
    rook_to = -1

    # Clear EP by default; set only on double pawn push below
    state.ep_sq = -1

    # captures
    if m.is_ep:
        # En passant: victim pawn is behind the target square
        # If white captures, victim is one rank below (to_sq - 8)
        # If black captures, victim is one rank above (to_sq + 8)
        side = prev_stm
        captured_sq = m.to_sq - 8 if side == WHITE else m.to_sq + 8
        captured_piece = b[captured_sq]
        b[captured_sq] = 0
    elif m.is_capture:
        captured_sq = m.to_sq
        captured_piece = b[m.to_sq]

    # move the piece
    b[m.to_sq] = b[m.from_sq]
    b[m.from_sq] = 0

    # promotion
    if m.is_promotion:
        side = piece_color(b[m.to_sq])
        b[m.to_sq] = side * QUEEN

    # castling rook move
    if m.is_castle:
        # Determine rook positions based on king's move
        # White kingside: e1->g1 (4->6), rook h1->f1 (7->5)
        # White queenside: e1->c1 (4->2), rook a1->d1 (0->3)
        # Black kingside: e8->g8 (60->62), rook h8->f8 (63->61)
        # Black queenside: e8->c8 (60->58), rook a8->d8 (56->59)
        if m.from_sq == 4 and m.to_sq == 6:  # White kingside
            rook_from, rook_to = 7, 5
        elif m.from_sq == 4 and m.to_sq == 2:  # White queenside
            rook_from, rook_to = 0, 3
        elif m.from_sq == 60 and m.to_sq == 62:  # Black kingside
            rook_from, rook_to = 63, 61
        elif m.from_sq == 60 and m.to_sq == 58:  # Black queenside
            rook_from, rook_to = 56, 59
        else:
            raise ValueError(f"Invalid castling move: {m.from_sq}->{m.to_sq}")

        rook_piece = b[rook_from]
        b[rook_to] = rook_piece
        b[rook_from] = 0

    # update castling rights based on king/rook moves or captures
    side = prev_stm
    if piece_kind(moved_piece_before) == KING:
        if side == WHITE:
            state.castling_rights &= ~(CR_WK | CR_WQ)
        else:
            state.castling_rights &= ~(CR_BK | CR_BQ)

    # rook moved from original rook square
    if piece_kind(moved_piece_before) == ROOK:
        if side == WHITE:
            if m.from_sq == 0:  state.castling_rights &= ~CR_WQ  # a1
            if m.from_sq == 7:  state.castling_rights &= ~CR_WK  # h1
        else:
            if m.from_sq == 56: state.castling_rights &= ~CR_BQ  # a8
            if m.from_sq == 63: state.castling_rights &= ~CR_BK  # h8

    # rook captured on original rook square
    if captured_piece != 0 and piece_kind(captured_piece) == ROOK:
        cap_side = piece_color(captured_piece)
        if cap_side == WHITE:
            if captured_sq == 0: state.castling_rights &= ~CR_WQ
            if captured_sq == 7: state.castling_rights &= ~CR_WK
        else:
            if captured_sq == 56: state.castling_rights &= ~CR_BQ
            if captured_sq == 63: state.castling_rights &= ~CR_BK

    # EP target square set on double pawn push
    if piece_kind(moved_piece_before) == PAWN and not m.is_capture and not m.is_ep:
        # detect 2-square advance
        diff = m.to_sq - m.from_sq
        if diff == 16:   # white
            state.ep_sq = m.from_sq + 8
        elif diff == -16: # black
            state.ep_sq = m.from_sq - 8

    # halfmove clock
    if piece_kind(moved_piece_before) == PAWN or m.is_capture or m.is_ep:
        state.halfmove_clock = 0
    else:
        state.halfmove_clock += 1

    # fullmove number increments after black move
    if prev_stm == BLACK:
        state.fullmove_number += 1

    # toggle side to move
    state.side_to_move = WHITE if prev_stm == BLACK else BLACK

    undo = Undo(
        move=m,
        captured_piece=captured_piece,
        captured_sq=captured_sq,
        prev_castling_rights=prev_cr,
        prev_ep_sq=prev_ep,
        prev_halfmove=prev_half,
        prev_fullmove=prev_full,
        prev_side_to_move=prev_stm,
        rook_piece=rook_piece,
        rook_from=rook_from,
        rook_to=rook_to,
        moved_piece_before=moved_piece_before,
        to_piece_before=to_piece_before
    )
    state.undo_stack.append(undo)
    return undo

def undo_move(state: GameState, undo: Undo) -> None:
    b = state.board
    m = undo.move

    # restore STM and counters
    state.side_to_move = undo.prev_side_to_move
    state.castling_rights = undo.prev_castling_rights
    state.ep_sq = undo.prev_ep_sq
    state.halfmove_clock = undo.prev_halfmove
    state.fullmove_number = undo.prev_fullmove

    # undo castling rook
    if m.is_castle:
        b[undo.rook_from] = undo.rook_piece
        b[undo.rook_to] = 0

    # undo move piece
    b[m.from_sq] = undo.moved_piece_before
    b[m.to_sq] = undo.to_piece_before

    # undo capture
    if m.is_ep:
        b[undo.captured_sq] = undo.captured_piece
    elif m.is_capture:
        b[undo.captured_sq] = undo.captured_piece

    state.undo_stack.pop()
