from __future__ import annotations
import argparse
import random
import time
import hashlib
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional, List, Set

from chess_metrics.engine.fen import parse_fen, to_fen
from chess_metrics.engine.movegen import generate_legal_moves
from chess_metrics.engine.apply import apply_move, undo_move
from chess_metrics.engine.metrics import compute_metrics, deltas
from chess_metrics.engine.search import choose_best_move, Profile
from chess_metrics.engine.san import move_to_san
from chess_metrics.engine.types import WHITE, BLACK, sq_to_alg, alg_to_sq, Move
from chess_metrics.db.repo import Repo
from chess_metrics.pgn import export_game_to_pgn
from chess_metrics.analysis import (
    detect_blunders, find_critical_positions, calculate_statistics, generate_game_report
)

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

def generate_variance() -> float:
    """Generate a random variance factor between 0.75 and 1.25."""
    return random.uniform(0.75, 1.25)

def render_board(state):
    b = state.board
    rows = []
    for r in range(7, -1, -1):
        row = []
        for f in range(8):
            sq = r*8 + f
            p = b[sq]
            if p == 0:
                row.append(".")
            else:
                k = abs(p)
                ch = {1:"P",2:"N",3:"B",4:"R",5:"Q",6:"K"}[k]
                row.append(ch if p > 0 else ch.lower())
        rows.append(" ".join(row))
    return "\n".join(rows)

def parse_uci_to_move(state, uci: str) -> Move:
    uci = uci.strip()
    if len(uci) < 4:
        raise ValueError("bad uci")
    from_sq = alg_to_sq(uci[0:2])
    to_sq = alg_to_sq(uci[2:4])
    promo = (len(uci) >= 5)

    legal = generate_legal_moves(state, state.side_to_move)
    for m in legal:
        if m.from_sq == from_sq and m.to_sq == to_sq:
            if promo and not m.is_promotion:
                continue
            return m
    raise ValueError("uci not legal in this position")

def get_profile(profile_name: str) -> Profile:
    """Get AI profile by name."""
    profiles = {
        "default": Profile("default", 1, 1, 1, 1),
        "offense-first": Profile("offense-first", 1, 1, 2, 1),
        "defense-first": Profile("defense-first", 1, 1, 1, 2),
        "board-coverage": Profile("board-coverage", 1, 2, 1, 1),
        "materialist": Profile("materialist", 2, 1, 1, 1),
    }
    return profiles.get(profile_name, Profile(profile_name, 1, 1, 1, 1))

def analyze_moves(state, legal_moves, apply_variance=False):
    """Analyze all legal moves and return metrics for each.

    Args:
        state: Current board state
        legal_moves: List of legal moves
        apply_variance: If True, apply random variance to delta metrics

    Returns list of tuples: (move, san, metrics_after_move, deltas_after_move, variance_factor)
    """
    from chess_metrics.engine.apply import apply_move, undo_move
    from chess_metrics.engine.san import move_to_san
    from chess_metrics.engine.metrics import compute_metrics, deltas

    move_analysis = []

    for move in legal_moves:
        # Get SAN notation
        san = move_to_san(state, move)

        # Apply move temporarily
        undo_info = apply_move(state, move)

        # Compute metrics after the move
        metrics = compute_metrics(state)
        metric_deltas = deltas(metrics)

        # Generate variance factor
        variance_factor = generate_variance() if apply_variance else 1.0

        # Apply variance to deltas
        if apply_variance:
            dPV, dMV, dOV, dDV = metric_deltas
            metric_deltas = (
                dPV * variance_factor,
                dMV * variance_factor,
                dOV * variance_factor,
                dDV * variance_factor
            )

        # Undo the move
        undo_move(state, undo_info)

        move_analysis.append((move, san, metrics, metric_deltas, variance_factor))

    return move_analysis

