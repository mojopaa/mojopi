import logging
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_user, logout_user
from peewee import DoesNotExist, IntegrityError
from werkzeug.utils import secure_filename

from .models import Profile, User, UserInfo, add_user, is_valid_email, is_valid_username
from .utils import (
    DPATH,
    PIC_PATH,
    SERVER_FILES_PATH,
    InvalidInputError,
    hash_password,
    login_manager,
    verify_password,
)

apibp = Blueprint("apibp", __name__, url_prefix="/api")

mbp = Blueprint("mbp", __name__)  # main bp

# files bp
fbp = Blueprint(
    "fbp",
    __name__,
    static_folder=SERVER_FILES_PATH / "public",
    static_url_path="/public",
    url_prefix="/files",
)


def avatar_url():
    if current_user.is_authenticated and current_user.picture:
        return url_for("fbp.get_profile_pic")
    else:
        return url_for("static", filename="Sample_User_Icon.png")


def profile_pic_url(user_id):
    try:
        user = User.get_by_id(user_id)
    except DoesNotExist:
        url = url_for("static", filename="Sample_User_Icon.png")

    if user.picture:
        url = url_for("fbp.get_profile_pic", user_id=user_id)
    else:
        url = url_for("static", filename="Sample_User_Icon.png")

    return url


@mbp.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("index.html", avatar=avatar_url())
    return render_template("index.html")


@login_manager.user_loader
def load_user(user_id):
    try:
        return User.get_by_id(user_id)
    except DoesNotExist:
        return None


@mbp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        next_url = request.args.get("next")
        return render_template("login.html", next_url=next_url)

    elif request.method == "POST":
        email = request.form.get("email")  # form 用 name="email" 才抓得到
        password = request.form.get("password")
        next_url = request.args.get("next")
        user = User.get_or_none(User.email == email)

        if user:
            if not user.password:
                login_user(user)
                flash("Need to reset password.")
                return redirect(next_url or url_for("mbp.reset_password"))

            elif verify_password(password=password, hashed_password=user.password):
                login_user(user)
                flash("Logged in successfully.")

                return redirect(next_url or url_for("mbp.index"))
            else:
                flash("Wrong password.")
                return redirect(url_for("mbp.login", next=next_url))
        else:
            flash("Email incorrect.")
            return redirect(url_for("mbp.login"))  # TODO: 或是顯示錯誤訊息


@mbp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    elif request.method == "POST":
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        if not is_valid_email(email) or not is_valid_username(username):
            flash("Register failed. Invalid email and username.")
            return redirect(url_for("mbp.index"))

        # start registering
        try:
            user, _ = add_user(email=email, username=username, password=password)
        except InvalidInputError:
            flash("Register failed. Invalid email and username.")
            return redirect(url_for("mbp.index"))

        login_user(user)
        flash("Register successfully.")

        return redirect(url_for("mbp.index"))


@apibp.route("/username/<string:usn>")
def username_api(usn):
    if is_valid_username(usn):
        return jsonify({"valid": True})
    else:
        return jsonify({"valid": False})


@apibp.route("/email/<string:eml>")
def email_api(eml):
    if is_valid_email(eml):
        return jsonify({"valid": True})
    else:
        return jsonify({"valid": False})


@mbp.route("/profile")
def profile_self():
    if not current_user.is_authenticated:
        return redirect(url_for("mbp.login", next="/profile"))
    return redirect(f"/profile/{current_user.id}")


@mbp.route("/profile/<int:user_id>")
def profile(user_id):
    try:
        user = User.get_by_id(user_id)
    except DoesNotExist:
        abort(404)

    pf = Profile.get(Profile.user == user)
    if pf.is_public or current_user == user:
        return render_template(
            "profile.html",
            profile_pic_url=profile_pic_url(user_id),
            avatar=avatar_url(),
            profile=pf,
        )
    else:
        abort(404, "User's profile is private.")


@fbp.route("/profile_pic", methods=["POST"])
def profile_pic_upload():
    if not current_user.is_authenticated:
        abort(401)

    if "file" not in request.files:
        abort(400, "No file provided.")

    file = request.files["file"]
    if file.filename == "":
        abort(400, "Empty filename.")

    if file:
        # 使用 secure_filename 函式來避免潛在的安全問題
        filename = secure_filename(file.filename)
        username = current_user.username
        filename_suffix = Path(filename).suffix  # 取得檔案副檔名

        # 儲存檔案到指定的目錄中
        file.save(PIC_PATH / f"{username}{filename_suffix}")

        current_user.picture = f"{username}{filename_suffix}"
        current_user.save()

        return {"message": "Profile picture saved successfully."}
    else:
        abort(400, "Invalid file.")


@fbp.route("/profile_pic", methods=["GET"], defaults={"user_id": None})
@fbp.route("/profile_pic/<int:user_id>", methods=["GET"])
def get_profile_pic(user_id):
    if user_id is None:
        if not current_user.is_authenticated:
            abort(401)
        user = current_user
    else:
        try:
            user = User.get_by_id(user_id)
        except DoesNotExist:
            abort(404, description="User not found.")

    if user.picture:
        pic_path = PIC_PATH / user.picture
        if pic_path.is_file():
            return send_from_directory(str(pic_path.parent), pic_path.name)
    else:
        abort(404, "Profile picture not found.")


@mbp.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if not current_user.is_authenticated:
        abort(401)

    if request.method == "GET":
        pf = Profile.get(Profile.user == current_user)
        return render_template("edit_profile.html", avatar=avatar_url(), profile=pf)

    elif request.method == "POST":
        username = request.form.get("username")
        education = request.form.get("education")
        experience = request.form.get("experience")
        bio = request.form.get("bio")

        current_user.username = username
        try:
            current_user.save()
        except IntegrityError:
            flash("New username conflicts with existing account.")

        pf = Profile.get(Profile.user == current_user)
        pf.education = education
        pf.experience = experience
        pf.bio = bio
        pf.save()

        flash("Edit Successful!")
        return redirect(url_for("mbp.profile", user_id=current_user.id))


@mbp.route("/settings")
def settings():
    if not current_user.is_authenticated:
        abort(401, description="Need to login to view settings.")
    return render_template("settings.html", avatar=avatar_url())


@mbp.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if not current_user.is_authenticated:
        abort(401)

    if request.method == "GET":
        return render_template("reset_password.html", avatar=avatar_url())

    elif request.method == "POST":
        new_password = request.form.get("new-password")
        confirm_password = request.form.get("confirm-password")

        try:
            assert new_password == confirm_password
        except AssertionError:
            abort(403, "New password is not equal to confirm password.")

        current_user.password = hash_password(new_password)
        current_user.save()

        flash("New password set!")

        return redirect(url_for("mbp.settings"))


@mbp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("mbp.index"))
