from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from .models import ClientStatus, InvoiceStatus, Priority, ProjectStatus, TaskStatus, UserRole


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
    cnpj: str | None = None
    address: str | None = None
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
    invoice_contact_id: int | None = None


class ProjectOut(ProjectIn, ORMModel):
    id: int
    created_by_id: int | None
    client_name: str | None = None
    invoice_contact_name: str | None = None
    invoice_contact_email: str | None = None


class InvoiceIn(BaseModel):
    invoice_number: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=3)
    amount: Decimal = Field(gt=0)
    issue_date: date = Field(default_factory=date.today)
    due_date: date
    payment_date: date | None = None
    status: InvoiceStatus = InvoiceStatus.pending
    project_id: int
    contact_id: int | None = None


class InvoiceOut(InvoiceIn, ORMModel):
    id: int
    created_by_id: int | None
    created_at: datetime | None = None
    project_name: str | None = None
    client_name: str | None = None
    client_cnpj: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None


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


class ApiKeyIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    user_id: int | None = None


class ApiKeyOut(ORMModel):
    id: int
    name: str
    key_prefix: str
    user_id: int
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None = None
    user_name: str | None = None


class ApiKeyCreatedOut(ApiKeyOut):
    raw_key: str

