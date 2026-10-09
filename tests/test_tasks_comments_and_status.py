import uuid
from datetime import datetime
from starlette.testclient import TestClient
from sqlalchemy import select

from flow_crm.database import SessionLocal, ensure_schema
from flow_crm.models import Client, Project, Task, TaskComment, TaskStatus, User
from flow_crm.main import app, create_token
from flow_crm.mcp import tools
from flow_crm.mcp.context import current_mcp_user_id


def setup_data():
    ensure_schema()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.is_deleted.is_(False)))
        client = db.scalar(select(Client).where(Client.is_deleted.is_(False)))
        project = db.scalar(select(Project).where(Project.client_id == client.id, Project.is_deleted.is_(False)))
        return user.id, client.id, project.id


def test_task_status_waiting_feedback():
    user_id, client_id, project_id = setup_data()
    client = TestClient(app)
    token = create_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}

    uid = uuid.uuid4().hex[:6]
    title = f"Tarefa Aguardando Retorno {uid}"

    # 1. Criação direta com status waiting_feedback
    resp = client.post(
        "/api/tasks",
        json={
            "title": title,
            "description": "Teste status aguardando retorno",
            "status": "waiting_feedback",
            "priority": "medium",
            "project_id": project_id,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    task_data = resp.json()
    assert task_data["status"] == "waiting_feedback"
    task_id = task_data["id"]

    # 2. Transição via endpoint PATCH /status
    resp_patch = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"status": "in_progress"},
        headers=headers,
    )
    assert resp_patch.status_code == 200
    assert resp_patch.json()["status"] == "in_progress"

    # 3. Retorno para waiting_feedback via PATCH
    resp_patch2 = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"status": "waiting_feedback"},
        headers=headers,
    )
    assert resp_patch2.status_code == 200
    assert resp_patch2.json()["status"] == "waiting_feedback"

    # 4. Transição para done
    resp_patch3 = client.patch(
        f"/api/tasks/{task_id}/status",
        json={"status": "done"},
        headers=headers,
    )
    assert resp_patch3.status_code == 200
    assert resp_patch3.json()["status"] == "done"


def test_task_comments_lifecycle():
    user_id, client_id, project_id = setup_data()
    client = TestClient(app)
    token = create_token(user_id)
    headers = {"Authorization": f"Bearer {token}"}

    uid = uuid.uuid4().hex[:6]
    title = f"Tarefa com Comentários {uid}"

    resp_task = client.post(
        "/api/tasks",
        json={
            "title": title,
            "status": "todo",
            "priority": "high",
            "project_id": project_id,
        },
        headers=headers,
    )
    assert resp_task.status_code == 201
    task_id = resp_task.json()["id"]

    # 1. Inclusão de comentário com data padrão (now)
    resp_c1 = client.post(
        f"/api/tasks/{task_id}/comments",
        json={"content": "Primeira observação: cliente contactado."},
        headers=headers,
    )
    assert resp_c1.status_code == 201
    c1_data = resp_c1.json()
    assert c1_data["content"] == "Primeira observação: cliente contactado."
    assert c1_data["task_id"] == task_id
    assert c1_data["created_by_id"] == user_id
    assert c1_data["observation_date"] is not None
    c1_id = c1_data["id"]

    # 2. Inclusão de comentário com data retroativa de observação
    obs_date_iso = "2026-10-01T10:00:00"
    resp_c2 = client.post(
        f"/api/tasks/{task_id}/comments",
        json={
            "content": "Reunião de alinhamento com feedback inicial.",
            "observation_date": obs_date_iso,
        },
        headers=headers,
    )
    assert resp_c2.status_code == 201
    c2_data = resp_c2.json()
    assert c2_data["content"] == "Reunião de alinhamento com feedback inicial."
    c2_id = c2_data["id"]

    # 3. Listar comentários da tarefa via GET /api/tasks/{task_id}/comments
    resp_list = client.get(f"/api/tasks/{task_id}/comments", headers=headers)
    assert resp_list.status_code == 200
    comments = resp_list.json()
    assert len(comments) == 2
    # Ordenado por observation_date desc (c1 é mais recente que 2026-10-01)
    assert comments[0]["id"] == c1_id
    assert comments[1]["id"] == c2_id

    # 4. Listar tarefas gerais e checar comments_count
    resp_tasks = client.get("/api/tasks", headers=headers)
    assert resp_tasks.status_code == 200
    matching = [t for t in resp_tasks.json() if t["id"] == task_id]
    assert len(matching) == 1
    assert matching[0]["comments_count"] == 2
    assert len(matching[0]["comments"]) == 2

    # 5. Excluir o primeiro comentário via DELETE
    resp_del = client.delete(f"/api/tasks/{task_id}/comments/{c1_id}", headers=headers)
    assert resp_del.status_code == 204

    # 6. Listar novamente e verificar que só resta 1 comentário
    resp_list2 = client.get(f"/api/tasks/{task_id}/comments", headers=headers)
    assert resp_list2.status_code == 200
    comments2 = resp_list2.json()
    assert len(comments2) == 1
    assert comments2[0]["id"] == c2_id


def test_mcp_task_comments_and_waiting_status():
    user_id, client_id, project_id = setup_data()
    token = current_mcp_user_id.set(user_id)

    try:
        uid = uuid.uuid4().hex[:6]
        # 1. Criar tarefa via MCP
        res_create = tools.create_task(
            title=f"Tarefa MCP {uid}",
            status="todo",
            priority="medium",
            project_id=project_id,
        )
        assert res_create["success"] is True
        task_id = res_create["id"]

        # 2. Atualizar status para waiting_feedback via MCP
        res_update = tools.update_task_status(task_id=task_id, status="waiting_feedback")
        assert res_update["success"] is True
        assert res_update["new_status"] == "waiting_feedback"

        # 3. Adicionar comentário via MCP tool add_task_comment
        res_comment = tools.add_task_comment(
            task_id=task_id,
            content="Aguardando retorno do cliente sobre os arquivos de design.",
            observation_date="2026-10-09T11:00:00",
        )
        assert res_comment["success"] is True
        assert res_comment["task_id"] == task_id
        assert res_comment["comment_id"] is not None

        # 4. Listar comentários via MCP tool list_task_comments
        res_list = tools.list_task_comments(task_id=task_id)
        assert res_list["task_id"] == task_id
        assert res_list["comments_count"] == 1
        assert res_list["comments"][0]["content"] == "Aguardando retorno do cliente sobre os arquivos de design."

        # 5. Listar tarefas filtradas por status waiting_feedback
        tasks_waiting = tools.list_tasks(status="waiting_feedback")
        ids = [t["id"] for t in tasks_waiting]
        assert task_id in ids
        task_item = next(t for t in tasks_waiting if t["id"] == task_id)
        assert task_item["comments_count"] >= 1

        # 6. MCP dashboard deve contar waiting_feedback como tarefa pendente
        dash = tools.get_dashboard()
        assert dash["visao_geral_ano"]["tarefas"]["nao_finalizadas"] >= 1
    finally:
        current_mcp_user_id.reset(token)
