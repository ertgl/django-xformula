from typing import Any

from django.conf import settings
from django.core.exceptions import PermissionDenied

__all__ = [
    "ForbiddenAttribute",
]


class ForbiddenAttribute(PermissionDenied):

    owner: Any

    attname: str

    def __init__(
        self,
        owner: Any,
        attname: str,
        message: str | None = None,
    ) -> None:
        self.owner = owner
        self.attname = attname
        if message is None:
            owner_str: str
            if not settings.DEBUG:
                owner_str = str(owner)
            else:
                owner_str = f"<{owner!r}>"
            message = f"Forbidden attribute: {owner_str}.{attname!s}"
        super(ForbiddenAttribute, self).__init__(message)
