"""
Performance benchmarking script for Chess Metrics Engine.

Runs standardized tests to measure performance of key operations:
- Move generation
- Metrics computation
- AI search at various depths
- Database operations
"""
import time
import sys
import logging
from pathlib import Path

# Disable profiling logging during benchmarks
logging.getLogger('chess_metrics.web.profiling').setLevel(logging.WARNING)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from chess_metrics.engine.fen import parse_fen
from chess_metrics.engine.movegen import generate_legal_moves
from chess_metrics.engine.metrics import compute_metrics
from chess_metrics.engine.search import choose_best_move, Profile, clear_transposition_table
from chess_metrics.engine.types import WHITE, BLACK
from chess_metrics.web.profiling import get_timing_stats, clear_timing_data, print_timing_report


def benchmark_move_generation(iterations=100):
    """Benchmark move generation speed."""
    print("\n" + "="*80)
    print("BENCHMARK: Move Generation")
    print("="*80)
    
    positions = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # Starting position
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",  # Italian Game
        "rnbqkb1r/pp1p1ppp/4pn2/2p5/2PP4/5NP1/PP2PP1P/RNBQKB1R w KQkq - 0 4",  # Catalan
        "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 6 7",  # Middlegame
    ]
    
    total_time = 0
    total_moves = 0
    
    for fen in positions:
        state = parse_fen(fen)
        start = time.perf_counter()
        
        for _ in range(iterations):
            moves = generate_legal_moves(state, state.side_to_move)
            total_moves += len(moves)
        
        elapsed = time.perf_counter() - start
        total_time += elapsed
        
        print(f"Position: {fen[:50]}...")
        print(f"  Moves: {len(moves)}")
        print(f"  Time: {elapsed*1000:.2f}ms for {iterations} iterations")
        print(f"  Avg: {elapsed*1000/iterations:.3f}ms per generation")
    
    print(f"\nTotal: {total_time*1000:.2f}ms, Avg: {total_time*1000/(iterations*len(positions)):.3f}ms")
    return total_time


def benchmark_metrics_computation(iterations=50):
    """Benchmark metrics computation speed."""
    print("\n" + "="*80)
    print("BENCHMARK: Metrics Computation")
    print("="*80)
    
    positions = [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "rnbqkb1r/pp1p1ppp/4pn2/2p5/2PP4/5NP1/PP2PP1P/RNBQKB1R w KQkq - 0 4",
        "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 6 7",
    ]
    
    total_time = 0
    
    for fen in positions:
        state = parse_fen(fen)
        start = time.perf_counter()
        
        for _ in range(iterations):
            metrics = compute_metrics(state)
        
        elapsed = time.perf_counter() - start
        total_time += elapsed
        
        print(f"Position: {fen[:50]}...")
        print(f"  Time: {elapsed*1000:.2f}ms for {iterations} iterations")
        print(f"  Avg: {elapsed*1000/iterations:.3f}ms per computation")
    
    print(f"\nTotal: {total_time*1000:.2f}ms, Avg: {total_time*1000/(iterations*len(positions)):.3f}ms")
    return total_time


def benchmark_ai_search(depths=[1, 2, 3]):
    """Benchmark AI search at various depths."""
    print("\n" + "="*80)
    print("BENCHMARK: AI Search")
    print("="*80)
    
    # Use a middlegame position for realistic testing
    fen = "r1bq1rk1/ppp2ppp/2np1n2/2b1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 6 7"
    state = parse_fen(fen)
    profile = Profile("default", 1.0, 1.0, 1.0, 1.0)
    
    print(f"Position: {fen}")
    print(f"Profile: {profile.name}")
    print()
    
    for depth in depths:
        clear_transposition_table()
        clear_timing_data()
        
        start = time.perf_counter()
        move = choose_best_move(state, profile, depth)
        elapsed = time.perf_counter() - start
        
        print(f"Depth {depth}:")
        print(f"  Best move: {move.uci() if move else 'None'}")
        print(f"  Time: {elapsed*1000:.2f}ms ({elapsed:.2f}s)")
        print(f"  Nodes/sec: ~{int(1000/elapsed) if elapsed > 0 else 'N/A'}")
        print()


def benchmark_database_operations():
    """Benchmark database query performance."""
    print("\n" + "="*80)
    print("BENCHMARK: Database Operations")
    print("="*80)
    
    try:
        from chess_metrics.db.repo import Repo
        
        repo = Repo.open("chess.sqlite")
        game_ids = repo.get_all_game_ids()
        
        if not game_ids:
            print("No games in database. Skipping database benchmarks.")
            repo.close()
            return
        
        # Test get_game_for_analysis
        test_id = game_ids[0]
        iterations = 10
        
        start = time.perf_counter()
        for _ in range(iterations):
            data = repo.get_game_for_analysis(test_id)
        elapsed = time.perf_counter() - start
        
        print(f"get_game_for_analysis (game {test_id}):")
        print(f"  Time: {elapsed*1000:.2f}ms for {iterations} iterations")
        print(f"  Avg: {elapsed*1000/iterations:.3f}ms per query")
        
        repo.close()
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run all benchmarks."""
    print("\n" + "="*80)
    print(" " * 25 + "PERFORMANCE BENCHMARK SUITE")
    print("="*80)
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    benchmark_move_generation(iterations=100)
    benchmark_metrics_computation(iterations=50)
    benchmark_ai_search(depths=[1, 2, 3])
    benchmark_database_operations()
    
    print("\n" + "="*80)
    print("PROFILING REPORT (from AI search)")
    print("="*80)
    print_timing_report()
    
    print("\n" + "="*80)
    print("BENCHMARK COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()

