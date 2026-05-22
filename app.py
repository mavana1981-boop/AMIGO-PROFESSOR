import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-prod")
    # Railway fornece DATABASE_URL como postgres:// mas SQLAlchemy exige postgresql://
    db_url = os.environ.get("DATABASE_URL",
                            f"sqlite:///{os.path.join(app.instance_path, 'amigo_professor.db')}")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Faça login para acessar esta página."
    login_manager.login_message_category = "info"

    # ── Jinja2 globals ────────────────────────────────────────────────────────
    app.jinja_env.globals.update(enumerate=enumerate, zip=zip, len=len)

    # ── Blueprints ────────────────────────────────────────────────────────────
    from routes.auth        import auth_bp
    from routes.main        import main_bp
    from routes.frequencia  import freq_bp
    from routes.planejamento import plan_bp
    from routes.avaliacoes  import aval_bp
    from routes.pedagogico  import ped_bp
    from routes.calendario  import cal_bp
    from routes.turmas      import turmas_bp
    from routes.rav         import rav_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(freq_bp)
    app.register_blueprint(plan_bp)
    app.register_blueprint(aval_bp)
    app.register_blueprint(ped_bp)
    app.register_blueprint(cal_bp)
    app.register_blueprint(turmas_bp)
    app.register_blueprint(rav_bp)

    with app.app_context():
        db.create_all()

    return app
