from pathlib import Path

from mojopi import InvalidInputError
from mojopi.models import User, add_user, init_db, is_valid_email, is_valid_username
from mojopi.utils import PIC_PATH, init_data


def test_add_user():
    init_data()
    init_db()
    try:
        add_user(
            email="eric@simutech.com.tw", username="drunkwcodes", password="123456"
        )
    except InvalidInputError:
        pass
    assert User.get(User.email == "eric@simutech.com.tw")


def test_is_valid_username():
    username = "drunkwcodes"
    u = User.get_or_none(User.username == username)
    if u:
        assert is_valid_username(username) is False
    else:
        assert is_valid_username(username) is True

    assert is_valid_username("") is False
    assert is_valid_username("../test") is False
    assert is_valid_username("stran_ge.username") is True


def test_is_valid_email():
    email = "eric@simutech.com.tw"
    if User.get_or_none(User.email == email):
        assert is_valid_email(email) is False
    else:
        assert is_valid_email(email) is True

    assert is_valid_email("") is False
    assert is_valid_email("asdf") is False


def test_change_username():
    username = "drunkwcodes"
    test_name = "testtest"
    u = User.get_or_none(User.username == username)
    if u:
        u.change_username(test_name)
        if u.picture:
            assert Path(u.picture).stem == test_name
            assert (Path(PIC_PATH) / u.picture).exists()

        u.change_username(username)
