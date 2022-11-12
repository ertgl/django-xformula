
.PHONY: lint.python.isort
lint.python.isort:
	$(ISORT) --extend-skip '$(TMP)' --check .
