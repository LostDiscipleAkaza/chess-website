"""
engine.py
Wraps python-chess + Stockfish to:
  - calculate the bot's best move given a FEN and bot profile
  - detect game events (blunder, check, capture, etc.) by comparing centipawn scores
"""

import chess
import chess.engine
import os

# Path to the Stockfish binary.
# Override via STOCKFISH_PATH environment variable or install system-wide.
STOCKFISH_PATH = os.environ.get('STOCKFISH_PATH', 'stockfish')

# Centipawn drop threshold to classify a player move as a blunder
BLUNDER_THRESHOLD = 200   # centipawns


# Bot profiles: each maps a bot_id to Stockfish UCI options + think time
BOT_PROFILES = {
    'rookie_riley': {
        'skill_level': 1,       # Stockfish Skill Level (0-20)
        'depth': 1,
        'time_limit': 0.05,
    },
    'balanced_bob': {
        'skill_level': 10,
        'depth': 8,
        'time_limit': 0.1,
    },
    'aggressive_alex': {
        'skill_level': 15,
        'depth': 12,
        'time_limit': 0.2,
    },
    'grandmaster_grace': {
        'skill_level': 20,
        'depth': 20,
        'time_limit': 0.5,
    },
}

DEFAULT_PROFILE = BOT_PROFILES['balanced_bob']


def _get_profile(bot_id: str) -> dict:
    return BOT_PROFILES.get(bot_id, DEFAULT_PROFILE)


def get_bot_move(fen: str, bot_id: str) -> tuple[str, str]:
    """
    Ask Stockfish for the best move for the current position.

    Returns:
        (uci_move, new_fen) — the move in UCI notation and the resulting FEN.
    """
    profile = _get_profile(bot_id)
    board = chess.Board(fen)

    with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
        engine.configure({'Skill Level': profile['skill_level']})
        result = engine.play(
            board,
            chess.engine.Limit(time=profile['time_limit'], depth=profile['depth']),
        )

    move = result.move
    board.push(move)
    return move.uci(), board.fen()


def _evaluate(fen: str) -> int | None:
    """
    Return centipawn score from white's perspective for the given FEN.
    Returns None if Stockfish is unavailable or position is terminal.
    """
    try:
        board = chess.Board(fen)
        if board.is_game_over():
            return None

        with chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH) as engine:
            info = engine.analyse(board, chess.engine.Limit(depth=12))
            score = info['score'].white()
            if score.is_mate():
                return None
            return score.score()
    except Exception:
        return None


def detect_event(prev_fen: str | None, current_fen: str, bot_id: str) -> str:
    """
    Compare board states before/after the player's move to classify an event.

    Event keys (match the keys in bot JSON files):
        'greeting'      — very first move of the game
        'blunder'       — player dropped ≥ BLUNDER_THRESHOLD centipawns
        'check'         — player put the bot in check
        'capture'       — player captured a bot piece
        'promotion'     — player promoted a pawn
        'default'       — nothing special happened
    """
    if prev_fen is None:
        return 'greeting'

    try:
        prev_board = chess.Board(prev_fen)
        curr_board = chess.Board(current_fen)
    except ValueError:
        return 'default'

    # Detect promotion: a pawn reached the back rank
    for move in prev_board.legal_moves:
        if move.promotion:
            pushed = chess.Board(prev_fen)
            pushed.push(move)
            if pushed.fen() == current_fen:
                return 'promotion'

    # Detect capture: a piece disappeared from the board
    prev_piece_count = sum(1 for sq in chess.SQUARES if prev_board.piece_at(sq))
    curr_piece_count = sum(1 for sq in chess.SQUARES if curr_board.piece_at(sq))
    if curr_piece_count < prev_piece_count:
        # also check if it was a blunder alongside the capture
        pass  # fall through to blunder check below; capture wins if no blunder

    # Detect check
    if curr_board.is_check():
        return 'check'

    # Detect blunder via centipawn evaluation
    prev_score = _evaluate(prev_fen)
    curr_score = _evaluate(current_fen)

    if prev_score is not None and curr_score is not None:
        # Score is from white's perspective; figure out who the player is
        # The side that just moved is the one whose turn it was in prev_fen
        prev_board_turn = prev_board.turn   # chess.WHITE or chess.BLACK
        score_change = curr_score - prev_score
        # If white just moved, a positive score_change is good for white (player didn't blunder)
        # A negative change means white lost material (blunder)
        if prev_board_turn == chess.WHITE:
            if score_change < -BLUNDER_THRESHOLD:
                return 'blunder'
        else:
            if score_change > BLUNDER_THRESHOLD:
                return 'blunder'

    if curr_piece_count < prev_piece_count:
        return 'capture'

    return 'default'
