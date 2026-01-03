#!/usr/bin/env python
"""
Database Query Examples
Demonstrates how to query the chess.sqlite database
"""

import sqlite3
import sys
from datetime import datetime

def connect_db(db_path='chess.sqlite'):
    """Connect to the database."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        sys.exit(1)

def list_all_games(conn):
    """List all games with player names."""
    print("\n" + "=" * 100)
    print("ALL GAMES")
    print("=" * 100)
    
    query = """
    SELECT 
      g.game_id,
      g.created_utc,
      wp.name AS white_player,
      wp.type AS white_type,
      bp.name AS black_player,
      bp.type AS black_type,
      g.result,
      g.termination
    FROM games g
    JOIN players wp ON g.white_player_id = wp.player_id
    JOIN players bp ON g.black_player_id = bp.player_id
    ORDER BY g.created_utc DESC
    """
    
    cursor = conn.cursor()
    cursor.execute(query)
    games = cursor.fetchall()
    
    if not games:
        print("No games found in database.")
        return
    
    print(f"\nFound {len(games)} game(s):\n")
    print(f"{'ID':<4} {'Date':<20} {'White':<15} {'vs':<3} {'Black':<15} {'Result':<8} {'Termination':<15}")
    print("-" * 100)
    
    for game in games:
        game_id = game['game_id']
        date = game['created_utc'][:19]  # Trim microseconds
        white = f"{game['white_player']} ({game['white_type']})"
        black = f"{game['black_player']} ({game['black_type']})"
        result = game['result'] or 'ongoing'
        termination = game['termination'] or '-'
        
        print(f"{game_id:<4} {date:<20} {white:<15} {'vs':<3} {black:<15} {result:<8} {termination:<15}")

def show_game_moves(conn, game_id):
    """Show all moves from a specific game."""
    print("\n" + "=" * 100)
    print(f"GAME {game_id} - MOVE HISTORY")
    print("=" * 100)
    
    query = """
    SELECT 
      m.ply,
      m.san,
      m.uci,
      m.is_capture,
      m.is_castle,
      m.is_promotion,
      m.variance_factor
    FROM moves m
    WHERE m.game_id = ?
    ORDER BY m.ply
    """
    
    cursor = conn.cursor()
    cursor.execute(query, (game_id,))
    moves = cursor.fetchall()
    
    if not moves:
        print(f"No moves found for game {game_id}")
        return
    
    print(f"\nTotal moves: {len(moves)}\n")
    print(f"{'Ply':<5} {'Move':<8} {'UCI':<8} {'Capture':<8} {'Castle':<8} {'Promotion':<10} {'Variance':<10}")
    print("-" * 100)
    
    for move in moves:
        ply = move['ply']
        san = move['san']
        uci = move['uci']
        capture = '✓' if move['is_capture'] else ''
        castle = '✓' if move['is_castle'] else ''
        promotion = '✓' if move['is_promotion'] else ''
        variance = f"{move['variance_factor']:.2f}" if move['variance_factor'] else '-'
        
        print(f"{ply:<5} {san:<8} {uci:<8} {capture:<8} {castle:<8} {promotion:<10} {variance:<10}")

def show_game_metrics(conn, game_id):
    """Show metrics for each position in a game."""
    print("\n" + "=" * 100)
    print(f"GAME {game_id} - METRICS ANALYSIS")
    print("=" * 100)
    
    query = """
    SELECT 
      ply,
      last_move_san,
      dPV, dMV, dOV, dDV,
      pv_w, mv_w, ov_w, dv_w,
      pv_b, mv_b, ov_b, dv_b
    FROM v_position_deltas
    WHERE game_id = ?
    ORDER BY ply
    """
    
    cursor = conn.cursor()
    cursor.execute(query, (game_id,))
    positions = cursor.fetchall()
    
    if not positions:
        print(f"No positions found for game {game_id}")
        return
    
    print(f"\nTotal positions: {len(positions)}\n")
    print(f"{'Ply':<5} {'Move':<8} {'dPV':>6} {'dMV':>6} {'dOV':>6} {'dDV':>6} | {'PVw':>4} {'MVw':>4} {'OVw':>4} {'DVw':>5} | {'PVb':>4} {'MVb':>4} {'OVb':>4} {'DVb':>5}")
    print("-" * 100)
    
    for pos in positions:
        ply = pos['ply']
        move = pos['last_move_san'] or 'start'
        dPV = pos['dPV']
        dMV = pos['dMV']
        dOV = pos['dOV']
        dDV = pos['dDV']
        
        print(f"{ply:<5} {move:<8} {dPV:>+6.1f} {dMV:>+6.1f} {dOV:>+6.1f} {dDV:>+6.1f} | "
              f"{pos['pv_w']:>4.0f} {pos['mv_w']:>4.0f} {pos['ov_w']:>4.0f} {pos['dv_w']:>5.1f} | "
              f"{pos['pv_b']:>4.0f} {pos['mv_b']:>4.0f} {pos['ov_b']:>4.0f} {pos['dv_b']:>5.1f}")

def show_statistics(conn):
    """Show database statistics."""
    print("\n" + "=" * 100)
    print("DATABASE STATISTICS")
    print("=" * 100)
    
    cursor = conn.cursor()
    
    # Count games
    cursor.execute("SELECT COUNT(*) FROM games")
    total_games = cursor.fetchone()[0]
    
    # Count players
    cursor.execute("SELECT COUNT(*) FROM players")
    total_players = cursor.fetchone()[0]
    
    # Count total moves
    cursor.execute("SELECT COUNT(*) FROM moves")
    total_moves = cursor.fetchone()[0]
    
    # Count captures
    cursor.execute("SELECT COUNT(*) FROM moves WHERE is_capture = 1")
    total_captures = cursor.fetchone()[0]
    
    # Count castles
    cursor.execute("SELECT COUNT(*) FROM moves WHERE is_castle = 1")
    total_castles = cursor.fetchone()[0]
    
    print(f"\nTotal Games:    {total_games}")
    print(f"Total Players:  {total_players}")
    print(f"Total Moves:    {total_moves}")
    print(f"Total Captures: {total_captures}")
    print(f"Total Castles:  {total_castles}")
    
    if total_moves > 0:
        print(f"\nAverage moves per game: {total_moves / total_games:.1f}")
        print(f"Capture rate: {total_captures / total_moves * 100:.1f}%")

def main():
    """Main function."""
    print("\n" + "=" * 100)
    print(" " * 35 + "CHESS DATABASE QUERY TOOL")
    print("=" * 100)
    
    conn = connect_db()
    
    # Show statistics
    show_statistics(conn)
    
    # List all games
    list_all_games(conn)
    
    # If there are games, show details of the most recent one
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(game_id) FROM games")
    latest_game = cursor.fetchone()[0]
    
    if latest_game:
        print(f"\n\nShowing details for most recent game (ID: {latest_game})...")
        show_game_moves(conn, latest_game)
        show_game_metrics(conn, latest_game)
    
    conn.close()
    
    print("\n" + "=" * 100)
    print("Query complete!")
    print("=" * 100)
    print("\nTo query a specific game, run:")
    print("  python query_database.py <game_id>")
    print("\nOr use sqlite3 directly:")
    print("  sqlite3 chess.sqlite")
    print("=" * 100 + "\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Query specific game
        game_id = int(sys.argv[1])
        conn = connect_db()
        show_game_moves(conn, game_id)
        show_game_metrics(conn, game_id)
        conn.close()
    else:
        # Show all games
        main()

