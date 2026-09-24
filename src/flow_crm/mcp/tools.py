from datetime import date, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from flow_crm.database import SessionLocal
from flow_crm.models import (
    Client,
    ClientStatus,
    Contact,
    Meeting,
    Priority,
    Project,
    ProjectStatus,
    Task,
    TaskStatus,
    UserRole,
)
from .context import get_current_actor


def get_dashboard() -> dict[str, Any]:
    """Retorna uma visão geral dos principais indicadores do FlowCRM:
    clientes ativos, projetos em andamento, tarefas para hoje e reuniões agendadas.
    """
    today = date.today()
    with SessionLocal() as db:
        active_clients = db.scalar(
            select(func.count()).select_from(Client).where(
                Client.status == ClientStatus.active, Client.is_deleted.is_(False)
            )
        )
        active_projects = db.scalar(
            select(func.count()).select_from(Project).where(
                Project.status == ProjectStatus.active, Project.is_deleted.is_(False)
            )
        )
        tasks_today = db.scalar(
            select(func.count()).select_from(Task).where(
                Task.due_date == today,
                Task.status != TaskStatus.done,
                Task.is_deleted.is_(False),
            )
        )
        meetings_today = db.scalar(
            select(func.count()).select_from(Meeting).where(
                func.date(Meeting.starts_at) == today,
                Meeting.is_deleted.is_(False),
            )
        )
        total_value = db.scalar(
            select(func.coalesce(func.sum(Client.monthly_value), 0)).where(
                Client.status == ClientStatus.active, Client.is_deleted.is_(False)
            )
        )

        return {
            "clientes_ativos": active_clients or 0,
            "projetos_ativos": active_projects or 0,
            "tarefas_pendentes_hoje": tasks_today or 0,
            "reunioes_hoje": meetings_today or 0,
            "receita_recorrente_mensal": float(total_value or 0),
        }


