from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Game
from engine import get_bot_move, detect_event
from dialogue import get_dialogue_line
import chess
import chess.pgn
import io

api_bp = Blueprint('api', __name__)


@api_bp.route('/move', methods=['POST'])
def bot_move():
    """
    Receive FEN after player's move, return bot's move + dialogue.

    Request JSON:
        {
            "fen": "<FEN string after player move>",
            "bot_id": "aggressive_alex",
            "prev_fen": "<FEN string before player move>"
        }

    Response JSON:
        {
            "move": "e2e4",          # bot's move in UCI notation
            "dialogue": "...",       # personality line
            "event": "blunder"       # detected event key
        }
    """
    data = request.get_json(force=True)
    fen = data.get('fen')
    bot_id = data.get('bot_id', 'balanced_bob')
    prev_fen = data.get('prev_fen')

    if not fen:
        return jsonify({'error': 'fen is required'}), 400

    try:
        board = chess.Board(fen)
    except ValueError:
        return jsonify({'error': 'invalid FEN'}), 400

    # Detect what event happened on the player's move
    event = detect_event(prev_fen, fen, bot_id)

    # Get bot's best move from Stockfish
    bot_uci, new_fen = get_bot_move(fen, bot_id)

    # Fetch a personality dialogue line for the event
    line = get_dialogue_line(bot_id, event)

    return jsonify({
        'move': bot_uci,
        'fen_after': new_fen,
        'dialogue': line,
        'event': event,
    })


@api_bp.route('/save', methods=['POST'])
@login_required
def save_game():
    """
    Save a completed game's PGN to the database.

    Request JSON:
        {
            "pgn": "<PGN string>",
            "result": "1-0",
            "mode": "bot",
            "bot_name": "aggressive_alex",
            "player_color": "white"
        }
    """
    data = request.get_json(force=True)
    pgn_str = data.get('pgn', '')
    result = data.get('result', '*')
    mode = data.get('mode', 'pass_and_play')
    bot_name = data.get('bot_name')
    player_color = data.get('player_color', 'white')

    if not pgn_str:
        return jsonify({'error': 'pgn is required'}), 400

    game = Game(
        user_id=current_user.id,
        pgn=pgn_str,
        result=result,
        mode=mode,
        bot_name=bot_name,
        player_color=player_color,
    )
    db.session.add(game)
    db.session.commit()

    return jsonify({'status': 'saved', 'game_id': game.id})


@api_bp.route('/history', methods=['GET'])
@login_required
def game_history():
    """Return the current user's last 20 games as JSON."""
    games = Game.query.filter_by(user_id=current_user.id)\
                      .order_by(Game.played_at.desc())\
                      .limit(20).all()
    return jsonify([g.to_dict() for g in games])


@api_bp.route('/bots', methods=['GET'])
def list_bots():
    """Return the list of available bot personalities."""
    from dialogue import BOTS_MANIFEST
    return jsonify(BOTS_MANIFEST)
