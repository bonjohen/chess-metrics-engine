from __future__ import annotations
import argparse
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
    return "\\n".join(rows)

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

if __name__ == "__main__":
    main()
