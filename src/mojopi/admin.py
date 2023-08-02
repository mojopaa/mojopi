import logging
from pathlib import Path

import flask_admin as fadmin
from flask import Blueprint, Flask, render_template, url_for
from flask_admin.contrib.peewee import ModelView
from flask_login import current_user

from mojopi.models import Post, User, UserInfo, db_path, init_db
from mojopi.utils import DPATH, conf, init_data, login_manager
from mojopi.views import apibp, fbp, mbp, mojobp


class UserAdmin(ModelView):
    inline_models = (UserInfo,)


class PostAdmin(ModelView):
    # Visible columns in the list view
    column_exclude_list = ["text"]

    # List of columns that can be sorted. For 'user' column, use User.email as
    # a column.
    column_sortable_list = ("title", ("user", User.email), "date")

    # Full text search
    column_searchable_list = ("title", User.username)

    # Column filters
    column_filters = ("title", "date", User.username)

    form_ajax_refs = {"user": {"fields": (User.username, "email")}}


def main():
    init_data()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = "123456790"  # 設置一個密鑰以進行會話加密

    # setup logging
    log_file = DPATH / "mojopi.log"
    logging.basicConfig(filename=log_file, filemode="a")
    logging.getLogger().setLevel(logging.DEBUG)

    # setup flask login
    login_manager.init_app(app)

    # setup flask admin
    admin = fadmin.Admin(app, name="MojoPI Admin")

    admin.add_view(UserAdmin(User))
    admin.add_view(PostAdmin(Post))

    # setup db
    if not Path(db_path).exists():
        init_db()

    # views
    adminbp = Blueprint("adminbp", __name__)

    @adminbp.route("/")
    def index():
        if current_user.is_authenticated:
            return render_template("index.html", admin_mode=True)
        return render_template("index.html", admin_mode=True)

    app.register_blueprint(
        adminbp
    )  # the router will route to the first registered view.
    app.register_blueprint(mbp)
    app.register_blueprint(fbp)
    app.register_blueprint(apibp)
    app.register_blueprint(mojobp)

    app.run(debug=True)


if __name__ == "__main__":
    main()
