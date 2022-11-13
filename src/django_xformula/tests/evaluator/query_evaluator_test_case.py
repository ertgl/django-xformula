from typing import Any

from django.test import TestCase

from django_xformula import QueryEvaluator

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
