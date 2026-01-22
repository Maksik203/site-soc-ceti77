from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user

from app.extensions import db
from app.forms import MessageForm
from app.models import Chat, ChatMembership, Message, User

messages_bp = Blueprint("messages", __name__, url_prefix="/messages")


def _ensure_private_chat(user_a: int, user_b: int) -> Chat:
    existing = (
        Chat.query.filter_by(is_group=False)
        .join(ChatMembership)
        .filter(ChatMembership.user_id == user_a)
        .all()
    )
    for chat in existing:
        member_ids = {m.user_id for m in chat.memberships}
        if user_b in member_ids:
            return chat
    chat = Chat(is_group=False)
    db.session.add(chat)
    db.session.flush()
    db.session.add(ChatMembership(chat_id=chat.id, user_id=user_a))
    db.session.add(ChatMembership(chat_id=chat.id, user_id=user_b))
    db.session.commit()
    return chat


@messages_bp.route("/")
@login_required
def inbox():
    chats = (
        Chat.query.join(ChatMembership).filter(ChatMembership.user_id == current_user.id).order_by(Chat.created_at.desc())
    )
    return render_template("messages/inbox.html", chats=chats)


@messages_bp.route("/with/<int:user_id>", methods=["GET", "POST"])
@login_required
def direct(user_id: int):
    target = User.query.get_or_404(user_id)
    chat = _ensure_private_chat(current_user.id, target.id)
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(chat_id=chat.id, sender_id=current_user.id, body=form.body.data)
        db.session.add(msg)
        db.session.commit()
        flash("Сообщение отправлено", "success")
        return redirect(url_for("messages.direct", user_id=user_id))
    messages = Message.query.filter_by(chat_id=chat.id).order_by(Message.created_at.asc()).all()
    return render_template("messages/direct.html", form=form, messages=messages, target=target)

