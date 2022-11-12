
.PHONY: format.python.pycln
format.python.pycln:
	$(PYCLN) --all --extend-exclude '$(TMP)' .
