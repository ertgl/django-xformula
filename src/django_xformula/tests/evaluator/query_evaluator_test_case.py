from contextlib import nullcontext
from operator import call
from random import randint
from typing import Any, ContextManager

from django.db.models import F, Q, Value
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
from django.test import TestCase

from django_xformula import BidirectionalOperator, QueryEvaluator

__all__ = [
    "DjangoQueryEvaluatorTestCase",
]


class DjangoQueryEvaluatorTestCase(TestCase):

    evaluator: QueryEvaluator

    def setUp(self) -> None:
        self.evaluator = QueryEvaluator()

    def evaluate(
        self,
        source: str,
        context: QueryEvaluator.Context | None = None,
    ) -> Any:
        return self.evaluator.evaluate(
            source,
            context=context,
        )

    def test__evaluate__literal__none(self) -> None:
        value = self.evaluate("none")
        self.assertIs(value, None)

    def test__evaluate__literal__bool__false(self) -> None:
        value = self.evaluate("false")
        self.assertIs(value, False)

    def test__evaluate__literal__bool__true(self) -> None:
        value = self.evaluate("true")
        self.assertIs(value, True)

    def test__evaluate__literal__int__decimal(self) -> None:
        value = self.evaluate("1")
        self.assertEqual(value, 1)

    def test__evaluate__literal__float(self) -> None:
        value = self.evaluate("1.2e+4")
        self.assertEqual(value, 1.2e4)

    def test__evaluate__literal__complex(self) -> None:
        value = self.evaluate("1.2e+4j")
        self.assertEqual(value, 1.2e4j)

    def test__evaluate__literal__str__single_line__single_quoted(self) -> None:
        value = self.evaluate("'value'")
        self.assertEqual(value, "value")

    def test__evaluate__literal__str__single_line__double_quoted(self) -> None:
        value = self.evaluate('"value"')
        self.assertEqual(value, "value")

    def test__evaluate__identifier(self) -> None:
        f = self.evaluate("value")
        self.assertIsInstance(f, F)
        self.assertEqual(f.name, "value")

    def test__evaluate__identifier__with_builtin_variable(self) -> None:
        auth_user_id = 1
        context = self.evaluator.__class__.Context(
            builtins=dict(
                AUTH_USER_ID=auth_user_id,
            ),
        )
        value = self.evaluate("AUTH_USER_ID", context=context)
        self.assertEqual(value, auth_user_id)

    def test__evaluate__list__literals(self) -> None:
        container = self.evaluate("[none, true, 1, 1.2, 'abc']")
        self.assertEqual(container, [None, True, 1, 1.2, "abc"])

    def test__evaluate__list__mixed_types(self) -> None:
        context = self.evaluator.__class__.Context(
            builtins=dict(
                is_authenticated=False,
            ),
        )
        container = self.evaluate("[False, id, is_authenticated]", context=context)
        self.assertEqual(container, [False, F("id"), False])

    def test__evaluate__set(self) -> None:
        container = self.evaluate("{id, id}")
        self.assertEqual(container, {F("id")})

    def test__evaluate__tuple(self) -> None:
        container = self.evaluate("(NONE, FALSE, TRUE)")
        self.assertEqual(container, (None, False, True))

    def test__evaluate__dict(self) -> None:
        mapping = self.evaluate(
            """
            {
                a: "a",
                "b": b,
            }
            """
        )
        self.assertEqual(
            mapping,
            {
                F("a"): "a",
                "b": F("b"),
            },
        )

    def test__evaluate__function_call__void_args(self) -> None:
        context = self.evaluator.__class__.Context(
            builtins=dict(
                f=lambda: 1,
            ),
            call=call,
        )
        value = self.evaluate("f()", context=context)
        self.assertEqual(value, 1)

    def test__evaluate__function_call__args(self) -> None:
        context = self.evaluator.__class__.Context(
            builtins=dict(
                f=lambda x: x + 1,
            ),
            call=call,
        )
        value = self.evaluate("f(1)", context=context)
        self.assertEqual(value, 2)

    def test__evaluate__function_call__kwargs(self) -> None:
        def get_value(x: int = 0) -> int:
            return x

        context = self.evaluator.__class__.Context(
            builtins=dict(
                get_value=get_value,
            ),
            call=call,
        )

        value = self.evaluate("get_value()", context=context)
        self.assertEqual(value, 0)

        value = self.evaluate("get_value(x = 1)", context=context)
        self.assertEqual(value, 1)

    def test__evaluate__function_call__args_kwargs(self) -> None:
        def get_value(
            *args: int,
            **kwargs: int,
        ) -> int | None:
            if "y" in kwargs:
                return kwargs["y"]
            if not args:
                return None
            return args[0]

        context = self.evaluator.__class__.Context(
            builtins=dict(
                get_value=get_value,
            ),
            call=call,
        )

        value = self.evaluate("get_value()", context=context)
        self.assertEqual(value, None)

        value = self.evaluate("get_value(1)", context=context)
        self.assertEqual(value, 1)

        value = self.evaluate("get_value(1, y = 2)", context=context)
        self.assertEqual(value, 2)

    def test__evaluate__operation__arity_1(self) -> None:
        for (
            symbol,
            operate,
        ) in self.evaluator.__class__.Operator.Unary.dispatcher.items():

            py_symbol = self.evaluator.__class__.Operator.Unary.aliases.get(
                symbol,
                symbol,
            )

            for _ in range(100):
                value = randint(0, 10)

                py_source = f"{py_symbol} {value}"
                xf_source = f"{symbol} {value}"

                expected = eval(py_source)
                result = self.evaluate(xf_source)

                self.assertEqual(
                    (py_source, xf_source, type(result), result),
                    (py_source, xf_source, type(expected), expected),
                )

    def test__evaluate__operation__not(self) -> None:
        context = self.evaluator.__class__.Context(
            builtins=dict(
                Q=Q,
                V=Value,
            ),
            call=call,
        )

        cases = (
            ("!7", not 7),
            ("not 7", not 7),
            ("!V(0)", Value(True)),
            ("!V(1)", Value(False)),
            ("not V(1)", Value(False)),
            ("!Q()", BidirectionalOperator.QEnum.NEGATED),
            ("not Q(a=1)", ~Q(a=1)),
            ("!field", ~BidirectionalOperator.q_test(F("field"))),
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0], context=context)),
                (case[0], case[1]),
            )

    def test__evaluate__operation__arity_2(self) -> None:
        excluded_symbols = {"@"}

        for (
            symbol,
            operate,
        ) in self.evaluator.__class__.Operator.Binary.dispatcher.items():

            if symbol in excluded_symbols:
                continue

            py_symbol = self.evaluator.__class__.Operator.Binary.aliases.get(
                symbol,
                symbol,
            )

            for _ in range(10):
                lhs = randint(0, 10)
                rhs = randint(0, 10)

                py_source = f"{lhs} {py_symbol} {rhs}"
                xf_source = f"{lhs} {symbol} {rhs}"

                cm: ContextManager = nullcontext()
                if symbol in ["/", "//", "%"] and rhs == 0:
                    cm = self.assertRaises(ZeroDivisionError)

                elif symbol in ["in", "!in", "not in"]:
                    py_source = f"{lhs} {py_symbol} [{rhs}]"
                    xf_source = f"{lhs} {symbol} [{rhs}]"

                # Bypass SyntaxWarning: "is / is not" with literals.
                elif symbol in ["is", "!is", "is not"]:
                    py_source = f"((lambda: {lhs})()) {py_symbol} ((lambda: {rhs})())"

                with cm:
                    expected = eval(py_source)
                    result = self.evaluate(xf_source)

                    self.assertEqual(
                        (py_source, xf_source, type(result), result),
                        (py_source, xf_source, type(expected), expected),
                    )

    def test__evaluate__operation__bidirectional__floordiv(self) -> None:
        cases = (
            ("7 // 2", 7 // 2),
            ("field // 2", Floor(F("field") / 2)),
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0])),
                (case[0], case[1]),
            )

    def test__evaluate__operation__bidirectional__lshift(self) -> None:
        cases = (
            ("7 << 2", 7 << 2),
            ("field << 2", F("field").bitleftshift(2)),
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0])),
                (case[0], case[1]),
            )

    def test__evaluate__operation__bidirectional__rshift(self) -> None:
        cases = (
            ("7 >> 2", 7 >> 2),
            ("field >> 2", F("field").bitrightshift(2)),
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0])),
                (case[0], case[1]),
            )

    def test__evaluate__operation__bidirectional__and(self) -> None:
        context = self.evaluator.__class__.Context(
            builtins=dict(
                Q=Q,
            ),
            call=call,
        )

        cases = (
            ("7 & 2", 7 & 2),
            ("field & 2", F("field").bitand(2)),
            ("Q(a=1) & field", Q(a=1) & BidirectionalOperator.q_test(F("field"))),
            ("none & field", Value(None).bitand(F("field"))),  # type: ignore[arg-type]
            ("field & none", F("field").bitand(Value(None))),  # type: ignore[arg-type]
            ("Q(field & another) & none", ~Q(F("field").bitand(F("another")))),  # type: ignore[arg-type]
            ("Q(field & another) & false", ~Q(F("field").bitand(F("another")))),  # type: ignore[arg-type]
            ("Q(field & another) & true", Q(F("field").bitand(F("another")))),  # type: ignore[arg-type]
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0], context=context)),
                (case[0], case[1]),
            )

    def test__evaluate__operation__bidirectional__xor(self) -> None:
        context = self.evaluator.__class__.Context(
            builtins=dict(
                Q=Q,
            ),
            call=call,
        )

        cases = (
            ("7 ^ 2", 7 ^ 2),
            ("field ^ 2", F("field").bitxor(2)),
            ("Q(a=1) ^ field", Q(a=1) ^ BidirectionalOperator.q_test(F("field"))),
            ("none ^ field", Value(None).bitxor(F("field"))),  # type: ignore[arg-type]
            ("field ^ none", F("field").bitxor(Value(None))),  # type: ignore[arg-type]
            ("Q(field ^ another) ^ none", Q(F("field").bitxor(F("another")))),  # type: ignore[arg-type]
            ("Q(field ^ another) ^ false", Q(F("field").bitxor(F("another")))),  # type: ignore[arg-type]
            ("Q(field ^ another) ^ true", Q(F("field").bitxor(F("another")))),  # type: ignore[arg-type]
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0], context=context)),
                (case[0], case[1]),
            )

    def test__evaluate__operation__bidirectional__or(self) -> None:
        context = self.evaluator.__class__.Context(
            builtins=dict(
                Q=Q,
            ),
            call=call,
        )

        cases = (
            ("7 | 2", 7 | 2),
            ("field | 2", F("field").bitor(2)),
            ("Q(a=1) | field", Q(a=1) | BidirectionalOperator.q_test(F("field"))),
            ("none | field", Value(None).bitor(F("field"))),  # type: ignore[arg-type]
            ("field | none", F("field").bitor(Value(None))),  # type: ignore[arg-type]
            ("Q(field | another) | none", Q(F("field").bitor(F("another")))),  # type: ignore[arg-type]
            ("Q(field | another) | false", Q(F("field").bitor(F("another")))),  # type: ignore[arg-type]
            ("Q(field | another) | true", Q(F("field").bitor(F("another")))),  # type: ignore[arg-type]
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0], context=context)),
                (case[0], case[1]),
            )

    def test__evaluate__operation__bidirectional__is_not(self) -> None:
        context = self.evaluator.__class__.Context(
            builtins=dict(
                Q=Q,
                V=Value,
            ),
            call=call,
        )

        cases = (
            ("7 is not 2", 7 != 2),
            ("1 is not V(2)", Value(True)),
            ("V(1) is not V(2)", Value(True)),
            ("V(1) is not V(1)", Value(False)),
            ("none !is field", ~Q(IsNull(F("field"), True))),
            ("field !is None", ~Q(IsNull(F("field"), True))),
            ("field !is 2", ~Q(Exact(F("field"), Value(2)))),
            ("field !is another", ~Q(Exact(F("field"), F("another")))),
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0], context=context)),
                (case[0], case[1]),
            )

    def test__evaluate__operation__bidirectional__is(self) -> None:
        context = self.evaluator.__class__.Context(
            builtins=dict(
                Q=Q,
                V=Value,
            ),
            call=call,
        )

        cases = (
            ("7 is 2", 7 == 2),
            ("0 is V(0)", Value(True)),
            ("V(1) is V(1)", Value(True)),
            ("V(1) is V(2)", Value(False)),
            ("none is field", Q(IsNull(F("field"), True))),
            ("field is None", Q(IsNull(F("field"), True))),
            ("field is 2", Q(Exact(F("field"), Value(2)))),
            ("field is another", Q(Exact(F("field"), F("another")))),
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0], context=context)),
                (case[0], case[1]),
            )

    def test__evaluate__operation__bidirectional__nlte(self) -> None:
        context = self.evaluator.__class__.Context(
            builtins=dict(
                V=Value,
            ),
            call=call,
        )

        cases = (
            ("7 !<= 2", 7 > 2),
            ("0 !<= V(0)", Value(False)),
            ("V(1) !<= V(1)", Value(False)),
            ("V(2) !<= V(1)", Value(True)),
            ("none !<= field", Value(False)),
            ("field !<= None", Value(False)),
            ("field !<= 2", Q(GreaterThan(F("field"), Value(2)))),
            ("field !<= another", Q(GreaterThan(F("field"), F("another")))),
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0], context=context)),
                (case[0], case[1]),
            )

    def test__evaluate__operation__bidirectional__nlt(self) -> None:
        context = self.evaluator.__class__.Context(
            builtins=dict(
                V=Value,
            ),
            call=call,
        )

        cases = (
            ("7 !< 2", 7 >= 2),
            ("0 !< V(0)", Value(True)),
            ("V(1) !< V(1)", Value(True)),
            ("V(1) !< V(2)", Value(False)),
            ("none !< field", Value(False)),
            ("field !< None", Value(False)),
            ("field !< 2", Q(GreaterThanOrEqual(F("field"), Value(2)))),
            ("field !< another", Q(GreaterThanOrEqual(F("field"), F("another")))),
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0], context=context)),
                (case[0], case[1]),
            )

    def test__evaluate__operation__bidirectional__le(self) -> None:
        context = self.evaluator.__class__.Context(
            builtins=dict(
                V=Value,
            ),
            call=call,
        )

        cases = (
            ("7 <= 2", 7 <= 2),
            ("0 <= V(0)", Value(True)),
            ("V(1) <= V(1)", Value(True)),
            ("V(2) <= V(1)", Value(False)),
            ("none <= field", Value(False)),
            ("field <= None", Value(False)),
            ("field <= 2", Q(LessThanOrEqual(F("field"), Value(2)))),
            ("field <= another", Q(LessThanOrEqual(F("field"), F("another")))),
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0], context=context)),
                (case[0], case[1]),
            )

    def test__evaluate__operation__bidirectional__lt(self) -> None:
        context = self.evaluator.__class__.Context(
            builtins=dict(
                V=Value,
            ),
            call=call,
        )

        cases = (
            ("7 < 2", 7 <= 2),
            ("0 < V(0)", Value(False)),
            ("V(1) < V(1)", Value(False)),
            ("V(1) < V(2)", Value(True)),
            ("none < field", Value(False)),
            ("field < None", Value(False)),
            ("field < 2", Q(LessThan(F("field"), Value(2)))),
            ("field < another", Q(LessThan(F("field"), F("another")))),
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0], context=context)),
                (case[0], case[1]),
            )

    def test__evaluate__operation__bidirectional__in(self) -> None:
        cases = (
            ("field in 2", Q(In(F("field"), Value(2)))),
            ("field in [1, 2]", Q(In(F("field"), [Value(1), Value(2)]))),
            ("field in (1, 2)", Q(In(F("field"), (Value(1), Value(2))))),
            ("field in {1, 2}", Q(In(F("field"), {Value(1), Value(2)}))),
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0])),
                (case[0], case[1]),
            )

    def test__evaluate__operation__bidirectional__nin(self) -> None:
        cases = (
            ("field !in 2", ~Q(In(F("field"), Value(2)))),
            ("field not in [1, 2]", ~Q(In(F("field"), [Value(1), Value(2)]))),
            ("field !in (1, 2)", ~Q(In(F("field"), (Value(1), Value(2))))),
            ("field not in {1, 2}", ~Q(In(F("field"), {Value(1), Value(2)}))),
        )

        for case in cases:
            self.assertEqual(
                (case[0], self.evaluate(case[0])),
                (case[0], case[1]),
            )
