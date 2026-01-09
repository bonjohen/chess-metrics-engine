"""
Test that AI doesn't make obvious blunders with material safety checks.
"""
import sys
sys.path.insert(0, 'src')

from chess_metrics.engine.fen import parse_fen
from chess_metrics.engine.search import choose_best_move, Profile, clear_transposition_table
from chess_metrics.engine.apply import apply_move
from chess_metrics.engine.types import PIECE_VALUE

# Test with offense-first profile (most likely to blunder)
profile = Profile(name='offense-first', wPV=1.0, wMV=1.0, wOV=2.0, wDV=0.5)

# Starting position
fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
state = parse_fen(fen)

print('Testing AI with offense-first profile...')
print('=' * 60)

for move_num in range(1, 6):
    clear_transposition_table()
    
    side_name = "White" if state.side_to_move == 1 else "Black"
    print(f'\nMove {move_num} ({side_name} to move):')
    
    # Count material before move
    material_before = {}
    for piece_val in range(1, 7):
        material_before[piece_val] = sum(1 for p in state.board if abs(p) == piece_val)
    
    # Get AI move
    move = choose_best_move(state, profile, depthN=2)
    
    if not move:
        print('  No legal moves (game over)')
        break
    
    print(f'  AI chose: {move.uci()}')
    
    # Apply move
    undo_info = apply_move(state, move)
    
    # Count material after move
    material_after = {}
    for piece_val in range(1, 7):
        material_after[piece_val] = sum(1 for p in state.board if abs(p) == piece_val)
    
    # Check for material loss
    material_lost = 0
    for piece_val in range(1, 7):
        diff = material_before[piece_val] - material_after[piece_val]
        if diff > 0:
            material_lost += diff * PIECE_VALUE[piece_val]
            piece_names = {1: 'Pawn', 2: 'Knight', 3: 'Bishop', 4: 'Rook', 5: 'Queen', 6: 'King'}
            print(f'  Warning: Lost {diff} {piece_names[piece_val]}(s) = {diff * PIECE_VALUE[piece_val]} points')
    
    if material_lost == 0:
        print(f'  OK: No material lost')
    elif material_lost > 5:
        print(f'  BLUNDER: Lost {material_lost} points of material!')
    
print()
print('=' * 60)
print('Test complete!')

