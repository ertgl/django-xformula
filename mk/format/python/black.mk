
.PHONY: format.python.black
format.python.black:
	$(BLACK) --extend-exclude '$(TMP)' .
