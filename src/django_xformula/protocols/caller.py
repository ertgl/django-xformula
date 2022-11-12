from typing import Callable, ParamSpec, Protocol, TypeVar, runtime_checkable

__all__ = [
    "Caller",
]


P = ParamSpec("P")

R = TypeVar("R")


@runtime_checkable
class Caller(Protocol):
    def __call__(
        self,
        callee: Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        ...
