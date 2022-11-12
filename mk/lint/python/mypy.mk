
.PHONY: lint.python.mypy
lint.python.mypy:
	$(MYPY) --cache-dir $(MYPY_CACHE) --exclude '$(TMP)' --explicit-package-bases --namespace-packages .
