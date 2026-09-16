
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
