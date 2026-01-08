#!/usr/bin/env python
"""Minimal test for batch game generation."""

import sys
import os
import tempfile
sys.path.insert(0, 'src')

from chess_metrics.db.repo import Repo
from chess_metrics.cli import OpeningTracker, play_silent_game, generate_batch_games, get_profile

def test_opening_tracker():
    """Test opening uniqueness detection."""
    print("Testing OpeningTracker...")
    
    tracker = OpeningTracker(uniqueness_depth=6)
    
    # Test 1: Same opening should be detected as duplicate
    opening1 = ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6"]
    opening2 = ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6"]
    
    assert tracker.add_opening(opening1) == True, "First opening should be unique"
    assert tracker.is_duplicate(opening2) == True, "Second opening should be duplicate"
    assert tracker.add_opening(opening2) == False, "Adding duplicate should return False"
    
    # Test 2: Different opening should be unique
    opening3 = ["d2d4", "d7d5", "c2c4", "e7e6", "b1c3", "g8f6"]
    assert tracker.is_duplicate(opening3) == False, "Different opening should be unique"
    assert tracker.add_opening(opening3) == True, "Different opening should be added"
    
    # Test 3: Stats
    stats = tracker.get_stats()
    assert stats["unique_openings"] == 2, f"Should have 2 unique openings, got {stats['unique_openings']}"
    assert stats["duplicates_rejected"] == 1, f"Should have 1 duplicate, got {stats['duplicates_rejected']}"
    
    print("✓ OpeningTracker tests passed!")

def test_silent_game():
    """Test silent game generation."""
    print("\nTesting silent game generation...")
    
    with tempfile.TemporaryDirectory() as td:
        dbp = os.path.join(td, "test.sqlite")
        repo = Repo.open(dbp)
        repo.migrate()
        repo.ensure_default_profiles()
        
        # Play a short game
        white_profile = get_profile("default")
        black_profile = get_profile("default")
        
        result = play_silent_game(
            repo, white_profile, black_profile,
            depth=1, max_moves=10
        )
        
        assert result.game_id > 0, "Game ID should be positive"
        assert result.moves_count > 0, "Should have made some moves"
        assert result.result in ["1-0", "0-1", "1/2-1/2"], f"Invalid result: {result.result}"
        assert len(result.opening_moves) == result.moves_count, "Opening moves count mismatch"
        
        # Verify database has the game
        cur = repo.conn.execute("SELECT COUNT(*) FROM games WHERE game_id=?", (result.game_id,))
        count = cur.fetchone()[0]
        assert count == 1, "Game should be in database"
        
        # Verify positions were saved
        cur = repo.conn.execute("SELECT COUNT(*) FROM positions WHERE game_id=?", (result.game_id,))
        pos_count = cur.fetchone()[0]
        assert pos_count == result.moves_count + 1, f"Should have {result.moves_count + 1} positions, got {pos_count}"
        
        # Verify moves were saved
        cur = repo.conn.execute("SELECT COUNT(*) FROM moves WHERE game_id=?", (result.game_id,))
        move_count = cur.fetchone()[0]
        assert move_count == result.moves_count, f"Should have {result.moves_count} moves, got {move_count}"
        
        repo.close()
        print(f"✓ Silent game test passed! (Game {result.game_id}: {result.result}, {result.moves_count} moves)")

def test_batch_generation():
    """Test batch game generation with uniqueness."""
    print("\nTesting batch generation...")
    
    with tempfile.TemporaryDirectory() as td:
        dbp = os.path.join(td, "test.sqlite")
        repo = Repo.open(dbp)
        repo.migrate()
        repo.ensure_default_profiles()
        
        # Generate 3 games
        result = generate_batch_games(
            repo=repo,
            count=3,
            white_profile_name="default",
            black_profile_name="default",
            depth=1,
            max_moves=10,
            uniqueness_depth=6,
            quiet=True
        )
        
        assert result.total_games == 3, f"Should have 3 games, got {result.total_games}"
        assert result.total_moves > 0, "Should have some moves"
        assert result.total_positions > result.total_moves, "Should have more positions than moves"
        
        # Verify all games are in database
        cur = repo.conn.execute("SELECT COUNT(*) FROM games")
        game_count = cur.fetchone()[0]
        assert game_count == 3, f"Should have 3 games in DB, got {game_count}"
        
        repo.close()
        print(f"✓ Batch generation test passed! ({result.total_games} games, {result.total_moves} moves)")

if __name__ == "__main__":
    print("=" * 80)
    print("BATCH GENERATION TESTS")
    print("=" * 80)
    
    try:
        test_opening_tracker()
        test_silent_game()
        test_batch_generation()
        
        print("\n" + "=" * 80)
        print("ALL TESTS PASSED! ✓")
        print("=" * 80)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

