
.PHONY: venv.init
venv.init:
	test -d $(VENV) || virtualenv $(VENV) -p python3
