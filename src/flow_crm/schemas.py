from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .models import ClientStatus, Priority, ProjectStatus, TaskStatus, UserRole


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginIn(BaseModel):
    email: str
    password: str


class UserIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(max_length=254)
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.member
    is_active: bool = True


class UserUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(max_length=254)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role: UserRole = UserRole.member
    is_active: bool = True


class UserOut(ORMModel):
    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool


class ClientIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    industry: str | None = None
    status: ClientStatus = ClientStatus.prospect
    health_score: int = Field(default=100, ge=0, le=100)
    monthly_value: Decimal | None = Field(default=None, ge=0)


class ClientOut(ClientIn, ORMModel):
    id: int
    created_by_id: int | None


class ContactIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(max_length=254)
    phone: str | None = None
    role: str | None = None
    client_id: int


class ContactOut(ContactIn, ORMModel):
    id: int
    created_by_id: int | None


class ProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    status: ProjectStatus = ProjectStatus.planning
    start_date: date | None = None
    due_date: date | None = None
    client_id: int


class ProjectOut(ProjectIn, ORMModel):
    id: int
    created_by_id: int | None


class TaskIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = None
    status: TaskStatus = TaskStatus.todo
    priority: Priority = Priority.medium
    due_date: date | None = None
    project_id: int | None = None


class TaskOut(TaskIn, ORMModel):
    id: int
    created_by_id: int | None


class MeetingIn(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    starts_at: datetime
    duration_minutes: int = Field(default=30, ge=5, le=480)
    notes: str | None = None
    client_id: int | None = None


class MeetingOut(MeetingIn, ORMModel):
    id: int
    created_by_id: int | None
