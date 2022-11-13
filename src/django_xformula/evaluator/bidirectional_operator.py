from operator import neg, pos
from types import NoneType
from typing import Any, Literal, TypeVar, cast, overload

from django.db.models import BooleanField, CharField, Field, Model, Q, QuerySet
from django.db.models.expressions import Case, Combinable, F, Value, When
from django.db.models.functions import Cast, Floor
from django.db.models.lookups import (
    Exact,
    GreaterThan,
    GreaterThanOrEqual,
    In,
    IsNull,
    LessThan,
    LessThanOrEqual,
    Lookup,
)
from django.db.models.options import Options

__all__ = [
    "BidirectionalOperator",
]

from django_xformula.db.lookups import Pure

T = TypeVar("T")


class BidirectionalOperator:
    @classmethod
    def is_constant(
        cls,
        py_object: Any,
    ) -> bool:
        return isinstance(
            py_object,
            (NoneType, bool, int, float, complex, str),
        )

    @classmethod
    def all_constant(
        cls,
        *py_objects: Any,
    ) -> bool:
        return all(map(cls.is_constant, py_objects))

    @classmethod
    @overload
    def is_combinable(
        cls,
        combinable: Combinable,
    ) -> Literal[True]:
        ...

    @classmethod
    @overload
    def is_combinable(
        cls,
        py_object: T,
    ) -> Literal[False]:
        ...

    @classmethod
    def is_combinable(
        cls,
        py_object,
    ):
        return isinstance(py_object, Combinable)

    @classmethod
    def any_combinable(
        cls,
        *py_objects: Any,
    ) -> bool:
        return any(map(cls.is_combinable, py_objects))

    @classmethod
    @overload
    def can_be_combinable(
        cls,
        q: Q,
    ) -> Literal[False]:
        ...

    @classmethod
    @overload
    def can_be_combinable(
        cls,
        queryset: QuerySet,
    ) -> Literal[False]:
        ...

    @classmethod
    @overload
    def can_be_combinable(
        cls,
        combinable: Combinable,
    ) -> Literal[False]:
        ...

    @classmethod
    @overload
    def can_be_combinable(
        cls,
        py_object: Any,
    ) -> Literal[True]:
        ...

    @classmethod
    def can_be_combinable(
        cls,
        py_object,
    ):
        return not isinstance(
            py_object,
            (
                Q,
                QuerySet,  # type: ignore[misc]
            ),
        )

    @classmethod
    def any_can_be_combinable(
        cls,
        *py_objects: Any,
    ) -> bool:
        return any(map(cls.can_be_combinable, py_objects))

    @classmethod
    @overload
    def ensure_if_combinable(
        cls,
        q: Q,
    ) -> Q:
        ...

    @classmethod
    @overload
    def ensure_if_combinable(
        cls,
        queryset: QuerySet,  # type: ignore[misc]
    ) -> QuerySet:  # type: ignore[misc]
        ...

    @classmethod
    @overload
    def ensure_if_combinable(
        cls,
        maybe_combinable: Any,
    ) -> Combinable:
        ...

    @classmethod
    def ensure_if_combinable(
        cls,
        py_object,
    ):
        if not cls.can_be_combinable(py_object):
            return py_object

        if cls.is_combinable(py_object):
            return py_object

        if cls.is_model_field(py_object):
            field = cast(Field, py_object)
            return F(field.attname)

        if cls.is_model_instance(py_object):
            model_instance = cast(Model, py_object)
            model_options = cast(
                Options,
                getattr(model_instance.__class__, "_meta", None),
            )
            pk_field = cast(
                str | Field | None,
                getattr(model_options, "pk", None),
            )
            pk_field_attname = (
                pk_field
                if isinstance(pk_field, str)
                else getattr(pk_field, "attname", "pk")
            )
            pk = getattr(model_instance, pk_field_attname)
            return pk

        return Value(py_object)

    @classmethod
    def test_combinable(
        cls,
        combinable: Combinable,
        negated: bool = False,
    ) -> Combinable:
        return Case(
            When(
                In(
                    Cast(combinable, CharField()),
                    [
                        Cast(Value(None), CharField()),
                        Cast(Value(False), CharField()),
                        Cast(Value(0), CharField()),
                        Cast(Value(0.0), CharField()),
                        Cast(Value(""), CharField()),
                    ],
                ),
                then=Value(True if negated else False),
            ),
            default=Value(False if negated else True),
            output_field=BooleanField(),
        )

    @classmethod
    @overload
    def is_model_field(
        cls,
        model: Field,
    ) -> Literal[True]:
        ...

    @classmethod
    @overload
    def is_model_field(
        cls,
        py_object: T,
    ) -> Literal[False]:
        ...

    @classmethod
    def is_model_field(
        cls,
        py_object,
    ):
        return isinstance(py_object, Field)

    @classmethod
    @overload
    def is_model_instance(
        cls,
        model: Model,
    ) -> Literal[True]:
        ...

    @classmethod
    @overload
    def is_model_instance(
        cls,
        py_object: T,
    ) -> Literal[False]:
        ...

    @classmethod
    def is_model_instance(
        cls,
        py_object,
    ):
        return isinstance(py_object, Model)

    @classmethod
    @overload
    def is_q(
        cls,
        q: Q,
    ) -> Literal[True]:
        ...

    @classmethod
    @overload
    def is_q(
        cls,
        py_object: T,
    ) -> Literal[False]:
        ...

    @classmethod
    def is_q(
        cls,
        py_object,
    ):
        return isinstance(py_object, Q)

    @classmethod
    @overload
    def ensure_if_q(
        cls,
        combinable: Combinable,
    ) -> Q:
        ...

    @classmethod
    @overload
    def ensure_if_q(
        cls,
        q: Q,
    ) -> Q:
        ...

    @classmethod
    @overload
    def ensure_if_q(
        cls,
        queryset: QuerySet,  # type: ignore[misc]
    ) -> QuerySet:  # type: ignore[misc]
        ...

    @classmethod
    @overload
    def ensure_if_q(
        cls,
        py_object: T,
    ) -> Q:
        ...

    @classmethod
    def ensure_if_q(
        cls,
        py_object,
    ):
        if cls.is_q(py_object):
            return py_object

        if cls.is_queryset(py_object):
            return py_object

        combinable = cls.ensure_if_combinable(py_object)

        if isinstance(combinable, Lookup):
            return Q(combinable)

        return Q(cls.test_combinable(combinable))

    @classmethod
    @overload
    def is_queryset(
        cls,
        queryset: QuerySet,
    ) -> Literal[True]:
        ...

    @classmethod
    @overload
    def is_queryset(
        cls,
        py_object: T,
    ) -> Literal[False]:
        ...

    @classmethod
    def is_queryset(
        cls,
        py_object,
    ):
        return isinstance(
            py_object,
            QuerySet,  # type: ignore[misc]
        )

    @classmethod
    def any_queryable(
        cls,
        *py_objects: Any,
    ) -> bool:
        return any(
            map(
                lambda py_object: (
                    cls.is_combinable(py_object)
                    or cls.is_model_field(py_object)
                    or cls.is_model_instance(py_object)
                    or cls.is_q(py_object)
                    or cls.is_queryset(py_object)
                ),
                py_objects,
            ),
        )

    @classmethod
    @overload
    def ensure_py_object(
        cls,
        value: Value,
    ) -> Any:
        ...

    @classmethod
    @overload
    def ensure_py_object(
        cls,
        py_object: T,
    ) -> T:
        ...

    @classmethod
    def ensure_py_object(
        cls,
        py_object,
    ):
        if isinstance(py_object, Value):
            return py_object.value
        return py_object

    @classmethod
    def pos(
        cls,
        py_object: Any,
    ) -> Any:
        if not cls.is_combinable(py_object):
            return pos(py_object)

        return py_object

    @classmethod
    def neg(
        cls,
        py_object: Any,
    ) -> Any:
        if cls.is_q(py_object):
            return ~py_object

        if cls.is_queryset(py_object):
            queryset = cast(QuerySet, py_object)
            return queryset.model.objects.difference(queryset)

        return neg(py_object)

    @classmethod
    def not_(
        cls,
        py_object: Any,
    ) -> Any:
        if cls.is_q(py_object):
            return ~py_object

        if cls.is_queryset(py_object):
            queryset = cast(QuerySet, py_object)
            return queryset.model.objects.difference(queryset)

        if cls.is_combinable(py_object):
            combinable = cast(Combinable, py_object)
            return cls.test_combinable(
                combinable,
                negated=True,
            )

        return not py_object

    @classmethod
    def inv(
        cls,
        py_object: Any,
    ) -> Any:
        if cls.is_q(py_object):
            return ~py_object

        if cls.is_queryset(py_object):
            queryset = cast(QuerySet, py_object)
            return queryset.model.objects.difference(queryset)

        if cls.is_combinable(py_object):
            combinable = cast(Combinable, py_object)
            return cls.test_combinable(
                combinable,
                negated=True,
            )

        return ~py_object

    @classmethod
    def pow(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lhs**rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return lhs**rhs

    @classmethod
    def mul(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lhs * rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return lhs * rhs

    @classmethod
    def truediv(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lhs / rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return lhs / rhs

    @classmethod
    def floordiv(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lhs // rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return Floor(lhs / rhs)

    @classmethod
    def mod(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lhs % rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return lhs % rhs

    @classmethod
    def add(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_queryable(lhs, rhs):
            return lhs + rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.is_combinable(lhs) and cls.is_combinable(rhs):
            return lhs + rhs

        lhs = cls.ensure_if_q(lhs)
        rhs = cls.ensure_if_q(rhs)

        if cls.is_queryset(lhs) and cls.is_queryset(rhs):
            return lhs.union(rhs)

        if cls.is_queryset(lhs) and not cls.is_queryset(rhs):
            return lhs.union(lhs.model.objects.filter(rhs))

        if not cls.is_queryset(lhs) and cls.is_queryset(rhs):
            return rhs.model.objects.filter(lhs).union(rhs)

        return lhs | rhs

    @classmethod
    def sub(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_queryable(lhs, rhs):
            return lhs - rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.is_combinable(lhs) and cls.is_combinable(rhs):
            return lhs - rhs

        lhs = cls.ensure_if_q(lhs)
        rhs = cls.ensure_if_q(rhs)

        if cls.is_queryset(lhs) and cls.is_queryset(rhs):
            return lhs.difference(rhs)

        if cls.is_queryset(lhs) and not cls.is_queryset(rhs):
            return lhs.filter(~rhs)

        if not cls.is_queryset(lhs) and cls.is_queryset(rhs):
            return rhs.model.objects.filter(lhs).difference(rhs)

        return lhs & ~rhs

    @classmethod
    def lshift(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lhs << rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return lhs.bitleftshift(rhs)  # type: ignore[arg-type]

    @classmethod
    def rshift(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lhs >> rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return lhs.bitrightshift(rhs)  # type: ignore[arg-type]

    @classmethod
    def iand(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_queryable(lhs, rhs):
            return lhs & rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.is_combinable(lhs) and cls.is_combinable(rhs):
            return lhs.bitand(rhs)  # type: ignore[arg-type]

        lhs = cls.ensure_if_q(lhs)
        rhs = cls.ensure_if_q(rhs)

        return lhs & rhs

    @classmethod
    def xor(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_queryable(lhs, rhs):
            return lhs ^ rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.is_combinable(lhs) and cls.is_combinable(rhs):
            return lhs.bitxor(rhs)  # type: ignore[arg-type]

        lhs = cls.ensure_if_q(lhs)
        rhs = cls.ensure_if_q(rhs)

        return lhs ^ rhs

    @classmethod
    def ior(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_queryable(lhs, rhs):
            return lhs | rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.is_combinable(lhs) and cls.is_combinable(rhs):
            return lhs.bitor(rhs)  # type: ignore[arg-type]

        lhs = cls.ensure_if_q(lhs)
        rhs = cls.ensure_if_q(rhs)

        return lhs | rhs

    @classmethod
    def nin(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_queryable(lhs, rhs):
            return lhs not in rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.is_combinable(lhs) and cls.is_combinable(rhs):
            return Exact(In(lhs, rhs), Value(False))

        lhs = cls.ensure_if_q(lhs)
        rhs = cls.ensure_if_q(rhs)

        if cls.is_queryset(lhs) and cls.is_queryset(rhs):
            return lhs.difference(rhs)

        if cls.is_queryset(lhs) and not cls.is_queryset(rhs):
            return lhs.filter(~rhs)

        if not cls.is_queryset(lhs) and cls.is_queryset(rhs):
            return rhs.model.objects.filter(lhs).difference(rhs)

        return lhs & ~rhs

    @classmethod
    def in_(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_queryable(lhs, rhs):
            return lhs in rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.is_combinable(lhs) and cls.is_combinable(rhs):
            return In(lhs, rhs)

        lhs = cls.ensure_if_q(lhs)
        rhs = cls.ensure_if_q(rhs)

        if cls.is_queryset(lhs) and cls.is_queryset(rhs):
            return lhs.intersection(rhs)

        if cls.is_queryset(lhs) and not cls.is_queryset(rhs):
            return lhs.intersection(lhs.model.objects.filter(rhs))

        if not cls.is_queryset(lhs) and cls.is_queryset(rhs):
            return rhs.model.objects.filter(lhs).intersection(rhs)

        return lhs & rhs

    @classmethod
    def is_not(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_queryable(lhs, rhs):
            if cls.all_constant(lhs, rhs):
                return lhs != rhs
            return lhs is not rhs

        lhs = cls.ensure_py_object(lhs)
        rhs = cls.ensure_py_object(rhs)

        if lhs is None and rhs is None:
            return IsNull(Value(None), Value(False))

        if lhs is None and rhs is not None:
            return IsNull(rhs, Value(False))

        if lhs is not None and rhs is None:
            return IsNull(lhs, Value(False))

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return Exact(Exact(lhs, rhs), Value(False))

    @classmethod
    def is_(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_queryable(lhs, rhs):
            if cls.all_constant(lhs, rhs):
                return lhs == rhs
            return lhs is rhs

        lhs = cls.ensure_py_object(lhs)
        rhs = cls.ensure_py_object(rhs)

        if lhs is None and rhs is None:
            return IsNull(Value(None), Value(True))

        if lhs is None and rhs is not None:
            return IsNull(rhs, Value(True))

        if lhs is not None and rhs is None:
            return IsNull(lhs, Value(True))

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return Exact(lhs, rhs)

    @classmethod
    def gt(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lhs > rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return GreaterThan(lhs, rhs)

    @classmethod
    def ge(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lhs > rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return GreaterThanOrEqual(lhs, rhs)

    @classmethod
    def le(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lhs > rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return LessThanOrEqual(lhs, rhs)

    @classmethod
    def lt(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lhs > rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return LessThan(lhs, rhs)

    @classmethod
    def ne(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_queryable(lhs, rhs):
            return lhs != rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.is_combinable(lhs) and cls.is_combinable(rhs):
            return Exact(Exact(lhs, rhs), Value(False))

        lhs = cls.ensure_if_q(lhs)
        rhs = cls.ensure_if_q(rhs)

        if cls.is_queryset(lhs) and cls.is_queryset(rhs):
            return lhs.difference(rhs)

        if cls.is_queryset(lhs) and not cls.is_queryset(rhs):
            return lhs.filter(~rhs)

        if not cls.is_queryset(lhs) and cls.is_queryset(rhs):
            return rhs.model.objects.filter(lhs).difference(rhs)

        return lhs & ~rhs

    @classmethod
    def eq(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_queryable(lhs, rhs):
            return lhs == rhs

        lhs = cls.ensure_py_object(lhs)
        rhs = cls.ensure_py_object(rhs)

        if lhs is None and rhs is None:
            return IsNull(Value(None), Value(True))

        if lhs is None and rhs is not None:
            return IsNull(rhs, Value(True))

        if lhs is not None and rhs is None:
            return IsNull(lhs, Value(True))

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return Exact(lhs, rhs)

    @classmethod
    def and_(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_queryable(lhs, rhs):
            return lhs and rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        lhs = cls.ensure_if_q(lhs)
        rhs = cls.ensure_if_q(rhs)

        return lhs & rhs

    @classmethod
    def or_(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_queryable(lhs, rhs):
            return lhs or rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        lhs = cls.ensure_if_q(lhs)
        rhs = cls.ensure_if_q(rhs)

        return lhs | rhs

    @classmethod
    def cond(
        cls,
        test: Any,
        then: Any,
        default: Any,
    ) -> Any:
        if not cls.any_combinable(test, then, default):
            return then if test else default

        test = cls.ensure_if_q(test)

        then = cls.ensure_if_combinable(then)
        default = cls.ensure_if_combinable(default)

        if cls.is_q(then) or cls.is_q(default):

            if cls.is_combinable(then) and not isinstance(then, Lookup):
                then = Pure(then)

            then = cls.ensure_if_q(then)

            if cls.is_combinable(default) and not isinstance(default, Lookup):
                default = Pure(default)

            default = cls.ensure_if_q(default)

        return Case(
            When(test, then=then),
            default=default,
        )
