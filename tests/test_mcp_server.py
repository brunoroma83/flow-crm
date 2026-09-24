"""Testes de integração para o Servidor MCP (Tools, Resources e Autenticação SSE)."""

import asyncio
import json
from sqlalchemy import select
from starlette.testclient import TestClient

from flow_crm.database import SessionLocal
from flow_crm.main import app
from flow_crm.mcp.context import current_mcp_user_id
from flow_crm.mcp.server import create_mcp_server
from flow_crm.models import Task, User, UserRole
from flow_crm.security import generate_api_key
from flow_crm.models import ApiKey


def run_tests():
    print("=== INICIANDO TESTES DO SERVIDOR MCP ===")
    client = TestClient(app)

    # 1. Configurar usuário Agente e gerar API Key de teste
    with SessionLocal() as db:
        agent_user = db.scalar(select(User).where(User.role == UserRole.agent, User.is_deleted.is_(False)))
        assert agent_user is not None, "Usuário Agente não encontrado"
        agent_id = agent_user.id

        admin_user = db.scalar(select(User).where(User.role == UserRole.admin, User.is_deleted.is_(False)))
        assert admin_user is not None, "Usuário Admin não encontrado"
        admin_id = admin_user.id

        raw_key, prefix, hashed = generate_api_key()
        api_key_record = ApiKey(
            name="MCP Test Key",
            key_prefix=prefix,
            hashed_key=hashed,
            user_id=agent_id,
            is_active=True,
        )
        db.add(api_key_record)
        db.commit()
        db.refresh(api_key_record)
        key_id = api_key_record.id

    print(f"1. Chave de teste criada: {prefix} (vinculada ao Agente ID {agent_id})")

    # 2. Testar proteção de rota SSE
    print("2. Testando bloqueio sem API Key em /mcp/sse...")
    unauth_resp = client.get("/mcp/sse")
    assert unauth_resp.status_code == 401, f"Deveria retornar 401, recebeu {unauth_resp.status_code}"
    print("   ✓ Bloqueio confirmado para requisições sem autenticação (401)")

    print("3. Testando bloqueio com chave inválida...")
    invalid_resp = client.get("/mcp/sse", headers={"X-API-Key": "fc_live_invalidkey123456789"})
    assert invalid_resp.status_code == 401
    print("   ✓ Bloqueio confirmado para chave inválida (401)")

    import urllib.request

    # 3. Testar conexão com query param ?api_key=
    print("4. Testando conexão em /mcp/sse com query param ?api_key=...")
    with urllib.request.urlopen(f"http://127.0.0.1:8000/mcp/sse?api_key={raw_key}") as resp:
        assert resp.status == 200
        assert "text/event-stream" in resp.headers.get("Content-Type", "")
        print("   ✓ Conexão SSE estabelecida com sucesso via ?api_key=")

    # 4. Testar conexão com header X-API-Key
    print("5. Testando conexão em /mcp/sse com header X-API-Key...")
    req = urllib.request.Request("http://127.0.0.1:8000/mcp/sse", headers={"X-API-Key": raw_key})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200
        assert "text/event-stream" in resp.headers.get("Content-Type", "")
        print("   ✓ Header X-API-Key aceito com sucesso pelo SSE")

    # 5. Testar execução de ferramentas (Tools) do MCP
    print("6. Testando execução direta das ferramentas do MCP...")
    mcp_server = create_mcp_server()

    # Define o contexto do agente para a execução
    token = current_mcp_user_id.set(agent_id)
    try:
        import secrets
        unique_client_name = f"Alpha Corp {secrets.token_hex(4)}"
        unique_task_title = f"Tarefa Alpha {secrets.token_hex(4)}"

        # Tool: get_dashboard
        dash_result = asyncio.run(mcp_server.call_tool("get_dashboard", {}))
        assert not dash_result.is_error
        print(f"   ✓ Tool get_dashboard executada com sucesso")

        # Tool: create_client
        client_result = asyncio.run(
            mcp_server.call_tool(
                "create_client",
                {
                    "name": unique_client_name,
                    "industry": "Logística e Transportes",
                    "status": "prospect",
                    "health_score": 90,
                    "monthly_value": 12500.0,
                },
            )
        )
        assert not client_result.is_error
        print(f"   ✓ Tool create_client executada com sucesso")

        # Tool: list_clients
        list_result = asyncio.run(mcp_server.call_tool("list_clients", {"search": unique_client_name}))
        assert not list_result.is_error
        clients_found = list_result.structured_content.get("result", [])
        assert len(clients_found) > 0
        print(f"   ✓ Tool list_clients executada: {len(clients_found)} cliente(s) encontrado(s)")

        # Obter ID do cliente criado
        with SessionLocal() as db:
            from flow_crm.models import Client
            created_c = db.scalar(select(Client).where(Client.name == unique_client_name))
            assert created_c is not None
            c_id = created_c.id
            assert created_c.created_by_id == agent_id
            print(f"   ✓ Cliente persistido no DB com created_by_id = {created_c.created_by_id} (Agente IA)")

        # Tool: add_contact
        contact_result = asyncio.run(
            mcp_server.call_tool(
                "add_contact",
                {
                    "client_id": c_id,
                    "name": "Carlos Eduardo",
                    "email": f"carlos_{secrets.token_hex(3)}@alphacorp.example",
                    "role": "Gerente de Operações",
                },
            )
        )
        assert not contact_result.is_error
        print(f"   ✓ Tool add_contact executada com sucesso")

        # Tool: schedule_meeting
        meeting_result = asyncio.run(
            mcp_server.call_tool(
                "schedule_meeting",
                {
                    "client_id": c_id,
                    "title": "Apresentação de Diagnóstico",
                    "starts_at": "2026-10-20T15:00:00",
                    "duration_minutes": 45,
                    "notes": "Alinhar escopo de integração",
                },
            )
        )
        assert not meeting_result.is_error
        print(f"   ✓ Tool schedule_meeting executada com sucesso")

        # Tool: get_client_details
        details_result = asyncio.run(mcp_server.call_tool("get_client_details", {"client_id": c_id}))
        assert not details_result.is_error
        print(f"   ✓ Tool get_client_details executada com sucesso")

        # Tool: create_task
        task_result = asyncio.run(
            mcp_server.call_tool(
                "create_task",
                {
                    "title": unique_task_title,
                    "priority": "high",
                    "status": "todo",
                    "due_date": "2026-10-25",
                },
            )
        )
        assert not task_result.is_error
        print(f"   ✓ Tool create_task executada com sucesso")

        with SessionLocal() as db:
            agent_task = db.scalar(
                select(Task).where(Task.title == unique_task_title, Task.is_deleted.is_(False))
            )
            assert agent_task is not None
            agent_task_id = agent_task.id
            assert agent_task.created_by_id == agent_id

        # Tool: update_task_status
        update_result = asyncio.run(
            mcp_server.call_tool("update_task_status", {"task_id": agent_task_id, "status": "in_progress"})
        )
        assert not update_result.is_error
        print(f"   ✓ Tool update_task_status executada com sucesso")

        # Tool: delete_task (própria) -> deve permitir
        del_result = asyncio.run(mcp_server.call_tool("delete_task", {"task_id": agent_task_id}))
        assert not del_result.is_error
        print(f"   ✓ Tool delete_task (tarefa própria) executada com sucesso")

        # Tool: delete_task em tarefa do admin -> deve bloquear!
        with SessionLocal() as db:
            admin_task = Task(title="Tarefa Privada do Admin", created_by_id=admin_id)
            db.add(admin_task)
            db.commit()
            db.refresh(admin_task)
            adm_task_id = admin_task.id

        blocked_del_result = asyncio.run(mcp_server.call_tool("delete_task", {"task_id": adm_task_id}))
        res_str = str(blocked_del_result)
        assert "Permissão negada" in res_str or "error" in res_str
        print(f"   ✓ Bloqueio confirmado em delete_task de item de outro autor: {res_str}")

        # 6. Testar Resources do MCP
        print("7. Testando leitura de recursos (Resources) do MCP...")
        dash_res_data = asyncio.run(mcp_server.read_resource("crm://dashboard"))
        assert dash_res_data is not None and len(dash_res_data) > 0
        print("   ✓ Recurso crm://dashboard lido com sucesso")

        clients_res_data = asyncio.run(mcp_server.read_resource("crm://clients/active"))
        assert clients_res_data is not None and len(clients_res_data) > 0
        print("   ✓ Recurso crm://clients/active lido com sucesso")

    finally:
        current_mcp_user_id.reset(token)

    # 7. Limpeza: revogar chave de teste
    with SessionLocal() as db:
        k = db.get(ApiKey, key_id)
        if k:
            k.is_deleted = True
            db.commit()

    print("\nTODOS OS TESTES DO SERVIDOR MCP PASSARAM COM 100% DE SUCESSO! 🚀")


if __name__ == "__main__":
    run_tests()
