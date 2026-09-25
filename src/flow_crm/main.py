from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, TypeVar

from fastapi import Depends, FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from .database import Base, engine, ensure_schema, get_db
from .models import (
    ApiKey,
    Client,
    ClientStatus,
    Contact,
    Invoice,
    InvoiceStatus,
    Meeting,
    Project,
    ProjectStatus,
    Task,
    TaskStatus,
    User,
    UserRole,
)
from .schemas import (
    ApiKeyCreatedOut,
    ApiKeyIn,
    ApiKeyOut,
    ClientIn,
    ClientOut,
    ContactIn,
    ContactOut,
    InvoiceIn,
    InvoiceOut,
    MeetingIn,
    MeetingOut,
    ProjectIn,
    ProjectOut,
    TaskIn,
    TaskOut,
    LoginIn,
    UserIn,
    UserOut,
    UserUpdate,
)
from .security import (
    create_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    token_subject,
    verify_password,
)
import secrets

ModelT = TypeVar("ModelT")


def seed_data(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Client)):
        return

    client = Client(
        name="Acme Consulting",
        industry="Consultoria",
        cnpj="12.345.678/0001-90",
        address="Av. Paulista, 1000, Bela Vista, São Paulo - SP, CEP 01310-100",
        status=ClientStatus.active,
        health_score=94,
        monthly_value=8500,
    )
    second = Client(
        name="Norte Tecnologia",
        industry="Tecnologia",
        cnpj="98.765.432/0001-10",
        address="Rua dos Andradas, 500, Centro, Porto Alegre - RS, CEP 90020-002",
        status=ClientStatus.prospect,
        health_score=78,
        monthly_value=4200,
    )
    db.add_all([client, second])
    db.flush()

    contact_marina = Contact(
        name="Marina Costa",
        email="marina@acme.example",
        role="Diretora de Operações",
        client_id=client.id,
    )
    contact_joao = Contact(
        name="João Pereira",
        email="joao@norte.example",
        role="Head de Produto",
        client_id=second.id,
    )
    db.add_all([contact_marina, contact_joao])
    db.flush()

    project = Project(
        name="Transformação Comercial",
        client_id=client.id,
        invoice_contact_id=contact_marina.id,
        status=ProjectStatus.active,
        start_date=date.today(),
        due_date=date.today().replace(day=min(date.today().day, 28)),
    )
    db.add(project)
    db.flush()

    invoice = Invoice(
        invoice_number="FAT-2026-001",
        description="Honorários mensais de consultoria em transformação comercial",
        amount=8500,
        issue_date=date.today(),
        due_date=date.today().replace(day=min(date.today().day, 28)),
        status=InvoiceStatus.pending,
        project_id=project.id,
        contact_id=contact_marina.id,
    )

    db.add_all([
        invoice,
        Task(
            title="Revisar plano da fase 2",
            project_id=project.id,
            status=TaskStatus.in_progress,
            due_date=date.today(),
        ),
        Task(
            title="Enviar proposta comercial",
            status=TaskStatus.todo,
            due_date=date.today(),
        ),
        Meeting(
            title="Checkpoint semanal",
            client_id=client.id,
            starts_at=datetime.combine(date.today(), time(14, 0)),
            duration_minutes=45,
        ),
    ])
    db.commit()


def ensure_admin(db: Session) -> None:
    if not db.scalar(select(User).where(User.email == "bruuno@gmail.com")):
        db.add(
            User(
                name="Administrador",
                email="bruuno@gmail.com",
                password_hash=hash_password("182436"),
                role=UserRole.admin,
            )
        )
        db.commit()


def ensure_agent_user(db: Session) -> User:
    agent_user = db.scalar(select(User).where(User.role == UserRole.agent, User.is_deleted.is_(False)))
    if not agent_user:
        agent_user = User(
            name="Agente IA",
            email="agente@flowcrm.local",
            password_hash=hash_password(secrets.token_urlsafe(32)),
            role=UserRole.agent,
        )
        db.add(agent_user)
        db.commit()
        db.refresh(agent_user)
    return agent_user


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    with Session(bind=engine) as db:
        ensure_admin(db)
        ensure_agent_user(db)
        seed_data(db)
    yield


