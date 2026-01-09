"""
Bridge between python-chess library and our custom metrics system.

This module provides utilities to:
1. Convert between python-chess Board and our GameState
2. Use python-chess's optimized move generation
3. Leverage python-chess's attack detection
"""
from __future__ import annotations
import chess
import numpy as np
from typing import List, Tuple
from .types import GameState, Move, WHITE, BLACK, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING
from .types import CR_WK, CR_WQ, CR_BK, CR_BQ

# Piece mapping: python-chess piece type to our piece kind
CHESS_TO_OUR_PIECE = {
    chess.PAWN: PAWN,
    chess.KNIGHT: KNIGHT,
    chess.BISHOP: BISHOP,
    chess.ROOK: ROOK,
    chess.QUEEN: QUEEN,
    chess.KING: KING,
}

OUR_TO_CHESS_PIECE = {v: k for k, v in CHESS_TO_OUR_PIECE.items()}


def chess_board_to_state(board: chess.Board) -> GameState:
    """
    Convert python-chess Board to our GameState.
    
    Args:
        board: python-chess Board object
        
    Returns:
        GameState with equivalent position
    """
    # Initialize empty board
    our_board = [0] * 64
    
    # Convert pieces
    for sq in range(64):
        piece = board.piece_at(sq)
        if piece:
            piece_kind = CHESS_TO_OUR_PIECE[piece.piece_type]
            side = WHITE if piece.color == chess.WHITE else BLACK
            our_board[sq] = side * piece_kind
    
    # Convert side to move
    side_to_move = WHITE if board.turn == chess.WHITE else BLACK
    
    # Convert castling rights
    castling_rights = 0
    if board.has_kingside_castling_rights(chess.WHITE):
        castling_rights |= CR_WK
    if board.has_queenside_castling_rights(chess.WHITE):
        castling_rights |= CR_WQ
    if board.has_kingside_castling_rights(chess.BLACK):
        castling_rights |= CR_BK
    if board.has_queenside_castling_rights(chess.BLACK):
        castling_rights |= CR_BQ
    
    # Convert en passant square
    ep_sq = -1
    if board.ep_square is not None:
        ep_sq = board.ep_square
    
    # Create GameState
    state = GameState(
        board=our_board,
        side_to_move=side_to_move,
        castling_rights=castling_rights,
        ep_sq=ep_sq,
        halfmove_clock=board.halfmove_clock,
        fullmove_number=board.fullmove_number,
        undo_stack=[]
    )
    
    return state


def state_to_chess_board(state: GameState) -> chess.Board:
    """
    Convert our GameState to python-chess Board.
    
    Args:
        state: Our GameState object
        
    Returns:
        python-chess Board with equivalent position
    """
    # Start with empty board
    board = chess.Board(fen=None)
    board.clear()
    
    # Set pieces
    for sq, piece in enumerate(state.board):
        if piece != 0:
            piece_kind = abs(piece)
            color = chess.WHITE if piece > 0 else chess.BLACK
            chess_piece_type = OUR_TO_CHESS_PIECE[piece_kind]
            board.set_piece_at(sq, chess.Piece(chess_piece_type, color))
    
    # Set turn
    board.turn = chess.WHITE if state.side_to_move == WHITE else chess.BLACK
    
    # Set castling rights
    board.castling_rights = 0
    if state.castling_rights & CR_WK:
        board.castling_rights |= chess.BB_H1
    if state.castling_rights & CR_WQ:
        board.castling_rights |= chess.BB_A1
    if state.castling_rights & CR_BK:
        board.castling_rights |= chess.BB_H8
    if state.castling_rights & CR_BQ:
        board.castling_rights |= chess.BB_A8
    
    # Set en passant square
    board.ep_square = None if state.ep_sq == -1 else state.ep_sq
    
    # Set move counters
    board.halfmove_clock = state.halfmove_clock
    board.fullmove_number = state.fullmove_number
    
    return board


def generate_legal_moves_fast(state: GameState, side: int) -> List[Move]:
    """
    Generate legal moves using python-chess (much faster than our implementation).
    
    Args:
        state: Current game state
        side: Side to generate moves for
        
    Returns:
        List of legal moves in our Move format
    """
    # Convert to python-chess board
    board = state_to_chess_board(state)
    
    # Generate legal moves using python-chess
    chess_moves = list(board.legal_moves)
    
    # Convert to our Move format
    our_moves = []
    for chess_move in chess_moves:
        from_sq = chess_move.from_square
        to_sq = chess_move.to_square
        
        moving_piece = state.board[from_sq]
        moving_kind = abs(moving_piece)
        
        captured_piece = state.board[to_sq]
        captured_kind = abs(captured_piece) if captured_piece != 0 else 0
        
        is_capture = captured_piece != 0
        is_ep = board.is_en_passant(chess_move)
        is_castle = board.is_castling(chess_move)
        is_promotion = chess_move.promotion is not None
        
        our_move = Move(
            from_sq=from_sq,
            to_sq=to_sq,
            moving_kind=moving_kind,
            captured_kind=captured_kind,
            is_capture=is_capture or is_ep,
            is_ep=is_ep,
            is_castle=is_castle,
            is_promotion=is_promotion,
            promotion_kind=QUEEN  # Always promote to queen for now
        )
        our_moves.append(our_move)
    
    # Sort for deterministic order
    our_moves.sort(key=lambda m: m.uci())
    
    return our_moves

