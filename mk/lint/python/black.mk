
.PHONY: lint.python.black
lint.python.black:
	$(BLACK) --extend-exclude '$(TMP)' --check .
