"""Run from backend/services/core_service: python -m unittest discover -s tests"""
import datetime
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-only-signing-key"
os.environ["AUDIT_SIGNING_KEY"] = "test-only-audit-key"

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1 import white_label_domains as domains_api
from app.core import certificates as certs
from app.core import white_label_rules as rules
from app.core.auth import get_current_user
from app.core.domain_verification import VerificationResult
from app.core.gateway_sync import Site, render_files, render_site, routing_status, write_candidate
from app.db.models import TenantDomain
from app.db.rls import RLS_TABLES
from app.db.session import get_read_db, get_write_db
from app.main import app
from app.schemas.white_label import BrandingProfilePayload, CertificateOut, DomainCreate, MappingPayload

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 20


def make_certificate(host="portal.example.org", days=30, san=None, start_days=-1):
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, host)])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(1)
        .not_valid_before(now + datetime.timedelta(days=start_days)).not_valid_after(now + datetime.timedelta(days=days))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(san or host)]), False).sign(key, hashes.SHA256())
    )
    pem = certificate.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    return pem, key_pem


class BrandingRuleTests(unittest.TestCase):
    def test_colours(self):
        self.assertEqual(rules.validate_colour("#1b8c77"), "#1B8C77")
        for bad in ("red", "#12345", "#1234567;}", "url(x)"):
            with self.assertRaises(ValueError):
                rules.validate_colour(bad)

    def test_css_that_loads_outside_content_is_rejected(self):
        for bad in (
            "a { background: url(https://evil.example/x) }", "@import 'x';", "@font-face { src: x }", "a { behavior: x }",
            "a { width: expression(alert(1)) }", "</style><script>", "a { background: \\75rl(x) }", "a { background: image-set('x') }",
        ):
            with self.assertRaises(ValueError, msg=bad):
                rules.validate_custom_css(bad)

    def test_harmless_css_is_kept(self):
        css = "@media (min-width: 768px) { .x { color: #123456; } }"
        self.assertEqual(rules.validate_custom_css(css), css)

    def test_uploads_are_judged_by_content(self):
        self.assertEqual(rules.validate_asset(PNG)[0], "image/png")
        for bad in (b"<svg onload='alert(1)'></svg>", b"<html>", b"", b"MZ\x90\x00"):
            with self.assertRaises(ValueError):
                rules.validate_asset(bad)
        with self.assertRaises(ValueError):
            rules.validate_asset(PNG + b"0" * rules.MAX_ASSET_BYTES)

    def test_ulb_profile_needs_a_ulb(self):
        values = dict(tenantLevel="ULB", stateTenantId="TG", profileName="P", displayName="D", primaryColour="#111111", secondaryColour="#222222")
        with self.assertRaises(ValidationError):
            BrandingProfilePayload(**values)
        self.assertEqual(BrandingProfilePayload(**values, ulbTenantId="GWMC").ulb_tenant_id, "GWMC")


class DomainRuleTests(unittest.TestCase):
    def test_spellings_of_one_name_normalize_to_one_claim(self):
        self.assertEqual(rules.normalize_domain("  Portal.Example.ORG. "), "portal.example.org")
        self.assertEqual(rules.normalize_domain("bücher.example.org"), "xn--bcher-kva.example.org")

    def test_unsafe_names_are_rejected(self):
        for bad in ("localhost", "127.0.0.1", "[::1]", "https://a.example.org", "a.example.org/x", "a.example.org:443", "*.example.org",
                    "svc.internal", "a.local", "noDots", "a b.example.org", "a.example.org;evil", "-bad.example.org", "1.2.3.4"):
            with self.assertRaises(ValueError, msg=bad):
                rules.normalize_domain(bad)

    def test_reserved_domains_cover_their_subdomains(self):
        with patch.object(rules.settings, "PLATFORM_RESERVED_DOMAINS", "platform.example.org"):
            for bad in ("platform.example.org", "x.platform.example.org"):
                with self.assertRaises(ValueError):
                    rules.normalize_domain(bad)
            self.assertEqual(rules.normalize_domain("notplatform.example.org"), "notplatform.example.org")

    def test_related_domains_lists_parents(self):
        self.assertEqual(rules.related_domains("a.b.example.org"), ["a.b.example.org", "b.example.org", "example.org"])

    def test_subdomain_must_sit_under_its_root(self):
        values = dict(tenantId="T", domainName="a.other.org", domainType="Subdomain", rootDomain="example.org", dnsRecordType="CNAME",
                      dnsHost="a", dnsTarget="b", verificationMethod="DNS TXT")
        with self.assertRaises(ValidationError):
            DomainCreate(**values)

    def test_routes_stay_on_the_site(self):
        self.assertEqual(rules.validate_route("/login"), "/login")
        for bad in ("https://evil.example", "//evil.example", "/a;return 301 x", "/../x", "login"):
            with self.assertRaises(ValueError, msg=bad):
                rules.validate_route(bad)

    def test_force_https_needs_ssl(self):
        with self.assertRaises(ValidationError):
            MappingPayload(mappingName="M", tenantId="T", domainId="D", targetApplication=rules.TARGET_APPLICATIONS[0], targetService="core",
                           routingStrategy=rules.ROUTING_HOST, sslRequired=False, forceHttps=True)

    def test_new_tables_have_row_level_security(self):
        for table in ("branding_profiles", "branding_asset_sets", "branding_asset_files", "tenant_domains", "tenant_certificates", "domain_mappings"):
            self.assertIn(table, RLS_TABLES)

    def test_verified_owner_is_unique_in_the_database(self):
        index = next(i for i in TenantDomain.__table__.indexes if i.name == "uq_domain_verified_owner")
        self.assertTrue(index.unique)
        self.assertEqual([c.name for c in index.columns], ["domain_name"])


