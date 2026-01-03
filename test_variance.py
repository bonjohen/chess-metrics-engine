#!/usr/bin/env python
"""Test variance feature in metrics."""

import sys
import os
import tempfile
sys.path.insert(0, 'src')

from chess_metrics.db.repo import Repo
from chess_metrics.engine.fen import parse_fen
from chess_metrics.engine.movegen import generate_legal_moves
from chess_metrics.engine.apply import apply_move
from chess_metrics.engine.metrics import compute_metrics
from chess_metrics.engine.san import move_to_san
from chess_metrics.engine.types import sq_to_alg
from chess_metrics.cli import generate_variance, analyze_moves

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

def test_variance_generation():
    """Test that variance is generated in the correct range."""
    print("=" * 80)
    print("TEST 1: Variance Generation")
    print("=" * 80)
    
    # Generate 100 variance values
    variances = [generate_variance() for _ in range(100)]
    
    # Check all are in range
    for v in variances:
        assert 0.75 <= v <= 1.25, f"Variance {v} out of range [0.75, 1.25]"
    
    min_v = min(variances)
    max_v = max(variances)
    avg_v = sum(variances) / len(variances)
    
    print(f"Generated 100 variance values:")
    print(f"  Min: {min_v:.3f}")
    print(f"  Max: {max_v:.3f}")
    print(f"  Avg: {avg_v:.3f}")
    print(f"  Expected range: [0.75, 1.25]")
    
    assert min_v >= 0.75, "Min variance too low"
    assert max_v <= 1.25, "Max variance too high"
    
    print("✅ PASS: All variance values in correct range\n")
    return True

def test_variance_in_analysis():
    """Test that variance is applied in move analysis."""
    print("=" * 80)
    print("TEST 2: Variance in Move Analysis")
    print("=" * 80)
    
    state = parse_fen(START_FEN)
    legal = generate_legal_moves(state, state.side_to_move)
    
    # Analyze without variance
    analysis_no_var = analyze_moves(state, legal, apply_variance=False)
    
    # Analyze with variance
    analysis_with_var = analyze_moves(state, legal, apply_variance=True)
    
    print(f"Analyzed {len(legal)} moves")
    
    # Check that variance factors are different
    variance_factors = [v for _, _, _, _, v in analysis_with_var]
    
    # Without variance, all should be 1.0
    no_var_factors = [v for _, _, _, _, v in analysis_no_var]
    assert all(v == 1.0 for v in no_var_factors), "No-variance should have all 1.0"
    
    # With variance, should have variety
    assert not all(v == 1.0 for v in variance_factors), "Variance should not all be 1.0"
    assert all(0.75 <= v <= 1.25 for v in variance_factors), "All variance in range"
    
    print(f"✅ PASS: Variance correctly applied")
    print(f"  Without variance: all factors = 1.0")
    print(f"  With variance: factors range [{min(variance_factors):.2f}, {max(variance_factors):.2f}]")
    
    # Show example
    print("\nExample move with variance:")
    move, san, metrics, deltas, var = analysis_with_var[0]
    dPV, dMV, dOV, dDV = deltas
    print(f"  Move: {move.uci()} ({san})")
    print(f"  Variance: {var:.3f}")
    print(f"  Deltas: dPV={dPV:+.1f}, dMV={dMV:+.1f}, dOV={dOV:+.1f}, dDV={dDV:+.1f}")
    print()
    
    return True

