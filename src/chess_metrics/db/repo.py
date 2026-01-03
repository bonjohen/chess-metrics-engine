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
                        pv_w: int, mv_w: int, ov_w: int, dv_w: int,
                        pv_b: int, mv_b: int, ov_b: int, dv_b: int) -> None:
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
                    promotion_piece: Optional[str]) -> None:
        self.conn.execute(
            """INSERT INTO moves(
                 game_id, ply, uci, san, from_sq, to_sq,
                 is_capture, is_ep, is_castle, is_promotion, promotion_piece,
                 created_utc
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (game_id, ply, uci, san, from_sq, to_sq,
             is_capture, is_ep, is_castle, is_promotion, promotion_piece, UTCNOW())
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