def display_move_options(state, legal_moves, player_name, player_side, apply_variance=False):
    """Display legal moves with their metrics.

    Args:
        state: Current board state
        legal_moves: List of legal moves
        player_name: Name of the player
        player_side: "White" or "Black"
        apply_variance: If True, apply random variance to metrics
    """
    print(f"\n{player_name} ({player_side}) - Legal Moves with Metrics:")
    print("=" * 105)

    move_analysis = analyze_moves(state, legal_moves, apply_variance)

    # Sort by sum of deltas (descending order - higher is better)
    move_analysis.sort(key=lambda x: sum(x[3]), reverse=True)

    # Header with variance and sum columns if applicable
    if apply_variance:
        print(f"{'#':<4} {'Move':<8} {'SAN':<8} {'dPV':>6} {'dMV':>6} {'dOV':>6} {'dDV':>6} {'Var':>5} {'Sum':>6} | {'PVw':>4} {'MVw':>4} {'OVw':>4} {'DVw':>5} {'PVb':>4} {'MVb':>4} {'OVb':>4} {'DVb':>5}")
    else:
        print(f"{'#':<4} {'Move':<8} {'SAN':<8} {'dPV':>6} {'dMV':>6} {'dOV':>6} {'dDV':>6} {'Sum':>6} | {'PVw':>4} {'MVw':>4} {'OVw':>4} {'DVw':>5} {'PVb':>4} {'MVb':>4} {'OVb':>4} {'DVb':>5}")
    print("-" * 105)

    for idx, (move, san, metrics, (dPV, dMV, dOV, dDV), variance) in enumerate(move_analysis, 1):
        delta_sum = dPV + dMV + dOV + dDV
        if apply_variance:
            print(f"{idx:<4} {move.uci():<8} {san:<8} {dPV:>+6.1f} {dMV:>+6.1f} {dOV:>+6.1f} {dDV:>+6.1f} {variance:>5.2f} {delta_sum:>+6.1f} | "
                  f"{metrics.pv_w:>4.0f} {metrics.mv_w:>4.0f} {metrics.ov_w:>4.0f} {metrics.dv_w:>5.1f} "
                  f"{metrics.pv_b:>4.0f} {metrics.mv_b:>4.0f} {metrics.ov_b:>4.0f} {metrics.dv_b:>5.1f}")
        else:
            print(f"{idx:<4} {move.uci():<8} {san:<8} {dPV:>+6.1f} {dMV:>+6.1f} {dOV:>+6.1f} {dDV:>+6.1f} {delta_sum:>+6.1f} | "
                  f"{metrics.pv_w:>4.0f} {metrics.mv_w:>4.0f} {metrics.ov_w:>4.0f} {metrics.dv_w:>5.1f} "
                  f"{metrics.pv_b:>4.0f} {metrics.mv_b:>4.0f} {metrics.ov_b:>4.0f} {metrics.dv_b:>5.1f}")

    print("=" * 105)
    print(f"Total: {len(legal_moves)} legal moves")
    print("\nMetrics Legend:")
    print("  dPV/dMV/dOV/dDV = Delta (White - Black) for Piece Value / Mobility / Offensive / Defensive")
    print("  Sum = Total of all deltas (dPV + dMV + dOV + dDV)")
    if apply_variance:
        print("  Var = Variance factor (0.75-1.25) applied to deltas")
    print("  PVw/MVw/OVw/DVw = White's absolute metrics")
    print("  PVb/MVb/OVb/DVb = Black's absolute metrics")
    print("  Moves are sorted by Sum (descending)")
    print()

def is_game_over(state) -> tuple[bool, str]:
    """Check if game is over. Returns (is_over, result_string)."""
    legal = generate_legal_moves(state, state.side_to_move)

    if not legal:
        # No legal moves - checkmate or stalemate
        from chess_metrics.engine.rules import is_in_check
        if is_in_check(state, state.side_to_move):
            # Checkmate
            if state.side_to_move == WHITE:
                return True, "0-1"  # Black wins
            else:
                return True, "1-0"  # White wins
        else:
            # Stalemate
            return True, "1/2-1/2"

    # Check for 50-move rule
    if state.halfmove_clock >= 100:
        return True, "1/2-1/2"

    return False, ""

@dataclass
class GameResult:
    """Result of a completed game."""
    game_id: int
    moves_count: int
    result: str  # "1-0", "0-1", "1/2-1/2"
    termination: str  # "checkmate", "stalemate", "draw", "max_moves"
    opening_moves: List[str]  # First N moves in UCI format

