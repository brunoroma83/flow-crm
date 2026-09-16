from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def ensure_schema() -> None:
    """Aplica ajustes de esquema que ainda não possuem uma migração formal.

    ``create_all`` cria tabelas novas, mas não acrescenta colunas às tabelas já
    existentes. Isto mantém bancos criados antes da adoção do soft delete
    compatíveis com os modelos atuais.
    """
    table_names = ("users", "clients", "contacts", "projects", "tasks", "meetings")
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    with engine.begin() as connection:
        for table_name in table_names:
            if table_name not in existing_tables:
                continue
            columns = {column["name"] for column in inspector.get_columns(table_name)}
            if "is_deleted" not in columns:
                connection.execute(text(
                    f"ALTER TABLE {table_name} "
                    "ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE"
                ))
            if table_name != "users" and "created_by_id" not in columns:
                connection.execute(text(
                    f"ALTER TABLE {table_name} "
                    "ADD COLUMN created_by_id INTEGER"
                ))


def get_db():
    with SessionLocal() as session:
        yield session
