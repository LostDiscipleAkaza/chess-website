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
    'rookie_riley': {
        'depth': 1,
        'maxThinkingTime': 10,
        'error_chance': 0.4,   # 40% random move = ~400 Elo feel
    },
    'balanced_bob': {
        'depth': 8,
        'maxThinkingTime': 50,
        'error_chance': 0.0,
    },
    'aggressive_alex': {
        'depth': 12,
        'maxThinkingTime': 80,
        'error_chance': 0.0,
    },
    'grandmaster_grace': {
        'depth': 18,
        'maxThinkingTime': 100,
        'error_chance': 0.0,
    },
}

DEFAULT_PROFILE = BOT_PROFILES['balanced_bob']


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

    # Promotion
    for move in prev_board.legal_moves:
        if move.promotion:
            pushed = chess.Board(prev_fen)
            pushed.push(move)
            if pushed.fen() == current_fen:
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