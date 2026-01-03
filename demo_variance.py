#!/usr/bin/env python
"""Demo: Show variance feature in action."""

import sys
sys.path.insert(0, 'src')

from chess_metrics.engine.fen import parse_fen
from chess_metrics.engine.movegen import generate_legal_moves
from chess_metrics.cli import analyze_moves, display_move_options

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

def demo_variance_comparison():
    """Show the same position analyzed with and without variance."""
    print("=" * 95)
    print("VARIANCE FEATURE DEMONSTRATION")
    print("=" * 95)
    print()
    print("This demo shows how variance affects move evaluation.")
    print("We'll analyze the starting position twice:")
    print("  1. WITHOUT variance (all factors = 1.0)")
    print("  2. WITH variance (factors between 0.75 and 1.25)")
    print()
    
    state = parse_fen(START_FEN)
    legal = generate_legal_moves(state, state.side_to_move)
    
    # Analysis without variance
    print("=" * 95)
    print("ANALYSIS 1: WITHOUT VARIANCE")
    print("=" * 95)
    display_move_options(state, legal, "Demo Player", "White", apply_variance=False)
    
    input("\nPress Enter to see the same position WITH variance...")
    print()
    
    # Analysis with variance
    print("=" * 95)
    print("ANALYSIS 2: WITH VARIANCE")
    print("=" * 95)
    display_move_options(state, legal, "Demo Player", "White", apply_variance=True)
    
    print("\n" + "=" * 95)
    print("OBSERVATIONS")
    print("=" * 95)
    print()
    print("Notice the differences:")
    print("  1. Delta values (dPV, dMV, dOV, dDV) are now decimals")
    print("  2. Each move has a unique variance factor (Var column)")
    print("  3. Move rankings might change slightly due to variance")
    print("  4. Variance makes evaluations less deterministic")
    print()
    print("Example interpretations:")
    print("  - Var = 0.85: Move appears 15% weaker than base evaluation")
    print("  - Var = 1.00: No variance applied (neutral)")
    print("  - Var = 1.20: Move appears 20% stronger than base evaluation")
    print()
    print("This variance is saved to the database for each move,")
    print("allowing post-game analysis of how randomness affected play.")
    print()

def demo_variance_range():
    """Show the range of variance values."""
    print("=" * 95)
    print("VARIANCE RANGE DEMONSTRATION")
    print("=" * 95)
    print()
    
    from chess_metrics.cli import generate_variance
    
    # Generate many variance values
    variances = [generate_variance() for _ in range(1000)]
    
    print(f"Generated 1000 variance values:")
    print(f"  Minimum: {min(variances):.3f}")
    print(f"  Maximum: {max(variances):.3f}")
    print(f"  Average: {sum(variances)/len(variances):.3f}")
    print(f"  Expected range: [0.750, 1.250]")
    print()
    
    # Show distribution
    bins = {
        "0.75-0.85": 0,
        "0.85-0.95": 0,
        "0.95-1.05": 0,
        "1.05-1.15": 0,
        "1.15-1.25": 0,
    }
    
    for v in variances:
        if v < 0.85:
            bins["0.75-0.85"] += 1
        elif v < 0.95:
            bins["0.85-0.95"] += 1
        elif v < 1.05:
            bins["0.95-1.05"] += 1
        elif v < 1.15:
            bins["1.05-1.15"] += 1
        else:
            bins["1.15-1.25"] += 1
    
    print("Distribution:")
    for range_name, count in bins.items():
        pct = (count / 1000) * 100
        bar = "█" * int(pct / 2)
        print(f"  {range_name}: {count:4d} ({pct:5.1f}%) {bar}")
    print()
    print("The distribution should be roughly uniform across all ranges.")
    print()

def demo_variance_impact():
    """Show how variance affects specific moves."""
    print("=" * 95)
    print("VARIANCE IMPACT ON SPECIFIC MOVES")
    print("=" * 95)
    print()
    
    state = parse_fen(START_FEN)
    legal = generate_legal_moves(state, state.side_to_move)
    
    # Analyze the same position multiple times
    print("Analyzing move 'e2e4' five times with different variance:\n")
    
    for i in range(5):
        analysis = analyze_moves(state, legal, apply_variance=True)
        
        # Find e2e4
        for move, san, metrics, deltas, var in analysis:
            if move.uci() == "e2e4":
                dPV, dMV, dOV, dDV = deltas
                print(f"  Trial {i+1}: Var={var:.3f} → dPV={dPV:+6.1f}, dMV={dMV:+6.1f}, dOV={dOV:+6.1f}, dDV={dDV:+6.1f}")
                break
    
    print()
    print("Notice how the same move gets different evaluations each time!")
    print("This is what makes games with variance more varied and interesting.")
    print()

def main():
    """Run all demos."""
    print("\n" + "=" * 95)
    print(" " * 30 + "VARIANCE FEATURE DEMO")
    print("=" * 95)
    print()
    
    # Demo 1: Comparison
    demo_variance_comparison()
    
    input("Press Enter to continue to variance range demo...")
    print("\n")
    
    # Demo 2: Range
    demo_variance_range()
    
    input("Press Enter to continue to variance impact demo...")
    print("\n")
    
    # Demo 3: Impact
    demo_variance_impact()
    
    print("=" * 95)
    print("DEMO COMPLETE")
    print("=" * 95)
    print()
    print("To play a game with variance:")
    print("  $env:PYTHONPATH=\"src\"")
    print("  python -m chess_metrics.cli play-game")
    print()
    print("For more information, see VARIANCE_FEATURE.md")
    print()

if __name__ == "__main__":
    main()

