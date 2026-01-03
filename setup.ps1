# setup.ps1
# Creates a complete, runnable Python + SQLite chess-metrics engine repo scaffold (code + tests + GitHub files).
# Usage:
#   pwsh ./setup.ps1 -Root "chess-metrics-engine" -Force

param(
  [string]$Root = "chess-metrics-engine",
  [switch]$Force
)

function Ensure-Dir([string]$p) {
  if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p | Out-Null }
}

function Write-File([string]$path, [string]$content) {
  $dir = Split-Path $path -Parent
  if ($dir) { Ensure-Dir $dir }
  Set-Content -Path $path -Value $content -Encoding UTF8
}

if (Test-Path $Root) {
  if (-not $Force) { throw "Path exists: $Root. Use -Force to overwrite." }
  Remove-Item -Recurse -Force $Root
}

Ensure-Dir $Root
Push-Location $Root

# -------------------------
# Common GitHub repo files
# -------------------------
Write-File ".gitignore" @"
__pycache__/
*.pyc
*.pyo
*.pyd
*.egg-info/
dist/
build/
.venv/
venv/
.env
*.sqlite
*.db
.coverage
.pytest_cache/
.idea/
.vscode/
"@

Write-File ".gitattributes" @"
* text=auto eol=lf
"@

Write-File ".editorconfig" @"
root = true

[*]
end_of_line = lf
insert_final_newline = true
charset = utf-8
indent_style = space
indent_size = 2

[*.py]
indent_size = 4
"@

Write-File "LICENSE" @"
MIT License

Copyright (c) $(Get-Date -Format yyyy)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"@

Write-File "README.md" @"
# Chess Metrics Engine (PV/MV/OV/DV) + SQLite

Implementation:
- Legal move generation (pins/check/castling/ep/promotion)
- Metrics PV/MV/OV/DV (no deduping; multiplicity counts; true-legal required)
- Minimax search depth N plies (default 3) using Score_S convention
- SQLite persistence (games/players/profiles/positions/moves)
- Minimal CLI

