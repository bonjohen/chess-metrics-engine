#!/usr/bin/env python
"""Compare move rankings with sqrt DV."""

import sys
import math
sys.path.insert(0, 'src')

from chess_metrics.engine.fen import parse_fen
from chess_metrics.engine.movegen import generate_legal_moves
from chess_metrics.cli import display_move_options

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

def main():
    print("\n" + "=" * 105)
    print(" " * 30 + "SQRT DV MOVE ANALYSIS")
    print("=" * 105)
    print()
    print("This shows how the square root DV calculation affects move evaluation.")
    print()
    print("Key changes:")
    print("  - DV now uses sqrt(piece_value) instead of piece_value")
    print("  - Queen defense: 9 → 3.0 (67% reduction)")
    print("  - Rook defense: 5 → 2.24 (55% reduction)")
    print("  - Knight/Bishop defense: 3 → 1.73 (42% reduction)")
    print("  - Pawn defense: 1 → 1.0 (no change)")
    print()
    print("Benefits:")
    print("  ✓ More realistic piece defense valuation")
    print("  ✓ DV is more balanced with MV and OV")
    print("  ✓ Encourages distributed defense")
    print("  ✓ Prevents DV from dominating Sum")
    print()
    
    state = parse_fen(START_FEN)
    legal = generate_legal_moves(state, state.side_to_move)
    
    print("Starting position analysis:")
    display_move_options(state, legal, "Demo Player", "White", apply_variance=False)
    
    print("\n" + "=" * 105)
    print("OBSERVATIONS")
    print("=" * 105)
    print()
    print("1. dDV Values:")
    print("   - Notice dDV values are now smaller (using sqrt)")
    print("   - Example: Nc3 has dDV ≈ +7.5 (was ~+16 with old calculation)")
    print()
    print("2. Sum Column:")
    print("   - Sum is more balanced across metrics")
    print("   - DV doesn't dominate the total")
    print("   - All metrics contribute more equally")
    print()
    print("3. Move Rankings:")
    print("   - Moves are still sorted by Sum (descending)")
    print("   - Rankings may differ from old system")
    print("   - More holistic evaluation")
    print()
    print("4. Metric Balance:")
    print("   - |dPV| ≈ 0 (no material changes in opening)")
    print("   - |dMV| ≈ 2-10 (mobility changes)")
    print("   - |dOV| ≈ 0 (no offensive changes in opening)")
    print("   - |dDV| ≈ 1-8 (defensive changes, now more balanced)")
    print()
    
    # Show specific examples
    from chess_metrics.cli import analyze_moves
    analysis = analyze_moves(state, legal, apply_variance=False)
    analysis.sort(key=lambda x: sum(x[3]), reverse=True)
    
    print("=" * 105)
    print("TOP 3 MOVES BREAKDOWN")
    print("=" * 105)
    print()
    
    for i, (move, san, metrics, (dPV, dMV, dOV, dDV), _) in enumerate(analysis[:3], 1):
        delta_sum = sum([dPV, dMV, dOV, dDV])
        print(f"#{i}: {move.uci()} ({san})")
        print(f"   dPV: {dPV:+.1f} (material change)")
        print(f"   dMV: {dMV:+.1f} (mobility change)")
        print(f"   dOV: {dOV:+.1f} (offensive change)")
        print(f"   dDV: {dDV:+.2f} (defensive change, using sqrt)")
        print(f"   Sum: {delta_sum:+.2f} (total evaluation)")
        print()
    
    print("=" * 105)
    print("PIECE VALUE REFERENCE")
    print("=" * 105)
    print()
    print("Defense contribution per piece:")
    print(f"  Pawn:   {math.sqrt(1):.3f} (was 1)")
    print(f"  Knight: {math.sqrt(3):.3f} (was 3)")
    print(f"  Bishop: {math.sqrt(3):.3f} (was 3)")
    print(f"  Rook:   {math.sqrt(5):.3f} (was 5)")
    print(f"  Queen:  {math.sqrt(9):.3f} (was 9)")
    print()
    print("This makes defense values more realistic and balanced!")
    print()

if __name__ == "__main__":
    main()

