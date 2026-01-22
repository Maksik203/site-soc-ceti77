from datetime import date
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SubmitField,
    TextAreaField,
    DateField,
    SelectField,
    BooleanField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from flask_wtf.file import FileField, FileAllowed


def validate_age_12_plus(form, field):
    """Минимальный возраст регистрации — 12 лет."""
    if not field.data:
        raise ValidationError("Укажите дату рождения")
    today = date.today()
    age = today.year - field.data.year - (
        (today.month, today.day) < (field.data.month, field.data.day)
    )
    if age < 12:
        raise ValidationError("Регистрация доступна с 12 лет")


class RegisterForm(FlaskForm):
    last_name = StringField("Фамилия", validators=[DataRequired(), Length(max=120)])
    first_name = StringField("Имя", validators=[DataRequired(), Length(max=120)])
    middle_name = StringField("Отчество", validators=[Length(max=120)])
    phone = StringField("Телефон", validators=[DataRequired(), Length(max=20)])
    date_of_birth = DateField(
        "Дата рождения", validators=[DataRequired(), validate_age_12_plus]
    )
    password = PasswordField("Пароль", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField("Повторите пароль", validators=[EqualTo("password")])
    submit = SubmitField("Создать аккаунт")


class LoginForm(FlaskForm):
    phone = StringField("Телефон", validators=[DataRequired(), Length(max=20)])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember = BooleanField("Запомнить меня")
    submit = SubmitField("Войти")


class ProfileForm(FlaskForm):
    bio = TextAreaField("О себе", validators=[Length(max=500)])
    city = StringField("Город", validators=[Length(max=120)])
    occupation = StringField("Род деятельности", validators=[Length(max=120)])
    interests = TextAreaField("Интересы", validators=[Length(max=500)])
    date_of_birth = DateField("Дата рождения", default=date(1990, 1, 1))
    avatar_upload = FileField(
        "Загрузить своё фото",
        validators=[FileAllowed(["jpg", "jpeg", "png", "gif"], "Только изображения.")],
    )
    privacy_level = SelectField(
        "Приватность профиля",
        choices=[("public", "Виден всем"), ("friends", "Только друзья"), ("private", "Только я")],
    )
    submit = SubmitField("Сохранить")


class PostForm(FlaskForm):
    body = TextAreaField("Что нового?", validators=[DataRequired(), Length(max=1000)])
    media_url = StringField("Ссылка на фото/видео (YouTube, VK и т.п.)")
    image = FileField(
        "Фото",
        validators=[FileAllowed(["jpg", "jpeg", "png", "gif"], "Только изображения.")],
    )
    video = FileField(
        "Видео до 3 минут",
        validators=[FileAllowed(["mp4", "webm", "ogg"], "Только видеофайлы.")],
    )
    media_type = SelectField(
        "Тип медиа",
        choices=[("none", "Без вложений"), ("image", "Фото"), ("video", "Видео"), ("link", "Ссылка на видео")],
    )
    visibility = SelectField(
        "Видимость",
        choices=[("public", "Все"), ("friends", "Друзья"), ("private", "Только я")],
    )
    submit = SubmitField("Опубликовать")


class CommentForm(FlaskForm):
    body = StringField("Комментарий", validators=[DataRequired(), Length(max=280)])
    submit = SubmitField("Отправить")


class MessageForm(FlaskForm):
    body = StringField("Сообщение", validators=[DataRequired(), Length(max=500)])
    submit = SubmitField("Отправить")


class GroupForm(FlaskForm):
    name = StringField("Название", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Описание", validators=[Length(max=500)])
    visibility = SelectField(
        "Видимость", choices=[("public", "Открытая"), ("friends", "Только участники"), ("private", "По приглашению")]
    )
    submit = SubmitField("Создать группу")