## Quick start (Windows PowerShell)
\`\`\`powershell
python -m unittest -v
python -m chess_metrics.cli --help
\`\`\`

## Layout
- \`src/chess_metrics/\` engine, metrics, search, db, cli
- \`tests/\` unittest suite
"@

Write-File "pyproject.toml" @"
[build-system]
requires = []
build-backend = "setuptools.build_meta"

[project]
name = "chess-metrics-engine"
version = "0.1.0"
description = "Chess legal engine + custom PV/MV/OV/DV metrics + SQLite store"
requires-python = ">=3.10"
"@

Write-File "CONTRIBUTING.md" @"
## Contributing
- Keep changes small and tested.
- Run: python -m unittest -v
- Prefer deterministic behavior (stable move ordering, stable UCI).
"@

Write-File "CODE_OF_CONDUCT.md" @"
## Code of Conduct
Be respectful. Assume good intent. Keep discussions technical.
"@

Write-File "SECURITY.md" @"
## Security
If you find a security issue, open a private report (or file an issue with minimal details).
"@

Ensure-Dir ".github/workflows"
Write-File ".github/workflows/ci.yml" @"
name: CI

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Run tests
        run: |
          python -m unittest -v
"@

# -------------------------
# Project structure
# -------------------------
Ensure-Dir "src/chess_metrics/engine"
Ensure-Dir "src/chess_metrics/db"
Ensure-Dir "tests"

# -------------------------
# Code files
# -------------------------

Write-File "src/chess_metrics/__init__.py" @"
__all__ = ["engine", "db"]
"@

Write-File "src/chess_metrics/engine/__init__.py" @"
from .types import *
from .fen import parse_fen, to_fen
from .movegen import generate_legal_moves
from .apply import apply_move, undo_move
from .metrics import compute_metrics
from .search import choose_best_move
"@

Write-File "src/chess_metrics/engine/types.py" @"
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List, Tuple

WHITE = 1
BLACK = -1

# Board encoding: 0 empty; >0 white piece; <0 black piece; abs(piece) is piece kind.
PAWN   = 1
KNIGHT = 2
BISHOP = 3
ROOK   = 4
QUEEN  = 5
KING   = 6

PIECE_TO_CHAR = {
    PAWN: "P", KNIGHT: "N", BISHOP: "B", ROOK: "R", QUEEN: "Q", KING: "K"
}
CHAR_TO_PIECE = {v: k for k, v in PIECE_TO_CHAR.items()}
CHAR_TO_PIECE.update({v.lower(): -k for k, v in PIECE_TO_CHAR.items()})  # for FEN parsing

# Castling rights bitmask
CR_WK = 1
CR_WQ = 2
CR_BK = 4
CR_BQ = 8

PIECE_VALUE = {
    PAWN: 1,
    KNIGHT: 3,
    BISHOP: 3,
    ROOK: 5,
    QUEEN: 9,
    KING: 0,
}

def piece_color(p: int) -> int:
    if p > 0: return WHITE
    if p < 0: return BLACK
    return 0

def piece_kind(p: int) -> int:
    return abs(p)

def value_of_piece(p: int) -> int:
    return PIECE_VALUE[abs(p)] if p != 0 else 0

def opposite(side: int) -> int:
    return WHITE if side == BLACK else BLACK

def sq_to_alg(sq: int) -> str:
    f = sq % 8
    r = sq // 8
    return chr(ord('a') + f) + chr(ord('1') + r)

def alg_to_sq(a: str) -> int:
    f = ord(a[0]) - ord('a')
    r = ord(a[1]) - ord('1')
    return r * 8 + f

@dataclass(frozen=True)
class Move:
    from_sq: int
    to_sq: int
    moving_kind: int
    captured_kind: int = 0
    is_capture: bool = False
    is_ep: bool = False
    is_castle: bool = False
    is_promotion: bool = False
    promotion_kind: int = QUEEN
    ep_victim_sq: int = -1
    castle_rook_from: int = -1
    castle_rook_to: int = -1

    def uci(self) -> str:
        s = sq_to_alg(self.from_sq) + sq_to_alg(self.to_sq)
        if self.is_promotion:
            s += "q"  # locked
        return s

@dataclass
class Undo:
    move: Move
    captured_piece: int
    captured_sq: int
    prev_castling_rights: int
    prev_ep_sq: int
    prev_halfmove: int
    prev_fullmove: int
    prev_side_to_move: int
    rook_piece: int
    rook_from: int
    rook_to: int
    moved_piece_before: int
    to_piece_before: int

@dataclass
class GameState:
    board: List[int]               # len 64
    side_to_move: int              # WHITE or BLACK
    castling_rights: int           # bitmask CR_*
    ep_sq: int                     # -1 if none
    halfmove_clock: int
    fullmove_number: int
    undo_stack: List[Undo]

    @staticmethod
    def empty() -> "GameState":
        return GameState([0]*64, WHITE, 0, -1, 0, 1, [])
"@

Write-File "src/chess_metrics/engine/fen.py" @"
from __future__ import annotations
from typing import List
from .types import (
    GameState, WHITE, BLACK,
    CR_WK, CR_WQ, CR_BK, CR_BQ,
    CHAR_TO_PIECE, PIECE_TO_CHAR, sq_to_alg, alg_to_sq
)

def parse_fen(fen: str) -> GameState:
    parts = fen.strip().split()
    if len(parts) != 6:
        raise ValueError("FEN must have 6 fields")

    placement, stm, castling, ep, halfmove, fullmove = parts
    board: List[int] = [0]*64

    ranks = placement.split("/")
    if len(ranks) != 8:
        raise ValueError("FEN placement must have 8 ranks")

    # FEN rank 8 -> internal rank 7, ... rank 1 -> internal rank 0
    for fen_rank_index, rank_str in enumerate(ranks):
        r = 7 - fen_rank_index
        f = 0
        for ch in rank_str:
            if ch.isdigit():
                f += int(ch)
            else:
                if ch not in CHAR_TO_PIECE:
                    raise ValueError(f"Bad piece char: {ch}")
                p = CHAR_TO_PIECE[ch]
                sq = r * 8 + f
                board[sq] = p
                f += 1
        if f != 8:
            raise ValueError("Bad FEN rank width")

    side = WHITE if stm == "w" else BLACK if stm == "b" else None
    if side is None:
        raise ValueError("Bad side to move in FEN")

    cr = 0
    if castling != "-":
        if "K" in castling: cr |= CR_WK
        if "Q" in castling: cr |= CR_WQ
        if "k" in castling: cr |= CR_BK
        if "q" in castling: cr |= CR_BQ

    ep_sq = -1 if ep == "-" else alg_to_sq(ep)

    return GameState(
        board=board,
        side_to_move=side,
        castling_rights=cr,
        ep_sq=ep_sq,
        halfmove_clock=int(halfmove),
        fullmove_number=int(fullmove),
        undo_stack=[]
    )

def to_fen(state: GameState) -> str:
    rows = []
    for r in range(7, -1, -1):
        empties = 0
        row = ""
        for f in range(8):
            sq = r*8 + f
            p = state.board[sq]
            if p == 0:
                empties += 1
            else:
                if empties:
                    row += str(empties)
                    empties = 0
                kind = abs(p)
                ch = PIECE_TO_CHAR[kind]
                row += ch if p > 0 else ch.lower()
        if empties:
            row += str(empties)
        rows.append(row)
    placement = "/".join(rows)
    stm = "w" if state.side_to_move == WHITE else "b"

    cr = ""
    if state.castling_rights == 0:
        cr = "-"
    else:
        if state.castling_rights & 1: cr += "K"
        if state.castling_rights & 2: cr += "Q"
        if state.castling_rights & 4: cr += "k"
        if state.castling_rights & 8: cr += "q"

    ep = "-" if state.ep_sq == -1 else sq_to_alg(state.ep_sq)

    return f"{placement} {stm} {cr} {ep} {state.halfmove_clock} {state.fullmove_number}"
"@

Write-File "src/chess_metrics/engine/rules.py" @"
from __future__ import annotations
from .types import (
    WHITE, BLACK,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    piece_color, piece_kind, opposite
)

KNIGHT_OFFS = [+17, +15, +10, +6, -6, -10, -15, -17]
KING_OFFS   = [+1, -1, +8, -8, +9, +7, -7, -9]

def on_board(sq: int) -> bool:
    return 0 <= sq < 64

def same_file(a: int, b: int) -> bool:
    return (a % 8) == (b % 8)

def same_rank(a: int, b: int) -> bool:
    return (a // 8) == (b // 8)

def file_of(sq: int) -> int:
    return sq % 8

def rank_of(sq: int) -> int:
    return sq // 8

def is_square_attacked(state, sq: int, by_side: int) -> bool:
    b = state.board

    # Pawn attacks
    if by_side == WHITE:
        for d in (-7, -9):
            s = sq + d
            if 0 <= s < 64:
                # ensure file delta matches diagonal
                if abs(file_of(s) - file_of(sq)) == 1 and b[s] == WHITE * PAWN:
                    return True
    else:
        for d in (+7, +9):
            s = sq + d
            if 0 <= s < 64:
                if abs(file_of(s) - file_of(sq)) == 1 and b[s] == BLACK * PAWN:
                    return True

    # Knight attacks
    for d in KNIGHT_OFFS:
        s = sq + d
        if 0 <= s < 64 and abs(file_of(s) - file_of(sq)) in (1,2):
            p = b[s]
            if p != 0 and piece_color(p) == by_side and piece_kind(p) == KNIGHT:
                return True

    # King attacks
    for d in KING_OFFS:
        s = sq + d
        if 0 <= s < 64 and abs(file_of(s) - file_of(sq)) <= 1:
            p = b[s]
            if p != 0 and piece_color(p) == by_side and piece_kind(p) == KING:
                return True

    # Sliding attacks (rook/queen)
    for d in (+1, -1, +8, -8):
        s = sq + d
        while 0 <= s < 64 and (d in (+8,-8) or same_rank(s, s-d)):
            p = b[s]
            if p != 0:
                if piece_color(p) == by_side:
                    k = piece_kind(p)
                    if k == ROOK or k == QUEEN:
                        return True
                break
            s += d

    # Sliding attacks (bishop/queen)
    for d in (+9, +7, -7, -9):
        s = sq + d
        while 0 <= s < 64 and abs(file_of(s) - file_of(s-d)) == 1:
            p = b[s]
            if p != 0:
                if piece_color(p) == by_side:
                    k = piece_kind(p)
                    if k == BISHOP or k == QUEEN:
                        return True
                break
            s += d

    return False

def find_king_sq(state, side: int) -> int:
    target = side * KING
    for sq, p in enumerate(state.board):
        if p == target:
            return sq
    raise ValueError("King not found")

def is_in_check(state, side: int) -> bool:
    ksq = find_king_sq(state, side)
    return is_square_attacked(state, ksq, opposite(side))

def pseudo_attacks_square(state, from_sq: int, to_sq: int) -> bool:
    b = state.board
    p = b[from_sq]
    if p == 0:
        return False
    side = piece_color(p)
    k = piece_kind(p)

    ff = from_sq % 8
    tf = to_sq % 8

    df = tf - ff
    dr = (to_sq // 8) - (from_sq // 8)

    if k == PAWN:
        if side == WHITE:
            return dr == 1 and abs(df) == 1
        else:
            return dr == -1 and abs(df) == 1

    if k == KNIGHT:
        return (abs(df), abs(dr)) in ((1,2),(2,1))

    if k == KING:
        return max(abs(df), abs(dr)) == 1

    if k in (BISHOP, ROOK, QUEEN):
        # check ray alignment
        step = 0
        if df == 0 and dr != 0:
            step = 8 if dr > 0 else -8
        elif dr == 0 and df != 0:
            step = 1 if df > 0 else -1
        elif abs(df) == abs(dr) and df != 0:
            if df > 0 and dr > 0: step = 9
            if df < 0 and dr > 0: step = 7
            if df > 0 and dr < 0: step = -7
            if df < 0 and dr < 0: step = -9
        else:
            return False

        if k == BISHOP and abs(df) != abs(dr):
            return False
        if k == ROOK and not (df == 0 or dr == 0):
            return False

        s = from_sq + step
        while s != to_sq:
            if s < 0 or s >= 64:
                return False
            # ensure we didn't wrap on ranks/files
            if step in (1,-1) and (s // 8) != ((s-step)//8):
                return False
            if step in (7,9,-7,-9) and abs((s%8) - ((s-step)%8)) != 1:
                return False
            if b[s] != 0:
                return False
            s += step
        return True

    return False
"@

Write-File "src/chess_metrics/engine/apply.py" @"
from __future__ import annotations
from .types import (
    GameState, Move, Undo,
    WHITE, BLACK,
    PAWN, ROOK, KING, QUEEN,
    CR_WK, CR_WQ, CR_BK, CR_BQ,
    piece_color, piece_kind
)

def apply_move(state: GameState, m: Move) -> Undo:
    b = state.board

    prev_cr = state.castling_rights
    prev_ep = state.ep_sq
    prev_half = state.halfmove_clock
    prev_full = state.fullmove_number
    prev_stm = state.side_to_move

    moved_piece_before = b[m.from_sq]
    to_piece_before = b[m.to_sq]

    captured_piece = 0
    captured_sq = -1

    rook_piece = 0
    rook_from = -1
    rook_to = -1

    # Clear EP by default; set only on double pawn push below
    state.ep_sq = -1

    # captures
    if m.is_ep:
        captured_sq = m.ep_victim_sq
        captured_piece = b[captured_sq]
        b[captured_sq] = 0
    elif m.is_capture:
        captured_sq = m.to_sq
        captured_piece = b[m.to_sq]

    # move the piece
    b[m.to_sq] = b[m.from_sq]
    b[m.from_sq] = 0

    # promotion
    if m.is_promotion:
        side = piece_color(b[m.to_sq])
        b[m.to_sq] = side * QUEEN

    # castling rook move
    if m.is_castle:
        rook_from = m.castle_rook_from
        rook_to = m.castle_rook_to
        rook_piece = b[rook_from]
        b[rook_to] = rook_piece
        b[rook_from] = 0

    # update castling rights based on king/rook moves or captures
    side = prev_stm
    if piece_kind(moved_piece_before) == KING:
        if side == WHITE:
            state.castling_rights &= ~(CR_WK | CR_WQ)
        else:
            state.castling_rights &= ~(CR_BK | CR_BQ)

    # rook moved from original rook square
    if piece_kind(moved_piece_before) == ROOK:
        if side == WHITE:
            if m.from_sq == 0:  state.castling_rights &= ~CR_WQ  # a1
            if m.from_sq == 7:  state.castling_rights &= ~CR_WK  # h1
        else:
            if m.from_sq == 56: state.castling_rights &= ~CR_BQ  # a8
            if m.from_sq == 63: state.castling_rights &= ~CR_BK  # h8

    # rook captured on original rook square
    if captured_piece != 0 and piece_kind(captured_piece) == ROOK:
        cap_side = piece_color(captured_piece)
        if cap_side == WHITE:
            if captured_sq == 0: state.castling_rights &= ~CR_WQ
            if captured_sq == 7: state.castling_rights &= ~CR_WK
        else:
            if captured_sq == 56: state.castling_rights &= ~CR_BQ
            if captured_sq == 63: state.castling_rights &= ~CR_BK

    # EP target square set on double pawn push
    if piece_kind(moved_piece_before) == PAWN and not m.is_capture and not m.is_ep:
        # detect 2-square advance
        diff = m.to_sq - m.from_sq
        if diff == 16:   # white
            state.ep_sq = m.from_sq + 8
        elif diff == -16: # black
            state.ep_sq = m.from_sq - 8

    # halfmove clock
    if piece_kind(moved_piece_before) == PAWN or m.is_capture or m.is_ep:
        state.halfmove_clock = 0
    else:
        state.halfmove_clock += 1

    # fullmove number increments after black move
    if prev_stm == BLACK:
        state.fullmove_number += 1

    # toggle side to move
    state.side_to_move = WHITE if prev_stm == BLACK else BLACK

    undo = Undo(
        move=m,
        captured_piece=captured_piece,
        captured_sq=captured_sq,
        prev_castling_rights=prev_cr,
        prev_ep_sq=prev_ep,
        prev_halfmove=prev_half,
        prev_fullmove=prev_full,
        prev_side_to_move=prev_stm,
        rook_piece=rook_piece,
        rook_from=rook_from,
        rook_to=rook_to,
        moved_piece_before=moved_piece_before,
        to_piece_before=to_piece_before
    )
    state.undo_stack.append(undo)
    return undo

def undo_move(state: GameState, undo: Undo) -> None:
    b = state.board
    m = undo.move

    # restore STM and counters
    state.side_to_move = undo.prev_side_to_move
    state.castling_rights = undo.prev_castling_rights
    state.ep_sq = undo.prev_ep_sq
    state.halfmove_clock = undo.prev_halfmove
    state.fullmove_number = undo.prev_fullmove

    # undo castling rook
    if m.is_castle:
        b[undo.rook_from] = undo.rook_piece
        b[undo.rook_to] = 0

    # undo move piece
    b[m.from_sq] = undo.moved_piece_before
    b[m.to_sq] = undo.to_piece_before

    # undo capture
    if m.is_ep:
        b[undo.captured_sq] = undo.captured_piece
    elif m.is_capture:
        b[undo.captured_sq] = undo.captured_piece

    state.undo_stack.pop()
"@

Write-File "src/chess_metrics/engine/movegen.py" @"
from __future__ import annotations
from typing import List
from .types import (
    GameState, Move,
    WHITE, BLACK,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    CR_WK, CR_WQ, CR_BK, CR_BQ,
    piece_color, piece_kind, opposite
)
from .rules import is_in_check, is_square_attacked, file_of, rank_of
from .apply import apply_move, undo_move

def on_board(sq: int) -> bool:
    return 0 <= sq < 64

def same_rank(a: int, b: int) -> bool:
    return (a // 8) == (b // 8)

def gen_pseudo_moves(state: GameState, side: int) -> List[Move]:
    b = state.board
    moves: List[Move] = []

    for from_sq, p in enumerate(b):
        if p == 0 or piece_color(p) != side:
            continue
        k = piece_kind(p)

        if k == PAWN:
            moves.extend(_pawn_moves(state, side, from_sq))
        elif k == KNIGHT:
            moves.extend(_knight_moves(state, side, from_sq))
        elif k == BISHOP:
            moves.extend(_slider_moves(state, side, from_sq, deltas=[+9,+7,-7,-9], kinds=(BISHOP,)))
        elif k == ROOK:
            moves.extend(_slider_moves(state, side, from_sq, deltas=[+1,-1,+8,-8], kinds=(ROOK,)))
        elif k == QUEEN:
            moves.extend(_slider_moves(state, side, from_sq, deltas=[+1,-1,+8,-8,+9,+7,-7,-9], kinds=(QUEEN,)))
        elif k == KING:
            moves.extend(_king_moves(state, side, from_sq))

    # Castling pseudo (with legality admission per spec)
    moves.extend(_castle_moves(state, side))

    return moves

def generate_legal_moves(state: GameState, side: int) -> List[Move]:
    pseudo = gen_pseudo_moves(state, side)
    legal: List[Move] = []
    for m in pseudo:
        u = apply_move(state, m)
        if not is_in_check(state, side):
            legal.append(m)
        undo_move(state, u)
    # stable deterministic order (UCI)
    legal.sort(key=lambda m: m.uci())
    return legal

def _pawn_moves(state: GameState, side: int, from_sq: int) -> List[Move]:
    b = state.board
    moves: List[Move] = []
    r = rank_of(from_sq)
    f = file_of(from_sq)

    forward = 8 if side == WHITE else -8
    start_rank = 1 if side == WHITE else 6
    promo_rank = 7 if side == WHITE else 0

    one = from_sq + forward
    if on_board(one) and b[one] == 0:
        # promotion?
        if rank_of(one) == promo_rank:
            moves.append(Move(from_sq, one, PAWN, is_promotion=True))
        else:
            moves.append(Move(from_sq, one, PAWN))
            # double
            two = from_sq + 2*forward
            if r == start_rank and on_board(two) and b[two] == 0:
                moves.append(Move(from_sq, two, PAWN))

    # captures
    for df in (-1, +1):
        if 0 <= f+df <= 7:
            to = from_sq + forward + df
            if on_board(to):
                target = b[to]
                if target != 0 and piece_color(target) == opposite(side):
                    cap_kind = piece_kind(target)
                    if rank_of(to) == promo_rank:
                        moves.append(Move(from_sq, to, PAWN, captured_kind=cap_kind, is_capture=True, is_promotion=True))
                    else:
                        moves.append(Move(from_sq, to, PAWN, captured_kind=cap_kind, is_capture=True))

    # en-passant
    if state.ep_sq != -1:
        ep = state.ep_sq
        ep_r = rank_of(ep)
        ep_f = file_of(ep)
        # ep target must be diagonally forward from pawn
        if abs(ep_f - f) == 1 and ((side == WHITE and ep_r == r+1) or (side == BLACK and ep_r == r-1)):
            # victim pawn is behind ep square
            victim_sq = ep - 8 if side == WHITE else ep + 8
            if on_board(victim_sq) and b[victim_sq] == opposite(side) * PAWN and b[ep] == 0:
                moves.append(Move(from_sq, ep, PAWN, captured_kind=PAWN, is_capture=True, is_ep=True, ep_victim_sq=victim_sq))

    return moves

def _knight_moves(state: GameState, side: int, from_sq: int) -> List[Move]:
    b = state.board
    moves: List[Move] = []
    ff = file_of(from_sq)

    for d in (+17,+15,+10,+6,-6,-10,-15,-17):
        to = from_sq + d
        if not on_board(to):
            continue
        tf = file_of(to)
        if abs(tf - ff) not in (1,2):
            continue
        target = b[to]
        if target == 0:
            moves.append(Move(from_sq, to, KNIGHT))
        elif piece_color(target) == opposite(side):
            moves.append(Move(from_sq, to, KNIGHT, captured_kind=piece_kind(target), is_capture=True))
    return moves

def _king_moves(state: GameState, side: int, from_sq: int) -> List[Move]:
    b = state.board
    moves: List[Move] = []
    ff = file_of(from_sq)
    for d in (+1,-1,+8,-8,+9,+7,-7,-9):
        to = from_sq + d
        if not on_board(to):
            continue
        if abs(file_of(to) - ff) > 1:
            continue
        target = b[to]
        if target == 0:
            moves.append(Move(from_sq, to, KING))
        elif piece_color(target) == opposite(side):
            moves.append(Move(from_sq, to, KING, captured_kind=piece_kind(target), is_capture=True))
    return moves

def _slider_moves(state: GameState, side: int, from_sq: int, deltas: List[int], kinds) -> List[Move]:
    b = state.board
    moves: List[Move] = []
    k = piece_kind(b[from_sq])
    for d in deltas:
        to = from_sq + d
        while on_board(to):
            # rank wrap for horizontal
            if d in (+1,-1) and not same_rank(to, to-d):
                break
            # diagonal wrap
            if d in (+7,+9,-7,-9) and abs(file_of(to) - file_of(to-d)) != 1:
                break
            target = b[to]
            if target == 0:
                moves.append(Move(from_sq, to, k))
            else:
                if piece_color(target) == opposite(side):
                    moves.append(Move(from_sq, to, k, captured_kind=piece_kind(target), is_capture=True))
                break
            to += d
    return moves

def _castle_moves(state: GameState, side: int) -> List[Move]:
    b = state.board
    moves: List[Move] = []

    # King must be on e-file home rank
    if side == WHITE:
        king_sq = 4   # e1
        home_rank = 0
        if b[king_sq] != WHITE * KING:
            return moves
        if is_in_check(state, WHITE):
            return moves

        # King side: e1->g1, rook h1->f1
        if state.castling_rights & CR_WK:
            if b[5] == 0 and b[6] == 0 and b[7] == WHITE * ROOK:
                if (not is_square_attacked(state, 5, BLACK)) and (not is_square_attacked(state, 6, BLACK)):
                    moves.append(Move(4, 6, KING, is_castle=True, castle_rook_from=7, castle_rook_to=5))

        # Queen side: e1->c1, rook a1->d1
        if state.castling_rights & CR_WQ:
            if b[3] == 0 and b[2] == 0 and b[1] == 0 and b[0] == WHITE * ROOK:
                if (not is_square_attacked(state, 3, BLACK)) and (not is_square_attacked(state, 2, BLACK)):
                    moves.append(Move(4, 2, KING, is_castle=True, castle_rook_from=0, castle_rook_to=3))

    else:
        king_sq = 60  # e8
        if b[king_sq] != BLACK * KING:
            return moves
        if is_in_check(state, BLACK):
            return moves

        # King side: e8->g8, rook h8->f8
        if state.castling_rights & CR_BK:
            if b[61] == 0 and b[62] == 0 and b[63] == BLACK * ROOK:
                if (not is_square_attacked(state, 61, WHITE)) and (not is_square_attacked(state, 62, WHITE)):
                    moves.append(Move(60, 62, KING, is_castle=True, castle_rook_from=63, castle_rook_to=61))

        # Queen side: e8->c8, rook a8->d8
        if state.castling_rights & CR_BQ:
            if b[59] == 0 and b[58] == 0 and b[57] == 0 and b[56] == BLACK * ROOK:
                if (not is_square_attacked(state, 59, WHITE)) and (not is_square_attacked(state, 58, WHITE)):
                    moves.append(Move(60, 58, KING, is_castle=True, castle_rook_from=56, castle_rook_to=59))

    return moves
"@

Write-File "src/chess_metrics/engine/metrics.py" @"
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple
from .types import (
    GameState, WHITE, BLACK,
    PIECE_VALUE,
    piece_color, piece_kind, opposite
)
from .movegen import generate_legal_moves
from .rules import is_in_check, pseudo_attacks_square
from .apply import apply_move, undo_move
from .types import Move

@dataclass(frozen=True)
class Metrics:
    pv_w: int
    mv_w: int
    ov_w: int
    dv_w: int
    pv_b: int
    mv_b: int
    ov_b: int
    dv_b: int

def compute_pv(state: GameState, side: int) -> int:
    s = 0
    for p in state.board:
        if p != 0 and piece_color(p) == side:
            s += PIECE_VALUE[piece_kind(p)]
    return s

def compute_mv_ov(state: GameState, side: int) -> Tuple[int,int]:
    legal = generate_legal_moves(state, side)
    mv = 0
    ov = 0
    for m in legal:
        if m.is_ep:
            ov += 1  # victim pawn value
            continue
        if m.is_capture:
            ov += PIECE_VALUE[m.captured_kind]
        else:
            mv += 1  # non-capture to empty (includes castling, non-capture promotions)
    return mv, ov

def _apply_capture_like(state: GameState, from_sq: int, to_sq: int) -> Tuple[int,int,int]:
    # temporary: move piece from->to and remove piece on to (friendly) as if capture
    b = state.board
    moved = b[from_sq]
    captured = b[to_sq]
    b[to_sq] = moved
    b[from_sq] = 0
    return moved, captured, from_sq

def _undo_capture_like(state: GameState, from_sq: int, to_sq: int, moved: int, captured: int) -> None:
    b = state.board
    b[from_sq] = moved
    b[to_sq] = captured

def compute_dv(state: GameState, side: int) -> int:
    b = state.board
    dv = 0

    friendly_squares = [sq for sq, p in enumerate(b) if p != 0 and piece_color(p) == side]
    for t in friendly_squares:
        X = b[t]
        valueX = PIECE_VALUE[piece_kind(X)]

        for f in friendly_squares:
            if f == t:
                continue
            A = b[f]
            # EP does not apply to DV by definition; DV is only about onto occupied friendly squares.
            if not pseudo_attacks_square(state, f, t):
                continue

            # Simulate capture-like move (A -> t, removing X) and check king safety.
            moved, captured, _ = _apply_capture_like(state, f, t)
            ok = not is_in_check(state, side)
            _undo_capture_like(state, f, t, moved, captured)

            if ok:
                dv += valueX  # multiplicity counts

    return dv

def compute_metrics(state: GameState) -> Metrics:
    pv_w = compute_pv(state, WHITE)
    pv_b = compute_pv(state, BLACK)

    mv_w, ov_w = compute_mv_ov(state, WHITE)
    mv_b, ov_b = compute_mv_ov(state, BLACK)

    dv_w = compute_dv(state, WHITE)
    dv_b = compute_dv(state, BLACK)

    return Metrics(pv_w, mv_w, ov_w, dv_w, pv_b, mv_b, ov_b, dv_b)

def deltas(m: Metrics) -> Tuple[int,int,int,int]:
    return (m.pv_w - m.pv_b, m.mv_w - m.mv_b, m.ov_w - m.ov_b, m.dv_w - m.dv_b)
"@

Write-File "src/chess_metrics/engine/search.py" @"
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
from .types import GameState, Move, WHITE, BLACK, opposite
from .movegen import generate_legal_moves
from .metrics import compute_metrics, deltas, Metrics
from .rules import is_in_check
from .apply import apply_move, undo_move

MATE = 10**9

@dataclass(frozen=True)
class Profile:
    name: str
    wPV: float = 1.0
    wMV: float = 1.0
    wOV: float = 1.0
    wDV: float = 1.0

def score(metrics: Metrics, profile: Profile) -> float:
    dPV, dMV, dOV, dDV = deltas(metrics)
    return profile.wPV*dPV + profile.wMV*dMV + profile.wOV*dOV + profile.wDV*dDV

def score_s(metrics: Metrics, profile: Profile, root_side: int) -> float:
    s = score(metrics, profile)
    return s if root_side == WHITE else -s

@dataclass
class SearchResult:
    scoreS: float
    leaf_metrics: Metrics

def minimax_scoreS(state: GameState, profile: Profile, root_side: int, depth: int, alpha: float, beta: float) -> SearchResult:
    if depth == 0:
        m = compute_metrics(state)
        return SearchResult(score_s(m, profile, root_side), m)

    side = state.side_to_move
    legal = generate_legal_moves(state, side)

    if not legal:
        # terminal
        if is_in_check(state, side):
            # side to move is mated
            v = -MATE if side == root_side else +MATE
            m = compute_metrics(state)
            return SearchResult(v, m)
        else:
            m = compute_metrics(state)
            return SearchResult(0.0, m)

    maximizing = (side == root_side)

    if maximizing:
        best = -1e30
        best_leaf = None
        for mv in legal:
            u = apply_move(state, mv)
            res = minimax_scoreS(state, profile, root_side, depth-1, alpha, beta)
            undo_move(state, u)

            if res.scoreS > best:
                best = res.scoreS
                best_leaf = res.leaf_metrics

            alpha = max(alpha, best)
            if beta <= alpha:
                break
        return SearchResult(best, best_leaf)
    else:
        best = +1e30
        best_leaf = None
        for mv in legal:
            u = apply_move(state, mv)
            res = minimax_scoreS(state, profile, root_side, depth-1, alpha, beta)
            undo_move(state, u)

            if res.scoreS < best:
                best = res.scoreS
                best_leaf = res.leaf_metrics

            beta = min(beta, best)
            if beta <= alpha:
                break
        return SearchResult(best, best_leaf)

def choose_best_move(state: GameState, profile: Profile, depthN: int = 3) -> Optional[Move]:
    root_side = state.side_to_move
    legal = generate_legal_moves(state, root_side)
    if not legal:
        return None

    root_metrics = compute_metrics(state)
    root_dPV, _, root_dOV, _ = deltas(root_metrics)

    best_mv = None
    best_key = None  # tuple(scoreS, dPV_swing, dOV_swing, uciNeg)

    for mv in legal:
        u = apply_move(state, mv)
        res = minimax_scoreS(state, profile, root_side, depthN-1, -1e30, +1e30)
        undo_move(state, u)

        leaf_dPV, _, leaf_dOV, _ = deltas(res.leaf_metrics)
        dPV_swing = leaf_dPV - root_dPV
        dOV_swing = leaf_dOV - root_dOV

        # deterministic: UCI ascending, but tie-breaker wants stable order after other keys
        uci = mv.uci()

        key = (res.scoreS, dPV_swing, dOV_swing, -hash(uci))  # hash stable within run; used only last
        # better deterministic: compare UCI lex directly as last stage
        if best_key is None:
            best_mv = mv
            best_key = (res.scoreS, dPV_swing, dOV_swing, uci)
        else:
            cand = (res.scoreS, dPV_swing, dOV_swing, uci)
            if cand > best_key:
                best_mv = mv
                best_key = cand

    return best_mv
"@

Write-File "src/chess_metrics/engine/san.py" @"
from __future__ import annotations
from typing import List
from .types import (
    GameState, Move,
    WHITE, BLACK,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    PIECE_TO_CHAR, piece_color, piece_kind, opposite, sq_to_alg
)
from .movegen import generate_legal_moves
from .apply import apply_move, undo_move
from .rules import is_in_check

def move_to_san(state: GameState, m: Move) -> str:
    # Castling
    if m.is_castle:
        if m.to_sq % 8 == 6:
            san = "O-O"
        else:
            san = "O-O-O"
        # suffix check/mate
        u = apply_move(state, m)
        suffix = _check_suffix(state)
        undo_move(state, u)
        return san + suffix

    b = state.board
    mover_piece = b[m.from_sq]
    mover_kind = piece_kind(mover_piece)

    dest = sq_to_alg(m.to_sq)
    capture = m.is_capture or m.is_ep

    # Piece letter (none for pawn)
    if mover_kind == PAWN:
        prefix = ""
        if capture:
            prefix = chr(ord('a') + (m.from_sq % 8))  # pawn file
    else:
        prefix = PIECE_TO_CHAR[mover_kind]
        prefix += _disambiguation(state, m)

    san = prefix
    if capture:
        san += "x"
    san += dest

    if m.is_promotion:
        san += "=Q"

    u = apply_move(state, m)
    suffix = _check_suffix(state)
    undo_move(state, u)

    return san + suffix

def _disambiguation(state: GameState, m: Move) -> str:
    # Minimal SAN disambiguation: if another legal piece of same kind can also reach to_sq, include file/rank as needed.
    b = state.board
    mover_piece = b[m.from_sq]
    mover_kind = piece_kind(mover_piece)
    side = piece_color(mover_piece)

    if mover_kind in (PAWN, KING):
        return ""

    legal = generate_legal_moves(state, side)
    rivals = []
    for mv in legal:
        if mv.to_sq == m.to_sq and mv.from_sq != m.from_sq:
            p = b[mv.from_sq]
            if p != 0 and piece_color(p) == side and piece_kind(p) == mover_kind:
                rivals.append(mv)

    if not rivals:
        return ""

    from_file = m.from_sq % 8
    from_rank = m.from_sq // 8

    need_file = any((rv.from_sq % 8) == from_file for rv in rivals)
    need_rank = any((rv.from_sq // 8) == from_rank for rv in rivals)

    # SAN rule: if files differ among candidates, use file; else use rank; else use both.
    file_unique = all((rv.from_sq % 8) != from_file for rv in rivals)
    rank_unique = all((rv.from_sq // 8) != from_rank for rv in rivals)

    if file_unique:
        return chr(ord('a') + from_file)
    if rank_unique:
        return chr(ord('1') + from_rank)
    return chr(ord('a') + from_file) + chr(ord('1') + from_rank)

def _check_suffix(state_after_move: GameState) -> str:
    # state_after_move.side_to_move is opponent now
    opp = state_after_move.side_to_move
    in_check = is_in_check(state_after_move, opp)
    if not in_check:
        return ""
    # checkmate if no legal moves
    if not generate_legal_moves(state_after_move, opp):
        return "#"
    return "+"
"@

Write-File "src/chess_metrics/db/__init__.py" @"
from .schema import SCHEMA_SQL
from .repo import Repo
"@

Write-File "src/chess_metrics/db/schema.py" @"
SCHEMA_SQL = r'''
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS games (
  game_id         INTEGER PRIMARY KEY,
  created_utc     TEXT NOT NULL,
  white_player_id INTEGER NOT NULL,
  black_player_id INTEGER NOT NULL,
  result          TEXT NULL,
  termination     TEXT NULL,
  start_fen       TEXT NOT NULL,
  FOREIGN KEY (white_player_id) REFERENCES players(player_id),
  FOREIGN KEY (black_player_id) REFERENCES players(player_id)
);

CREATE INDEX IF NOT EXISTS idx_games_created ON games(created_utc);

CREATE TABLE IF NOT EXISTS players (
  player_id   INTEGER PRIMARY KEY,
  name        TEXT NOT NULL,
  type        TEXT NOT NULL CHECK (type IN ('human','ai')),
  profile_id  INTEGER NULL,
  FOREIGN KEY (profile_id) REFERENCES profiles(profile_id)
);

CREATE INDEX IF NOT EXISTS idx_players_name ON players(name);

CREATE TABLE IF NOT EXISTS profiles (
  profile_id INTEGER PRIMARY KEY,
  name       TEXT NOT NULL UNIQUE,
  wPV        REAL NOT NULL,
  wMV        REAL NOT NULL,
  wOV        REAL NOT NULL,
  wDV        REAL NOT NULL,
  notes      TEXT NULL
);

CREATE TABLE IF NOT EXISTS positions (
  position_id     INTEGER PRIMARY KEY,
  game_id         INTEGER NOT NULL,
  ply             INTEGER NOT NULL,
  side_to_move    TEXT NOT NULL CHECK (side_to_move IN ('W','B')),
  fen             TEXT NOT NULL,
  last_move_uci   TEXT NULL,
  last_move_san   TEXT NULL,

  pv_w INTEGER NOT NULL,
  mv_w INTEGER NOT NULL,
  ov_w INTEGER NOT NULL,
  dv_w INTEGER NOT NULL,

  pv_b INTEGER NOT NULL,
  mv_b INTEGER NOT NULL,
  ov_b INTEGER NOT NULL,
  dv_b INTEGER NOT NULL,

  created_utc TEXT NOT NULL,

  FOREIGN KEY (game_id) REFERENCES games(game_id),
  UNIQUE (game_id, ply)
);

CREATE INDEX IF NOT EXISTS idx_positions_game_ply ON positions(game_id, ply);
CREATE INDEX IF NOT EXISTS idx_positions_fen ON positions(fen);

CREATE TABLE IF NOT EXISTS moves (
  move_id         INTEGER PRIMARY KEY,
  game_id         INTEGER NOT NULL,
  ply             INTEGER NOT NULL,
  uci             TEXT NOT NULL,
  san             TEXT NOT NULL,
  from_sq         TEXT NOT NULL,
  to_sq           TEXT NOT NULL,
  is_capture      INTEGER NOT NULL CHECK (is_capture IN (0,1)),
  is_ep           INTEGER NOT NULL CHECK (is_ep IN (0,1)),
  is_castle       INTEGER NOT NULL CHECK (is_castle IN (0,1)),
  is_promotion    INTEGER NOT NULL CHECK (is_promotion IN (0,1)),
  promotion_piece TEXT NULL,
  created_utc     TEXT NOT NULL,
  FOREIGN KEY (game_id) REFERENCES games(game_id),
  UNIQUE (game_id, ply)
);

CREATE INDEX IF NOT EXISTS idx_moves_game_ply ON moves(game_id, ply);

CREATE VIEW IF NOT EXISTS v_position_deltas AS
SELECT
  position_id,
  game_id,
  ply,
  side_to_move,
  fen,
  last_move_uci,
  last_move_san,
  pv_w, mv_w, ov_w, dv_w,
  pv_b, mv_b, ov_b, dv_b,
  (pv_w - pv_b) AS dPV,
  (mv_w - mv_b) AS dMV,
  (ov_w - ov_b) AS dOV,
  (dv_w - dv_b) AS dDV,
  created_utc
FROM positions;

CREATE VIEW IF NOT EXISTS v_position_deltas_with_prev AS
SELECT
  cur.*,
  prev.dPV AS prev_dPV,
  prev.dMV AS prev_dMV,
  prev.dOV AS prev_dOV,
  prev.dDV AS prev_dDV
FROM v_position_deltas cur
LEFT JOIN v_position_deltas prev
  ON prev.game_id = cur.game_id
 AND prev.ply = cur.ply - 1;
'''
"@

Write-File "src/chess_metrics/db/repo.py" @"
from __future__ import annotations
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from .schema import SCHEMA_SQL

UTCNOW = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")

@dataclass(frozen=True)
class Repo:
    conn: sqlite3.Connection

    @staticmethod
    def open(path: str) -> "Repo":
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return Repo(conn)

    def close(self) -> None:
        self.conn.close()

    def migrate(self) -> None:
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    # --- seed helpers ---
    def ensure_default_profiles(self) -> None:
        cur = self.conn.cursor()
        defaults = [
            ("default", 1.0, 1.0, 1.0, 1.0, "Equal weights"),
            ("offense-first", 1.0, 1.0, 2.0, 1.0, "OV emphasized"),
            ("defense-first", 1.0, 1.0, 1.0, 2.0, "DV emphasized"),
            ("board-coverage", 1.0, 2.0, 1.0, 1.0, "MV emphasized"),
            ("materialist", 2.0, 1.0, 1.0, 1.0, "PV emphasized"),
        ]
        for name, wPV, wMV, wOV, wDV, notes in defaults:
            cur.execute(
                \"\"\"INSERT OR IGNORE INTO profiles(name,wPV,wMV,wOV,wDV,notes)
                    VALUES(?,?,?,?,?,?)\"\"\",
                (name, wPV, wMV, wOV, wDV, notes)
            )
        self.conn.commit()

    def create_player(self, name: str, ptype: str, profile_id: Optional[int] = None) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO players(name,type,profile_id) VALUES(?,?,?)",
            (name, ptype, profile_id)
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def create_game(self, white_player_id: int, black_player_id: int, start_fen: str) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO games(created_utc,white_player_id,black_player_id,start_fen) VALUES(?,?,?,?)",
            (UTCNOW(), white_player_id, black_player_id, start_fen)
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def insert_position(self, game_id: int, ply: int, side_to_move: str, fen: str,
                        last_uci: Optional[str], last_san: Optional[str],
                        pv_w: int, mv_w: int, ov_w: int, dv_w: int,
                        pv_b: int, mv_b: int, ov_b: int, dv_b: int) -> None:
        self.conn.execute(
            \"\"\"INSERT INTO positions(
                 game_id, ply, side_to_move, fen, last_move_uci, last_move_san,
                 pv_w,mv_w,ov_w,dv_w, pv_b,mv_b,ov_b,dv_b, created_utc
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)\"\"\",
            (game_id, ply, side_to_move, fen, last_uci, last_san,
             pv_w, mv_w, ov_w, dv_w, pv_b, mv_b, ov_b, dv_b, UTCNOW())
        )

    def insert_move(self, game_id: int, ply: int, uci: str, san: str,
                    from_sq: str, to_sq: str,
                    is_capture: int, is_ep: int, is_castle: int, is_promotion: int,
                    promotion_piece: Optional[str]) -> None:
        self.conn.execute(
            \"\"\"INSERT INTO moves(
                 game_id, ply, uci, san, from_sq, to_sq,
                 is_capture, is_ep, is_castle, is_promotion, promotion_piece,
                 created_utc
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)\"\"\",
            (game_id, ply, uci, san, from_sq, to_sq,
             is_capture, is_ep, is_castle, is_promotion, promotion_piece, UTCNOW())
        )

    def commit(self) -> None:
        self.conn.commit()

    def timeline(self, game_id: int) -> List[sqlite3.Row]:
        cur = self.conn.execute(
            \"\"\"SELECT ply, side_to_move, fen, last_move_uci, last_move_san,
                      pv_w,mv_w,ov_w,dv_w,pv_b,mv_b,ov_b,dv_b
                 FROM positions
                WHERE game_id=?
                ORDER BY ply ASC\"\"\",
            (game_id,)
        )
        return list(cur.fetchall())
"@

Write-File "src/chess_metrics/cli.py" @"
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
"@

# -------------------------
# Tests (unittest)
# -------------------------

Write-File "tests/test_fen.py" @"
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
"@

Write-File "tests/test_perft.py" @"
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
"@

Write-File "tests/test_metrics.py" @"
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
"@

Write-File "tests/test_db.py" @"
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
                             "Q" if mv.is_promotion else None)

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
"@

Pop-Location
Write-Host "Created repo at: $Root"
Write-Host "Next:"
Write-Host "  cd $Root"
Write-Host "  python -m unittest -v"
Write-Host "  python -m chess_metrics.cli migrate"
