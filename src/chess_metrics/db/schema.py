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
