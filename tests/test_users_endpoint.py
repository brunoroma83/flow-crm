from starlette.testclient import TestClient
from sqlalchemy import select

from flow_crm.database import SessionLocal, ensure_schema
from flow_crm.models import User
from flow_crm.main import app, create_token


def test_users_list_endpoint():
    ensure_schema()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.is_deleted.is_(False)))
        user_id = user.id

    client = TestClient(app)
    token = create_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/api/users", headers=headers)
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)
    assert len(users) > 0
    ids = [u["id"] for u in users]
    assert user_id in ids
