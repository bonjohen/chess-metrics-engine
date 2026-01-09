#!/usr/bin/env python3
"""
Benchmark script to test the performance improvements from optimizations.
"""

import time
from chess_metrics.engine.fen import parse_fen
from chess_metrics.engine.search import choose_best_move, clear_transposition_table, Profile

# Test positions
POSITIONS = [
    ("Starting position", "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"),
    ("Middle game", "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"),
    ("Tactical position", "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 2 3"),
    ("Endgame", "8/5k2/3p4/1p1Pp2p/pP2Pp1P/P4P1K/8/8 b - - 99 50"),
]

PROFILES = [
    Profile("balanced", wPV=1.0, wMV=1.0, wOV=1.0, wDV=1.0),
    Profile("materialist", wPV=0.5, wMV=2.0, wOV=0.5, wDV=0.5),
]

def benchmark_position(fen: str, profile: Profile, depth: int = 4) -> tuple[float, str]:
    """
    Benchmark a single position.
    
    Returns:
        (time_taken, best_move_uci)
    """
    clear_transposition_table()
    state = parse_fen(fen)
    
    start = time.time()
    best_move = choose_best_move(state, profile, depth, use_iterative_deepening=True)
    elapsed = time.time() - start
    
    move_uci = best_move.uci() if best_move else "none"
    return elapsed, move_uci

def main():
    print("=" * 80)
    print("Chess Metrics Engine - Performance Benchmark")
    print("=" * 80)
    print("\nOptimizations enabled:")
    print("  ✓ Null Move Pruning")
    print("  ✓ PV Move Ordering")
    print("  ✓ Aspiration Windows")
    print("  ✓ Late Move Reduction")
    print("  ✓ Futility Pruning")
    print("  ✓ Transposition Table Improvements (bound types, depth-preferred replacement)")
    print()
    
    depths = [3, 4, 5]
    
    for depth in depths:
        print(f"\n{'=' * 80}")
        print(f"Depth {depth} Search")
        print(f"{'=' * 80}\n")
        
        total_time = 0.0
        total_positions = 0
        
        for pos_name, fen in POSITIONS:
            print(f"{pos_name}:")
            
            for profile in PROFILES:
                elapsed, move = benchmark_position(fen, profile, depth)
                total_time += elapsed
                total_positions += 1
                
                print(f"  {profile.name:20s}: {elapsed:6.3f}s -> {move}")
            
            print()
        
        avg_time = total_time / total_positions
        print(f"Average time per position: {avg_time:.3f}s")
        print(f"Total time: {total_time:.3f}s")
    
    print("\n" + "=" * 80)
    print("Benchmark complete!")
    print("=" * 80)

if __name__ == "__main__":
    main()

