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
import chess.engine
import chess.pgn
import io
import os

api_bp = Blueprint('api', __name__)

STOCKFISH_PATH = os.environ.get(
    'STOCKFISH_PATH',
    r'C:\Users\bhuvaneshwar\OneDrive\Desktop\chess website\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe'  # update this to your full path if needed
)


@api_bp.route('/move', methods=['POST'])
def bot_move():
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

    event = detect_event(prev_fen, fen, bot_id)

    try:
        bot_uci, new_fen = get_bot_move(fen, bot_id)
    except Exception as e:
        return jsonify({'error': f'Engine failed: {str(e)}'}), 500

    line = get_dialogue_line(bot_id, event)

    return jsonify({
        'move': bot_uci,
        'fen_after': new_fen,
        'dialogue': line,
        'event': event,
    })


@api_bp.route('/review', methods=['POST'])
def review_game():
    """
    Analyse a completed game PGN with Stockfish.
    Returns per-move classifications and accuracy scores.

    Request JSON:
        { "pgn": "<PGN string>", "player_color": "white" }

    Response JSON:
        {
          "moves": [
            {
              "san": "e4", "move_num": 1, "color": "white",
              "cp_loss": 0, "classification": "best",
              "symbol": "★", "color_hex": "#1bada6",
              "eval_before": 30, "eval_after": 30
            }, ...
          ],
          "white": { "accuracy": 94.2, "best": 12, "blunder": 0, ... },
          "black": { "accuracy": 88.1, "best": 8, "blunder": 2, ... }
        }
    """
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

    try:
        with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
            board = game.board()
            move_num = 1

            for move in game.mainline_moves():
                color = 'white' if board.turn == chess.WHITE else 'black'

                # Evaluate before move
                info_before = engine.analyse(board, chess.engine.Limit(depth=14))
                score_before = info_before['score'].white()
                cp_before = score_before.score(mate_score=10000)

                # Make move
                san = board.san(move)
                board.push(move)

                # Evaluate after move
                info_after = engine.analyse(board, chess.engine.Limit(depth=14))
                score_after = info_after['score'].white()
                cp_after = score_after.score(mate_score=10000)

                # Calculate centipawn loss from perspective of the player who moved
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

                if color == 'black':
                    move_num += 1

    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

    white_profile = build_style_profile(white_classifications, len(white_classifications))
    black_profile = build_style_profile(black_classifications, len(black_classifications))

    # Update Elo based on analysis results
    rating_info = {}
    if current_user.is_authenticated:
        try:
            player_color = data.get('player_color', 'white')
            result       = data.get('result', '*')
            bot_id       = data.get('bot_id', '')
            mode         = data.get('mode', 'bot')

            # Get player's accuracy from the review
            acc_data = white_profile if player_color == 'white' else black_profile
            accuracy = acc_data.get('accuracy')

            new_rating, change = update_player_rating(
                current_user, result, mode,
                bot_id=bot_id,
                player_color=player_color,
                accuracy=accuracy
            )
            rating_info = {'new_rating': new_rating, 'change': change}
        except Exception:
            pass
    return jsonify({
        'moves': moves_data,
        'white': white_profile,
        'black': black_profile,
        **rating_info,
    })


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

    return jsonify({'status': 'saved', 'game_id': game.id, **rating_info})


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