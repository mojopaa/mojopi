import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import List

import peewee
from flask_login import UserMixin
from werkzeug.utils import secure_filename

from mojopi.utils import (
    DPATH,
    MOCK_DB,
    PIC_PATH,
    RINGS_PATH,
    InvalidInputError,
    calculate_sha256,
    conf,
    file_size,
    generate_password,
    hash_password,
    hr_size,
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


# refer to pypi, look at test/read_pypi_json.ipynb
# info = dir(Ring) + dir(Project)
class Ring(BaseModel):
    name = peewee.CharField(max_length=50)
    version = peewee.CharField(max_length=50, null=True)
    platform = peewee.CharField(max_length=100, null=True)
    author = peewee.CharField(max_length=50, null=True)
    author_email = peewee.CharField(max_length=50, null=True)
    requires_dist = peewee.TextField(null=True)
    requires_mojo = peewee.CharField(max_length=20, null=True)
    yanked = peewee.CharField(max_length=10, null=True)
    yanked_reason = peewee.CharField(max_length=100, null=True)
    file_name = peewee.CharField(max_length=100, null=True)
    sha256 = peewee.CharField(max_length=64, null=True)
    size = peewee.CharField(max_length=20, null=True)
    upload_at = peewee.DateTimeField(default=datetime.now)

    class Meta:
        database = db
        primary_key = peewee.CompositeKey("name", "version", "platform")  # 設定聯合主鍵

    def __str__(self) -> str:
        return f"{self.name}-{self.version}"


# 1 project to many rings
class Project(BaseModel):
    name = peewee.CharField(max_length=50)
    version = peewee.CharField(max_length=50, null=True)
    description = peewee.TextField(null=True)
    # _valid_description_content_types = {"text/plain", "text/x-rst", "text/markdown"}
    description_content_type = peewee.CharField(max_length=20, null=True)
    home_page = peewee.CharField(max_length=100, null=True)
    keywords = peewee.CharField(max_length=200, null=True)
    license = peewee.TextField(null=True)
    maintainer = peewee.CharField(max_length=50, null=True)
    maintainer_email = peewee.CharField(max_length=50, null=True)
    summary = peewee.CharField(max_length=100, null=True)
    create_at = peewee.DateTimeField(default=datetime.now)
    last_modified = peewee.DateTimeField(default=datetime.now)

    class Meta:
        database = db
        primary_key = peewee.CompositeKey("name", "version")  # 設定聯合主鍵


def init_db(mock=MOCK_DB):
    if not db_path.parent.is_dir():
        os.makedirs(db_path.parent)

    try:
        User.create_table()
        Profile.create_table()
        Ring.create_table()
        Project.create_table()
    except Exception as e:
        logging.exception(e)
        print("Create table error. See log for more information.")
        # pass

    if not mock:
        return

    # start mocking
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
    mock_profile.bio = """**I am an experienced Python engineer with 5 years of relevant work experience.** I am deeply passionate about this profession, and I believe my expertise in Python and related technologies, along with my adaptability, make me the ideal candidate for your company.

In my previous roles, I have been responsible for designing and developing various complex Python applications. My expertise extends to, but is not limited to, Django, Flask, NumPy, Pandas, Selenium, and more.

I have excelled in problem-solving and optimizing code. I possess strong coding practices, adhere to software development life cycles and software engineering principles, and am proficient in using version control tools like Git for code management. I am also skilled in teamwork, boasting excellent communication abilities that enable me to collaborate effectively with designers and other technical professionals to solve intricate problems and create high-quality products.

I am a diligent and responsible individual, driven by a love for learning. I can quickly grasp new technologies and tools and apply them in practical scenarios. I firmly believe that my skills and experience can bring great value to your company."""
    mock_profile.save()

    # add mock project
    des = """The Advanced Scientific Data Format (ASDF) is a next-generation interchange format for scientific data. This package contains the Python implementation of the ASDF Standard. More information on the ASDF Standard itself can be found here.

The ASDF format has the following features:

A hierarchical, human-readable metadata format (implemented using YAML)

Numerical arrays are stored as binary data blocks which can be memory mapped. Data blocks can optionally be compressed.

The structure of the data can be automatically validated using schemas (implemented using JSON Schema)

Native Python data types (numerical types, strings, dicts, lists) are serialized automatically

ASDF can be extended to serialize custom data types

ASDF is under active development on github. More information on contributing can be found below.

Overview
This section outlines basic use cases of the ASDF package for creating and reading ASDF files.
"""
    try:
        add_project(name="test", version="1")
        add_project(
            name="test",
            version="2",
            description=des,
            description_content_type="text/plain",
            summary="asdf asdf",
            license="MIT",
            keywords="test1, test2",
            maintainer="asdf",
            maintainer_email="asdf@gmail.com",
            home_page="https://pypi.org/project/asdf/",
        )

        # mock ring
        add_ring(name="test", version="1")
        add_ring(
            name="test",
            version="2",
            file_name="test-2.ring",
            sha256="a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
        )
    except InvalidInputError:
        pass


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


def add_ring(
    name,
    version="",
    author="",
    author_email="",
    platform="",
    require_dist: List[str] | None = None,
    requires_mojo="",
    file_name="",
    sha256="",
    yanked=False,
    yanked_reason="",
):
    # NULL version and platform will have duplicates in DB
    ring = Ring(name=name, version=version, platform=platform)

    if author:
        ring.author = author
    if author_email:
        if not is_email(author_email):
            raise InvalidInputError("Invalid author email")
        ring.author_email = author_email
    if require_dist:
        if type(require_dist) is str:
            ring.requires_dist = require_dist
        else:
            ring.requires_dist = json.dumps(require_dist)
    if requires_mojo:
        ring.requires_mojo = requires_mojo
    if sha256:
        ring.sha256 = sha256
    if yanked:
        ring.yanked = yanked
    if yanked_reason:
        ring.yanked_reason = yanked_reason

    if file_name:
        ring.file_name = file_name
        ring.size = hr_size(file_size(RINGS_PATH / file_name))
        ring.sha256 = calculate_sha256(RINGS_PATH / file_name)

    try:
        ring.save(force_insert=True)
    except peewee.IntegrityError:
        raise InvalidInputError("Duplicate ring.")

    if (
        Project.get_or_none((Project.name == name) & (Project.version == version))
        is None
    ):
        add_project(
            name=name, version=version, maintainer=author, maintainer_email=author_email
        )
    return ring


def add_project(
    name,
    version="",
    description="",
    description_content_type="",
    home_page="",
    keywords="",
    license="",
    maintainer="",
    maintainer_email="",
    summary="",
):
    pj = Project(name=name)
    pj.version = version

    if description:
        pj.description = description
    if description_content_type:
        pj.description_content_type = description_content_type
    elif description:
        pj.description_content_type = "text/plain"
    if home_page:
        pj.home_page = home_page
    if keywords:
        pj.keywords = keywords
    if license:
        pj.license = license
    if maintainer:
        pj.maintainer = maintainer
    if maintainer_email:
        if not is_email(maintainer_email):
            raise InvalidInputError("Invalid email")
        pj.maintainer_email = maintainer_email
    if summary:
        pj.summary = summary

    try:
        pj.save(force_insert=True)
    except peewee.IntegrityError as e:
        if "project.name" in str(e):
            raise InvalidInputError(
                f"Invalid project: {pj.name}-{pj.version}. It's duplicate."
            )

        # Why varchar(100) no exception?
        # This is because in some database systems, a VARCHAR(100) field can store data that does not exceed 100 characters,
        # and when attempting to store data that exceeds the limit, it will automatically truncate the exceeding part.
        # This may result in data being truncated without raising an exception.

    return pj
