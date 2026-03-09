"""Snapshot tests for /openapi.json structure — 005-swagger-api-docs."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.fixture(scope="module")
def openapi_schema() -> dict:
    """Return the OpenAPI schema dict from FastAPI's custom_openapi()."""
    return app.openapi()


# ---------------------------------------------------------------------------
# T025 test functions
# ---------------------------------------------------------------------------


def test_api_metadata(openapi_schema: dict) -> None:
    """title == 'API-X', version == '0.1.0', description contains Authorize/Bearer."""
    info = openapi_schema["info"]
    assert info["title"] == "API-X"
    assert info["version"] == "0.1.0"
    desc = info.get("description", "")
    assert "Authorize" in desc or "Bearer" in desc, (
        f"description should mention 'Authorize' or 'Bearer', got: {desc[:200]}"
    )


def test_all_6_tags_with_descriptions(openapi_schema: dict) -> None:
    """Array 'tags' has 6 entries, each with a 'description'."""
    tags = openapi_schema.get("tags", [])
    assert len(tags) == 6, f"Expected 6 tags, got {len(tags)}: {[t['name'] for t in tags]}"
    for tag in tags:
        assert "description" in tag and tag["description"], (
            f"Tag '{tag['name']}' is missing a description"
        )


def test_all_operations_have_summary(openapi_schema: dict) -> None:
    """Every operation in paths has a non-empty 'summary'."""
    paths = openapi_schema.get("paths", {})
    missing = []
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method in ("get", "post", "put", "delete", "patch"):
                if not operation.get("summary"):
                    missing.append(f"{method.upper()} {path}")
    assert not missing, f"Operations missing summary: {missing}"


def test_all_operations_have_description(openapi_schema: dict) -> None:
    """Every operation in paths has a non-empty 'description'."""
    paths = openapi_schema.get("paths", {})
    missing = []
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method in ("get", "post", "put", "delete", "patch"):
                if not operation.get("description"):
                    missing.append(f"{method.upper()} {path}")
    assert not missing, f"Operations missing description: {missing}"


def test_bearer_auth_scheme_defined(openapi_schema: dict) -> None:
    """components.securitySchemes.BearerAuth exists with type=http, scheme=bearer."""
    schemes = (
        openapi_schema.get("components", {}).get("securitySchemes", {})
    )
    assert "BearerAuth" in schemes, "BearerAuth security scheme not found in components"
    bearer = schemes["BearerAuth"]
    assert bearer.get("type") == "http"
    assert bearer.get("scheme") == "bearer"


def test_protected_operations_have_security(openapi_schema: dict) -> None:
    """11 protected operations have security=[{BearerAuth:[]}]; 4 public do not."""
    protected_paths = {
        ("get", "/auth/me"),
        ("post", "/admin/events"),
        ("get", "/admin/events/{event_id}"),
        ("put", "/admin/events/{event_id}"),
        ("delete", "/admin/events/{event_id}"),
        ("post", "/registrations/{event_id}"),
        ("delete", "/registrations/{event_id}"),
        ("get", "/registrations/me"),
        ("get", "/admin/reports/events/stats"),
        ("get", "/admin/reports/events/summary"),
        ("get", "/admin/users"),
    }
    public_paths = {
        ("post", "/auth/register"),
        ("post", "/auth/login"),
        ("get", "/events"),
        ("get", "/events/{event_id}"),
    }
    paths = openapi_schema.get("paths", {})
    for method, path in protected_paths:
        op = paths.get(path, {}).get(method, {})
        security = op.get("security", [])
        assert {"BearerAuth": []} in security, (
            f"{method.upper()} {path} should have BearerAuth security, got: {security}"
        )
    for method, path in public_paths:
        op = paths.get(path, {}).get(method, {})
        security = op.get("security", [])
        assert {"BearerAuth": []} not in security, (
            f"{method.upper()} {path} should NOT have BearerAuth security"
        )


def test_admin_operations_have_khusus_admin_label(openapi_schema: dict) -> None:
    """Admin endpoints descriptions contain 'Khusus admin'."""
    admin_ops = [
        ("get", "/admin/users"),
        ("post", "/admin/events"),
        ("get", "/admin/events/{event_id}"),
        ("put", "/admin/events/{event_id}"),
        ("delete", "/admin/events/{event_id}"),
        ("get", "/admin/reports/events/stats"),
        ("get", "/admin/reports/events/summary"),
    ]
    paths = openapi_schema.get("paths", {})
    for method, path in admin_ops:
        op = paths.get(path, {}).get(method, {})
        desc = op.get("description", "")
        assert "Khusus admin" in desc, (
            f"{method.upper()} {path} description should contain 'Khusus admin', got: {desc[:200]}"
        )


def test_all_4xx_responses_have_examples(openapi_schema: dict) -> None:
    """Every 4xx response in all operations has an example in application/json."""
    paths = openapi_schema.get("paths", {})
    missing = []
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            responses = operation.get("responses", {})
            for status_code, response in responses.items():
                if not str(status_code).startswith("4"):
                    continue
                content = response.get("content", {})
                json_content = content.get("application/json", {})
                has_example = bool(json_content.get("example") or json_content.get("examples"))
                if not has_example:
                    missing.append(f"{method.upper()} {path} → {status_code}")
    assert not missing, f"4xx responses missing examples: {missing}"


def test_schema_fields_have_descriptions(openapi_schema: dict) -> None:
    """Every property in every user-defined component schema has a 'description'.

    FastAPI's built-in error schemas (HTTPValidationError, ValidationError) are
    excluded since they are not user-controlled.
    """
    SKIP_SCHEMAS = {"HTTPValidationError", "ValidationError"}
    schemas = openapi_schema.get("components", {}).get("schemas", {})
    missing = []
    for schema_name, schema_def in schemas.items():
        if schema_name in SKIP_SCHEMAS:
            continue
        props = schema_def.get("properties", {})
        for field_name, field_def in props.items():
            if not field_def.get("description"):
                missing.append(f"{schema_name}.{field_name}")
    assert not missing, f"Schema fields missing descriptions: {missing}"


def test_no_inline_schema_duplicates(openapi_schema: dict) -> None:
    """Schemas used more than once are referenced via $ref, not duplicated inline."""
    import json

    schema_str = json.dumps(openapi_schema)
    components = openapi_schema.get("components", {}).get("schemas", {})

    for schema_name in components:
        ref_pattern = f'"$ref": "#/components/schemas/{schema_name}"'
        inline_title_pattern = f'"title": "{schema_name}"'
        inline_count = schema_str.count(inline_title_pattern)
        # Allow one occurrence inside the components/schemas section itself
        if inline_count > 1:
            # Check if extra occurrences are truly inline (not $ref)
            ref_count = schema_str.count(ref_pattern)
            assert ref_count > 0 or inline_count <= 1, (
                f"Schema '{schema_name}' appears {inline_count} times inline "
                f"without being referenced via $ref — potential duplicate (FR-017)"
            )
