"""
engine.py
Uses chess-api.com (free Stockfish 18) instead of a local binary.
"""

import chess
import requests
import random

API_URL = "https://chess-api.com/v1"
BLUNDER_THRESHOLD = 200

BOT_PROFILES = {
    'recruit': {
    'depth': 1,
    'maxThinkingTime': 50,
    'error_chance': 0.50,
},

'guard': {
    'depth': 2,
    'maxThinkingTime': 80,
    'error_chance': 0.35,
},

'scout': {
    'depth': 4,
    'maxThinkingTime': 120,
    'error_chance': 0.20,
},

'squad_leader': {
    'depth': 6,
    'maxThinkingTime': 200,
    'error_chance': 0.10,
},

'field_captain': {
    'depth': 8,
    'maxThinkingTime': 350,
    'error_chance': 0.05,
},

'royal_knight': {
    'depth': 12,
    'maxThinkingTime': 800,
    'error_chance': 0.01,
},

'grand_marshal': {
    'depth': 16,
    'maxThinkingTime': 1500,
    'error_chance': 0.005,
},

'monarch': {
    'depth': 20,
    'maxThinkingTime': 2500,
    'error_chance': 0.002,
},

'sovereign': {
    'depth': 24,
    'maxThinkingTime': 4000,
    'error_chance': 0.0,
}
}

DEFAULT_PROFILE = BOT_PROFILES['recruit']


def _get_profile(bot_id: str) -> dict:
    return BOT_PROFILES.get(bot_id, DEFAULT_PROFILE)


def get_bot_move(fen: str, bot_id: str) -> tuple[str, str]:
    profile = _get_profile(bot_id)
    board = chess.Board(fen)

    # Simulate weak play for Riley
    if profile['error_chance'] > 0 and random.random() < profile['error_chance']:
        move = random.choice(list(board.legal_moves))
        board.push(move)
        return move.uci(), board.fen()

    payload = {
        "fen": fen,
        "depth": profile["depth"],
        "maxThinkingTime": profile["maxThinkingTime"],
    }

    try:
        resp = requests.post(API_URL, json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        uci_move = data["move"]
        board.push_uci(uci_move)
        return uci_move, board.fen()
    except Exception as e:
        # Fallback: random legal move so the game never freezes
        move = random.choice(list(board.legal_moves))
        board.push(move)
        return move.uci(), board.fen()


def _evaluate(fen: str) -> int | None:
    try:
        board = chess.Board(fen)
        if board.is_game_over():
            return None

        resp = requests.post(API_URL, json={"fen": fen, "depth": 12}, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if data.get("mate") is not None:
            return None
        cp = data.get("centipawns")
        return int(cp) if cp is not None else None
    except Exception:
        return None


def detect_event(prev_fen: str | None, current_fen: str, bot_id: str) -> str:
    if prev_fen is None:
        return 'greeting'

    try:
        prev_board = chess.Board(prev_fen)
        curr_board = chess.Board(current_fen)
    except ValueError:
        return 'default'

    # Promotion — fires only when the side that JUST MOVED (prev_board.turn)
    # is the one whose pawn promoted. prev_board.turn is the bot's color here
    # since this function is now called with (fen_before_bot_move, fen_after).
    def _piece_set(board):
        return {(sq, str(board.piece_at(sq))) for sq in chess.SQUARES if board.piece_at(sq)}

    mover_color = prev_board.turn  # True = white just moved, False = black just moved

    prev_pieces = _piece_set(prev_board)
    curr_pieces = _piece_set(curr_board)
    appeared = curr_pieces - prev_pieces
    for sq, piece_str in appeared:
        rank = chess.square_rank(sq)
        if not piece_str:
            continue
        pchar = piece_str.upper()
        piece_color = chess.WHITE if piece_str.isupper() else chess.BLACK
        if rank in (0, 7) and pchar in ('Q', 'R', 'B', 'N') and piece_color == mover_color:
            # A non-pawn appeared on a back rank, placed by the side that moved
            return 'promotion'

    # Check
    if curr_board.is_check():
        return 'check'

    # Blunder
    prev_score = _evaluate(prev_fen)
    curr_score = _evaluate(current_fen)
    if prev_score is not None and curr_score is not None:
        score_change = curr_score - prev_score
        if prev_board.turn == chess.WHITE:
            if score_change < -BLUNDER_THRESHOLD:
                return 'blunder'
        else:
            if score_change > BLUNDER_THRESHOLD:
                return 'blunder'

    # Capture
    prev_count = sum(1 for sq in chess.SQUARES if prev_board.piece_at(sq))
    curr_count = sum(1 for sq in chess.SQUARES if curr_board.piece_at(sq))
    if curr_count < prev_count:
        return 'capture'

    return 'default'
