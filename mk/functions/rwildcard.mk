
# Usage: $(call rwildcard,__init__.py,.venv)
rwildcard = $(filter-out $3$2, \
	$(wildcard $3$1) \
	$(foreach entry, \
		$(filter-out $(wildcard $3$2), $(wildcard $3*)), \
		$(call rwildcard,$1,$2,$(entry)/) \
	) \
)
