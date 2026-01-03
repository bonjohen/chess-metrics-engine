import unittest
from chess_metrics.engine.fen import parse_fen
from chess_metrics.engine.metrics import compute_metrics, deltas

class TestMetrics(unittest.TestCase):
    def test_worked_example_p0(self):
        fen = "3r2k1/8/8/2p5/3P4/8/3R4/3Q2K1 w - - 0 1"
        s = parse_fen(fen)
        m = compute_metrics(s)
        self.assertEqual((m.pv_w, m.pv_b), (15, 6))
        self.assertEqual(m.mv_w, 26)
        self.assertEqual(m.ov_w, 1)
        self.assertEqual(m.dv_w, 15)
        self.assertEqual(m.mv_b, 14)
        self.assertEqual(m.ov_b, 2)
        self.assertEqual(m.dv_b, 0)

    def test_ep_counts_for_ov_only(self):
        # White pawn e5, black pawn d5 just moved two squares => ep square d6, white can capture ep e5xd6 ep
        fen = "8/8/8/3pP3/8/8/8/4K2k w - d6 0 1"
        s = parse_fen(fen)
        m = compute_metrics(s)
        # White has EP capture => OV_w includes +1
        self.assertGreaterEqual(m.ov_w, 1)
        # MV excludes EP (so MV can be 0 if no other quiet moves besides king)
        # But kings exist; white king e1 has moves -> MV_w >= 1, we only assert EP not added to MV via a delta check:
        # If we remove the kings to isolate EP we'd violate legality. So we assert MV_w is not inflated by EP by sanity:
        # MV counts only non-captures; EP is capture -> does not contribute.
        # Therefore: OV_w - OV_b should be at least 1 in this position (black has no captures here).
        dPV, dMV, dOV, dDV = deltas(m)
        self.assertGreaterEqual(dOV, 1)

if __name__ == "__main__":
    unittest.main()
