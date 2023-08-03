"""一些基本的函數，不牽涉到其他模組的東西。盡量不要 import other project's module to avoid circular imports."""

import os
import random
import re
import string
from hashlib import sha256

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


if (
    conf.get("data_folder") is None or not Path(conf.get("data_folder")).parent.exists()
):  # The folder contains data not exists
    if "python" in str(Path(__file__)).lower():
        DPATH = Path(os.getcwd()) / "data"  # TODO: test
    else:
        DPATH = Path(__file__).parent.parent.parent / "data"
else:
    DPATH = Path(conf["data_folder"])


SERVER_FILES_PATH = DPATH / "server_files"
PIC_PATH = DPATH / "server_files" / "profile_pic"
RINGS_PATH = DPATH / "server_files" / "rings"
PUBLIC_PATH = DPATH / "server_files" / "public"


MOCK_DB = conf.get("mock_db", False)
MOCK_DATA = conf.get("mock_data", False)


def init_data(mock=MOCK_DATA):
    if not os.path.exists(Path(DPATH)):
        os.makedirs(DPATH)

    # mkdir fbp
    if not os.path.exists(SERVER_FILES_PATH):
        os.mkdir(SERVER_FILES_PATH)

    # mkdir profile picture
    if not os.path.exists(PIC_PATH):
        os.mkdir(PIC_PATH)

    # mkdir ring files
    if not os.path.exists(RINGS_PATH):
        os.mkdir(RINGS_PATH)

    # public server files
    if not PUBLIC_PATH.exists():
        os.mkdir(PUBLIC_PATH)

    if not mock:
        return

    # start mocking
    # create mock ring
    with open(RINGS_PATH / "test-2.ring", "w", encoding="utf-8") as f:
        f.writelines("123")


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


def file_size(file_path):
    try:
        size = os.path.getsize(file_path)
        return size
    except FileNotFoundError:
        print(f"file not found：{file_path}")
    except Exception as e:
        print(f"error：{e}")
        return None


def hr_size(size_in_bytes):
    """
    Calculate the human-readable size of a file.

    Args:
        size_in_bytes (int): The size of the file in bytes.

    Returns:
        str: The human-readable size of the file.
    """
    # 定義不同的大小單位
    units = ["B", "KB", "MB", "GB", "TB"]

    # 若檔案大小小於 1 B，直接回傳
    if size_in_bytes < 1:
        return f"{size_in_bytes} B"

    # 計算使用哪個單位
    unit_index = 0
    while size_in_bytes >= 1024 and unit_index < len(units) - 1:
        size_in_bytes /= 1024
        unit_index += 1

    # 使用適當的單位進行格式化
    return f"{size_in_bytes:.2f} {units[unit_index]}"


def calculate_sha256(file_path):
    sha256_hash = sha256()

    # 使用二進位模式打開檔案並將整個內容讀取到記憶體中
    with open(file_path, "rb") as file:
        file_content = file.read()

    # 將檔案內容傳遞給 hashlib.sha256 函數
    sha256_hash.update(file_content)

    # 回傳計算得到的 SHA-256 雜湊值（以十六進位字串表示）
    return sha256_hash.hexdigest()
