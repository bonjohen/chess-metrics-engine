import os
import unittest
import tempfile

from chess_metrics.db.repo import Repo
from chess_metrics.engine.fen import parse_fen, to_fen
from chess_metrics.engine.metrics import compute_metrics
from chess_metrics.engine.movegen import generate_legal_moves
from chess_metrics.engine.apply import apply_move, undo_move
from chess_metrics.engine.san import move_to_san

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

class TestDB(unittest.TestCase):
    def test_store_two_plies(self):
        with tempfile.TemporaryDirectory() as td:
            dbp = os.path.join(td, "t.sqlite")
            repo = Repo.open(dbp)
            repo.migrate()
            repo.ensure_default_profiles()

            w = repo.create_player("W", "human")
            b = repo.create_player("B", "ai")
            gid = repo.create_game(w, b, START_FEN)

            s = parse_fen(START_FEN)
            m0 = compute_metrics(s)
            repo.insert_position(gid, 0, "W", START_FEN, None, None,
                                 m0.pv_w, m0.mv_w, m0.ov_w, m0.dv_w,
                                 m0.pv_b, m0.mv_b, m0.ov_b, m0.dv_b)

            # make one legal move e2e4
            legal = generate_legal_moves(s, s.side_to_move)
            mv = next(x for x in legal if x.uci() == "e2e4")
            san = move_to_san(s, mv)
            u = apply_move(s, mv)
            fen1 = to_fen(s)
            m1 = compute_metrics(s)

            repo.insert_move(gid, 1, mv.uci(), san, "e2", "e4",
                             1 if (mv.is_capture or mv.is_ep) else 0,
                             1 if mv.is_ep else 0,
                             1 if mv.is_castle else 0,
                             1 if mv.is_promotion else 0,
                             "Q" if mv.is_promotion else None,
                             1.0)  # variance_factor

            repo.insert_position(gid, 1, "B", fen1, mv.uci(), san,
                                 m1.pv_w, m1.mv_w, m1.ov_w, m1.dv_w,
                                 m1.pv_b, m1.mv_b, m1.ov_b, m1.dv_b)

            repo.commit()

            tl = repo.timeline(gid)
            self.assertEqual(len(tl), 2)
            self.assertEqual(tl[0]["ply"], 0)
            self.assertEqual(tl[1]["ply"], 1)

            undo_move(s, u)
            repo.close()

if __name__ == "__main__":
    unittest.main()
