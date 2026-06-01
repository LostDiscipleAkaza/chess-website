from extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    rating        = db.Column(db.Integer, default=1200)   # NEW — Elo rating
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)

    games = db.relationship('Game', backref='player', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username} ({self.rating})>'


class Game(db.Model):
    __tablename__ = 'games'

    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    pgn          = db.Column(db.Text, nullable=False)
    result       = db.Column(db.String(10))
    mode         = db.Column(db.String(20))
    bot_name     = db.Column(db.String(50))
    player_color = db.Column(db.String(10))
    # NEW — store accuracy after review
    white_accuracy = db.Column(db.Float, nullable=True)
    black_accuracy = db.Column(db.Float, nullable=True)
    played_at    = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id':             self.id,
            'pgn':            self.pgn,
            'result':         self.result,
            'mode':           self.mode,
            'bot_name':       self.bot_name,
            'player_color':   self.player_color,
            'white_accuracy': self.white_accuracy,
            'black_accuracy': self.black_accuracy,
            'played_at':      self.played_at.isoformat(),
        }

    def __repr__(self):
        return f'<Game {self.id} | {self.mode} | {self.result}>'