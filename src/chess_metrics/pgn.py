"""PGN (Portable Game Notation) export functionality."""

from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import datetime

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def format_pgn_date(utc_str: str) -> str:
    """
    Convert UTC timestamp to PGN date format (YYYY.MM.DD).
    
    Args:
        utc_str: UTC timestamp string (e.g., "2026-01-08T12:34:56")
    
    Returns:
        PGN formatted date (e.g., "2026.01.08")
    """
    try:
        dt = datetime.fromisoformat(utc_str.replace('Z', '+00:00'))
        return dt.strftime("%Y.%m.%d")
    except:
        return "????.??.??"


def generate_pgn_headers(game_data: Dict[str, Any]) -> str:
    """
    Generate PGN headers from game data.
    
    Args:
        game_data: Dictionary with game metadata
            - created_utc: Game creation timestamp
            - game_id: Game ID
            - white_name: White player name
            - black_name: Black player name
            - white_type: White player type (human/ai)
            - black_type: Black player type (human/ai)
            - result: Game result (1-0, 0-1, 1/2-1/2, or None)
            - termination: How game ended (optional)
            - start_fen: Starting position FEN (optional)
    
    Returns:
        PGN header string
    """
    headers = [
        '[Event "Chess Metrics Engine Game"]',
        '[Site "Local"]',
        f'[Date "{format_pgn_date(game_data["created_utc"])}"]',
        f'[Round "{game_data["game_id"]}"]',
        f'[White "{game_data["white_name"]}"]',
        f'[Black "{game_data["black_name"]}"]',
        f'[Result "{game_data.get("result") or "*"}"]',
    ]
    
    # Add custom headers
    if game_data.get("white_type"):
        headers.append(f'[WhiteType "{game_data["white_type"]}"]')
    if game_data.get("black_type"):
        headers.append(f'[BlackType "{game_data["black_type"]}"]')
    if game_data.get("termination"):
        headers.append(f'[Termination "{game_data["termination"]}"]')
    
    # Add FEN if not standard starting position
    start_fen = game_data.get("start_fen", START_FEN)
    if start_fen != START_FEN:
        headers.append(f'[FEN "{start_fen}"]')
        headers.append('[SetUp "1"]')
    
    return "\n".join(headers)


def format_metrics_comment(metrics: Dict[str, Any]) -> str:
    """
    Format position metrics as PGN comment.
    
    Args:
        metrics: Dictionary with position metrics
            - pv_w, pv_b: Piece values
            - mv_w, mv_b: Mobility values
            - ov_w, ov_b: Offense values
            - dv_w, dv_b: Defense values
    
    Returns:
        Formatted comment string (without braces)
    """
    # Calculate deltas (White advantage)
    dPV = metrics['pv_w'] - metrics['pv_b']
    dMV = metrics['mv_w'] - metrics['mv_b']
    dOV = metrics['ov_w'] - metrics['ov_b']
    dDV = metrics['dv_w'] - metrics['dv_b']
    
    # Format: dPV:+5 dMV:+2 dOV:+3 dDV:+1.5 | PV:45/40 MV:25/23 OV:5/2 DV:30.5/29.0
    deltas = f"dPV:{dPV:+.0f} dMV:{dMV:+.0f} dOV:{dOV:+.0f} dDV:{dDV:+.1f}"
    absolutes = (f"PV:{metrics['pv_w']:.0f}/{metrics['pv_b']:.0f} "
                 f"MV:{metrics['mv_w']:.0f}/{metrics['mv_b']:.0f} "
                 f"OV:{metrics['ov_w']:.0f}/{metrics['ov_b']:.0f} "
                 f"DV:{metrics['dv_w']:.1f}/{metrics['dv_b']:.1f}")
    
    return f"{deltas} | {absolutes}"


def generate_pgn_moves(moves: List[Dict[str, Any]], result: str, include_metrics: bool = True) -> str:
    """
    Generate PGN move list with optional metrics comments.
    
    Args:
        moves: List of move dictionaries with:
            - ply: Move number (0-indexed)
            - san: Standard Algebraic Notation
            - metrics: Position metrics after move (optional)
        result: Game result (1-0, 0-1, 1/2-1/2, *)
        include_metrics: Whether to include metrics as comments
    
    Returns:
        PGN move list string
    """
    if not moves:
        return result
    
    lines = []
    current_line = ""
    
    for move in moves:
        ply = move['ply']  # 1-indexed: 1=white's first move, 2=black's first move, etc.
        san = move['san']
        move_num = (ply + 1) // 2  # Convert 1-indexed ply to move number
        is_white = (ply % 2) == 1  # Odd ply = white, even ply = black

        # Format move with number
        if is_white:
            move_str = f"{move_num}. {san}"
        else:
            move_str = f"{move_num}...{san}"
        
        # Add metrics comment if available
        if include_metrics and move.get('metrics'):
            comment = format_metrics_comment(move['metrics'])
            move_str += f" {{{comment}}}"
        
        # Add to current line (wrap at ~80 chars for readability)
        if current_line and len(current_line) + len(move_str) + 1 > 80:
            lines.append(current_line)
            current_line = move_str
        else:
            if current_line:
                current_line += " " + move_str
            else:
                current_line = move_str
    
    # Add final line and result
    if current_line:
        lines.append(current_line)
    lines.append(result)
    
    return "\n".join(lines)


def export_game_to_pgn(game_data: Dict[str, Any], moves: List[Dict[str, Any]], include_metrics: bool = True) -> str:
    """
    Export a complete game to PGN format.
    
    Args:
        game_data: Game metadata dictionary
        moves: List of move dictionaries
        include_metrics: Whether to include metrics comments
    
    Returns:
        Complete PGN string
    """
    headers = generate_pgn_headers(game_data)
    result = game_data.get("result") or "*"
    move_text = generate_pgn_moves(moves, result, include_metrics)
    
    return f"{headers}\n\n{move_text}\n"

