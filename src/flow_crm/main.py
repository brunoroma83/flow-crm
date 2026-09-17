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
    Client,
    ClientStatus,
    Contact,
    Meeting,
    Project,
    ProjectStatus,
    Task,
    TaskStatus,
    User,
    UserRole,
)
from .schemas import (
    ClientIn,
    ClientOut,
    ContactIn,
    ContactOut,
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
from .security import create_token, hash_password, token_subject, verify_password

ModelT = TypeVar("ModelT")


def seed_data(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Client)):
        return

    client = Client(
        name="Acme Consulting",
        industry="Consultoria",
        status=ClientStatus.active,
        health_score=94,
        monthly_value=8500,
    )
    second = Client(
        name="Norte Tecnologia",
        industry="Tecnologia",
        status=ClientStatus.prospect,
        health_score=78,
        monthly_value=4200,
    )
    db.add_all([client, second])
    db.flush()

    project = Project(
        name="Transformação Comercial",
        client_id=client.id,
        status=ProjectStatus.active,
        start_date=date.today(),
        due_date=date.today().replace(day=min(date.today().day, 28)),
    )
    db.add(project)
    db.flush()

    db.add_all([
        Contact(
            name="Marina Costa",
            email="marina@acme.example",
            role="Diretora de Operações",
            client_id=client.id,
        ),
        Contact(
            name="João Pereira",
            email="joao@norte.example",
            role="Head de Produto",
            client_id=second.id,
        ),
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


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    with Session(bind=engine) as db:
        ensure_admin(db)
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
    db: Session = Depends(get_db),
) -> User:
    token = authorization.removeprefix("Bearer ") if authorization else ""
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
    return list_records(db, Project)


@app.post("/api/projects", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectIn,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return create_record(db, Project, payload, actor)


@app.put("/api/projects/{item_id}", response_model=ProjectOut)
def update_project(
    item_id: int,
    payload: ProjectIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return update_record(db, Project, item_id, payload)


@app.delete("/api/projects/{item_id}", status_code=204)
def delete_project(
    item_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return delete_record(db, Project, item_id, actor)


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


static_dir = Path(__file__).parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")


def run() -> None:
    import uvicorn

    uvicorn.run("flow_crm.main:app", host="0.0.0.0", port=8000, reload=True)
