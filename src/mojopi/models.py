import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

import peewee
from flask_login import UserMixin
from werkzeug.utils import secure_filename

from mojopi.utils import (
    DPATH,
    PIC_PATH,
    InvalidInputError,
    conf,
    generate_password,
    hash_password,
    is_email,
)

db_path = DPATH / "test.sqlite"
db = peewee.SqliteDatabase(db_path, check_same_thread=False)


class BaseModel(peewee.Model):
    class Meta:
        database = db


class User(BaseModel, UserMixin):
    username = peewee.CharField(
        max_length=80, unique=True
    )  # will raise IntegrityError when username duplicated
    email = peewee.CharField(max_length=120, unique=True)
    password = peewee.CharField(max_length=60, null=True)
    picture = peewee.CharField(max_length=120, null=True)
    add_at = peewee.DateTimeField(default=datetime.now)

    def __str__(self):
        return self.username

    def change_username(self, new_name):
        if not is_valid_username(new_name):
            raise InvalidInputError(f"Invalid username: {new_name}")
        self.username = new_name

        # change profile avatar filename and user.picture
        if self.picture:
            old_path = PIC_PATH / self.picture
            new_path = PIC_PATH / f"{self.username}{old_path.suffix}"
            os.rename(old_path, new_path)

            self.picture = f"{self.username}{old_path.suffix}"

        self.save()


class Profile(BaseModel):
    """1個 user 對應 1個 profile"""

    user = peewee.ForeignKeyField(User, unique=True)
    education = peewee.TextField(null=True)
    experience = peewee.TextField(null=True)
    bio = peewee.TextField(null=True)
    is_public = peewee.BooleanField(default=True)


class UserInfo(BaseModel):
    key = peewee.CharField(max_length=64)
    value = peewee.CharField(max_length=64)

    user = peewee.ForeignKeyField(User)

    def __str__(self):
        return f"{self.key} - {self.value}"


class Post(BaseModel):
    id = peewee.UUIDField(primary_key=True, default=uuid.uuid4)
    title = peewee.CharField(max_length=120)
    text = peewee.TextField(null=False)
    date = peewee.DateTimeField()

    user = peewee.ForeignKeyField(User)

    def __str__(self):
        return self.title


def init_db():
    try:
        User.create_table()
        UserInfo.create_table()
        Post.create_table()
        Profile.create_table()
    except Exception as e:
        logging.exception(e)
        print("Create table error. See log for more information.")
        # pass

    try:
        add_user(
            email="eric@simutech.com.tw", username="drunkwcodes", password="123456"
        )
    except InvalidInputError:
        pass

    mock_user = User.get_or_none(User.email == "eric@simutech.com.tw")
    mock_profile = Profile.get(Profile.user == mock_user)
    mock_profile.education = "建國中學"
    mock_profile.experience = "Simutech New Comer"
    mock_profile.bio = """I am an experienced Python engineer with 5 years of relevant work experience. I am deeply passionate about this profession, and I believe my expertise in Python and related technologies, along with my adaptability, make me the ideal candidate for your company.

In my previous roles, I have been responsible for designing and developing various complex Python applications. My expertise extends to, but is not limited to, Django, Flask, NumPy, Pandas, Selenium, and more.

I have excelled in problem-solving and optimizing code. I possess strong coding practices, adhere to software development life cycles and software engineering principles, and am proficient in using version control tools like Git for code management. I am also skilled in teamwork, boasting excellent communication abilities that enable me to collaborate effectively with designers and other technical professionals to solve intricate problems and create high-quality products.

I am a diligent and responsible individual, driven by a love for learning. I can quickly grasp new technologies and tools and apply them in practical scenarios. I firmly believe that my skills and experience can bring great value to your company."""
    mock_profile.save()


def add_user(email="", username="", password=""):
    """新增使用者，成功 return (User(), password), 失敗 raise InvalidInputError.

    Required field: email

    Raises: InvalidInputError
    """

    if not email:
        raise InvalidInputError("email can not be empty.")
    if not is_email(email):
        raise InvalidInputError("Wrong email format.")

    # Secure username for profile pic
    if username and secure_filename(username) != username:
        raise InvalidInputError("Malformed username. Should be secure_filename().")

    if not password:
        password = generate_password()
    hpw = hash_password(password)

    # https://stackoverflow.com/questions/49395393/return-max-value-in-a-column-with-peewee
    max_user_id = User.select(peewee.fn.MAX(User.id)).scalar()
    if not username:
        username = f"user{max_user_id + 1}"
    user = User(username=username, email=email, password=hpw)
    try:
        user.save()
    except peewee.IntegrityError:
        raise InvalidInputError(
            f"Used email or username. email: {email}, username: {username}"
        )

    p = Profile(user=user)
    p.save()

    return user, password


def is_valid_username(new_name):
    if not new_name:
        return False
    if secure_filename(new_name) != new_name:
        return False
    if User.get_or_none(User.username == new_name):
        return False
    return True


def is_valid_email(new_email):
    if not new_email:
        return False
    if not is_email(new_email):
        return False
    if User.get_or_none(User.email == new_email):
        return False
    return True
