import contextvars
from sqlalchemy import select
from sqlalchemy.orm import Session

from flow_crm.models import User, UserRole

current_mcp_user_id: contextvars.ContextVar[int | None] = contextvars.ContextVar("current_mcp_user_id", default=None)


def get_current_actor(db: Session) -> User:
    """Retorna o usuário autenticado na requisição MCP ou o usuário padrão 'Agente IA'."""
    user_id = current_mcp_user_id.get()
    if user_id:
        user = db.get(User, user_id)
        if user and user.is_active and not user.is_deleted:
            return user

    # Fallback para o usuário agente padrão
    agent_user = db.scalar(
        select(User).where(User.role == UserRole.agent, User.is_deleted.is_(False))
    )
    if not agent_user:
        # Se não encontrar, tenta qualquer admin
        agent_user = db.scalar(
            select(User).where(User.role == UserRole.admin, User.is_deleted.is_(False))
        )
    if not agent_user:
        raise RuntimeError("Nenhum usuário disponível para atribuir a ação do agente.")
    return agent_user
