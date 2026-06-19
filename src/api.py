"""
Add these routes to your existing src/api.py
Replace the entire api.py with this file.
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Game
from engine import get_bot_move, detect_event
from dialogue import get_dialogue_line
from rating import update_player_rating, classify_move, build_style_profile, get_bot_rating
import chess
import chess.pgn
import io
import os
import secrets
import requests

api_bp = Blueprint('api', __name__)


@api_bp.route('/play_token', methods=['POST'])
@login_required
def play_token():
    from play_sessions import _play_tokens
    data  = request.get_json(force=True)
    mode  = data.get('mode', 'bot')
    bot   = data.get('bot', '')
    color = data.get('color', 'white')
    token = secrets.token_urlsafe(8)
    _play_tokens[token] = {'mode': mode, 'bot': bot, 'color': color}
    return jsonify({'token': token})

STOCKFISH_PATH = os.environ.get( 'STOCKFISH_PATH', 'stockfish')  # Default to 'stockfish' in PATH


@api_bp.route('/move', methods=['POST'])
def bot_move():
    data = request.get_json(force=True)
    fen = data.get('fen')
    bot_id = data.get('bot_id', 'recruit')
    prev_fen = data.get('prev_fen')

    if not fen:
        return jsonify({'error': 'fen is required'}), 400

    try:
        board = chess.Board(fen)
    except ValueError:
        return jsonify({'error': 'invalid FEN'}), 400

    try:
        bot_uci, new_fen = get_bot_move(fen, bot_id)
    except Exception as e:
        return jsonify({'error': f'Engine failed: {str(e)}'}), 500

    # Detect event from the bot's OWN move (fen -> new_fen), not the
    # player's prior move. This ensures promotion/capture/check dialogue
    # reacts to what the bot itself just did.
    event = detect_event(fen, new_fen, bot_id)

    line = get_dialogue_line(bot_id, event)

    return jsonify({
        'move': bot_uci,
        'fen_after': new_fen,
        'dialogue': line,
        'event': event,
    })


@api_bp.route('/review', methods=['POST'])
def review_game():
    data = request.get_json(force=True)
    pgn_str = data.get('pgn', '')
    player_color = data.get('player_color', 'white')

    if not pgn_str:
        return jsonify({'error': 'pgn is required'}), 400

    try:
        game = chess.pgn.read_game(io.StringIO(pgn_str))
        if game is None:
            return jsonify({'error': 'invalid PGN'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    moves_data = []
    white_classifications = []
    black_classifications = []

    board = game.board()
    move_num = 1

    # Evaluate the starting position once, then reuse each eval as the
    # next move's cp_before — halves the number of API calls.
    cp_before = _eval_via_api(board.fen())

    for move in game.mainline_moves():
        color = 'white' if board.turn == chess.WHITE else 'black'
        san = board.san(move)
        board.push(move)
        fen_after = board.fen()

        cp_after = _eval_via_api(fen_after)

        if cp_before is not None and cp_after is not None:
            if color == 'white':
                cp_loss = max(0, cp_before - cp_after)
            else:
                cp_loss = max(0, cp_after - cp_before)
        else:
            cp_loss = None

        classification, symbol, color_hex = classify_move(cp_loss)

        move_entry = {
            'san': san,
            'move_num': move_num,
            'color': color,
            'cp_loss': cp_loss,
            'classification': classification,
            'symbol': symbol,
            'color_hex': color_hex,
            'eval_before': cp_before,
            'eval_after': cp_after,
        }
        moves_data.append(move_entry)

        if color == 'white':
            white_classifications.append((classification, symbol, color_hex))
        else:
            black_classifications.append((classification, symbol, color_hex))
            move_num += 1

        # Reuse this eval as the next move's starting point
        cp_before = cp_after

    white_profile = build_style_profile(white_classifications, len(white_classifications))
    black_profile = build_style_profile(black_classifications, len(black_classifications))

    # NOTE: Elo is NOT updated here — it was already updated on /save.
    return jsonify({
        'moves': moves_data,
        'white': white_profile,
        'black': black_profile,
    })


def _eval_via_api(fen: str):
    """Evaluate a position using chess-api.com. Returns centipawns or None."""
    try:
        resp = requests.post('https://chess-api.com/v1', json={'fen': fen, 'depth': 8}, timeout=10)
        resp.raise_for_status()
        d = resp.json()
        if d.get('mate') is not None:
            return None
        cp = d.get('centipawns')
        return int(cp) if cp is not None else None
    except Exception:
        return None
    


@api_bp.route('/save', methods=['POST'])
@login_required
def save_game():
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

    # Update Elo rating
    try:
        current_user._last_game_color = player_color
        new_rating, change = update_player_rating(
            current_user, result, mode, bot_id=bot_name
        )
        rating_info = {'new_rating': new_rating, 'change': change}
    except Exception:
        rating_info = {}

    return jsonify({'status': 'saved', 'game_id': game.id, 'token': game.token, **rating_info})


@api_bp.route('/history', methods=['GET'])
@login_required
def game_history():
    games = Game.query.filter_by(user_id=current_user.id)\
                      .order_by(Game.played_at.desc())\
                      .limit(20).all()
    return jsonify([g.to_dict() for g in games])


@api_bp.route('/bots', methods=['GET'])
def list_bots():
    from dialogue import BOTS_MANIFEST
    return jsonify(BOTS_MANIFEST)


@api_bp.route('/bot_dialogue/<bot_id>', methods=['GET'])
def bot_dialogue(bot_id):
    """Return the full dialogue JSON for a bot so the frontend can manage sequencing."""
    import json, os
    bots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bots')
    path = os.path.join(bots_dir, f'{bot_id}.json')
    if not os.path.exists(path):
        path = os.path.join(bots_dir, 'recruit.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    except Exception as e:
        return jsonify({'error': str(e)}), 500