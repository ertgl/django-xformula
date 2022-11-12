
.PHONY: unittest.run
unittest.run:
	$(PYTHON) dev/django/manage.py test $(PREPEND_ARGV) $(app_name)


.PHONY: unittest.run.verbose
unittest.run.verbose: PREPEND_ARGV=-v 2
unittest.run.verbose: unittest.run
