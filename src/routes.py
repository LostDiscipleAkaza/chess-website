from flask import Blueprint, render_template, request, abort
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


@game_bp.route('/play/<token>')
def play(token):
    from play_sessions import _play_tokens
    params = _play_tokens.get(token)
    if not params:
        abort(404)
    return render_template('play.html',
                           mode=params['mode'],
                           bot=params['bot'],
                           color=params['color'])


@game_bp.route('/play')
def play_passandplay():
    return render_template('play.html', mode='pass_and_play', bot='', color='white')


@game_bp.route('/history')
@login_required
def history():
    page = request.args.get('page', 1, type=int)
    games = Game.query.filter_by(user_id=current_user.id)\
                      .order_by(Game.played_at.desc())\
                      .paginate(page=page, per_page=10, error_out=False)
    return render_template('history.html', games=games)


@game_bp.route('/replay/<token>')
@login_required
def replay(token):
    game = Game.query.filter_by(token=token, user_id=current_user.id).first_or_404()
    return render_template('replay.html', game=game)