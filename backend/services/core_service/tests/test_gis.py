"""Run from backend/services/core_service: python -m unittest discover -s tests"""
import os
import unittest

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-only-signing-key"
os.environ["AUDIT_SIGNING_KEY"] = "test-only-audit-key"

from fastapi import HTTPException
from fastapi.testclient import TestClient

from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError

from app.api.v1.gis import WIDTH_SQL, _srid, _validate_layer, declared_crs, parse_bbox, resolve_scope, url_is_approved
from app.api.v1.gis_services import host_is_public, normalize_service_url
from app.core.auth import get_current_user
from app.db.rls import RLS_TABLES
from app.main import app
from app.schemas.gis import GisLayerPayload, GisWorkspacePayload, GisWorkspaceResponse


def layer(**overrides):
    values = dict(tenantId="GWMC", layerName="L", layerCode="L", layerCategory="Road", layerType="Line", dataSource="PostGIS", crs="EPSG:4326", layerStatus="Active")
    return GisLayerPayload(**{**values, **overrides})


class GisValidationTests(unittest.TestCase):
    def test_unknown_crs_rejected(self):
        with self.assertRaises(HTTPException):
            _srid("EPSG:9999")

    def test_remote_layer_needs_service_details(self):
        with self.assertRaises(HTTPException):
            _validate_layer(layer(dataSource="WMS"))

    def test_service_url_scheme_is_restricted(self):
        with self.assertRaises(HTTPException):
            _validate_layer(layer(dataSource="WMS", serviceUrl="javascript:alert(1)", layerIdentifier="roads"))

    def test_identifier_cannot_inject_parameters(self):
        with self.assertRaises(HTTPException):
            _validate_layer(layer(dataSource="WFS", serviceUrl="https://gis.example.org/wfs", layerIdentifier="a&b=c"))

    def test_valid_remote_layer_passes(self):
        _validate_layer(layer(dataSource="WFS", serviceUrl="https://gis.example.org/wfs", layerIdentifier="city:roads"))


class GisAccessTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.addCleanup(app.dependency_overrides.clear)

    def routes(self):
        for path, operations in app.openapi()["paths"].items():
            if path.startswith("/api/v1/executive/gis"):
                for method in operations:
                    yield method.upper(), path.replace("{", "").replace("}", "")

    def test_all_routes_reject_anonymous(self):
        routes = list(self.routes())
        self.assertGreater(len(routes), 8)
        for method, path in routes:
            with self.subTest(path=path):
                self.assertEqual(self.client.request(method, path).status_code, 401)

    def test_citizens_are_refused(self):
        app.dependency_overrides[get_current_user] = lambda: {"realm_access": {"roles": ["citizen"]}, "tenant_id": "GWMC"}
        for method, path in self.routes():
            with self.subTest(path=path):
                self.assertEqual(self.client.request(method, path).status_code, 403)

    def test_spatial_tables_have_rls(self):
        self.assertIn("gis_layers", RLS_TABLES)
        self.assertIn("gis_features", RLS_TABLES)


class GisRuleTests(unittest.TestCase):
    def test_approved_url_compares_origin_and_path_segments(self):
        approved = ["https://gis.example.org/geoserver"]
        self.assertTrue(url_is_approved("https://gis.example.org/geoserver/wms", approved))
        self.assertTrue(url_is_approved("https://gis.example.org/geoserver", approved))
        for bad in ("https://gis.example.org.evil.test/geoserver/wms", "http://gis.example.org/geoserver/wms", "https://gis.example.org/geoserver2/wms", "https://gis.example.org/other", None):
            self.assertFalse(url_is_approved(bad, approved), bad)

    def test_service_urls_cannot_carry_passwords_or_queries(self):
        for bad in ("https://user:pw@gis.example.org/wms", "https://gis.example.org/wms?x=1", "ftp://gis.example.org", "nonsense"):
            with self.assertRaises(HTTPException, msg=bad):
                normalize_service_url(bad)
        with patch("app.api.v1.gis_services.host_is_public", return_value=True):
            self.assertEqual(normalize_service_url("https://gis.example.org/wms/"), "https://gis.example.org/wms")

    def test_private_hosts_are_not_public(self):
        for host in ("127.0.0.1", "localhost", "169.254.169.254", "10.0.0.5"):
            self.assertFalse(host_is_public(host), host)

    def test_declared_crs_is_read_from_the_file(self):
        self.assertIsNone(declared_crs({}))
        self.assertEqual(declared_crs({"crs": {"properties": {"name": "urn:ogc:def:crs:EPSG::32644"}}}), "EPSG:32644")
        self.assertEqual(declared_crs({"crs": {"properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}}}), "EPSG:4326")

    def test_bbox_is_kept_on_the_globe(self):
        self.assertEqual(parse_bbox("-200,-95,200,95"), [-180.0, -90.0, 180.0, 90.0])
        with self.assertRaises(HTTPException):
            parse_bbox("1,2,3")

    def test_workspace_extent_and_zoom_are_validated(self):
        values = dict(geographicScope="Custom Extent", baseMap="osm", crs="EPSG:4326")
        with self.assertRaises(ValidationError):
            GisWorkspacePayload(**values, mapExtent=[80, 17, 79, 18])
        with self.assertRaises(ValidationError):
            GisWorkspacePayload(**values, defaultCentre=[100, 80])
        self.assertEqual(GisWorkspacePayload(**values, mapExtent=[79, 17, 80, 18]).mapExtent, [79, 17, 80, 18])

    def test_older_saved_values_still_load(self):
        saved = GisWorkspaceResponse(id="1", geographicScope="Custom Extent", baseMap="osm", crs="EPSG:4326", mapExtent=[17, 79, 18, 80, 0.5], defaultCentre=[500, 500])
        self.assertEqual(saved.defaultCentre, [500, 500])

    def test_width_filter_cannot_fail_on_text(self):
        self.assertIn("CASE WHEN", WIDTH_SQL)

    def test_new_table_has_rls(self):
        self.assertIn("gis_approved_services", RLS_TABLES)


class ScopeTests(unittest.IsolatedAsyncioTestCase):
    def db_with(self, *tenants):
        result = MagicMock()
        result.all.return_value = list(tenants)
        db = AsyncMock()
        db.scalars = AsyncMock(return_value=result)
        return db

    def tenant(self, code, state):
        return MagicMock(tenant_id=code, state_code=state)

    USER = {"realm_access": {"roles": ["super_admin"]}}

    async def test_outside_access_is_refused_not_widened(self):
        db = self.db_with(self.tenant("GWMC", "TG"))
        for states, ulbs in ((["MH"], []), ([], ["PMC"])):
            with self.assertRaises(HTTPException) as caught:
                await resolve_scope("Selected ULBs" if ulbs else "Selected States", states, ulbs, None, self.USER, db)
            self.assertEqual(caught.exception.status_code, 403)

    async def test_each_scope_needs_its_selection(self):
        db = self.db_with()
        for scope in ("Selected States", "Selected ULBs", "Custom Extent", "Unknown"):
            with self.assertRaises(HTTPException) as caught:
                await resolve_scope(scope, [], [], None, self.USER, db)
            self.assertEqual(caught.exception.status_code, 422, scope)

    async def test_scope_narrows(self):
        db = self.db_with(self.tenant("GWMC", "TG"), self.tenant("PMC", "MH"))
        self.assertEqual([t.tenant_id for t in await resolve_scope("Selected States", ["TG"], [], None, self.USER, db)], ["GWMC"])
        self.assertEqual(len(await resolve_scope("All Accessible States", [], [], None, self.USER, db)), 2)
