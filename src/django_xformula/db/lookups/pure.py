from typing import Any

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import Lookup
from django.db.models.sql.compiler import SQLCompiler

__all__ = [
    "Pure",
]


class Pure(Lookup):

    prepare_rhs = False

    can_use_none_as_rhs = True

    def __init__(
        self,
        expression: Any,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super(Pure, self).__init__(expression, None)

    def as_sql(
        self,
        compiler: SQLCompiler,
        connection: BaseDatabaseWrapper,
    ) -> tuple[str, Any]:
        lhs_sql, params = self.process_lhs(compiler, connection)
        return "%s" % lhs_sql, params

    def __repr__(self) -> str:
        return repr(self.lhs)
