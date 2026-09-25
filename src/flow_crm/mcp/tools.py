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
    Invoice,
    InvoiceStatus,
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
                "cnpj": c.cnpj,
                "address": c.address,
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
            "cnpj": client.cnpj,
            "address": client.address,
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


def list_contacts(
    search: str | None = None,
    client_id: int | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Lista pessoas de contato cadastradas no CRM, com filtros opcionais por empresa ou busca por nome/email/cargo.
    
    Args:
        search: Termo de busca opcional (pesquisa no nome, e-mail, telefone ou cargo do contato).
        client_id: Filtro opcional por ID da empresa cliente.
        limit: Quantidade máxima de registros a retornar (padrão: 50).
    """
    with SessionLocal() as db:
        stmt = (
            select(Contact)
            .options(selectinload(Contact.client))
            .where(Contact.is_deleted.is_(False))
        )
        if client_id:
            stmt = stmt.where(Contact.client_id == client_id)
        if search:
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                (Contact.name.ilike(term))
                | (Contact.email.ilike(term))
                | (Contact.phone.ilike(term))
                | (Contact.role.ilike(term))
            )
        
        stmt = stmt.order_by(Contact.name.asc()).limit(limit)
        contacts = db.scalars(stmt).all()

        return [
            {
                "id": c.id,
                "name": c.name,
                "email": c.email,
                "phone": c.phone,
                "role": c.role,
                "client_id": c.client_id,
                "client_name": c.client.name if c.client else None,
            }
            for c in contacts
        ]


def get_contact_details(contact_id: int) -> dict[str, Any]:
    """Retorna detalhes completos de uma pessoa de contato, dados da empresa cliente,
    projetos vinculados e faturas enviadas para este contato.
    
    Args:
        contact_id: ID do contato no CRM.
    """
    with SessionLocal() as db:
        contact = db.scalar(
            select(Contact)
            .options(selectinload(Contact.client))
            .where(Contact.id == contact_id, Contact.is_deleted.is_(False))
        )
        if not contact:
            return {"error": f"Contato com ID {contact_id} não encontrado."}

        client = contact.client

        billing_projects = db.scalars(
            select(Project)
            .where(Project.invoice_contact_id == contact_id, Project.is_deleted.is_(False))
        ).all()

        invoices = db.scalars(
            select(Invoice)
            .options(selectinload(Invoice.project))
            .where(Invoice.contact_id == contact_id, Invoice.is_deleted.is_(False))
            .order_by(Invoice.id.desc())
        ).all()

        return {
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone,
            "role": contact.role,
            "empresa": {
                "id": client.id,
                "nome": client.name,
                "cnpj": client.cnpj,
                "endereco": client.address,
                "segmento": client.industry,
            } if client else None,
            "projetos_como_contato_cobranca": [
                {"id": p.id, "nome": p.name, "status": p.status.value}
                for p in billing_projects
            ],
            "faturas_recebidas": [
                {
                    "id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "amount": float(inv.amount),
                    "status": inv.status.value,
                    "due_date": inv.due_date.isoformat() if inv.due_date else None,
                    "projeto": inv.project.name if inv.project else None,
                }
                for inv in invoices
            ],
        }


def get_project_details(project_id: int) -> dict[str, Any]:
    """Retorna detalhes completos de um projeto, incluindo dados fiscais da empresa cliente (CNPJ e Endereço)
    e o contato designado para o envio de faturas e cobranças.
    
    Args:
        project_id: ID do projeto no CRM.
    """
    with SessionLocal() as db:
        project = db.scalar(
            select(Project)
            .options(
                selectinload(Project.client).selectinload(Client.contacts),
                selectinload(Project.invoice_contact),
                selectinload(Project.invoices),
            )
            .where(Project.id == project_id, Project.is_deleted.is_(False))
        )
        if not project:
            return {"error": f"Projeto com ID {project_id} não encontrado."}

        client = project.client
        invoice_contact = project.invoice_contact

        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status.value,
            "project_value": float(project.project_value or 0),
            "contract_type": project.contract_type,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "due_date": project.due_date.isoformat() if project.due_date else None,
            "cliente": {
                "id": client.id,
                "nome": client.name,
                "cnpj": client.cnpj,
                "endereco": client.address,
                "segmento": client.industry,
                "status": client.status.value,
            } if client else None,
            "contato_faturamento": {
                "id": invoice_contact.id,
                "nome": invoice_contact.name,
                "email": invoice_contact.email,
                "telefone": invoice_contact.phone,
                "cargo": invoice_contact.role,
            } if invoice_contact and not invoice_contact.is_deleted else None,
            "contatos_disponiveis_cliente": [
                {
                    "id": ct.id,
                    "nome": ct.name,
                    "email": ct.email,
                    "telefone": ct.phone,
                    "cargo": ct.role,
                }
                for ct in (client.contacts if client else [])
                if not ct.is_deleted
            ],
            "faturas": [
                {
                    "id": inv.id,
                    "invoice_number": inv.invoice_number,
                    "amount": float(inv.amount),
                    "due_date": inv.due_date.isoformat() if inv.due_date else None,
                    "status": inv.status.value,
                }
                for inv in project.invoices
                if not inv.is_deleted
            ],
        }


def list_invoices(
    project_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Lista faturas de projetos cadastradas no FlowCRM com filtros opcionais.
    
    Args:
        project_id: Filtro opcional por ID do projeto.
        status: Filtro opcional por status ('draft', 'pending', 'paid', 'overdue', 'cancelled').
        limit: Quantidade máxima de registros a retornar (padrão: 50).
    """
    with SessionLocal() as db:
        stmt = (
            select(Invoice)
            .options(
                selectinload(Invoice.project).selectinload(Project.client),
                selectinload(Invoice.contact),
            )
            .where(Invoice.is_deleted.is_(False))
            .order_by(Invoice.id.desc())
        )
        if project_id:
            stmt = stmt.where(Invoice.project_id == project_id)
        if status:
            try:
                stmt = stmt.where(Invoice.status == InvoiceStatus(status.lower()))
            except ValueError:
                pass
        
        invoices = db.scalars(stmt.limit(limit)).all()
        return [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "amount": float(inv.amount),
                "description": inv.description,
                "status": inv.status.value,
                "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "payment_date": inv.payment_date.isoformat() if inv.payment_date else None,
                "project_id": inv.project_id,
                "project_name": inv.project.name if inv.project else None,
                "client_name": inv.project.client.name if inv.project and inv.project.client else None,
                "contact_id": inv.contact_id,
                "contact_name": inv.contact.name if inv.contact else None,
                "contact_email": inv.contact.email if inv.contact else None,
            }
            for inv in invoices
        ]


