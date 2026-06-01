"""
rating.py
Elo rating system + playing style analysis.
"""

from extensions import db

K_FACTOR = 32  # Standard K-factor for casual play


def expected_score(player_rating, opponent_rating):
    return 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))


def calculate_new_rating(player_rating, opponent_rating, score):
    """
    score: 1.0 = win, 0.5 = draw, 0.0 = loss
    Returns new integer rating.
    """
    expected = expected_score(player_rating, opponent_rating)
    new_rating = player_rating + K_FACTOR * (score - expected)
    return max(100, round(new_rating))


def get_bot_rating(bot_id):
    bot_ratings = {
        'rookie_riley':     400,
        'balanced_bob':     1200,
        'aggressive_alex':  1800,
        'grandmaster_grace': 2800,
    }
    return bot_ratings.get(bot_id, 1200)


def update_player_rating(user, result, mode, bot_id=None,
                          player_color='white', accuracy=None):
    """
    Update Elo after game. If accuracy provided, adjust K-factor:
    - High accuracy (>85%) → bigger reward for wins
    - Low accuracy (<50%) → smaller penalty for losses
    """
    from models import User

    if mode == 'bot' and bot_id:
        opp_rating = get_bot_rating(bot_id)
    else:
        opp_rating = 1200

    if result == '1/2-1/2':
        score = 0.5
    elif (result == '1-0' and player_color == 'white') or \
         (result == '0-1' and player_color == 'black'):
        score = 1.0
    else:
        score = 0.0

    # Adjust K-factor based on accuracy if available
    k = K_FACTOR
    if accuracy is not None:
        if accuracy >= 85:
            k = K_FACTOR * 1.3   # played well, bigger rating swing
        elif accuracy < 50:
            k = K_FACTOR * 0.7   # played poorly, smaller swing

    current_rating = user.rating or 1200
    expected = expected_score(current_rating, opp_rating)
    new_rating = max(100, round(current_rating + k * (score - expected)))
    rating_change = new_rating - current_rating

    user.rating = new_rating
    db.session.commit()

    return new_rating, rating_change



def classify_move(cp_loss):
    """Classify a move based on centipawn loss."""
    if cp_loss is None:
        return 'book', '📘', '#8b8b8b'
    if cp_loss <= 0:
        return 'best', '★', '#1bada6'
    elif cp_loss <= 10:
        return 'excellent', '✓', '#96bc4b'
    elif cp_loss <= 25:
        return 'good', '●', '#96bc4b'
    elif cp_loss <= 50:
        return 'inaccuracy', '?!', '#f0c15f'
    elif cp_loss <= 100:
        return 'mistake', '?', '#e87b2e'
    else:
        return 'blunder', '??', '#ca3431'


def build_style_profile(move_classifications, total_moves):
    """Build a playing style profile from move classifications."""
    counts = {
        'best': 0, 'excellent': 0, 'good': 0,
        'inaccuracy': 0, 'mistake': 0, 'blunder': 0
    }
    for cls, _, _ in move_classifications:
        if cls in counts:
            counts[cls] += 1

    if total_moves == 0:
        return {}

    accuracy = round(
        100 * (counts['best'] * 1.0 + counts['excellent'] * 0.9 +
               counts['good'] * 0.75 + counts['inaccuracy'] * 0.5) / total_moves,
        1
    )

    return {
        'accuracy': accuracy,
        'best': counts['best'],
        'excellent': counts['excellent'],
        'good': counts['good'],
        'inaccuracy': counts['inaccuracy'],
        'mistake': counts['mistake'],
        'blunder': counts['blunder'],
    }