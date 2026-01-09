"""
Flask web application for chess metrics viewer.
"""
from __future__ import annotations
import os
from flask import Flask, render_template, jsonify, request
from typing import Optional

from chess_metrics.db.repo import Repo
from chess_metrics.analysis import (
    detect_blunders, find_critical_positions, calculate_statistics
)


def create_app(db_path: str = "chess.sqlite") -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    app.config['DATABASE'] = db_path
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    
    # Get database connection
    def get_repo() -> Repo:
        return Repo.open(app.config['DATABASE'])
    
    @app.route('/')
    def index():
        """Game list page."""
        return render_template('index.html')
    
    @app.route('/game/<int:game_id>')
    def game_viewer(game_id: int):
        """Game viewer page."""
        return render_template('game.html', game_id=game_id)
    
    @app.route('/api/games')
    def api_games():
        """Get list of all games."""
        repo = get_repo()
        try:
            # Get all game IDs
            game_ids = repo.get_all_game_ids()
            
            # Get details for each game
            games = []
            for gid in game_ids:
                game_data = repo.get_game_for_pgn(gid)
                if game_data:
                    g = game_data['game']
                    games.append({
                        'game_id': g['game_id'],
                        'white_name': g['white_name'],
                        'black_name': g['black_name'],
                        'result': g['result'],
                        'termination': g['termination'],
                        'created_utc': g['created_utc'],
                        'move_count': len(game_data['moves'])
                    })
            
            repo.close()
            return jsonify(games)
        except Exception as e:
            repo.close()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/game/<int:game_id>')
    def api_game(game_id: int):
        """Get game details with moves and metrics."""
        repo = get_repo()
        try:
            game_data = repo.get_game_for_analysis(game_id)
            
            if not game_data:
                repo.close()
                return jsonify({'error': 'Game not found'}), 404
            
            # Format response
            response = {
                'game': game_data['game'],
                'positions': game_data['positions']
            }
            
            repo.close()
            return jsonify(response)
        except Exception as e:
            repo.close()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/analysis/<int:game_id>')
    def api_analysis(game_id: int):
        """Get game analysis."""
        repo = get_repo()
        try:
            game_data = repo.get_game_for_analysis(game_id)
            
            if not game_data:
                repo.close()
                return jsonify({'error': 'Game not found'}), 404
            
            positions = game_data['positions']
            
            # Perform analysis
            blunders = detect_blunders(positions)
            critical_positions = find_critical_positions(positions)
            stats = calculate_statistics(positions, blunders)
            
            # Format response
            response = {
                'blunders': [
                    {
                        'ply': b.ply,
                        'side': b.side,
                        'san': b.san,
                        'metric': b.metric,
                        'delta': b.delta,
                        'before': b.before,
                        'after': b.after,
                        'severity': b.severity
                    }
                    for b in blunders
                ],
                'critical_positions': [
                    {
                        'ply': cp.ply,
                        'fen': cp.fen,
                        'san': cp.san,
                        'reason': cp.reason,
                        'metrics': cp.metrics
                    }
                    for cp in critical_positions
                ],
                'statistics': {
                    'total_moves': stats.total_moves,
                    'white_blunders': stats.white_blunders,
                    'black_blunders': stats.black_blunders,
                    'white_mistakes': stats.white_mistakes,
                    'black_mistakes': stats.black_mistakes,
                    'white_inaccuracies': stats.white_inaccuracies,
                    'black_inaccuracies': stats.black_inaccuracies,
                    'avg_pv_white': stats.avg_pv_white,
                    'avg_pv_black': stats.avg_pv_black,
                    'avg_mv_white': stats.avg_mv_white,
                    'avg_mv_black': stats.avg_mv_black,
                    'avg_ov_white': stats.avg_ov_white,
                    'avg_ov_black': stats.avg_ov_black,
                    'avg_dv_white': stats.avg_dv_white,
                    'avg_dv_black': stats.avg_dv_black,
                    'turning_points': stats.turning_points
                }
            }
            
            repo.close()
            return jsonify(response)
        except Exception as e:
            repo.close()
            return jsonify({'error': str(e)}), 500
    
    return app