def get_invoice_details(invoice_id: int) -> dict[str, Any]:
    """Retorna detalhes completos de uma fatura específica, dados do projeto,
    dados fiscais da empresa cliente (CNPJ e Endereço) e dados do contato destinatário do envio.
    
    Args:
        invoice_id: ID da fatura no CRM.
    """
    with SessionLocal() as db:
        invoice = db.scalar(
            select(Invoice)
            .options(
                selectinload(Invoice.project).selectinload(Project.client),
                selectinload(Invoice.contact),
            )
            .where(Invoice.id == invoice_id, Invoice.is_deleted.is_(False))
        )
        if not invoice:
            return {"error": f"Fatura com ID {invoice_id} não encontrada."}

        client = invoice.project.client if invoice.project else None
        contact = invoice.contact

        return {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "amount": float(invoice.amount),
            "description": invoice.description,
            "status": invoice.status.value,
            "issue_date": invoice.issue_date.isoformat() if invoice.issue_date else None,
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
            "payment_date": invoice.payment_date.isoformat() if invoice.payment_date else None,
            "projeto": {
                "id": invoice.project.id,
                "nome": invoice.project.name,
            } if invoice.project else None,
            "cliente": {
                "id": client.id,
                "nome": client.name,
                "cnpj": client.cnpj,
                "endereco": client.address,
            } if client else None,
            "destinatario_envio": {
                "id": contact.id,
                "nome": contact.name,
                "email": contact.email,
                "telefone": contact.phone,
                "cargo": contact.role,
            } if contact else None,
        }


