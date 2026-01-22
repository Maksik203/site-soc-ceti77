import os
import uuid

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request
from flask_login import login_required, current_user

from app.extensions import db
from app.forms import GroupForm, PostForm
from app.models import Group, GroupMember, GroupPost, Visibility

groups_bp = Blueprint("groups", __name__, url_prefix="/groups")


def _save_group_image(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    filename = file_storage.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".gif"}:
        return None
    new_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join(current_app.root_path, "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, new_name)
    file_storage.save(file_path)
    return url_for("static", filename=f"uploads/{new_name}")


@groups_bp.route("/", methods=["GET", "POST"])
@login_required
def list_groups():
    form = GroupForm()
    if form.validate_on_submit():
        group = Group(
            name=form.name.data,
            description=form.description.data,
            visibility=Visibility(form.visibility.data),
            owner_id=current_user.id,
        )
        db.session.add(group)
        db.session.flush()
        db.session.add(GroupMember(group_id=group.id, user_id=current_user.id, is_admin=True))
        db.session.commit()
        flash("Группа создана", "success")
        return redirect(url_for("groups.detail", group_id=group.id))
    groups = Group.query.order_by(Group.created_at.desc()).limit(50).all()
    return render_template("groups/list.html", form=form, groups=groups)


@groups_bp.route("/<int:group_id>", methods=["GET", "POST"])
@login_required
def detail(group_id: int):
    group = Group.query.get_or_404(group_id)
    members = GroupMember.query.filter_by(group_id=group.id).all()
    is_member = any(m.user_id == current_user.id for m in members)
    post_form = PostForm()
    if is_member and post_form.validate_on_submit():
        image_url = None
        if post_form.image.data:
            image_url = _save_group_image(post_form.image.data)
        post = GroupPost(
            group_id=group.id,
            author_id=current_user.id,
            body=post_form.body.data,
            media_url=image_url
            or (post_form.media_url.data if post_form.media_type.data != "none" else None),
            media_type="image"
            if image_url
            else (None if post_form.media_type.data == "none" else post_form.media_type.data),
        )
        db.session.add(post)
        db.session.commit()
        flash("Пост опубликован в группе", "success")
        return redirect(url_for("groups.detail", group_id=group.id))
    posts = GroupPost.query.filter_by(group_id=group.id).order_by(GroupPost.created_at.desc()).all()
    return render_template("groups/detail.html", group=group, posts=posts, post_form=post_form, members=members, is_member=is_member)


@groups_bp.route("/<int:group_id>/join", methods=["POST"])
@login_required
def join(group_id: int):
    group = Group.query.get_or_404(group_id)
    already = GroupMember.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    if not already:
        db.session.add(GroupMember(group_id=group.id, user_id=current_user.id))
        db.session.commit()
        flash("Вы вступили в группу", "success")
    return redirect(url_for("groups.detail", group_id=group.id))


@groups_bp.route("/<int:group_id>/leave", methods=["POST"])
@login_required
def leave(group_id: int):
    group = Group.query.get_or_404(group_id)
    membership = GroupMember.query.filter_by(group_id=group.id, user_id=current_user.id).first()
    # владельцу не даём выйти, чтобы группа не осталась без хозяина
    if membership and not membership.is_admin:
        db.session.delete(membership)
        db.session.commit()
        flash("Вы вышли из группы", "info")
    return redirect(url_for("groups.detail", group_id=group.id))