@dataclass
class BatchResult:
    """Result of batch game generation."""
    total_games: int
    total_positions: int
    total_moves: int
    duplicates_rejected: int
    time_elapsed: float
    profile_distribution: dict

class OpeningTracker:
    """Tracks opening signatures to detect duplicate games."""

    def __init__(self, uniqueness_depth: int = 6):
        """
        Args:
            uniqueness_depth: Number of moves (plies) to use for uniqueness check
        """
        self.uniqueness_depth = uniqueness_depth
        self.seen_openings: Set[str] = set()
        self.duplicate_count = 0

    def get_opening_signature(self, moves: List[str]) -> str:
        """Generate hash signature from first N moves."""
        opening_moves = moves[:self.uniqueness_depth]
        signature = "|".join(opening_moves)
        return hashlib.md5(signature.encode()).hexdigest()

    def is_duplicate(self, moves: List[str]) -> bool:
        """Check if this opening has been seen before."""
        if len(moves) < self.uniqueness_depth:
            # Not enough moves yet, can't determine uniqueness
            return False

        signature = self.get_opening_signature(moves)
        return signature in self.seen_openings

    def add_opening(self, moves: List[str]) -> bool:
        """
        Add opening to tracker.
        Returns True if added (unique), False if duplicate.
        """
        if len(moves) < self.uniqueness_depth:
            return True  # Not enough moves to check

        signature = self.get_opening_signature(moves)
        if signature in self.seen_openings:
            self.duplicate_count += 1
            return False

        self.seen_openings.add(signature)
        return True

    def get_stats(self) -> dict:
        """Get statistics about tracked openings."""
        return {
            "unique_openings": len(self.seen_openings),
            "duplicates_rejected": self.duplicate_count
        }

