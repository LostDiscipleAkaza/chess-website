from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from extensions import db
from models import Game

game_bp = Blueprint('game', __name__)

@game_bp.route('/')
def home():
    return render_template('login.html')

@game_bp.route('/dashboard')
@login_required
def dashboard():
    games = Game.query.filter_by(user_id=current_user.id)\
                      .order_by(Game.played_at.desc())\
                      .limit(5).all()
    return render_template('dashboard.html', games=games)

@game_bp.route('/play')
def play():
    mode = request.args.get('mode', 'pass_and_play')
    bot = request.args.get('bot', '')
    color = request.args.get('color', 'white')
    return render_template('play.html', mode=mode, bot=bot, color=color)

@game_bp.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    games = Game.query.filter_by(user_id=current_user.id)\
                    .order_by(Game.played_at.desc())\
                    .paginate(page=page, per_page=10, error_out=False)
    return render_template('history.html', games=games)

@game_bp.route('/replay/<int:game_id>')
@login_required
def replay(game_id):
    game = Game.query.filter_by(id=game_id, user_id=current_user.id).first_or_404()
    return render_template('replay.html', game=game)