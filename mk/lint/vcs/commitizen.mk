
.PHONY: lint.vcs.commitizen
lint.vcs.commitizen:
	$(COMMITIZEN) check --rev-range HEAD
