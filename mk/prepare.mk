include mk/prepare/*.mk


.PHONY: prepare
prepare: venv.init deps.install
