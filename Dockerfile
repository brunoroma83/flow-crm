FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_COMPILE_BYTECODE=1
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.12.0 /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
# As fontes ainda não foram copiadas: instala somente as dependências para
# aproveitar o cache desta camada durante o desenvolvimento.
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
# Instala o pacote local depois que src/ estiver disponível.
RUN uv sync --frozen --no-dev
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "flow_crm.main:app", "--host", "0.0.0.0", "--port", "8000"]
