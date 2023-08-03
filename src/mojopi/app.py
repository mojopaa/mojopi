import logging
from pathlib import Path

from flask import Flask

from mojopi.models import db_path, init_db
from mojopi.utils import DPATH, conf, init_data, login_manager
from mojopi.views import fbp, mbp, mojobp, api


def main():
    init_data()

    app = Flask(__name__)
    app.config["SECRET_KEY"] = "123456790"  # 設置一個密鑰以進行會話加密

    # setup logging
    log_file = DPATH / "mojopi.log"
    logging.basicConfig(filename=log_file, filemode="a")
    logging.getLogger().setLevel(logging.INFO)

    # setup flask login
    login_manager.init_app(app)

    # setup db
    if not Path(db_path).exists():
        init_db()

    # views
    app.register_blueprint(mbp)
    app.register_blueprint(fbp)
    app.register_blueprint(mojobp)

    # init api
    api.init_app(app)

    app.run()


if __name__ == "__main__":
    main()
