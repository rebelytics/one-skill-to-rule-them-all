"""Shared test fixtures.

Both scripts live in `scripts/` and are not a package. Worse, one of them is
named `migrate-log.py` — a filename whose base is not a valid Python
identifier, so it cannot be imported by name at all. Load both by path with
importlib so tests can call their functions directly.
"""

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def migrate():
    return _load("migrate_log", "scripts/migrate-log.py")


@pytest.fixture(scope="session")
def validate():
    return _load("validate_skill_bundle", "scripts/validate-skill-bundle.py")


@pytest.fixture(scope="session")
def audit():
    return _load("audit_siblings", "scripts/audit-siblings.py")
