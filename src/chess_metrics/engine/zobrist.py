"""
Zobrist hashing for fast position fingerprinting.

Zobrist hashing uses precomputed random numbers to create a unique hash
for each chess position. This is much faster than FEN string generation
and provides O(1) hash computation.
"""
from __future__ import annotations
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import GameState

# Zobrist hash tables (initialized once at module load)
# We use 64-bit integers for hash values

# Piece-square table: [square][piece_type]
# piece_type ranges from -6 to +6 (BLACK_KING to WHITE_KING)
# We offset by 6 to get array index 0-12
ZOBRIST_PIECES = [[0] * 13 for _ in range(64)]

# Castling rights: [castling_rights_bitmask]
ZOBRIST_CASTLING = [0] * 16  # 4 bits = 16 possible states

# En passant file: [file + 1]  (0 = no EP, 1-8 = files a-h)
ZOBRIST_EP = [0] * 9

# Side to move
ZOBRIST_SIDE = [0, 0]  # [0] = WHITE, [1] = BLACK

# Initialize with random 64-bit values
_SEED = 0x123456789ABCDEF0  # Fixed seed for reproducibility
_rng = random.Random(_SEED)

def _random_u64() -> int:
    """Generate a random 64-bit unsigned integer."""
    return _rng.getrandbits(64)

# Initialize all Zobrist tables
for sq in range(64):
    for piece_idx in range(13):
        ZOBRIST_PIECES[sq][piece_idx] = _random_u64()

for i in range(16):
    ZOBRIST_CASTLING[i] = _random_u64()

for i in range(9):
    ZOBRIST_EP[i] = _random_u64()

ZOBRIST_SIDE[0] = _random_u64()
ZOBRIST_SIDE[1] = _random_u64()


def zobrist_hash(state: GameState) -> int:
    """
    Compute Zobrist hash for a position.
    
    This is much faster than FEN string generation:
    - FEN: O(64) string operations + allocations
    - Zobrist: O(32) XOR operations (only occupied squares)
    
    Args:
        state: Game state to hash
        
    Returns:
        64-bit hash value
    """
    h = 0
    
    # Hash pieces on board
    for sq, piece in enumerate(state.board):
        if piece != 0:
            # Convert piece value (-6 to +6) to array index (0 to 12)
            piece_idx = piece + 6
            h ^= ZOBRIST_PIECES[sq][piece_idx]
    
    # Hash castling rights
    h ^= ZOBRIST_CASTLING[state.castling_rights]
    
    # Hash en passant square
    # Convert -1 (no EP) to 0, and 0-63 to file+1
    ep_idx = 0 if state.ep_sq == -1 else (state.ep_sq % 8) + 1
    h ^= ZOBRIST_EP[ep_idx]
    
    # Hash side to move
    side_idx = 0 if state.side_to_move == 1 else 1  # WHITE=1 -> idx 0, BLACK=-1 -> idx 1
    h ^= ZOBRIST_SIDE[side_idx]
    
    return h


def incremental_hash_move(prev_hash: int, state: GameState, from_sq: int, to_sq: int, 
                          moved_piece: int, captured_piece: int = 0) -> int:
    """
    Update Zobrist hash incrementally after a move.
    
    This is even faster than full hash computation - only XOR the changed squares.
    
    Args:
        prev_hash: Hash before the move
        state: Current game state (after move)
        from_sq: Source square
        to_sq: Destination square
        moved_piece: Piece that moved
        captured_piece: Piece that was captured (0 if none)
        
    Returns:
        Updated hash value
    """
    h = prev_hash
    
    # Remove piece from source square
    piece_idx = moved_piece + 6
    h ^= ZOBRIST_PIECES[from_sq][piece_idx]
    
    # Remove captured piece from destination (if any)
    if captured_piece != 0:
        cap_idx = captured_piece + 6
        h ^= ZOBRIST_PIECES[to_sq][cap_idx]
    
    # Add piece to destination square
    h ^= ZOBRIST_PIECES[to_sq][piece_idx]
    
    # Toggle side to move
    h ^= ZOBRIST_SIDE[0]
    h ^= ZOBRIST_SIDE[1]
    
    # Note: Castling rights and EP square changes would need to be handled separately
    # For now, we'll use full hash computation when those change
    
    return h

