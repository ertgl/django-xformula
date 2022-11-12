include mk/clean/*.mk


.PHONY: clean.soft
clean.soft: mypy.clean


.PHONY: clean
clean: clean.soft venv.clean
