from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Notification

notifications_bp = Blueprint("notifications", __name__, url_prefix="/notifications")


@notifications_bp.route("/")
@login_required
def list_notifications():
    notes = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template("notifications/list.html", notifications=notes)


@notifications_bp.route("/read/<int:note_id>", methods=["POST"])
@login_required
def mark_read(note_id: int):
    note = Notification.query.get_or_404(note_id)
    if note.user_id == current_user.id:
        note.is_read = True
        db.session.commit()
    return redirect(url_for("notifications.list_notifications"))

