import json
import logging
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_user, logout_user
from peewee import DoesNotExist, IntegrityError, fn
from werkzeug.utils import secure_filename
from mups import RingInfo
from serde import to_dict
from flask_restx import Api, Resource, fields
from dataclasses import dataclass, is_dataclass

from .models import (
    Profile,
    Project,
    Ring,
    User,
    add_project,
    add_ring,
    add_user,
    is_valid_email,
    is_valid_username,
)
from .readme import render  # TODO: Not working, need to investigate
from .utils import (
    DPATH,
    PIC_PATH,
    RINGS_PATH,
    SERVER_FILES_PATH,
    InvalidInputError,
    calculate_sha256,
    hash_password,
    login_manager,
    verify_password,
)
from . import __version__

# apibp = Blueprint("apibp", __name__, url_prefix="/api")  # json api

mbp = Blueprint(
    "mbp", __name__
)  # main bp, including index page, login, register, profile, settings etc.

mojobp = Blueprint("mojobp", __name__)  # everything related to mojo

# TODO: 404 handler. PYPI has a search bar and good color.

# files bp
fbp = Blueprint(
    "fbp",
    __name__,
    static_folder=SERVER_FILES_PATH / "public",
    static_url_path="/public",
    url_prefix="/files",
)


# 對應不同型別和 fields 類之間的對應關係
TYPE_TO_FIELD = {
    int: fields.Integer,
    str: fields.String,
    bool: fields.Boolean,
    float: fields.Float,
    list: fields.List,
    # 在這裡添加其他型別對應的 fields 類
}


# 轉換 dataclass 屬性到資料模型的 fields
def convert_to_fields(data_class):
    fields_dict = {}
    for field_name, field_type in data_class.__annotations__.items():
        if is_dataclass(field_type):
            fields_dict[field_name] = convert_to_fields(field_type)
        else:
            field_class = TYPE_TO_FIELD.get(field_type, fields.Raw)
            fields_dict[field_name] = field_class(description=f"The {field_name} field")
    return fields_dict


# 初始化資料模型
api = Api(
    version=__version__,
    title="MojoPI API",
    description="MojoPI API are all list here",
    terms_url="https://github.com/drunkwcodes/mojopi/blob/main/terms_of_service.txt",
    contact="drunkwcodes@gmail.com",
    license="MIT",
    license_url="https://github.com/drunkwcodes/mojopi/blob/main/LICENSE",
    prefix="/api",
)

ring_info_model = api.model("ModelName", convert_to_fields(RingInfo))


def profile_pic_url(user_id=0, username=""):
    # default anonymous avatar
    url = url_for("static", filename="Sample_User_Icon.png")

    if user_id:
        try:
            user = User.get_by_id(user_id)
        except DoesNotExist:
            return url
    elif username:
        user = User.get_or_none(User.username == username)
        if user is None:
            return url
    else:
        return url

    if user.picture:
        user_id = user.id
        url = url_for("fbp.get_profile_pic", user_id=user_id)

    return url


@mbp.route("/")
def index():
    if current_user.is_authenticated:
        return render_template("index.html")
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


@api.route("/username/<string:usn>")
def username_api(usn):
    if is_valid_username(usn):
        return {"valid": True}
    else:
        return {"valid": False}


@api.route("/email/<string:eml>")
def email_api(eml):
    if is_valid_email(eml):
        return {"valid": True}
    else:
        return {"valid": False}


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
            profile_pic_url=profile_pic_url(user_id=user_id),
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
    abort(404, "Profile picture not found.")


@mbp.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if not current_user.is_authenticated:
        abort(401)

    if request.method == "GET":
        pf = Profile.get(Profile.user == current_user)
        return render_template("edit_profile.html", profile=pf)

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
    return render_template("settings.html")


@mbp.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if not current_user.is_authenticated:
        abort(401)

    if request.method == "GET":
        return render_template("reset_password.html")

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


