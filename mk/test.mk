include mk/test/*.mk


.PHONY: test
test: unittest.run


.PHONY: test.verbose
test.verbose: unittest.run.verbose
