import os
import uuid

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.forms import PostForm, CommentForm
from app.models import Post, Comment, Like, Visibility, Notification, followers

main_bp = Blueprint("main", __name__)


def _save_image(file_storage):
    """Сохранение загруженного изображения и возврат относительного URL или None."""
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


def _save_video(file_storage):
    """Сохранение загруженного видео. В демо ограничиваемся форматом/размером, без точной проверки 3 минут."""
    if not file_storage or not file_storage.filename:
        return None
    filename = file_storage.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in {".mp4", ".webm", ".ogg"}:
        return None
    new_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join(current_app.root_path, "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, new_name)
    file_storage.save(file_path)
    return url_for("static", filename=f"uploads/{new_name}")


@main_bp.route("/")
def feed():
    if current_user.is_authenticated:
        # NOTE: `User.followers` is configured with lazy="dynamic", which cannot be used with `.any()`
        # in a SQLAlchemy filter expression. Use the association table instead.
        followed_user_ids = (
            db.session.query(followers.c.followed_id)
            .filter(followers.c.follower_id == current_user.id)
            .subquery()
        )
        # В общей ленте показываем только исходные посты (без репостов),
        # а сами репосты живут в разделе «Мои репосты».
        posts = (
            Post.query.filter(Post.original_post_id.is_(None))
            .filter(
                (Post.visibility == Visibility.PUBLIC)
                | (Post.user_id == current_user.id)
                | (Post.user_id.in_(followed_user_ids))
            )
            .order_by(Post.created_at.desc())
            .limit(50)
            .all()
        )
        post_form = PostForm()
        comment_form = CommentForm()
    else:
        posts = (
            Post.query.filter(Post.original_post_id.is_(None), Post.visibility == Visibility.PUBLIC)
            .order_by(Post.created_at.desc())
            .limit(50)
            .all()
        )
        post_form = None
        comment_form = CommentForm()
    return render_template("main/feed.html", posts=posts, post_form=post_form, comment_form=comment_form)


@main_bp.route("/my-reposts")
@login_required
def my_reposts():
    posts = (
        Post.query.filter_by(user_id=current_user.id)
        .filter(Post.original_post_id.isnot(None))
        .order_by(Post.created_at.desc())
        .all()
    )
    # в этом окне новая форма поста не нужна
    comment_form = CommentForm()
    return render_template("main/my_reposts.html", posts=posts, comment_form=comment_form)


@main_bp.route("/post", methods=["POST"])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        image_url = None
        video_url = None
        if form.image.data:
            image_url = _save_image(form.image.data)
        # если выбран тип "video" и загружен файл, сохраняем видео
        if hasattr(form, "video") and form.video.data:
            video_url = _save_video(form.video.data)
        post = Post(
            user_id=current_user.id,
            body=form.body.data,
            media_url=video_url
            or image_url
            or (form.media_url.data if form.media_type.data != "none" else None),
            media_type=(
                "video"
                if video_url
                else ("image" if image_url else (None if form.media_type.data == "none" else form.media_type.data))
            ),
            visibility=Visibility(form.visibility.data),
        )
        db.session.add(post)
        db.session.commit()
        flash("Пост опубликован", "success")
    else:
        flash("Не удалось опубликовать пост", "danger")
    return redirect(url_for("main.feed"))


@main_bp.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def comment(post_id: int):
    form = CommentForm()
    post = Post.query.get_or_404(post_id)
    if form.validate_on_submit():
        comment = Comment(post_id=post.id, user_id=current_user.id, body=form.body.data)
        db.session.add(comment)
        if post.author.id != current_user.id:
            db.session.add(
                Notification(
                    user_id=post.author.id,
                    kind="comment",
                    payload={"from": current_user.name, "post_id": post.id, "text": comment.body},
                )
            )
        db.session.commit()
        flash("Комментарий добавлен", "success")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify(
                {
                    "ok": True,
                    "author": comment.author.name,
                    "time": comment.created_at.strftime("%H:%M"),
                    "body": comment.body,
                }
            )
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": False}), 400
    return redirect(url_for("main.feed"))


@main_bp.route("/post/<int:post_id>/like", methods=["POST"])
@login_required
def like(post_id: int):
    post = Post.query.get_or_404(post_id)
    already = Like.query.filter_by(post_id=post.id, user_id=current_user.id).first()
    if already:
        db.session.delete(already)
        flash("Лайк убран", "info")
        liked = False
    else:
        like = Like(post_id=post.id, user_id=current_user.id)
        db.session.add(like)
        if post.author.id != current_user.id:
            db.session.add(
                Notification(
                    user_id=post.author.id,
                    kind="like",
                    payload={"from": current_user.name, "post_id": post.id},
                )
            )
        liked = True
        flash("Понравилось!", "success")
    db.session.commit()
    likes_count = Like.query.filter_by(post_id=post.id).count()
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"liked": liked, "likes_count": likes_count})
    return redirect(url_for("main.feed"))


@main_bp.route("/post/<int:post_id>/repost", methods=["POST"])
@login_required
def repost(post_id: int):
    clicked = Post.query.get_or_404(post_id)
    # Если нажали "репост" на репосте — работаем с исходным постом,
    # чтобы не плодить цепочки репостов/дубликаты.
    original = clicked.original_post or clicked
    # Тоггл-поведение: первый клик создаёт репост, повторный клик удаляет его
    existing_repost = Post.query.filter_by(
        user_id=current_user.id, original_post_id=original.id
    ).first()
    if existing_repost:
        db.session.delete(existing_repost)
        db.session.commit()
        flash("Репост убран из вашей ленты", "info")
        action = "removed"
    else:
        repost = Post(
            user_id=current_user.id,
            body=f"Репост: {original.body[:200]}",
            media_url=original.media_url,
            media_type=original.media_type,
            visibility=Visibility.PUBLIC,
            original_post=original,
        )
        db.session.add(repost)
        if original.author.id != current_user.id:
            db.session.add(
                Notification(
                    user_id=original.author.id,
                    kind="repost",
                    payload={"from": current_user.name, "post_id": original.id},
                )
            )
        db.session.commit()
        flash("Репост добавлен в вашу ленту", "success")
        action = "added"
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"action": action})
    return redirect(url_for("main.feed"))

