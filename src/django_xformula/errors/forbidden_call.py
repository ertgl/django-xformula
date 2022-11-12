from typing import Any, Callable

from django.conf import settings
from django.core.exceptions import PermissionDenied

__all__ = [
    "ForbiddenCall",
]


class ForbiddenCall(PermissionDenied):

    callee: Callable

    args: tuple[Any, ...]

    kwargs: dict[str, Any]

    def __init__(
        self,
        callee: Callable,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        message: str | None = None,
    ) -> None:
        self.callee = callee
        self.args = args
        self.kwargs = kwargs
        if message is None:
            callee_str: str
            if not settings.DEBUG:
                callee_str = getattr(callee, "__name__", str(callee))
            else:
                callee_str = getattr(callee, "__name__", repr(callee))
            message = f"Forbidden call: {callee_str}"
        super(ForbiddenCall, self).__init__(message)
