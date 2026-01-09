"""
Material safety evaluation to prevent AI blunders.

This module provides functions to:
1. Detect undefended pieces under attack
2. Evaluate material risk after a move
3. Prevent obvious material losses (queen sacrifices, hanging pieces)
4. Evaluate king safety (exposure, early movement, lack of castling)
"""
from __future__ import annotations
from typing import List, Tuple
from .types import GameState, Move, PIECE_VALUE, piece_color, piece_kind, opposite
from .rules import is_square_attacked, is_in_check, pseudo_attacks_square
from .apply import apply_move, undo_move


# King safety constants
KING_EXPOSURE_PENALTY = 5.0  # Penalty for exposed king (equivalent to losing a rook)
EARLY_KING_MOVE_PENALTY = 3.0  # Penalty for moving king in opening
KING_ATTACK_ZONE_PENALTY = 1.0  # Penalty per attacker near king


def is_piece_defended(state: GameState, square: int, by_side: int) -> bool:
    """
    Check if a piece at the given square is defended by any piece of the given side.
    
    Args:
        state: Current game state
        square: Square to check
        by_side: Side that should be defending (WHITE or BLACK)
        
    Returns:
        True if the piece is defended by at least one friendly piece
    """
    board = state.board
    
    # Find all friendly pieces
    for sq, piece in enumerate(board):
        if piece == 0:
            continue
        if piece_color(piece) != by_side:
            continue
        if sq == square:
            continue
            
        # Check if this piece can pseudo-attack the target square
        if not pseudo_attacks_square(state, sq, square):
            continue
            
        # Simulate the defensive move to ensure it doesn't leave king in check
        moved = board[sq]
        captured = board[square]
        board[square] = moved
        board[sq] = 0
        
        # Check if this defense is legal (doesn't expose our king)
        legal = not is_in_check(state, by_side)
        
        # Undo the simulation
        board[sq] = moved
        board[square] = captured
        
        if legal:
            return True
    
    return False


def evaluate_hanging_pieces(state: GameState, side: int) -> float:
    """
    Evaluate the material value of hanging (undefended and attacked) pieces.
    
    Args:
        state: Current game state
        side: Side whose pieces to evaluate
        
    Returns:
        Total value of hanging pieces (negative = bad)
    """
    board = state.board
    opponent = opposite(side)
    hanging_value = 0.0
    
    # Check each of our pieces
    for sq, piece in enumerate(board):
        if piece == 0:
            continue
        if piece_color(piece) != side:
            continue
            
        # Skip kings (they can't really "hang")
        kind = piece_kind(piece)
        if kind == 6:  # KING
            continue
            
        # Check if piece is under attack
        if is_square_attacked(state, sq, opponent):
            # Check if piece is defended
            if not is_piece_defended(state, sq, side):
                # Piece is hanging!
                hanging_value += PIECE_VALUE[kind]
    
    return -hanging_value  # Negative because it's bad


def evaluate_material_safety(state: GameState, move: Move) -> float:
    """
    Evaluate material safety after making a move.

    This checks if the move:
    1. Leaves pieces hanging (undefended and under attack)
    2. Moves a piece to an attacked square without adequate defense
    3. Exposes pieces to attack by moving defenders
    4. Compromises king safety (exposure, early movement)

    Args:
        state: Current game state (before move)
        move: Move to evaluate

    Returns:
        Safety score (negative = unsafe, 0 = safe)
        - Returns large negative values for moves that lose material or expose king
    """
    side = state.side_to_move

    # Apply the move
    undo_info = apply_move(state, move)

    # Evaluate hanging pieces after the move
    safety_score = evaluate_hanging_pieces(state, side)

    # Check if the moved piece itself is now hanging
    # (moved to an attacked square without defense)
    if not move.is_capture:  # If it's a capture, we already got the piece
        if is_square_attacked(state, move.to_sq, opposite(side)):
            if not is_piece_defended(state, move.to_sq, side):
                # The piece we just moved is now hanging!
                moved_value = PIECE_VALUE[move.moving_kind]
                safety_score -= moved_value

    # Undo the move
    undo_move(state, undo_info)

    # Evaluate king safety (this applies the move internally)
    king_safety = evaluate_king_safety(state, move)
    safety_score += king_safety

    return safety_score


def has_adequate_compensation(state: GameState, move: Move, material_loss: float) -> bool:
    """
    Check if a move that loses material has adequate compensation.

    Compensation can be:
    - Checkmate threat
    - Winning back more material
    - Forcing opponent into bad position

    Args:
        state: Current game state
        move: Move being considered
        material_loss: How much material is being lost

    Returns:
        True if the sacrifice has adequate compensation
    """
    # For now, we'll use a simple heuristic:
    # - Sacrifices of 3+ points need to deliver checkmate or win material back
    # - This is a placeholder for more sophisticated analysis

    if material_loss < 3.0:
        # Small sacrifices might be tactical
        return True

    # Apply the move
    undo_info = apply_move(state, move)

    # Check if opponent is in checkmate
    opponent = opposite(state.side_to_move)
    if is_in_check(state, opponent):
        # If we're giving check, the sacrifice might be justified
        # (This is a simplification - we'd need to check if it leads to mate)
        undo_move(state, undo_info)
        return True

    # Undo the move
    undo_move(state, undo_info)

    # For now, assume large sacrifices without immediate check are bad
    return False


