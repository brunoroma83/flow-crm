"""Testes para autenticação e permissões do perfil Agente_IA e API Keys."""

from starlette.testclient import TestClient

from flow_crm.main import app
from flow_crm.models import UserRole


def run_tests():
    client = TestClient(app)

    print("1. Efetuando login como Administrador...")
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "bruuno@gmail.com", "password": "182436"},
    )
    assert login_resp.status_code == 200, f"Falha no login admin: {login_resp.text}"
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("   ✓ Login admin realizado com sucesso")

    print("2. Verificando existência do usuário 'Agente IA'...")
    users_resp = client.get("/api/users", headers=admin_headers)
    assert users_resp.status_code == 200
    users = users_resp.json()
    agent_user = next((u for u in users if u["role"] == "agent"), None)
    assert agent_user is not None, "Usuário do tipo 'agent' não encontrado"
    print(f"   ✓ Usuário Agente IA encontrado: {agent_user['name']} (ID {agent_user['id']})")

    print("3. Criando nova API Key vinculada ao Agente IA...")
    key_resp = client.post(
        "/api/api-keys",
        headers=admin_headers,
        json={"name": "Chave de Teste do Agente", "user_id": agent_user["id"]},
    )
    assert key_resp.status_code == 201, f"Erro ao criar API Key: {key_resp.text}"
    key_data = key_resp.json()
    raw_key = key_data["raw_key"]
    key_id = key_data["id"]
    assert raw_key.startswith("fc_live_"), f"Chave inválida: {raw_key}"
    print(f"   ✓ Chave criada com sucesso: prefixo={key_data['key_prefix']}, id={key_id}")

    agent_headers = {"X-API-Key": raw_key}

    print("4. Testando autenticação via X-API-Key (/api/auth/me)...")
    me_resp = client.get("/api/auth/me", headers=agent_headers)
    assert me_resp.status_code == 200, f"Falha na autenticação da API Key: {me_resp.text}"
    me = me_resp.json()
    assert me["id"] == agent_user["id"]
    assert me["role"] == "agent"
    print(f"   ✓ Autenticação OK: identificado como {me['name']} (perfil {me['role']})")

    print("5. Testando autenticação via Authorization: Bearer fc_live_...")
    bearer_headers = {"Authorization": f"Bearer {raw_key}"}
    bearer_resp = client.get("/api/auth/me", headers=bearer_headers)
    assert bearer_resp.status_code == 200
    assert bearer_resp.json()["id"] == agent_user["id"]
    print("   ✓ Autenticação via Authorization: Bearer fc_live_... OK")

    print("6. Testando consulta ao Dashboard pelo Agente...")
    dash_resp = client.get("/api/dashboard", headers=agent_headers)
    assert dash_resp.status_code == 200
    print(f"   ✓ Dashboard consultado com sucesso: {dash_resp.json().keys()}")

    print("7. Criando nova tarefa através do Agente...")
    create_task_resp = client.post(
        "/api/tasks",
        headers=agent_headers,
        json={
            "title": "Tarefa Criada pelo Agente IA",
            "priority": "high",
            "status": "todo",
        },
    )
    assert create_task_resp.status_code == 201, f"Erro ao criar tarefa: {create_task_resp.text}"
    created_task = create_task_resp.json()
    task_id = created_task["id"]
    assert created_task["created_by_id"] == agent_user["id"]
    print(f"   ✓ Tarefa criada (ID {task_id}) com created_by_id = {created_task['created_by_id']}")

    print("8. Testando permissão de exclusão da própria tarefa pelo Agente...")
    del_task_resp = client.delete(f"/api/tasks/{task_id}", headers=agent_headers)
    assert del_task_resp.status_code == 204, f"Falha ao excluir própria tarefa: {del_task_resp.status_code}"
    print("   ✓ Exclusão de item próprio permitida com sucesso")

    print("9. Testando restrição: Agente tentando excluir item de outro usuário...")
    # Admin cria uma tarefa
    admin_task_resp = client.post(
        "/api/tasks",
        headers=admin_headers,
        json={"title": "Tarefa do Admin", "priority": "low", "status": "todo"},
    )
    assert admin_task_resp.status_code == 201
    admin_task_id = admin_task_resp.json()["id"]

    # Agente tenta excluir tarefa do admin -> deve receber 403 Forbidden!
    unauth_del = client.delete(f"/api/tasks/{admin_task_id}", headers=agent_headers)
    assert unauth_del.status_code == 403, f"Deveria retornar 403, recebeu: {unauth_del.status_code}"
    print(f"   ✓ Bloqueio confirmado: agente não pôde excluir item de outro usuário (status {unauth_del.status_code})")

    print("10. Testando restrição: Agente tentando acessar gerenciamento de usuários (/api/users)...")
    forbidden_users_resp = client.get("/api/users", headers=agent_headers)
    assert forbidden_users_resp.status_code == 403
    print("   ✓ Bloqueio confirmado: agente proibido de acessar /api/users (status 403)")

    print("11. Revogando a API Key e testando se o acesso é bloqueado...")
    del_key_resp = client.delete(f"/api/api-keys/{key_id}", headers=admin_headers)
    assert del_key_resp.status_code == 204

    revoked_resp = client.get("/api/auth/me", headers=agent_headers)
    assert revoked_resp.status_code == 401, f"Deveria retornar 401 para chave revogada, recebeu {revoked_resp.status_code}"
    print("   ✓ Chave revogada bloqueada imediatamente com status 401")

    print("\nTODOS OS TESTES DE API KEYS E PERFIL AGENTE PASSARAM COM SUCESSO! 🎉")


if __name__ == "__main__":
    run_tests()
