from datetime import datetime
import os
import uuid

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

from app.extensions import db
from app.forms import ProfileForm
from app.models import User, Visibility

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/<int:user_id>")
@login_required
def view(user_id: int):
    user = User.query.get_or_404(user_id)
    can_view = user.privacy_level == Visibility.PUBLIC or user.id == current_user.id or user.is_friend(current_user)
    return render_template("profile/profile.html", user=user, can_view=can_view)


@profile_bp.route("/edit", methods=["GET", "POST"])
@login_required
def edit():
    form = ProfileForm(
        privacy_level=current_user.privacy_level.value if current_user.privacy_level else Visibility.PUBLIC.value
    )
    # список доступных готовых аватарок (стикеров) из static/uploads
    stickers = []
    upload_dir = os.path.join(current_app.static_folder, "uploads")
    if os.path.isdir(upload_dir):
        for name in sorted(os.listdir(upload_dir)):
            ext = os.path.splitext(name)[1].lower()
            if ext in {".jpg", ".jpeg", ".png", ".gif"}:
                stickers.append(url_for("static", filename=f"uploads/{name}"))

    if form.validate_on_submit():
        # выбор готовой аватарки
        chosen_avatar = request.form.get("avatar_choice") or None

        # загрузка своего файла
        upload = form.avatar_upload.data
        if upload and getattr(upload, "filename", ""):
            ext = os.path.splitext(upload.filename)[1].lower()
            if ext in {".jpg", ".jpeg", ".png", ".gif"}:
                new_name = f"avatar_{current_user.id}_{uuid.uuid4().hex}{ext}"
                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, new_name)
                upload.save(file_path)
                current_user.avatar_url = url_for("static", filename=f"uploads/{new_name}")
        elif chosen_avatar:
            # если файл не загружали, но выбрали готовый стикер
            current_user.avatar_url = chosen_avatar

        current_user.bio = form.bio.data
        current_user.city = form.city.data
        current_user.occupation = form.occupation.data
        current_user.interests = form.interests.data
        current_user.date_of_birth = form.date_of_birth.data
        current_user.privacy_level = Visibility(form.privacy_level.data)
        current_user.avatar_url = current_user.avatar_url or "/static/img/avatar-placeholder.svg"
        db.session.commit()
        flash("Профиль обновлен", "success")
        return redirect(url_for("profile.view", user_id=current_user.id))
    if request.method == "GET":
        form.bio.data = current_user.bio
        form.city.data = current_user.city
        form.occupation.data = current_user.occupation
        form.interests.data = current_user.interests
        form.date_of_birth.data = current_user.date_of_birth or datetime.utcnow().date()
        form.privacy_level.data = current_user.privacy_level.value if current_user.privacy_level else "public"
    return render_template("profile/edit.html", form=form, stickers=stickers)


@profile_bp.route("/follow/<int:user_id>", methods=["POST"])
@login_required
def follow(user_id: int):
    target = User.query.get_or_404(user_id)
    if target.id == current_user.id:
        return redirect(url_for("profile.view", user_id=user_id))
    current_user.follow(target)
    db.session.commit()
    flash(f"Вы подписались на {target.name}", "success")
    return redirect(url_for("profile.view", user_id=user_id))