def find_king_square(state: GameState, side: int) -> int:
    """
    Find the square where the king of the given side is located.

    Args:
        state: Current game state
        side: Side whose king to find (WHITE or BLACK)

    Returns:
        Square index where the king is located, or -1 if not found
    """
    board = state.board
    for sq, piece in enumerate(board):
        if piece == 0:
            continue
        if piece_color(piece) == side and piece_kind(piece) == 6:  # KING
            return sq
    return -1


def count_attackers_near_king(state: GameState, king_sq: int, side: int) -> int:
    """
    Count how many enemy pieces are attacking squares near the king.

    Args:
        state: Current game state
        king_sq: Square where the king is located
        side: Side whose king it is

    Returns:
        Number of enemy pieces attacking the king's zone
    """
    opponent = opposite(side)

    # Define king zone (king square + adjacent squares)
    king_zone = [king_sq]
    rank = king_sq // 8
    file = king_sq % 8

    # Add adjacent squares
    for dr in [-1, 0, 1]:
        for df in [-1, 0, 1]:
            if dr == 0 and df == 0:
                continue
            new_rank = rank + dr
            new_file = file + df
            if 0 <= new_rank < 8 and 0 <= new_file < 8:
                king_zone.append(new_rank * 8 + new_file)

    # Count unique attackers
    attackers = set()
    for sq in king_zone:
        # Find all enemy pieces attacking this square
        for attacker_sq, piece in enumerate(state.board):
            if piece == 0:
                continue
            if piece_color(piece) != opponent:
                continue
            if pseudo_attacks_square(state, attacker_sq, sq):
                attackers.add(attacker_sq)

    return len(attackers)


def is_king_exposed(state: GameState, king_sq: int, side: int) -> bool:
    """
    Check if the king is dangerously exposed.

    A king is considered exposed if:
    1. It's not on the back rank (moved forward)
    2. It has few friendly pieces nearby for protection
    3. It's under attack or near attacked squares

    Args:
        state: Current game state
        king_sq: Square where the king is located
        side: Side whose king it is

    Returns:
        True if the king is dangerously exposed
    """
    rank = king_sq // 8
    back_rank = 0 if side == 1 else 7  # WHITE=1 starts at rank 0, BLACK=-1 at rank 7

    # Check if king has moved from back rank
    if rank != back_rank:
        # King has moved forward - check if it's in danger
        opponent = opposite(side)

        # Count friendly pieces nearby
        friendly_nearby = 0
        for dr in [-1, 0, 1]:
            for df in [-1, 0, 1]:
                if dr == 0 and df == 0:
                    continue
                new_rank = rank + dr
                new_file = (king_sq % 8) + df
                if 0 <= new_rank < 8 and 0 <= new_file < 8:
                    sq = new_rank * 8 + new_file
                    piece = state.board[sq]
                    if piece != 0 and piece_color(piece) == side:
                        friendly_nearby += 1

        # If king is forward with few defenders, it's exposed
        if friendly_nearby < 2:
            return True

        # Check if king is under direct attack
        if is_square_attacked(state, king_sq, opponent):
            return True

    return False


def evaluate_king_safety(state: GameState, move: Move) -> float:
    """
    Evaluate king safety after making a move.

    This penalizes:
    1. Moving the king in the opening (before castling)
    2. Exposing the king to attack
    3. Moving the king to a square with many nearby attackers

    Args:
        state: Current game state (before move)
        move: Move to evaluate

    Returns:
        Safety score (negative = unsafe, 0 = safe)
    """
    side = state.side_to_move
    safety_penalty = 0.0

    # Check if this is a king move
    is_king_move = (move.moving_kind == 6)

    # Apply the move
    undo_info = apply_move(state, move)

    # Find king position after move
    king_sq = find_king_square(state, side)
    if king_sq == -1:
        # King not found (shouldn't happen)
        undo_move(state, undo_info)
        return 0.0

    # Penalty 1: Moving king in opening (before move 10 or so)
    if is_king_move and state.fullmove_number < 10:
        # Check if this is castling (castling is OK)
        is_castling = abs(move.from_sq - move.to_sq) == 2
        if not is_castling:
            safety_penalty += EARLY_KING_MOVE_PENALTY

    # Penalty 2: King exposure
    if is_king_exposed(state, king_sq, side):
        safety_penalty += KING_EXPOSURE_PENALTY

    # Penalty 3: Attackers near king
    num_attackers = count_attackers_near_king(state, king_sq, side)
    if num_attackers >= 3:
        # Multiple attackers near king is very dangerous
        safety_penalty += KING_ATTACK_ZONE_PENALTY * num_attackers

    # Undo the move
    undo_move(state, undo_info)

    return -safety_penalty  # Negative because it's bad

