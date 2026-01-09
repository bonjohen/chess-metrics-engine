"""Fix incorrect game results and terminations in the database."""
import sqlite3

def fix_game_results(db_path='chess.sqlite'):
    """
    Fix game results where termination doesn't match result.
    
    Rules:
    - result "1-0" or "0-1" → termination should be "checkmate" (not "stalemate")
    - result "1/2-1/2" → termination should be "stalemate" or "draw" (not "checkmate")
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Find games with incorrect termination
    cursor.execute("""
        SELECT game_id, result, termination 
        FROM games 
        WHERE result IS NOT NULL AND termination IS NOT NULL
    """)
    
    games = cursor.fetchall()
    fixed_count = 0
    
    print("Checking games for incorrect result/termination combinations...")
    print("=" * 80)
    
    for game_id, result, termination in games:
        new_termination = None

        # Check for mismatches
        if result in ("1-0", "0-1"):
            # Win should be checkmate or resignation
            # If it's anything else (stalemate, draw, max_moves), it's wrong
            if termination not in ("checkmate", "resignation"):
                new_termination = "checkmate"
                print(f"Game {game_id}: Result {result} with termination '{termination}' → fixing to 'checkmate'")

        elif result == "1/2-1/2":
            # Draw should be stalemate, draw, or max_moves
            # If it's checkmate or resignation, it's wrong
            if termination in ("checkmate", "resignation"):
                new_termination = "stalemate"
                print(f"Game {game_id}: Result {result} with termination '{termination}' → fixing to 'stalemate'")

        # Apply fix if needed
        if new_termination:
            cursor.execute(
                "UPDATE games SET termination = ? WHERE game_id = ?",
                (new_termination, game_id)
            )
            fixed_count += 1
    
    if fixed_count > 0:
        conn.commit()
        print("=" * 80)
        print(f"Fixed {fixed_count} game(s)")
    else:
        print("No games needed fixing")
    
    # Show final state
    print("\n" + "=" * 80)
    print("Current game results:")
    print("=" * 80)
    cursor.execute("""
        SELECT game_id, result, termination 
        FROM games 
        WHERE result IS NOT NULL
        ORDER BY game_id
    """)
    
    for game_id, result, termination in cursor.fetchall():
        print(f"Game {game_id}: {result} ({termination})")
    
    conn.close()
    print("\nDone!")

if __name__ == "__main__":
    fix_game_results()

