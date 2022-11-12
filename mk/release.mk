include mk/release/*.mk


.PHONY: release
release: twine.upload
