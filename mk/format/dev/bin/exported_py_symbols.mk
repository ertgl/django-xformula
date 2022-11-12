
format_exported_py_symbols = $(foreach filepath, \
	$(call rwildcard,$1,.venv $(TMP) $2), \
	$(info cat $(filepath) | $(PYTHON) $(DEVBIN)/format_exported_py_symbols.py $(3) > $(filepath)) \
	$(shell cat $(filepath) | $(PYTHON) $(DEVBIN)/format_exported_py_symbols.py $(3) > $(filepath)~) \
	$(shell test -f $(filepath)~ && cp -f $(filepath)~ $(filepath) && rm $(filepath)~) \
)


.PHONY: dev.bin.format.exported_py_symbols
dev.bin.format.exported_py_symbols:
	$(call format_exported_py_symbols,__init__.py,,-export-all)
	$(call format_exported_py_symbols,*.py,__init__.py)