def play_interactive_game(repo: Repo, args):
    """Play an interactive chess game and save to database."""
    # Initialize database
    repo.migrate()
    repo.ensure_default_profiles()

    # Create players
    white_pid = repo.create_player(args.white, args.white_type)
    black_pid = repo.create_player(args.black, args.black_type)

    # Create game
    game_id = repo.create_game(white_pid, black_pid, args.start_fen)
    print(f"Game created with ID: {game_id}")
    print(f"White ({args.white}): {args.white_type}")
    print(f"Black ({args.black}): {args.black_type}")
    print()

    # Initialize game state
    state = parse_fen(args.start_fen)
    ply = 0

    # Save initial position
    met = compute_metrics(state)
    repo.insert_position(
        game_id, ply, "W" if state.side_to_move == WHITE else "B",
        args.start_fen, None, None,
        met.pv_w, met.mv_w, met.ov_w, met.dv_w,
        met.pv_b, met.mv_b, met.ov_b, met.dv_b
    )
    repo.commit()

    # Get AI profile if needed
    ai_profile = get_profile(args.ai_profile)

    # Game loop
    while True:
        # Display board
        print(render_board(state))
        print()

        # Show metrics
        met = compute_metrics(state)
        dPV, dMV, dOV, dDV = deltas(met)
        print(f"Metrics: PV={dPV:+.1f} MV={dMV:+.1f} OV={dOV:+.1f} DV={dDV:+.1f}")
        print()

        # Check if game is over
        game_over, result = is_game_over(state)
        if game_over:
            print(f"Game Over! Result: {result}")
            # Update game result
            termination = "checkmate" if "#" in result and result != "1/2-1/2" else "draw"
            repo.conn.execute(
                "UPDATE games SET result=?, termination=? WHERE game_id=?",
                (result, termination, game_id)
            )
            repo.commit()
            repo.close()
            return

        # Determine current player
        current_side = "White" if state.side_to_move == WHITE else "Black"
        current_type = args.white_type if state.side_to_move == WHITE else args.black_type
        current_name = args.white if state.side_to_move == WHITE else args.black

        # Get legal moves
        legal = generate_legal_moves(state, state.side_to_move)

        # Display move options with metrics (with variance)
        display_move_options(state, legal, current_name, current_side, apply_variance=True)

        # Get move and variance
        move = None
        variance_factor = None

        if current_type == "human":
            # Human player - get input
            while move is None:
                uci_input = input(f"\n{current_name}, enter your move (UCI format, e.g., e2e4) or 'quit': ").strip()

                if uci_input.lower() in ("quit", "exit", "resign"):
                    print("Game resigned.")
                    result = "0-1" if state.side_to_move == WHITE else "1-0"
                    repo.conn.execute(
                        "UPDATE games SET result=?, termination=? WHERE game_id=?",
                        (result, "resignation", game_id)
                    )
                    repo.commit()
                    repo.close()
                    return

                try:
                    move = parse_uci_to_move(state, uci_input)
                    # Generate variance for this move
                    variance_factor = generate_variance()
                except (ValueError, KeyError) as e:
                    print(f"Invalid move: {e}. Try again.")
        else:
            # AI player
            print(f"\n{current_name} (AI) is thinking...")
            move = choose_best_move(state, ai_profile, args.ai_depth)
            if move is None:
                print("AI has no legal moves!")
                break
            san = move_to_san(state, move)
            # Generate variance for AI move
            variance_factor = generate_variance()
            print(f"AI plays: {move.uci()} ({san}) [variance: {variance_factor:.2f}]")

        # Get SAN notation before applying move
        san = move_to_san(state, move)

        # Apply move
        undo_info = apply_move(state, move)
        ply += 1

        # Compute metrics after move
        met = compute_metrics(state)

        # Apply variance to metrics (multiply deltas by variance)
        # Note: We store the raw metrics, variance is just for display/analysis
        # But we'll apply it to the stored deltas
        dPV, dMV, dOV, dDV = deltas(met)
        varied_metrics_w = (
            met.pv_w,  # Keep absolute values unchanged
            met.mv_w,
            met.ov_w,
            met.dv_w
        )
        varied_metrics_b = (
            met.pv_b,
            met.mv_b,
            met.ov_b,
            met.dv_b
        )

        # Save move to database with variance
        from_alg = sq_to_alg(move.from_sq)
        to_alg = sq_to_alg(move.to_sq)
        repo.insert_move(
            game_id, ply, move.uci(), san, from_alg, to_alg,
            1 if (move.is_capture or move.is_ep) else 0,
            1 if move.is_ep else 0,
            1 if move.is_castle else 0,
            1 if move.is_promotion else 0,
            "Q" if move.is_promotion else None,
            variance_factor
        )

        # Save new position
        fen = to_fen(state)
        repo.insert_position(
            game_id, ply, "W" if state.side_to_move == WHITE else "B",
            fen, move.uci(), san,
            varied_metrics_w[0], varied_metrics_w[1], varied_metrics_w[2], varied_metrics_w[3],
            varied_metrics_b[0], varied_metrics_b[1], varied_metrics_b[2], varied_metrics_b[3]
        )
        repo.commit()

        print(f"Move {ply}: {san} [variance: {variance_factor:.2f}]")
        print()

