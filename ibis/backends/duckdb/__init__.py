"""DuckDB backend."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import sqlalchemy as sa

if TYPE_CHECKING:
    import duckdb

import ibis.expr.schema as sch
from ibis.backends.base.sql.alchemy import BaseAlchemyBackend

from .compiler import DuckDBSQLCompiler
from .datatypes import parse_type


class Backend(BaseAlchemyBackend):
    name = "duckdb"
    compiler = DuckDBSQLCompiler

    def current_database(self) -> str:
        return "main"

    @property
    def version(self) -> str:
        # TODO: there is a `PRAGMA version` we could use instead
        try:
            import importlib.metadata as importlib_metadata
        except ImportError:
            # TODO: remove this when Python 3.9 support is dropped
            import importlib_metadata
        return importlib_metadata.version("duckdb")

    def do_connect(
        self,
        path: str | Path = ":memory:",
        read_only: bool = False,
    ) -> None:
        """Create an Ibis client connected to a DuckDB database.

        Parameters
        ----------
        path
            Path to a duckdb database
        read_only
            Whether the database is read-only
        """
        if path != ":memory:":
            path = Path(path).absolute()
        super().do_connect(
            sa.create_engine(
                f"duckdb:///{path}",
                connect_args={"read_only": read_only},
            )
        )
        self._meta = sa.MetaData(bind=self.con)

    def fetch_from_cursor(
        self,
        cursor: duckdb.DuckDBPyConnection,
        schema: sch.Schema,
    ):
        df = cursor.cursor.fetch_df()
        return schema.apply_to(df)

    def _get_schema_using_query(self, query: str) -> sch.Schema:
        """Return an ibis Schema from a SQL string."""
        with self.con.connect() as con:
            rel = con.connection.c.query(query)
        return sch.Schema.from_dict(
            {
                name: parse_type(type)
                for name, type in zip(rel.columns, rel.types)
            }
        )

    def _get_temp_view_definition(
        self,
        name: str,
        definition: sa.sql.compiler.Compiled,
    ) -> str:
        return f"CREATE OR REPLACE TEMPORARY VIEW {name} AS {definition}"
