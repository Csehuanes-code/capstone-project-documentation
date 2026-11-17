"""Architecture boundary tests verifying Clean Architecture invariants (ADR-02, ADR-09, EC-MANT-01)."""

from __future__ import annotations

import ast
from pathlib import Path


def _get_imports(file_path: Path) -> list[str]:
    """Parse a Python file and return all imported module names."""
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def test_domain_layer_has_zero_outer_dependencies() -> None:
    """Domain layer must NOT import from application, api, infrastructure, fastapi, sqlalchemy, or pydantic."""
    domain_dir = Path(__file__).parent.parent.parent / "catalog_service" / "domain"
    forbidden_prefixes = (
        "catalog_service.application",
        "catalog_service.api",
        "catalog_service.infrastructure",
        "fastapi",
        "sqlalchemy",
        "pydantic",
        "httpx",
    )

    for py_file in domain_dir.glob("*.py"):
        imports = _get_imports(py_file)
        for imp in imports:
            for forbidden in forbidden_prefixes:
                assert not imp.startswith(forbidden), (
                    f"Clean Architecture violation in {py_file.name}: "
                    f"domain imports '{imp}', which is forbidden ({forbidden})."
                )


def test_application_layer_has_zero_infrastructure_or_api_dependencies() -> None:
    """Application layer must NOT import from api, infrastructure, fastapi, or sqlalchemy."""
    app_dir = Path(__file__).parent.parent.parent / "catalog_service" / "application"
    forbidden_prefixes = (
        "catalog_service.api",
        "catalog_service.infrastructure",
        "fastapi",
        "sqlalchemy",
    )

    for py_file in app_dir.glob("*.py"):
        imports = _get_imports(py_file)
        for imp in imports:
            for forbidden in forbidden_prefixes:
                assert not imp.startswith(forbidden), (
                    f"Clean Architecture violation in {py_file.name}: "
                    f"application imports '{imp}', which is forbidden ({forbidden})."
                )
