"""
dialogue.py
Loads per-bot JSON personality files and serves random event-triggered lines.
"""

import json
import random
import os

BOTS_DIR = os.path.join(os.path.dirname(__file__), 'bots')

# Public manifest returned by /api/bots
BOTS_MANIFEST = [
    {
        'id': 'rookie_riley',
        'name': 'Rookie',
        'elo': 400,
        'description': 'Just learning the game.',
        'avatar': 'R',
    },
    {
        'id': 'balanced_bob',
        'name': 'Balanced',
        'elo': 1200,
        'description': 'Solid and Hard to trick.',
        'avatar': 'B',
    },
    {
        'id': 'aggressive_alex',
        'name': 'Aggressive',
        'elo': 1800,
        'description': 'Attacks at every opportunity. Hates draws.',
        'avatar': 'A',
    },
    {
        'id': 'grandmaster_grace',
        'name': 'Master',
        'elo': 2400,
        'description': 'Ice-cold. Sees everything.',
        'avatar': 'M',
    },
]

# Cache loaded JSON in memory
_cache: dict[str, dict] = {}


def _load_bot(bot_id: str) -> dict:
    if bot_id in _cache:
        return _cache[bot_id]

    path = os.path.join(BOTS_DIR, f'{bot_id}.json')
    if not os.path.exists(path):
        # Fall back to a generic file
        path = os.path.join(BOTS_DIR, 'balanced_bob.json')

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    _cache[bot_id] = data
    return data


def get_dialogue_line(bot_id: str, event: str) -> str:
    """
    Return a random dialogue line for a bot + event combination.
    Falls back to 'default' if the event key is missing.
    """
    try:
        data = _load_bot(bot_id)
    except FileNotFoundError:
        return ''

    lines = data.get(event) or data.get('default') or ['...']
    return random.choice(lines)