def test_variance_in_database():
    """Test that variance is saved to database."""
    print("=" * 80)
    print("TEST 3: Variance in Database")
    print("=" * 80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_var.db")
        repo = Repo.open(db_path)
        
        # Initialize
        repo.migrate()
        repo.ensure_default_profiles()
        
        # Create game
        white_pid = repo.create_player("TestWhite", "human")
        black_pid = repo.create_player("TestBlack", "human")
        game_id = repo.create_game(white_pid, black_pid, START_FEN)
        
        # Save initial position
        state = parse_fen(START_FEN)
        met = compute_metrics(state)
        repo.insert_position(
            game_id, 0, "W", START_FEN, None, None,
            met.pv_w, met.mv_w, met.ov_w, met.dv_w,
            met.pv_b, met.mv_b, met.ov_b, met.dv_b
        )
        repo.commit()
        
        # Make a move with variance
        legal = generate_legal_moves(state, state.side_to_move)
        move = legal[0]
        san = move_to_san(state, move)
        variance = 0.95  # Test value
        
        apply_move(state, move)
        
        # Save move with variance
        from_alg = sq_to_alg(move.from_sq)
        to_alg = sq_to_alg(move.to_sq)
        repo.insert_move(
            game_id, 1, move.uci(), san, from_alg, to_alg,
            1 if (move.is_capture or move.is_ep) else 0,
            1 if move.is_ep else 0,
            1 if move.is_castle else 0,
            1 if move.is_promotion else 0,
            "Q" if move.is_promotion else None,
            variance
        )
        repo.commit()
        
        # Retrieve and verify
        cur = repo.conn.execute(
            "SELECT variance_factor FROM moves WHERE game_id=? AND ply=1",
            (game_id,)
        )
        row = cur.fetchone()
        
        assert row is not None, "Move not found"
        saved_variance = row['variance_factor']
        
        print(f"Saved variance: {variance}")
        print(f"Retrieved variance: {saved_variance}")
        
        assert abs(saved_variance - variance) < 0.001, "Variance mismatch"
        
        print("✅ PASS: Variance correctly saved and retrieved from database")
        
        repo.close()
    
    print()
    return True

def test_decimal_metrics():
    """Test that metrics can be stored as decimals."""
    print("=" * 80)
    print("TEST 4: Decimal Metrics in Database")
    print("=" * 80)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_decimal.db")
        repo = Repo.open(db_path)
        
        # Initialize
        repo.migrate()
        repo.ensure_default_profiles()
        
        # Create game
        white_pid = repo.create_player("TestWhite", "human")
        black_pid = repo.create_player("TestBlack", "human")
        game_id = repo.create_game(white_pid, black_pid, START_FEN)
        
        # Save position with decimal metrics
        test_metrics = {
            'pv_w': 39.5, 'mv_w': 20.3, 'ov_w': 5.7, 'dv_w': 35.2,
            'pv_b': 38.8, 'mv_b': 19.6, 'ov_b': 4.9, 'dv_b': 34.1
        }
        
        repo.insert_position(
            game_id, 0, "W", START_FEN, None, None,
            test_metrics['pv_w'], test_metrics['mv_w'], test_metrics['ov_w'], test_metrics['dv_w'],
            test_metrics['pv_b'], test_metrics['mv_b'], test_metrics['ov_b'], test_metrics['dv_b']
        )
        repo.commit()
        
        # Retrieve and verify
        timeline = repo.timeline(game_id)
        assert len(timeline) == 1, "Should have 1 position"
        
        pos = timeline[0]
        
        print("Saved metrics:")
        for key, val in test_metrics.items():
            print(f"  {key}: {val}")
        
        print("\nRetrieved metrics:")
        for key in test_metrics.keys():
            retrieved = pos[key]
            print(f"  {key}: {retrieved}")
            assert abs(retrieved - test_metrics[key]) < 0.01, f"{key} mismatch"
        
        print("\n✅ PASS: Decimal metrics correctly saved and retrieved")
        
        repo.close()
    
    print()
    return True

def main():
    """Run all variance tests."""
    print("\n" + "=" * 80)
    print("VARIANCE FEATURE TEST SUITE")
    print("=" * 80 + "\n")
    
    tests = [
        test_variance_generation,
        test_variance_in_analysis,
        test_variance_in_database,
        test_decimal_metrics,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, True, None))
        except Exception as e:
            results.append((test.__name__, False, str(e)))
            print(f"\n❌ FAIL: {e}\n")
    
    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for name, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {name}")
        if error:
            print(f"  Error: {error}")
    
    print("=" * 80)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 80)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

