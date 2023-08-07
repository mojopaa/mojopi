from flask import Flask

from mojopi.utils import login_manager
from mojopi.views import fbp, mbp


def test_mbp():
    app = Flask(__name__, template_folder="../../src/mojopi/templates")
    app.secret_key = "your_secret_key"
    login_manager.init_app(app)

    app.register_blueprint(mbp)
    app.register_blueprint(fbp)

    client = app.test_client()

    response = client.get("/")
    assert response.status_code == 200

    response = client.get("/login")
    assert response.status_code == 200

    response = client.get("/register")
    assert response.status_code == 200

    response = client.get("/profile")
    assert response.status_code == 302

    response = client.get("/profile/1")
    assert response.status_code == 200

    response = client.get("/profile/100")
    assert response.status_code == 404

    # login simulation
    response = client.post(
        "/login", data=dict(email="eric@simutech.com.tw", password="123456")
    )
    assert response.status_code == 302

    with app.test_request_context():
        # with client.session_transaction() as sess:
        #     pass  # TODO
        pass
