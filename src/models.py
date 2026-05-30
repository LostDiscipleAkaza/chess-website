from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    games = db.relationship('Game', backref='player', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'


class Game(db.Model):
    __tablename__ = 'games'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # nullable for guest games
    pgn = db.Column(db.Text, nullable=False)
    result = db.Column(db.String(10))          # '1-0', '0-1', '1/2-1/2'
    mode = db.Column(db.String(20))            # 'pass_and_play', 'bot'
    bot_name = db.Column(db.String(50))        # None if pass_and_play
    player_color = db.Column(db.String(10))    # 'white' or 'black'
    played_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'pgn': self.pgn,
            'result': self.result,
            'mode': self.mode,
            'bot_name': self.bot_name,
            'player_color': self.player_color,
            'played_at': self.played_at.isoformat(),
        }

    def __repr__(self):
        return f'<Game {self.id} | {self.mode} | {self.result}>'