def create_invoice(
    invoice_number: str,
    project_id: int,
    amount: float,
    description: str,
    due_date: str,
    contact_id: int | None = None,
    issue_date: str | None = None,
) -> dict[str, Any]:
    """Cria uma nova fatura vinculada a um projeto no CRM.
    Se contact_id não for fornecido, utiliza automaticamente o contato designado para faturamento no projeto.
    
    Args:
        invoice_number: Número identificador mandatório da fatura (ex: 'FAT-2026-001').
        project_id: ID do projeto vinculado.
        amount: Valor monetário da fatura em reais (deve ser > 0).
        description: Descrição dos serviços faturados ou entregas concluídas.
        due_date: Data de vencimento no formato AAAA-MM-DD.
        contact_id: ID do contato que receberá a fatura (opcional se o projeto já tiver contato definido).
        issue_date: Data de emissão no formato AAAA-MM-DD (padrão: hoje).
    """
    with SessionLocal() as db:
        actor = get_current_actor(db)
        
        # Validação de unicidade do número
        existing = db.scalar(
            select(Invoice).where(
                Invoice.invoice_number == invoice_number.strip(),
                Invoice.is_deleted.is_(False),
            )
        )
        if existing:
            return {"error": f"Já existe uma fatura ativa com o número '{invoice_number.strip()}'."}

        project = db.get(Project, project_id)
        if not project or project.is_deleted:
            return {"error": f"Projeto ID {project_id} não encontrado."}

        target_contact_id = contact_id or project.invoice_contact_id

        try:
            parsed_due_date = date.fromisoformat(due_date.strip())
            parsed_issue_date = date.fromisoformat(issue_date.strip()) if issue_date else date.today()
        except ValueError as e:
            return {"error": f"Formato de data inválido. Use AAAA-MM-DD. Erro: {e}"}

        invoice = Invoice(
            invoice_number=invoice_number.strip(),
            project_id=project_id,
            amount=Decimal(str(amount)),
            description=description.strip(),
            due_date=parsed_due_date,
            issue_date=parsed_issue_date,
            contact_id=target_contact_id,
            status=InvoiceStatus.pending,
            created_by_id=actor.id,
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        db.refresh(invoice, ["project", "contact"])
        client_name = invoice.project.client.name if invoice.project and invoice.project.client else "N/A"
        contact_name = invoice.contact.name if invoice.contact else "Nenhum"

        return {
            "success": True,
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "amount": float(invoice.amount),
            "project_name": invoice.project.name,
            "client_name": client_name,
            "destinatario": contact_name,
            "due_date": invoice.due_date.isoformat(),
            "status": invoice.status.value,
            "message": f"Fatura '{invoice.invoice_number}' criada com sucesso no valor de R$ {invoice.amount:,.2f}.",
        }


def update_invoice_status(
    invoice_id: int,
    status: str,
    payment_date: str | None = None,
) -> dict[str, Any]:
    """Atualiza o status de uma fatura (ex: marcar como paga, enviada, vencida ou cancelada).
    
    Args:
        invoice_id: ID da fatura no CRM.
        status: Novo status ('draft', 'pending', 'paid', 'overdue', 'cancelled').
        payment_date: Data de pagamento no formato AAAA-MM-DD (se marcar como 'paid' e omitir, assume hoje).
    """
    with SessionLocal() as db:
        invoice = db.get(Invoice, invoice_id)
        if not invoice or invoice.is_deleted:
            return {"error": f"Fatura ID {invoice_id} não encontrada."}

        try:
            target_status = InvoiceStatus(status.lower().strip())
        except ValueError:
            valid = [s.value for s in InvoiceStatus]
            return {"error": f"Status '{status}' inválido. Valores aceitos: {valid}"}

        invoice.status = target_status
        if target_status == InvoiceStatus.paid:
            if payment_date:
                try:
                    invoice.payment_date = date.fromisoformat(payment_date.strip())
                except ValueError:
                    return {"error": "Formato de data de pagamento inválido. Use AAAA-MM-DD."}
            elif not invoice.payment_date:
                invoice.payment_date = date.today()

        db.commit()
        db.refresh(invoice)

        return {
            "success": True,
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "new_status": invoice.status.value,
            "payment_date": invoice.payment_date.isoformat() if invoice.payment_date else None,
            "message": f"Fatura '{invoice.invoice_number}' atualizada para o status '{invoice.status.value}'.",
        }
