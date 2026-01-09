"""
Test that AI doesn't make terrible king moves like Kf1 in the opening.
"""
import sys
sys.path.insert(0, 'src')

from chess_metrics.engine.fen import parse_fen
from chess_metrics.engine.search import choose_best_move, Profile, clear_transposition_table
from chess_metrics.engine.apply import apply_move
from chess_metrics.engine.movegen import generate_legal_moves

# Test the exact position where AI played Kf1
# Position after: 1.e4 e5 2.Qh4 Nc6 3.Bc4 Qf6 4.Nc3 Bb4 5.Qb4 Qb6 6.Qb6 ab6
fen = 'r1b1kb1r/1ppp1ppp/1qn5/4p3/2B5/2N1P3/PPPP1PPP/R1B1K1NR w KQkq - 0 7'
state = parse_fen(fen)

print('Testing King Safety Fix')
print('=' * 70)
print(f'Position: {fen}')
print()
print('This is the position where AI previously played Kf1 (terrible blunder)')
print()

# Test with board-coverage profile (the one that made the blunder)
profile = Profile(name='board-coverage', wPV=1.0, wMV=2.0, wOV=1.0, wDV=1.0)

clear_transposition_table()

print(f'Testing with {profile.name} profile (wMV=2.0 - prioritizes mobility)')
print()

# Get AI move
move = choose_best_move(state, profile, depthN=2)

if not move:
    print('ERROR: No legal moves found!')
    sys.exit(1)

print(f'AI chose: {move.uci()}')
print()

# Check if it's a king move
if move.moving_kind == 6:  # KING
    print('⚠️  WARNING: AI chose a king move!')
    print()
    
    # Check if it's castling
    is_castling = abs(move.from_sq - move.to_sq) == 2
    if is_castling:
        print('✅ OK: King move is castling (acceptable)')
    else:
        print('❌ FAIL: King move is NOT castling (should be penalized heavily)')
        print(f'   King moved from {move.from_sq} to {move.to_sq}')
        print('   This should have been prevented by king safety checks!')
        sys.exit(1)
else:
    print('✅ PASS: AI did NOT move the king')
    print('   King safety checks are working!')

print()
print('=' * 70)

# Also test that we can see all legal moves and their evaluations
print()
print('Analyzing all legal moves to verify king safety penalties:')
print()

legal_moves = generate_legal_moves(state, state.side_to_move)
print(f'Found {len(legal_moves)} legal moves')

# Find king moves
king_moves = [m for m in legal_moves if m.moving_kind == 6]
if king_moves:
    print(f'King moves available: {[m.uci() for m in king_moves]}')
    print('These should be heavily penalized by king safety evaluation')

    # Test king safety evaluation on Kf1
    from chess_metrics.engine.material_safety import evaluate_king_safety
    for km in king_moves:
        safety = evaluate_king_safety(state, km)
        print(f'  {km.uci()}: king safety score = {safety:.2f}')
else:
    print('No king moves available in this position')

print()
print('Test complete!')