def play_silent_game(
    repo: Repo,
    white_profile: Profile,
    black_profile: Profile,
    depth: int = 3,
    max_moves: int = 200,
    start_fen: str = START_FEN,
    white_name: str = "White",
    black_name: str = "Black"
) -> GameResult:
    """
    Play a complete AI vs AI game silently (no display) and save to database.

    Args:
        repo: Database repository
        white_profile: AI profile for white
        black_profile: AI profile for black
        depth: Search depth for AI
        max_moves: Maximum moves before declaring draw
        start_fen: Starting position
        white_name: Name for white player
        black_name: Name for black player

    Returns:
        GameResult with game statistics
    """
    # Create players
    white_pid = repo.create_player(white_name, "ai")
    black_pid = repo.create_player(black_name, "ai")

    # Create game
    game_id = repo.create_game(white_pid, black_pid, start_fen)

    # Initialize game state
    state = parse_fen(start_fen)
    ply = 0
    opening_moves = []

    # Save initial position
    met = compute_metrics(state)
    repo.insert_position(
        game_id, ply, "W" if state.side_to_move == WHITE else "B",
        start_fen, None, None,
        met.pv_w, met.mv_w, met.ov_w, met.dv_w,
        met.pv_b, met.mv_b, met.ov_b, met.dv_b
    )
    repo.commit()

    # Game loop
    while ply < max_moves:
        # Check if game is over
        game_over, result = is_game_over(state)
        if game_over:
            termination = "checkmate" if "#" in result and result != "1/2-1/2" else "stalemate"
            repo.conn.execute(
                "UPDATE games SET result=?, termination=? WHERE game_id=?",
                (result, termination, game_id)
            )
            repo.commit()
            return GameResult(game_id, ply, result, termination, opening_moves)

        # Get AI move
        current_profile = white_profile if state.side_to_move == WHITE else black_profile
        move = choose_best_move(state, current_profile, depth)

        if move is None:
            # No legal moves (shouldn't happen if is_game_over works correctly)
            result = "1/2-1/2"
            repo.conn.execute(
                "UPDATE games SET result=?, termination=? WHERE game_id=?",
                (result, "stalemate", game_id)
            )
            repo.commit()
            return GameResult(game_id, ply, result, "stalemate", opening_moves)

        # Get SAN notation
        san = move_to_san(state, move)

        # Track opening moves
        opening_moves.append(move.uci())

        # Apply move
        apply_move(state, move)
        ply += 1

        # Compute metrics after move
        met = compute_metrics(state)

        # Generate variance for this move
        variance_factor = generate_variance()

        # Save move to database
        from_alg = sq_to_alg(move.from_sq)
        to_alg = sq_to_alg(move.to_sq)
        repo.insert_move(
            game_id, ply, move.uci(), san, from_alg, to_alg,
            1 if (move.is_capture or move.is_ep) else 0,
            1 if move.is_ep else 0,
            1 if move.is_castle else 0,
            1 if move.is_promotion else 0,
            "Q" if move.is_promotion else None,
            variance_factor
        )

        # Save new position
        fen = to_fen(state)
        repo.insert_position(
            game_id, ply, "W" if state.side_to_move == WHITE else "B",
            fen, move.uci(), san,
            met.pv_w, met.mv_w, met.ov_w, met.dv_w,
            met.pv_b, met.mv_b, met.ov_b, met.dv_b
        )
        repo.commit()

    # Max moves reached - draw
    result = "1/2-1/2"
    repo.conn.execute(
        "UPDATE games SET result=?, termination=? WHERE game_id=?",
        (result, "max_moves", game_id)
    )
    repo.commit()
    return GameResult(game_id, ply, result, "max_moves", opening_moves)

