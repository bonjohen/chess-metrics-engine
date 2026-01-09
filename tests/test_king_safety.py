"""
Tests for king safety evaluation to prevent early king moves.
"""
import sys
sys.path.insert(0, 'src')

from chess_metrics.engine.fen import parse_fen
from chess_metrics.engine.search import choose_best_move, Profile, clear_transposition_table
from chess_metrics.engine.material_safety import evaluate_king_safety
from chess_metrics.engine.movegen import generate_legal_moves
from chess_metrics.engine.types import Move


def test_no_early_king_moves():
    """Test that AI doesn't move king in opening without good reason."""
    # Position after: 1.e4 e5 2.Qh4 Nc6 3.Bc4 Qf6 4.Nc3 Bb4 5.Qb4 Qb6 6.Qb6 ab6
    # This is where AI previously played Kf1 (terrible blunder)
    fen = 'r1b1kb1r/1ppp1ppp/1qn5/4p3/2B5/2N1P3/PPPP1PPP/R1B1K1NR w KQkq - 0 7'
    state = parse_fen(fen)
    
    # Test with board-coverage profile (most likely to make king moves for mobility)
    profile = Profile(name='board-coverage', wPV=1.0, wMV=2.0, wOV=1.0, wDV=1.0)
    
    clear_transposition_table()
    move = choose_best_move(state, profile, depthN=2)
    
    assert move is not None, "AI should find a legal move"
    
    # AI should NOT move the king (unless castling)
    if move.moving_kind == 6:  # KING
        # Check if it's castling
        is_castling = abs(move.from_sq - move.to_sq) == 2
        assert is_castling, f"AI moved king to {move.uci()} but it's not castling!"


def test_king_safety_penalties():
    """Test that king moves in opening are heavily penalized."""
    # Starting position
    fen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1'
    state = parse_fen(fen)
    
    # After 1.e4, white has king moves available
    state = parse_fen('rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 1')
    
    # Find king moves
    legal_moves = generate_legal_moves(state, state.side_to_move)
    king_moves = [m for m in legal_moves if m.moving_kind == 6]
    
    # There should be king moves available (Ke2)
    assert len(king_moves) > 0, "Should have king moves available"
    
    # All king moves should be penalized
    for km in king_moves:
        safety = evaluate_king_safety(state, km)
        assert safety < 0, f"King move {km.uci()} should be penalized (got {safety})"
        # Should be at least -3 (EARLY_KING_MOVE_PENALTY)
        assert safety <= -3.0, f"King move {km.uci()} penalty too small: {safety}"


def test_castling_not_penalized():
    """Test that castling is not penalized like regular king moves."""
    # Position where white can castle kingside
    fen = 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4'
    state = parse_fen(fen)
    
    # Find castling move (O-O = e1g1)
    legal_moves = generate_legal_moves(state, state.side_to_move)
    castling_move = None
    for m in legal_moves:
        if m.moving_kind == 6 and abs(m.from_sq - m.to_sq) == 2:
            castling_move = m
            break
    
    if castling_move:
        # Castling should still have some penalty but much less than regular king move
        safety = evaluate_king_safety(state, castling_move)
        # Castling gets EARLY_KING_MOVE_PENALTY (3.0) but not KING_EXPOSURE_PENALTY (5.0)
        # So it should be around -3.0, not -8.0
        assert safety >= -4.0, f"Castling penalty too high: {safety}"


def test_king_exposure_detection():
    """Test that king moves to exposed positions are penalized."""
    # Starting position - test moving king forward
    fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    state = parse_fen(fen)

    # Create a king move to e2 (forward from e1)
    # This should be detected as exposing the king
    from chess_metrics.engine.types import Move

    # King on e1 (square 4) moving to e2 (square 12)
    king_move = Move(from_sq=4, to_sq=12, moving_kind=6, is_capture=False)

    # Evaluate this king move
    safety = evaluate_king_safety(state, king_move)

    # Should be penalized for early king move (at least -3.0)
    assert safety <= -3.0, f"Early king move not penalized: {safety}"


def test_all_profiles_avoid_early_king_moves():
    """Test that all profiles avoid moving king in opening."""
    # Starting position
    fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    state = parse_fen(fen)
    
    profiles = [
        Profile(name='materialist', wPV=2.0, wMV=1.0, wOV=1.0, wDV=1.0),
        Profile(name='defense-first', wPV=1.0, wMV=1.0, wOV=0.5, wDV=2.0),
        Profile(name='offense-first', wPV=1.0, wMV=1.0, wOV=2.0, wDV=0.5),
        Profile(name='board-coverage', wPV=1.0, wMV=2.0, wOV=1.0, wDV=1.0),
    ]
    
    for profile in profiles:
        clear_transposition_table()
        move = choose_best_move(state, profile, depthN=2)
        
        assert move is not None, f"{profile.name} should find a legal move"
        
        # No profile should move king on move 1
        assert move.moving_kind != 6, f"{profile.name} moved king on move 1: {move.uci()}"


if __name__ == '__main__':
    print("Running king safety tests...")
    
    print("Test 1: No early king moves...")
    test_no_early_king_moves()
    print("  ✅ PASS")
    
    print("Test 2: King safety penalties...")
    test_king_safety_penalties()
    print("  ✅ PASS")
    
    print("Test 3: Castling not over-penalized...")
    test_castling_not_penalized()
    print("  ✅ PASS")
    
    print("Test 4: King exposure detection...")
    test_king_exposure_detection()
    print("  ✅ PASS")
    
    print("Test 5: All profiles avoid early king moves...")
    test_all_profiles_avoid_early_king_moves()
    print("  ✅ PASS")
    
    print()
    print("All king safety tests passed! ✅")

