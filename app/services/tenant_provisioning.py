import psycopg
from psycopg import sql

from app.core.config import settings
from app.db.tenant import (
    dispose_tenant_engine,
    init_tenant_db,
    tenant_role_name,
    tenant_role_password,
)


def make_tenant_database_name(owner_id: str) -> str:
    return f"cabin_owner_{owner_id.replace('-', '')[:24]}"


def create_tenant_database(database_name: str, owner_id: str) -> None:
    role_name = tenant_role_name(owner_id)
    role_password = tenant_role_password(owner_id)

    # Role and database identifiers are generated from the server-side UUID.
    # psycopg.sql safely quotes identifiers and the password literal.
    with psycopg.connect(settings.provision_database_url, autocommit=True) as connection:
        connection.execute(
            sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
                sql.Identifier(role_name), sql.Literal(role_password)
            )
        )
        try:
            connection.execute(
                sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    sql.Identifier(database_name), sql.Identifier(role_name)
                )
            )
        except Exception:
            connection.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role_name)))
            raise


def provision_tenant_database(database_name: str, owner_id: str) -> None:
    create_tenant_database(database_name, owner_id)
    try:
        init_tenant_db(database_name, owner_id)
    except Exception:
        drop_tenant_database(database_name, owner_id)
        raise


def drop_tenant_database(database_name: str, owner_id: str) -> None:
    dispose_tenant_engine(database_name)
    role_name = tenant_role_name(owner_id)
    with psycopg.connect(settings.provision_database_url, autocommit=True) as connection:
        connection.execute(
            sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(database_name))
        )
        connection.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(role_name)))
