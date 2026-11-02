"""Applies PostgreSQL row-level security and the restricted application role. Idempotent."""
import logging
import re
import uuid

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.config import settings

logger = logging.getLogger(__name__)

RLS_TABLES = ("zones", "wards", "localities", "property_parcels", "buildings", "property_units", "owners", "gis_layers", "gis_features",
              "branding_profiles", "branding_asset_sets", "branding_asset_files", "tenant_domains", "tenant_certificates", "domain_mappings")
POLICY_NAME = "tenant_isolation"
_SCOPE = "string_to_array(current_setting('app.tenant_ids', true), ',')"


def policy_expression(table: str) -> str:
    return (
        "current_setting('app.rls_bypass', true) = 'on' "
        f"OR upper({table}.tenant_id) = ANY({_SCOPE}) "
        "OR EXISTS (SELECT 1 FROM tenants t "
        f"WHERE t.tenant_id = {table}.tenant_id "
        f"AND (upper(t.state_code) = ANY({_SCOPE}) OR upper(t.parent_state_tenant_id) = ANY({_SCOPE})))"
    )


async def _ensure_app_role(conn: AsyncConnection) -> None:
    app_url = make_url(settings.write_db_url)
    if app_url.username == make_url(settings.admin_db_url).username:
        logger.error("The application uses the admin database role, so row-level security can be bypassed.")
        return
    role = app_url.username or ""
    if not re.fullmatch(r"[a-z_][a-z0-9_]*", role):
        raise ValueError("The application database role name contains unsupported characters.")
    password = (app_url.password or "").replace("'", "''")
    attributes = f"LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD '{password}'"
    exists = await conn.scalar(text("SELECT 1 FROM pg_roles WHERE rolname = :role"), {"role": role})
    await conn.execute(text(f"{'ALTER' if exists else 'CREATE'} ROLE {role} {attributes}"))
    database = await conn.scalar(text("SELECT current_database()"))
    await conn.execute(text(f'GRANT CONNECT ON DATABASE "{database}" TO {role}'))
    await conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
    await conn.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role}"))
    await conn.execute(text(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {role}"))
    await conn.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {role}"))


async def apply_rls(conn: AsyncConnection) -> None:
    await _ensure_app_role(conn)
    for table in RLS_TABLES:
        expression = policy_expression(table)
        await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        await conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        await conn.execute(text(f"DROP POLICY IF EXISTS {POLICY_NAME} ON {table}"))
        await conn.execute(text(f"CREATE POLICY {POLICY_NAME} ON {table} FOR ALL USING ({expression}) WITH CHECK ({expression})"))
        await conn.execute(
            text(
                "INSERT INTO rls_policy_registry (id, policy_name, policy_code, database_service, schema_name, table_name, "
                "tenant_key_column, policy_type, database_commands, applicable_tenant_levels, policy_definition, policy_status, "
                "last_verified_at, last_verification_result, verification_latency_ms, enforcement_notes, created_at, updated_at) "
                "VALUES (:id, :name, :code, 'PostgreSQL', 'public', :table, 'tenant_id', 'ALL', "
                "CAST(:commands AS json), CAST(:levels AS json), :definition, 'ACTIVE', NULL, 'NOT_VERIFIED', 0, "
                "'Applied at service startup.', now(), now()) ON CONFLICT (policy_code) DO NOTHING"
            ),
            {
                "id": str(uuid.uuid4()),
                "name": f"Tenant isolation on {table}",
                "code": f"RLS-{table.upper().replace('_', '-')}",
                "table": table,
                "commands": '["SELECT", "INSERT", "UPDATE", "DELETE"]',
                "levels": '["State", "ULB"]',
                "definition": expression,
            },
        )


async def app_role_bypasses_rls(conn: AsyncConnection) -> bool:
    return bool(
        await conn.scalar(text("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"))
    )
