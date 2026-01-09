"""
Game analysis tools for chess metrics engine.

Provides blunder detection, critical position analysis, and game statistics.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from chess_metrics.web.profiling import profile_function, profile_section


@dataclass
class Blunder:
    """Represents a blunder (poor move) in a game."""
    ply: int
    side: str  # 'white' or 'black'
    san: str
    metric: str  # 'PV', 'MV', 'OV', 'DV'
    delta: float
    before: float
    after: float
    severity: str  # 'blunder', 'mistake', 'inaccuracy'


@dataclass
class CriticalPosition:
    """Represents a critical position in the game."""
    ply: int
    fen: str
    san: str
    reason: str
    metrics: Dict[str, float]


@dataclass
class GameStatistics:
    """Aggregate statistics for a game."""
    total_moves: int
    white_blunders: int
    black_blunders: int
    white_mistakes: int
    black_mistakes: int
    white_inaccuracies: int
    black_inaccuracies: int
    avg_pv_white: float
    avg_pv_black: float
    avg_mv_white: float
    avg_mv_black: float
    avg_ov_white: float
    avg_ov_black: float
    avg_dv_white: float
    avg_dv_black: float
    turning_points: List[int]  # ply numbers


def assess_move_quality(delta: float) -> str:
    """
    Assess move quality based on metric delta.
    
    Args:
        delta: Change in metric value (negative is bad for the player)
    
    Returns:
        Quality category: 'excellent', 'good', 'inaccuracy', 'mistake', 'blunder'
    """
    if delta < -15:
        return 'blunder'
    elif delta < -10:
        return 'mistake'
    elif delta < -5:
        return 'inaccuracy'
    elif delta > 5:
        return 'excellent'
    else:
        return 'good'


def detect_blunders(
    positions: List[Dict[str, Any]],
    blunder_threshold: float = -15,
    mistake_threshold: float = -10,
    inaccuracy_threshold: float = -5
) -> List[Blunder]:
    """
    Detect blunders, mistakes, and inaccuracies in a game.
    
    Args:
        positions: List of position dictionaries with metrics
        blunder_threshold: Delta threshold for blunders (default: -15)
        mistake_threshold: Delta threshold for mistakes (default: -10)
        inaccuracy_threshold: Delta threshold for inaccuracies (default: -5)
    
    Returns:
        List of Blunder objects
    """
    blunders = []
    
    for i in range(1, len(positions)):
        prev_pos = positions[i - 1]
        curr_pos = positions[i]
        
        ply = curr_pos['ply']
        san = curr_pos.get('last_move_san', '?')
        
        # Determine which side moved (odd ply = white, even ply = black)
        side = 'white' if ply % 2 == 1 else 'black'
        
        # Check each metric for the side that just moved
        if side == 'white':
            metrics_to_check = [
                ('PV', prev_pos['pv_w'], curr_pos['pv_w']),
                ('MV', prev_pos['mv_w'], curr_pos['mv_w']),
                ('OV', prev_pos['ov_w'], curr_pos['ov_w']),
                ('DV', prev_pos['dv_w'], curr_pos['dv_w']),
            ]
        else:
            metrics_to_check = [
                ('PV', prev_pos['pv_b'], curr_pos['pv_b']),
                ('MV', prev_pos['mv_b'], curr_pos['mv_b']),
                ('OV', prev_pos['ov_b'], curr_pos['ov_b']),
                ('DV', prev_pos['dv_b'], curr_pos['dv_b']),
            ]
        
        # Find the worst delta for this move
        worst_delta = 0
        worst_metric = None
        worst_before = 0
        worst_after = 0
        
        for metric_name, before, after in metrics_to_check:
            delta = after - before
            if delta < worst_delta:
                worst_delta = delta
                worst_metric = metric_name
                worst_before = before
                worst_after = after
        
        # Categorize the move
        if worst_delta <= blunder_threshold:
            severity = 'blunder'
        elif worst_delta <= mistake_threshold:
            severity = 'mistake'
        elif worst_delta <= inaccuracy_threshold:
            severity = 'inaccuracy'
        else:
            continue  # Not a poor move
        
        if worst_metric:
            blunders.append(Blunder(
                ply=ply,
                side=side,
                san=san,
                metric=worst_metric,
                delta=worst_delta,
                before=worst_before,
                after=worst_after,
                severity=severity
            ))
    
    return blunders


def find_critical_positions(
    positions: List[Dict[str, Any]],
    peak_threshold: float = 40,
    swing_threshold: float = 20
) -> List[CriticalPosition]:
    """
    Find critical positions in the game.

    Args:
        positions: List of position dictionaries with metrics
        peak_threshold: Threshold for peak metric values (default: 40)
        swing_threshold: Threshold for large metric swings (default: 20)

    Returns:
        List of CriticalPosition objects
    """
    critical = []

    for i in range(len(positions)):
        pos = positions[i]
        ply = pos['ply']
        fen = pos.get('fen', '')
        san = pos.get('last_move_san', 'start')

        # Check for peak values
        max_metric = max(
            pos['pv_w'], pos['pv_b'],
            pos['mv_w'], pos['mv_b'],
            pos['ov_w'], pos['ov_b'],
            pos['dv_w'], pos['dv_b']
        )

        if max_metric >= peak_threshold:
            critical.append(CriticalPosition(
                ply=ply,
                fen=fen,
                san=san,
                reason='peak_value',
                metrics={
                    'pv_w': pos['pv_w'], 'pv_b': pos['pv_b'],
                    'mv_w': pos['mv_w'], 'mv_b': pos['mv_b'],
                    'ov_w': pos['ov_w'], 'ov_b': pos['ov_b'],
                    'dv_w': pos['dv_w'], 'dv_b': pos['dv_b'],
                }
            ))

        # Check for large swings (turning points)
        if i > 0:
            prev_pos = positions[i - 1]

            # Calculate max absolute delta across all metrics
            deltas = [
                abs(pos['pv_w'] - prev_pos['pv_w']),
                abs(pos['pv_b'] - prev_pos['pv_b']),
                abs(pos['mv_w'] - prev_pos['mv_w']),
                abs(pos['mv_b'] - prev_pos['mv_b']),
                abs(pos['ov_w'] - prev_pos['ov_w']),
                abs(pos['ov_b'] - prev_pos['ov_b']),
                abs(pos['dv_w'] - prev_pos['dv_w']),
                abs(pos['dv_b'] - prev_pos['dv_b']),
            ]

            max_swing = max(deltas)

            if max_swing >= swing_threshold:
                critical.append(CriticalPosition(
                    ply=ply,
                    fen=fen,
                    san=san,
                    reason='turning_point',
                    metrics={
                        'pv_w': pos['pv_w'], 'pv_b': pos['pv_b'],
                        'mv_w': pos['mv_w'], 'mv_b': pos['mv_b'],
                        'ov_w': pos['ov_w'], 'ov_b': pos['ov_b'],
                        'dv_w': pos['dv_w'], 'dv_b': pos['dv_b'],
                    }
                ))

    return critical


def calculate_statistics(
    positions: List[Dict[str, Any]],
    blunders: List[Blunder]
) -> GameStatistics:
    """
    Calculate aggregate statistics for a game.

    Args:
        positions: List of position dictionaries with metrics
        blunders: List of detected blunders

    Returns:
        GameStatistics object
    """
    if not positions:
        return GameStatistics(
            total_moves=0,
            white_blunders=0, black_blunders=0,
            white_mistakes=0, black_mistakes=0,
            white_inaccuracies=0, black_inaccuracies=0,
            avg_pv_white=0, avg_pv_black=0,
            avg_mv_white=0, avg_mv_black=0,
            avg_ov_white=0, avg_ov_black=0,
            avg_dv_white=0, avg_dv_black=0,
            turning_points=[]
        )

    # Count blunders by side and severity
    white_blunders = sum(1 for b in blunders if b.side == 'white' and b.severity == 'blunder')
    black_blunders = sum(1 for b in blunders if b.side == 'black' and b.severity == 'blunder')
    white_mistakes = sum(1 for b in blunders if b.side == 'white' and b.severity == 'mistake')
    black_mistakes = sum(1 for b in blunders if b.side == 'black' and b.severity == 'mistake')
    white_inaccuracies = sum(1 for b in blunders if b.side == 'white' and b.severity == 'inaccuracy')
    black_inaccuracies = sum(1 for b in blunders if b.side == 'black' and b.severity == 'inaccuracy')

    # Calculate averages
    total = len(positions)
    avg_pv_white = sum(p['pv_w'] for p in positions) / total
    avg_pv_black = sum(p['pv_b'] for p in positions) / total
    avg_mv_white = sum(p['mv_w'] for p in positions) / total
    avg_mv_black = sum(p['mv_b'] for p in positions) / total
    avg_ov_white = sum(p['ov_w'] for p in positions) / total
    avg_ov_black = sum(p['ov_b'] for p in positions) / total
    avg_dv_white = sum(p['dv_w'] for p in positions) / total
    avg_dv_black = sum(p['dv_b'] for p in positions) / total

    # Find turning points (plies with blunders)
    turning_points = sorted(set(b.ply for b in blunders if b.severity == 'blunder'))

    return GameStatistics(
        total_moves=total,
        white_blunders=white_blunders,
        black_blunders=black_blunders,
        white_mistakes=white_mistakes,
        black_mistakes=black_mistakes,
        white_inaccuracies=white_inaccuracies,
        black_inaccuracies=black_inaccuracies,
        avg_pv_white=avg_pv_white,
        avg_pv_black=avg_pv_black,
        avg_mv_white=avg_mv_white,
        avg_mv_black=avg_mv_black,
        avg_ov_white=avg_ov_white,
        avg_ov_black=avg_ov_black,
        avg_dv_white=avg_dv_white,
        avg_dv_black=avg_dv_black,
        turning_points=turning_points
    )


def generate_game_report(
    game_data: Dict[str, Any],
    positions: List[Dict[str, Any]],
    blunders: List[Blunder],
    critical_positions: List[CriticalPosition],
    stats: GameStatistics,
    verbose: bool = False
) -> str:
    """
    Generate a comprehensive text report for a game.

    Args:
        game_data: Game metadata dictionary
        positions: List of position dictionaries
        blunders: List of detected blunders
        critical_positions: List of critical positions
        stats: Game statistics
        verbose: Include detailed move-by-move analysis

    Returns:
        Formatted text report
    """
    lines = []

    # Header
    game_id = game_data.get('game_id', '?')
    lines.append(f"{'=' * 60}")
    lines.append(f"GAME ANALYSIS: Game #{game_id}")
    lines.append(f"{'=' * 60}")
    lines.append(f"White: {game_data.get('white_name', '?')} ({game_data.get('white_type', '?')})")
    lines.append(f"Black: {game_data.get('black_name', '?')} ({game_data.get('black_type', '?')})")
    lines.append(f"Result: {game_data.get('result', '?')} ({game_data.get('termination', '?')})")
    lines.append(f"Date: {game_data.get('created_utc', '?')}")
    lines.append("")

    # Summary
    lines.append(f"{'─' * 60}")
    lines.append("SUMMARY")
    lines.append(f"{'─' * 60}")
    lines.append(f"Total Moves: {stats.total_moves} ({stats.total_moves // 2} full moves)")
    lines.append("")
    lines.append(f"White Performance:")
    lines.append(f"  Blunders: {stats.white_blunders}")
    lines.append(f"  Mistakes: {stats.white_mistakes}")
    lines.append(f"  Inaccuracies: {stats.white_inaccuracies}")
    lines.append("")
    lines.append(f"Black Performance:")
    lines.append(f"  Blunders: {stats.black_blunders}")
    lines.append(f"  Mistakes: {stats.black_mistakes}")
    lines.append(f"  Inaccuracies: {stats.black_inaccuracies}")
    lines.append("")

    if stats.turning_points:
        lines.append(f"Turning Points: {len(stats.turning_points)} (ply {', '.join(map(str, stats.turning_points))})")
    else:
        lines.append("Turning Points: None")
    lines.append("")

    # Blunders section
    if blunders:
        lines.append(f"{'─' * 60}")
        lines.append("BLUNDERS & MISTAKES")
        lines.append(f"{'─' * 60}")

        # Group by severity
        severe_blunders = [b for b in blunders if b.severity == 'blunder']
        mistakes = [b for b in blunders if b.severity == 'mistake']
        inaccuracies = [b for b in blunders if b.severity == 'inaccuracy']

        if severe_blunders:
            lines.append("Blunders:")
            for b in severe_blunders:
                move_num = (b.ply + 1) // 2
                side_marker = "..." if b.ply % 2 == 0 else "."
                lines.append(f"  [{move_num}{side_marker}] {b.side.capitalize()}: {b.san}")
                lines.append(f"      {b.metric}: {b.before:.1f} → {b.after:.1f} (Δ{b.delta:+.1f})")
            lines.append("")

        if mistakes:
            lines.append("Mistakes:")
            for b in mistakes:
                move_num = (b.ply + 1) // 2
                side_marker = "..." if b.ply % 2 == 0 else "."
                lines.append(f"  [{move_num}{side_marker}] {b.side.capitalize()}: {b.san}")
                lines.append(f"      {b.metric}: {b.before:.1f} → {b.after:.1f} (Δ{b.delta:+.1f})")
            lines.append("")

        if verbose and inaccuracies:
            lines.append("Inaccuracies:")
            for b in inaccuracies:
                move_num = (b.ply + 1) // 2
                side_marker = "..." if b.ply % 2 == 0 else "."
                lines.append(f"  [{move_num}{side_marker}] {b.side.capitalize()}: {b.san}")
                lines.append(f"      {b.metric}: {b.before:.1f} → {b.after:.1f} (Δ{b.delta:+.1f})")
            lines.append("")

    # Critical positions
    if critical_positions:
        lines.append(f"{'─' * 60}")
        lines.append("CRITICAL POSITIONS")
        lines.append(f"{'─' * 60}")

        # Deduplicate by ply (keep first occurrence)
        seen_plies = set()
        unique_critical = []
        for cp in critical_positions:
            if cp.ply not in seen_plies:
                seen_plies.add(cp.ply)
                unique_critical.append(cp)

        for cp in unique_critical[:10]:  # Limit to top 10
            move_num = (cp.ply + 1) // 2
            side_marker = "..." if cp.ply % 2 == 0 else "."
            reason_text = cp.reason.replace('_', ' ').title()
            lines.append(f"[{move_num}{side_marker}] {cp.san} - {reason_text}")

            if verbose:
                lines.append(f"    PV: W={cp.metrics['pv_w']:.1f} B={cp.metrics['pv_b']:.1f}")
                lines.append(f"    MV: W={cp.metrics['mv_w']:.1f} B={cp.metrics['mv_b']:.1f}")
                lines.append(f"    OV: W={cp.metrics['ov_w']:.1f} B={cp.metrics['ov_b']:.1f}")
                lines.append(f"    DV: W={cp.metrics['dv_w']:.1f} B={cp.metrics['dv_b']:.1f}")
        lines.append("")

    # Statistics
    lines.append(f"{'─' * 60}")
    lines.append("AVERAGE METRICS")
    lines.append(f"{'─' * 60}")
    lines.append(f"Material Value (PV):")
    lines.append(f"  White: {stats.avg_pv_white:.1f} | Black: {stats.avg_pv_black:.1f}")
    lines.append(f"Mobility Value (MV):")
    lines.append(f"  White: {stats.avg_mv_white:.1f} | Black: {stats.avg_mv_black:.1f}")
    lines.append(f"Offensive Value (OV):")
    lines.append(f"  White: {stats.avg_ov_white:.1f} | Black: {stats.avg_ov_black:.1f}")
    lines.append(f"Defensive Value (DV):")
    lines.append(f"  White: {stats.avg_dv_white:.1f} | Black: {stats.avg_dv_black:.1f}")
    lines.append("")
    lines.append(f"{'=' * 60}")

    return '\n'.join(lines)

