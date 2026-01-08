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
                """INSERT OR IGNORE INTO profiles(name,wPV,wMV,wOV,wDV,notes)
                    VALUES(?,?,?,?,?,?)""",
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
        assert cur.lastrowid is not None, "Failed to get lastrowid after insert"
        return cur.lastrowid

    def create_game(self, white_player_id: int, black_player_id: int, start_fen: str) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO games(created_utc,white_player_id,black_player_id,start_fen) VALUES(?,?,?,?)",
            (UTCNOW(), white_player_id, black_player_id, start_fen)
        )
        self.conn.commit()
        assert cur.lastrowid is not None, "Failed to get lastrowid after insert"
        return cur.lastrowid

    def insert_position(self, game_id: int, ply: int, side_to_move: str, fen: str,
                        last_uci: Optional[str], last_san: Optional[str],
                        pv_w: float, mv_w: float, ov_w: float, dv_w: float,
                        pv_b: float, mv_b: float, ov_b: float, dv_b: float) -> None:
        self.conn.execute(
            """INSERT INTO positions(
                 game_id, ply, side_to_move, fen, last_move_uci, last_move_san,
                 pv_w,mv_w,ov_w,dv_w, pv_b,mv_b,ov_b,dv_b, created_utc
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (game_id, ply, side_to_move, fen, last_uci, last_san,
             pv_w, mv_w, ov_w, dv_w, pv_b, mv_b, ov_b, dv_b, UTCNOW())
        )

    def insert_move(self, game_id: int, ply: int, uci: str, san: str,
                    from_sq: str, to_sq: str,
                    is_capture: int, is_ep: int, is_castle: int, is_promotion: int,
                    promotion_piece: Optional[str], variance_factor: Optional[float] = None) -> None:
        self.conn.execute(
            """INSERT INTO moves(
                 game_id, ply, uci, san, from_sq, to_sq,
                 is_capture, is_ep, is_castle, is_promotion, promotion_piece,
                 variance_factor, created_utc
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (game_id, ply, uci, san, from_sq, to_sq,
             is_capture, is_ep, is_castle, is_promotion, promotion_piece,
             variance_factor, UTCNOW())
        )

    def commit(self) -> None:
        self.conn.commit()

    def timeline(self, game_id: int) -> List[sqlite3.Row]:
        cur = self.conn.execute(
            """SELECT ply, side_to_move, fen, last_move_uci, last_move_san,
                      pv_w,mv_w,ov_w,dv_w,pv_b,mv_b,ov_b,dv_b
                 FROM positions
                WHERE game_id=?
                ORDER BY ply ASC""",
            (game_id,)
        )
        return list(cur.fetchall())

    def get_game_for_pgn(self, game_id: int) -> Optional[Dict[str, Any]]:
        """
        Get all game data needed for PGN export.

        Returns:
            Dictionary with 'game' metadata and 'moves' list, or None if game not found
        """
        # Query game metadata with player info
        game_row = self.conn.execute(
            """SELECT g.game_id, g.created_utc, g.result, g.termination, g.start_fen,
                      wp.name as white_name, wp.type as white_type,
                      bp.name as black_name, bp.type as black_type
               FROM games g
               JOIN players wp ON g.white_player_id = wp.player_id
               JOIN players bp ON g.black_player_id = bp.player_id
               WHERE g.game_id = ?""",
            (game_id,)
        ).fetchone()

        if not game_row:
            return None

        # Convert Row to dict
        game_data = dict(game_row)

        # Query moves with position metrics
        moves_rows = self.conn.execute(
            """SELECT m.ply, m.san, m.uci,
                      p.pv_w, p.mv_w, p.ov_w, p.dv_w,
                      p.pv_b, p.mv_b, p.ov_b, p.dv_b
               FROM moves m
               JOIN positions p ON m.game_id = p.game_id AND m.ply = p.ply
               WHERE m.game_id = ?
               ORDER BY m.ply ASC""",
            (game_id,)
        ).fetchall()

        # Convert moves to list of dicts
        moves = []
        for row in moves_rows:
            move_dict = {
                'ply': row['ply'],
                'san': row['san'],
                'uci': row['uci'],
                'metrics': {
                    'pv_w': row['pv_w'],
                    'mv_w': row['mv_w'],
                    'ov_w': row['ov_w'],
                    'dv_w': row['dv_w'],
                    'pv_b': row['pv_b'],
                    'mv_b': row['mv_b'],
                    'ov_b': row['ov_b'],
                    'dv_b': row['dv_b'],
                }
            }
            moves.append(move_dict)

        return {'game': game_data, 'moves': moves}

    def get_all_game_ids(self) -> List[int]:
        """Get list of all game IDs in database."""
        rows = self.conn.execute("SELECT game_id FROM games ORDER BY game_id ASC").fetchall()
        return [row['game_id'] for row in rows]

    def get_game_ids_in_range(self, start: int, end: int) -> List[int]:
        """Get list of game IDs in specified range (inclusive)."""
        rows = self.conn.execute(
            "SELECT game_id FROM games WHERE game_id >= ? AND game_id <= ? ORDER BY game_id ASC",
            (start, end)
        ).fetchall()
        return [row['game_id'] for row in rows]