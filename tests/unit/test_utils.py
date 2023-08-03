import os
from pathlib import Path

from mojopi.models import User, add_user
from mojopi.utils import (
    DPATH,
    generate_password,
    hash_password,
    init_data,
    is_email,
    verify_password,
)


def test_init_data():
    init_data()
    assert Path(DPATH).exists()


def test_generate_password():
    pw = generate_password()
    assert len(pw) == 5


def test_hash_password():
    pw = hash_password(generate_password())
    assert len(pw) == 60


def test_verify_password():
    pw = generate_password()
    hpw = hash_password(pw)
    assert verify_password(pw, hpw)


def test_is_email():
    assert is_email("strange@email.com") is True
    assert is_email("str.ange@email.com") is True
