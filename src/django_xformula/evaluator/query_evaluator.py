import dataclasses
from functools import partial
from operator import matmul
from typing import Any, TypeVar, cast

from django.db.models import F
from xformula.syntax import Parser, ast

from django_xformula.errors import ForbiddenAttribute, ForbiddenCall
from django_xformula.evaluator.bidirectional_operator import BidirectionalOperator
from django_xformula.protocols import AttributeGetter, Caller

__all__ = [
    "QueryEvaluator",
]


T = TypeVar("T")


class QueryEvaluator:
    @dataclasses.dataclass()
    class Context:

        builtins: dict[str, Any] = dataclasses.field(
            kw_only=True,
            default_factory=dict,
        )

        call: Caller | None = dataclasses.field(
            kw_only=True,
            default=None,
        )

        getattr: AttributeGetter | None = dataclasses.field(
            kw_only=True,
            default=None,
        )

    class Operator:
        class Unary:

            aliases = {
                "!": "not",
            }

            dispatcher = {
                "+": BidirectionalOperator.pos,
                "-": BidirectionalOperator.neg,
                "!": BidirectionalOperator.not_,
                "~": BidirectionalOperator.inv,
                "not": BidirectionalOperator.not_,
            }

        class Binary:

            aliases = {
                "!in": "not in",
                "!is": "is not",
                "!<=": ">",
                "!<": ">=",
                "!>=": "<",
                "!>": "<=",
                "&&": "and",
                "||": "or",
            }

            dispatcher = {
                "**": BidirectionalOperator.pow,
                "*": BidirectionalOperator.mul,
                "@": matmul,
                "/": BidirectionalOperator.truediv,
                "//": BidirectionalOperator.floordiv,
                "%": BidirectionalOperator.mod,
                "+": BidirectionalOperator.add,
                "-": BidirectionalOperator.sub,
                "<<": BidirectionalOperator.lshift,
                ">>": BidirectionalOperator.rshift,
                "&": BidirectionalOperator.iand,
                "^": BidirectionalOperator.xor,
                "|": BidirectionalOperator.ior,
                "not in": BidirectionalOperator.nin,
                "!in": BidirectionalOperator.nin,
                "in": BidirectionalOperator.in_,
                "is not": BidirectionalOperator.is_not,
                "!is": BidirectionalOperator.is_not,
                "is": BidirectionalOperator.is_,
                "!<=": BidirectionalOperator.gt,
                "!<": BidirectionalOperator.ge,
                "<=": BidirectionalOperator.le,
                "<": BidirectionalOperator.lt,
                "!>=": BidirectionalOperator.lt,
                "!>": BidirectionalOperator.le,
                ">=": BidirectionalOperator.ge,
                ">": BidirectionalOperator.gt,
                "!=": BidirectionalOperator.ne,
                "==": BidirectionalOperator.eq,
                "&&": BidirectionalOperator.and_,
                "||": BidirectionalOperator.or_,
                "and": BidirectionalOperator.and_,
                "or": BidirectionalOperator.or_,
            }

    parser: Parser

    def __init__(
        self,
        parser: Parser | None = None,
    ) -> None:
        if parser is None:
            parser = Parser()
        self.parser = parser

    def evaluate(
        self,
        source: str,
        context: Context | None = None,
    ) -> Any:
        tree = self.parser.parse(source)
        return self.evaluate_ast(tree, context=context)

    def evaluate_ast(
        self,
        tree: ast.Node,
        context: Context | None = None,
    ) -> Any:
        return self.evaluate_node(tree, context=context)

    def evaluate_node(
        self,
        node: ast.Node,
        context: Context | None = None,
    ) -> Any:
        if context is None:
            context = self.__class__.Context()

        if isinstance(node, ast.Literal):
            return self.evaluate_literal(context, node)

        if isinstance(node, ast.Identifier):
            return self.evaluate_identifier(context, node)

        if isinstance(node, ast.Attribute):
            return self.evaluate_attribute(context, node)

        if isinstance(node, ast.Call):
            return self.evaluate_call(context, node)

        if isinstance(node, ast.List):
            return self.evaluate_list(context, node)

        if isinstance(node, ast.Set):
            return self.evaluate_set(context, node)

        if isinstance(node, ast.Tuple):
            return self.evaluate_tuple(context, node)

        if isinstance(node, ast.Dict):
            return self.evaluate_dict(context, node)

        if isinstance(node, ast.Pair):
            return self.evaluate_pair(context, node)

        if isinstance(node, ast.Operation):
            return self.evaluate_operation(context, node)

        raise NotImplementedError(
            f"{self.__class__.__qualname__}.evaluate_node is not implemented for"
            f" node: {node!r}"
        )

    def evaluate_literal(
        self,
        context: Context,
        node: ast.Literal[T],
    ) -> T:
        return node.value

    def evaluate_identifier(
        self,
        context: Context,
        node: ast.Identifier,
    ) -> Any:
        if node.context == ast.Context.LOAD:
            if node.name in context.builtins:
                return context.builtins[node.name]
            return F(node.name)
        elif node.context == ast.Context.ATTRIBUTE:
            return node.name
        elif node.context == ast.Context.KEYWORD_ARGUMENT:
            return node.name
        raise NotImplementedError(
            f"{self.__class__.__qualname__}.evaluate_identifier"
            f" is not implemented for context: {context!r}"
        )

    def evaluate_attribute(
        self,
        context: Context,
        node: ast.Attribute,
    ) -> Any:
        if node.context == ast.Context.LOAD:
            owner = self.evaluate_node(node.owner, context)
            attname = cast(str, self.evaluate_node(node.name, context))
            if isinstance(owner, F):
                return F(f"{owner.name}__{attname}")
            if callable(context.getattr):
                return context.getattr(owner, attname)
            raise ForbiddenAttribute(owner, attname)
        raise NotImplementedError(
            f"{self.__class__.__qualname__}.evaluate_attribute"
            f" is not implemented for context: {context!r}"
        )

    def evaluate_call(
        self,
        context: Context,
        node: ast.Call,
    ) -> Any:
        args: list[Any] = []
        kwargs: dict[str, Any] = dict()

        for element in node.arguments:
            if isinstance(element, ast.Pair):
                key = self.evaluate_node(
                    element.elements[0],
                    context=context,
                )
                key_value = self.evaluate_node(
                    element.elements[1],
                    context=context,
                )
                kwargs[key] = key_value

            else:
                value = self.evaluate_node(element, context=context)
                args.append(value)

        f = self.evaluate_node(node.callee, context=context)

        if callable(context.call):
            return context.call(
                f,
                *args,
                **kwargs,
            )

        raise ForbiddenCall(f, tuple(args), kwargs)

    def evaluate_list(
        self,
        context: Context,
        node: ast.List,
    ) -> list[Any]:
        return list(
            map(
                partial(self.evaluate_node, context=context),
                node.elements,
            ),
        )

    def evaluate_set(
        self,
        context: Context,
        node: ast.Set,
    ) -> set[Any]:
        return set(
            map(
                partial(self.evaluate_node, context=context),
                node.elements,
            ),
        )

    def evaluate_tuple(
        self,
        context: Context,
        node: ast.Tuple,
    ) -> tuple[Any, ...]:
        return tuple(
            map(
                partial(self.evaluate_node, context=context),
                node.elements,
            ),
        )

    def evaluate_dict(
        self,
        context: Context,
        node: ast.Dict,
    ) -> dict[Any, Any]:
        return dict(
            map(
                partial(self.evaluate_node, context=context),
                node.elements,
            ),
        )

    def evaluate_pair(
        self,
        context: Context,
        node: ast.Pair,
    ) -> tuple[Any, Any]:
        return (
            self.evaluate_node(node.elements[0], context=context),
            self.evaluate_node(node.elements[1], context=context),
        )

    def evaluate_operation(
        self,
        context: Context,
        node: ast.Operation,
    ) -> Any:
        if node.operator.arity == 1:
            return self.evaluate_operation_arity_1(context, node)

        if node.operator.arity == 2:
            return self.evaluate_operation_arity_2(context, node)

        return self.evaluate_operation_dynamic_arity(context, node)

    def evaluate_operation_arity_1(
        self,
        context: Context,
        node: ast.Operation,
    ) -> Any:
        operate = self.__class__.Operator.Unary.dispatcher.get(
            node.operator.symbols[0].value,
            None,
        )

        if not callable(operate):
            raise NotImplementedError(
                f"{self.__class__.__qualname__}.evaluate_operation_arity_1"
                f" is not implemented for operator: {node.operator!r}"
            )

        operand = self.evaluate_node(
            node.operands[0],
            context=context,
        )

        return operate(operand)

    def evaluate_operation_arity_2(
        self,
        context: Context,
        node: ast.Operation,
    ) -> Any:
        operate = self.__class__.Operator.Binary.dispatcher.get(
            node.operator.symbols[0].value,
            None,
        )

        if not callable(operate):
            raise NotImplementedError(
                f"{self.__class__.__qualname__}.evaluate_operation_arity_2"
                f" is not implemented for operator: {node.operator!r}"
            )

        lhs = self.evaluate_node(
            node.operands[0],
            context=context,
        )

        rhs = self.evaluate_node(
            node.operands[1],
            context=context,
        )

        return operate(lhs, rhs)

    def evaluate_operation_dynamic_arity(
        self,
        context: Context,
        node: ast.Operation,
    ) -> Any:
        raise NotImplementedError(
            f"{self.__class__.__qualname__}.evaluate_operation_dynamic_arity"
            f" is not implemented for operator: {node.operator!r}"
        )
