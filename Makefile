# 'make' by itself runs the 'all' target
.DEFAULT_GOAL := all

.PHONY: all
all:	format lint

.PHONY: format
format:
	@echo "[Task] Starting format *********************************************"
	find . -name "*.py" | xargs black --diff
	find . -name "*.py" | xargs black

.PHONY: lint
lint:
	@echo "[Task] Starting yamllint *******************************************"
	find . -name "*.yaml" | xargs yamllint
	@echo "[Task] Starting pylint *********************************************"
	find . -name "*.py" | xargs pylint
	@echo "[Task] Starting bandit *********************************************"
	find . -name "*.py" | xargs bandit
