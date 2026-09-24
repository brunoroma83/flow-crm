import json
from datetime import datetime
from typing import Any

from mcp.server.mcpserver import MCPServer
from sqlalchemy import select
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from flow_crm.database import SessionLocal
from flow_crm.models import ApiKey, User
from flow_crm.security import hash_api_key
from .context import current_mcp_user_id
from . import tools


class MCPAuthMiddleware:
    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        # Permite requisições preflight OPTIONS (CORS)
        if request.method == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # 1. Extração do token: Header X-API-Key, Authorization: Bearer, ou Query Param api_key
        api_token = request.headers.get("x-api-key")
        if not api_token:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                candidate = auth_header.removeprefix("Bearer ").strip()
                if candidate.startswith("fc_live_"):
                    api_token = candidate

        if not api_token:
            api_token = request.query_params.get("api_key")

        if not api_token:
            response = JSONResponse(
                {
                    "detail": "Autenticação MCP necessária. Forneça a chave via cabeçalho X-API-Key, Bearer ou query param ?api_key="
                },
                status_code=401,
            )
            await response(scope, receive, send)
            return

        hashed = hash_api_key(api_token)
        with SessionLocal() as db:
            key_record = db.scalar(
                select(ApiKey).where(
                    ApiKey.hashed_key == hashed,
                    ApiKey.is_active.is_(True),
                    ApiKey.is_deleted.is_(False),
                )
            )
            if not key_record:
                response = JSONResponse({"detail": "API Key inválida ou inativa"}, status_code=401)
                await response(scope, receive, send)
                return
            if key_record.expires_at and key_record.expires_at < datetime.now():
                response = JSONResponse({"detail": "API Key expirada"}, status_code=401)
                await response(scope, receive, send)
                return

            key_record.last_used_at = datetime.now()
            user_id = key_record.user_id
            db.commit()

            user = db.get(User, user_id)
            if not user or not user.is_active or user.is_deleted:
                response = JSONResponse({"detail": "Usuário associado à API Key está inativo"}, status_code=401)
                await response(scope, receive, send)
                return

        # Define contexto da requisição para que todas as tools saibam quem é o autor
        reset_token = current_mcp_user_id.set(user_id)
        try:
            await self.app(scope, receive, send)
        finally:
            current_mcp_user_id.reset(reset_token)




def create_mcp_server() -> MCPServer:
    """Instancia o MCPServer com todas as ferramentas e recursos do FlowCRM."""
    server = MCPServer("FlowCRM")

    # Registro das Ferramentas (Tools)
    server.add_tool(tools.get_dashboard)
    server.add_tool(tools.list_clients)
    server.add_tool(tools.get_client_details)
    server.add_tool(tools.create_client)
    server.add_tool(tools.list_tasks)
    server.add_tool(tools.create_task)
    server.add_tool(tools.update_task_status)
    server.add_tool(tools.delete_task)
    server.add_tool(tools.schedule_meeting)
    server.add_tool(tools.add_contact)

    # Registro de Recursos (Resources)
    @server.resource("crm://dashboard")
    def dashboard_resource() -> str:
        """Snapshot das métricas operacionais e financeiras em tempo real do CRM."""
        return json.dumps(tools.get_dashboard(), ensure_ascii=False)

    @server.resource("crm://clients/active")
    def active_clients_resource() -> str:
        """Lista rápida das empresas com status ativo no CRM."""
        return json.dumps(tools.list_clients(status="active"), ensure_ascii=False)

    return server


from mcp.server.transport_security import TransportSecuritySettings


def create_mcp_app() -> Starlette:
    """Cria a sub-aplicação Starlette para transporte SSE do MCP com middleware de autenticação."""
    mcp_server = create_mcp_server()
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
        allowed_hosts=["*"],
        allowed_origins=["*"],
    )
    app = mcp_server.sse_app(transport_security=security)
    app.add_middleware(MCPAuthMiddleware)
    return app