def generate_batch_games(
    repo: Repo,
    count: int,
    white_profile_name: Optional[str] = None,
    black_profile_name: Optional[str] = None,
    random_profiles: bool = False,
    depth: int = 3,
    max_moves: int = 200,
    uniqueness_depth: int = 6,
    max_retries: int = 20,
    quiet: bool = False
) -> BatchResult:
    """
    Generate multiple unique games in batch mode.

    Args:
        repo: Database repository
        count: Number of unique games to generate
        white_profile_name: Profile name for white (or None for random)
        black_profile_name: Profile name for black (or None for random)
        random_profiles: If True, randomly select profiles for each game
        depth: AI search depth
        max_moves: Maximum moves per game
        uniqueness_depth: Number of plies to check for uniqueness
        max_retries: Maximum attempts to generate unique game
        quiet: If True, minimal output

    Returns:
        BatchResult with statistics
    """
    start_time = time.time()
    tracker = OpeningTracker(uniqueness_depth)
    profile_distribution = {}

    all_profiles = ["default", "offense-first", "defense-first", "board-coverage", "materialist"]

    if not quiet:
        print(f"Generating {count} unique games...")
        print(f"Settings: depth={depth}, max_moves={max_moves}, uniqueness_depth={uniqueness_depth}")
        print()

    games_completed = 0
    total_moves = 0
    total_positions = 0

    while games_completed < count:
        # Select profiles
        if random_profiles:
            white_prof_name = random.choice(all_profiles)
            black_prof_name = random.choice(all_profiles)
        else:
            white_prof_name = white_profile_name or "default"
            black_prof_name = black_profile_name or "default"

        white_profile = get_profile(white_prof_name)
        black_profile = get_profile(black_prof_name)

        # Track profile usage
        profile_key = f"{white_prof_name} vs {black_prof_name}"
        profile_distribution[profile_key] = profile_distribution.get(profile_key, 0) + 1

        # Try to generate unique game
        retry_count = 0
        game_is_unique = False

        while retry_count < max_retries and not game_is_unique:
            # Play game
            result = play_silent_game(
                repo, white_profile, black_profile, depth, max_moves,
                START_FEN, f"W_{white_prof_name}", f"B_{black_prof_name}"
            )

            # Check uniqueness
            if tracker.is_duplicate(result.opening_moves):
                # Duplicate - delete game and retry
                repo.conn.execute("DELETE FROM positions WHERE game_id=?", (result.game_id,))
                repo.conn.execute("DELETE FROM moves WHERE game_id=?", (result.game_id,))
                repo.conn.execute("DELETE FROM games WHERE game_id=?", (result.game_id,))
                repo.commit()
                retry_count += 1
            else:
                # Unique game!
                tracker.add_opening(result.opening_moves)
                game_is_unique = True
                games_completed += 1
                total_moves += result.moves_count
                total_positions += result.moves_count + 1  # +1 for initial position

                if not quiet:
                    elapsed = time.time() - start_time
                    avg_moves = total_moves / games_completed if games_completed > 0 else 0
                    games_per_sec = games_completed / elapsed if elapsed > 0 else 0
                    eta = (count - games_completed) / games_per_sec if games_per_sec > 0 else 0

                    print(f"[{games_completed}/{count}] Game {result.game_id}: "
                          f"{result.result} ({result.termination}, {result.moves_count} moves) "
                          f"| Avg: {avg_moves:.1f} moves | ETA: {eta:.0f}s")

        if not game_is_unique:
            if not quiet:
                print(f"Warning: Could not generate unique game after {max_retries} retries. Skipping.")

    elapsed_time = time.time() - start_time

    if not quiet:
        print()
        print("=" * 80)
        print("Batch Generation Complete!")
        print(f"  Total games: {games_completed}")
        print(f"  Total positions: {total_positions}")
        print(f"  Total moves: {total_moves}")
        print(f"  Duplicates rejected: {tracker.duplicate_count}")
        print(f"  Time elapsed: {elapsed_time:.1f}s")
        print(f"  Avg time per game: {elapsed_time/games_completed:.2f}s")
        print()
        print("Profile distribution:")
        for profile_combo, count_val in sorted(profile_distribution.items()):
            print(f"  {profile_combo}: {count_val} games")

    return BatchResult(
        total_games=games_completed,
        total_positions=total_positions,
        total_moves=total_moves,
        duplicates_rejected=tracker.duplicate_count,
        time_elapsed=elapsed_time,
        profile_distribution=profile_distribution
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="chess.sqlite", help="sqlite db path")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("migrate")

    ng = sub.add_parser("new-game")
    ng.add_argument("--white", default="White")
    ng.add_argument("--black", default="Black")
    ng.add_argument("--start-fen", default=START_FEN)

    sh = sub.add_parser("show")
    sh.add_argument("--fen", default=START_FEN)

    lm = sub.add_parser("legal-moves")
    lm.add_argument("--fen", default=START_FEN)

    ai = sub.add_parser("ai-move")
    ai.add_argument("--fen", default=START_FEN)
    ai.add_argument("--depth", type=int, default=3)
    ai.add_argument("--profile", default="default")

    pg = sub.add_parser("play-game")
    pg.add_argument("--white", default="White", help="White player name")
    pg.add_argument("--black", default="Black", help="Black player name")
    pg.add_argument("--white-type", default="human", choices=["human", "ai"], help="White player type")
    pg.add_argument("--black-type", default="ai", choices=["human", "ai"], help="Black player type")
    pg.add_argument("--ai-depth", type=int, default=3, help="AI search depth")
    pg.add_argument("--ai-profile", default="default", help="AI profile")
    pg.add_argument("--start-fen", default=START_FEN, help="Starting position FEN")

    gg = sub.add_parser("generate-games", help="Generate multiple games in batch mode")
    gg.add_argument("--count", type=int, required=True, help="Number of unique games to generate")
    gg.add_argument("--white-profile", default=None, help="AI profile for white (default: random if --random-profiles)")
    gg.add_argument("--black-profile", default=None, help="AI profile for black (default: random if --random-profiles)")
    gg.add_argument("--random-profiles", action="store_true", help="Randomly select profiles for each game")
    gg.add_argument("--depth", type=int, default=3, help="AI search depth (default: 3)")
    gg.add_argument("--max-moves", type=int, default=200, help="Maximum moves per game before draw (default: 200)")
    gg.add_argument("--uniqueness-depth", type=int, default=6, help="Number of plies to check for uniqueness (default: 6)")
    gg.add_argument("--max-retries", type=int, default=20, help="Max attempts to generate unique game (default: 20)")
    gg.add_argument("--quiet", action="store_true", help="Minimal output")

    ep = sub.add_parser("export-pgn", help="Export game(s) to PGN format")
    ep.add_argument("--game-id", type=int, help="Game ID to export (omit to export all games)")
    ep.add_argument("--output", "-o", help="Output file (default: stdout)")
    ep.add_argument("--no-metrics", action="store_true", help="Exclude metrics comments")
    ep.add_argument("--range", help="Game ID range (e.g., '1-10')")

    ag = sub.add_parser("analyze-game", help="Analyze a game for blunders and critical positions")
    ag.add_argument("--game-id", type=int, required=True, help="Game ID to analyze")
    ag.add_argument("--output", "-o", help="Output file (default: stdout)")
    ag.add_argument("--blunder-threshold", type=float, default=-15, help="Threshold for blunders (default: -15)")
    ag.add_argument("--mistake-threshold", type=float, default=-10, help="Threshold for mistakes (default: -10)")
    ag.add_argument("--inaccuracy-threshold", type=float, default=-5, help="Threshold for inaccuracies (default: -5)")
    ag.add_argument("--verbose", "-v", action="store_true", help="Include detailed analysis")

    args = ap.parse_args()
    repo = Repo.open(args.db)

    if args.cmd == "migrate":
        repo.migrate()
        repo.ensure_default_profiles()
        print("OK")
        repo.close()
        return

    if args.cmd == "new-game":
        repo.migrate()
        repo.ensure_default_profiles()
        w = repo.create_player(args.white, "human")
        b = repo.create_player(args.black, "ai")
        gid = repo.create_game(w, b, args.start_fen)

        st = parse_fen(args.start_fen)
        met = compute_metrics(st)
        repo.insert_position(gid, 0, "W" if st.side_to_move==WHITE else "B", args.start_fen,
                             None, None,
                             met.pv_w, met.mv_w, met.ov_w, met.dv_w,
                             met.pv_b, met.mv_b, met.ov_b, met.dv_b)
        repo.commit()
        print(gid)
        repo.close()
        return

    if args.cmd == "show":
        st = parse_fen(args.fen)
        print(render_board(st))
        met = compute_metrics(st)
        dPV, dMV, dOV, dDV = deltas(met)
        print(f"PVw={met.pv_w} MVw={met.mv_w} OVw={met.ov_w} DVw={met.dv_w}")
        print(f"PVb={met.pv_b} MVb={met.mv_b} OVb={met.ov_b} DVb={met.dv_b}")
        print(f"dPV={dPV} dMV={dMV} dOV={dOV} dDV={dDV}")
        repo.close()
        return

    if args.cmd == "legal-moves":
        st = parse_fen(args.fen)
        legal = generate_legal_moves(st, st.side_to_move)
        for m in legal:
            print(m.uci())
        repo.close()
        return

    if args.cmd == "ai-move":
        st = parse_fen(args.fen)
        # minimal profile mapping for CLI
        prof = {
            "default": Profile("default", 1,1,1,1),
            "offense-first": Profile("offense-first", 1,1,2,1),
            "defense-first": Profile("defense-first", 1,1,1,2),
            "board-coverage": Profile("board-coverage", 1,2,1,1),
            "materialist": Profile("materialist", 2,1,1,1),
        }.get(args.profile, Profile(args.profile, 1,1,1,1))

        mv = choose_best_move(st, prof, args.depth)
        if mv is None:
            print("NO_MOVE")
            repo.close()
            return
        san = move_to_san(st, mv)
        print(mv.uci(), san)
        repo.close()
        return

    if args.cmd == "play-game":
        play_interactive_game(repo, args)
        return

    if args.cmd == "generate-games":
        repo.migrate()
        repo.ensure_default_profiles()

        # Validate profiles if specified
        valid_profiles = ["default", "offense-first", "defense-first", "board-coverage", "materialist"]
        if args.white_profile and args.white_profile not in valid_profiles:
            print(f"Error: Invalid white profile '{args.white_profile}'. Valid: {', '.join(valid_profiles)}")
            repo.close()
            return
        if args.black_profile and args.black_profile not in valid_profiles:
            print(f"Error: Invalid black profile '{args.black_profile}'. Valid: {', '.join(valid_profiles)}")
            repo.close()
            return

        # Generate games
        result = generate_batch_games(
            repo=repo,
            count=args.count,
            white_profile_name=args.white_profile,
            black_profile_name=args.black_profile,
            random_profiles=args.random_profiles,
            depth=args.depth,
            max_moves=args.max_moves,
            uniqueness_depth=args.uniqueness_depth,
            max_retries=args.max_retries,
            quiet=args.quiet
        )

        repo.close()
        return

    if args.cmd == "export-pgn":
        # Determine which games to export
        game_ids = []

        if args.game_id is not None:
            # Single game
            game_ids = [args.game_id]
        elif args.range:
            # Range of games (e.g., "1-10")
            try:
                start_str, end_str = args.range.split('-')
                start = int(start_str.strip())
                end = int(end_str.strip())
                game_ids = repo.get_game_ids_in_range(start, end)
                if not game_ids:
                    print(f"No games found in range {start}-{end}")
                    repo.close()
                    return
            except ValueError:
                print(f"Error: Invalid range format '{args.range}'. Use format: '1-10'")
                repo.close()
                return
        else:
            # All games
            game_ids = repo.get_all_game_ids()
            if not game_ids:
                print("No games found in database")
                repo.close()
                return

        # Export games
        include_metrics = not args.no_metrics
        output_lines = []

        for game_id in game_ids:
            game_data = repo.get_game_for_pgn(game_id)
            if not game_data:
                print(f"Warning: Game {game_id} not found, skipping")
                continue

            pgn = export_game_to_pgn(
                game_data['game'],
                game_data['moves'],
                include_metrics=include_metrics
            )
            output_lines.append(pgn)

        # Combine all PGNs
        full_output = "\n".join(output_lines)

        # Write to file or stdout
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(full_output)
                print(f"Exported {len(game_ids)} game(s) to {args.output}")
            except IOError as e:
                print(f"Error writing to file: {e}")
                repo.close()
                return
        else:
            print(full_output)

        repo.close()
        return

    if args.cmd == "analyze-game":
        # Get game data
        game_data = repo.get_game_for_analysis(args.game_id)

        if not game_data:
            print(f"Error: Game {args.game_id} not found")
            repo.close()
            return

        positions = game_data['positions']

        if not positions:
            print(f"Error: No positions found for game {args.game_id}")
            repo.close()
            return

        # Perform analysis
        blunders = detect_blunders(
            positions,
            blunder_threshold=args.blunder_threshold,
            mistake_threshold=args.mistake_threshold,
            inaccuracy_threshold=args.inaccuracy_threshold
        )

        critical_positions = find_critical_positions(positions)

        stats = calculate_statistics(positions, blunders)

        # Generate report
        report = generate_game_report(
            game_data['game'],
            positions,
            blunders,
            critical_positions,
            stats,
            verbose=args.verbose
        )

        # Output report
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"Analysis saved to {args.output}")
            except IOError as e:
                print(f"Error writing to file: {e}")
                repo.close()
                return
        else:
            print(report)

        repo.close()
        return

if __name__ == "__main__":
    main()