class CertificateTests(unittest.TestCase):
    def test_valid_upload_reads_expiry_from_the_certificate(self):
        pem, key = make_certificate()
        self.assertGreater(certs.validate_upload(pem, key, None, "portal.example.org").expiry, datetime.datetime.utcnow())

    def test_wildcard_covers_one_label_only(self):
        pem, key = make_certificate(san="*.example.org")
        certs.validate_upload(pem, key, None, "portal.example.org")
        with self.assertRaises(ValueError):
            certs.validate_upload(pem, key, None, "a.portal.example.org")

    def test_bad_uploads_are_rejected_without_quoting_the_key(self):
        pem, key = make_certificate()
        _, other_key = make_certificate()
        expired, expired_key = make_certificate(days=-1, start_days=-5)
        for args in ((pem, other_key, None, "portal.example.org"), (pem, key, None, "other.example.org"),
                     (expired, expired_key, None, "portal.example.org"), ("nope", key, None, "portal.example.org"),
                     (pem, "SECRET-KEY-TEXT", None, "portal.example.org")):
            with self.assertRaises(ValueError) as caught:
                certs.validate_upload(*args)
            self.assertNotIn("SECRET-KEY-TEXT", str(caught.exception))
            self.assertNotIn("PRIVATE KEY", str(caught.exception))

    def test_keys_are_encrypted_and_need_the_setting(self):
        with patch.object(certs.settings, "CERT_ENCRYPTION_KEY", "test-key"):
            token = certs.encrypt_private_key("KEY")
            self.assertNotIn(b"KEY", token)
            self.assertEqual(certs.decrypt_private_key(token), "KEY")
        with patch.object(certs.settings, "CERT_ENCRYPTION_KEY", ""):
            with self.assertRaises(RuntimeError):
                certs.encrypt_private_key("KEY")

    def test_response_schema_cannot_carry_key_material(self):
        fields = " ".join(CertificateOut.model_fields).lower()
        self.assertNotIn("encrypted", fields)
        self.assertNotIn("pem", fields)
        self.assertEqual([f for f in CertificateOut.model_fields if "key" in f], ["has_private_key"])

    def test_status_comes_from_expiry(self):
        now = datetime.datetime.utcnow()
        self.assertEqual(certs.status_for_expiry(None, 30), "Pending Issuance")
        self.assertEqual(certs.status_for_expiry(now - datetime.timedelta(days=1), 30), "Expired")
        self.assertEqual(certs.status_for_expiry(now + datetime.timedelta(days=5), 30), "Expiring Soon")
        self.assertEqual(certs.status_for_expiry(now + datetime.timedelta(days=90), 30), "Active")


class GatewayRenderTests(unittest.TestCase):
    def test_https_site_redirects_http_and_sets_hsts(self):
        output = render_site(Site(host="a.example.org", certificate_id="c1", fullchain="C", private_key="K", root_redirect="/login"))
        self.assertIn("return 301 https://$host$request_uri", output)
        self.assertIn("listen 8443 ssl", output)
        self.assertIn("Strict-Transport-Security", output)
        self.assertIn("return 302 /login", output)

    def test_site_waiting_for_a_certificate_serves_nothing_in_plain_http(self):
        output = render_site(Site(host="a.example.org"))
        self.assertIn("acme-challenge", output)
        self.assertNotIn("server_common", output)
        self.assertNotIn("8443", output)

    def test_unsafe_values_never_reach_the_config(self):
        for site in (Site(host="a.example.org; evil"), Site(host="a.example.org", root_redirect="/x; return 301 evil")):
            with self.assertRaises(ValueError):
                render_site(site)

    def test_candidate_writes_private_keys_owner_only_and_skips_repeats(self):
        files = render_files([Site(host="a.example.org", certificate_id="c1", fullchain="C", private_key="K")], [])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertTrue(write_candidate(files, root))
            self.assertEqual((root / "candidate/certs/c1.key").stat().st_mode & 0o777, 0o600)
            self.assertFalse(write_candidate(files, root))
            self.assertEqual(routing_status(root)["appliedVersion"], None)

    def test_rejected_candidate_is_not_written_again(self):
        files = render_files([], [])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_candidate(files, root)
            version = (root / "candidate/version").read_text()
            (root / "candidate/version").unlink()
            (root / "rejected_version").write_text(version)
            self.assertFalse(write_candidate(files, root))


