
.PHONY: lint.python.pycln
lint.python.pycln:
	$(PYCLN) --extend-exclude '$(TMP)' --check .
