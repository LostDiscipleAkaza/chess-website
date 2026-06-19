"""
dialogue.py
Loads per-bot JSON personality files and serves dialogue lines in order.
Each (bot_id, event) pair cycles through its lines sequentially.
"""

import json
import os

BOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bots')

# Public manifest returned by /api/bots
BOTS_MANIFEST = [
    {
    'id': 'recruit',
    'name': 'Recruit',
    'elo': 400,
    'description': 'Ambitious soldier chasing impossible dreams.',
},

{
    'id': 'guard',
    'name': 'Guard',
    'elo': 700,
    'description': 'Loyal protector of kingdom gates.',
},

{
    'id': 'scout',
    'name': 'Scout',
    'elo': 1000,
    'description': 'Wisdom across squares.',
},

{
    'id': 'squad_leader',
    'name': 'Squad Leader',
    'elo': 1300,
    'description': 'Responsible leader.',
},

{
    'id': 'field_captain',
    'name': 'Field Captain',
    'elo': 1700,
    'description': 'Veteran commander.',
},

{
    'id': 'royal_knight',
    'name': 'Royal Knight',
    'elo': 2100,
    'description': 'Hero of the kingdom.',
},

{
    'id': 'grand_marshal',
    'name': 'Grand Marshal',
    'elo': 2500,
    'description': 'Supreme strategist.',
},

{
    'id': 'monarch',
    'name': 'Monarch',
    'elo': 2800,
    'description': 'Burdened King.',
},

{
    'id': 'sovereign',
    'name': 'Sovereign',
    'elo': 3100,
    'description': 'The Creator.',
}

]

# Cache loaded JSON in memory
_cache: dict[str, dict] = {}

# Tracks next line index per (bot_id, event) pair
_indices: dict[tuple[str, str], int] = {}


def _load_bot(bot_id: str) -> dict:
    if bot_id in _cache:
        return _cache[bot_id]

    path = os.path.join(BOTS_DIR, f'{bot_id}.json')
    if not os.path.exists(path):
        path = os.path.join(BOTS_DIR, 'recruit.json')

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    _cache[bot_id] = data
    return data


def get_dialogue_line(bot_id: str, event: str) -> str:
    """
    Return the next dialogue line in sequence for a bot + event combination.
    Cycles back to the start after the last line.
    Falls back to 'default' if the event key is missing.
    """
    try:
        data = _load_bot(bot_id)
    except FileNotFoundError:
        return ''

    lines = data.get(event) or data.get('default') or ['...']

    key = (bot_id, event)
    idx = _indices.get(key, 0)
    line = lines[idx % len(lines)]
    _indices[key] = idx + 1

    return line