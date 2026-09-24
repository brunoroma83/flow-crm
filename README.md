
# FlowCRM

CRM de operações B2B construído em Python 3.14, FastAPI e PostgreSQL. O FastAPI foi escolhido para manter API e interface no mesmo serviço, com documentação OpenAPI já disponível.

## Executar com Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Abra `http://localhost:8000`. A API interativa está em `http://localhost:8000/docs`.

## Desenvolvimento com Docker

Para vincular o código local ao container e habilitar recarga automática do Python:

```powershell
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

Após a primeira execução, alterações em `src/` são refletidas automaticamente. Se preferir reiniciar manualmente, `docker compose -f compose.yaml -f compose.dev.yaml restart app` também utilizará o código local montado.

## Acesso inicial

O primeiro administrador é criado automaticamente na inicialização:

- E-mail: `bruuno@gmail.com`
- Senha: `123456`

Altere a chave `SECRET_KEY` no `.env` antes de publicar a aplicação. Somente usuários com perfil de administrador podem criar, editar ou remover usuários.

## Desenvolvimento com UV

```powershell
uv sync
$env:DATABASE_URL = "postgresql+psycopg://flowcrm:flowcrm_dev_password@localhost:5433/flowcrm"
uv run uvicorn flow_crm.main:app --reload
```

Suba apenas o banco antes, se necessário: `docker compose up db -d`.

---

## Integração com Agentes de IA e Servidor MCP

O FlowCRM possui suporte nativo para integração com agentes de IA (como Claude Desktop, Antigravity, Cursor, LangChain e CrewAI) via **API Keys** e **Model Context Protocol (MCP)**.

### 1. Perfil `Agente_IA` e API Keys
- Usuários com o perfil `Agente IA` possuem permissão completa de **leitura** e **criação/edição** em todas as entidades.
- **Regra de exclusão**: agentes de IA só podem excluir registros criados por eles mesmos (`created_by_id`).
- Administradores podem gerar chaves seguras (`fc_live_...`) na interface web através da aba **Agentes & API Keys** ou via `POST /api/api-keys`.

### 2. Autenticação para Agentes
As requisições à API REST ou ao servidor MCP podem ser autenticadas de três formas:
- **Header:** `X-API-Key: fc_live_...`
- **Header:** `Authorization: Bearer fc_live_...`
- **Query Param (apenas MCP SSE):** `http://localhost:8000/mcp/sse?api_key=fc_live_...`

### 3. Servidor MCP Embutido (SSE)
O servidor MCP roda diretamente no serviço FastAPI e expõe ferramentas e recursos para clientes de IA:
- **Endpoint MCP (SSE):** `http://localhost:8000/mcp/sse`
- **Ferramentas disponíveis:**
  - `get_dashboard`: Indicadores gerais de operações e receita.
  - `list_clients`: Busca e listagem de empresas clientes.
  - `get_client_details`: Ficha completa do cliente com contatos, projetos e reuniões.
  - `create_client`: Cadastro de nova empresa.
  - `list_tasks`: Listagem de tarefas com filtros por status e prioridade.
  - `create_task`: Criação de tarefa atribuída ao agente.
  - `update_task_status`: Atualização de status da tarefa (`todo`, `in_progress`, `done`).
  - `delete_task`: Exclusão de tarefa (restrita a tarefas criadas pelo agente).
  - `schedule_meeting`: Agendamento de reunião com cliente.
  - `add_contact`: Cadastro de pessoa de contato.
- **Recursos em tempo real:**
  - `crm://dashboard`: JSON com o resumo do dia e métricas.
  - `crm://clients/active`: Lista rápida de contas ativas.

### 4. Conectar Agentes (Claude Desktop / Cursor / Antigravity)
Adicione ao seu arquivo de configuração de MCP (consulte o arquivo de exemplo `mcp_client_example.json`):

```json
{
  "mcpServers": {
    "flowcrm": {
      "url": "http://localhost:8000/mcp/sse",
      "headers": {
        "X-API-Key": "fc_live_sua_chave_aqui"
      }
    }
  }
}
```

### 5. Convenções de Desenvolvimento e Testes

- **Adicionar bibliotecas:** `uv add <nome_da_biblioteca>`
- **Executar testes de API Keys:**
  ```powershell
  docker compose exec app uv run python tests/test_agent_api_keys.py
  ```
- **Executar testes do Servidor MCP:**
  ```powershell
  docker compose exec app uv run python tests/test_mcp_server.py
  ```
- **Reiniciar o serviço:**
  ```powershell
  docker compose restart app
  ```
