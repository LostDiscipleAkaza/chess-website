from flask import Flask
from extensions import db, login_manager
import os



def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-secret-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chess.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    import models
    from auth import auth_bp
    from routes import game_bp
    from api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(game_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    with app.app_context():
        db.create_all()

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