def project_info(pname, version=""):
    pj = Project.get_or_none((Project.name == pname) & (Project.version == version))
    latest_ring_dt = (
        Ring.select(fn.MAX(Ring.upload_at)).where(Ring.name == pname).scalar()
    )
    ring = Ring.get_or_none((Ring.name == pname) & (Ring.upload_at == latest_ring_dt))

    if pj is None:
        return None

    info = {"name": pname}
    info["version"] = pj.version
    if pj.description:
        info["description"] = pj.description
    if pj.description_content_type:
        info["description_content_type"] = pj.description_content_type
    if pj.home_page:
        info["home_page"] = pj.home_page
    if pj.keywords:
        info["keywords"] = pj.keywords
    if pj.license:
        info["license"] = pj.license
    if ring is not None:
        if ring.author:
            info["author"] = ring.author
        if ring.author_email:
            info["author_email"] = ring.author_email
        if ring.requires_mojo:
            info["requires_mojo"] = ring.requires_mojo
        if ring.file_name:
            info["file_name"] = ring.file_name

    if pj.maintainer:
        info["maintainer"] = pj.maintainer
    if pj.maintainer_email:
        info["maintainer_email"] = pj.maintainer_email
    if pj.summary:
        info["summary"] = pj.summary
    info["create_at"] = str(pj.create_at)
    info["last_modified"] = str(pj.last_modified)

    return info


def composite_info(ring):
    pj = Project.get_or_none(
        (Project.name == ring.name) & (Project.version == ring.version)
    )

    info = {"name": ring.name}
    info["version"] = ring.version
    if ring.author:
        info["author"] = ring.author
    if ring.author_email:
        info["author_email"] = ring.author_email
    if ring.requires_mojo:
        info["requires_mojo"] = ring.requires_mojo
    if ring.file_name:
        info["file_name"] = ring.file_name

    if pj is not None:
        if pj.description:
            info["description"] = pj.description
        if pj.description_content_type:
            info["description_content_type"] = pj.description_content_type
        if pj.home_page:
            info["home_page"] = pj.home_page
        if pj.keywords:
            info["keywords"] = pj.keywords
        if pj.license:
            info["license"] = pj.license
        if pj.maintainer:
            info["maintainer"] = pj.maintainer
        if pj.maintainer_email:
            info["maintainer_email"] = pj.maintainer_email
        if pj.summary:
            info["summary"] = pj.summary
        info["create_at"] = str(pj.create_at)
        info["last_modified"] = str(pj.last_modified)

    return info


def latest_project_version(project_name):
    latest_version = (
        Project.select(fn.MAX(Project.version))
        .where(Project.name == project_name)
        .scalar()
    )
    return latest_version


@mojobp.route("/project/<string:project_name>", defaults={"version": ""})
@mojobp.route("/project/<string:project_name>/<string:version>")
def project(project_name, version):
    if version == "":
        version = latest_project_version(project_name=project_name)

    pj = Project.get_or_none(
        (Project.name == project_name) & (Project.version == version)
    )
    if pj is None:
        abort(404)
    return render_template(
        "project.html",
        info=project_info(project_name, version=version),
        description=render(pj.description, content_type=pj.description_content_type),
    )


@mojobp.route("/project/<string:project_name>/history", defaults={"version": ""})
@mojobp.route("/project/<string:project_name>/<string:version>/history")
def project_history(project_name, version):
    if version == "":
        version = latest_project_version(project_name=project_name)

    pj = Project.get_or_none(
        (Project.name == project_name) & (Project.version == version)
    )
    if pj is None:
        abort(404, "Project not exist.")

    releases = (
        Ring.select().where(Ring.name == project_name).order_by(Ring.upload_at.desc())
    )

    return render_template(
        "project_history.html",
        info=project_info(project_name, version=version),
        releases=releases,
    )


@mojobp.route("/project/<string:project_name>/files", defaults={"version": ""})
@mojobp.route("/project/<string:project_name>/<string:version>/files")
def project_files(project_name, version):
    if version == "":
        version = latest_project_version(project_name=project_name)

    pj = Project.get_or_none(
        (Project.name == project_name) & (Project.version == version)
    )
    if pj is None:
        abort(404, "Project not exist.")

    rings = Ring.select().where((Ring.name == project_name) & (Ring.version == version))

    # TODO: source dist
    return render_template(
        "project_download.html",
        info=project_info(project_name, version=version),
        rings=rings,
    )


