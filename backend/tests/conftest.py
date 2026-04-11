from flask_jwt_extended import create_access_token
import pytest

from app import create_app, db, socketio
from app.models.user import User


@pytest.fixture()
def app_instance():
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["CELERY_TASK_ALWAYS_EAGER"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app_instance):
    return app_instance.test_client()


@pytest.fixture()
def socket_client(app_instance):
    clients = []

    def _socket_client(token):
        client = socketio.test_client(app_instance, flask_test_client=app_instance.test_client(), auth={"token": token})
        clients.append(client)
        return client

    yield _socket_client

    for client in clients:
        client.disconnect()


@pytest.fixture()
def create_user(app_instance):
    def _create_user(email, password="Password123", username="tester"):
        with app_instance.app_context():
            user = User(email=email, username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return user.id

    return _create_user


@pytest.fixture()
def auth_headers(app_instance, create_user):
    def _auth_headers(email="tokenuser@example.com"):
        user_id = create_user(email=email)
        with app_instance.app_context():
            token = create_access_token(identity=str(user_id))
        return {"Authorization": f"Bearer {token}"}, user_id

    return _auth_headers
