
.PHONY: twine.upload
twine.upload:
	$(PYTHON) -m twine upload $(DIST)
