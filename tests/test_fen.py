import unittest
from chess_metrics.engine.fen import parse_fen, to_fen

class TestFEN(unittest.TestCase):
    def test_roundtrip_start(self):
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        s = parse_fen(fen)
        fen2 = to_fen(s)
        self.assertEqual(fen, fen2)

    def test_roundtrip_custom(self):
        fen = "3r2k1/8/8/2p5/3P4/8/3R4/3Q2K1 w - - 0 1"
        s = parse_fen(fen)
        self.assertEqual(fen, to_fen(s))

if __name__ == "__main__":
    unittest.main()
