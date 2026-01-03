import unittest
from chess_metrics.engine.fen import parse_fen
from chess_metrics.engine.movegen import generate_legal_moves
from chess_metrics.engine.apply import apply_move, undo_move

def perft(state, depth):
    if depth == 0:
        return 1
    side = state.side_to_move
    moves = generate_legal_moves(state, side)
    if depth == 1:
        return len(moves)
    total = 0
    for m in moves:
        u = apply_move(state, m)
        total += perft(state, depth-1)
        undo_move(state, u)
    return total

class TestPerft(unittest.TestCase):
    def test_startpos_depth1(self):
        s = parse_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertEqual(perft(s, 1), 20)

    def test_startpos_depth2(self):
        s = parse_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        self.assertEqual(perft(s, 2), 400)

if __name__ == "__main__":
    unittest.main()
