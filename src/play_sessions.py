# play_sessions.py
# Single shared store for play session tokens: token -> {mode, bot, color}
# Both api.py and routes.py import from here to use the same dict object.
_play_tokens: dict = {}
