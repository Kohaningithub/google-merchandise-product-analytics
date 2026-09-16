.PHONY: audit models validate export analyze monitor site test all
audit models validate export analyze monitor site:
	python -m src.pipeline $@
test:
	python -m pytest
	python -m ruff check src tests airflow
all:
	python -m src.pipeline all
