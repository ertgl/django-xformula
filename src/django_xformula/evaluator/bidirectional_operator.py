from decimal import Decimal
from operator import (
    add,
    eq,
    floordiv,
    ge,
    gt,
    iand,
    inv,
    ior,
    is_,
    is_not,
    le,
    lshift,
    lt,
    mod,
    ne,
    neg,
    not_,
    pos,
    rshift,
    sub,
    truediv,
)
from types import NoneType
from typing import Any, TypeGuard, TypeVar, cast, overload

from django.db.models import BooleanField, Field, Model, Q
from django.db.models.expressions import (
    BaseExpression,
    Case,
    Combinable,
    F,
    Value,
    When,
)
from django.db.models.functions import Floor
from django.db.models.lookups import (
    Exact,
    GreaterThan,
    GreaterThanOrEqual,
    In,
    IsNull,
    LessThan,
    LessThanOrEqual,
)
from django.db.models.options import Options

from django_xformula.db.lookups import Pure

__all__ = [
    "BidirectionalOperator",
]


T = TypeVar("T")


class BidirectionalOperator:
    class QEnum:

        EMPTY = Q()

        # Pointer; will not belong to any query.
        NEGATED = ~Q(Exact(Value(False), Value(False)))

    class Optimization:

        LITERAL_TYPES = (
            NoneType,
            bool,
            int,
            float,
            complex,
            str,
        )

        EXCLUDED_TYPES: dict[str, tuple[type, ...]] = dict(
            # Floating-point arithmetic implementations may vary
            # between DBs / runtimes.
            # For consistency of results, get operations done, in DBs.
            arithmetic=(float, Decimal),
            bitwise=(float, Decimal),
            compare=(float, Decimal),
            logical=(float, Decimal),
        )

    @classmethod
    def is_q(
        cls,
        py_value: Any,
    ) -> TypeGuard[Q]:
        return isinstance(py_value, Q)

    @classmethod
    @overload
    def is_q_or_combinable(
        cls,
        q: Q,
    ) -> TypeGuard[Q]:
        ...

    @classmethod
    @overload
    def is_q_or_combinable(
        cls,
        combinable: Combinable,
    ) -> TypeGuard[Combinable]:
        ...

    @classmethod
    def is_q_or_combinable(
        cls,
        py_value,
    ):
        return cls.is_q(py_value) or cls.is_combinable(py_value)

    @classmethod
    def is_expression(
        cls,
        py_value: Any,
    ) -> TypeGuard[BaseExpression]:
        return isinstance(py_value, BaseExpression)

    @classmethod
    def is_combinable(
        cls,
        py_value: Any,
    ) -> TypeGuard[Combinable]:
        return isinstance(py_value, Combinable)

    @classmethod
    def is_f(
        cls,
        py_value: Any,
    ) -> TypeGuard[F]:
        return isinstance(py_value, F)

    @classmethod
    def is_value(
        cls,
        py_value: Any,
    ) -> TypeGuard[Value]:
        return isinstance(py_value, Value)

    @classmethod
    def is_model_instance(
        cls,
        py_value: Any,
    ) -> TypeGuard[Model]:
        return isinstance(py_value, Model)

    @classmethod
    def is_field(
        cls,
        py_value: Any,
    ) -> TypeGuard[Field]:
        return isinstance(py_value, Field)

    @classmethod
    def is_constant(
        cls,
        py_value: Any,
    ) -> TypeGuard[Any]:
        py_value = cls.ensure_if_py_value(py_value)
        return isinstance(py_value, cls.Optimization.LITERAL_TYPES)

    @classmethod
    def any_q(
        cls,
        *py_values: Any,
    ) -> bool:
        return any(map(cls.is_q, py_values))

    @classmethod
    def any_combinable(
        cls,
        *py_values: Any,
    ) -> bool:
        return any(map(cls.is_combinable, py_values))

    @classmethod
    def any_constant(
        cls,
        *maybe_combinables: Any,
    ) -> bool:
        return any(map(cls.is_constant, maybe_combinables))

    @classmethod
    def any_q_or_combinable(
        cls,
        *py_values: Any,
    ) -> bool:
        return any(
            map(
                lambda py_value: (cls.is_q(py_value) or cls.is_combinable(py_value)),
                py_values,
            ),
        )

    @classmethod
    @overload
    def ensure_if_combinable(
        cls,
        combinable: Combinable,
    ) -> Combinable:
        ...

    @classmethod
    @overload
    def ensure_if_combinable(
        cls,
        model_instance: Model,
    ) -> Any:
        ...

    @classmethod
    @overload
    def ensure_if_combinable(
        cls,
        py_value: T,
    ) -> T:
        ...

    @classmethod
    def ensure_if_combinable(
        cls,
        maybe_combinable,
    ):
        if cls.is_combinable(maybe_combinable):
            combinable = cast(Combinable, maybe_combinable)
            return combinable

        if cls.is_model_instance(maybe_combinable):
            model_instance = cast(Model, maybe_combinable)
            model_options = cast(Options, getattr(model_instance.__class__, "_meta"))
            if model_options.abstract or model_options.pk is None:
                return model_instance
            pk_attname = cls.ensure_field_attname(model_options.pk)
            pk = getattr(model_instance, pk_attname)
            return Value(pk)

        if not cls.is_q(maybe_combinable) and not cls.is_expression(maybe_combinable):
            value = Value(maybe_combinable)
            return value

        return maybe_combinable

    @classmethod
    @overload
    def ensure_if_py_value(
        cls,
        value: Value,
    ) -> Any:
        ...

    @classmethod
    @overload
    def ensure_if_py_value(
        cls,
        py_value: T,
    ) -> T:
        ...

    @classmethod
    def ensure_if_py_value(
        cls,
        maybe_value,
    ):
        if cls.is_value(maybe_value):
            value = cast(Value, maybe_value)
            return value.value
        return maybe_value

    @classmethod
    @overload
    def ensure_field_attname(
        cls,
        field: Field,
    ) -> str:
        ...

    @classmethod
    @overload
    def ensure_field_attname(
        cls,
        py_value: T,
    ) -> T:
        ...

    @classmethod
    def ensure_field_attname(
        cls,
        py_value,
    ):
        if cls.is_field(py_value):
            field = cast(Field, py_value)
            return field.attname

        return py_value

    @classmethod
    def split_qs(
        cls,
        *py_values: Any,
    ) -> tuple[list[Q], list[Combinable]]:
        qs: list[Q] = []
        combinables: list[Combinable] = []

        for py_value in py_values:
            if cls.is_q(py_value):
                q = cast(Q, py_value)
                qs.append(q)
            else:
                combinable = cls.ensure_if_combinable(py_value)
                combinables.append(combinable)

        return qs, combinables

    @classmethod
    def split_values(
        cls,
        *maybe_combinables: Any,
    ) -> tuple[list[Value], list[Any]]:
        values: list[Value] = []
        py_values: list[Any] = []

        for maybe_combinable in maybe_combinables:
            maybe_combinable = cls.ensure_if_combinable(maybe_combinable)

            if cls.is_value(maybe_combinable):
                value = cast(Value, maybe_combinable)
                values.append(value)
            else:
                py_value = cls.ensure_if_py_value(maybe_combinable)
                py_values.append(py_value)

        return values, py_values

    @classmethod
    def is_falsy_combinable(
        cls,
        maybe_combinable: Any,
    ) -> bool:
        py_value = cls.ensure_if_py_value(maybe_combinable)
        return not py_value

    @classmethod
    def should_optimize_for(
        cls,
        operation_name: str,
        *maybe_combinables: Any,
    ) -> bool:
        if operation_name not in cls.Optimization.EXCLUDED_TYPES:
            return True
        types = cls.Optimization.EXCLUDED_TYPES[operation_name]
        return all(
            map(
                lambda py_value: not isinstance(py_value, types),
                map(
                    cls.ensure_if_py_value,
                    maybe_combinables,
                ),
            ),
        )

    @classmethod
    def q_test(
        cls,
        maybe_combinable: Any,
    ) -> Q:
        if cls.is_q(maybe_combinable):
            q = cast(Q, maybe_combinable)
            return q

        combinable = cls.ensure_if_combinable(maybe_combinable)

        if cls.is_falsy_combinable(combinable):
            return cls.QEnum.NEGATED

        elif cls.is_value(combinable):
            return cls.QEnum.EMPTY

        return Q(
            Case(
                When(
                    Pure(combinable),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )

    @classmethod
    def q_and(
        cls,
        q1: Q,
        q2: Q,
    ) -> Q:
        if not q1.children and not q2.children:
            return cls.QEnum.EMPTY

        if q1.children and not q2.children:
            return q1

        if not q1.children and q2.children:
            return q2

        if q1 is cls.QEnum.NEGATED and q2 is cls.QEnum.NEGATED:
            return cls.QEnum.NEGATED

        if q1 is cls.QEnum.NEGATED and q2 is not cls.QEnum.NEGATED:
            return ~q2

        if q1 is not cls.QEnum.NEGATED and q2 is cls.QEnum.NEGATED:
            return ~q1

        return q1 & q2

    @classmethod
    def q_xor(
        cls,
        q1: Q,
        q2: Q,
    ) -> Q:
        if not q1.children and not q2.children:
            return cls.QEnum.EMPTY

        if q1.children and not q2.children:
            return ~q1

        if not q1.children and q2.children:
            return ~q2

        if q1 is cls.QEnum.NEGATED and q2 is cls.QEnum.NEGATED:
            return cls.QEnum.NEGATED

        if q1 is cls.QEnum.NEGATED and q2 is not cls.QEnum.NEGATED:
            return q2

        if q1 is not cls.QEnum.NEGATED and q2 is cls.QEnum.NEGATED:
            return q1

        return q1 ^ q2

    @classmethod
    def q_or(
        cls,
        q1: Q,
        q2: Q,
    ) -> Q:
        if not q1.children and not q2.children:
            return cls.QEnum.EMPTY

        if q1.children and not q2.children:
            return q1

        if not q1.children and q2.children:
            return q2

        if q1 is cls.QEnum.NEGATED and q2 is cls.QEnum.NEGATED:
            return cls.QEnum.NEGATED

        if q1 is cls.QEnum.NEGATED and q2 is not cls.QEnum.NEGATED:
            return q2

        if q1 is not cls.QEnum.NEGATED and q2 is cls.QEnum.NEGATED:
            return q1

        return q1 | q2

    @classmethod
    def pos(
        cls,
        operand: Any,
    ) -> Any:
        if not cls.is_combinable(operand):
            return pos(operand)

        operand = cls.ensure_if_combinable(operand)
        return operand

    @classmethod
    def neg(
        cls,
        operand: Any,
    ) -> Any:
        if not cls.is_combinable(operand):
            return neg(operand)

        operand = cls.ensure_if_combinable(operand)

        if cls.should_optimize_for("arithmetic", operand):

            if cls.is_value(operand):
                operand = cast(Value, operand)
                return Value(neg(operand.value))

        return neg(operand)

    @classmethod
    def not_(
        cls,
        operand: Any,
    ) -> Any:
        if not cls.is_q_or_combinable(operand):
            return not_(operand)

        operand = cls.ensure_if_combinable(operand)

        if cls.is_q(operand):
            q = cast(Q, operand)

            if not q.children:
                if not q.negated:
                    return cls.QEnum.NEGATED
                else:
                    return cls.QEnum.EMPTY
            return ~q

        if not cls.is_value(operand):
            return ~cls.q_test(operand)

        if cls.should_optimize_for("logical", operand):

            if cls.is_value(operand):
                operand = cast(Value, operand)
                return Value(not_(operand.value))

        return not_(operand)

    @classmethod
    def inv(
        cls,
        operand: Any,
    ) -> Any:
        if not cls.is_q_or_combinable(operand):
            return inv(operand)

        operand = cls.ensure_if_combinable(operand)

        if cls.should_optimize_for("bitwise", operand):

            if cls.is_value(operand):
                operand = cast(Value, operand)
                return Value(inv(operand.value))

        if cls.is_q(operand):
            q = cast(Q, operand)
            return ~q

        return inv(operand)

    @classmethod
    def pow(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return pow(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.should_optimize_for("arithmetic", lhs, rhs):

            if cls.is_value(lhs) and cls.is_value(rhs):
                lhs = cast(Value, lhs)
                rhs = cast(Value, rhs)
                return Value(pow(lhs.value, rhs.value))

        return pow(lhs, rhs)

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

        if cls.should_optimize_for("arithmetic", lhs, rhs):

            if cls.is_value(lhs) and cls.is_value(rhs):
                lhs = cast(Value, lhs)
                rhs = cast(Value, rhs)
                return Value(lhs.value * rhs.value)

        return lhs * rhs

    @classmethod
    def truediv(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return truediv(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.should_optimize_for("arithmetic", lhs, rhs):

            if cls.is_value(lhs) and cls.is_value(rhs):
                lhs = cast(Value, lhs)
                rhs = cast(Value, rhs)
                return Value(truediv(lhs.value, rhs.value))

        return truediv(lhs, rhs)

    @classmethod
    def floordiv(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return floordiv(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.should_optimize_for("arithmetic", lhs, rhs):

            if cls.is_value(lhs) and cls.is_value(rhs):
                lhs = cast(Value, lhs)
                rhs = cast(Value, rhs)
                return Value(floordiv(lhs.value, rhs.value))

        return Floor(lhs / rhs)

    @classmethod
    def mod(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return mod(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.should_optimize_for("arithmetic", lhs, rhs):

            if cls.is_value(lhs) and cls.is_value(rhs):
                lhs = cast(Value, lhs)
                rhs = cast(Value, rhs)
                return Value(mod(lhs.value, rhs.value))

        return mod(lhs, rhs)

    @classmethod
    def add(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return add(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.should_optimize_for("arithmetic", lhs, rhs):

            if cls.is_value(lhs) and cls.is_value(rhs):
                lhs = cast(Value, lhs)
                rhs = cast(Value, rhs)
                return Value(add(lhs.value, rhs.value))

        return add(lhs, rhs)

    @classmethod
    def sub(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return sub(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.should_optimize_for("arithmetic", lhs, rhs):

            if cls.is_value(lhs) and cls.is_value(rhs):
                lhs = cast(Value, lhs)
                rhs = cast(Value, rhs)
                return Value(sub(lhs.value, rhs.value))

        return sub(lhs, rhs)

    @classmethod
    def lshift(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lshift(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return lhs.bitleftshift(rhs)

    @classmethod
    def rshift(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return rshift(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return lhs.bitrightshift(rhs)

    @classmethod
    def and_(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_q_or_combinable(lhs, rhs):
            return lhs and rhs

        qs, combinables = cls.split_qs(lhs, rhs)

        if not qs and combinables:
            return cls.q_test(combinables[0]) & cls.q_test(combinables[1])

        if qs and not combinables:
            return cls.q_and(qs[0], qs[1])

        if qs and combinables:
            q1 = qs[0]

            if cls.is_falsy_combinable(combinables[0]):
                return ~q1

            elif cls.is_value(combinables[0]):
                return q1

            else:
                q2 = cls.q_test(combinables[0])
                return cls.q_and(q1, q2)

        raise NotImplementedError(
            f"{cls.__qualname__}.and_ is not implemented for: " f" {[lhs, rhs]!r}"
        )

    @classmethod
    def iand(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_q_or_combinable(lhs, rhs):
            return iand(lhs, rhs)

        qs, combinables = cls.split_qs(lhs, rhs)

        if not qs and combinables:
            return combinables[0].bitand(combinables[1])  # type: ignore[arg-type]

        if qs and not combinables:
            return cls.q_and(qs[0], qs[1])

        if qs and combinables:
            q1 = qs[0]

            if cls.is_falsy_combinable(combinables[0]):
                return ~q1

            elif cls.is_value(combinables[0]):
                return q1

            else:
                q2 = cls.q_test(combinables[0])
                return cls.q_and(q1, q2)

        raise NotImplementedError(
            f"{cls.__qualname__}.iand is not implemented for: " f" {[lhs, rhs]!r}"
        )

    @classmethod
    def xor(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_q_or_combinable(lhs, rhs):
            return lhs ^ rhs

        qs, combinables = cls.split_qs(lhs, rhs)

        if not qs and combinables:
            return combinables[0].bitxor(combinables[1])  # type: ignore[arg-type]

        if qs and not combinables:
            return cls.q_xor(qs[0], qs[1])

        if qs and combinables:
            q1 = qs[0]

            if cls.is_falsy_combinable(combinables[0]):
                return q1

            elif cls.is_value(combinables[0]):
                return q1

            else:
                q2 = cls.q_test(combinables[0])
                return cls.q_xor(q1, q2)

        raise NotImplementedError(
            f"{cls.__qualname__}.xor is not implemented for: {[lhs, rhs]!r}",
        )

    @classmethod
    def or_(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_q_or_combinable(lhs, rhs):
            return lhs or rhs

        qs, combinables = cls.split_qs(lhs, rhs)

        if not qs and combinables:
            return cls.q_test(combinables[0]) | cls.q_test(combinables[1])

        if qs and not combinables:
            return cls.q_or(qs[0], qs[1])

        if qs and combinables:
            q1 = qs[0]

            if cls.is_falsy_combinable(combinables[0]):
                return q1

            elif cls.is_value(combinables[0]):
                return q1

            else:
                q2 = cls.q_test(combinables[0])
                return cls.q_or(q1, q2)

        raise NotImplementedError(
            f"{cls.__qualname__}.or_ is not implemented for: " f" {[lhs, rhs]!r}"
        )

    @classmethod
    def ior(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_q_or_combinable(lhs, rhs):
            return ior(lhs, rhs)

        qs, combinables = cls.split_qs(lhs, rhs)

        if not qs and combinables:
            return combinables[0].bitor(
                cast(int, combinables[1]),
            )

        if qs and not combinables:
            return cls.q_or(qs[0], qs[1])

        if qs and combinables:
            q1 = qs[0]

            if cls.is_falsy_combinable(combinables[0]):
                return q1

            elif cls.is_value(combinables[0]):
                return q1

            else:
                q2 = cls.q_test(combinables[0])
                return cls.q_or(q1, q2)

        raise NotImplementedError(
            f"{cls.__qualname__}.ior is not implemented for: " f" {[lhs, rhs]!r}"
        )

    @classmethod
    def nin(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lhs not in rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return ~Q(In(lhs, rhs))

    @classmethod
    def in_(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lhs in rhs

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        return Q(In(lhs, rhs))

    @classmethod
    def is_not(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):

            if cls.any_constant(lhs, rhs):
                return ne(lhs, rhs)

            return is_not(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        values, py_values = cls.split_values(lhs, rhs)

        if cls.should_optimize_for("compare", lhs, rhs):

            if values and not py_values:

                if values[0].value is None and values[1].value is None:
                    return Value(False)

                if values[0].value == values[1].value:
                    return Value(False)

                else:
                    return Value(True)

            elif py_values and not values:
                return ~Q(Exact(lhs, rhs))

        value = values[0]
        py_value = py_values[0]

        if value.value is None:
            return ~Q(IsNull(py_value, True))

        return ~Q(Exact(lhs, rhs))

    @classmethod
    def is_(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):

            if cls.any_constant(lhs, rhs):
                return eq(lhs, rhs)

            return is_(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        values, py_values = cls.split_values(lhs, rhs)

        if cls.should_optimize_for("compare", lhs, rhs):

            if values and not py_values:

                if values[0].value is None and values[1].value is None:
                    return Value(True)

                if values[0].value == values[1].value:
                    return Value(True)
                else:
                    return Value(False)

            elif py_values and not values:
                return Q(Exact(lhs, rhs))

        value = values[0]
        py_value = py_values[0]

        if value.value is None:
            return Q(IsNull(py_value, True))

        return Q(Exact(lhs, rhs))

    @classmethod
    def gt(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return gt(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.should_optimize_for("compare", lhs, rhs):
            values, py_values = cls.split_values(lhs, rhs)

            if values and not py_values:

                if values[0].value is None or values[1].value is None:
                    return Value(False)

                if values[0].value > values[1].value:
                    return Value(True)

                else:
                    return Value(False)

            elif values and py_values and values[0].value is None:
                return Value(False)

        return Q(GreaterThan(lhs, rhs))

    @classmethod
    def ge(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return ge(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.should_optimize_for("compare", lhs, rhs):
            values, py_values = cls.split_values(lhs, rhs)

            if values and not py_values:

                if values[0].value is None or values[1].value is None:
                    return Value(False)

                if values[0].value >= values[1].value:
                    return Value(True)

                else:
                    return Value(False)

            elif values and py_values and values[0].value is None:
                return Value(False)

        return Q(GreaterThanOrEqual(lhs, rhs))

    @classmethod
    def le(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return le(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.should_optimize_for("compare", lhs, rhs):
            values, py_values = cls.split_values(lhs, rhs)

            if values and not py_values:

                if values[0].value is None or values[1].value is None:
                    return Value(False)

                if values[0].value <= values[1].value:
                    return Value(True)

                else:
                    return Value(False)

            elif values and py_values and values[0].value is None:
                return Value(False)

        return Q(LessThanOrEqual(lhs, rhs))

    @classmethod
    def lt(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return lt(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        if cls.should_optimize_for("compare", lhs, rhs):
            values, py_values = cls.split_values(lhs, rhs)

            if values and not py_values:

                if values[0].value is None or values[1].value is None:
                    return Value(False)

                if values[0].value < values[1].value:
                    return Value(True)

                else:
                    return Value(False)

            elif values and py_values and values[0].value is None:
                return Value(False)

        return Q(LessThan(lhs, rhs))

    @classmethod
    def ne(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return ne(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        values, py_values = cls.split_values(lhs, rhs)

        if cls.should_optimize_for("compare", lhs, rhs):

            if values and not py_values:

                if values[0].value is None and values[1].value is None:
                    return Value(False)

                if values[0].value == values[1].value:
                    return Value(False)

                else:
                    return Value(True)

            elif py_values and not values:
                return ~Q(Exact(lhs, rhs))

        value = values[0]
        py_value = py_values[0]

        if value.value is None:
            return ~Q(IsNull(py_value, True))

        return ~Q(Exact(lhs, rhs))

    @classmethod
    def eq(
        cls,
        lhs: Any,
        rhs: Any,
    ) -> Any:
        if not cls.any_combinable(lhs, rhs):
            return eq(lhs, rhs)

        lhs = cls.ensure_if_combinable(lhs)
        rhs = cls.ensure_if_combinable(rhs)

        values, py_values = cls.split_values(lhs, rhs)

        if cls.should_optimize_for("compare", lhs, rhs):

            if values and not py_values:

                if values[0].value is None and values[1].value is None:
                    return Value(True)

                if values[0].value == values[1].value:
                    return Value(True)
                else:
                    return Value(False)

            elif py_values and not values:
                return Q(Exact(lhs, rhs))

        value = values[0]
        py_value = py_values[0]

        if value.value is None:
            return Q(IsNull(py_value, True))

        return Q(Exact(lhs, rhs))
