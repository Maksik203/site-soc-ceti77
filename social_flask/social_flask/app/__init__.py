import os

from flask import Flask, request, url_for
from flask_login import current_user

from config import config_by_name
from .extensions import db, login_manager, mail
from .models import Notification


def create_app(config_name: str = "dev") -> Flask:
    app = Flask(__name__, instance_relative_config=False, static_folder="static", template_folder="templates")
    app.config.from_object(config_by_name.get(config_name, config_by_name["dev"]))

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    login_manager.login_view = "auth.login"

    register_blueprints(app)
    register_template_globals(app)

    with app.app_context():
        db.create_all()

    return app


def register_blueprints(app: Flask) -> None:
    from .auth.routes import auth_bp
    from .main.routes import main_bp
    from .profile.routes import profile_bp
    from .messages.routes import messages_bp
    from .groups.routes import groups_bp
    from .notifications.routes import notifications_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(notifications_bp)


def register_template_globals(app: Flask) -> None:
    @app.context_processor
    def inject_notifications():
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        return dict(unread_notifications=unread_count)

    @app.context_processor
    def inject_breadcrumbs():
        # Простая и понятная подсказка "где вы находитесь"
        endpoint = request.endpoint or ""
        page_name_by_endpoint = {
            "main.feed": "Лента",
            "main.my_reposts": "Мои репосты",
            "messages.inbox": "Сообщения",
            "groups.list_groups": "Группы",
            "notifications.list_notifications": "Уведомления",
            "auth.login": "Вход",
            "auth.register": "Регистрация",
        }
        current_page_name = page_name_by_endpoint.get(endpoint, "Страница")
        # 1-й элемент всегда "Главная/Лента"
        crumbs = [
            {"name": "Лента", "url": url_for("main.feed")},
            {"name": current_page_name, "url": None},
        ]
        return dict(current_page_name=current_page_name, current_endpoint=endpoint, breadcrumbs=crumbs)


def ensure_dirs():
    os.makedirs(os.path.join(os.path.dirname(__file__), "static", "uploads"), exist_ok=True)