app = FastAPI(title="FlowCRM API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_current_user(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> User:
    # 1. Autenticação por API Key (via header X-API-Key ou Bearer fc_live_...)
    api_token = x_api_key
    if not api_token and authorization:
        candidate = authorization.removeprefix("Bearer ").strip()
        if candidate.startswith("fc_live_"):
            api_token = candidate

    if api_token:
        hashed = hash_api_key(api_token)
        key_record = db.scalar(
            select(ApiKey).where(
                ApiKey.hashed_key == hashed,
                ApiKey.is_active.is_(True),
                ApiKey.is_deleted.is_(False),
            )
        )
        if not key_record:
            raise HTTPException(401, "API Key inválida ou inativa")
        if key_record.expires_at and key_record.expires_at < datetime.now():
            raise HTTPException(401, "API Key expirada")

        key_record.last_used_at = datetime.now()
        db.commit()

        user = db.get(User, key_record.user_id)
        if not user or not user.is_active or user.is_deleted:
            raise HTTPException(401, "Usuário associado à API Key está inativo")
        return user

    # 2. Autenticação tradicional por JWT
    token = authorization.removeprefix("Bearer ").strip() if authorization else ""
    user_id = token_subject(token)
    user = db.get(User, user_id) if user_id else None
    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(401, "Autenticação necessária")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(403, "Apenas administradores podem gerenciar usuários")
    return user


@app.post("/api/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower(), User.is_deleted.is_(False)))
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "E-mail ou senha inválidos")
    return {"access_token": create_token(user.id), "user": UserOut.model_validate(user)}


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@app.get("/api/users", response_model=list[UserOut])
def users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return list_records(db, User)


@app.post("/api/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(409, "Este e-mail já está cadastrado")
    values = payload.model_dump()
    values["email"] = values["email"].lower()
    values["password_hash"] = hash_password(values.pop("password"))
    user = User(**values)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.put("/api/users/{item_id}", response_model=UserOut)
def update_user(
    item_id: int,
    payload: UserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = get_or_404(db, User, item_id)
    if user.id == admin.id and (not payload.is_active or payload.role != UserRole.admin):
        raise HTTPException(400, "O administrador atual não pode remover o próprio acesso")
    values = payload.model_dump()
    password = values.pop("password")
    for key, value in values.items():
        setattr(user, key, value.lower() if key == "email" else value)
    if password:
        user.password_hash = hash_password(password)
    db.commit()
    db.refresh(user)
    return user


@app.delete("/api/users/{item_id}", status_code=204)
def delete_user(
    item_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if item_id == admin.id:
        raise HTTPException(400, "O administrador atual não pode excluir a si mesmo")
    return delete_record(db, User, item_id, admin)


@app.get("/api/api-keys", response_model=list[ApiKeyOut])
def list_api_keys(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    keys = db.scalars(
        select(ApiKey)
        .options(selectinload(ApiKey.user))
        .where(ApiKey.is_deleted.is_(False))
        .order_by(ApiKey.id.desc())
    ).all()
    return [
        ApiKeyOut(
            id=key.id,
            name=key.name,
            key_prefix=key.key_prefix,
            user_id=key.user_id,
            is_active=key.is_active,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            user_name=key.user.name if key.user else None,
        )
        for key in keys
    ]


@app.post("/api/api-keys", response_model=ApiKeyCreatedOut, status_code=201)
def create_api_key_endpoint(
    payload: ApiKeyIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    target_user_id = payload.user_id
    if target_user_id:
        target_user = db.get(User, target_user_id)
        if not target_user or target_user.is_deleted:
            raise HTTPException(404, "Usuário especificado não encontrado")
    else:
        target_user = ensure_agent_user(db)
        target_user_id = target_user.id

    raw_key, prefix, hashed = generate_api_key()
    record = ApiKey(
        name=payload.name,
        key_prefix=prefix,
        hashed_key=hashed,
        user_id=target_user_id,
        is_active=True,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return ApiKeyCreatedOut(
        id=record.id,
        name=record.name,
        key_prefix=record.key_prefix,
        user_id=record.user_id,
        is_active=record.is_active,
        created_at=record.created_at,
        last_used_at=record.last_used_at,
        user_name=target_user.name,
        raw_key=raw_key,
    )


@app.delete("/api/api-keys/{item_id}", status_code=204)
def delete_api_key_endpoint(
    item_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    record = get_or_404(db, ApiKey, item_id)
    record.is_deleted = True
    db.commit()
    return Response(status_code=204)



def get_or_404(db: Session, model: type[ModelT], item_id: int) -> ModelT:
    record = db.get(model, item_id)
    if not record or getattr(record, "is_deleted", False):
        raise HTTPException(404, "Registro não encontrado")
    return record


def list_records(db: Session, model: type[ModelT]) -> list[ModelT]:
    return list(db.scalars(select(model).where(model.is_deleted.is_(False)).order_by(model.id.desc())))  # type: ignore[attr-defined]


def create_record(db: Session, model: type[ModelT], payload: Any, creator: User) -> ModelT:
    record = model(**payload.model_dump(), created_by_id=creator.id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_record(db: Session, model: type[ModelT], item_id: int, payload: Any) -> ModelT:
    record = get_or_404(db, model, item_id)
    for key, value in payload.model_dump().items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, model: type[ModelT], item_id: int, actor: User) -> Response:
    record = get_or_404(db, model, item_id)
    creator_id = getattr(record, "created_by_id", None)
    if actor.role != UserRole.admin and creator_id != actor.id:
        raise HTTPException(403, "Você só pode excluir registros criados por você")
    record.is_deleted = True
    db.commit()
    return Response(status_code=204)


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    today = date.today()
    total_value = db.scalar(
        select(func.coalesce(func.sum(Client.monthly_value), 0)).where(
            Client.status == ClientStatus.active,
            Client.is_deleted.is_(False),
        )
    )
    project_rows = db.scalars(
        select(Project)
        .options(
            selectinload(Project.client).selectinload(Client.contacts),
            selectinload(Project.tasks),
        )
        .where(
            Project.status.in_([ProjectStatus.active, ProjectStatus.planning]),
            Project.is_deleted.is_(False),
        )
        .order_by(Project.due_date.asc().nulls_last(), Project.name)
    ).all()

    def project_summary(project: Project) -> dict[str, Any]:
        client = project.client if (project.client and not project.client.is_deleted) else None
        tasks = [task for task in project.tasks if not task.is_deleted]
        return {
            "id": project.id,
            "name": project.name,
            "due_date": project.due_date.isoformat() if project.due_date else None,
            "client": {
                "id": client.id,
                "name": client.name,
                "monthly_value": float(client.monthly_value or 0),
            }
            if client
            else None,
            "contacts": [
                {
                    "name": contact.name,
                    "role": contact.role,
                    "email": contact.email,
                }
                for contact in client.contacts
                if not contact.is_deleted
            ]
            if client
            else [],
            "tasks": [
                {
                    "title": task.title,
                    "status": task.status,
                    "priority": task.priority,
                    "due_date": task.due_date.isoformat() if task.due_date else None,
                }
                for task in tasks
            ],
            "task_summary": {
                "total": len(tasks),
                "done": sum(task.status == TaskStatus.done for task in tasks),
                "in_progress": sum(task.status == TaskStatus.in_progress for task in tasks),
            },
        }

    return {
        "active_clients": db.scalar(
            select(func.count())
            .select_from(Client)
            .where(
                Client.status == ClientStatus.active,
                Client.is_deleted.is_(False),
            )
        ),
        "active_projects": db.scalar(
            select(func.count())
            .select_from(Project)
            .where(
                Project.status == ProjectStatus.active,
                Project.is_deleted.is_(False),
            )
        ),
        "tasks_today": db.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.due_date == today,
                Task.status != TaskStatus.done,
                Task.is_deleted.is_(False),
            )
        ),
        "meetings_today": db.scalar(
            select(func.count())
            .select_from(Meeting)
            .where(
                func.date(Meeting.starts_at) == today,
                Meeting.is_deleted.is_(False),
            )
        ),
        "monthly_value": float(total_value or 0),
        "invoices_pending_count": db.scalar(
            select(func.count())
            .select_from(Invoice)
            .where(
                Invoice.status == InvoiceStatus.pending,
                Invoice.is_deleted.is_(False),
            )
        ) or 0,
        "invoices_pending_value": float(
            db.scalar(
                select(func.coalesce(func.sum(Invoice.amount), 0))
                .where(
                    Invoice.status == InvoiceStatus.pending,
                    Invoice.is_deleted.is_(False),
                )
            ) or 0
        ),
        "invoices_overdue_count": db.scalar(
            select(func.count())
            .select_from(Invoice)
            .where(
                Invoice.status == InvoiceStatus.pending,
                Invoice.due_date < today,
                Invoice.is_deleted.is_(False),
            )
        ) or 0,
        "in_progress_projects": [
            project_summary(project)
            for project in project_rows
            if project.status == ProjectStatus.active
        ],
        "prospecting_projects": [
            project_summary(project)
            for project in project_rows
            if project.status == ProjectStatus.planning
        ],
    }


@app.get("/api/clients", response_model=list[ClientOut])
def clients(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list_records(db, Client)


@app.post("/api/clients", response_model=ClientOut, status_code=201)
def create_client(
    payload: ClientIn,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return create_record(db, Client, payload, actor)


@app.put("/api/clients/{item_id}", response_model=ClientOut)
def update_client(
    item_id: int,
    payload: ClientIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return update_record(db, Client, item_id, payload)


@app.delete("/api/clients/{item_id}", status_code=204)
def delete_client(
    item_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return delete_record(db, Client, item_id, actor)


@app.get("/api/contacts", response_model=list[ContactOut])
def contacts(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list_records(db, Contact)


@app.post("/api/contacts", response_model=ContactOut, status_code=201)
def create_contact(
    payload: ContactIn,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return create_record(db, Contact, payload, actor)


@app.put("/api/contacts/{item_id}", response_model=ContactOut)
def update_contact(
    item_id: int,
    payload: ContactIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return update_record(db, Contact, item_id, payload)


@app.delete("/api/contacts/{item_id}", status_code=204)
def delete_contact(
    item_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return delete_record(db, Contact, item_id, actor)


@app.get("/api/projects", response_model=list[ProjectOut])
def projects(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = (
        select(Project)
        .options(
            selectinload(Project.client),
            selectinload(Project.invoice_contact),
        )
        .where(Project.is_deleted.is_(False))
        .order_by(Project.id.desc())
    )
    project_rows = db.scalars(stmt).all()
    return [
        ProjectOut(
            id=p.id,
            name=p.name,
            description=p.description,
            status=p.status,
            start_date=p.start_date,
            due_date=p.due_date,
            client_id=p.client_id,
            invoice_contact_id=p.invoice_contact_id,
            created_by_id=p.created_by_id,
            client_name=p.client.name if p.client else None,
            invoice_contact_name=p.invoice_contact.name if p.invoice_contact else None,
            invoice_contact_email=p.invoice_contact.email if p.invoice_contact else None,
        )
        for p in project_rows
    ]


@app.post("/api/projects", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectIn,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    project = Project(**payload.model_dump(), created_by_id=actor.id)
    db.add(project)
    db.commit()
    db.refresh(project)
    db.refresh(project, ["client", "invoice_contact"])
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        start_date=project.start_date,
        due_date=project.due_date,
        client_id=project.client_id,
        invoice_contact_id=project.invoice_contact_id,
        created_by_id=project.created_by_id,
        client_name=project.client.name if project.client else None,
        invoice_contact_name=project.invoice_contact.name if project.invoice_contact else None,
        invoice_contact_email=project.invoice_contact.email if project.invoice_contact else None,
    )


@app.put("/api/projects/{item_id}", response_model=ProjectOut)
def update_project(
    item_id: int,
    payload: ProjectIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    project = get_or_404(db, Project, item_id)
    for key, value in payload.model_dump().items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    db.refresh(project, ["client", "invoice_contact"])
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        start_date=project.start_date,
        due_date=project.due_date,
        client_id=project.client_id,
        invoice_contact_id=project.invoice_contact_id,
        created_by_id=project.created_by_id,
        client_name=project.client.name if project.client else None,
        invoice_contact_name=project.invoice_contact.name if project.invoice_contact else None,
        invoice_contact_email=project.invoice_contact.email if project.invoice_contact else None,
    )


@app.delete("/api/projects/{item_id}", status_code=204)
def delete_project(
    item_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return delete_record(db, Project, item_id, actor)


@app.get("/api/invoices", response_model=list[InvoiceOut])
def get_invoices(
    project_id: int | None = None,
    status: InvoiceStatus | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
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
        stmt = stmt.where(Invoice.status == status)

    invoices = db.scalars(stmt).all()
    return [
        InvoiceOut(
            id=inv.id,
            invoice_number=inv.invoice_number,
            description=inv.description,
            amount=inv.amount,
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            payment_date=inv.payment_date,
            status=inv.status,
            project_id=inv.project_id,
            contact_id=inv.contact_id,
            created_by_id=inv.created_by_id,
            created_at=inv.created_at,
            project_name=inv.project.name if inv.project else None,
            client_name=inv.project.client.name if inv.project and inv.project.client else None,
            client_cnpj=inv.project.client.cnpj if inv.project and inv.project.client else None,
            contact_name=inv.contact.name if inv.contact else None,
            contact_email=inv.contact.email if inv.contact else None,
        )
        for inv in invoices
    ]


@app.post("/api/invoices", response_model=InvoiceOut, status_code=201)
def create_invoice_endpoint(
    payload: InvoiceIn,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    existing = db.scalar(
        select(Invoice).where(
            Invoice.invoice_number == payload.invoice_number,
        )
    )
    if existing:
        raise HTTPException(409, f"Já existe uma fatura cadastrada com o número {payload.invoice_number}")

    project = get_or_404(db, Project, payload.project_id)
    contact_id = payload.contact_id or project.invoice_contact_id

    invoice = Invoice(
        invoice_number=payload.invoice_number,
        description=payload.description,
        amount=payload.amount,
        issue_date=payload.issue_date,
        due_date=payload.due_date,
        payment_date=payload.payment_date,
        status=payload.status,
        project_id=payload.project_id,
        contact_id=contact_id,
        created_by_id=actor.id,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    db.refresh(invoice, ["project", "contact"])
    client = invoice.project.client if invoice.project else None

    return InvoiceOut(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        description=invoice.description,
        amount=invoice.amount,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        payment_date=invoice.payment_date,
        status=invoice.status,
        project_id=invoice.project_id,
        contact_id=invoice.contact_id,
        created_by_id=invoice.created_by_id,
        created_at=invoice.created_at,
        project_name=invoice.project.name if invoice.project else None,
        client_name=client.name if client else None,
        client_cnpj=client.cnpj if client else None,
        contact_name=invoice.contact.name if invoice.contact else None,
        contact_email=invoice.contact.email if invoice.contact else None,
    )


@app.get("/api/invoices/{item_id}", response_model=InvoiceOut)
def get_invoice_endpoint(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    invoice = get_or_404(db, Invoice, item_id)
    db.refresh(invoice, ["project", "contact"])
    client = invoice.project.client if invoice.project else None
    return InvoiceOut(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        description=invoice.description,
        amount=invoice.amount,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        payment_date=invoice.payment_date,
        status=invoice.status,
        project_id=invoice.project_id,
        contact_id=invoice.contact_id,
        created_by_id=invoice.created_by_id,
        created_at=invoice.created_at,
        project_name=invoice.project.name if invoice.project else None,
        client_name=client.name if client else None,
        client_cnpj=client.cnpj if client else None,
        contact_name=invoice.contact.name if invoice.contact else None,
        contact_email=invoice.contact.email if invoice.contact else None,
    )


@app.put("/api/invoices/{item_id}", response_model=InvoiceOut)
def update_invoice_endpoint(
    item_id: int,
    payload: InvoiceIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    invoice = get_or_404(db, Invoice, item_id)
    if payload.invoice_number != invoice.invoice_number:
        existing = db.scalar(
            select(Invoice).where(
                Invoice.invoice_number == payload.invoice_number,
                Invoice.id != item_id,
            )
        )
        if existing:
            raise HTTPException(409, f"Já existe uma fatura cadastrada com o número {payload.invoice_number}")

    get_or_404(db, Project, payload.project_id)
    for key, value in payload.model_dump().items():
        setattr(invoice, key, value)
    db.commit()
    db.refresh(invoice)
    db.refresh(invoice, ["project", "contact"])
    client = invoice.project.client if invoice.project else None

    return InvoiceOut(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        description=invoice.description,
        amount=invoice.amount,
        issue_date=invoice.issue_date,
        due_date=invoice.due_date,
        payment_date=invoice.payment_date,
        status=invoice.status,
        project_id=invoice.project_id,
        contact_id=invoice.contact_id,
        created_by_id=invoice.created_by_id,
        created_at=invoice.created_at,
        project_name=invoice.project.name if invoice.project else None,
        client_name=client.name if client else None,
        client_cnpj=client.cnpj if client else None,
        contact_name=invoice.contact.name if invoice.contact else None,
        contact_email=invoice.contact.email if invoice.contact else None,
    )


@app.delete("/api/invoices/{item_id}", status_code=204)
def delete_invoice_endpoint(
    item_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return delete_record(db, Invoice, item_id, actor)


@app.get("/api/tasks", response_model=list[TaskOut])
def tasks(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list_records(db, Task)


@app.post("/api/tasks", response_model=TaskOut, status_code=201)
def create_task(
    payload: TaskIn,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return create_record(db, Task, payload, actor)


@app.put("/api/tasks/{item_id}", response_model=TaskOut)
def update_task(
    item_id: int,
    payload: TaskIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return update_record(db, Task, item_id, payload)


@app.delete("/api/tasks/{item_id}", status_code=204)
def delete_task(
    item_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return delete_record(db, Task, item_id, actor)


@app.get("/api/meetings", response_model=list[MeetingOut])
def meetings(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list_records(db, Meeting)


@app.post("/api/meetings", response_model=MeetingOut, status_code=201)
def create_meeting(
    payload: MeetingIn,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return create_record(db, Meeting, payload, actor)


@app.put("/api/meetings/{item_id}", response_model=MeetingOut)
def update_meeting(
    item_id: int,
    payload: MeetingIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return update_record(db, Meeting, item_id, payload)


@app.delete("/api/meetings/{item_id}", status_code=204)
def delete_meeting(
    item_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return delete_record(db, Meeting, item_id, actor)


# Servidor MCP (Model Context Protocol) via SSE para agentes de IA
from .mcp import create_mcp_app
app.mount("/mcp", create_mcp_app())

static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")


def run() -> None:
    import uvicorn

    uvicorn.run("flow_crm.main:app", host="0.0.0.0", port=8000, reload=True)