def list_clients(status: str | None = None, search: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    """Lista empresas clientes cadastradas no CRM.
    
    Args:
        status: Filtro opcional por status ('active', 'prospect', 'inactive').
        search: Termo de busca opcional pelo nome da empresa.
        limit: Quantidade máxima de registros a retornar (padrão: 50).
    """
    with SessionLocal() as db:
        stmt = select(Client).where(Client.is_deleted.is_(False))
        if status:
            try:
                stmt = stmt.where(Client.status == ClientStatus(status.lower()))
            except ValueError:
                pass
        if search:
            stmt = stmt.where(Client.name.ilike(f"%{search.strip()}%"))

        stmt = stmt.order_by(Client.name.asc()).limit(limit)
        clients = db.scalars(stmt).all()

        return [
            {
                "id": c.id,
                "name": c.name,
                "industry": c.industry,
                "status": c.status.value,
                "health_score": c.health_score,
                "monthly_value": float(c.monthly_value or 0),
            }
            for c in clients
        ]


def get_client_details(client_id: int) -> dict[str, Any]:
    """Retorna detalhes completos de um cliente específico, incluindo contatos, projetos e reuniões.
    
    Args:
        client_id: ID do cliente no CRM.
    """
    with SessionLocal() as db:
        client = db.scalar(
            select(Client)
            .options(
                selectinload(Client.contacts),
                selectinload(Client.projects),
                selectinload(Client.meetings),
            )
            .where(Client.id == client_id, Client.is_deleted.is_(False))
        )
        if not client:
            return {"error": f"Cliente com ID {client_id} não encontrado."}

        return {
            "id": client.id,
            "name": client.name,
            "industry": client.industry,
            "status": client.status.value,
            "health_score": client.health_score,
            "monthly_value": float(client.monthly_value or 0),
            "contacts": [
                {"id": ct.id, "name": ct.name, "email": ct.email, "phone": ct.phone, "role": ct.role}
                for ct in client.contacts if not ct.is_deleted
            ],
            "projects": [
                {"id": p.id, "name": p.name, "status": p.status.value, "due_date": p.due_date.isoformat() if p.due_date else None}
                for p in client.projects if not p.is_deleted
            ],
            "meetings": [
                {"id": m.id, "title": m.title, "starts_at": m.starts_at.isoformat(), "notes": m.notes}
                for m in client.meetings if not m.is_deleted
            ],
        }


def create_client(
    name: str,
    industry: str | None = None,
    status: str = "prospect",
    health_score: int = 100,
    monthly_value: float | None = None,
) -> dict[str, Any]:
    """Cadastra um novo cliente no CRM.
    
    Args:
        name: Razão social ou nome da empresa.
        industry: Setor de atuação (ex: 'Tecnologia', 'Saúde', 'Financeiro').
        status: Estado comercial ('prospect', 'active', 'inactive'). Padrão: 'prospect'.
        health_score: Índice de saúde de 0 a 100. Padrão: 100.
        monthly_value: Valor recorrente mensal em R$.
    """
    with SessionLocal() as db:
        actor = get_current_actor(db)
        try:
            client_status = ClientStatus(status.lower())
        except ValueError:
            client_status = ClientStatus.prospect

        # Verifica se já existe cliente com esse nome
        existing = db.scalar(select(Client).where(Client.name.ilike(name.strip()), Client.is_deleted.is_(False)))
        if existing:
            return {"error": f"Já existe um cliente cadastrado com o nome '{name}' (ID {existing.id})."}

        client = Client(
            name=name.strip(),
            industry=industry.strip() if industry else None,
            status=client_status,
            health_score=max(0, min(100, health_score)),
            monthly_value=Decimal(str(monthly_value)) if monthly_value is not None else None,
            created_by_id=actor.id,
        )
        db.add(client)
        db.commit()
        db.refresh(client)

        return {
            "success": True,
            "id": client.id,
            "name": client.name,
            "status": client.status.value,
            "created_by_id": client.created_by_id,
            "message": f"Cliente '{client.name}' criado com sucesso.",
        }


def list_tasks(
    project_id: int | None = None,
    status: str | None = None,
    priority: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Lista tarefas pendentes ou em andamento no CRM com filtros opcionais.
    
    Args:
        project_id: ID do projeto para filtrar (opcional).
        status: Filtro por status ('todo', 'in_progress', 'done').
        priority: Filtro por prioridade ('low', 'medium', 'high').
        limit: Máximo de registros a retornar (padrão: 50).
    """
    with SessionLocal() as db:
        stmt = (
            select(Task)
            .options(selectinload(Task.project))
            .where(Task.is_deleted.is_(False))
        )
        if project_id:
            stmt = stmt.where(Task.project_id == project_id)
        if status:
            try:
                stmt = stmt.where(Task.status == TaskStatus(status.lower()))
            except ValueError:
                pass
        if priority:
            try:
                stmt = stmt.where(Task.priority == Priority(priority.lower()))
            except ValueError:
                pass

        stmt = stmt.order_by(Task.due_date.asc().nulls_last(), Task.id.desc()).limit(limit)
        tasks = db.scalars(stmt).all()

        return [
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "status": t.status.value,
                "priority": t.priority.value,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "project_id": t.project_id,
                "project_name": t.project.name if t.project else None,
                "created_by_id": t.created_by_id,
            }
            for t in tasks
        ]


def create_task(
    title: str,
    description: str | None = None,
    project_id: int | None = None,
    priority: str = "medium",
    due_date: str | None = None,
    status: str = "todo",
) -> dict[str, Any]:
    """Cria uma nova tarefa no FlowCRM.
    
    Args:
        title: Título descritivo da tarefa.
        description: Detalhes ou orientações adicionais.
        project_id: ID do projeto vinculado (opcional).
        priority: Nível de prioridade ('low', 'medium', 'high'). Padrão: 'medium'.
        due_date: Data de entrega no formato AAAA-MM-DD (ex: '2026-10-15').
        status: Estado inicial ('todo', 'in_progress', 'done'). Padrão: 'todo'.
    """
    with SessionLocal() as db:
        actor = get_current_actor(db)
        try:
            task_status = TaskStatus(status.lower())
        except ValueError:
            task_status = TaskStatus.todo

        try:
            task_priority = Priority(priority.lower())
        except ValueError:
            task_priority = Priority.medium

        parsed_date = None
        if due_date:
            try:
                parsed_date = date.fromisoformat(due_date.strip())
            except ValueError:
                return {"error": f"Formato de data inválido: '{due_date}'. Use AAAA-MM-DD."}

        if project_id:
            project = db.get(Project, project_id)
            if not project or project.is_deleted:
                return {"error": f"Projeto com ID {project_id} não existe."}

        task = Task(
            title=title.strip(),
            description=description.strip() if description else None,
            project_id=project_id,
            priority=task_priority,
            status=task_status,
            due_date=parsed_date,
            created_by_id=actor.id,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        return {
            "success": True,
            "id": task.id,
            "title": task.title,
            "status": task.status.value,
            "priority": task.priority.value,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "created_by_id": task.created_by_id,
            "message": f"Tarefa '{task.title}' criada com sucesso.",
        }


def update_task_status(task_id: int, status: str) -> dict[str, Any]:
    """Atualiza o status de uma tarefa no CRM.
    
    Args:
        task_id: ID da tarefa.
        status: Novo status ('todo', 'in_progress', 'done').
    """
    with SessionLocal() as db:
        task = db.get(Task, task_id)
        if not task or task.is_deleted:
            return {"error": f"Tarefa com ID {task_id} não encontrada."}

        try:
            new_status = TaskStatus(status.lower())
        except ValueError:
            return {"error": f"Status inválido: '{status}'. Opções válidas: 'todo', 'in_progress', 'done'."}

        task.status = new_status
        db.commit()
        return {
            "success": True,
            "id": task.id,
            "title": task.title,
            "new_status": task.status.value,
            "message": f"Status da tarefa '{task.title}' atualizado para '{task.status.value}'.",
        }


def delete_task(task_id: int) -> dict[str, Any]:
    """Exclui uma tarefa do CRM.
    
    Regra de permissão: Administradores podem excluir qualquer tarefa.
    Usuários com perfil Agente_IA ou Membro só podem excluir tarefas criadas por si mesmos.
    
    Args:
        task_id: ID da tarefa a ser excluída.
    """
    with SessionLocal() as db:
        actor = get_current_actor(db)
        task = db.get(Task, task_id)
        if not task or task.is_deleted:
            return {"error": f"Tarefa com ID {task_id} não encontrada."}

        if actor.role != UserRole.admin and task.created_by_id != actor.id:
            return {
                "error": "Permissão negada: o perfil Agente_IA só pode excluir itens criados por si mesmo.",
                "created_by_id": task.created_by_id,
                "current_actor_id": actor.id,
            }

        task.is_deleted = True
        db.commit()
        return {
            "success": True,
            "message": f"Tarefa ID {task_id} ('{task.title}') excluída com sucesso.",
        }


def schedule_meeting(
    title: str,
    starts_at: str,
    duration_minutes: int = 30,
    client_id: int | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Agenda uma reunião vinculada a um cliente.
    
    Args:
        title: Assunto ou pauta da reunião.
        starts_at: Data e hora de início no formato ISO (ex: '2026-10-15T14:30:00').
        duration_minutes: Duração em minutos (padrão: 30).
        client_id: ID do cliente participante (opcional).
        notes: Notas prévias ou link da reunião.
    """
    with SessionLocal() as db:
        actor = get_current_actor(db)
        try:
            start_dt = datetime.fromisoformat(starts_at.strip())
        except ValueError:
            return {"error": f"Formato de data/hora inválido: '{starts_at}'. Use ISO 8601 (ex: 2026-10-15T14:00:00)."}

        if client_id:
            client = db.get(Client, client_id)
            if not client or client.is_deleted:
                return {"error": f"Cliente ID {client_id} não encontrado."}

        meeting = Meeting(
            title=title.strip(),
            starts_at=start_dt,
            duration_minutes=duration_minutes,
            client_id=client_id,
            notes=notes.strip() if notes else None,
            created_by_id=actor.id,
        )
        db.add(meeting)
        db.commit()
        db.refresh(meeting)

        return {
            "success": True,
            "id": meeting.id,
            "title": meeting.title,
            "starts_at": meeting.starts_at.isoformat(),
            "duration_minutes": meeting.duration_minutes,
            "created_by_id": meeting.created_by_id,
            "message": f"Reunião '{meeting.title}' agendada com sucesso.",
        }


def add_contact(
    client_id: int,
    name: str,
    email: str,
    phone: str | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    """Adiciona um novo contato vinculado a uma empresa cliente.
    
    Args:
        client_id: ID do cliente no CRM.
        name: Nome completo do contato.
        email: E-mail profissional.
        phone: Telefone ou WhatsApp (opcional).
        role: Cargo ou departamento (ex: 'Diretor Comercial', 'Gerente de TI').
    """
    with SessionLocal() as db:
        actor = get_current_actor(db)
        client = db.get(Client, client_id)
        if not client or client.is_deleted:
            return {"error": f"Cliente ID {client_id} não encontrado."}

        contact = Contact(
            name=name.strip(),
            email=email.strip().lower(),
            phone=phone.strip() if phone else None,
            role=role.strip() if role else None,
            client_id=client_id,
            created_by_id=actor.id,
        )
        db.add(contact)
        db.commit()
        db.refresh(contact)

        return {
            "success": True,
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "client_name": client.name,
            "created_by_id": contact.created_by_id,
            "message": f"Contato '{contact.name}' adicionado à empresa '{client.name}'.",
        }
