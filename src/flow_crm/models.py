from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ClientStatus(StrEnum):
    active = "active"
    prospect = "prospect"
    inactive = "inactive"


class ProjectStatus(StrEnum):
    planning = "planning"
    active = "active"
    paused = "paused"
    completed = "completed"


class TaskStatus(StrEnum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class Priority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


class UserRole(StrEnum):
    admin = "admin"
    member = "member"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


from sqlalchemy import Boolean as SQLBool  # para compatibilidade com SQLAlchemy 2.0+

class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.member)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_deleted: Mapped[bool] = mapped_column(SQLBool, default=False)

class Client(TimestampMixin, Base):
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    industry: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[ClientStatus] = mapped_column(Enum(ClientStatus), default=ClientStatus.prospect)
    health_score: Mapped[int] = mapped_column(default=100)
    monthly_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    contacts: Mapped[list["Contact"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    meetings: Mapped[list["Meeting"]] = relationship(back_populates="client", cascade="all, delete-orphan")
    is_deleted: Mapped[bool] = mapped_column(SQLBool, default=False)

class Contact(TimestampMixin, Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    role: Mapped[str | None] = mapped_column(String(100))
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    client: Mapped[Client] = relationship(back_populates="contacts")
    is_deleted: Mapped[bool] = mapped_column(SQLBool, default=False)

class Project(TimestampMixin, Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.planning)
    start_date: Mapped[date | None] = mapped_column(Date)
    due_date: Mapped[date | None] = mapped_column(Date)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    client: Mapped[Client] = relationship(back_populates="projects")
    tasks: Mapped[list["Task"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    is_deleted: Mapped[bool] = mapped_column(SQLBool, default=False)

class Task(TimestampMixin, Base):
    __tablename__ = "tasks"
    __table_args__ = (
        # Indexes para performance em consultas de status + due_date
        # Index('ix_tasks_project_status_due', 'project_id', 'status', 'due_date'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.todo)
    priority: Mapped[Priority] = mapped_column(Enum(Priority), default=Priority.medium)
    due_date: Mapped[date | None] = mapped_column(Date)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    project: Mapped[Project | None] = relationship(back_populates="tasks")
    is_deleted: Mapped[bool] = mapped_column(SQLBool, default=False)

class Meeting(TimestampMixin, Base):
    __tablename__ = "meetings"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    duration_minutes: Mapped[int] = mapped_column(default=30)
    notes: Mapped[str | None] = mapped_column(Text)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    client: Mapped[Client | None] = relationship(back_populates="meetings")
    is_deleted: Mapped[bool] = mapped_column(SQLBool, default=False)
