"""一些基本的函數，不牽涉到其他模組的東西。盡量不要 import other project's module to avoid circular imports."""

import os
import random
import re
import string

try:
    import tomllib
except ImportError:
    import tomlkit

from pathlib import Path

import bcrypt
from flask_login import LoginManager

conf_file = Path(__file__).with_name("conf.toml")
try:
    with open(conf_file, "rb") as f:
        conf = tomllib.load(f)
except NameError:
    with open(conf_file, "r") as f:
        conf = tomlkit.load(f)

login_manager = LoginManager()


class InvalidInputError(Exception):
    pass


if not Path(conf["data_folder"]).parent.exists():  # The folder contains data not exists
    DPATH = Path(__file__).parent.parent.parent / "data"
else:
    DPATH = Path(conf["data_folder"])

SERVER_FILES_PATH = DPATH / "server_files"
PIC_PATH = DPATH / "server_files" / "profile_pic"
MATERIAL_PATH = DPATH / "server_files" / "materials"
PUBLIC_PATH = DPATH / "server_files" / "public"


def init_data():
    if not os.path.exists(Path(DPATH)):
        os.makedirs(DPATH)

    # mkdir fbp
    if not os.path.exists(SERVER_FILES_PATH):
        os.mkdir(SERVER_FILES_PATH)

    # mkdir profile picture
    if not os.path.exists(PIC_PATH):
        os.mkdir(PIC_PATH)

    # mkdir material files
    if not os.path.exists(MATERIAL_PATH):
        os.mkdir(MATERIAL_PATH)

    # public server files
    if not PUBLIC_PATH.exists():
        os.mkdir(PUBLIC_PATH)


def generate_password(length=5):
    clist = string.ascii_letters + string.digits
    pw = []
    for _ in range(length):
        pw.append(random.choice(clist))
    return "".join(pw)


def hash_password(password):
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt)

    return hashed_password


def verify_password(password, hashed_password):
    # Check if the provided password matches the hashed password
    if password is None:
        password = ""
    if hashed_password is None:
        hashed_password = ""

    if type(password) is not bytes:
        password = password.encode("utf-8")

    if type(hashed_password) is not bytes:
        hashed_password = hashed_password.encode("utf-8")

    return bcrypt.checkpw(password, hashed_password)


def is_email(email):
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"  # 正則表達式模式
    return re.match(pattern, email) is not None