@fbp.route(
    "/ring/<string:name>",
    defaults={"version": "", "platform": ""},
    methods=["GET", "POST"],
)
@fbp.route(
    "/ring/<string:name>/<string:version>",
    defaults={"platform": ""},
    methods=["GET", "POST"],
)
@fbp.route(
    "/ring/<string:name>/<string:version>/<string:platform>", methods=["GET", "POST"]
)
def ring_file(name, version, platform):  # TODO: Add upload test script
    if not version:
        version = latest_project_version(name)

    if request.method == "GET":
        if platform:
            ring = Ring.get_or_none(
                (Ring.name == name)
                & (Ring.version == version)
                & (Ring.platform == platform)
            )
        else:  # TODO: determine a default platform
            ring = Ring.get_or_none((Ring.name == name) & (Ring.version == version))

        if ring is None:
            abort(
                404, f"Ring not found: {name}, version: {version}, platform: {platform}"
            )

        if ring.file_name:
            # Your logic to generate the additional info JSON
            additional_info = composite_info(ring)

            # Sending the file from the specified directory
            file_path = RINGS_PATH / ring.file_name

            # Creating a custom response with file content and additional info
            response = make_response(send_file(file_path))

            # Adding additional_info to the response headers
            response.headers["x-ring-info"] = json.dumps(additional_info)

            return response

        else:
            abort(404, "Ring file not uploaded.")

    elif request.method == "POST":  # TODO: dead code. To be removed.
        if not request.is_json:
            abort(415, "Not JSON")

        file = request.files["file"]
        if file.filename == "":
            abort(400, "No file upload.")

        data = request.get_json()
        name = data.get("name")
        version = data.get("version", "")
        platform = data.get("platform", "")
        author = data.get("author", "")
        author_email = data.get("author_email", "")
        require_dist = data.get("require_dist", "")
        require_mojo = data.get("require_mojo", "")
        file_name = file.filename
        sha256 = calculate_sha256(RINGS_PATH / file_name)

        if name is None:
            abort(
                422, "name not provided."
            )  # https://developer.mozilla.org/zh-CN/docs/Web/HTTP/Status/422

        try:
            add_ring(
                name=name,
                version=version,
                platform=platform,
                author=author,
                author_email=author_email,
                require_dist=require_dist,
                require_mojo=require_mojo,
                file_name=file_name,
                sha256=sha256,
            )
        except InvalidInputError:
            abort(400, "Upload failed. Duplicate ring.")

        file.save(RINGS_PATH / file.filename)


@mojobp.route("/search")
def search():
    # 從 URL 中取得搜尋字串
    query_string = request.args.get("q", "")

    # 在資料庫  或內容中進行搜尋操作

    pjs = Project.select().where(Project.name ** f"%{query_string}%")
    results = []
    for pj in pjs:
        if query_string.lower() in pj.name.lower():
            results.append(pj)

    # 返回搜尋結果給前端頁面
    return render_template("search_results.html", results=results)


@api.route("/ring/<string:name>/<string:version>/<string:platform>")
@api.route("/ring/<string:name>/<string:version>")
class RingResource(Resource):
    def get(self, name, version, platform=""):
        ring = Ring.get_or_none(
            (Ring.name == name) & (Ring.version == version) & (Ring.platform == platform)
        )
        if ring is None:
            return {"message": "Ring not found."}, 404

        return composite_info(ring)
    
    def post(self, name, version, platform=""):
        ring = Ring.get_or_none(
            (Ring.name == name) & (Ring.version == version) & (Ring.platform == platform)
        )
        if ring is not None:
            print(f"{ring = }")
            return {"message": "Ring exists."}, 400

        # 檢查是否有檔案和 info 資料
        if "file" not in request.files or "info" not in request.files:
            return {"error": "Missing file or info data."}, 400

        # 取得檔案和 info 資料
        file = request.files["file"]
        info = request.files["info"].read()

        # 解析 info 資料
        try:
            info = json.loads(info)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON format in info data."}, 400

        # 取得 info 中的檔案名稱
        file_name = info.get("file_name")

        # 確認檔案名稱存在且非空
        if not file_name:
            return {"error": "File name missing in info data."}, 400

        # 儲存檔案
        file.save(RINGS_PATH / file_name)
        add_ring(
            name=name,
            version=version,
            platform=platform,
            file_name=file_name,
            author=info.get("author"),
            author_email=info.get("author_email"),
            require_dist=info.get("require_dist"),
            requires_mojo=info.get("require_mojo"),  # TODO: rename require_mojo
            sha256=calculate_sha256(RINGS_PATH / file_name),
        )
        # 回傳成功訊息
        return {"message": "File uploaded successfully."}, 200



@api.route("/ring/<string:name>/<string:version>/download")
@api.route("/ring/<string:name>/<string:version>/<string:platform>/download")
class RingDownloadResource(Resource):
    def get(name, version, platform=""):
        ring = Ring.get_or_none(
            (Ring.name == name) & (Ring.version == version) & (Ring.platform == platform)
        )
        if ring is None:
            return {"message": "Ring not found."}, 404

        return redirect(
            url_for("fbp.ring_file", name=name, version=version, platform=platform)
        )

