
.PHONY: format.python.isort
format.python.isort:
	$(ISORT) --extend-skip '$(TMP)' .
