"""Pacote MCP (Model Context Protocol) para integração com agentes de IA."""

from .server import create_mcp_app, create_mcp_server

__all__ = ["create_mcp_app", "create_mcp_server"]