def user(role="super_admin", tenant="GWMC"):
    return {"preferred_username": "tester", "realm_access": {"roles": [role]}, "tenant_id": tenant}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(app.dependency_overrides.clear)

    def use_db(self, db):
        app.dependency_overrides[get_read_db] = lambda: db
        app.dependency_overrides[get_write_db] = lambda: db

    def test_admin_routes_need_a_super_admin(self):
        paths = ["options", "tenants", "branding", "assets", "domains", "certificates", "mappings", "routing-status"]
        for role in ("citizen", "state_admin", "revenue_officer"):
            app.dependency_overrides[get_current_user] = lambda role=role: user(role)
            for path in paths:
                self.assertEqual(self.client.get(f"/api/v1/white-label/{path}").status_code, 403, f"{role} {path}")

    def test_admin_routes_need_a_login(self):
        self.assertEqual(self.client.get("/api/v1/white-label/domains").status_code, 401)
        self.assertEqual(self.client.post("/api/v1/white-label/certificates", data={}).status_code, 401)

    def domain(self, **overrides):
        values = dict(id="d1", tenant_id="GWMC", domain_name="portal.example.org", domain_type="Custom Domain", dns_record_type="CNAME",
                      dns_host="portal", dns_target="x", verification_method="DNS TXT", verification_status="Pending",
                      verification_token="t" * 64, is_primary=False, domain_status="Pending")
        return TenantDomain(**{**values, **overrides})

    def db_returning(self, *scalars):
        db = AsyncMock()
        db.add = MagicMock()
        db.scalar = AsyncMock(side_effect=list(scalars))
        return db

    def test_domain_cannot_activate_before_verification(self):
        app.dependency_overrides[get_current_user] = lambda: user()
        self.use_db(self.db_returning(self.domain()))
        response = self.client.put("/api/v1/white-label/domains/d1", json={
            "dnsRecordType": "CNAME", "dnsHost": "a", "dnsTarget": "b", "verificationMethod": "DNS TXT", "domainStatus": "Active",
        })
        self.assertEqual(response.status_code, 409)

    def test_domain_held_by_another_tenant_cannot_be_claimed(self):
        app.dependency_overrides[get_current_user] = lambda: user()
        # Tenant exists, then the ownership check finds another tenant's verified domain.
        self.use_db(self.db_returning("GWMC", "other-domain"))
        response = self.client.post("/api/v1/white-label/domains", json={
            "tenantId": "GWMC", "domainName": "portal.example.org", "domainType": "Custom Domain", "dnsRecordType": "CNAME",
            "dnsHost": "a", "dnsTarget": "b", "verificationMethod": "DNS TXT",
        })
        self.assertEqual(response.status_code, 409)
        self.assertNotIn("other-domain", response.text)

    def test_failed_verification_does_not_verify(self):
        app.dependency_overrides[get_current_user] = lambda: user()
        domain = self.domain()
        self.use_db(self.db_returning(domain, None))
        with patch.object(domains_api, "verify_domain", AsyncMock(return_value=VerificationResult(False, "Not found."))):
            response = self.client.post("/api/v1/white-label/domains/d1/verify")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["verificationStatus"], "Failed")

    def test_dns_outage_does_not_fail_a_claim(self):
        app.dependency_overrides[get_current_user] = lambda: user()
        domain = self.domain()
        self.use_db(self.db_returning(domain, None))
        with patch.object(domains_api, "verify_domain", AsyncMock(return_value=VerificationResult(False, "Down.", conclusive=False))):
            self.client.post("/api/v1/white-label/domains/d1/verify")
        self.assertEqual(domain.verification_status, "Pending")

    def test_certificate_needs_a_verified_domain(self):
        app.dependency_overrides[get_current_user] = lambda: user()
        self.use_db(self.db_returning(self.domain()))
        response = self.client.post("/api/v1/white-label/certificates", data={"domainId": "d1", "provider": rules.CERTIFICATE_ACME, "certificateType": "Domain Validated"})
        self.assertEqual(response.status_code, 409)

    def test_upload_error_never_echoes_the_private_key(self):
        app.dependency_overrides[get_current_user] = lambda: user()
        self.use_db(self.db_returning(self.domain(verification_status="Verified")))
        pem, _ = make_certificate()
        response = self.client.post(
            "/api/v1/white-label/certificates",
            data={"domainId": "d1", "provider": rules.CERTIFICATE_MANUAL, "certificateType": "Domain Validated", "privateKey": "SECRET-KEY-TEXT"},
            files={"certificate": ("c.pem", pem)},
        )
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("SECRET-KEY-TEXT", response.text)


if __name__ == "__main__":
    unittest.main()
