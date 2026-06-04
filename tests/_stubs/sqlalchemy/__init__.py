"""Minimal stub of sqlalchemy used for tests.

Provides a `text` helper and exposes the `orm` submodule.
This stub avoids importing the real SQLAlchemy package during lightweight test runs.
"""
from . import orm

def text(sql_string):
    # Return the SQL string as-is; the test/mocked DB executor should accept it.
    return sql_string

__all__ = ["orm", "text"]
