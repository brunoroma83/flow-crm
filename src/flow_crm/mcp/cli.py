import asyncio
from .server import create_mcp_server


def main():
    """Entrypoint para execução do servidor MCP em modo STDIO (linha de comando)."""
    server = create_mcp_server()
    asyncio.run(server.run_stdio_async())


if __name__ == "__main__":
    main()
