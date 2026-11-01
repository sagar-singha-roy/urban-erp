"""Run from backend/services/core_service: python -m unittest discover -s tests"""
import os
import unittest

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-only-signing-key"
os.environ["AUDIT_SIGNING_KEY"] = "test-only-audit-key"

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.gis import _srid, _validate_layer
from app.core.auth import get_current_user
from app.db.rls import RLS_TABLES
from app.main import app
from app.schemas.gis import GisLayerPayload


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
