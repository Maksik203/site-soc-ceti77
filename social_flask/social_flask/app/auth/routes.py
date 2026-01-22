from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required

from app.extensions import db, mail
from app.forms import RegisterForm, LoginForm
from app.models import User
from flask_mail import Message

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        # Используем телефон как основной идентификатор, email генерируем технически
        normalized_phone = form.phone.data.strip()
        if User.query.filter_by(phone=normalized_phone).first():
            flash("Пользователь с таким телефоном уже существует", "danger")
            return redirect(url_for("auth.register"))

        generated_email = f"{normalized_phone}@local"
        full_name = " ".join(
            filter(
                None,
                [form.last_name.data.strip(), form.first_name.data.strip(), (form.middle_name.data or "").strip()],
            )
        )

        user = User(
            email=generated_email.lower(),
            phone=normalized_phone,
            name=full_name,
            date_of_birth=form.date_of_birth.data,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        token = _get_serializer().dumps(user.email)
        verify_link = url_for("auth.verify_email", token=token, _external=True)

        try:
            msg = Message("Подтверждение аккаунта", recipients=[user.email])
            msg.body = f"Перейдите по ссылке, чтобы подтвердить аккаунт: {verify_link}"
            mail.send(msg)
            flash("Письмо с подтверждением отправлено на email", "info")
        except Exception:
            flash("Не удалось отправить письмо, попробуйте позже или проверьте настройки почты", "warning")

        flash("Аккаунт создан! Подтвердите email для полного доступа.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/verify/<token>")
def verify_email(token: str):
    serializer = _get_serializer()
    try:
        email = serializer.loads(token, max_age=60 * 60 * 24)
    except SignatureExpired:
        flash("Ссылка истекла, запросите новую.", "warning")
        return redirect(url_for("auth.register"))
    except BadSignature:
        flash("Неверный токен подтверждения.", "danger")
        return redirect(url_for("auth.register"))

    user = User.query.filter_by(email=email).first_or_404()
    user.is_verified = True
    db.session.commit()
    flash("Email успешно подтвержден!", "success")
    return redirect(url_for("main.feed"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(phone=form.phone.data.strip()).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash("Добро пожаловать!", "success")
            next_url = request.args.get("next") or url_for("main.feed")
            return redirect(next_url)
        flash("Неверный email или пароль", "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login/<provider>")
def social_login(provider: str):
    flash(f"OAuth вход через {provider} еще не настроен. Добавьте ключи в config.py.", "warning")
    return redirect(url_for("auth.login"))

