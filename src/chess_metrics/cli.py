from __future__ import annotations
import argparse
import random
from datetime import datetime, timezone

from chess_metrics.engine.fen import parse_fen, to_fen
from chess_metrics.engine.movegen import generate_legal_moves
from chess_metrics.engine.apply import apply_move, undo_move
from chess_metrics.engine.metrics import compute_metrics, deltas
from chess_metrics.engine.search import choose_best_move, Profile
from chess_metrics.engine.san import move_to_san
from chess_metrics.engine.types import WHITE, BLACK, sq_to_alg, alg_to_sq, Move
from chess_metrics.db.repo import Repo

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
        print(f"{'#':<4} {'Move':<8} {'SAN':<8} {'dPV':>6} {'dMV':>6} {'dOV':>6} {'dDV':>6} {'Var':>5} {'Sum':>6} | {'PVw':>4} {'MVw':>4} {'OVw':>4} {'DVw':>4} {'PVb':>4} {'MVb':>4} {'OVb':>4} {'DVb':>4}")
    else:
        print(f"{'#':<4} {'Move':<8} {'SAN':<8} {'dPV':>6} {'dMV':>6} {'dOV':>6} {'dDV':>6} {'Sum':>6} | {'PVw':>4} {'MVw':>4} {'OVw':>4} {'DVw':>4} {'PVb':>4} {'MVb':>4} {'OVb':>4} {'DVb':>4}")
    print("-" * 105)

    for idx, (move, san, metrics, (dPV, dMV, dOV, dDV), variance) in enumerate(move_analysis, 1):
        delta_sum = dPV + dMV + dOV + dDV
        if apply_variance:
            print(f"{idx:<4} {move.uci():<8} {san:<8} {dPV:>+6.1f} {dMV:>+6.1f} {dOV:>+6.1f} {dDV:>+6.1f} {variance:>5.2f} {delta_sum:>+6.1f} | "
                  f"{metrics.pv_w:>4.0f} {metrics.mv_w:>4.0f} {metrics.ov_w:>4.0f} {metrics.dv_w:>4.0f} "
                  f"{metrics.pv_b:>4.0f} {metrics.mv_b:>4.0f} {metrics.ov_b:>4.0f} {metrics.dv_b:>4.0f}")
        else:
            print(f"{idx:<4} {move.uci():<8} {san:<8} {dPV:>+6.1f} {dMV:>+6.1f} {dOV:>+6.1f} {dDV:>+6.1f} {delta_sum:>+6.1f} | "
                  f"{metrics.pv_w:>4.0f} {metrics.mv_w:>4.0f} {metrics.ov_w:>4.0f} {metrics.dv_w:>4.0f} "
                  f"{metrics.pv_b:>4.0f} {metrics.mv_b:>4.0f} {metrics.ov_b:>4.0f} {metrics.dv_b:>4.0f}")

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

if __name__ == "__main__":
    main()
