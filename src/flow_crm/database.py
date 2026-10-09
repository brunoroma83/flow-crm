from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def ensure_schema() -> None:
    """Aplica ajustes de esquema que ainda não possuem uma migração formal.

    ``create_all`` cria tabelas novas, mas não acrescenta colunas às tabelas já
    existentes. Isto mantém bancos criados antes da adoção do soft delete
    compatíveis com os modelos atuais.
    """
    Base.metadata.create_all(bind=engine)
    table_names = (
        "users", "clients", "contacts", "projects", "tasks",
        "meetings", "api_keys", "invoices", "project_monthly_values",
        "task_comments",
    )
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        # Garante que o enum de role no Postgres suporte o novo papel 'agent'
        try:
            connection.execute(text("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'agent'"))
        except Exception:
            pass

        # Garante que o enum de status da tarefa no Postgres suporte 'waiting_feedback'
        try:
            connection.execute(text("ALTER TYPE taskstatus ADD VALUE IF NOT EXISTS 'waiting_feedback'"))
        except Exception:
            pass

        for table_name in table_names:
            if table_name not in existing_tables:
                continue
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            if "is_deleted" not in columns:
                connection.execute(text(
                    f"ALTER TABLE {table_name} "
                    "ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE"
                ))
            if table_name not in ("users", "api_keys") and "created_by_id" not in columns:
                connection.execute(text(
                    f"ALTER TABLE {table_name} "
                    "ADD COLUMN created_by_id INTEGER"
                ))

        if "clients" in existing_tables:
            client_cols = {col["name"] for col in inspector.get_columns("clients")}
            if "cnpj" not in client_cols:
                connection.execute(text("ALTER TABLE clients ADD COLUMN cnpj VARCHAR(20)"))
            if "address" not in client_cols:
                connection.execute(text("ALTER TABLE clients ADD COLUMN address TEXT"))

        if "projects" in existing_tables:
            project_cols = {col["name"] for col in inspector.get_columns("projects")}
            if "invoice_contact_id" not in project_cols:
                connection.execute(text("ALTER TABLE projects ADD COLUMN invoice_contact_id INTEGER REFERENCES contacts(id)"))
            if "project_value" not in project_cols:
                connection.execute(
                    text("ALTER TABLE projects ADD COLUMN project_value NUMERIC(12, 2) NOT NULL DEFAULT 0")
                )
            if "contract_type" not in project_cols:
                connection.execute(
                    text("ALTER TABLE projects ADD COLUMN contract_type VARCHAR(20) NOT NULL DEFAULT 'mensal'")
                )

        if "projects" in existing_tables and "project_monthly_values" in existing_tables:
            try:
                connection.execute(text("""
                    UPDATE projects
                    SET project_value = (
                        SELECT COALESCE(SUM(amount), 0)
                        FROM project_monthly_values
                        WHERE project_monthly_values.project_id = projects.id
                          AND project_monthly_values.is_deleted = FALSE
                    )
                    WHERE EXISTS (
                        SELECT 1 FROM project_monthly_values
                        WHERE project_monthly_values.project_id = projects.id
                          AND project_monthly_values.is_deleted = FALSE
                    )
                """))
            except Exception:
                pass

        if "tasks" in existing_tables:
            task_cols = {col["name"] for col in inspector.get_columns("tasks")}
            if "client_id" not in task_cols:
                connection.execute(text("ALTER TABLE tasks ADD COLUMN client_id INTEGER REFERENCES clients(id)"))

        if "tasks" in existing_tables and "projects" in existing_tables:
            try:
                connection.execute(text("""
                    UPDATE tasks
                    SET client_id = (
                        SELECT client_id
                        FROM projects
                        WHERE projects.id = tasks.project_id
                    )
                    WHERE project_id IS NOT NULL AND client_id IS NULL
                """))
            except Exception:
                pass




def get_db():
    with SessionLocal() as session:
        yield session
