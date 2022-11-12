include mk/lint/python/*.mk


.PHONY: lint.python
lint.python: lint.python.mypy lint.python.pycln lint.python.isort lint.python.black
