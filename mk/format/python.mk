include mk/format/python/*.mk


.PHONY: format.python
format.python: dev.bin.format.exported_py_symbols format.python.pycln format.python.isort format.python.black
