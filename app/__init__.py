from flask import Flask

from app.config import Config
from app.db import close_db, init_db
from app.routes import bp


def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config.from_object(config_class)
    app.json.ensure_ascii = False
    app.register_blueprint(bp)
    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()

    return app
