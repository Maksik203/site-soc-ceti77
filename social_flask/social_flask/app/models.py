from datetime import datetime
from enum import Enum
from typing import Optional

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from .extensions import db, login_manager


class Visibility(str, Enum):
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"


friendship = db.Table(
    "friendship",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("friend_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("created_at", db.DateTime, default=datetime.utcnow),
)


followers = db.Table(
    "followers",
    db.Column("follower_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("followed_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("created_at", db.DateTime, default=datetime.utcnow),
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.Text)
    avatar_url = db.Column(db.String(255))
    date_of_birth = db.Column(db.Date)
    city = db.Column(db.String(120))
    occupation = db.Column(db.String(120))
    interests = db.Column(db.Text)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    privacy_level = db.Column(db.Enum(Visibility), default=Visibility.PUBLIC)

    posts = db.relationship("Post", backref="author", lazy="dynamic")
    comments = db.relationship("Comment", backref="author", lazy="dynamic")
    messages = db.relationship("Message", backref="sender", lazy="dynamic")
    notifications = db.relationship("Notification", backref="user", lazy="dynamic")

    friends = db.relationship(
        "User",
        secondary=friendship,
        primaryjoin=id == friendship.c.user_id,
        secondaryjoin=id == friendship.c.friend_id,
        backref="friend_of",
        lazy="dynamic",
    )
    following = db.relationship(
        "User",
        secondary=followers,
        primaryjoin=id == followers.c.follower_id,
        secondaryjoin=id == followers.c.followed_id,
        backref="followers",
        lazy="dynamic",
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_friend(self, user: "User") -> bool:
        return (
            self.friends.filter(friendship.c.friend_id == user.id).count() > 0
            or self.friend_of.filter(friendship.c.user_id == user.id).count() > 0
        )

    def add_friend(self, user: "User") -> None:
        if not self.is_friend(user):
            self.friends.append(user)

    def follow(self, user: "User") -> None:
        if not self.is_following(user):
            self.following.append(user)

    def is_following(self, user: "User") -> bool:
        return self.following.filter(followers.c.followed_id == user.id).count() > 0

    def __repr__(self) -> str:
        return f"<User {self.email}>"


@login_manager.user_loader
def load_user(user_id: str) -> Optional[User]:
    return User.query.get(int(user_id))


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(255))
    media_type = db.Column(db.String(50))
    visibility = db.Column(db.Enum(Visibility), default=Visibility.PUBLIC)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    original_post_id = db.Column(db.Integer, db.ForeignKey("post.id"))
    original_post = db.relationship("Post", remote_side=[id])

    comments = db.relationship("Comment", backref="post", lazy="dynamic", cascade="all, delete")
    likes = db.relationship("Like", backref="post", lazy="dynamic", cascade="all, delete")


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    is_group = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"))

    memberships = db.relationship("ChatMembership", backref="chat", cascade="all, delete")
    messages = db.relationship("Message", backref="chat", cascade="all, delete")


class ChatMembership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.Integer, db.ForeignKey("chat.id"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    body = db.Column(db.Text)
    media_url = db.Column(db.String(255))
    media_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    visibility = db.Column(db.Enum(Visibility), default=Visibility.PUBLIC)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship("GroupMember", backref="group", cascade="all, delete")
    posts = db.relationship("GroupPost", backref="group", cascade="all, delete")


class GroupMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # связь с пользователем для удобного доступа к имени и аватарке в шаблонах
    user = db.relationship("User", backref="group_memberships")


class GroupPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey("group.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    body = db.Column(db.Text, nullable=False)
    media_url = db.Column(db.String(255))
    media_type = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship("User", backref="group_posts")


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    kind = db.Column(db.String(50))
    payload = db.Column(db.JSON)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

