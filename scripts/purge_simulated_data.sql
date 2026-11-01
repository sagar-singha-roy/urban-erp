-- Removes rows created by the former simulated seeders. Review before running on any shared database.
-- Usage: psql "$DATABASE_URL" -f scripts/purge_simulated_data.sql
BEGIN;
DELETE FROM backup_jobs;
DELETE FROM restore_jobs;
DELETE FROM dr_drills;
DELETE FROM backup_policies;
DELETE FROM tenant_isolation_test_runs;
DELETE FROM isolation_finding_reports;
DELETE FROM rls_policy_registry;
DELETE FROM immutable_audit_events WHERE signature NOT LIKE 'HMAC-SHA256:%' OR signature IS NULL;
DELETE FROM audit_retention_policies WHERE policy_code IN ('RET-CERT-IN-7YR', 'RET-MUNICIPAL-FIN-10YR', 'RET-LEGAL-DISPUTE-HOLD');
DELETE FROM fleet_pods;
DELETE FROM fleet_worker_queues;
DELETE FROM fleet_db_pools;
DELETE FROM fleet_microservices;
COMMIT;
