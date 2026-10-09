from pathlib import Path
from unittest.mock import patch
from starlette.testclient import TestClient

from flow_crm.backup import (
    create_backup,
    delete_backup,
    list_backups,
    restore_backup,
    rotate_old_backups,
)
from flow_crm.main import app


def test_create_and_list_backup(tmp_path: Path):
    temp_backup_dir = tmp_path / "backups"
    temp_backup_dir.mkdir(parents=True, exist_ok=True)

    res = create_backup(label="test", custom_backup_dir=temp_backup_dir)
    assert res["status"] == "success"
    assert res["filename"].startswith("backup_test_")
    assert res["size_bytes"] > 0
    assert "checksum_sha256" in res

    backups = list_backups(custom_backup_dir=temp_backup_dir)
    assert len(backups) == 1
    assert backups[0]["filename"] == res["filename"]


def test_restore_backup_with_safety(tmp_path: Path):
    temp_backup_dir = tmp_path / "backups"
    temp_backup_dir.mkdir(parents=True, exist_ok=True)

    original = create_backup(label="original", custom_backup_dir=temp_backup_dir)

    res = restore_backup(
        filename=original["filename"],
        safety_snapshot=True,
        custom_backup_dir=temp_backup_dir,
    )
    assert res["status"] == "restored"
    assert res["filename"] == original["filename"]
    assert res["safety_snapshot"].startswith("backup_pre_restore_safety_")

    backups = list_backups(custom_backup_dir=temp_backup_dir)
    assert len(backups) == 2  # Original + safety snapshot


def test_delete_backup(tmp_path: Path):
    temp_backup_dir = tmp_path / "backups"
    temp_backup_dir.mkdir(parents=True, exist_ok=True)

    res = create_backup(label="to_delete", custom_backup_dir=temp_backup_dir)
    fname = res["filename"]

    assert len(list_backups(custom_backup_dir=temp_backup_dir)) == 1
    delete_backup(fname, custom_backup_dir=temp_backup_dir)
    assert len(list_backups(custom_backup_dir=temp_backup_dir)) == 0


def test_rotate_old_backups(tmp_path: Path):
    temp_backup_dir = tmp_path / "backups"
    temp_backup_dir.mkdir(parents=True, exist_ok=True)

    res = create_backup(label="old", custom_backup_dir=temp_backup_dir)
    fname = res["filename"]

    # Simula um backup antigo alterando a data no metadata
    meta_file = temp_backup_dir / "metadata.json"
    content = meta_file.read_text(encoding="utf-8")
    content = content.replace("2026-", "2020-")
    meta_file.write_text(content, encoding="utf-8")

    deleted = rotate_old_backups(retention_days=30, custom_backup_dir=temp_backup_dir)
    assert fname in deleted
    assert len(list_backups(custom_backup_dir=temp_backup_dir)) == 0


def test_backup_api_admin_only(tmp_path: Path):
    temp_backup_dir = tmp_path / "backups"
    temp_backup_dir.mkdir(parents=True, exist_ok=True)

    client = TestClient(app)

    # 1. Login como admin para obter token
    login_resp = client.post("/api/auth/login", json={"email": "bruuno@gmail.com", "password": "182436"})
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Requisitar sem token (401)
    resp = client.get("/api/v1/admin/backups")
    assert resp.status_code == 401

    with patch("flow_crm.main.get_backup_dir", return_value=temp_backup_dir), \
         patch("flow_crm.backup.get_backup_dir", return_value=temp_backup_dir):

        # 3. Admin lista backups
        resp = client.get("/api/v1/admin/backups", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

        # 4. Admin dispara backup manual
        resp = client.post(
            "/api/v1/admin/backups",
            json={"label": "api_test"},
            headers=admin_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        filename = data["filename"]

        # 5. Admin faz download
        resp = client.get(
            f"/api/v1/admin/backups/{filename}/download",
            headers=admin_headers,
        )
        assert resp.status_code == 200

        # 6. Admin restaura sem confirm=True (400)
        resp = client.post(
            f"/api/v1/admin/backups/{filename}/restore",
            json={"confirm": False},
            headers=admin_headers,
        )
        assert resp.status_code == 400

        # 7. Admin restaura com confirm=True (200)
        resp = client.post(
            f"/api/v1/admin/backups/{filename}/restore",
            json={"confirm": True, "safety_snapshot": True},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "restored"

        # 8. Admin deleta backup
        resp = client.delete(
            f"/api/v1/admin/backups/{filename}",
            headers=admin_headers,
        )
        assert resp.status_code == 204
