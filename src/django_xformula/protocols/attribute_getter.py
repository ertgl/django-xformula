from typing import Any, Protocol, runtime_checkable

__all__ = [
    "AttributeGetter",
]


@runtime_checkable
class AttributeGetter(Protocol):
    def __call__(
        self,
        owner: Any,
        atname: str,
    ) -> Any:
        ...
